"""
Curriculum & Quiz Solvability Validator
Tanya Russian Learning App (Moscow Conservatory Edition)

Provides automated verification of all lesson sessions and quiz questions.
Ensures zero unsolvable, ambiguous, or malformed questions can enter the system.
Can be executed as:
1. CLI validator: python scripts/validate_curriculum.py
2. Imported module in batch_generator, daily_batch, and server
3. Unit test suite
"""

import os
import re
import sys
import json
from collections import Counter

# Standard Russian label cleaning logic (mirrors js/quiz_engine.js:cleanRu)
def clean_ru_label(text):
    if not text:
        return ''
    # Only remove parentheses containing Japanese characters (hiragana, katakana, kanji)
    def repl(m):
        inner = m.group(1)
        if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', inner):
            return ''
        return f' ({inner.strip()})'
    return re.sub(r'\s*\((.*?)\)', repl, text).strip()

class HandbookTagResolver:
    """
    Validates that any grammar tag in curriculum resolves to an existing handbook chapter.
    Mandatory quality standard: NEVER link to grammar handbook topics that do not exist.
    """
    _instance = None

    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.root_dir = root_dir
        self.valid_chapters = set()
        self.alias_map = {}
        self.quiz_tag_map = {}
        self._load()

    def _load(self):
        handbook_p = os.path.join(self.root_dir, 'data', 'grammar_handbook.json')
        if os.path.exists(handbook_p):
            with open(handbook_p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for cat in data.get('categories', []):
                for ch in cat.get('chapters', []):
                    if ch.get('tag_id'):
                        self.valid_chapters.add(ch['tag_id'])

        js_handbook_p = os.path.join(self.root_dir, 'js', 'handbook.js')
        if os.path.exists(js_handbook_p):
            with open(js_handbook_p, 'r', encoding='utf-8') as f:
                js_text = f.read()
            m_alias = re.search(r'const ALIAS_MAP = \{([^}]+)\};', js_text, re.DOTALL)
            if m_alias:
                for line in m_alias.group(1).splitlines():
                    line = line.strip()
                    if line.startswith('//') or not line:
                        continue
                    m_pair = re.search(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", line)
                    if m_pair:
                        self.alias_map[m_pair.group(1).lower()] = m_pair.group(2)

        js_quiz_p = os.path.join(self.root_dir, 'js', 'quiz_engine.js')
        if os.path.exists(js_quiz_p):
            with open(js_quiz_p, 'r', encoding='utf-8') as f:
                quiz_js = f.read()
            m_quiz_map = re.search(r'const tagMap = \{([^}]+)\};', quiz_js, re.DOTALL)
            if m_quiz_map:
                for line in m_quiz_map.group(1).splitlines():
                    line = line.strip()
                    if line.startswith('//') or not line:
                        continue
                    m_pair = re.search(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", line)
                    if m_pair:
                        self.quiz_tag_map[m_pair.group(1)] = m_pair.group(2)

    @classmethod
    def get_instance(cls, root_dir=None):
        if cls._instance is None:
            cls._instance = cls(root_dir)
        return cls._instance

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

        # Heuristics (mirrors js/handbook.js)
        if ('collective' in tag) or ('集合数詞' in tag) or ('оба' in tag) or ('обе' in tag):
            if 'numeral.collective' in self.valid_chapters:
                return 'numeral.collective'
        if ('subordinate' in tag) or ('従属節' in tag) or ('чтобы' in tag) or ('хотя' in tag):
            if 'syntax.subordinate' in self.valid_chapters:
                return 'syntax.subordinate'
        if ('indef' in tag) or ('不定代名詞' in tag):
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

def validate_quiz_item(q, loc=""):
    """
    Validates a single quiz item for solvability and correctness.
    Returns: (is_valid: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []
    
    qid = q.get('id', '<no_id>')
    qtype = q.get('type')
    prefix = f"[{loc} id={qid} type={qtype}]"

    if not qtype:
        errors.append(f"{prefix} Missing question 'type'")
        return False, errors, warnings

    valid_types = {
        'single_choice', 'fill_in_blank', 'grammaticality',
        'sentence_builder', 'error_spotter', 'matching', 'listening_check'
    }
    if qtype not in valid_types:
        errors.append(f"{prefix} Unknown question type '{qtype}'")
        return False, errors, warnings

    # General metadata & Pedagogical Explanation Integrity
    exp = q.get('explanation', '').strip()
    if not exp or len(exp) < 15:
        errors.append(f"{prefix} Missing or inadequate explanation (must be detailed pedagogical text >= 15 chars, got '{exp}')")
    else:
        stem = q.get('ru_stem') or q.get('ru') or ''
        # 1. Impersonal modal sentences with dative logical subject (e.g. солисту нельзя волноваться)
        if re.search(r'\b(нельзя|нужно|надо|можно|пора|кажется|хочется)\b', stem):
            if any(k in stem for k in ('солист', 'пианист', 'студент', 'музыкант', 'мне', 'нам', 'вам', 'ей', 'ему')) and '与格' not in exp:
                errors.append(f"{prefix} Impersonal modal sentence tests dative subject, but explanation fails to explain why 与格 is used!")

        qtag = q.get('tag', '')
        # 2. Passive participle questions must explain passive structure
        if 'participle.passive' in qtag and not any(k in exp for k in ('受動', '短語尾', '過去分詞', '造格', '一致')):
            errors.append(f"{prefix} Passive participle question explanation must explain passive construction (受動/短語尾/造格)!")

        # 3. Conditional mood questions must explain past tense + бы rule
        if 'syntax.conditional' in qtag and not any(k in exp for k in ('仮定', '条件', '過去形', 'бы')):
            errors.append(f"{prefix} Conditional mood question explanation must explain past tense + бы rule!")

        # 4. Verbal adverb questions must explain subject agreement rule
        if 'gerund.verbal_adverb' in qtag and not any(k in exp for k in ('主語', '一致', '動作主')):
            errors.append(f"{prefix} Verbal adverb question explanation must explain subject agreement rule (主語一致)!")

    # 1. Matching
    if qtype == 'matching':
        pairs = q.get('pairs', [])
        if not isinstance(pairs, list) or len(pairs) < 2:
            errors.append(f"{prefix} matching requires pairs array with at least 2 items (got {len(pairs)})")
        else:
            left_cleaned = []
            right_cleaned = []
            for idx, p in enumerate(pairs):
                l_raw = p.get('left', '')
                r_raw = p.get('right', '')
                if not l_raw or not r_raw:
                    errors.append(f"{prefix} pair #{idx+1} has empty left ('{l_raw}') or right ('{r_raw}')")
                
                l_c = clean_ru_label(l_raw)
                r_c = clean_ru_label(r_raw)
                if not l_c:
                    errors.append(f"{prefix} pair #{idx+1} left label became empty after UI cleaning: '{l_raw}'")
                if not r_c:
                    errors.append(f"{prefix} pair #{idx+1} right label became empty after UI cleaning: '{r_raw}'")
                
                left_cleaned.append(l_c)
                right_cleaned.append(r_c)

            # Check duplicate card labels
            left_dups = [item for item, count in Counter(left_cleaned).items() if count > 1]
            if left_dups:
                errors.append(f"{prefix} UNSOLVABLE MATCHING: duplicate left cards {left_dups}. Raw lefts: {[p.get('left') for p in pairs]}")

            right_dups = [item for item, count in Counter(right_cleaned).items() if count > 1]
            if right_dups:
                errors.append(f"{prefix} UNSOLVABLE MATCHING: duplicate right cards {right_dups}. Raw rights: {[p.get('right') for p in pairs]}")

            # Check grammatical ambiguity (Multiple subjects sharing the same agreement category
            # with multiple verbs of that same category, e.g., two feminine subjects and two feminine verbs)
            fem_pronouns = [l for l in left_cleaned if any(k in l.lower() for k in ['она', 'женщина', 'женский'])]
            fem_verbs = [r for r in right_cleaned if r.endswith('ла бы') or (r.endswith('ла') and not r.endswith('ли'))]
            if len(fem_pronouns) > 1 and len(fem_verbs) > 1:
                errors.append(
                    f"{prefix} UNSOLVABLE MATCHING AMBIGUITY: Multiple feminine subjects {fem_pronouns} "
                    f"with multiple feminine verbs {fem_verbs}. In Russian past/conditional, feminine forms are grammatically "
                    f"interchangeable across 1st/3rd person. Use distinct categories (он, она, оно, мы) to ensure 1-to-1 solvability."
                )

            masc_pronouns = [l for l in left_cleaned if any(k in l.lower() for k in ['он', 'мужчина', 'мужской'])]
            masc_verbs = [r for r in right_cleaned if r.endswith('л бы') or (r.endswith('л') and not r.endswith('ла') and not r.endswith('ли') and not r.endswith('ло'))]
            if len(masc_pronouns) > 1 and len(masc_verbs) > 1:
                errors.append(
                    f"{prefix} UNSOLVABLE MATCHING AMBIGUITY: Multiple masculine subjects {masc_pronouns} "
                    f"with multiple masculine verbs {masc_verbs}. Use distinct categories to ensure 1-to-1 solvability."
                )

            neut_pronouns = [l for l in left_cleaned if any(k in l.lower() for k in ['оно', 'средний'])]
            neut_verbs = [r for r in right_cleaned if r.endswith('ло бы') or r.endswith('ло')]
            if len(neut_pronouns) > 1 and len(neut_verbs) > 1:
                errors.append(
                    f"{prefix} UNSOLVABLE MATCHING AMBIGUITY: Multiple neuter subjects {neut_pronouns} "
                    f"with multiple neuter verbs {neut_verbs}."
                )

            plur_pronouns = [l for l in left_cleaned if any(k in l.lower() for k in ['мы', 'вы', 'они', 'множественное'])]
            plur_past_verbs = [r for r in right_cleaned if r.endswith('ли бы') or r.endswith('ли')]
            if len(plur_pronouns) > 1 and len(plur_past_verbs) > 1:
                errors.append(
                    f"{prefix} UNSOLVABLE MATCHING AMBIGUITY: Multiple plural subjects {plur_pronouns} "
                    f"with multiple plural past verbs {plur_past_verbs}."
                )

    # 2. Single Choice & Listening Check
    elif qtype in ('single_choice', 'listening_check'):
        opts = q.get('options', [])
        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"{prefix} options must have at least 2 items (got {len(opts)})")
        else:
            opt_dups = [item for item, count in Counter(opts).items() if count > 1]
            if opt_dups:
                errors.append(f"{prefix} UNSOLVABLE: duplicate choices in options: {opt_dups}")

        c_idx = q.get('correct_index')
        if c_idx is None:
            c_idx = q.get('answer_index')
        if c_idx is None:
            errors.append(f"{prefix} Missing 'correct_index' / 'answer_index'")
        elif not isinstance(c_idx, int) or c_idx < 0 or c_idx >= len(opts):
            errors.append(f"{prefix} correct_index {c_idx} is out of bounds (options len: {len(opts)})")

        if qtype == 'listening_check' and not q.get('audio_text'):
            errors.append(f"{prefix} listening_check missing 'audio_text'")

        # Detect missing Russian stem/context in single_choice
        prompt = q.get('prompt') or ''
        stem = q.get('ru_stem') or q.get('ru') or ''
        if ('空所' in prompt or '空欄' in prompt) and ('___' not in stem and '＿' not in stem):
            errors.append(f"{prefix} Prompt mentions '空所'/'空欄' but ru_stem has no '___' blank placeholder")

        has_cyrillic_opts = any(re.search(r'[\u0400-\u04ff]', str(opt)) for opt in opts)
        if has_cyrillic_opts and not q.get('ru_stem') and not q.get('ru'):
            errors.append(f"{prefix} Russian options provided but question has no 'ru_stem' or 'ru' context")

    # 3. Fill in the Blank
    elif qtype == 'fill_in_blank':
        opts = q.get('options', [])
        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"{prefix} options must have at least 2 items (got {len(opts)})")
        else:
            opt_dups = [item for item, count in Counter(opts).items() if count > 1]
            if opt_dups:
                errors.append(f"{prefix} UNSOLVABLE: duplicate choices in options: {opt_dups}")

        c_idx = q.get('correct_index')
        if c_idx is None:
            c_idx = q.get('answer_index')
        if c_idx is None:
            errors.append(f"{prefix} Missing 'correct_index' / 'answer_index'")
        elif not isinstance(c_idx, int) or c_idx < 0 or c_idx >= len(opts):
            errors.append(f"{prefix} correct_index {c_idx} is out of bounds (options len: {len(opts)})")

        stem = q.get('ru_stem') or q.get('ru') or ''
        if not stem:
            errors.append(f"{prefix} fill_in_blank requires 'ru_stem' with Russian sentence")
        elif '___' not in stem and '＿' not in stem:
            errors.append(f"{prefix} fill_in_blank missing blank placeholder '___' in ru_stem (got: '{stem}')")

    # 4. Grammaticality (True / False)
    elif qtype == 'grammaticality':
        if not q.get('ru'):
            errors.append(f"{prefix} grammaticality missing sentence 'ru'")
        is_corr = q.get('is_correct')
        if is_corr is None or not isinstance(is_corr, bool):
            errors.append(f"{prefix} grammaticality missing boolean 'is_correct' (got {is_corr})")

    # 5. Sentence Builder
    elif qtype == 'sentence_builder':
        tokens = q.get('tokens', [])
        if not isinstance(tokens, list) or len(tokens) < 2:
            errors.append(f"{prefix} sentence_builder requires tokens list with >= 2 words (got {len(tokens)})")
        else:
            # If explicit bank is provided, verify it contains all tokens
            bank = q.get('bank') or q.get('options')
            if bank:
                token_counts = Counter(tokens)
                bank_counts = Counter(bank)
                missing = [t for t, cnt in token_counts.items() if bank_counts[t] < cnt]
                if missing:
                    errors.append(f"{prefix} UNSOLVABLE: bank missing required tokens: {missing}")

    # 6. Error Spotter
    elif qtype == 'error_spotter':
        sentence_tokens = q.get('sentence_tokens', [])
        if not isinstance(sentence_tokens, list) or len(sentence_tokens) < 2:
            errors.append(f"{prefix} error_spotter requires sentence_tokens list with >= 2 tokens")
        else:
            err_count = sum(1 for t in sentence_tokens if t.get('has_error'))
            if err_count == 0:
                errors.append(f"{prefix} UNSOLVABLE: no token has 'has_error: true'")
            elif err_count == len(sentence_tokens):
                errors.append(f"{prefix} UNSOLVABLE: all tokens have 'has_error: true'")

    return len(errors) == 0, errors, warnings

def validate_day_data(day, day_idx=None):
    """
    Validates an entire day object including all sessions and quiz items.
    Returns: (is_valid: bool, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    if day_idx is None:
        day_idx = day.get('day_index', '?')

    sessions = day.get('sessions', {})
    if not isinstance(sessions, dict):
        errors.append(f"[Day {day_idx}] 'sessions' must be a dictionary")
        return False, errors, warnings

    resolver = HandbookTagResolver.get_instance()

    # Handbook tag coverage validation across all sessions
    for s_name, sess in sessions.items():
        if not isinstance(sess, dict):
            continue
        rgt = sess.get('related_grammar_tag')
        if rgt:
            res = resolver.resolve_tag(rgt)
            if not res:
                errors.append(f"[Day {day_idx} {s_name}] related_grammar_tag '{rgt}' does NOT resolve to any grammar handbook chapter! (Constraint: No missing handbook chapters)")

        for q_idx, q in enumerate(sess.get('quiz_items', [])):
            qt = q.get('tag') or q.get('grammar_tag')
            if qt:
                res = resolver.resolve_tag(qt)
                if not res:
                    errors.append(f"[Day {day_idx} {s_name} Q{q_idx+1}] quiz tag '{qt}' does NOT resolve to any grammar handbook chapter! (Constraint: No missing handbook chapters)")

        paragraphs = sess.get('paragraphs', []) + sess.get('audio_paragraphs', []) + sess.get('audio_sentences', [])
        for p in paragraphs:
            if isinstance(p, dict):
                pt = p.get('related_tag')
                if pt:
                    res = resolver.resolve_tag(pt)
                    if not res:
                        errors.append(f"[Day {day_idx} {s_name}] paragraph related_tag '{pt}' does NOT resolve to any grammar handbook chapter! (Constraint: No missing handbook chapters)")

    for s_name in ['morning', 'noon']:
        sess = sessions.get(s_name)
        if not sess:
            warnings.append(f"[Day {day_idx}] Missing '{s_name}' session")
            continue
        
        # Validate hero sentence (MANDATORY for 4-phase sessions: morning and noon)
        hero = sess.get('hero_sentence')
        if not hero:
            errors.append(f"[Day {day_idx} {s_name}] Missing required 'hero_sentence' for 4-phase session!")
        else:
            ru = str(hero.get('ru', '')).strip()
            ja = str(hero.get('ja', '')).strip()
            tokens = hero.get('tokens')

            if not ru:
                errors.append(f"[Day {day_idx} {s_name}] hero_sentence missing 'ru'")
            elif not re.search(r'[\u0400-\u04ff]', ru):
                errors.append(f"[Day {day_idx} {s_name}] hero_sentence 'ru' contains no Cyrillic characters: {ru}")

            if not ja:
                errors.append(f"[Day {day_idx} {s_name}] hero_sentence missing 'ja'")

            if not tokens or not isinstance(tokens, list) or len(tokens) == 0:
                errors.append(f"[Day {day_idx} {s_name}] hero_sentence missing 'tokens' (empty or not a list). Phase 1/2 will render empty without tokens!")
            else:
                for t_idx, tok in enumerate(tokens):
                    t_word = tok.get('word', '').strip()
                    t_base = tok.get('base', '').strip()
                    t_role = tok.get('role', '') or tok.get('grammar', '')
                    t_tag = tok.get('tag', '')

                    if not t_word:
                        errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} missing 'word'")
                    elif not re.search(r'[\u0400-\u04ff]', t_word):
                        errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} '{t_word}' contains no Cyrillic characters")

                    if not t_base:
                        errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} '{t_word}' missing 'base'")

                    if not t_role:
                        errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} '{t_word}' missing 'role' / 'grammar'")

                    if not t_tag:
                        errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} '{t_word}' missing 'tag'")
                    else:
                        tag_res = resolver.resolve_tag(t_tag)
                        if not tag_res:
                            errors.append(f"[Day {day_idx} {s_name}] hero token #{t_idx+1} '{t_word}' tag '{t_tag}' does NOT resolve to any grammar handbook chapter!")

        # Validate all quiz items
        quiz_items = sess.get('quiz_items', [])
        for q_idx, q in enumerate(quiz_items):
            loc = f"Day {day_idx} ({s_name}) Q{q_idx+1}"
            valid, q_errs, q_warns = validate_quiz_item(q, loc)
            errors.extend(q_errs)
            warnings.extend(q_warns)

    # Validate evening session (Listening Bath paragraphs must have tokens and key_vocab)
    eve_sess = sessions.get('evening')
    if eve_sess:
        paras = eve_sess.get('audio_paragraphs', []) or eve_sess.get('paragraphs', [])
        if not paras:
            errors.append(f"[Day {day_idx} evening] Missing paragraphs / audio_paragraphs in evening session!")
        else:
            for p_idx, p in enumerate(paras):
                p_ru = p.get('ru', '').strip()
                p_ja = p.get('ja', '').strip()
                p_tokens = p.get('tokens', [])
                p_kv = p.get('key_vocab', [])

                if not p_ru:
                    errors.append(f"[Day {day_idx} evening P{p_idx+1}] missing 'ru'")
                if not p_ja:
                    errors.append(f"[Day {day_idx} evening P{p_idx+1}] missing 'ja'")

                if not p_tokens or not isinstance(p_tokens, list):
                    errors.append(f"[Day {day_idx} evening P{p_idx+1}] missing 'tokens' (required for interactive word lookup cards)!")
                else:
                    for t_idx, tok in enumerate(p_tokens):
                        t_word = tok.get('word', '').strip()
                        t_base = tok.get('base', '').strip()
                        t_role = tok.get('role', '') or tok.get('grammar', '')
                        t_tag = tok.get('tag', '')
                        if not t_word:
                            errors.append(f"[Day {day_idx} evening P{p_idx+1}] token #{t_idx+1} missing 'word'")
                        if not t_base:
                            errors.append(f"[Day {day_idx} evening P{p_idx+1}] token #{t_idx+1} '{t_word}' missing 'base'")
                        if not t_role:
                            errors.append(f"[Day {day_idx} evening P{p_idx+1}] token #{t_idx+1} '{t_word}' missing 'role'")
                        if t_tag:
                            tag_res = resolver.resolve_tag(t_tag)
                            if not tag_res:
                                errors.append(f"[Day {day_idx} evening P{p_idx+1}] token #{t_idx+1} '{t_word}' tag '{t_tag}' does NOT resolve to any grammar handbook chapter!")

                if not p_kv or not isinstance(p_kv, list):
                    errors.append(f"[Day {day_idx} evening P{p_idx+1}] missing 'key_vocab'!")
                else:
                    for kv_idx, kv in enumerate(p_kv):
                        kv_word = kv.get('word', '').strip()
                        kv_meaning = kv.get('meaning', '').strip()
                        if not kv_word:
                            errors.append(f"[Day {day_idx} evening P{p_idx+1}] key_vocab #{kv_idx+1} missing 'word'")
                        if not kv_meaning:
                            errors.append(f"[Day {day_idx} evening P{p_idx+1}] key_vocab #{kv_idx+1} '{kv_word}' missing 'meaning'")

    return len(errors) == 0, errors, warnings

def validate_catalog_list(days):
    """
    Validates a list of day objects.
    Returns: (is_valid: bool, summary: dict)
    """
    all_errors = []
    all_warnings = []
    total_questions = 0

    for day in days:
        day_idx = day.get('day_index', '?')
        valid, errs, warns = validate_day_data(day, day_idx)
        all_errors.extend(errs)
        all_warnings.extend(warns)

        for sess in day.get('sessions', {}).values():
            total_questions += len(sess.get('quiz_items', []))

    summary = {
        "total_days": len(days),
        "total_questions": total_questions,
        "total_errors": len(all_errors),
        "total_warnings": len(all_warnings),
        "errors": all_errors,
        "warnings": all_warnings,
        "is_valid": len(all_errors) == 0
    }
    return summary["is_valid"], summary

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(base_dir, "data", "curriculum_catalog.json")
    buffer_path = os.path.join(base_dir, "data", "lesson_buffer.json")

    has_error = False

    # Check handbook coverage of quiz_engine.js tagMap
    resolver = HandbookTagResolver.get_instance(base_dir)
    missing_labels = []
    for ch in resolver.valid_chapters:
        if ch not in resolver.quiz_tag_map:
            missing_labels.append(f"Chapter '{ch}' missing human-readable label in quiz_engine.js tagMap")
    if missing_labels:
        has_error = True
        print("❌ HANDBOOK INTEGRITY ERROR: Missing labels in quiz_engine.js:")
        for m in missing_labels:
            print(f"  • {m}")
    else:
        print(f"✅ HANDBOOK COVERAGE GATE: All {len(resolver.valid_chapters)} handbook chapters have verified titles in quiz_engine.js.")

    for name, p in [("Curriculum Catalog", catalog_path), ("Lesson Buffer", buffer_path)]:
        print(f"\n=======================================================")
        print(f"VALIDATING: {name} ({p})")
        print(f"=======================================================")
        if not os.path.exists(p):
            print(f"[ERROR] File not found: {p}")
            has_error = True
            continue

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        days = data if isinstance(data, list) else data.get('days', [])
        valid, summary = validate_catalog_list(days)

        print(f"Days: {summary['total_days']} | Questions: {summary['total_questions']}")
        print(f"Errors: {summary['total_errors']} | Warnings: {summary['total_warnings']}")

        if summary['errors']:
            has_error = True
            print("\n❌ SOLVABILITY & INTEGRITY ERRORS DETECTED:")
            for e in summary['errors']:
                print(f"  • {e}")
        else:
            print("✅ 100% SOLVABLE & VALID (0 Errors)")

        if summary['warnings']:
            print(f"\n⚠️ Warnings ({len(summary['warnings'])}):")
            for w in summary['warnings'][:5]:
                print(f"  • {w}")
            if len(summary['warnings']) > 5:
                print(f"  ... and {len(summary['warnings']) - 5} more")

    print("\n=======================================================")
    if has_error:
        print("❌ VALIDATION FAILED: Some questions are broken, unsolvable, or have invalid handbook tags.")
        return 1
    else:
        print("🎉 ALL CURRICULUM QUESTIONS PASSED SOLVABILITY & HANDBOOK INTEGRITY VALIDATION!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
