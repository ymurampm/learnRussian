# -*- coding: utf-8 -*-
"""
Test suite for TTS pipeline and fallback to Google Neural TTS.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import fetch_google_tts

class TestTTSPipeline(unittest.TestCase):
    def test_fetch_google_tts_basic(self):
        """Test that fetch_google_tts generates valid MP3 bytes for Russian words."""
        audio_data = fetch_google_tts("музыка", lang="ru")
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), 1000)
        # MPEG audio frame header starts with 0xFF
        self.assertEqual(audio_data[0], 0xFF)

    def test_fetch_google_tts_strips_accents_and_slashes(self):
        """Test accent removal and slash handling in Google TTS fetcher."""
        audio_data = fetch_google_tts("звучи́шь / звучать", lang="ru")
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), 2000)
        self.assertEqual(audio_data[0], 0xFF)

    def test_fetch_google_tts_long_sentence_chunking(self):
        """Test that long sentences exceeding 120 chars are chunked and concatenated properly."""
        long_sentence = (
            "Вчера вечером в Большом зале Московской консерватории состоялся потрясающий концерт, "
            "на котором исполнялись произведения Чайковского и Рахманинова."
        )
        audio_data = fetch_google_tts(long_sentence, lang="ru")
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), 10000)
        self.assertEqual(audio_data[0], 0xFF)

if __name__ == '__main__':
    unittest.main()
