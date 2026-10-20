# -*- coding: utf-8 -*-
"""
Unit tests for Russian Verb Conjugation Table Verification
Verifies that:
1. Perfective motion verbs (пойти, поехать, прийти) and their past forms (пошла, пошёл, пришёл)
   strictly display '単純未来' (Simple Future) and NEVER '現在形' (Present Tense).
2. The conjugations of пойти are 100% genuine Russian (пойду, пойдёшь, пойдёт, пойдём, пойдёте, пойдут)
   and NEVER corrupted algorithmic pseudo-forms (пойю, пойишь, пою, поишь).
3. Mixed and consonant-alternating verbs (хотеть, бежать, видеть, любить, писать, мочь)
   generate accurate Russian conjugations.
"""

import unittest
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from server import generate_smart_table, RUSSIAN_CORE_ENTRIES, IRREGULAR_GRAMMAR_REGISTRY

class TestVerbConjugations(unittest.TestCase):
    def test_poyti_conjugation_accuracy(self):
        """пойти is perfective (СВ): must have 単純未来, true stems, and past forms."""
        tbl, note = generate_smart_table('пойти', '完了体動詞')
        self.assertTrue(len(tbl) >= 7, "Table must have header + 6 person rows")
        
        header = tbl[0]
        self.assertIn('単純未来', header[1], "Perfective verb non-past must be labeled '単純未来'")
        self.assertNotIn('現在形', header[1], "Perfective verb must NEVER have '現在形' in header")

        # Extract 6 persons: я, ты, он/она, мы, вы, они
        conjugations = {row[0]: row[1].replace('́', '') for row in tbl[1:7]}
        self.assertEqual(conjugations.get('я'), 'пойду')
        self.assertEqual(conjugations.get('ты'), 'пойдёшь')
        self.assertEqual(conjugations.get('он/она'), 'пойдёт')
        self.assertEqual(conjugations.get('мы'), 'пойдём')
        self.assertEqual(conjugations.get('вы'), 'пойдёте')
        self.assertEqual(conjugations.get('они'), 'пойдут')

        # Strictly verify no corrupted/bogus forms exist
        for row in tbl:
            for cell in row:
                self.assertNotIn('пойю', cell)
                self.assertNotIn('пойишь', cell)
                self.assertNotIn('пойит', cell)
                self.assertNotIn('пойят', cell)

    def test_poshla_past_form_resolution(self):
        """пошла (past feminine) must resolve to пойти (単純未来) with proper past forms."""
        tbl, note = generate_smart_table('пошла', '動詞')
        self.assertTrue(len(tbl) >= 7)
        header = tbl[0]
        self.assertIn('単純未来', header[1])
        
        # Check core entries
        self.assertIn('пошла', RUSSIAN_CORE_ENTRIES)
        core_poshla = RUSSIAN_CORE_ENTRIES['пошла']
        self.assertEqual(core_poshla['word'], 'пойти')
        poshla_tbl = core_poshla['declension_table']
        self.assertIn('単純未来', poshla_tbl[0][1])
        self.assertIn('пойдёшь', poshla_tbl[2][1])
        self.assertIn('пошла́', poshla_tbl[3][2])

    def test_poshel_and_poshli_core_entries(self):
        """пошёл and пошли must be properly defined in RUSSIAN_CORE_ENTRIES and IRREGULAR_ALERTS."""
        for w in ['пошёл', 'пошли']:
            self.assertIn(w, RUSSIAN_CORE_ENTRIES, f"{w} must be in RUSSIAN_CORE_ENTRIES")
            self.assertIn(w, IRREGULAR_GRAMMAR_REGISTRY, f"{w} must be in IRREGULAR_GRAMMAR_REGISTRY")
            tbl = RUSSIAN_CORE_ENTRIES[w]['declension_table']
            self.assertIn('単純未来', tbl[0][1])

    def test_poekhat_and_priyti_conjugations(self):
        """поехать and прийти must have correct simple future and past conjugations."""
        tbl_poekhat, _ = generate_smart_table('поехать', '動詞')
        self.assertIn('単純未来', tbl_poekhat[0][1])
        self.assertEqual(tbl_poekhat[1][1].replace('́', ''), 'поеду')
        self.assertEqual(tbl_poekhat[2][1].replace('́', ''), 'поедешь')

        tbl_priyti, _ = generate_smart_table('прийти', '動詞')
        self.assertIn('単純未来', tbl_priyti[0][1])
        self.assertEqual(tbl_priyti[1][1].replace('́', ''), 'приду')
        self.assertEqual(tbl_priyti[2][1].replace('́', ''), 'придёшь')
        self.assertIn('пришёл', tbl_priyti[1][2])

    def test_mixed_and_alternating_verbs(self):
        """хотеть, бежать, видеть, любить, писать, мочь must conjugate correctly."""
        # хотеть (mixed)
        tbl_xotet, _ = generate_smart_table('хотеть', '動詞')
        forms_x = {r[0]: r[1].replace('́', '') for r in tbl_xotet[1:7]}
        self.assertEqual(forms_x.get('я'), 'хочу')
        self.assertEqual(forms_x.get('ты'), 'хочешь')
        self.assertEqual(forms_x.get('мы'), 'хотим')
        self.assertEqual(forms_x.get('они'), 'хотят')

        # бежать (mixed)
        tbl_begat, _ = generate_smart_table('бежать', '動詞')
        forms_b = {r[0]: r[1].replace('́', '') for r in tbl_begat[1:7]}
        self.assertEqual(forms_b.get('я'), 'бегу')
        self.assertEqual(forms_b.get('ты'), 'бежишь')
        self.assertEqual(forms_b.get('они'), 'бегут')

        # видеть (д -> ж in 1st person)
        tbl_videt, _ = generate_smart_table('видеть', '動詞')
        forms_v = {r[0]: r[1].replace('́', '') for r in tbl_videt[1:7]}
        self.assertEqual(forms_v.get('я'), 'вижу')
        self.assertEqual(forms_v.get('ты'), 'видишь')

        # любить (labial л insertion)
        tbl_lyubit, _ = generate_smart_table('любить', '動詞')
        forms_l = {r[0]: r[1].replace('́', '') for r in tbl_lyubit[1:7]}
        self.assertEqual(forms_l.get('я'), 'люблю')
        self.assertEqual(forms_l.get('ты'), 'любишь')

        # писать (с -> ш in all persons)
        tbl_pisat, _ = generate_smart_table('писать', '動詞')
        forms_p = {r[0]: r[1].replace('́', '') for r in tbl_pisat[1:7]}
        self.assertEqual(forms_p.get('я'), 'пишу')
        self.assertEqual(forms_p.get('ты'), 'пишешь')

        # мочь (г -> ж alternation, past мог)
        tbl_moch, _ = generate_smart_table('мочь', '動詞')
        forms_m = {r[0]: r[1].replace('́', '') for r in tbl_moch[1:7]}
        self.assertEqual(forms_m.get('я'), 'могу')
        self.assertEqual(forms_m.get('ты'), 'можешь')
        self.assertEqual(forms_m.get('они'), 'могут')
        self.assertIn('мог', tbl_moch[1][2])

if __name__ == '__main__':
    unittest.main()
