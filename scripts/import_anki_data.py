"""
Anki Russian Data Importer
Parses all batch JSON files in ../AnkiRussian, extracts structured information:
- Word, POS, Meaning, Notes
- Detailed grammar anatomy
- Declension / Conjugation tables
- Vocabulary networks (derivatives, aspect pairs, synonyms)
- Musical/Conservatory example sentences
Outputs to data/vocabulary_db.json
"""
import glob
import json
import os
import re
import sys
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_examples(html_chunk):
    lines = re.split(r'<br\s*/?>|\n', html_chunk)
    examples = []
    current_ru = None
    for line in lines:
        if not line.strip() or '【応用例文' in line or '応用例文' in line:
            continue
        soup_line = BeautifulSoup(line, 'html.parser')
        clean_l = soup_line.get_text().strip()
        if not clean_l:
            continue
        if (clean_l.startswith('(') or clean_l.startswith('（')) and (clean_l.endswith(')') or clean_l.endswith('）')):
            ja = clean_l.strip('()（）')
            if current_ru:
                examples.append({'ru': current_ru, 'ja': ja})
                current_ru = None
        else:
            ru = re.sub(r'^[①②③④⑤\d\.\s]+', '', clean_l).strip()
            if ru:
                if current_ru:
                    examples.append({'ru': current_ru, 'ja': ''})
                current_ru = ru
    if current_ru:
        examples.append({'ru': current_ru, 'ja': ''})
    return examples

def parse_network(html_chunk):
    lines = re.split(r'<br\s*/?>|\n', html_chunk)
    items = []
    for line in lines:
        if not line.strip() or '【語彙ネットワーク' in line or '語彙ネットワーク' in line:
            continue
        soup_line = BeautifulSoup(line, 'html.parser')
        line_text = soup_line.get_text().strip()
        clean_l = re.sub(r'^[^\wа-яА-ЯёЁ]+', '', line_text).strip()
        if not clean_l:
            continue
        sub_items = re.split(r'(?<=\))\s*,\s*', clean_l)
        for si in sub_items:
            si = si.strip().rstrip(',')
            if si:
                items.append(si)
    return items

def extract_pos_and_notes(english_str):
    pos = "その他"
    notes = ""
    meaning = english_str
    
    bracket_match = re.search(r'\[(.*?)\]', english_str)
    if bracket_match:
        notes = bracket_match.group(1).strip()
        meaning = meaning.replace(bracket_match.group(0), '')
        
    paren_match = re.search(r'\((.*?)\)', meaning)
    if paren_match:
        pos = paren_match.group(1).strip()
        meaning = meaning.replace(paren_match.group(0), '')
        
    meaning = clean_text(meaning).rstrip(',; ')
    return pos, notes, meaning

def tag_word(word, pos, meaning, notes):
    tags = []
    p = pos.lower()
    m = meaning.lower()
    n = notes.lower()
    
    if '名詞' in pos:
        tags.append('pos.noun')
        if '男性' in pos: tags.append('gender.masc')
        elif '女性' in pos: tags.append('gender.fem')
        elif '中性' in pos: tags.append('gender.neut')
    elif '動詞' in pos:
        tags.append('pos.verb')
        if '不完了体' in pos: tags.append('verb.aspect_nsv')
        if '完了体' in pos: tags.append('verb.aspect_sv')
        if any(v in word for v in ['идти', 'ходить', 'ехать', 'ездить', 'бежать', 'летать', 'плыть', 'нести', 'вести']):
            tags.append('verb.motion')
    elif '形容詞' in pos:
        tags.append('pos.adj')
        if '最上級' in pos or '比較級' in pos: tags.append('adj.comparative')
    elif '副詞' in pos:
        tags.append('pos.adv')
    elif '前置詞' in pos:
        tags.append('pos.prep')
    elif '接続詞' in pos:
        tags.append('syntax.conjunction')
    elif '数詞' in pos:
        tags.append('numeral')

    music_keywords = ['ピアノ', '音楽', '演奏', '曲', '音', 'コンサート', '楽譜', 'ホール', '歌', '劇場', '芸術', 'マエストロ', 'コンクール', '音大', '音楽院']
    if any(k in m for k in music_keywords) or any(k in n for k in music_keywords):
        tags.append('theme.music')
        
    emotion_keywords = ['愛', '気', '心', '喜', '悲', '感', '希望', '信頼', '憧れ', '熱心']
    if any(k in m for k in emotion_keywords):
        tags.append('theme.emotion')
        
    return tags

def main():
    possible_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../AnkiRussian')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../../AnkiRussian')),
        r'c:\Antigravity\Projects\AnkiRussian'
    ]
    anki_dir = None
    for d in possible_dirs:
        if os.path.exists(d):
            anki_dir = d
            break
            
    if not anki_dir:
        print(f"Directory not found in: {possible_dirs}")
        sys.exit(1)
        
    files = glob.glob(os.path.join(anki_dir, '*_data.json'))
    print(f"Found {len(files)} batch files in {anki_dir}")
    
    vocab_db = {}
    total_raw_cards = 0
    
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                cards = json.load(f)
                if not isinstance(cards, list):
                    continue
                total_raw_cards += len(cards)
                for card in cards:
                    if not isinstance(card, dict):
                        continue
                    word = clean_text(card.get('russian', ''))
                    if not word:
                        continue
                    clean_word = re.sub(r'\s*\([mfn]\)', '', word).strip()
                    english_raw = card.get('english', '')
                    sentence_html = card.get('sentence', '')
                    
                    pos, notes, meaning = extract_pos_and_notes(english_raw)
                    sections = re.split(r'<hr[^>]*>', sentence_html)
                    
                    anatomy_text = ""
                    table_rows = []
                    table_html = ""
                    network_items = []
                    examples = []
                    
                    soup = BeautifulSoup(sentence_html, 'html.parser')
                    
                    for s in sections:
                        s_strip = s.strip()
                        if not s_strip:
                            continue
                        if '【文法・単語の徹底解剖' in s_strip or '【文法・構造' in s_strip:
                            sec0_soup = BeautifulSoup(s_strip, 'html.parser')
                            anatomy_text = clean_text(sec0_soup.get_text(separator=' '))
                            anatomy_text = re.sub(r'【[^】]+】', '', anatomy_text).strip()
                        elif '【語彙ネットワーク' in s_strip or '語彙ネットワーク' in s_strip:
                            network_items = parse_network(s_strip)
                        elif '【応用例文' in s_strip or '応用例文' in s_strip:
                            examples = parse_examples(s_strip)
                        
                    table = soup.find('table')
                    if table:
                        for tr in table.find_all('tr'):
                            row = [clean_text(td.get_text()) for td in tr.find_all(['th', 'td'])]
                            if any(row):
                                table_rows.append(row)
                        table_html = str(table)
                        
                    tags = tag_word(clean_word, pos, meaning, notes)
                    
                    entry = {
                        'id': card.get('id'),
                        'word': clean_word,
                        'raw_word': word,
                        'pos': pos,
                        'meaning': meaning,
                        'notes': notes,
                        'anatomy': anatomy_text,
                        'declension_table': table_rows,
                        'declension_html': table_html,
                        'network': network_items,
                        'examples': examples,
                        'tags': tags
                    }
                    
                    if clean_word not in vocab_db or len(examples) > len(vocab_db[clean_word]['examples']):
                        vocab_db[clean_word] = entry
                        
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")
            
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/vocabulary_db.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(vocab_db, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully processed {total_raw_cards} cards.")
    print(f"Extracted {len(vocab_db)} unique vocabulary entries into {out_path}")

if __name__ == '__main__':
    main()
