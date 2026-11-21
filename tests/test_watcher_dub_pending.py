"""Watcher keeps episodes pending until they exist in the requested dub (audio fallback off)."""

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from crunchyroll.types import DubVersion
from crunchyroll.watcher import MonitoredStore, SeriesWatcher, _audio_ready


def ep(ep_id, num, locales):
    return SimpleNamespace(
        id=ep_id, episode_number=num, season_number=3, title=f"Ep {num}", season_title="",
        audio_locale=locales[0] if locales else "",
        versions=[DubVersion(audio_locale=l, guid=f"{ep_id}-{l}") for l in locales],
    )


class DubPendingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue = MagicMock()
        self.queue.queue = []
        self.queue.active_job = None
        self.queue.enqueue_batch.side_effect = lambda items, *a, **k: list(items)
        self.cfg = {
            "audio_lang": "fr-FR", "subs_lang": "fr-FR", "video_quality": "1080p",
            "audio_quality": "192k", "download_dir": os.path.join(self.tmp, "dl"),
            "audio_fallback": False,
        }
        os.makedirs(self.cfg["download_dir"])
        self.watcher = SeriesWatcher(
            queue=self.queue,
            client_factory=lambda: MagicMock(),
            config_provider=lambda: self.cfg,
            store=MonitoredStore(os.path.join(self.tmp, "m.json")),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _enqueued_ids(self):
        return [i["id"] for call in self.queue.enqueue_batch.call_args_list for i in call.args[0]]

    def _known(self, sid):
        return set(self.watcher.store.load()["series"][sid]["known_episodes"])

    @patch("crunchyroll.api.get_series")
    def test_late_dub_is_downloaded_once_released(self, get_series):
        vf1, vf2 = ep("E1", 1, ["ja-JP", "fr-FR"]), ep("E2", 2, ["ja-JP", "fr-FR"])
        get_series.return_value = {"episodes": [vf1, vf2, ep("E3", 3, ["ja-JP"])]}
        self.watcher.add_series("S", "Apothecary", mode="latest_only")
        # E3 is out in VO only: not part of the baseline
        self.assertEqual(self._known("S"), {"E1", "E2"})

        self.watcher.check_series("S")
        self.assertEqual(self._enqueued_ids(), [])  # VO-only: not queued
        self.assertEqual(self._known("S"), {"E1", "E2"})  # still pending

        # VF of E3 is released, E4 airs in VO only
        get_series.return_value = {"episodes": [vf1, vf2, ep("E3", 3, ["ja-JP", "fr-FR"]), ep("E4", 4, ["ja-JP"])]}
        self.watcher.check_series("S")
        self.assertEqual(self._enqueued_ids(), ["E3"])
        self.assertEqual(self._known("S"), {"E1", "E2", "E3"})

    @patch("crunchyroll.api.get_series")
    def test_all_missing_skips_vo_only(self, get_series):
        get_series.return_value = {"episodes": [ep("E1", 1, ["ja-JP", "fr-FR"]), ep("E2", 2, ["ja-JP"])]}
        self.watcher.add_series("S", "Apothecary", mode="all_missing")
        self.watcher.check_series("S")
        self.assertEqual(self._enqueued_ids(), ["E1"])

    @patch("crunchyroll.api.get_series")
    def test_fallback_enabled_keeps_old_behaviour(self, get_series):
        self.cfg["audio_fallback"] = True
        get_series.return_value = {"episodes": [ep("E1", 1, ["ja-JP"])]}
        self.watcher.add_series("S", "Apothecary", mode="latest_only")
        self.assertEqual(self._known("S"), {"E1"})

    def test_empty_version_list_uses_episode_lookup(self):
        bare = SimpleNamespace(id="E9", audio_locale="ja-JP", versions=[])
        info = SimpleNamespace(episode_metadata=SimpleNamespace(
            audio_locale="ja-JP", versions=[DubVersion(audio_locale="fr-FR")]))
        with patch("crunchyroll.api.get_episode_info", return_value=info) as lookup:
            self.assertTrue(_audio_ready(MagicMock(), bare, "fr-FR", self.cfg))
            lookup.assert_called_once()

    def test_all_requested_languages_must_exist(self):
        e = ep("E1", 1, ["ja-JP", "fr-FR"])
        self.assertTrue(_audio_ready(None, e, "fr-FR", self.cfg))
        self.assertFalse(_audio_ready(None, e, "fr-FR,de-DE", self.cfg))
        self.assertTrue(_audio_ready(None, e, "all", self.cfg))


if __name__ == "__main__":
    unittest.main()
