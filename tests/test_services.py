from pathlib import Path

from PIL import Image

from general_bug_report.services import compress_image_to_jpg


def test_compress_image_to_jpg(tmp_path: Path):
    src = tmp_path / "a.png"
    Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(src)

    dst = compress_image_to_jpg(src)

    assert dst.exists()
    assert dst.suffix == ".jpg"
    assert not src.exists()
