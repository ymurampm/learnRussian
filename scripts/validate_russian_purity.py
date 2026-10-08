# -*- coding: utf-8 -*-
"""
Linguistic Purity Linter for Russian Training App.
Ensures Russian content fields have 0 Japanese (CJK) characters,
0 untranslated English words, and 0 corrupting Latin homoglyphs in sentences.
"""

import json
import os
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Pattern for CJK characters (Hiragana, Katakana, CJK Unified Ideographs)
CJK_REGEX = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')

# Pattern for Katakana-Cyrillic Chimera tokens (accidental IME mix like роヤль, Юсуクэ, Наム, замыスレ)
CHIMERA_CYRILLIC_KATAKANA = re.compile(r'([а-яёА-ЯЁ]+[ァ-ンヴヵヶ]+[а-яёА-ЯЁァ-ンヴヵヶ]*|[ァ-ンヴヵヶ]+[а-яёА-ЯЁ]+[а-яёА-ЯЁァ-ンヴヵヶ]*)')

# Permitted Roman numerals, brand names and musical abbreviations in sentences
PERMITTED_LATIN_TOKENS = {
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI',
    'Op', 'op', 'D', 'BWV', 'KV', 'p', 'pp', 'ppp', 'f', 'ff', 'fff', 'mf', 'mp', 'sfz',
    'Steinway', 'Yamaha', 'Kawai', 'Bösendorfer', 'Bechstein', 'N', 'No'
}

# Permitted dictionary grammar tags in headword/raw_word fields (e.g. (+inst), (m), etc.)
PERMITTED_GRAMMAR_TAGS = {
    'm', 'f', 'n', 'pl', 'sg', 'i', 'p', 'adj', 'adv', 'num', 'prep', 'conj', 'part', 'interj',
    'inst', 'gen', 'dat', 'acc', 'prep', 'loc', 'inf', 'a', 'g', 'd', 'or', 'pr', 'no', 'o', 'indecl', 'nom', 'of', 'person'
}

def check_string_purity(val, path_str, is_headword=False):
    issues = []
    
    # 1. CJK Detection - ABSOLUTELY ZERO TOLERANCE across all pure Russian fields
    cjk_matches = CJK_REGEX.findall(val)
    if cjk_matches:
        issues.append({
            'type': 'CJK_CONTAMINATION',
            'path': path_str,
            'details': f"Found CJK characters: {''.join(set(cjk_matches))}",
            'snippet': val
        })
        
    # 2. Latin token / homoglyph inspection
    # Tokenize words
    words = re.findall(r'[\w-]+', val, re.UNICODE)
    for w in words:
        has_cyrillic = bool(re.search(r'[\u0400-\u04ff]', w))
        has_latin = bool(re.search(r'[a-zA-Z]', w))
        
        if has_cyrillic and has_latin:
            issues.append({
                'type': 'HOMOGLYPH_CORRUPTION',
                'path': path_str,
                'details': f"Mixed Cyrillic and Latin characters in single word '{w}'",
                'snippet': val
            })
        elif has_latin and not has_cyrillic:
            clean_token = w.strip('.,!?:;"()«»[]+-')
            if is_headword:
                if clean_token.lower() in PERMITTED_GRAMMAR_TAGS or clean_token in PERMITTED_LATIN_TOKENS:
                    continue
            if clean_token not in PERMITTED_LATIN_TOKENS:
                issues.append({
                    'type': 'UNAUTHORIZED_LATIN_WORD',
                    'path': path_str,
                    'details': f"Unauthorized Latin token '{w}' in Russian text",
                    'snippet': val
                })
                
    return issues

def validate_data_tree(obj, current_path=""):
    issues = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            field_path = f"{current_path}.{k}" if current_path else k
            # Universal Chimera Token Check: In ANY field (bilingual, Japanese, or Russian),
            # words containing mixed Cyrillic and Katakana (e.g. роヤль, Наム) are STRICTLY FORBIDDEN!
            if isinstance(v, str):
                chimeras = CHIMERA_CYRILLIC_KATAKANA.findall(v)
                if chimeras:
                    issues.append({
                        'type': 'CHIMERA_CONTAMINATION',
                        'path': field_path,
                        'details': f"Illegal Cyrillic-Katakana chimera token(s): {list(set(chimeras))}",
                        'snippet': v
                    })

            # Pure Russian sentence fields
            if k in ['ru', 'russian', 'sentence_ru', 'text_ru', 'target_phrase', 'ru_stem']:
                if isinstance(v, str):
                    issues.extend(check_string_purity(v, field_path, is_headword=False))
                elif isinstance(v, list):
                    for idx, item in enumerate(v):
                        if isinstance(item, str):
                            issues.extend(check_string_purity(item, f"{field_path}[{idx}]", is_headword=False))
            # Pure Russian headword fields
            elif k in ['word', 'raw_word', 'lemma']:
                if isinstance(v, str):
                    issues.extend(check_string_purity(v, field_path, is_headword=True))
                elif isinstance(v, list):
                    for idx, item in enumerate(v):
                        if isinstance(item, str):
                            issues.extend(check_string_purity(item, f"{field_path}[{idx}]", is_headword=True))
            elif k in ['audio_paragraphs', 'audio_sentences', 'examples', 'pairs', 'conjugations', 'conservatory_examples']:
                if isinstance(v, list):
                    for idx, item in enumerate(v):
                        issues.extend(validate_data_tree(item, f"{field_path}[{idx}]"))
                else:
                    issues.extend(validate_data_tree(v, field_path))
            else:
                issues.extend(validate_data_tree(v, field_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            issues.extend(validate_data_tree(item, f"{current_path}[{idx}]"))
            
    return issues

def main():
    target_files = [
        'data/vocabulary_db.json',
        'data/curriculum_catalog.json',
        'data/lesson_buffer.json',
        'data/grammar_handbook.json',
        'data/grammar_taxonomy.json',
        'data/grammar_patterns.json',
        'data/verb_conjugations.json',
        'data/canonical_composer_quotes.json'
    ]
    
    total_violations = 0
    print("==================================================")
    print("[INFO] RUSSIAN LINGUISTIC PURITY LINTER (CI / BATCH)")
    print("==================================================")
    
    for fpath in target_files:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            file_issues = validate_data_tree(data, fpath)
            if file_issues:
                print(f"[FAIL] {fpath}: {len(file_issues)} violations found")
                for iss in file_issues[:5]:
                    print(f"   [{iss['type']}] {iss['path']}: {iss['details']}")
                    print(f"      Snippet: {iss['snippet'][:90]}...")
                if len(file_issues) > 5:
                    print(f"   ... and {len(file_issues) - 5} more issues in {fpath}")
                total_violations += len(file_issues)
            else:
                print(f"[PASS] {fpath}: 0 violations (100% pure Russian)")
        except Exception as e:
            print(f"[ERROR] Error reading {fpath}: {e}")
            total_violations += 1
            
    print("--------------------------------------------------")
    if total_violations > 0:
        print(f"FAILED: Total violations across databases: {total_violations}")
        return False
    else:
        print("SUCCESS: All Russian content passes linguistic purity standards!")
        return True

if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
