import urllib.request, urllib.parse, json, re

def test_all_curriculum():
    with open('data/curriculum_catalog.json', 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    tested_queries = set()
    errors = []
    total_tokens = 0

    for day in catalog:
        for s_name, s_data in day.get('sessions', {}).items():
            paras = s_data.get('paragraphs', []) + s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', [])
            hero = s_data.get('hero_sentence')
            if hero:
                paras.append(hero)
            for p in paras:
                for t in p.get('tokens', []):
                    total_tokens += 1
                    w = t.get('word', '').strip()
                    b = t.get('base', '').strip()
                    clean_w = re.sub(r'[«»„“".,!?;:()—]', '', w).strip().lower()
                    clean_b = re.sub(r'[«»„“".,!?;:()—]', '', b).strip().lower()
                    if not clean_w:
                        continue
                    key = (clean_w, clean_b)
                    if key in tested_queries:
                        continue
                    tested_queries.add(key)

                    q_str = urllib.parse.urlencode({'q': clean_w, 'base': clean_b})
                    url = f"http://127.0.0.1:8085/api/vocabulary?{q_str}"
                    req = urllib.request.Request(url)
                    try:
                        with urllib.request.urlopen(req, timeout=3) as resp:
                            res = json.loads(resp.read().decode('utf-8'))
                    except Exception as e:
                        errors.append(f"HTTP Error for {key}: {e}")
                        continue

                    if not res:
                        errors.append(f"Empty result for {key}")
                        continue

                    entry = res[0]
                    tbl = entry.get('declension_table')
                    pos = entry.get('pos', '')
                    
                    if tbl and isinstance(tbl, list) and len(tbl) > 1:
                        # Check 1: Phonotactic validity
                        for r_idx, row in enumerate(tbl):
                            if isinstance(row, list):
                                for c_idx, cell in enumerate(row):
                                    if isinstance(cell, str):
                                        # In any word, double ы (ыы) or illegal vowel after ы (excluding legitimate prefix вы-)
                                        words_in_cell = re.findall(r'[а-яёА-ЯЁ]+', cell)
                                        for w_cell in words_in_cell:
                                            w_low = w_cell.lower()
                                            # Prefix вы- can precede roots starting with vowels (выучить, выиграть, выяснить)
                                            if w_low.startswith(('выуч', 'выигр', 'выясн', 'выход')):
                                                continue
                                            if re.search(r'ы[аёиоуыэюя]', w_low):
                                                errors.append(f"Illegal vowel after ы in {key} cell ({r_idx},{c_idx}): '{cell}' (word: '{w_cell}')")
                                            # True nouns cannot have ending -ые (nouns end in -ы or -и in plural)
                                            if '名詞' in pos and '代名詞' not in pos and '形容詞' not in pos and '形動詞' not in pos:
                                                if w_low.endswith('ые') and w_low not in ('вы', 'мы'):
                                                    errors.append(f"Noun {key} has illegal 'ые' ending in word '{w_cell}' (cell: '{cell}')")
                                            # Systematic morphemic integrity: Infinitive -ть cannot be followed directly by non-grammatical consonant suffixes
                                            if re.search(r'ть(?!(?:ся|сь|те|тесь|ма|мой|ме|му|ми)\b)[бвгджзклмнпрстфхцчшщ]', w_low):
                                                errors.append(f"Illegal morphemic concatenation (-ть + consonant) in word '{w_cell}' (cell: '{cell}')")
                    
                    # Check 2: Verbs cannot have 6-case tables (格 as header), Nouns cannot have 人称 as header
                    if tbl and isinstance(tbl, list) and len(tbl) > 1 and isinstance(tbl[0], list):
                        hdr0 = str(tbl[0][0])
                        if any(n in pos for n in ('名詞', '代名詞')) and '動詞' not in pos:
                            if '人称' in hdr0:
                                errors.append(f"Noun {key} (pos={pos}) has verb conjugation table (header='{hdr0}')")

    print(f"Audited {len(tested_queries)} unique token queries across {total_tokens} total tokens.")
    with open('scratch/declension_test_errors.json', 'w', encoding='utf-8') as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    if errors:
        print(f"FAILED with {len(errors)} errors. Saved to scratch/declension_test_errors.json")
        return False
    else:
        print("ALL TOKENS PASSED GRAMMAR AND PHONOTACTIC AUDIT!")
        return True

if __name__ == '__main__':
    success = test_all_curriculum()
    if not success:
        exit(1)
