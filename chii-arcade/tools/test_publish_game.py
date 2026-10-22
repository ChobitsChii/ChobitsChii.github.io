"""Regression tests for the public store publisher (no network or SDK required)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PUBLISHER = Path(__file__).with_name("publish_game.py")
spec = importlib.util.spec_from_file_location("publish_game", PUBLISHER)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

SIGNER = "f180a9c294153bdc6fb700794bf980736ff1785331058beb933e474b8c8fcb5c"


class PublishGameTest(unittest.TestCase):
    def test_dry_run_accepts_normal_apk_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            apk = root / "kaskellia-m07.apk"
            apk.write_bytes(b"test only")
            config = root / "chii-arcade.json"
            config.write_text(json.dumps({
                "id": "kaskellia",
                "title": "Kaskellia", "category": "Puzzle",
                "teaser": "Kugelrätsel", "description": "Eine Beschreibung", "symbol": "🌸",
                "android": {
                    "packageName": "de.chobitschii.kaskellia",
                    "signingCertificateSha256": SIGNER,
                }
            }), encoding="utf-8")
            with (
                patch.object(sys, "argv", ["publish_game.py", "--config", str(config),
                                           "--apk", str(apk), "--dry-run"]),
                patch.object(publisher, "inspect_apk",
                             return_value=("de.chobitschii.kaskellia", 7, "0.7.0", SIGNER)),
            ):
                self.assertEqual(0, publisher.main())

    def test_filename_rejects_unsafe_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            apk = Path(temp) / "bad name.apk"
            apk.write_bytes(b"test")
            config = Path(temp) / "config.json"
            config.write_text("{}")
            with patch.object(sys, "argv", ["publish_game.py", "--config", str(config),
                                            "--apk", str(apk), "--dry-run"]):
                with self.assertRaisesRegex(RuntimeError, "APK-Dateiname"):
                    publisher.main()


if __name__ == "__main__":
    unittest.main()
