"""Conservative COOL verification; filesystem presence alone is insufficient."""

import hashlib
import platform
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2


@dataclass
class EnvironmentEvidence:
    python_version: str
    platform: str
    machine: str
    cv2_version: str
    cv2_file: str
    opencv5_verified: bool
    cool_verified: bool
    architecture_arm64: bool
    cool_root_exists: bool
    build_excerpt: list[str]
    build_sha256: str
    evidence: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def status(self) -> str:
        if self.cool_verified:
            return "OpenCV 5 + COOL VERIFIED"
        if self.opencv5_verified:
            return "OpenCV 5 / COOL NOT VERIFIED"
        return "LOCAL DEVELOPMENT — unsupported OpenCV major version"


def inspect_environment(
    *,
    version: str | None = None,
    module_path: str | None = None,
    machine: str | None = None,
    build: str | None = None,
    cool_exists: bool | None = None,
) -> EnvironmentEvidence:
    version = cv2.__version__ if version is None else version
    module_path = cv2.__file__ if module_path is None else module_path
    machine = platform.machine() if machine is None else machine
    build = cv2.getBuildInformation() if build is None else build
    exists = Path("/opt/cool").is_dir() if cool_exists is None else cool_exists
    opencv5 = version.split(".")[0] == "5"
    arm = machine.lower() in {"aarch64", "arm64"}
    path_ok = str(module_path).replace("\\", "/").startswith("/opt/cool/")
    excerpt = [
        line.strip()
        for line in build.splitlines()
        if any(
            marker in line.lower()
            for marker in (
                "kleidicv",
                "custom hal",
                "sve",
                "neon",
                "parallel framework",
                "version control",
            )
        )
    ]
    # SVE/NEON alone are generic Arm features; require an affirmative custom backend.
    accelerated = False
    for line in excerpt:
        marker = re.search(r"(kleidicv|custom hal)\s*[:=]\s*(.*)", line, re.I)
        if (
            marker
            and marker.group(2).strip()
            and not re.search(
                r"\b(no|none|off|false|disabled|unavailable|n/a)\b", marker.group(2), re.I
            )
        ):
            accelerated = True
    checks = {
        "OpenCV major version 5": opencv5,
        "Arm64 architecture": arm,
        "COOL installation root exists": exists,
        "cv2 loaded from /opt/cool": path_ok,
        "Affirmative custom acceleration build marker": accelerated,
    }
    verified = all(checks.values())
    warnings = [f"Not verified: {label}" for label, passed in checks.items() if not passed]
    warnings.append("Build provenance does not prove per-operation acceleration or AWS hosting")
    return EnvironmentEvidence(
        platform.python_version(),
        platform.platform(),
        machine,
        version,
        str(module_path),
        opencv5,
        verified,
        arm,
        exists,
        excerpt,
        hashlib.sha256(build.encode()).hexdigest(),
        [label for label, passed in checks.items() if passed],
        warnings,
    )


def runtime_identity() -> dict:
    """A local host fingerprint supports pairing without disclosing its hostname."""
    return {
        "host_id": hashlib.sha256(platform.node().encode()).hexdigest()[:16],
        "processor": platform.processor(),
        "python_implementation": sys.implementation.name,
        "cv_threads": cv2.getNumThreads(),
    }
