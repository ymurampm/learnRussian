# -*- coding: utf-8 -*-
"""
Tanya Russian Trainer - Comprehensive 100% Curriculum Token Grammar Audit
Tests EVERY SINGLE token across all 20 days and all 4 daily sessions.
Guarantees zero POS mismatch, zero participle-noun confusion, and zero whack-a-mole regression.
"""
import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import server
from server import resolve_missing_vocabulary, get_lesson_token_map, get_vocab_db

COMPARATIVE_LEMMA_MAP = {
    'лучше': ('хороший', 'хорошо'),
    'хуже': ('плохой', 'плохо'),
    'больше': ('большой', 'много'),
    'меньше': ('маленький', 'мало'),
    'выше': ('высокий', 'высоко'),
    'ниже': ('низкий', 'низко'),
    'легче': ('лёгкий', 'легко'),
    'тяжелее': ('тяжёлый', 'тяжело'),
    'проще': ('простой', 'просто'),
    'сложнее': ('сложный', 'сложно'),
    'чище': ('чистый', 'чисто'),
    'тише': ('тихий', 'тихо'),
    'громче': ('громкий', 'громко'),
    'глубже': ('глубокий', 'глубоко'),
    'шире': ('широкий', 'широко'),
    'уже': ('узкий', 'узко', 'уже', 'уж'),
    'ближе': ('близкий', 'близко'),
    'дальше': ('далёкий', 'далеко'),
    'дольше': ('долгий', 'долго'),
    'раньше': ('ранний', 'рано'),
    'позже': ('поздний', 'поздно'),
    'дороже': ('дорогой', 'дорого'),
    'дешевле': ('дешёвый', 'дёшево'),
    'старше': ('старый', 'старо'),
    'моложе': ('молодой', 'молодо'),
    'быстрее': ('быстрый', 'быстро'),
    'красивее': ('красивый', 'красиво')
}

class TestCurriculumTokenGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server._LESSON_TOKEN_CACHE = None
        cls.root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        with open(os.path.join(cls.root, 'data', 'curriculum_catalog.json'), encoding='utf-8') as f:
            cls.catalog = json.load(f)
        with open(os.path.join(cls.root, 'data', 'lesson_buffer.json'), encoding='utf-8') as f:
            cls.buffer = json.load(f)

    def test_all_catalog_tokens_grammatical_integrity(self):
        """Audit 100% of tokens in curriculum_catalog.json (hero, paragraphs, mutations)."""
        violations = []
        total_checked = 0

        for d in self.catalog:
            day_idx = d.get('day_index')
            for s_name, s_data in d.get('sessions', {}).items():
                tokens = []
                hero = s_data.get('hero_sentence')
                if hero:
                    tokens.extend(hero.get('tokens', []))
                for p in s_data.get('paragraphs', []) + s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []):
                    tokens.extend(p.get('tokens', []))
                for m in s_data.get('interactive_mutations', []):
                    tokens.extend(m.get('tokens', []))

                for t in tokens:
                    total_checked += 1
                    raw_w = t.get('word', '').strip()
                    w = raw_w.replace('.', '').replace(',', '').replace('«', '').replace('»', '').replace('!', '').replace('?', '').lower()
                    b = t.get('base', '').strip().replace('.', '').replace(',', '').replace('«', '').replace('»', '').replace('!', '').replace('?', '').lower()
                    role = t.get('role', '') or t.get('grammar', '')
                    tag = t.get('tag', '')

                    if not w:
                        continue

                    # 1. Resolve vocabulary
                    res = resolve_missing_vocabulary(w)
                    if not res and b:
                        res = resolve_missing_vocabulary(b)

                    if not res:
                        violations.append(f"Day {day_idx} [{s_name}] '{w}': Could not resolve vocabulary entry.")
                        continue

                    pos = res.get('pos', '')
                    tbl = res.get('declension_table', [])

                    # 2. Participles MUST NOT be classified as pure nouns or given noun 6-case tables
                    if ('participle' in tag or '受動' in role or '形動詞' in role) and '名詞' in pos and '形動詞' not in pos:
                        violations.append(f"Day {day_idx} [{s_name}] '{w}': Participle wrongly classified as noun: {pos}")

                    # 3. Pure uninflected words (adv, prep, conj, particle, interj) MUST NOT have declension tables
                    # (Note: Gerunds have base verbs with conjugations, comparatives have base adjectives with declensions, and pronouns have pronoun tables)
                    is_uninflected = (any(x in tag for x in ['prep', 'conj', 'particle', 'interj']) or \
                                      (any(x in role for x in ['前置詞', '接続詞', '助詞', '不変化']) and '代名詞' not in role) or \
                                      (('副詞' in role or 'adv' in tag) and not ('副動詞' in role or 'gerund' in tag or 'adverbial' in tag))) and \
                                     not any(x in role for x in ['副動詞', '形動詞', '代名詞', '比較級']) and \
                                     'comparative' not in tag
                    if is_uninflected and tbl and len(tbl) > 1:
                        h0 = str(tbl[0][0])
                        if '格' in h0 or '人称' in h0:
                            violations.append(f"Day {day_idx} [{s_name}] '{w}': Uninflected word has inflection table '{h0}'")

                    # 4. Systematic Comparative & Irregular Lemma Integrity
                    if w in COMPARATIVE_LEMMA_MAP:
                        valid_bases = COMPARATIVE_LEMMA_MAP[w]
                        if b and not any(v in b for v in valid_bases):
                            violations.append(f"Day {day_idx} [{s_name}] Comparative '{w}' has invalid base lemma '{b}' (must resolve to one of {valid_bases})")

        self.assertGreater(total_checked, 500, "Should have inspected at least 500 tokens.")
        self.assertEqual(len(violations), 0, f"Found {len(violations)} grammatical violations in curriculum_catalog.json:\n" + "\n".join(violations))

    def test_all_lesson_buffer_tokens_grammatical_integrity(self):
        """Audit 100% of tokens in lesson_buffer.json."""
        violations = []
        total_checked = 0

        for d in self.buffer:
            day_idx = d.get('day_index')
            for s_name, s_data in d.get('sessions', {}).items():
                tokens = []
                hero = s_data.get('hero_sentence')
                if hero:
                    tokens.extend(hero.get('tokens', []))
                for p in s_data.get('paragraphs', []) + s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []):
                    tokens.extend(p.get('tokens', []))
                for m in s_data.get('interactive_mutations', []):
                    tokens.extend(m.get('tokens', []))

                for t in tokens:
                    total_checked += 1
                    raw_w = t.get('word', '').strip()
                    w = raw_w.replace('.', '').replace(',', '').replace('«', '').replace('»', '').replace('!', '').replace('?', '').lower()
                    b = t.get('base', '').strip().replace('.', '').replace(',', '').replace('«', '').replace('»', '').replace('!', '').replace('?', '').lower()
                    role = t.get('role', '') or t.get('grammar', '')
                    tag = t.get('tag', '')

                    if not w:
                        continue

                    res = resolve_missing_vocabulary(w)
                    if not res and b:
                        res = resolve_missing_vocabulary(b)

                    if not res:
                        violations.append(f"Buffer Day {day_idx} [{s_name}] '{w}': Could not resolve vocabulary entry.")
                        continue

                    pos = res.get('pos', '')
                    tbl = res.get('declension_table', [])

                    if ('participle' in tag or '受動' in role or '形動詞' in role) and '名詞' in pos and '形動詞' not in pos:
                        violations.append(f"Buffer Day {day_idx} [{s_name}] '{w}': Participle wrongly classified as noun: {pos}")

                    # 3. Pure uninflected words (adv, prep, conj, particle, interj) MUST NOT have declension tables
                    # (Note: Gerunds have base verbs with conjugations, comparatives have base adjectives with declensions, and pronouns have pronoun tables)
                    is_uninflected = (any(x in tag for x in ['prep', 'conj', 'particle', 'interj']) or \
                                      (any(x in role for x in ['前置詞', '接続詞', '助詞', '不変化']) and '代名詞' not in role) or \
                                      (('副詞' in role or 'adv' in tag) and not ('副動詞' in role or 'gerund' in tag or 'adverbial' in tag))) and \
                                     not any(x in role for x in ['副動詞', '形動詞', '代名詞', '比較級']) and \
                                     'comparative' not in tag
                    if is_uninflected and tbl and len(tbl) > 1:
                        h0 = str(tbl[0][0])
                        if '格' in h0 or '人称' in h0:
                            violations.append(f"Buffer Day {day_idx} [{s_name}] '{w}': Uninflected word has inflection table '{h0}'")

                    # 4. Systematic Comparative & Irregular Lemma Integrity
                    if w in COMPARATIVE_LEMMA_MAP:
                        valid_bases = COMPARATIVE_LEMMA_MAP[w]
                        if b and not any(v in b for v in valid_bases):
                            violations.append(f"Buffer Day {day_idx} [{s_name}] Comparative '{w}' has invalid base lemma '{b}' (must resolve to one of {valid_bases})")

        self.assertGreater(total_checked, 500, "Should have inspected at least 500 buffer tokens.")
        self.assertEqual(len(violations), 0, f"Found {len(violations)} violations in lesson_buffer.json:\n" + "\n".join(violations))

    def test_all_morning_and_noon_hero_sentences_have_complete_tokens(self):
        """Permanent Invariant Gate: 100% of morning and noon sessions must have non-empty tokens."""
        for dataset_name, dataset in [("curriculum_catalog", self.catalog), ("lesson_buffer", self.buffer)]:
            for d in dataset:
                day_idx = d.get('day_index')
                sessions = d.get('sessions', {})
                for s_name in ['morning', 'noon']:
                    sess = sessions.get(s_name)
                    if not sess:
                        continue
                    hero = sess.get('hero_sentence')
                    self.assertIsNotNone(
                        hero,
                        f"[{dataset_name}] Day {day_idx} [{s_name}] must have hero_sentence for Phase 1/2"
                    )
                    ru = hero.get('ru', '').strip()
                    ja = hero.get('ja', '').strip()
                    tokens = hero.get('tokens')
                    self.assertTrue(
                        len(ru) > 0,
                        f"[{dataset_name}] Day {day_idx} [{s_name}] hero_sentence has empty 'ru'"
                    )
                    self.assertTrue(
                        len(ja) > 0,
                        f"[{dataset_name}] Day {day_idx} [{s_name}] hero_sentence has empty 'ja'"
                    )
                    self.assertIsInstance(
                        tokens, list,
                        f"[{dataset_name}] Day {day_idx} [{s_name}] hero_sentence 'tokens' must be a list"
                    )
                    self.assertGreater(
                        len(tokens), 0,
                        f"[{dataset_name}] Day {day_idx} [{s_name}] hero_sentence has 0 tokens! Phase 1/2 would be blank!"
                    )
                    for t_idx, t in enumerate(tokens):
                        self.assertTrue(
                            t.get('word'),
                            f"[{dataset_name}] Day {day_idx} [{s_name}] token #{t_idx+1} missing word"
                        )
                        self.assertTrue(
                            t.get('base'),
                            f"[{dataset_name}] Day {day_idx} [{s_name}] token #{t_idx+1} missing base"
                        )
                        self.assertTrue(
                            t.get('role') or t.get('grammar'),
                            f"[{dataset_name}] Day {day_idx} [{s_name}] token #{t_idx+1} missing role/grammar"
                        )
                        self.assertTrue(
                            t.get('tag'),
                            f"[{dataset_name}] Day {day_idx} [{s_name}] token #{t_idx+1} missing tag"
                        )

if __name__ == '__main__':
    unittest.main()

