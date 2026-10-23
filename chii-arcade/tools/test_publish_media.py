"""Offline tests for the media-only publisher. Nothing is written to GitHub."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).with_name("publish_media.py")
spec = importlib.util.spec_from_file_location("publish_media", MODULE)
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


class MediaPublisherTests(unittest.TestCase):
    def example(self, folder: Path) -> Path:
        (folder / "store-media").mkdir()
        for name in ("cover.webp", "level.webp"):
            (folder / "store-media" / name).write_bytes(
                b"RIFF" + (4).to_bytes(4, "little") + b"WEBP" + name.encode()
            )
        config = folder / "chii-arcade.json"
        config.write_text(json.dumps({
            "id": "kaskellia",
            "coverImage": "store-media/cover.webp",
            "screenshots": ["store-media/level.webp"]
        }), encoding="utf-8")
        return config

    def test_dry_run_does_not_use_github(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.example(Path(directory))
            with (
                patch.object(sys, "argv", ["publish_media", "--config", str(config), "--dry-run"]),
                patch.object(media, "gh_api", side_effect=AssertionError("Network used")),
                patch.object(media, "lookup", side_effect=AssertionError("Network used")),
            ):
                self.assertEqual(media.main(), 0)

    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.example(Path(directory))
            cfg = json.loads(config.read_text())
            cfg["coverImage"] = "../secrets.webp"
            config.write_text(json.dumps(cfg))
            with patch.object(sys, "argv", ["publish_media", "--config", str(config), "--dry-run"]):
                with self.assertRaisesRegex(ValueError, "Bildpfad"):
                    media.main()

    def test_rejects_more_than_eight_screenshots(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.example(Path(directory))
            cfg = json.loads(config.read_text())
            cfg["screenshots"] = ["store-media/level.webp"] * 9
            config.write_text(json.dumps(cfg))
            with patch.object(sys, "argv", ["publish_media", "--config", str(config), "--dry-run"]):
                with self.assertRaisesRegex(ValueError, "1–8"):
                    media.main()


if __name__ == "__main__":
    unittest.main()
