"""
Unit Test Suite for Curriculum & Quiz Solvability
Ensures that all current and future questions generated in the app are strictly solvable,
unambiguous, and free of defects (preventing 'whack-a-mole' bugs).
"""

import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from validate_curriculum import (
    validate_quiz_item,
    validate_day_data,
    validate_catalog_list,
    clean_ru_label
)

class TestCurriculumSolvability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_path = os.path.join(BASE_DIR, "data", "curriculum_catalog.json")
        cls.buffer_path = os.path.join(BASE_DIR, "data", "lesson_buffer.json")

    def test_catalog_all_questions_solvable(self):
        """All questions in curriculum_catalog.json must be 100% solvable with 0 errors."""
        self.assertTrue(os.path.exists(self.catalog_path), "curriculum_catalog.json does not exist")
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            days = json.load(f)
        
        is_valid, summary = validate_catalog_list(days)
        self.assertTrue(
            is_valid,
            f"Curriculum catalog has unsolvable questions: {summary['errors']}"
        )
        self.assertEqual(len(summary['errors']), 0)
        self.assertGreater(summary['total_questions'], 0)

    def test_buffer_all_questions_solvable(self):
        """All questions in lesson_buffer.json must be 100% solvable with 0 errors."""
        self.assertTrue(os.path.exists(self.buffer_path), "lesson_buffer.json does not exist")
        with open(self.buffer_path, "r", encoding="utf-8") as f:
            days = json.load(f)

        is_valid, summary = validate_catalog_list(days)
        self.assertTrue(
            is_valid,
            f"Lesson buffer has unsolvable questions: {summary['errors']}"
        )
        self.assertEqual(len(summary['errors']), 0)
        self.assertGreater(summary['total_questions'], 0)

    def test_matching_duplicate_left_cards_caught(self):
        """Regression test for Day 13 bug: duplicate left cards after UI cleaning must be caught."""
        # Simulated bug where both cards clean to 'ты'
        broken_matching = {
            "id": "q_broken_matching",
            "type": "matching",
            "prompt": "マッチングテスト",
            "explanation": "解説",
            "pairs": [
                {"left": "ты", "right": "слушай"},
                {"left": "вы", "right": "слушайте"},
                {"left": "ты", "right": "играй"},
                {"left": "вы", "right": "играйте"}
            ]
        }
        is_valid, errors, _ = validate_quiz_item(broken_matching, "TestSession")
        self.assertFalse(is_valid, "Broken matching with duplicate 'ты' cards should fail validation")
        self.assertTrue(any("duplicate left cards" in e for e in errors))

    def test_matching_clean_ru_preserves_russian_disambiguation(self):
        """clean_ru_label must preserve Russian annotations like (слушать) while stripping Japanese."""
        # Russian in parentheses must remain
        self.assertEqual(clean_ru_label("ты (слушать)"), "ты (слушать)")
        self.assertEqual(clean_ru_label("я (женщина)"), "я (женщина)")
        # Japanese in parentheses must be stripped
        self.assertEqual(clean_ru_label("прийти (到着する)"), "прийти")
        self.assertEqual(clean_ru_label("читать (読む)"), "читать")

    def test_single_choice_duplicate_options_caught(self):
        """Options with duplicate text must be rejected."""
        broken_sc = {
            "id": "q_broken_sc",
            "type": "single_choice",
            "prompt": "選択肢テスト",
            "options": ["зал", "зал", "залу", "залом"],
            "correct_index": 0,
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_sc, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("duplicate choices" in e for e in errors))

    def test_single_choice_out_of_bounds_caught(self):
        """correct_index out of bounds must be rejected."""
        broken_sc = {
            "id": "q_broken_sc2",
            "type": "single_choice",
            "prompt": "選択肢テスト",
            "options": ["зал", "зала", "залу", "залом"],
            "correct_index": 4,  # Out of range (0-3)
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_sc, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("out of bounds" in e for e in errors))

    def test_sentence_builder_missing_tokens_caught(self):
        """Sentence builder bank missing a required token must be rejected."""
        broken_sb = {
            "id": "q_broken_sb",
            "type": "sentence_builder",
            "tokens": ["Я", "играю", "на", "рояле"],
            "bank": ["Я", "играю", "рояле"],  # Missing "на"
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_sb, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("missing required tokens" in e for e in errors))

    def test_error_spotter_no_error_token_caught(self):
        """Error spotter with no tokens flagged as error must be rejected."""
        broken_es = {
            "id": "q_broken_es",
            "type": "error_spotter",
            "sentence_tokens": [
                {"text": "Мы", "has_error": False},
                {"text": "играем", "has_error": False}
            ],
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_es, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("no token has 'has_error: true'" in e for e in errors))

    def test_matching_grammatical_ambiguity_caught(self):
        """Regression test for Day 14 bug: duplicate feminine subjects with duplicate feminine verbs must be caught."""
        ambiguous_matching = {
            "id": "q_ambiguous_matching",
            "type": "matching",
            "prompt": "主語の性・数に応じた正しい条件法ペアを結びつけましょう",
            "explanation": "解説",
            "pairs": [
                {"left": "он", "right": "сыграл бы"},
                {"left": "она", "right": "сыграла бы"},
                {"left": "мы", "right": "сыграли бы"},
                {"left": "я (женщина)", "right": "хотела бы"}
            ]
        }
        is_valid, errors, _ = validate_quiz_item(ambiguous_matching, "TestSession")
        self.assertFalse(is_valid, "Ambiguous matching with multiple feminine subjects and verbs must fail validation")
        self.assertTrue(any("UNSOLVABLE MATCHING AMBIGUITY" in e for e in errors))

    def test_fill_in_blank_missing_blank_caught(self):
        """fill_in_blank without '___' in ru_stem must be rejected."""
        broken_fib = {
            "id": "q_broken_fib",
            "type": "fill_in_blank",
            "ru_stem": "Оркестр играет концерт.",
            "options": ["зал", "зала", "залу", "залом"],
            "correct_index": 0,
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_fib, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("missing blank placeholder '___'" in e for e in errors))

    def test_single_choice_cyrillic_without_ru_stem_caught(self):
        """Regression test for Day 19 bug: single_choice with Cyrillic choices but no Russian sentence/stem must be rejected."""
        broken_sc = {
            "id": "q_broken_sc_no_ru",
            "type": "single_choice",
            "prompt": "「私には時間が必要だ」の空所に入る正しい主語（与格代名詞）を選んでください",
            "options": ["Мне", "Я", "Меня", "Мной"],
            "correct_index": 0,
            "explanation": "解説"
        }
        is_valid, errors, _ = validate_quiz_item(broken_sc, "TestSession")
        self.assertFalse(is_valid)
        self.assertTrue(any("Prompt mentions '空所'/'空欄' but ru_stem has no '___'" in e or "has no 'ru_stem'" in e for e in errors))

if __name__ == "__main__":
    unittest.main()

