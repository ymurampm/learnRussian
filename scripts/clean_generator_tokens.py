# -*- coding: utf-8 -*-
import glob
import re

for path in glob.glob('scripts/generate_*.py'):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    def clean_tokens_block(match):
        block = match.group(0)
        # remove punctuation before closing quote
        cleaned = re.sub(r'"([^"]*?)[,.?!;:…«»]+"', r'"\1"', block)
        return cleaned

    new_content = re.sub(r'"tokens":\s*\[[^\]]+\]', clean_tokens_block, content)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Cleaned tokens in generation script: {path}")
