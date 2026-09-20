"""Create, validate, and summarize the anonymous Y-03 usability study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

PARTICIPANT_IDS = tuple(f"P{index}" for index in range(1, 6))
TASKS = (
    "upload",
    "interpret_result",
    "visual_evidence",
    "history",
    "report",
)
RATINGS = (
    "upload_ease",
    "result_clarity",
    "evidence_limitations_clarity",
)
TASK_STATUSES = {"success", "assisted", "failed", "not_run"}
PARTICIPANT_FIELDS = {
    "id",
    "tasks",
    "ratings",
    "most_confusing",
    "recommended_change",
}


def blank_study() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "Y-03",
        "protocol": "five-person-formative-usability-study-v1",
        "study_date": None,
        "participants": [
            {
                "id": participant_id,
                "tasks": {task: "not_run" for task in TASKS},
                "ratings": {rating: None for rating in RATINGS},
                "most_confusing": "",
                "recommended_change": "",
            }
            for participant_id in PARTICIPANT_IDS
        ],
    }


def _validate_participant(participant: dict[str, Any]) -> list[str]:
    participant_id = participant.get("id", "unknown")
    errors: list[str] = []
    extra_fields = set(participant) - PARTICIPANT_FIELDS
    if extra_fields:
        errors.append(
            f"{participant_id}: unexpected fields {sorted(extra_fields)}; "
            "do not record personal data"
        )

    tasks = participant.get("tasks")
    if not isinstance(tasks, dict) or set(tasks) != set(TASKS):
        errors.append(f"{participant_id}: tasks must contain exactly {list(TASKS)}")
    elif invalid := {value for value in tasks.values() if value not in TASK_STATUSES}:
        errors.append(f"{participant_id}: invalid task statuses {sorted(invalid)}")

    ratings = participant.get("ratings")
    if not isinstance(ratings, dict) or set(ratings) != set(RATINGS):
        errors.append(f"{participant_id}: ratings must contain exactly {list(RATINGS)}")
    else:
        for name, value in ratings.items():
            invalid_rating = (
                value is not None
                and (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 1 <= value <= 5
                )
            )
            if invalid_rating:
                errors.append(f"{participant_id}: {name} must be an integer from 1 to 5 or null")

    for field in ("most_confusing", "recommended_change"):
        value = participant.get(field)
        if not isinstance(value, str) or len(value) > 500:
            errors.append(f"{participant_id}: {field} must be text of at most 500 characters")
    return errors


def validate_study(study: dict[str, Any]) -> None:
    errors: list[str] = []
    if study.get("schema_version") != 1 or study.get("task") != "Y-03":
        errors.append("Unsupported usability study schema")

    participants = study.get("participants")
    if not isinstance(participants, list):
        errors.append("participants must be a list")
    else:
        participant_ids = [participant.get("id") for participant in participants]
        if participant_ids != list(PARTICIPANT_IDS):
            errors.append(f"participants must appear exactly as {list(PARTICIPANT_IDS)}")
        for participant in participants:
            if not isinstance(participant, dict):
                errors.append("each participant must be an object")
                continue
            errors.extend(_validate_participant(participant))

    if errors:
        raise ValueError("; ".join(errors))


def summarize_study(study: dict[str, Any]) -> dict[str, Any]:
    validate_study(study)
    participants = study["participants"]
    completed = [
        participant
        for participant in participants
        if "not_run" not in participant["tasks"].values()
        and all(value is not None for value in participant["ratings"].values())
    ]

    task_results = {
        task: {
            status: sum(participant["tasks"][task] == status for participant in participants)
            for status in ("success", "assisted", "failed", "not_run")
        }
        for task in TASKS
    }
    rating_results = {}
    for rating in RATINGS:
        values = [
            participant["ratings"][rating]
            for participant in participants
            if participant["ratings"][rating] is not None
        ]
        rating_results[rating] = {
            "responses": len(values),
            "mean": round(mean(values), 2) if values else None,
        }

    study_complete = len(completed) == len(PARTICIPANT_IDS)
    return {
        "schema_version": 1,
        "task": "Y-03",
        "study_complete": study_complete,
        "publishable": study_complete,
        "completed_participants": len(completed),
        "required_participants": len(PARTICIPANT_IDS),
        "task_results": task_results,
        "rating_results": rating_results,
        "most_confusing": [
            participant["most_confusing"]
            for participant in completed
            if participant["most_confusing"].strip()
        ],
        "recommended_changes": [
            participant["recommended_change"]
            for participant in completed
            if participant["recommended_change"].strip()
        ],
        "interpretation": (
            "All five anonymous participant records are complete. Results remain formative, "
            "not population-level evidence."
            if study_complete
            else (
                "Study is incomplete. Do not report participant success rates or claim "
                "Y-03 completion."
            )
        ),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a blank anonymous study record")
    init_parser.add_argument("output", type=Path)

    summary_parser = subparsers.add_parser("summarize", help="Validate and summarize a study")
    summary_parser.add_argument("input", type=Path)
    summary_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "init":
        write_json(args.output, blank_study())
        print(f"Created blank Y-03 study record: {args.output}")
        return

    study = json.loads(args.input.read_text(encoding="utf-8"))
    summary = summarize_study(study)
    write_json(args.output, summary)
    print(
        f"Validated {summary['completed_participants']}/{summary['required_participants']} "
        f"participant records (publishable={summary['publishable']})"
    )


if __name__ == "__main__":
    main()
