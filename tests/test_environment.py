import pytest

from coolforge.environment import inspect_environment


def test_local_structured_evidence():
    result = inspect_environment()
    assert isinstance(result.cool_verified, bool)
    assert len(result.build_sha256) == 64
    assert result.status


def test_corroborated_evidence():
    result = inspect_environment(
        version="5.0.0",
        machine="aarch64",
        cool_exists=True,
        module_path="/opt/cool/python_3.12/site-packages/cv2/__init__.py",
        build="Custom HAL: KleidiCV 0.7.0\nCPU: SVE NEON",
    )
    assert result.cool_verified and result.opencv5_verified


@pytest.mark.parametrize(
    "change",
    [
        {"version": "4.13.0"},
        {"machine": "AMD64"},
        {"cool_exists": False},
        {"module_path": "/tmp/opt/cool/cv2.so"},
        {"build": "CPU: SVE NEON"},
        {"build": "Custom HAL: NO"},
        {"build": "Custom HAL: disabled"},
        {"build": "Custom HAL:"},
        {"build": "Custom HAL = NO"},
        {"build": "KleidiCV: unavailable"},
    ],
)
def test_weak_evidence_never_verifies(change):
    evidence = dict(
        version="5.0.0",
        machine="aarch64",
        cool_exists=True,
        module_path="/opt/cool/cv2.so",
        build="Custom HAL: KleidiCV",
    )
    evidence.update(change)
    assert not inspect_environment(**evidence).cool_verified
