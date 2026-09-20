from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import cv2

from evaluation.deepfake.metrics import binary_metrics

MANIPULATIONS = ("Deepfakes", "Face2Face", "FaceSwap", "NeuralTextures")
METADATA_FIELDS = ("path", "label", "identity_ids", "source_group", "manipulation")
AGGREGATIONS = ("mean", "top20", "softmax")


@dataclass(frozen=True)
class VideoRecord:
    relative_path: str
    label: str
    identity_ids: tuple[str, ...]
    source_group: str
    manipulation: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def fixed_frame_indexes(frame_count: int) -> tuple[int, ...]:
    """Choose five interior, evenly spaced frame indexes without using model output."""
    if frame_count < 5:
        raise ValueError("A video needs at least five frames for the frozen protocol")
    indexes = tuple(min(frame_count - 1, frame_count * position // 6) for position in range(1, 6))
    if len(set(indexes)) != 5:
        raise ValueError("Could not choose five distinct frame positions")
    return indexes


def read_official_pairs(path: Path) -> list[tuple[str, str]]:
    raw_pairs = json.loads(path.read_text(encoding="utf-8"))
    pairs = [tuple(str(item) for item in pair) for pair in raw_pairs]
    if len(pairs) != 70 or any(len(pair) != 2 for pair in pairs):
        raise ValueError("Expected the official frozen test.json containing 70 pairs")
    identities = [identity for pair in pairs for identity in pair]
    if len(set(identities)) != 140:
        raise ValueError("Expected 140 unique source sequences across the 70 test pairs")
    return pairs


def build_video_records(pairs: list[tuple[str, str]]) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    for first, second in pairs:
        source_group = "ffpp-pair-" + "-".join(sorted((first, second)))
        for sequence_id in (first, second):
            records.append(
                VideoRecord(
                    relative_path=f"original_sequences/youtube/c23/videos/{sequence_id}.mp4",
                    label="real",
                    identity_ids=(f"ffpp-sequence-{sequence_id}",),
                    source_group=source_group,
                    manipulation="original",
                )
            )
        for manipulation in MANIPULATIONS:
            for source_id, target_id in ((first, second), (second, first)):
                records.append(
                    VideoRecord(
                        relative_path=(
                            f"manipulated_sequences/{manipulation}/c23/videos/"
                            f"{source_id}_{target_id}.mp4"
                        ),
                        label="fake",
                        identity_ids=tuple(
                            sorted(
                                (
                                    f"ffpp-sequence-{source_id}",
                                    f"ffpp-sequence-{target_id}",
                                )
                            )
                        ),
                        source_group=source_group,
                        manipulation=manipulation,
                    )
                )
    if len(records) != 700:
        raise ValueError(f"Expected 700 videos, constructed {len(records)}")
    return records


def _aggregate_scores(scores: list[float], method: str) -> float:
    if not scores:
        raise ValueError("Cannot aggregate an empty score list")
    if method == "mean":
        return sum(scores) / len(scores)
    if method == "top20":
        count = max(1, math.ceil(len(scores) * 0.2))
        return sum(sorted(scores, reverse=True)[:count]) / count
    if method == "softmax":
        temperature = 0.1
        scaled = [score / temperature for score in scores]
        maximum = max(scaled)
        weights = [math.exp(value - maximum) for value in scaled]
        return sum(score * weight for score, weight in zip(scores, weights, strict=True)) / sum(
            weights
        )
    raise ValueError(f"Unsupported video aggregation: {method}")


def video_level_metrics(rows: list[dict[str, object]], *, threshold: float) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        sample_path = PurePosixPath(str(row["path"]))
        parent = sample_path.parent.as_posix()
        video_key = sample_path.as_posix() if parent == "." else parent
        grouped[video_key].append(row)

    output: dict[str, object] = {}
    for method in AGGREGATIONS:
        videos = []
        for video_key, video_rows in sorted(grouped.items()):
            evaluated = [row for row in video_rows if row["status"] == "evaluated"]
            if not evaluated:
                continue
            labels = {int(row["label"]) for row in video_rows}
            manipulations = {str(row["manipulation"]) for row in video_rows}
            if len(labels) != 1 or len(manipulations) != 1:
                raise ValueError(f"Inconsistent frame metadata for video {video_key!r}")
            videos.append(
                {
                    "video": video_key,
                    "label": labels.pop(),
                    "manipulation": manipulations.pop(),
                    "score": _aggregate_scores(
                        [float(row["score"]) for row in evaluated], method
                    ),
                    "evaluated_frames": len(evaluated),
                    "expected_frames": len(video_rows),
                }
            )
        labels = [int(video["label"]) for video in videos]
        scores = [float(video["score"]) for video in videos]
        original_videos = [video for video in videos if video["manipulation"] == "original"]
        by_manipulation = {}
        for manipulation in sorted(
            {str(video["manipulation"]) for video in videos if video["manipulation"] != "original"}
        ):
            comparison = original_videos + [
                video for video in videos if video["manipulation"] == manipulation
            ]
            by_manipulation[manipulation] = binary_metrics(
                [int(video["label"]) for video in comparison],
                [float(video["score"]) for video in comparison],
                threshold=threshold,
            )
        output[method] = {
            "evaluated_videos": len(videos),
            "videos_without_evaluated_frames": len(grouped) - len(videos),
            "metrics": binary_metrics(labels, scores, threshold=threshold),
            "metrics_by_manipulation": by_manipulation,
        }
    return output


def _extract_record(
    record: VideoRecord, *, video_root: Path, frame_root: Path
) -> tuple[list[dict[str, str]], dict[str, object]]:
    video_path = video_root / Path(record.relative_path)
    plan: dict[str, object] = {
        "video": record.relative_path,
        "label": record.label,
        "source_group": record.source_group,
        "manipulation": record.manipulation,
        "video_sha256": None,
        "reported_frame_count": 0,
        "frozen_frame_indexes": [],
        "decoded_frame_indexes": [],
        "failures": [],
    }
    if not video_path.is_file():
        plan["failures"] = ["missing_video"]
        return [], plan

    plan["video_sha256"] = sha256_file(video_path)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        plan["failures"] = ["open_error"]
        capture.release()
        return [], plan
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    plan["reported_frame_count"] = frame_count
    try:
        indexes = fixed_frame_indexes(frame_count)
    except ValueError as error:
        plan["failures"] = [str(error)]
        capture.release()
        return [], plan
    plan["frozen_frame_indexes"] = list(indexes)

    stem = Path(record.relative_path).stem
    output_directory = frame_root / record.manipulation / stem
    rows: list[dict[str, str]] = []
    for frame_index in indexes:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, image = capture.read()
        if not ok or image is None:
            plan["failures"].append(f"decode_error:{frame_index}")
            continue
        relative_frame = Path(record.manipulation) / stem / f"frame_{frame_index:06d}.png"
        output_path = frame_root / relative_frame
        output_directory.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(
            str(output_path), image, [cv2.IMWRITE_PNG_COMPRESSION, 1]
        ):
            plan["failures"].append(f"write_error:{frame_index}")
            continue
        plan["decoded_frame_indexes"].append(frame_index)
        rows.append(
            {
                "path": relative_frame.as_posix(),
                "label": record.label,
                "identity_ids": ";".join(record.identity_ids),
                "source_group": record.source_group,
                "manipulation": record.manipulation,
            }
        )
    capture.release()
    return rows, plan


def extract_frozen_frames(
    *, test_json: Path, video_root: Path, frame_root: Path, metadata_path: Path, plan_path: Path
) -> dict[str, object]:
    pairs = read_official_pairs(test_json)
    records = build_video_records(pairs)
    metadata_rows: list[dict[str, str]] = []
    video_plans: list[dict[str, object]] = []
    extracted: dict[int, tuple[list[dict[str, str]], dict[str, object]]] = {}
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _extract_record,
                record,
                video_root=video_root,
                frame_root=frame_root,
            ): (index, record)
            for index, record in enumerate(records)
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            index, record = futures[future]
            extracted[index] = future.result()
            print(f"[{completed:03d}/{len(records)}] {record.relative_path}", flush=True)

    for index in range(len(records)):
        rows, plan = extracted[index]
        metadata_rows.extend(rows)
        video_plans.append(plan)

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(metadata_rows)

    summary: dict[str, object] = {
        "protocol": "FaceForensics++ official 70-pair test set; five positions i/6, i=1..5",
        "test_json_sha256": sha256_file(test_json),
        "video_count_expected": 700,
        "video_count_with_all_frames": sum(
            len(plan["decoded_frame_indexes"]) == 5 for plan in video_plans
        ),
        "frame_count_expected": 3500,
        "frame_count_extracted": len(metadata_rows),
        "videos_with_failures": sum(bool(plan["failures"]) for plan in video_plans),
        "videos": video_plans,
    }
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze and extract five model-independent frames per official test video"
    )
    parser.add_argument("--test-json", required=True, type=Path)
    parser.add_argument("--video-root", required=True, type=Path)
    parser.add_argument("--frame-root", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--frame-plan", required=True, type=Path)
    args = parser.parse_args()
    summary = extract_frozen_frames(
        test_json=args.test_json,
        video_root=args.video_root,
        frame_root=args.frame_root,
        metadata_path=args.metadata,
        plan_path=args.frame_plan,
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "videos"}, indent=2))


if __name__ == "__main__":
    main()
