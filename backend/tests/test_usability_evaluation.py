from copy import deepcopy

import pytest

from evaluation.usability.study import blank_study, summarize_study, validate_study


def completed_study() -> dict:
    study = blank_study()
    study["study_date"] = "2026-09-20"
    for index, participant in enumerate(study["participants"]):
        participant["tasks"] = {
            "upload": "success",
            "interpret_result": "success" if index < 4 else "assisted",
            "visual_evidence": "success",
            "history": "success",
            "report": "success",
        }
        participant["ratings"] = {
            "upload_ease": 5,
            "result_clarity": 4,
            "evidence_limitations_clarity": 4,
        }
    return study


def test_blank_study_is_anonymous_and_not_publishable() -> None:
    study = blank_study()
    validate_study(study)

    assert [participant["id"] for participant in study["participants"]] == [
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
    ]
    summary = summarize_study(study)
    assert summary["completed_participants"] == 0
    assert summary["study_complete"] is False
    assert summary["publishable"] is False


def test_completed_study_reports_task_counts_and_ratings() -> None:
    summary = summarize_study(completed_study())

    assert summary["completed_participants"] == 5
    assert summary["publishable"] is True
    assert summary["task_results"]["interpret_result"] == {
        "success": 4,
        "assisted": 1,
        "failed": 0,
        "not_run": 0,
    }
    assert summary["rating_results"]["result_clarity"] == {
        "responses": 5,
        "mean": 4,
    }


def test_study_rejects_personal_fields_and_invalid_values() -> None:
    study = completed_study()
    invalid = deepcopy(study)
    invalid["participants"][0]["name"] = "Do not store names"
    invalid["participants"][1]["ratings"]["upload_ease"] = 6
    invalid["participants"][2]["tasks"]["history"] = "maybe"

    with pytest.raises(ValueError, match="unexpected fields") as error:
        validate_study(invalid)

    message = str(error.value)
    assert "integer from 1 to 5" in message
    assert "invalid task statuses" in message
