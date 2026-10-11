# -*- coding: utf-8 -*-
import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

punc_regex = re.compile(r'^[,.?!;:…«»"()]+|[,.?!;:…«»"()]+$')

def check_and_clean_file(file_path, save=True):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cleaned_items = 0
    cleaned_tokens_total = 0

    def clean_quiz_items(quiz_items):
        nonlocal cleaned_items, cleaned_tokens_total
        for q in quiz_items:
            if q.get('type') == 'sentence_builder' and 'tokens' in q:
                old_tokens = q['tokens']
                new_tokens = [punc_regex.sub('', t).strip() for t in old_tokens]
                if old_tokens != new_tokens:
                    cleaned_items += 1
                    diffs = [(o, n) for o, n in zip(old_tokens, new_tokens) if o != n]
                    cleaned_tokens_total += len(diffs)
                    print(f"  [{q.get('id', 'unknown')}] Cleaned: {diffs}")
                    q['tokens'] = new_tokens

    if isinstance(data, list):
        for entry in data:
            if 'sessions' in entry:
                for s in entry['sessions'].values():
                    if 'quiz_items' in s:
                        clean_quiz_items(s['quiz_items'])
            if 'quiz_items' in entry:
                clean_quiz_items(entry['quiz_items'])
    elif isinstance(data, dict):
        if 'sessions' in data:
            for s in data['sessions'].values():
                if 'quiz_items' in s:
                    clean_quiz_items(s['quiz_items'])

    if save and cleaned_items > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved cleaned data to {file_path}")

    print(f"File {file_path}: cleaned {cleaned_items} questions, {cleaned_tokens_total} dirty tokens.")
    return cleaned_items

print("=== Cleaning curriculum_catalog.json ===")
check_and_clean_file('data/curriculum_catalog.json', save=True)

print("\n=== Cleaning lesson_buffer.json ===")
check_and_clean_file('data/lesson_buffer.json', save=True)
