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
