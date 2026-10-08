# -*- coding: utf-8 -*-
"""
tests/test_participle_declensions.py
Permanently protects participle declension tables and handbook integrity from regressions.
"""

import json
import unittest
import os
import sys
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import get_vocab_db, generate_smart_table, resolve_missing_vocabulary

class TestParticipleDeclensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('data/vocabulary_db.json', 'r', encoding='utf-8') as f:
            cls.vocab_db = json.load(f)
        with open('data/grammar_handbook.json', 'r', encoding='utf-8') as f:
            cls.handbook = json.load(f)

    def test_handbook_has_active_and_passive_participle_chapters(self):
        tags = []
        for cat in self.handbook.get('categories', []):
            for ch in cat.get('chapters', []):
                tags.append(ch.get('tag_id'))
        self.assertIn('participle.active', tags, "Handbook must contain participle.active")
        self.assertIn('participle.passive', tags, "Handbook must contain participle.passive")

    def test_active_participles_declension_tables_have_six_cases(self):
        active_participles = ['звучащий', 'звучащая', 'смолкающий', 'смолкающие', 'парящий', 'парящая', 'уставший', 'уставшего']
        expected_cases = ['主格', '生格', '与格', '対格', '造格', '前置格']
        
        for word in active_participles:
            self.assertIn(word, self.vocab_db, f"Word '{word}' must exist in vocabulary_db.json")
            entry = self.vocab_db[word]
            tbl = entry.get('declension_table')
            self.assertIsNotNone(tbl, f"Word '{word}' must have declension_table")
            self.assertIsInstance(tbl, list, f"declension_table must be a 2D list")
            
            headers = tbl[0]
            self.assertEqual(headers[0], '格', f"Word '{word}' table header must start with '格'")
            
            rows = tbl[1:]
            self.assertEqual(len(rows), 6, f"Word '{word}' table must have exactly 6 rows (cases)")
            
            case_names = [r[0] for r in rows]
            self.assertEqual(case_names, expected_cases, f"Word '{word}' rows must match 6 cases exactly")
            
            # Ensure no person conjugations
            for r in rows:
                self.assertNotIn(r[0], ['я', 'ты', 'он / она / оно', 'мы', 'вы', 'они'], f"Word '{word}' must not have verb conjugation rows")

    def test_passive_long_participles_declension_tables(self):
        passive_participles = ['написанный', 'написанные']
        expected_cases = ['主格', '生格', '与格', '対格', '造格', '前置格']
        
        for word in passive_participles:
            self.assertIn(word, self.vocab_db, f"Word '{word}' must exist in vocabulary_db.json")
            entry = self.vocab_db[word]
            tbl = entry.get('declension_table')
            self.assertIsNotNone(tbl, f"Word '{word}' must have declension_table")
            
            rows = tbl[1:]
            self.assertEqual(len(rows), 6, f"Word '{word}' table must have 6 rows")
            case_names = [r[0] for r in rows]
            self.assertEqual(case_names, expected_cases)

    def test_short_passive_participles_structure(self):
        short_participles = ['написан', 'написана', 'продан', 'проданы']
        for word in short_participles:
            self.assertIn(word, self.vocab_db, f"Word '{word}' must exist in vocabulary_db.json")
            entry = self.vocab_db[word]
            tbl = entry.get('declension_table')
            self.assertIsNotNone(tbl, f"Word '{word}' must have declension_table")
            
            headers = tbl[0]
            self.assertIn('性・数', headers[0], f"Short participle '{word}' header must be 性・数")
            self.assertEqual(len(tbl[1:]), 4, f"Short participle '{word}' must have 4 rows")

    def test_server_api_returns_adjectival_table_for_participle_even_with_base_verb(self):
        try:
            url = 'http://127.0.0.1:8085/api/vocabulary?q=%D0%B7%D0%B2%D1%83%D1%87%D0%B0%D1%89%D0%B0%D1%8F&base=%D0%B7%D0%B2%D1%83%D1%87%D0%B0%D1%82%D1%8C'
            with urllib.request.urlopen(url, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode('utf-8'))
                self.assertIsInstance(data, list)
                self.assertTrue(len(data) > 0)
                item = data[0]
                self.assertIn('declension_table', item)
                tbl = item['declension_table']
                self.assertEqual(tbl[0][0], '格')
                self.assertEqual(len(tbl[1:]), 6)
                self.assertEqual(tbl[1][0], '主格')
        except urllib.error.URLError:
            # If server is not running on 8085 during test run, verify via resolve_missing_vocabulary
            res = resolve_missing_vocabulary('звучащая')
            self.assertIsNotNone(res)
            self.assertEqual(res['declension_table'][0][0], '格')
            self.assertEqual(len(res['declension_table'][1:]), 6)

if __name__ == '__main__':
    unittest.main()
