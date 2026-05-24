import pytest

from app.domain.dag import validate_dag


def test_validate_dag_accepts_valid_graph() -> None:
    validate_dag(
        ["capture_image", "detect_target", "upload_report"],
        [
            ("capture_image", "detect_target"),
            ("detect_target", "upload_report"),
        ],
    )


def test_validate_dag_accepts_branching_graph() -> None:
    validate_dag(
        ["capture_image", "detect_target", "measure_temperature", "upload_report"],
        [
            ("capture_image", "detect_target"),
            ("capture_image", "measure_temperature"),
            ("detect_target", "upload_report"),
            ("measure_temperature", "upload_report"),
        ],
    )


def test_validate_dag_rejects_empty_subtasks() -> None:
    with pytest.raises(ValueError, match="at least one subtask"):
        validate_dag([], [])


def test_validate_dag_rejects_duplicate_subtask_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        validate_dag(["capture_image", "capture_image"], [])


def test_validate_dag_rejects_unknown_dependency_reference() -> None:
    with pytest.raises(ValueError, match="unknown subtask"):
        validate_dag(
            ["capture_image", "upload_report"],
            [("capture_image", "detect_target")],
        )


def test_validate_dag_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="depend on itself"):
        validate_dag(
            ["capture_image"],
            [("capture_image", "capture_image")],
        )


def test_validate_dag_rejects_cycle() -> None:
    with pytest.raises(ValueError, match="cycle"):
        validate_dag(
            ["a", "b", "c"],
            [
                ("a", "b"),
                ("b", "c"),
                ("c", "a"),
            ],
        )
