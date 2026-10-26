"""Bounded, observation-driven coordinate search with an auditable rollback trail."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from coolforge.config import PipelineConfig
from coolforge.evaluation import evaluate
from coolforge.models import EvaluationResult, Sample
from coolforge.pipeline import PipelineError

SPACE = {
    "processing_scale": (1.0, 0.9, 0.8, 0.7, 0.6),
    "blur_kernel": (3, 5, 7),
    "adaptive_block_size": (11, 15, 21, 31, 41),
    "adaptive_c": (2.0, 5.0, 8.0, 11.0),
    "morphology_kernel": (1, 3, 5),
    "min_contour_area": (0.0, 5.0, 12.0, 25.0),
}


@dataclass
class AgentTraceEntry:
    iteration: int
    observation: dict[str, Any]
    action: str
    rationale: str
    candidate_config: dict[str, Any]
    result: dict[str, Any] | None
    accepted: bool
    failure: str | None = None


@dataclass
class AgentResult:
    initial: EvaluationResult
    final: EvaluationResult
    trace: list[AgentTraceEntry]
    stop_reason: str
    quality_floor: float
    feasible: bool
    pareto: list[dict[str, Any]]


def snapshot(result: EvaluationResult) -> dict[str, Any]:
    return {"quality": result.quality, "timing": result.timing, "valid": result.valid}


class PipelineOptimizationAgent:
    """Policy is deterministic given observations; measured timing is naturally noisy."""

    def __init__(self, quality_floor: float = 0.85, max_iterations: int = 12,
                 latency_target_ms: float | None = None, min_speed_gain: float = 0.03,
                 evaluator: Callable | None = None) -> None:
        if not 0 <= quality_floor <= 1 or not 1 <= max_iterations <= 100:
            raise ValueError("Quality floor must be in [0, 1]; iteration budget in [1, 100]")
        if latency_target_ms is not None and not 0 < latency_target_ms < float("inf"):
            raise ValueError("Latency target must be finite and positive")
        if not 0 <= min_speed_gain < 1:
            raise ValueError("Minimum speed gain must be in [0, 1)")
        self.quality_floor = quality_floor
        self.max_iterations = max_iterations
        self.latency_target_ms = latency_target_ms
        self.min_speed_gain = min_speed_gain
        self.evaluator = evaluator or (lambda s, c: evaluate(s, c, repetitions=3, warmups=1))

    def decide(self, current: EvaluationResult, tried: set[PipelineConfig],
               last: EvaluationResult | None) -> tuple[PipelineConfig, str, str] | None:
        # A failed scale experiment changes the next branch, even after rollback.
        if last is not None and last.quality["recall"] < self.quality_floor:
            order = ("adaptive_c", "blur_kernel", "adaptive_block_size", "processing_scale")
            reason = "Last candidate lost recall; recover thin-defect sensitivity"
        elif current.quality["precision"] < self.quality_floor:
            order = ("adaptive_c", "min_contour_area", "morphology_kernel", "blur_kernel")
            reason = "False positives dominate; test stronger noise suppression"
        elif current.quality["f1"] < self.quality_floor:
            order = ("adaptive_block_size", "adaptive_c", "blur_kernel", "min_contour_area")
            reason = "Incumbent is infeasible; recover foreground quality first"
        else:
            order = ("processing_scale", "blur_kernel", "adaptive_block_size",
                     "morphology_kernel", "min_contour_area", "adaptive_c")
            reason = "Quality floor is satisfied; probe a cheaper pipeline"
        for field in order:
            values = list(SPACE[field])
            old = getattr(current.config, field)
            if field == "adaptive_c":
                noisy = current.quality["precision"] < self.quality_floor
                values.sort(key=lambda v: (not (v > old if noisy else v < old), abs(v-old)))
            elif field == "processing_scale":
                values.sort(key=lambda v: (v >= old, abs(v-old)))
            else:
                values.sort(key=lambda v: abs(v-old))
            for value in values:
                candidate = replace(current.config, **{field: value})
                if candidate not in tried:
                    return candidate, f"{field}: {old} -> {value}", reason
        return None

    def run(self, samples: list[Sample], config: PipelineConfig | None = None,
            on_step: Callable[[AgentTraceEntry], None] | None = None) -> AgentResult:
        initial = self.evaluator(samples, config or PipelineConfig())
        current, last = initial, None
        trace: list[AgentTraceEntry] = []
        tried = {initial.config}
        observed = [initial] if initial.valid else []
        stop = "iteration_limit"
        if not initial.valid:
            return AgentResult(initial, initial, [], "initial_evaluation_failed",
                               self.quality_floor, False, [])
        for iteration in range(1, self.max_iterations + 1):
            if (current.quality["f1"] >= self.quality_floor
                    and self.latency_target_ms is not None
                    and current.timing["p50_ms"] <= self.latency_target_ms):
                stop = "objective_met"
                break
            decision = self.decide(current, tried, last)
            if decision is None:
                stop = "search_exhausted"
                break
            candidate, action, rationale = decision
            tried.add(candidate)
            observation = {"incumbent": snapshot(current),
                           "previous_candidate": snapshot(last) if last else None}
            failure, result, accepted = None, None, False
            try:
                result = self.evaluator(samples, candidate)
                last = result
                if not result.valid:
                    failure = "Candidate evaluation was incomplete; incumbent retained"
                elif result.quality["f1"] < self.quality_floor:
                    failure = "Quality floor violated; incumbent retained"
                else:
                    faster = result.timing["p50_ms"] < (
                        current.timing["p50_ms"] * (1 - self.min_speed_gain))
                    quality_gain = result.quality["f1"] > current.quality["f1"] + 0.005
                    accepted = (current.quality["f1"] < self.quality_floor or faster
                                or (quality_gain and result.timing["p50_ms"]
                                    <= current.timing["p50_ms"] * 1.02))
                if result.valid:
                    observed.append(result)
            except (ValueError, PipelineError) as exc:
                failure = str(exc)
            entry = AgentTraceEntry(iteration, observation, action, rationale,
                                    candidate.to_dict(), snapshot(result) if result else None,
                                    accepted, failure)
            trace.append(entry)
            if accepted:
                current = result
            if on_step:
                on_step(entry)
        feasible = current.quality["f1"] >= self.quality_floor
        if not feasible and stop == "iteration_limit":
            stop = "quality_floor_unmet"
        frontier = [r for r in observed if r.quality["f1"] >= self.quality_floor and not any(
            other.quality["f1"] >= r.quality["f1"] and
            other.timing["p50_ms"] <= r.timing["p50_ms"] and
            (other.quality["f1"] > r.quality["f1"] or
             other.timing["p50_ms"] < r.timing["p50_ms"]) for other in observed)]
        return AgentResult(initial, current, trace, stop, self.quality_floor, feasible,
                           [{"config": r.config.to_dict(), **snapshot(r)} for r in frontier])
