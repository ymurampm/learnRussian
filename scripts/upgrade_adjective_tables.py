"""
Upgrade all adjective declension tables in data/vocabulary_db.json to full 6 cases.
"""
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
VOCAB_PATH = os.path.join(DATA_DIR, 'vocabulary_db.json')

def generate_adjective_declension_table(m, f, n, pl):
    m = m.strip().replace('́', '')
    f = f.strip().replace('́', '')
    n = n.strip().replace('́', '')
    pl = pl.strip().replace('́', '')

    # Special case: третий (третья, третье, третьи)
    if m == 'третий' or (m.endswith('ий') and f.endswith('ья')):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格 (Nom)', m, f, n, pl],
            ['生格 (Gen)', f'{stem}ьего', f'{stem}ьей', f'{stem}ьего', f'{stem}ьих'],
            ['与格 (Dat)', f'{stem}ьему', f'{stem}ьей', f'{stem}ьему', f'{stem}ьим'],
            ['対格 (Acc)', f'{m} / {stem}ьего', f'{stem}ью', n, f'{pl} / {stem}ьих'],
            ['造格 (Ins)', f'{stem}ьим', f'{stem}ьей', f'{stem}ьим', f'{stem}ьими'],
            ['前置格 (Prp)', f'{stem}ьем', f'{stem}ьей', f'{stem}ьем', f'{stem}ьих'],
        ]

    # Soft declension: синий (синяя, синее, синие)
    if f.endswith('яя') and n.endswith('ее'):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格 (Nom)', m, f, n, pl],
            ['生格 (Gen)', f'{stem}его', f'{stem}ей', f'{stem}его', f'{stem}их'],
            ['与格 (Dat)', f'{stem}ему', f'{stem}ей', f'{stem}ему', f'{stem}им'],
            ['対格 (Acc)', f'{m} / {stem}его', f'{stem}юю', n, f'{pl} / {stem}их'],
            ['造格 (Ins)', f'{stem}им', f'{stem}ей', f'{stem}им', f'{stem}ими'],
            ['前置格 (Prp)', f'{stem}ем', f'{stem}ей', f'{stem}ем', f'{stem}их'],
        ]

    # Sibilant stem unstressed: хороший, горячий, свежий (хорошая, хорошее, хорошие)
    last_cons = m[:-2][-1:] if len(m) >= 3 else ''
    if last_cons in ['ж', 'ч', 'ш', 'щ', 'ц'] and n.endswith('ее'):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格 (Nom)', m, f, n, pl],
            ['生格 (Gen)', f'{stem}его', f'{stem}ей', f'{stem}его', f'{stem}их'],
            ['与格 (Dat)', f'{stem}ему', f'{stem}ей', f'{stem}ему', f'{stem}им'],
            ['対格 (Acc)', f'{m} / {stem}его', f'{stem}ую', n, f'{pl} / {stem}их'],
            ['造格 (Ins)', f'{stem}им', f'{stem}ей', f'{stem}им', f'{stem}ими'],
            ['前置格 (Prp)', f'{stem}ем', f'{stem}ей', f'{stem}ем', f'{stem}их'],
        ]

    # Velar stem (г, к, х) or sibilant stressed (большой): русский, великий, тихий, большой
    if last_cons in ['г', 'к', 'х'] or (last_cons in ['ж', 'ч', 'ш', 'щ'] and m.endswith('ой')):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格 (Nom)', m, f, n, pl],
            ['生格 (Gen)', f'{stem}ого', f'{stem}ой', f'{stem}ого', f'{stem}их'],
            ['与格 (Dat)', f'{stem}ому', f'{stem}ой', f'{stem}ому', f'{stem}им'],
            ['対格 (Acc)', f'{m} / {stem}ого', f'{stem}ую', n, f'{pl} / {stem}их'],
            ['造格 (Ins)', f'{stem}им', f'{stem}ой', f'{stem}им', f'{stem} Jimi'.replace('Jimi', 'ими')],
            ['前置格 (Prp)', f'{stem}ом', f'{stem}ой', f'{stem}ом', f'{stem}их'],
        ]

    # Standard hard declension: новый, сложный, трудный, красивый, молодой
    stem = m[:-2]
    return [
        ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
        ['主格 (Nom)', m, f, n, pl],
        ['生格 (Gen)', f'{stem}ого', f'{stem}ой', f'{stem}ого', f'{stem}ых'],
        ['与格 (Dat)', f'{stem}ому', f'{stem}ой', f'{stem}ому', f'{stem}ым'],
        ['対格 (Acc)', f'{m} / {stem}ого', f'{stem}ую', n, f'{pl} / {stem}ых'],
        ['造格 (Ins)', f'{stem}ым', f'{stem}ой', f'{stem}ым', f'{stem}ыми'],
        ['前置格 (Prp)', f'{stem}ом', f'{stem}ой', f'{stem}ом', f'{stem}ых'],
    ]

def table_to_html(table):
    if not table:
        return ''
    headers = table[0]
    rows = table[1:]
    h_html = "".join([f'<th style="border:1px solid #444; padding:4px 8px; background:rgba(212,168,83,0.15); color:#ffd88a;">{h}</th>' for h in headers])
    r_html = ""
    for r in rows:
        cells = "".join([f'<td style="border:1px solid #444; padding:4px 8px;">{c}</td>' for c in r])
        r_html += f'<tr>{cells}</tr>'
    return f'<table class="declension-table" style="border-collapse:collapse; width:100%; font-size:0.85rem; margin-top:4px;"><thead><tr>{h_html}</tr></thead><tbody>{r_html}</tbody></table>'

def main():
    with open(VOCAB_PATH, 'r', encoding='utf-8') as f:
        vdb = json.load(f)

    upgraded = 0
    for word, item in vdb.items():
        tbl = item.get('declension_table', [])
        pos = item.get('pos', '')
        tags = item.get('tags', [])
        is_adj = '形容詞' in pos or 'pos.adj' in tags or 'adj' in pos.lower()
        if is_adj and tbl and len(tbl) <= 2:
            # Check row 1
            if len(tbl) == 2:
                row0 = tbl[0]
                row1 = tbl[1]
                if len(row1) == 4:
                    m, f, n, pl = row1
                elif len(row1) == 3:
                    m, f, pl = row1
                    stem = m[:-2]
                    n = stem + ('ее' if f.endswith('яя') else 'ое')
                else:
                    continue

                full_tbl = generate_adjective_declension_table(m, f, n, pl)
                item['declension_table'] = full_tbl
                item['declension_html'] = table_to_html(full_tbl)
                upgraded += 1

    print(f"Upgraded {upgraded} adjectives in {VOCAB_PATH}")
    with open(VOCAB_PATH, 'w', encoding='utf-8') as f:
        json.dump(vdb, f, ensure_ascii=False, indent=2)
    print("Saved successfully.")

if __name__ == '__main__':
    main()
