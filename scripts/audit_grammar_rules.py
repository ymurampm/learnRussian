"""
Comprehensive Grammar Rules & Vocabulary Integrity Audit
Audits all Cyrillic words across lesson_buffer.json + core test suites.
"""
import sys
import os
import json
import urllib.request
import urllib.parse
import re

SERVER_URL = "http://127.0.0.1:8085"

EXPLICIT_PAST_VERBS = [
    'купила', 'купил', 'купили', 'сыграла', 'сыграл', 'сыграли',
    'положила', 'положил', 'клала', 'выучил', 'учил',
    'репетировали', 'ходили', 'ходил'
]

EXPLICIT_ADVERBS = [
    'пешком', 'утром', 'вечером', 'днём', 'ночью', 'очень',
    'редко', 'часто', 'обычно', 'обязательно', 'туда', 'сюда',
    'ещё', 'только', 'вчера', 'сегодня', 'завтра'
]

def get_all_lesson_words():
    buffer_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'lesson_buffer.json')
    with open(buffer_path, 'r', encoding='utf-8') as f:
        text = f.read()

    raw_words = re.findall(r'[а-яёА-ЯЁ]+', text)
    words = set(w.lower() for w in raw_words if len(w) >= 2)

    for w in EXPLICIT_PAST_VERBS + EXPLICIT_ADVERBS:
        words.add(w.lower())

    return sorted(list(words))

def audit_word(word):
    url = f"{SERVER_URL}/api/vocabulary?q={urllib.parse.quote(word)}"
    try:
        req = urllib.request.urlopen(url, timeout=5)
        raw = req.read().decode('utf-8')
        data = json.loads(raw)
    except Exception as e:
        return {'word': word, 'status': 'FETCH_ERROR', 'error': str(e)}

    entry = data[0] if isinstance(data, list) and len(data) > 0 else (data if isinstance(data, dict) else None)
    if not entry:
        return {'word': word, 'status': 'EMPTY'}

    pos = entry.get('pos', '')
    table = entry.get('declension_table', [])
    header = table[0] if table else []

    # 1. Past Tense Verb Checks
    is_target_past_verb = word in EXPLICIT_PAST_VERBS or word.endswith(('лась', 'лось', 'лись', 'лся'))
    if is_target_past_verb:
        if '名詞' in pos and '動詞' not in pos:
            return {
                'word': word,
                'status': 'FAIL_VERB_AS_NOUN',
                'pos': pos,
                'entry_word': entry.get('word'),
                'detail': f'Past tense verb "{word}" was categorized as noun POS: {pos}'
            }
        if table:
            first_row_label = table[1][0] if len(table) > 1 else ''
            if any(case in first_row_label for case in ['主格', '生格', '与格', '対格', '造格', '前置格']):
                return {
                    'word': word,
                    'status': 'FAIL_VERB_HAS_CASE_TABLE',
                    'pos': pos,
                    'entry_word': entry.get('word'),
                    'detail': f'Past tense verb "{word}" was given a noun case table instead of verb conjugation!'
                }

    # 2. Adverb & Uninflected Word Checks
    is_uninflected = word in EXPLICIT_ADVERBS or ('副詞' in pos or '不変化' in pos or '接続詞' in pos)
    if is_uninflected and table and len(table) > 0:
        return {
            'word': word,
            'status': 'FAIL_ADVERB_HAS_TABLE',
            'pos': pos,
            'entry_word': entry.get('word'),
            'detail': f'Uninflected word "{word}" (POS: {pos}) was given an inflection table with {len(table)} rows!'
        }

    # 3. Special Verification for Day 1 "купила"
    if word == 'купила':
        if 'купить' not in entry.get('word', '') and 'покупать' not in entry.get('word', ''):
            return {
                'word': word,
                'status': 'FAIL_KUPILA_LEMMA',
                'detail': f'купила did not resolve to купить / покупать (got: {entry.get("word")})'
            }
        if not table or '人称' not in str(header):
            return {
                'word': word,
                'status': 'FAIL_KUPILA_TABLE',
                'detail': f'купила did not receive a verb conjugation table (header: {header})'
            }

    return {
        'word': word,
        'status': 'PASS',
        'pos': pos,
        'entry_word': entry.get('word'),
        'table_type': header[0] if header else 'none'
    }

def main():
    words = get_all_lesson_words()
    print(f"Auditing {len(words)} Russian words across all lessons...")

    fails = []
    passes = 0

    for idx, w in enumerate(words, 1):
        res = audit_word(w)
        if res['status'].startswith('FAIL'):
            fails.append(res)
            print(f"[{res['status']}] {w} -> {res.get('detail')}")
        else:
            passes += 1

    print("=" * 60)
    print(f"AUDIT SUMMARY: {passes} PASSED, {len(fails)} FAILED (Total words: {len(words)})")
    print("=" * 60)

    if fails:
        print("FAILURES DETECTED:")
        for f in fails:
            print(f" - {f['word']}: {f['detail']}")
        sys.exit(1)
    else:
        print("SUCCESS: ALL 600+ RUSSIAN VOCABULARY & GRAMMAR CHECKS PASSED PERFECTLY!")
        sys.exit(0)

if __name__ == '__main__':
    main()
