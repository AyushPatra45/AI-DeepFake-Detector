from pathlib import Path

import pytest
from app.forensics.keyed_lsb import recover
from PIL import Image

from evaluation.steganography.corpus import embed_keyed_layout


def test_recovers_exact_binary_payload_with_known_seed(tmp_path: Path) -> None:
    path = tmp_path / "keyed.png"
    payload = b"binary\0payload\xff"
    embed_keyed_layout(Image.new("RGB", (32, 32)), payload, 812).save(path)

    assert recover(path, seed=812, payload_size=len(payload)) == payload
    with pytest.raises(ValueError, match="marker or terminator"):
        recover(path, seed=813, payload_size=len(payload))


def test_rejects_payload_larger_than_image(tmp_path: Path) -> None:
    path = tmp_path / "small.png"
    Image.new("RGB", (4, 4)).save(path)
    with pytest.raises(ValueError, match="capacity"):
        recover(path, seed=1, payload_size=128)
