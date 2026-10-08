import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import resolve_missing_vocabulary, generate_smart_table

class TestShortParticiplesAndTokens(unittest.TestCase):
    def test_napisana_not_feminine_noun(self):
        res = resolve_missing_vocabulary("написана")
        self.assertIsNotNone(res)
        self.assertNotIn("女性名詞", res.get("pos", ""))
        self.assertTrue("受動" in res.get("pos", "") or "短語尾" in res.get("pos", ""))
        
        tbl = res.get("declension_table", [])
        self.assertTrue(len(tbl) > 0)
        self.assertIn("性・数", tbl[0][0])
        case_names = [row[0] for row in tbl[1:]]
        self.assertIn("男性単数 (он)", case_names[0])
        self.assertIn("女性単数 (она)", case_names[1])
        self.assertNotIn("生格", case_names)
        self.assertNotIn("与格", case_names)

    def test_prodany_short_participle(self):
        tbl, note = generate_smart_table("проданы", "受動過去短語尾")
        self.assertTrue(len(tbl) > 0)
        self.assertIn("性・数", tbl[0][0])
        self.assertIn("短語尾", note)
        self.assertNotIn("女性名詞の格変化", note)

    def test_day16_tokens_have_role_and_tag(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        with open(os.path.join(root, "data", "curriculum_catalog.json"), encoding="utf-8") as f:
            cat = json.load(f)
        d16 = None
        for d in cat:
            if d.get("day_index") == 16:
                d16 = d
                break
        self.assertIsNotNone(d16)
        m_tokens = d16["sessions"]["morning"]["hero_sentence"]["tokens"]
        for t in m_tokens:
            self.assertIn("word", t)
            self.assertIn("role", t)
            self.assertIn("tag", t)
            self.assertIn("base", t)
            self.assertTrue(len(t["role"]) > 0, f"Empty role for {t['word']}")
            self.assertTrue(len(t["base"]) > 0, f"Empty base for {t['word']}")

if __name__ == "__main__":
    unittest.main()
