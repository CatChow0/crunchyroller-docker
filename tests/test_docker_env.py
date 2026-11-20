"""Env overrides used by the Docker image: allowed origins and data directory."""

import importlib
import os
import unittest
from unittest.mock import patch

from crunchyroll.server import _origin_allowed


class OriginAllowedTests(unittest.TestCase):
    def test_localhost_always_allowed(self):
        with patch.dict(os.environ, {"CRUNCHYROLLER_ALLOWED_ORIGINS": ""}):
            self.assertTrue(_origin_allowed("localhost"))
            self.assertTrue(_origin_allowed("127.0.0.1"))
            self.assertFalse(_origin_allowed("192.168.1.20"))
            self.assertFalse(_origin_allowed(None))

    def test_extra_origins_from_env(self):
        with patch.dict(os.environ, {"CRUNCHYROLLER_ALLOWED_ORIGINS": "192.168.1.20, Crunchy.Example.org"}):
            self.assertTrue(_origin_allowed("192.168.1.20"))
            self.assertTrue(_origin_allowed("crunchy.example.org"))
            self.assertFalse(_origin_allowed("evil.example.org"))


class DataDirTests(unittest.TestCase):
    def test_config_file_follows_data_dir(self):
        import crunchyroll.auth as auth
        try:
            with patch.dict(os.environ, {"CRUNCHYROLLER_DATA_DIR": os.path.abspath("somewhere")}):
                importlib.reload(auth)
                self.assertEqual(auth.CONFIG_FILE, os.path.join(os.path.abspath("somewhere"), "config.json"))
        finally:
            importlib.reload(auth)


if __name__ == "__main__":
    unittest.main()
