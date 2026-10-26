from dataclasses import replace

import pytest

from coolforge.agent import PipelineOptimizationAgent
from coolforge.config import PipelineConfig
from coolforge.dataset import generate_samples
from coolforge.models import EvaluationResult
from coolforge.pipeline import PipelineError


def observation(config, f1=0.95, latency=10, recall=None, precision=None):
    return EvaluationResult(config, {"f1": f1, "iou": f1,
                                     "recall": f1 if recall is None else recall,
                                     "precision": f1 if precision is None else precision},
                            {"p50_ms": latency, "mean_ms": latency}, {}, [{"id": "test"}], [])


def test_closed_loop_rejects_and_changes_next_decision():
    calls = []

    def evaluator(samples, config):
        calls.append(config)
        if len(calls) == 2:
            return observation(config, f1=0.4, recall=0.3, latency=2)
        return observation(config, latency=10 if len(calls) == 1 else 8)

    result = PipelineOptimizationAgent(max_iterations=3, evaluator=evaluator).run([])
    assert len(calls) == 4
    assert not result.trace[0].accepted
    assert "Quality floor" in result.trace[0].failure
    assert result.trace[1].action.startswith("adaptive_c")
    assert "lost recall" in result.trace[1].rationale
    assert result.trace[1].accepted
    assert result.final.config.processing_scale == 1  # rejected scale did not leak
    assert PipelineConfig.from_dict(result.final.config.to_dict()) == result.final.config


def test_observations_select_different_actions():
    agent = PipelineOptimizationAgent()
    config = PipelineConfig()
    fast = agent.decide(observation(config), {config}, None)
    noisy = agent.decide(observation(config, precision=0.5), {config}, None)
    assert fast[1].startswith("processing_scale")
    assert noisy[1].startswith("adaptive_c")
    assert noisy[0].adaptive_c > config.adaptive_c


def test_objective_and_infeasible_stops():
    agent = PipelineOptimizationAgent(latency_target_ms=15, evaluator=lambda s, c: observation(c))
    result = agent.run([])
    assert result.stop_reason == "objective_met" and not result.trace
    agent = PipelineOptimizationAgent(max_iterations=2,
                                      evaluator=lambda s, c: observation(c, f1=0.3))
    result = agent.run([])
    assert result.stop_reason == "quality_floor_unmet" and not result.feasible
    assert not any(entry.accepted for entry in result.trace)


def test_failed_candidate_retains_incumbent():
    def evaluator(samples, config):
        if config != PipelineConfig():
            raise PipelineError("deliberate failure")
        return observation(config)
    result = PipelineOptimizationAgent(max_iterations=2, evaluator=evaluator).run([])
    assert result.final == result.initial
    assert all(entry.failure == "deliberate failure" for entry in result.trace)


def test_real_agent_invokes_opencv():
    result = PipelineOptimizationAgent(quality_floor=0.6, max_iterations=3).run(generate_samples(5))
    assert len(result.trace) == 3
    assert all(entry.result is not None for entry in result.trace)
    assert result.initial.valid and result.final.valid


def test_initial_failure_stops():
    def evaluator(samples, config):
        return replace(observation(config), failures=[{"error": "bad sample"}])
    assert PipelineOptimizationAgent(evaluator=evaluator).run([]).stop_reason == "initial_evaluation_failed"


@pytest.mark.parametrize("kwargs", [{"quality_floor": 2}, {"max_iterations": 0},
                                     {"latency_target_ms": float("nan")}])
def test_invalid_budget(kwargs):
    with pytest.raises(ValueError):
        PipelineOptimizationAgent(**kwargs)
