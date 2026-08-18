from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://huggingface.co/yyouretoast/deepfake-detector/resolve/main/dual_stream_calibrated.pth"
)
EXPECTED_SHA256 = "c5c2002b5ef6c7ee0c542d7d203e16386dc641b685859d8a58ac883b52c8e4c9"


def download(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "AI-Forensics/0.1"})
    try:
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            temporary.open("wb") as output,
        ):
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    digest = hashlib.sha256()
    with destination.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest.update(chunk)
    checksum = digest.hexdigest()
    if checksum != EXPECTED_SHA256:
        destination.unlink(missing_ok=True)
        raise ValueError(
            f"Checkpoint checksum mismatch: expected {EXPECTED_SHA256}, received {checksum}"
        )
    return checksum


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the attributed deepfake checkpoint")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/dual_stream_calibrated.pth"),
    )
    args = parser.parse_args()
    checksum = download(args.output)
    print(f"Downloaded {args.output} (SHA-256: {checksum})")


if __name__ == "__main__":
    main()
