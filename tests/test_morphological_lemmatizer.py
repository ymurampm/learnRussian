import unittest
import json
import os
import sys

# Ensure server module is importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))

from server import (
    generate_russian_lemma_candidates,
    find_dictionary_entry_by_lemma,
    resolve_missing_vocabulary,
    extract_headwords,
    get_vocab_db,
    get_lesson_token_map
)

class TestMorphologicalLemmatizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocab_db = get_vocab_db()
        cls.token_map = get_lesson_token_map()

    def test_extract_headwords(self):
        self.assertEqual(extract_headwords("стоять/по-"), ["стоять", "постоять"])
        self.assertEqual(extract_headwords("начинать/начать"), ["начинать", "начать"])
        self.assertEqual(extract_headwords("репетировать/от-"), ["репетировать", "отрепетировать"])
        self.assertEqual(extract_headwords("состоять (i) (из +g)"), ["состоять"])
        self.assertEqual(extract_headwords("сын (pl сыновья)"), ["сын", "сыновья"])

    def test_generate_lemma_candidates_past_tense(self):
        # -ял -> -ять
        cands_стоял = generate_russian_lemma_candidates("стоял")
        self.assertIn("стоять", cands_стоял)

        # -ал -> -ать, -ять
        cands_начали = generate_russian_lemma_candidates("начали")
        self.assertIn("начать", cands_начали)

        cands_звучали = generate_russian_lemma_candidates("звучали")
        self.assertIn("звучать", cands_звучали)

        # Prefixed motion verbs with -шёл
        cands_пришёл = generate_russian_lemma_candidates("пришёл")
        self.assertIn("прийти", cands_пришёл)

        cands_вышли = generate_russian_lemma_candidates("вышли")
        self.assertIn("выйти", cands_вышли)

    def test_stoyal_resolution_never_returns_placeholder(self):
        """
        REGRESSION TEST FOR USER REPORT:
        Clicking 'стоял' must NEVER produce '«стоял»（文脈重要語彙）'.
        It must resolve to the real dictionary entry with Japanese meaning.
        """
        res = resolve_missing_vocabulary("стоял")
        self.assertIsNotNone(res)
        self.assertNotEqual(res.get("meaning"), "«стоял»（文脈重要語彙）")
        self.assertNotIn("（文脈重要語彙）", res.get("meaning", ""))
        self.assertTrue(
            "立っ" in res.get("meaning", "") or "置かれ" in res.get("meaning", ""),
            f"Expected Japanese meaning for стоять, got: {res.get('meaning')}"
        )
        self.assertEqual(res.get("base"), "стоять")
        # Check that declension table is present and non-empty
        self.assertTrue(len(res.get("declension_table", [])) > 1)

    def test_prishyol_resolution(self):
        res = resolve_missing_vocabulary("пришёл")
        self.assertIsNotNone(res)
        self.assertNotIn("（文脈重要語彙）", res.get("meaning", ""))
        self.assertTrue(
            "来" in res.get("meaning", "") or "到着" in res.get("meaning", ""),
            f"Expected Japanese meaning for прийти, got: {res.get('meaning')}"
        )

    def test_nastroychik_registered_in_dictionary(self):
        res = resolve_missing_vocabulary("настройщик")
        self.assertIsNotNone(res)
        self.assertIn("調律師", res.get("meaning", ""))
        self.assertEqual(res.get("pos"), "男性名詞 (活動体)")

    def test_unseen_inflected_words_resolution(self):
        """
        Verify that first-time novel inflected words automatically resolve
        without requiring ad-hoc hardcoded if-statements.
        """
        test_cases = [
            ("погулял", "散歩"),
            ("потеряли", "失う"),
            ("написали", "書く"),
            ("увидели", "見"),
            ("открыли", "開")
        ]
        for word, expected_snippet in test_cases:
            res = resolve_missing_vocabulary(word)
            self.assertIsNotNone(res, f"Failed to resolve {word}")
            meaning = res.get("meaning", "")
            self.assertNotIn("（文脈重要語彙）", meaning, f"Got dummy placeholder for {word}")
            self.assertIn(
                expected_snippet,
                meaning,
                f"Word {word} resolved to meaning '{meaning}' which lacked '{expected_snippet}'"
            )

    def test_days_21_to_30_evening_tokens_complete(self):
        """
        Verify that all evening audio paragraphs for Days 21-30
        have non-empty tokens and key_vocab.
        """
        cat_path = os.path.join(ROOT_DIR, "data", "curriculum_catalog.json")
        with open(cat_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for day in catalog:
            d_idx = day.get("day_index")
            if d_idx and 21 <= d_idx <= 30:
                eve = day.get("sessions", {}).get("evening", {})
                paras = eve.get("audio_paragraphs", [])
                self.assertTrue(len(paras) >= 2, f"Day {d_idx} evening missing paragraphs")
                for p_idx, p in enumerate(paras):
                    tokens = p.get("tokens", [])
                    key_vocab = p.get("key_vocab", [])
                    self.assertTrue(
                        len(tokens) >= 5,
                        f"Day {d_idx} evening P{p_idx+1} has too few tokens ({len(tokens)})"
                    )
                    self.assertTrue(
                        len(key_vocab) >= 3,
                        f"Day {d_idx} evening P{p_idx+1} has too few key_vocab ({len(key_vocab)})"
                    )
                    # Every token must have word and base
                    for t in tokens:
                        self.assertTrue(bool(t.get("word")), f"Empty token word in Day {d_idx}")
                        self.assertTrue(bool(t.get("base")), f"Empty token base in Day {d_idx}")

if __name__ == "__main__":
    unittest.main()
