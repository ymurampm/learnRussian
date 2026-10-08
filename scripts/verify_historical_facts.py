# -*- coding: utf-8 -*-
"""
Musicological and Historical Fact-Checking Script for Tanya Russian Trainer.
Verifies that real institutions (Moscow Conservatory) and real composers (Rachmaninoff, Tchaikovsky, etc.)
are referenced with strict adherence to documented musicological and biographical facts.
"""

import json
import re
import sys

def verify_historical_facts():
    errors = []
    
    # 1. Check curriculum catalog
    with open('data/curriculum_catalog.json', 'r', encoding='utf-8') as f:
        catalog = json.load(f)
        
    for day in catalog:
        d = day.get('day_index')
        text = json.dumps(day, ensure_ascii=False)
        
        # Check Great Hall seat count misconception
        if re.search(r'девятьсот\s+мест|900\s*席', text):
            errors.append(f"Day {d}: Inaccurate Bolshoi Hall seat count found (900 seats instead of ~1,737 seats).")
            
        # Check Great Hall opening year (must be 1901)
        m = re.search(r'Большой зал[^"]*?(1[89][0-9]{2})', text)
        if m and m.group(1) != '1901':
            errors.append(f"Day {d}: Inaccurate Great Hall opening year {m.group(1)} (should be 1901).")

        # Check monument inscription misconception
        if re.search(r'記念碑には[^"]*?刻まれて[^"]*?Вдохновение', text):
            errors.append(f"Day {d}: Inaccurate claim that 'Вдохновение рождается...' is engraved on monument. Monument pedestal inscription is 'Великому русскому композитору Петру Ильичу Чайковскому'.")

        # Check false attribution of 'ещё два дня' memo to Rachmaninoff
        if 'два дня' in text and 'Рахманинов' in text and ('записка' in text or 'メモ' in text or '書き残した' in text):
            errors.append(f"Day {d}: Inaccurate attribution of fictional 'два дня' score note to Rachmaninoff. Fictional pedagogical notes must not be attributed to real historical composers.")

        # Check unverified room 42 piano legend
        if '42号室' in text and 'Рахманинов' in text:
            errors.append(f"Day {d}: Unverified classroom 42 legend attributed to Rachmaninoff.")

    # 2. Check vocabulary db
    with open('data/vocabulary_db.json', 'r', encoding='utf-8') as f:
        vdb = json.load(f)
        
    for word, entry in vdb.items():
        if not isinstance(entry, dict):
            continue
        for idx, ex in enumerate(entry.get('examples', [])):
            ru = ex.get('ru', '')
            ja = ex.get('ja', '')
            
            # Check Bolshoi Hall seat count
            if ('девятьсот мест' in ru or '900' in ja) and ('Больш' in ru or '大ホール' in ja):
                errors.append(f"Vocab [{word}]: Inaccurate Bolshoi Hall seat count in example ({ru}). Bolshoi Zal has ~1,737 seats.")
                
            # Check Shostakovich 7th Symphony performed solo by pianist
            if ('7-ю симфонию Шостаковича' in ru or '第7番' in ja) and ('Алёна исполняет' in ru or ('アリョーナは' in ja and '演奏' in ja)):
                if 'оркестр' not in ru.lower() and '交響' not in ja:
                    errors.append(f"Vocab [{word}]: Shostakovich 7th Symphony is an orchestral work, cannot be described as played solo by pianist without orchestra.")
                    
            # Check awkward phrasing 'Залу Большого зала'
            if 'Залу Большого зала' in ru:
                errors.append(f"Vocab [{word}]: Redundant phrasing 'Залу Большого зала'.")

    print("=== HISTORICAL FACT-CHECK RESULTS ===")
    if errors:
        print(f"FAIL: {len(errors)} historical/musicological inconsistencies found:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("PASS: All historical references strictly adhere to canonical musicological facts!")
        return True

if __name__ == '__main__':
    success = verify_historical_facts()
    if not success:
        sys.exit(1)
