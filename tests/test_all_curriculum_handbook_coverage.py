# -*- coding: utf-8 -*-
"""
Tanya Russian Trainer - 100% Curriculum to Handbook Coverage & Tag Safeguard Audit
Prevents regressions where curriculum sessions, quiz items, or paragraph links
point to non-existent grammar handbook chapters or fall back unexpectedly.
"""
import os
import sys
import json
import re
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class TestCurriculumHandbookCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT_DIR, 'data', 'grammar_handbook.json'), encoding='utf-8') as f:
            cls.handbook = json.load(f)
        with open(os.path.join(ROOT_DIR, 'data', 'curriculum_catalog.json'), encoding='utf-8') as f:
            cls.catalog = json.load(f)
        with open(os.path.join(ROOT_DIR, 'data', 'lesson_buffer.json'), encoding='utf-8') as f:
            cls.buffer = json.load(f)
        
        # Collect valid chapter IDs
        cls.valid_chapters = set()
        for cat in cls.handbook.get('categories', []):
            for ch in cat.get('chapters', []):
                cls.valid_chapters.add(ch.get('tag_id'))

        # Parse ALIAS_MAP from js/handbook.js to ensure Python audit matches JS engine 100%
        with open(os.path.join(ROOT_DIR, 'js', 'handbook.js'), encoding='utf-8') as f:
            js_text = f.read()

        m_alias = re.search(r'const ALIAS_MAP = \{([^}]+)\};', js_text, re.DOTALL)
        cls.alias_map = {}
        if m_alias:
            for line in m_alias.group(1).splitlines():
                line = line.strip()
                if line.startswith('//') or not line:
                    continue
                m_pair = re.search(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", line)
                if m_pair:
                    cls.alias_map[m_pair.group(1).lower()] = m_pair.group(2)

        # Parse tagMap from js/quiz_engine.js
        with open(os.path.join(ROOT_DIR, 'js', 'quiz_engine.js'), encoding='utf-8') as f:
            quiz_js = f.read()
        m_quiz_map = re.search(r'const tagMap = \{([^}]+)\};', quiz_js, re.DOTALL)
        cls.quiz_tag_map = {}
        if m_quiz_map:
            for line in m_quiz_map.group(1).splitlines():
                line = line.strip()
                if line.startswith('//') or not line:
                    continue
                m_pair = re.search(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", line)
                if m_pair:
                    cls.quiz_tag_map[m_pair.group(1)] = m_pair.group(2)

    def resolve_tag(self, raw_tag):
        if not raw_tag:
            return None
        tag = raw_tag.strip().lower()

        # Direct
        for c in self.valid_chapters:
            if c.lower() == tag:
                return c

        # Alias
        if tag in self.alias_map:
            target = self.alias_map[tag]
            if target in self.valid_chapters:
                return target

        # Heuristics (matches js/handbook.js)
        if (tag.includes if hasattr(tag, 'includes') else ('indef' in tag) or ('不定代名詞' in tag)):
            if 'pronoun.indefinite' in self.valid_chapters:
                return 'pronoun.indefinite'
        if ('neg' in tag) or ('否定代名詞' in tag) or ('否定副詞' in tag):
            if 'pronoun.negative' in self.valid_chapters:
                return 'pronoun.negative'
        if ('impersonal' in tag) or ('無人称' in tag):
            if 'syntax.impersonal' in self.valid_chapters:
                return 'syntax.impersonal'
        if (('perfective' in tag) or ('完了体' in tag) or (' св' in tag) or tag.endswith('_sv')) and \
           (('gerund' in tag) or ('adverbial' in tag) or ('副動詞' in tag) or ('деепричастие' in tag)):
            if 'gerund.perfective' in self.valid_chapters:
                return 'gerund.perfective'
        if (('imperfective' in tag) or ('不完了体' in tag) or (' нсв' in tag) or tag.endswith('_nsv')) and \
           (('gerund' in tag) or ('adverbial' in tag) or ('副動詞' in tag) or ('деепричастие' in tag)):
            if 'gerund.imperfective' in self.valid_chapters:
                return 'gerund.imperfective'
        if any(k in tag for k in ['gerund', 'деепричастие', '副動詞', 'adverbial']):
            if 'gerund.verbal_adverb' in self.valid_chapters:
                return 'gerund.verbal_adverb'
        if 'passive' in tag or '受動' in tag:
            if 'participle.passive' in self.valid_chapters:
                return 'participle.passive'
        if 'participle' in tag or '形動詞' in tag:
            if 'participle.active' in self.valid_chapters:
                return 'participle.active'
        if 'motion_prefixed' in tag or '接頭辞' in tag:
            if 'verb.motion_prefixed' in self.valid_chapters:
                return 'verb.motion_prefixed'
        if 'motion' in tag or '移動動詞' in tag:
            if 'verb.motion_uni' in self.valid_chapters:
                return 'verb.motion_uni'
        if 'aspect' in tag or '体' in tag:
            if 'verb.aspect_nsv' in self.valid_chapters:
                return 'verb.aspect_nsv'
        if 'government' in tag or '格支配' in tag:
            if 'verb.government' in self.valid_chapters:
                return 'verb.government'
        if 'fleeting' in tag or '出没音' in tag:
            if 'noun.irregular_fleeting' in self.valid_chapters:
                return 'noun.irregular_fleeting'
        if 'soft_sign' in tag or '-ь' in tag:
            if 'noun.soft_sign' in self.valid_chapters:
                return 'noun.soft_sign'

        m = re.search(r'case\.(nom|gen|dat|acc|ins|prp)', tag)
        if m:
            c_tag = f"case.{m.group(1)}"
            if c_tag in self.valid_chapters:
                return c_tag

        for c in self.valid_chapters:
            if tag.startswith(c) or c.startswith(tag):
                return c

        return None

    def test_all_catalog_tags_resolve_to_valid_handbook_chapters(self):
        """Verify that every single quiz item, session related tag, and paragraph tag in catalog resolves."""
        unresolved = []
        total_checked = 0

        for d in self.catalog:
            d_idx = d.get('day_index')
            for s_name, s_data in d.get('sessions', {}).items():
                rgt = s_data.get('related_grammar_tag')
                if rgt:
                    total_checked += 1
                    res = self.resolve_tag(rgt)
                    if not res:
                        unresolved.append(f"Day {d_idx} [{s_name}] related_grammar_tag '{rgt}' does not resolve to handbook.")

                for q in s_data.get('quiz_items', []):
                    qt = q.get('tag') or q.get('grammar_tag')
                    if qt:
                        total_checked += 1
                        res = self.resolve_tag(qt)
                        if not res:
                            unresolved.append(f"Day {d_idx} [{s_name}] quiz {q.get('id')} tag '{qt}' does not resolve to handbook.")

                for p in s_data.get('paragraphs', []) + s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []):
                    pt = p.get('related_tag')
                    if pt:
                        total_checked += 1
                        res = self.resolve_tag(pt)
                        if not res:
                            unresolved.append(f"Day {d_idx} [{s_name}] paragraph related_tag '{pt}' does not resolve to handbook.")

        self.assertGreater(total_checked, 100, "Should have audited over 100 grammar tag touchpoints.")
        self.assertEqual(len(unresolved), 0, f"Found {len(unresolved)} unresolved handbook tags:\n" + "\n".join(unresolved))

    def test_all_lesson_buffer_tags_resolve_to_valid_handbook_chapters(self):
        """Verify that every single tag in lesson_buffer.json resolves to a valid handbook chapter."""
        unresolved = []
        total_checked = 0

        for d in self.buffer:
            d_idx = d.get('day_index')
            for s_name, s_data in d.get('sessions', {}).items():
                rgt = s_data.get('related_grammar_tag')
                if rgt:
                    total_checked += 1
                    res = self.resolve_tag(rgt)
                    if not res:
                        unresolved.append(f"Buffer Day {d_idx} [{s_name}] related_grammar_tag '{rgt}' does not resolve to handbook.")

                for q in s_data.get('quiz_items', []):
                    qt = q.get('tag') or q.get('grammar_tag')
                    if qt:
                        total_checked += 1
                        res = self.resolve_tag(qt)
                        if not res:
                            unresolved.append(f"Buffer Day {d_idx} [{s_name}] quiz {q.get('id')} tag '{qt}' does not resolve to handbook.")

                for p in s_data.get('paragraphs', []) + s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []):
                    pt = p.get('related_tag')
                    if pt:
                        total_checked += 1
                        res = self.resolve_tag(pt)
                        if not res:
                            unresolved.append(f"Buffer Day {d_idx} [{s_name}] paragraph related_tag '{pt}' does not resolve to handbook.")

        self.assertGreater(total_checked, 100, "Should have audited over 100 buffer grammar tag touchpoints.")
        self.assertEqual(len(unresolved), 0, f"Found {len(unresolved)} unresolved handbook tags in buffer:\n" + "\n".join(unresolved))

    def test_quiz_engine_tag_map_covers_all_handbook_chapters(self):
        """Ensure that every handbook chapter has a human-readable title in quiz_engine.js tagMap."""
        missing = []
        for ch in self.valid_chapters:
            if ch not in self.quiz_tag_map:
                missing.append(f"Chapter '{ch}' missing human-readable label in quiz_engine.js tagMap")
        self.assertEqual(len(missing), 0, "\n".join(missing))

if __name__ == '__main__':
    unittest.main()
