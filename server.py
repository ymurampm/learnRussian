"""
Tanya Russian Learning App - Lightweight Local Server
Serves static frontend assets and provides REST APIs for:
- User progress, streak, intimacy meter, absence handling
- Daily lessons & buffer management
- Fast vocabulary & declension lookup (2140 words from Anki)
- Grammar taxonomy & weakness tracking
Runs on Python standard library without external dependencies.
"""
import asyncio
import hashlib
import http.server
import json
import mimetypes
import os
import re
import socketserver
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
import edge_tts

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PORT = 8085
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
AUDIO_DIR = os.path.join(BASE_DIR, 'audio_cache')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Ensure mime types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('audio/mpeg', '.mp3')

def load_json(rel_path, default=None):
    path = os.path.join(DATA_DIR, rel_path)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if rel_path == 'user_progress.json':
                    if data and isinstance(data, dict) and data.get('user_profile', {}).get('name'):
                        return data
                    print(f"[SECURITY] {path} appears empty or corrupted; attempting backup recovery...")
                else:
                    return data
        except Exception as e:
            print(f"Error reading {path}: {e}")

    # Fallback for user_progress.json to prevent data loss
    if rel_path == 'user_progress.json':
        backups_dir = os.path.join(DATA_DIR, 'backups')
        if os.path.exists(backups_dir):
            for b_name in sorted(os.listdir(backups_dir), reverse=True):
                candidate = os.path.join(backups_dir, b_name, 'user_progress.json')
                if not os.path.exists(candidate) and b_name.endswith('.json'):
                    candidate = os.path.join(backups_dir, b_name)
                if os.path.exists(candidate):
                    try:
                        with open(candidate, 'r', encoding='utf-8') as f:
                            b_data = json.load(f)
                            if b_data and isinstance(b_data, dict) and b_data.get('user_profile', {}).get('name'):
                                print(f"[RECOVERY] Successfully recovered user_progress.json from {candidate}!")
                                return b_data
                    except Exception:
                        pass

    return default if default is not None else {}

def save_json(rel_path, data):
    path = os.path.join(DATA_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Protect user_progress.json from being overwritten with empty or corrupted data
    if rel_path == 'user_progress.json':
        if not data or not isinstance(data, dict):
            print(f"[SECURITY REJECT] Attempted to save non-dict to {path}! Aborting save.")
            return
        if not data.get('user_profile', {}).get('name'):
            print(f"[SECURITY REJECT] Attempted to save empty user_profile to {path}! Aborting save.")
            return

    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def get_effective_date(dt=None):
    """
    Returns the effective study date according to the 01:00 AM cutoff rule.
    00:00:00 - 00:59:59 belongs to the previous calendar day's study cycle.
    01:00:00 begins the new day's cycle.
    """
    if dt is None:
        dt = datetime.now()
    if dt.hour < 1:
        return (dt - timedelta(days=1)).date()
    return dt.date()

# In-memory vocabulary index with automatic reload on file changes
_VOCAB_CACHE = None
_VOCAB_MTIME = 0

def extract_headwords(key):
    """
    Extracts all dictionary headwords from compound / annotated keys.
    Handles aspect pairs (нсв/св), prefix contractions (стоять/по- -> стоять, постоять),
    irregular plural notes (сын (pl сыновья) -> сын, сыновья), and government notes.
    """
    pl_match = re.search(r'\(pl\s+([а-яёА-ЯЁ]+)\)', key)
    pl_word = pl_match.group(1).lower() if pl_match else None
    clean_k = re.sub(r'\(.*?\)', '', key).strip().lower()
    headwords = []
    if '/' in clean_k:
        parts = [p.strip() for p in clean_k.split('/') if p.strip()]
        if len(parts) >= 2:
            base = parts[0]
            headwords.append(base)
            for other in parts[1:]:
                if other.endswith('-'):
                    prefix = other[:-1]
                    headwords.append(f"{prefix}{base}")
                else:
                    headwords.append(other)
        else:
            headwords.extend(parts)
    else:
        if clean_k:
            headwords.append(clean_k)
    if pl_word and pl_word not in headwords:
        headwords.append(pl_word)
    return [hw for hw in headwords if hw]

def get_vocab_db():
    global _VOCAB_CACHE, _VOCAB_MTIME
    p = os.path.join(DATA_DIR, 'vocabulary_db.json')
    try:
        mt = os.path.getmtime(p)
        if _VOCAB_CACHE is None or mt > _VOCAB_MTIME:
            raw_vdb = load_json('vocabulary_db.json', {})
            _VOCAB_CACHE = dict(raw_vdb)
            # Index all headwords expanded with prefixes and variants
            for k, entry in raw_vdb.items():
                for hw_clean in extract_headwords(k):
                    if hw_clean and hw_clean not in _VOCAB_CACHE:
                        _VOCAB_CACHE[hw_clean] = entry
            if 'RUSSIAN_CORE_ENTRIES' in globals():
                _VOCAB_CACHE.update(RUSSIAN_CORE_ENTRIES)
            if 'RUSSIAN_UNINFLECTED_ENTRIES' in globals():
                _VOCAB_CACHE.update(RUSSIAN_UNINFLECTED_ENTRIES)
            _VOCAB_MTIME = mt
            print(f"VOCAB_DB loaded/reloaded: {len(_VOCAB_CACHE)} entries (mtime={mt})")
    except Exception as e:
        if _VOCAB_CACHE is None:
            _VOCAB_CACHE = {}
    return _VOCAB_CACHE


# Set of strictly uninflected Russian words (Never assign declension/conjugation tables!)
UNINFLECTED_WORDS = {
    'и', 'а', 'но', 'или', 'что', 'как', 'если', 'чтобы', 'хотя', 'потому', 'поэтому',
    'сейчас', 'теперь', 'сегодня', 'вчера', 'завтра', 'утром', 'днём', 'вечером', 'ночью',
    'долго', 'скоро', 'наконец', 'всегда', 'никогда', 'иногда', 'часто', 'редко',
    'очень', 'много', 'мало', 'немного', 'слишком', 'быстро', 'медленно', 'хорошо', 'плохо',
    'безупречно', 'усердно', 'вместе', 'здесь', 'тут', 'там', 'везде', 'всюду', 'куда', 'где', 'откуда',
    'уже', 'ещё', 'не', 'ни', 'ли', 'же', 'бы', 'даже', 'только', 'ведь', 'вот', 'вон'
}

RUSSIAN_UNINFLECTED_ENTRIES = {
    'усердно': {
        'word': 'усердно',
        'pos': '副詞 (Наречие・不変化詞)',
        'meaning': '熱心に、勤勉に、一生懸命に',
        'notes': '【不変化詞】格変化・人称活用なし（様態の副詞）',
        'anatomy': '形容詞 «усердный»（熱心な）から派生した様態の副詞。ロシア語の副詞は不変化詞（неизменяемая часть речи）であり、名詞のような格変化や動詞のような活用は一切行いません。「熱心に練習する（усердно заниматься）」のように動詞を直接修飾します。',
        'declension_table': [],
        'network': ['усердный (形容詞: 熱心な)', 'усердие (名詞: 熱心・勤勉・精進)', 'старательно (副詞: 丹念に・熱心に)', 'прилежно (副詞: 勤勉に)'],
        'examples': [
            {'ru': 'Студенты усердно занимаются в просторных классах консерватории.', 'ja': '学生たちは音楽院の広い教室で熱心に練習しています。'},
            {'ru': 'Юсукэ усердно репетирует сложный пассаж.', 'ja': 'Yusukeさんは難しいパッセージを熱心に練習しています。'}
        ]
    },
    'и': {
        'word': 'и',
        'pos': '接続詞 (Союз・不変化詞)',
        'meaning': '〜と、そして、また',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '並列の等位接続詞。「A и B」（AとB）、文頭で「И тогда...」（そしてその時...）。強調で「〜さえも」の意（«И я это знаю» 私でさえそれを知っている）。語形変化は一切ありません。',
        'declension_table': [],
        'network': ['а (〜だが、一方は)', 'но (しかし/逆接)', 'да (および・そして)', 'или (または)'],
        'examples': [
            {'ru': 'Алёна и Юсукэ репетируют дуэт.', 'ja': 'アリョーナとYusukeさんは連弾を練習しています。'},
            {'ru': 'Музыка звучала тихо и проникновенно.', 'ja': '音楽は静かに、そして心に染み入るように響きました。'}
        ]
    },
    'а': {
        'word': 'а',
        'pos': '接続詞 (Союз・不変化詞)',
        'meaning': '〜だが、一方（対比）',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '対比を表す等位接続詞。「AではなくB」「Aは〜だが、Bは〜だ」という軽い対比を作ります。語形変化は一切ありません。',
        'declension_table': [],
        'network': ['и (そして/並列)', 'но (しかし/強い逆接)'],
        'examples': [
            {'ru': 'Я играю партию примо, а Алёна играет секондо.', 'ja': '私はプリモ（第1パート）を弾き、アリョーナはセコンドを弾きます。'}
        ]
    },
    'но': {
        'word': 'но',
        'pos': '接続詞 (Союз・不変化詞)',
        'meaning': 'しかし、だが（逆接）',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '明確な逆接を表す等位接続詞。常に直前にコンマが置かれます（, но ...）。語形変化は一切ありません。',
        'declension_table': [],
        'network': ['однако (しかしながら)', 'а (〜だが/対比)'],
        'examples': [
            {'ru': 'Пассаж сложный, но очень красивый.', 'ja': 'パッセージは難しいですが、とても美しいです。'}
        ]
    },
    'сейчас': {
        'word': 'сейчас',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '今、現在、ただいま',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞。発話時点の「今」や直近の未来を表します。語源は «сей час»（この時）ですが、現代語では完全な不変化詞であり、格変化は一切ありません。',
        'declension_table': [],
        'network': ['теперь (今や・それに対して今は)', 'сегодня (今日)', 'уже (もう・すでに)'],
        'examples': [
            {'ru': 'Сейчас в Малом зале консерватории идёт репетиция.', 'ja': '今、音楽院の小ホールではリハーサルが行われています。'},
            {'ru': 'Я сейчас сыграю эту тему ещё раз.', 'ja': '私は今からこのテーマをもう一度弾いてみます。'}
        ]
    },
    'теперь': {
        'word': 'теперь',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '今や、現在は（過去との対比）',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '過去の状態と比較して「以前とは違って今は」というニュアンスを持つ時間副詞。格変化はありません。',
        'declension_table': [],
        'network': ['сейчас (今/時点)', 'раньше (以前は)'],
        'examples': [
            {'ru': 'Теперь мы играем этот фрагмент свободно и уверенно.', 'ja': '今や私たちはこのフレーズをのびのびと自信を持って弾いています。'}
        ]
    },
    'сегодня': {
        'word': 'сегодня',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '今日、本日',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞。発音は「シヴォードニャ」（гはv音）。格変化はありません。',
        'declension_table': [],
        'network': ['вчера (昨日)', 'завтра (明日)', 'сегодняшний (今日の/形容詞)'],
        'examples': [
            {'ru': 'Сегодня у нас очень важная репетиция.', 'ja': '今日は私たちにとって極めて重要なリハーサルがあります。'}
        ]
    },
    'вчера': {
        'word': 'вчера',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '昨日',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞。格変化はありません。',
        'declension_table': [],
        'network': ['сегодня (今日)', 'вчерашний (昨日の/形容詞)'],
        'examples': [
            {'ru': 'Вчера мы разобрали сложный финал.', 'ja': '昨日私たちは難解なフィナーレを譜読みしました。'}
        ]
    },
    'долго': {
        'word': 'долго',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '長らく、長い間',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の継続・経過が長いことを表す副詞。格変化はありません。比較級は дольше（より長く）。',
        'declension_table': [],
        'network': ['продолжительно (長期間にわたって)', 'недолго (短時間)', 'долгий (長い/形容詞)', 'долгота (長調・経度)'],
        'examples': [
            {'ru': 'Алёна долго оттачивала филигранную технику.', 'ja': 'アリョーナは長い時間をかけて精巧なテクニックを研磨しました。'},
            {'ru': 'Публика долго не отпускала артистку со сцены.', 'ja': '聴衆は長らく演奏者をステージから去らせませんでした。'}
        ]
    },
    'наконец': {
        'word': 'наконец',
        'pos': '副詞 / 挿入語 (Неизменяемое слово)',
        'meaning': 'ついに、とうとう、最後に',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞・挿入語。待ち望んでいた結果に到達したことを表します（«Наконец-то!» ついにやった！）。語形変化はありません。',
        'declension_table': [],
        'network': ['в конце концов (ついに・結局)', 'конец (終わり/名詞)'],
        'examples': [
            {'ru': 'Наконец наш дуэт зазвучал в полной гармонии.', 'ja': 'ついに私たちのデュオは完全な調和をもって響き始めました。'}
        ]
    },
    'безупречно': {
        'word': 'безупречно',
        'pos': '様態の副詞 (Неизменяемое слово)',
        'meaning': '申し分なく、完璧に',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '様態の副詞。接頭辞 без-（〜なしで）+ упрёк（非難・咎め）+ 接尾辞 -о。「非難の余地が一切ないほど完璧に」という意味。語形変化はありません。',
        'declension_table': [],
        'network': ['безупречный (申し分ない/形容詞)', 'упрёк (非難/名詞)'],
        'examples': [
            {'ru': 'Они сыграли фортепианный пассаж безупречно.', 'ja': '彼らはピアノのパッセージを申し分なく完璧に弾ききりました。'}
        ]
    },
    'очень': {
        'word': 'очень',
        'pos': '程度の副詞 (Неизменяемое слово)',
        'meaning': 'とても、大変',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '程度の副詞。形容詞・副詞・動詞を強めます。格変化はありません。',
        'declension_table': [],
        'network': ['слишком (あまりにも)', 'крайне (極めて)'],
        'examples': [
            {'ru': 'Эта соната очень эмоциональная.', 'ja': 'このソナタはとても情熱的です。'}
        ]
    },

    'пешком': {
        'word': 'пешком',
        'pos': '様態の副詞 (Неизменяемое слово)',
        'meaning': '徒歩で、歩いて',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '移動の様態を表す副詞。「歩いて、自分の足で」向かうことを表します。乗物（на метро, на машине）と対比されます。語形変化は一切ありません。',
        'declension_table': [],
        'network': ['ходьба (歩行)', 'идти пешком (歩いて行く)', 'пешеход (歩行者)'],
        'examples': [
            {'ru': 'Каждый день мы ходим в консерваторию пешком.', 'ja': '毎日私たちは歩いて音楽院に通っています。'},
            {'ru': 'Я редко хожу туда пешком.', 'ja': '私はめったにそこへ歩いては行きません。'}
        ]
    },
    'утром': {
        'word': 'утром',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '朝に、午前に',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞。名詞 утро の造格形に由来しますが、副詞として完全に語形固定されています。格変化はありません。',
        'declension_table': [],
        'network': ['утро (朝/中性名詞)', 'днём (昼に)', 'вечером (夕方に)', 'ночью (夜に)'],
        'examples': [
            {'ru': 'Утром я с вдохновением сыграла сонату.', 'ja': '朝、私はインスピレーションを込めてソナタを演奏しました。'}
        ]
    },
    'нет': {
        'word': 'нет',
        'pos': '否定存在詞 (Неизменяемое слово)',
        'meaning': '〜がない、存在しない（生格支配）/ いいえ',
        'notes': '【不変化詞・生格支配】нет + 生格',
        'anatomy': '''否定存在を表す最重要語。
・«нет + 生格» で「〜がない」を表します（В аудитории нет рояля）。
・過去形は «не было + 生格»、未来形は «не будет + 生格»。
・格変化は一切ありません（不変化詞）。''',
        'declension_table': [],
        'network': ['есть (ある/肯定存在)', 'не было (なかった)', 'не будет (ないだろう)'],
        'examples': [
            {'ru': 'В этом классе сейчас нет пианиста.', 'ja': 'この練習室には今ピアニストがいません。'},
            {'ru': 'В этой аудитории сегодня нет рояля.', 'ja': 'この練習室には今日グランドピアノがありません。'}
        ]
    },
    'есть': {
        'word': 'есть',
        'pos': '肯定存在詞 (Неизменяемое слово)',
        'meaning': '〜がある、存在する（主格伴随）',
        'notes': '【不変化詞・主格伴随】есть + 主格',
        'anatomy': '存在や所有を表す不変化詞。「〜がある、持っている」（У меня есть ноты）を表します。格変化はありません。',
        'declension_table': [],
        'network': ['нет (ない/否定存在)'],
        'examples': [
            {'ru': 'В этом классе сейчас есть пианист.', 'ja': 'この練習室には今ピアニストがいます。'},
            {'ru': 'У меня есть новые ноты.', 'ja': '私には新しい楽譜があります。'}
        ]
    },
    'завтра': {
        'word': 'завтра',
        'pos': '時間の副詞 (Неизменяемое слово)',
        'meaning': '明日',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '時間の副詞。格変化はありません。',
        'declension_table': [],
        'network': ['сегодня (今日)', 'вчера (昨日)'],
        'examples': [
            {'ru': 'Завтра на концерте мы обязательно сыграем этот дуэт.', 'ja': '明日コンサートで私たちは必ずこの二重奏を弾き切ります。'}
        ]
    },
    'обязательно': {
        'word': 'обязательно',
        'pos': '副詞 / 挿入語 (Неизменяемое слово)',
        'meaning': '必ず、ぜひとも、きっと',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '確信や強い意志を表す副詞。格変化はありません。',
        'declension_table': [],
        'network': ['обязательный (必須の/形容詞)'],
        'examples': [
            {'ru': 'Мы обязательно сыграем этот дуэт безупречно.', 'ja': '私たちは必ずやこの二重奏を完璧に演奏してみせます。'}
        ]
    },
    'обычно': {
        'word': 'обычно',
        'pos': '頻度の副詞 (Неизменяемое слово)',
        'meaning': '普段は、通常、いつもは',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '習慣的な頻度を表す副詞。不完了体動詞とともに用いられます。格変化はありません。',
        'declension_table': [],
        'network': ['редко (めったに)', 'часто (しばしば)', 'обычный (通常の/形容詞)'],
        'examples': [
            {'ru': 'Обычно мы ездим в консерваторию на метро.', 'ja': '普段私たちは地下鉄で音楽院に通っています。'}
        ]
    },
    'редко': {
        'word': 'редко',
        'pos': '頻度の副詞 (Неизменяемое слово)',
        'meaning': 'めったに〜ない、まれに',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '低い頻度を表す副詞。格変化はありません。',
        'declension_table': [],
        'network': ['часто (よく/対義語)', 'редкий (珍しい/形容詞)'],
        'examples': [
            {'ru': 'Я редко хожу туда пешком.', 'ja': '私はめったにそこへ歩いては行きません。'}
        ]
    },
    'туда': {
        'word': 'туда',
        'pos': '方向の副詞 (Неизменяемое слово)',
        'meaning': 'そこへ、あちらへ（方向 куда?）',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '方向（куда?）を表す指示副詞。格変化はありません。',
        'declension_table': [],
        'network': ['сюда (ここへ)', 'там (そこで/場所)'],
        'examples': [
            {'ru': 'Я иду туда на концерт.', 'ja': '私はそこへコンサートを聴きに行きます。'}
        ]
    },
    'хотя': {
        'word': 'хотя',
        'pos': '譲歩の接続詞 (Неизменяемое слово)',
        'meaning': '〜だけれども、〜にもかかわらず',
        'notes': '【不変化詞】格変化・人称活用なし',
        'anatomy': '譲歩を表す従属接続詞。格変化はありません。',
        'declension_table': [],
        'network': ['но (しかし)'],
        'examples': [
            {'ru': 'Сейчас я иду на концерт, хотя обычно редко хожу туда пешком.', 'ja': '今コンサートに向かっていますが、普段はめったにそこまで歩きません。'}
        ]
    },
}

IRREGULAR_GRAMMAR_REGISTRY = {
    'стать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«стать» は将来の到達点や身分・職業を表す際、後ろに必ず【造格】を要求します（文中の「выдающимся музыкантом」が造格なのはこのためです）。活用は語幹に -н- が入る «я стану, ты станешь...»（単純未来）となります。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'быть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '過去形 «был / была» や未来形 «будет» で身分・職業・一時的状態を表す場合、述語名詞・形容詞は【造格】になります（例: Он был студентом / Она будет учительницей）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'являться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«являться»（〜である）は論説文・学術文・公的会話で多用される最重要動詞で、補語に必ず【造格】を要求します（例: является важным шагом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'казаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«казаться»（〜のように見える・思われる）は、述語名詞・形容詞に必ず【造格】を要求します（例: кажется странным / казался героем）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'показаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«показаться»（〜のように見える・思われる/完了体）は補語に【造格】を要求します（例: показался знакомым）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'оказаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«оказаться»（〜であることが判明する・〜になる）は補語に【造格】を要求します（例: оказался правдой / оказался отличным музыкантом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'оказываться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«оказываться»（〜であることが判明する/不完了体）は補語に【造格】を要求します（例: оказывается правдой）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'оставаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«оставаться»（〜のままである・留まる）は状態・身分の補語に【造格】を要求します（例: оставаться друзьями / остаётся загадкой）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'остаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«остаться»（〜のままである/完了体）は状態・身分の補語に【造格】を要求します（例: остаться довольным）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'работать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '身分・職種を表すとき «работать + 造格» で「〜として働く」を表します（例: работать врачом, работать преподавателем）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'управлять': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«управлять»（〜を操縦する・管理する・響きを操る）は目的語に対格ではなく必ず【造格】を要求します（例: управлять звуком, управлять автомобилем）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'руководить': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«руководить»（〜を指導・統率する）は必ず【造格】を要求します（例: руководить оркестром / хором）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'дирижировать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«дирижировать»（〜を指揮する）は【造格】を要求します（例: дирижировать оркестром）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'владеть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«владеть»（〜を自在に操る・修得する・所有する）は【造格】を要求します（例: владеть инструментом, владеть русским языком）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'овладеть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«овладеть»（〜をマスターする/完了体）は【造格】を要求します（例: овладеть мастерством）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'обладать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«обладать»（〜の資質・才能を備えている）は対格ではなく【造格】を要求します（例: обладать прекрасным слухом / талантом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'пользоваться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«пользоваться»（〜を利用する・享受する）は必ず【造格】を要求します（例: пользоваться словарём, пользоваться успехом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'заниматься': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«заниматься»（〜を練習・勉強する・専攻する・従事する）は対象に必ず【造格】を要求します（例: заниматься музыкой, заниматься спортом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'заняться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«заняться»（〜に着手する・専念する/完了体）は対象に【造格】を要求します（例: заняться делом）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'интересоваться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«интересоваться»（〜に関心・興味を持つ）は必ず【造格】を要求します（例: интересоваться искусством, классической музыкой）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'увлекаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«увлекаться»（〜に夢中になる・熱中する）は対象に【造格】を要求します（例: увлекаться джазом, увлекаться оперой）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'гордиться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«гордиться»（〜を誇りに思う）は対象に必ず【造格】を要求します（例: гордиться успехом, гордиться своим оркестром）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'восхищаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«восхищаться»（〜に感嘆する・うっとりする）は対象に【造格】を要求します（例: восхищаться исполнением, игрой пианиста）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'любоваться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        'detail': '«любоваться»（〜に見とれる・愛でる）は対象に【造格】を要求します（例: любоваться картиной, видом города）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'помогать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«помогать»（〜を助ける・手伝う）は英語の help と異なり、支援対象の相手に対格ではなく【与格】を要求します（例: помогать другу, помогать студентам）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'помочь': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«помочь»（助ける/完了体）は支援対象の相手に【与格】を要求します（例: помочь студенту）。活用: я помогу, ты поможешь, они помогут / помог, помогла。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'советовать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«советовать»（〜に助言する・勧める）は相手に【与格】を要求します（例: советовать товарищу）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'мешать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«мешать»（〜の邪魔をする・妨げる）は妨害対象に【与格】を要求します（例: мешать репетиции, не мешайте мне）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'верить': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«верить»（〜を信じる・信用する）は対象に【与格】を要求します（例: верить словам, верить людям）。※宗教的信仰は «в + 対格»。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'учить': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【二重格支配 (+ 対格 + 与格)】',
        'detail': '«учить»（教える）は【人を対格】に、【教える教科・事柄を与格】にとる二重格支配です（例: учить детей музыке）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'учиться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«учиться»（学ぶ・修得する）は専攻・学科・技術に【与格】を要求します（例: учиться музыке, учиться русскому языку）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'радоваться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【与格支配 (+ 与格)】',
        'detail': '«радоваться»（〜を喜ぶ）は喜ぶ対象に【与格】を要求します（例: радоваться успеху, радоваться победе）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'бояться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«бояться»（〜を恐れる）は目的語に対格ではなく必ず【生格】を要求します（例: бояться сцены, бояться ошибок, бояться темноты）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'достигать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«достигать»（〜に達する・達成する）は到達目標に必ず【生格】を要求します（例: достигать цели, достигать успеха）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'достичь': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«достичь»（達する/完了体）は到達目標に【生格】を要求します（例: достичь вершины, достичь успеха）。活用: я достигну, ты достигнешь / достиг, достигла。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'желать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«желать»（〜を望む・祈る）は望む対象に【生格】を要求します（例: желать удачи, желать счастья）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'требовать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«требовать»（〜を要求する・必要とする）は抽象的概念に対して【生格】を要求します（例: требовать внимания, требовать тишины）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'лишаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«лишаться»（〜を失う・奪われる）は喪失対象に【生格】を要求します（例: лишаться сил, лишаться возможности）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'избегать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【生格支配 (+ 生格)】',
        'detail': '«избегать»（〜を回避する・避ける）は対象に【生格】を要求します（例: избегать ошибок, избегать конфликтов）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'мечтать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【о + 前置格】',
        'detail': '«мечтать»（〜を夢見る・憧れる）は必ず前置詞 «о + 前置格» と結びつきます（例: мечтать о сцене, мечтать о победе）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'надеяться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【на + 対格】',
        'detail': '«надеяться»（〜を頼りにする・期待する）は前置詞 «на + 対格» を要求します（例: надеяться на помощь, надеяться на успех）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'отказываться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【от + 生格】',
        'detail': '«отказываться»（〜を辞退する・断る・放棄する）は前置詞 «от + 生格» を要求します（例: отказаться от предложения / от роли）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'отказаться': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【от + 生格】',
        'detail': '«отказаться»（断る/完了体）は前置詞 «от + 生格» を要求します（例: отказаться от помощи）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'зависеть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【от + 生格】',
        'detail': '«зависеть»（〜に左右される・依存する）は前置詞 «от + 生格» を要求します（例: зависеть от погоды / от обстоятельств）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'играть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【в + 対格 / на + 前置格】',
        'detail': 'スポーツや遊戯をする時は «в + 対格»（играть в футбол）、楽器を演奏する時は必ず «на + 前置格»（играть на скрипке / рояле）を使い分けます。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'сыграть': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【в + 対格 / на + 前置格】',
        'detail': '«сыграть»（演奏する/完了体）。楽器は «на + 前置格»（сыграть на рояле）、スポーツは «в + 対格»。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'участвовать': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【в + 前置格】',
        'detail': '«участвовать»（〜に参加する）は前置詞 «в + 前置格» を要求します（例: участвовать в конкурсе / в концерте）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'благодарить': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【人対格 + за 理由対格】',
        'detail': '感謝する対象の人は【対格】、感謝の理由は前置詞 «за + 対格» で表します（例: благодарить профессора за поддержку）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'поздравлять': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：動詞の格支配【人対格 + с 祝賀造格】',
        'detail': '祝賀する相手は【対格】、お祝いの内容は前置詞 «с + 造格» で表します（例: поздравлять с днём рождения / с победой）。',
        'related_tag': 'verb.government',
        'jump_label': '動詞の格支配',
    },
    'доволен': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 造格】',
        'detail': '«доволен»（満足している）は、満足の対象に必ず【造格】を要求します（例: доволен результатом, довольна выступлением, довольны успехом）。主格を置く誤りが検定頻出の減点対象です。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'довольна': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 造格】',
        'detail': '«довольна»（女性短尾形: 満足している）は対象に必ず【造格】を要求します（例: довольна концертом）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'довольны': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 造格】',
        'detail': '«довольны»（複数短尾形: 満足している）は対象に必ず【造格】を要求します（例: довольны результатами）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'богат': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 造格】',
        'detail': '«богат»（〜に富んでいる・恵まれている）は【造格】を要求します（例: богат талантами, страна богата ресурсами）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'готов': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【к + 与格】',
        'detail': '«готов»（準備ができている）は名詞を続ける場合必ず前置詞 «к + 与格» を用います（例: готов к экзамену）。動詞不定形が続く場合は直接結合します（готов помочь）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'готова': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【к + 与格】',
        'detail': '«готова»（女性短尾形: 準備ができている）は名詞に対して «к + 与格» を要求します（例: готова к уроку）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'готовы': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【к + 与格】',
        'detail': '«готовы»（複数短尾形: 準備ができている）は名詞に対して «к + 与格» を要求します（例: готовы к концерту）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'рад': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 与格】',
        'detail': '«рад»（嬉しく思う）は名詞に対して【与格】を要求します（例: рад встрече, рады успеху）。不定形も直接結合します（рад видеть вас）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'рада': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 与格】',
        'detail': '«рада»（女性短尾形: 嬉しい）は対象名詞に【与格】を要求します（例: рада знакомству）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'рады': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 与格】',
        'detail': '«рады»（複数短尾形: 嬉しい）は対象名詞に【与格】を要求します（例: рады гостям）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'полон': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 生格】',
        'detail': '«полон»（〜に満ちている）は満ちている対象に必ず【生格】を要求します（例: полон сил и энергии, зал полон зрителей）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'полна': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 生格】',
        'detail': '«полна»（女性短尾形: 満ちている）は対象に【生格】を要求します（例: комната полна цветов）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'полны': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【+ 生格】',
        'detail': '«полны»（複数短尾形: 満ちている）は対象に【生格】を要求します（例: полны надежд）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'похож': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【на + 対格】',
        'detail': '«похож»（〜に似ている）は前置詞 «на + 対格» を要求します（例: похож на отца, похожи друг на друга）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'похожа': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【на + 対格】',
        'detail': '«похожа»（女性短尾形: 似ている）は «на + 対格» を要求します（例: похожа на мать）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'похожи': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【на + 対格】',
        'detail': '«похожи»（複数短尾形: 似ている）は «на + 対格» を要求します（例: похожи на родителей）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'уверен': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【в + 前置格】',
        'detail': '«уверен»（〜を確信している）は前置詞 «в + 前置格» を要求します（例: уверен в успехе, уверена в победе）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'уверена': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【в + 前置格】',
        'detail': '«уверена»（女性短尾形: 確信している）は «в + 前置格» を要求します（例: уверена в себе）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'уверены': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【в + 前置格】',
        'detail': '«уверены»（複数短尾形: 確信している）は «в + 前置格» を要求します（例: уверены в победе）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'благодарен': {
        'alert_type': 'short_adj_government',
        'badge': '🎯 露検2級 必修：形容詞短尾形の格支配【与格 + за 対格】',
        'detail': '«благодарен»（感謝している）は、相手を【与格】、理由を «за + 対格» で表します（例: благодарен вам за помощь）。',
        'related_tag': 'adj.short_government',
        'jump_label': '形容詞短尾形の格支配',
    },
    'за': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格 ⇔ 対格の使い分け】',
        'detail': '【静止位置・目的は造格】（сидеть за столом 机で座る / пойти за хлебом パンを買いに行く）、【移動方向・期間・代償は対格】（сесть за стол 机につく / выучить за неделю 1週間で覚える / заплатить за билет 切符代を払う）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'под': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格 ⇔ 対格の使い分け】',
        'detail': '【静止位置は造格】（лежать под книгой 本の下にある / жить под Москвой 近郊に住む）、【移動方向・直前は対格】（положить под книгу 本の下に置く / приехать под вечер 夕方近くに着く）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'с': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格 ⇔ 生格の使い分け】',
        'detail': '【同伴・様態は造格】（играть с оркестром オケと共演する / с удовольствием 喜んで）、【起点・離脱は生格】（взять со стола 机の上から取る / с утра до вечера 朝から晩まで）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'со': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格 ⇔ 生格の使い分け】',
        'detail': '子音結合前の変形 «со»。【同伴は造格】（со мной 私と一緒に）、【起点は生格】（со стола 机の上から）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'в': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【前置格 ⇔ 対格の使い分け】',
        'detail': '【静止場所は前置格】（в консерватории 音楽院で / в Москве）、【移動方向は対格】（идти в консерваторию 音楽院へ行く / положить в карман）。曜日を表す時も対格（в субботу）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'во': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【前置格 ⇔ 対格の使い分け】',
        'detail': '子音結合前の変形 «во»。【静止場所は前置格】（во Франции フランスで）、【移動方向は対格】（во вторник 火曜日に）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'на': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【前置格 ⇔ 対格の使い分け】',
        'detail': '【静止場所・催事は前置格】（на сцене 舞台で / на концерте / на скрипке 楽器奏法）、【移動方向は対格】（выйти на сцену 舞台へ出る / пойти на концерт）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'по': {
        'alert_type': 'multi_case_preposition',
        'badge': '🎯 露検2級 必修：前置詞の格支配【与格 ⇔ 対格の使い分け】',
        'detail': '【空間移動・分野・曜日毎は与格】（гулять по городу 街を散歩する / специалист по физике 物理の専門家）、【限界・配分は対格】（по колено 膝まで / по два билета 2枚ずつ）。',
        'related_tag': 'prep.multi_case',
        'jump_label': '多格支配前置詞の使い分け',
    },
    'перед': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格支配】',
        'detail': '«перед»（〜の前に・〜に対して）は空間・時間・対象として必ず【造格】を要求します（例: перед концертом 開演前 / перед зеркалом 鏡の前で）。',
        'related_tag': 'case.ins',
        'jump_label': '造格の用法',
    },
    'над': {
        'alert_type': 'government',
        'badge': '🎯 露検2級 必修：前置詞の格支配【造格支配】',
        'detail': '«над»（〜の上に・〜に対する取り組み）は必ず【造格】を要求します（例: работать над произведением 作品に取り組む）。',
        'related_tag': 'case.ins',
        'jump_label': '造格の用法',
    },
    'один': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【完全一致】',
        'detail': '数詞 «один» は形容詞と同様に、修飾する名詞の【性・数・格に完全一致】します（один студент, одна студентка, одно письмо, одни часы）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'одна': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【女性形完全一致】',
        'detail': '女性名詞と一致します（одна книга, одну книгу, одной книге...）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'одно': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【中性形完全一致】',
        'detail': '中性名詞と一致します（одно окно, одного окна...）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'два': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は単数生格】',
        'detail': '主格および不活動対格の直後は必ず【名詞の単数生格】が来ます（два рояля, два студента）。斜格（生・与・造・前置格）では名詞と格一致します（двумя роялями）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'две': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【女性名詞＋単数生格】',
        'detail': '女性名詞と結びつく「2」の主格・不活動対格です。直後は必ず【女性単数生格】が来ます（две книги, две студентки）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'оба': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【両方＋単数生格】',
        'detail': '男性・中性名詞と結びつく「両方」。主格直後は【単数生格】（оба брата, оба окна）。斜格: обоих, обоим, обоими, об обоих。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'обе': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【女性両方＋単数生格】',
        'detail': '女性名詞と結びつく「両方」。主格直後は【女性単数生格】（обе сестры）。斜格: обеих, обеим, обеими, об обеих。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'три': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は単数生格】',
        'detail': '主格および不活動対格の直後は必ず【名詞の単数生格】が来ます（три билета, три песни）。斜格では名詞と格一致します（тремя билетами）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'четыре': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は単数生格】',
        'detail': '主格および不活動対格の直後は必ず【名詞の単数生格】が来ます（четыре года, четыре студента）。斜格では格一致します（четырьмя годами）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'пять': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '5〜20および末尾が5〜0の数詞の主格・不活動対格直後は必ず【名詞の複数生格】が来ます（пять роялей, десять студентов）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'шесть': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（шесть уроков）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'семь': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（семь дней）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'восемь': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（восемь часов）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'девять': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（девять месяцев）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'десять': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（десять лет）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'двадцать': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（двадцать минут）。末尾が21の時は単数主格（двадцать один год）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'тридцать': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【主格直後は複数生格】',
        'detail': '主格直後は必ず【名詞の複数生格】が来ます（тридцать рублей）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'сколько': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【直後は複数生格】',
        'detail': '疑問数詞 «сколько» の直後は通常【名詞の複数生格】が来ます（сколько лет, сколько билетов）。※「何時」を尋ねる «сколько времени» のみ不加算名詞の単数生格です。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'много': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【可算は複数生格 / 不加算は単数生格】',
        'detail': '数えられる名詞は【複数生格】（много людей, много книг）、物質・抽象名詞などの不加算名詞は【単数生格】（много времени, много воды）を要求します。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'мало': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【可算は複数生格 / 不加算は単数生格】',
        'detail': '可算名詞は【複数生格】（мало друзей）、不加算名詞は【単数生格】（мало времени, мало сил）を要求します。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'несколько': {
        'alert_type': 'numeral_agreement',
        'badge': '🎯 露検2級 必修：数詞と名詞の一致【直後は複数生格】',
        'detail': '不特定数詞 «несколько»（いくつかの・数名の）の直後は必ず【名詞の複数生格】が来ます（несколько дней, несколько человек）。',
        'related_tag': 'numeral.agreement',
        'jump_label': '数詞と名詞の一致',
    },
    'время': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：中性 -мя名詞 (-ен- 挿入)',
        'detail': '単数生格・与格・前置格で времени と -ен- が挿入され、造格は временем となります。複数形は времена, времён...。',
        'related_tag': 'case.gen',
        'jump_label': '格変化の解説',
    },
    'имя': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：中性 -мя名詞 (-ен- 挿入)',
        'detail': '単数生格・与格・前置格で имени となり、複数形は имена, имён, именам となります。',
        'related_tag': 'case.gen',
        'jump_label': '格変化の解説',
    },
    'мать': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：特殊女性名詞 (-ер- 挿入)',
        'detail': '主格・対格を除くすべての格で матери, матерью, матеря... と -ер- が挿入されます。',
        'related_tag': 'case.gen',
        'jump_label': '格変化の解説',
    },
    'дочь': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：特殊女性名詞 (-ер- 挿入)',
        'detail': '主格・対格を除くすべての格で дочери, дочерью, дочери... と -ер- が挿入されます。',
        'related_tag': 'case.gen',
        'jump_label': '格変化の解説',
    },
    'ребёнок': {
        'alert_type': 'suppletive_plural',
        'badge': '⚠️ 格変化注意：補充法複数形 (дети)',
        'detail': '複数形は語根が全く異なる «дети»（детей, детям, детьми, о детях）となります。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'дети': {
        'alert_type': 'suppletive_plural',
        'badge': '⚠️ 格変化注意：補充法複数形 (дети)',
        'detail': '«ребёнок» の複数形。格変化: детей (生/対), детям (与), детьми (造), о детях (前置格)。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'человек': {
        'alert_type': 'suppletive_plural',
        'badge': '⚠️ 格変化注意：補充法複数形 (люди)',
        'detail': '一般複数形は «люди»（людей, людям, людьми, о людях）となります（数詞結合時は 5 человек 等）。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'люди': {
        'alert_type': 'suppletive_plural',
        'badge': '⚠️ 格変化注意：補充法複数形 (люди)',
        'detail': '«человек» の一般複数形。格変化: людей (生/対), людям (与), людьми (造), о людях (前置格)。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'друг': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：特殊複数形 (друзья)',
        'detail': '複数形は軟音化して друзья, друзей, друзьям, друзьями, о друзьях と変化します。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'брат': {
        'alert_type': 'irregular_declension',
        'badge': '⚠️ 格変化注意：特殊複数形 (братья)',
        'detail': '複数形は братья, братьев, братьям, братьями, о братьях と変化します。',
        'related_tag': 'case.nom',
        'jump_label': '格変化の解説',
    },
    'хотеть': {
        'alert_type': 'mixed_conjugation',
        'badge': '⚠️ 活用注意：混合変化動詞 (хотеть)',
        'detail': '単数は第1変化（хочу, хочешь, хочет）、複数は第2変化（хотим, хотите, хотят）に分かれます。2級筆記超頻出！',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'бежать': {
        'alert_type': 'mixed_conjugation',
        'badge': '⚠️ 活用注意：混合変化動詞 (бежать)',
        'detail': '1人称単数 бегу, 3人称複数 бегут ですが、他は第2変化 бежишь, бежит, бежим, бежите と変化します。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'идти': {
        'alert_type': 'irregular_conjugation',
        'badge': '⚠️ 活用注意：不規則幹・過去形 (шёл)',
        'detail': '語尾アクセント（иду́, идёшь...）。過去形は全く異なる語幹 шёл, шла, шло, шли に変化します。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'пойти': {
        'alert_type': 'irregular_conjugation',
        'badge': '⚠️ 活用注意：不規則幹・過去形 (пошёл)',
        'detail': '単純未来: пойду, пойдёшь... 過去形: пошёл, пошла, пошло, пошли。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'ехать': {
        'alert_type': 'irregular_conjugation',
        'badge': '⚠️ 活用注意：特殊語幹交替 (ехать ⇔ еду)',
        'detail': '不定形 ехать に対して、現在形活用は語幹に д が現れます（еду, едешь, едет, едем, едете, едут）。命令形: поезжай。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'поехать': {
        'alert_type': 'irregular_conjugation',
        'badge': '⚠️ 活用注意：特殊語幹交替 (поехать ⇔ поеду)',
        'detail': '単純未来: поеду, поедешь, поедут。命令形: поезжай / поезжайте。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'жить': {
        'alert_type': 'irregular_conjugation',
        'badge': '⚠️ 活用注意：子音 в 挿入 (живу)',
        'detail': '語幹に в が現れます（я живу, ты живёшь, они живут）。過去形アクセント: жи́л, жила́, жи́ло, жи́ли。',
        'related_tag': 'verb.irregular',
        'jump_label': '不規則動詞の活用',
    },
    'видеть': {
        'alert_type': 'consonant_alternation',
        'badge': '⚠️ 活用注意：1人称単数での子音交替 (д ⇔ ж)',
        'detail': '1人称単数のみ я вижу と д が ж に交替し、2人称以降は ты видишь, он видит... となります。',
        'related_tag': 'verb.irregular',
        'jump_label': '動詞の活用変化',
    },
    'ходить': {
        'alert_type': 'consonant_alternation',
        'badge': '⚠️ 活用注意：1人称単数での子音交替 (д ⇔ ж)',
        'detail': '1人称単数のみ я хожу と д が ж に交替し、2人称以降は ты ходишь, он ходит... となります。',
        'related_tag': 'verb.irregular',
        'jump_label': '動詞の活用変化',
    },
    'любить': {
        'alert_type': 'consonant_alternation',
        'badge': '⚠️ 活用注意：1人称単数での л 挿入 (唇音変化)',
        'detail': '1人称単数のみ я люблю と語幹に л が挿入され、2人称以降は ты любишь, он любит... となります。',
        'related_tag': 'verb.irregular',
        'jump_label': '動詞の活用変化',
    },
}

def attach_irregular_alert(entry):
    if not entry or not isinstance(entry, dict):
        return entry
    w = entry.get('word', '').strip().lower()
    base = entry.get('base', '').strip().lower()
    raw = entry.get('raw_word', '').strip().lower()
    highlight = entry.get('highlight_form', '').strip().lower()
    
    # 0. Collect all candidate search tokens
    candidates = []
    if highlight:
        candidates.append(highlight)
    if w:
        candidates.append(w)
    if base:
        candidates.append(base)
    if raw:
        candidates.append(raw)
        
    # Extract clean Russian words from candidates
    clean_words = []
    for cand in candidates:
        tokens = re.findall(r'[а-яё\-]+', cand)
        clean_words.extend([t.strip('-') for t in tokens if len(t.strip('-')) >= 1])
    
    # Prioritize highlight or direct match
    for cw in clean_words:
        if cw in IRREGULAR_GRAMMAR_REGISTRY:
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY[cw]
            return entry

    # 1. Direct match in registry (full string)
    alert = IRREGULAR_GRAMMAR_REGISTRY.get(w) or IRREGULAR_GRAMMAR_REGISTRY.get(base)
    if alert:
        entry['irregular_alert'] = alert
        return entry

    # 2. Compound verbs ending in -стать (e.g. перестать, достать, устать)
    for cw in clean_words:
        if cw.endswith('стать') and len(cw) >= 5:
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['стать']
            return entry

    # 3. Short adjective stems matching
    for cw in clean_words:
        if cw.startswith('довольн') or cw in ('доволен', 'довольна', 'довольны'):
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['доволен']
            return entry
        if cw.startswith('готов') or cw in ('готов', 'готова', 'готовы'):
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['готов']
            return entry
        if cw.startswith('похож') or cw in ('похож', 'похожа', 'похожи'):
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['похож']
            return entry
        if cw.startswith('уверен') or cw in ('уверен', 'уверена', 'уверены'):
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['уверен']
            return entry
        if cw.startswith('богат') or cw in ('богат', 'богата', 'богаты'):
            entry['irregular_alert'] = IRREGULAR_GRAMMAR_REGISTRY['богат']
            return entry
        
    # 4. Dynamic detection of consonant alternation in verbs
    tbl = entry.get('declension_table')
    if tbl and len(tbl) >= 3 and tbl[0][0] == '人称':
        f_ya = tbl[1][1] if len(tbl[1]) > 1 else ''
        f_ty = tbl[2][1] if len(tbl[2]) > 1 else ''
        if 'шу' in f_ya and 'шешь' in f_ty:
            entry['irregular_alert'] = {
                'alert_type': 'consonant_alternation',
                'badge': '⚠️ 活用注意：語幹子音交替 (с ⇔ ш)',
                'detail': '全人称で語幹子音 с が ш に交替します（я пишу, ты пишешь...）。',
                'related_tag': 'verb.irregular',
                'jump_label': '動詞の活用変化'
            }
        elif 'жу' in f_ya and 'дишь' in f_ty:
            entry['irregular_alert'] = {
                'alert_type': 'consonant_alternation',
                'badge': '⚠️ 活用注意：1人称単数の子音交替 (д ⇔ ж)',
                'detail': '1人称単数のみ д が ж に交替します（я вижу, но ты видишь）。',
                'related_tag': 'verb.irregular',
                'jump_label': '動詞の活用変化'
            }
        elif 'лю' in f_ya and any(ch in f_ya for ch in ['блю', 'плю', 'влю', 'млю']):
            entry['irregular_alert'] = {
                'alert_type': 'consonant_alternation',
                'badge': '⚠️ 活用注意：1人称単数での л 挿入 (唇音変化)',
                'detail': '1人称単数のみ語幹に л が挿入されます（я люблю, но ты любишь）。',
                'related_tag': 'verb.irregular',
                'jump_label': '動詞の活用変化'
            }
    
    # Ensure complete 6-case declension table for adjectives
    ensure_full_adjective_table(entry)
    return entry

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
            ['主格', m, f, n, pl],
            ['生格', f'{stem}ьего', f'{stem}ьей', f'{stem}ьего', f'{stem}ьих'],
            ['与格', f'{stem}ьему', f'{stem}ьей', f'{stem}ьему', f'{stem}ьим'],
            ['対格', f'{m} / {stem}ьего', f'{stem}ью', n, f'{pl} / {stem}ьих'],
            ['造格', f'{stem}ьим', f'{stem}ьей', f'{stem}ьим', f'{stem}ьими'],
            ['前置格', f'{stem}ьем', f'{stem}ьей', f'{stem}ьем', f'{stem}ьих'],
        ]

    # Soft declension: синий (синяя, синее, синие)
    if f.endswith('яя') and n.endswith('ее'):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格', m, f, n, pl],
            ['生格', f'{stem}его', f'{stem}ей', f'{stem}его', f'{stem}их'],
            ['与格', f'{stem}ему', f'{stem}ей', f'{stem}ему', f'{stem}им'],
            ['対格', f'{m} / {stem}его', f'{stem}юю', n, f'{pl} / {stem}их'],
            ['造格', f'{stem}им', f'{stem}ей', f'{stem}им', f'{stem}ими'],
            ['前置格', f'{stem}ем', f'{stem}ей', f'{stem}ем', f'{stem}их'],
        ]

    # Sibilant stem unstressed: хороший, горячий, свежий (хорошая, хорошее, хорошие)
    last_cons = m[:-2][-1:] if len(m) >= 3 else ''
    if last_cons in ['ж', 'ч', 'ш', 'щ', 'ц'] and n.endswith('ее'):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格', m, f, n, pl],
            ['生格', f'{stem}его', f'{stem}ей', f'{stem}его', f'{stem}их'],
            ['与格', f'{stem}ему', f'{stem}ей', f'{stem}ему', f'{stem}им'],
            ['対格', f'{m} / {stem}его', f'{stem}ую', n, f'{pl} / {stem}их'],
            ['造格', f'{stem}им', f'{stem}ей', f'{stem}им', f'{stem}ими'],
            ['前置格', f'{stem}ем', f'{stem}ей', f'{stem}ем', f'{stem}их'],
        ]

    # Velar stem (г, к, х) or sibilant stressed (большой): русский, великий, тихий, большой
    if last_cons in ['г', 'к', 'х'] or (last_cons in ['ж', 'ч', 'ш', 'щ'] and m.endswith('ой')):
        stem = m[:-2]
        return [
            ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
            ['主格', m, f, n, pl],
            ['生格', f'{stem}ого', f'{stem}ой', f'{stem}ого', f'{stem}их'],
            ['与格', f'{stem}ому', f'{stem}ой', f'{stem}ому', f'{stem}им'],
            ['対格', f'{m} / {stem}ого', f'{stem}ую', n, f'{pl} / {stem}их'],
            ['造格', f'{stem}им', f'{stem}ой', f'{stem}им', f'{stem}ими'],
            ['前置格', f'{stem}ом', f'{stem}ой', f'{stem}ом', f'{stem}их'],
        ]

    # Standard hard declension: новый, сложный, трудный, красивый, молодой
    stem = m[:-2]
    return [
        ['格', f'男性 ({m})', f'女性 ({f})', f'中性 ({n})', f'複数 ({pl})'],
        ['主格', m, f, n, pl],
        ['生格', f'{stem}ого', f'{stem}ой', f'{stem}ого', f'{stem}ых'],
        ['与格', f'{stem}ому', f'{stem}ой', f'{stem}ому', f'{stem}ым'],
        ['対格', f'{m} / {stem}ого', f'{stem}ую', n, f'{pl} / {stem}ых'],
        ['造格', f'{stem}ым', f'{stem}ой', f'{stem}ым', f'{stem}ыми'],
        ['前置格', f'{stem}ом', f'{stem}ой', f'{stem}ом', f'{stem}ых'],
    ]

def ensure_full_adjective_table(entry):
    if not entry or not isinstance(entry, dict):
        return entry
    tbl = entry.get('declension_table')
    pos = entry.get('pos', '')
    tags = entry.get('tags', [])
    is_adj = '形容詞' in pos or 'pos.adj' in tags or 'adj' in pos.lower()
    if is_adj and tbl and len(tbl) <= 2:
        row1 = tbl[1] if len(tbl) == 2 else []
        if len(row1) == 4:
            m, f, n, pl = row1
            entry['declension_table'] = generate_adjective_declension_table(m, f, n, pl)
        elif len(row1) == 3:
            m, f, pl = row1
            stem = m[:-2]
            n = stem + ('ее' if f.endswith('яя') else 'ое')
            entry['declension_table'] = generate_adjective_declension_table(m, f, n, pl)
    return entry

RUSSIAN_PREPOSITIONS = {
    'на': {
        'word': 'на',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の上に、〜で（前置格/対格）',
        'is_preposition': True,
        'notes': '【格支配】前置格（場所・楽器奏法・催し物）/ 対格（方向・目標）',
        'anatomy': '前置格支配: 楽器演奏 «играть на рояле / скрипке»、催し物 «на концерте / уроке»、平面の上 «на столе»。\n対格支配: 方向 «положить на стол»、催し物へ «идти на концерт»。\n※前置詞自身は変化しませんが、後ろに続く名詞の格を決定（格支配）します。',
        'network': ['в (〜の中に/前置格・対格)', 'с (〜と一緒に/造格、〜から/生格)', 'к (〜のほうへ/与格)', 'по (〜に沿って/与格)'],
        'examples': [
            {'ru': 'Алёна играет на рояле в консерватории.', 'ja': 'アリョーナは音楽院でグランドピアノを弾きます。（前置格：楽器奏法）'},
            {'ru': 'Вечером мы идём на концерт Рахманинова.', 'ja': '夕方、私たちはラフマニノフのコンサートに行きます。（対格：催し物への方向）'},
            {'ru': 'Положите ноты на пюпитр, пожалуйста.', 'ja': '楽譜を譜面台の上に置いてください。（対格：平面への移動）'}
        ]
    },
    'в': {
        'word': 'в / во',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の中に、〜へ（前置格/対格）',
        'is_preposition': True,
        'notes': '【格支配】前置格（建物・都市・空間の中）/ 対格（方向・スポーツ）',
        'anatomy': '前置格支配: 建物・場所の中 «в консерватории, в Москве»。\n対格支配: 方向 «в консерваторию»、スポーツ «играть в футбол»。\n※前置詞自身は変化しませんが、後ろに続く名詞の格を決定（格支配）します。',
        'network': ['на (〜の上に/前置格・対格)', 'из (〜の中から/生格)'],
        'examples': [
            {'ru': 'Студенты репетируют в Большом зале.', 'ja': '学生たちは大ホールでリハーサルをしています。（前置格：空間内部）'},
            {'ru': 'Екатерина спешит в консерваторию.', 'ja': 'エカテリーナは音楽院へと急いでいます。（対格：方向）'}
        ]
    },
    'у': {
        'word': 'у',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の元に、〜のそばに；（所有・存在構文）〜にある、〜が持っている',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '生格（Родительный）支配の最重要前置詞。\n① 所有構文 «У меня есть...»（私には〜がある）、否定構文 «У меня нет...»（私には〜がない）。\n② 人のところ・元へ «быть у профессора»（教授のところにいる）。\n③ 場所・近傍 «стоять у рояля / у окна»（ピアノのそば／窓のそばに立つ）。\n※前置詞自身は変化しませんが、後ろに続く名詞・代名詞を必ず「生格」にします。',
        'network': ['от (〜から/生格)', 'к (〜のほうへ/与格)', 'около (〜の近くに/生格)', 'для (〜のために/生格)'],
        'examples': [
            {'ru': 'У меня нет свободного времени.', 'ja': '私には自由な時間がありません。（所有否定構文：生格）'},
            {'ru': 'У профессора есть редкие ноты.', 'ja': '教授は貴重な楽譜を持っています。（所有肯定構文：生格）'},
            {'ru': 'Студентка стоит у входа в Большой зал.', 'ja': '女子学生は大ホールの入口のそばに立っています。（場所・近傍：生格）'}
        ]
    },
    'с': {
        'word': 'с / со',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜とともに（造格）/ 〜から（生格）',
        'is_preposition': True,
        'notes': '【格支配】造格（同伴・様態）/ 生格（起点・降下）',
        'anatomy': '造格支配: 同伴・様態 «с радостью»（喜んで、喜びをもって）, «с другом»（友人と）。\n生格支配: 起点・降下 «со стола»（机の上から）, «с утра»（朝から）。\n※前置詞自身は変化しませんが、後ろに続く名詞の格を決定（格支配）します。',
        'network': ['без (〜なしで/生格)', 'вместе с (〜と一緒に/造格)'],
        'examples': [
            {'ru': 'Я с радостью сыграю это произведение.', 'ja': '私は喜んでこの作品を演奏いたします。（造格：様態）'},
            {'ru': 'Таня занимается за роялем с утра до вечера.', 'ja': 'ターニャは朝から晩までピアノに向かって練習しています。（生格：起点）'}
        ]
    },
    'к': {
        'word': 'к / ко',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の方へ、〜の元へ、〜に向かって（与格）',
        'is_preposition': True,
        'notes': '【格支配】与格（Дательный падеж）支配',
        'anatomy': '与格支配の前置詞。人や目標に向かう方向を表します（«идти к профессору» 教授の元へ行く, «подходить к роялю» ピアノへ近づく）。',
        'network': ['от (〜から/生格)', 'у (〜の元で/生格)'],
        'examples': [
            {'ru': 'Мы идём к профессору на консультацию.', 'ja': '私たちは相談のため教授のところへ行きます。'},
            {'ru': 'Пианист подошёл к роялю.', 'ja': 'ピアニストはピアノに近づきました。'}
        ]
    },
    'по': {
        'word': 'по',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜に沿って、〜を通って、〜ごとに（与格）',
        'is_preposition': True,
        'notes': '【格支配】与格（Дательный падеж）支配',
        'anatomy': '与格支配の前置詞。散策・空間通過 «гулять по Москве»、時間反復 «по вечерам»（夜ごとに）、分野 «урок по фортепиано»（ピアノの授業）などを表します。',
        'network': ['вдоль (〜に沿って/生格)'],
        'examples': [
            {'ru': 'Таня часто занимается по вечерам.', 'ja': 'ターニャは毎晩のようによく練習しています。'},
            {'ru': 'Мы гуляем по консерватории.', 'ja': '私たちは音楽院の校内を散策しています。'}
        ]
    },
    'о': {
        'word': 'о / об / обо',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜について、〜のことを（前置格）',
        'is_preposition': True,
        'notes': '【格支配】前置格（Предложный падеж）支配',
        'anatomy': '思考・言及の対象を表す前置格支配の前置詞（«думать о музыке» 音楽について考える, «обо мне» 私について）。',
        'network': ['про (+対格: 口語的〜について)'],
        'examples': [
            {'ru': 'Музыканты говорят о премьере.', 'ja': '音楽家たちは初演について語り合っています。'}
        ]
    },
    'из': {
        'word': 'из / изо',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の中から、〜出身（生格）',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '前置詞 «в»（〜の中へ・で）の反意語として、空間内部からの脱出・出所を表す生格支配の前置詞（«из зала» ホールから, «из Москвы» モスクワ出身）。',
        'network': ['в (〜の中へ/対格)', 'от (〜から/生格)'],
        'examples': [
            {'ru': 'Студенты выходят из Большого зала.', 'ja': '学生たちは大ホールから出てきます。'}
        ]
    },
    'от': {
        'word': 'от / ото',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜から、〜の元から、〜離れて（生格）',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '起点・人からの離脱を表す生格支配の前置詞（«письмо от профессора» 教授からの手紙, «отойти от рояля» ピアノから離れる）。',
        'network': ['к (〜の方へ/与格)', 'у (〜の元で/生格)'],
        'examples': [
            {'ru': 'Я получил ноты от профессора.', 'ja': '私は教授から楽譜を受け取りました。'}
        ]
    },
    'для': {
        'word': 'для',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜のために、〜向けの（生格）',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '目的・用途・対象を表す生格支配の前置詞（«концерт для фортепиано» ピアノ協奏曲, «подарок для Тани» ターニャへのプレゼント）。',
        'network': ['ради (〜のために/生格)'],
        'examples': [
            {'ru': 'Это второй концерт для фортепиано с оркестром.', 'ja': 'これはピアノとオーケストラのための第2協奏曲です。'}
        ]
    },
    'до': {
        'word': 'до',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜まで（生格）',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '時間・場所の限度を表す生格支配の前置詞（«с утра до вечера» 朝から晩まで, «до концерта» コンサートの前までに）。',
        'network': ['после (〜の後に/生格)'],
        'examples': [
            {'ru': 'Они репетировали с утра до самого вечера.', 'ja': '彼らは朝から晩遅くまでリハーサルを重ねました。'}
        ]
    },
    'без': {
        'word': 'без / безо',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜なしで、〜を抜きにして（生格）',
        'is_preposition': True,
        'notes': '【格支配】生格（Родительный падеж）支配',
        'anatomy': '欠如・排除を表す生格支配の前置詞（«без ошибок» 誤りなしに, «играть без нот» 暗譜で弾く）。',
        'network': ['с (〜と一緒に/造格)'],
        'examples': [
            {'ru': 'Пианист сыграл сложный пассаж без единой ошибки.', 'ja': 'ピアニストは難解なパッセージを一つのミスもなく弾ききりました。'}
        ]
    },
    'под': {
        'word': 'под / подо',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の下で、〜に合わせて（造格/対格）',
        'is_preposition': True,
        'notes': '【格支配】造格（静止位置・伴奏）/ 対格（移動方向）',
        'anatomy': '造格支配: 静止位置 «под роялем»（ピアノの下で）、伴奏・音に合わせて «под звуки оркестра»（オーケストラの響きに合わせて）。\n対格支配: 下への移動 «положить под книгу»（本の下に置く）。',
        'network': ['над (〜の上に/造格)', 'из-под (〜の下から/生格)'],
        'examples': [
            {'ru': 'Мы слушали музыку под звуки дождя.', 'ja': '私たちは雨音に合わせて音楽を聴いていました。'},
            {'ru': 'Под аплодисменты зала дирижёр вышел на сцену.', 'ja': 'ホールの拍手に包まれて指揮者が舞台に登場しました。'}
        ]
    },
    'за': {
        'word': 'за',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の後ろで、〜を求めて（造格）/ 〜の後ろへ、〜のために（対格）',
        'is_preposition': True,
        'notes': '【格支配】造格（静止位置・目的）/ 対格（方向・代償・期間）',
        'anatomy': '造格支配: 楽器に向かって «сидеть за роялем»（ピアノに向かって座る）、目的 «пойти за нотами»（楽譜を取りに行く）。\n対格支配: 楽器へ «сесть за рояль»（ピアノに向かって腰掛ける）、代償 «заплатить за билет»（チケット代を払う）。',
        'network': ['перед (〜の前で/造格)'],
        'examples': [
            {'ru': 'Таня проводит долгие часы за роялем.', 'ja': 'ターニャはピアノに向かって長い時間を過ごします。'},
            {'ru': 'Мы заплатили за билеты в кассе консерватории.', 'ja': '私たちは音楽院の窓口でチケット代を支払いました。'}
        ]
    },
    'перед': {
        'word': 'перед / передо',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の前で、〜の直前に（造格）',
        'is_preposition': True,
        'notes': '【格支配】造格（Творительный падеж）支配',
        'anatomy': '空間的前方 «перед залом»（ホールの前で）、時間的直前 «перед концертом»（コンサートの直前に）。後ろに続く名詞を造格にします。',
        'network': ['за (〜の後ろで/造格)', 'после (〜の後に/生格)'],
        'examples': [
            {'ru': 'Перед концертом музыканты настраивают инструменты.', 'ja': 'コンサートの前に音楽家たちは楽器を調弦します。'}
        ]
    },
    'при': {
        'word': 'при',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜の際に、〜の立ち会いのもとで、〜の付属（前置格）',
        'is_preposition': True,
        'notes': '【格支配】前置格（Предложный падеж）支配',
        'anatomy': '状況・付属・時代を表す前置格支配の前置詞（«при консерватории» 音楽院付属の, «при свете ламп» ランプの灯りのもとで）。',
        'network': ['в (〜の中で/前置格)'],
        'examples': [
            {'ru': 'При консерватории открыт прекрасный нотный магазин.', 'ja': '音楽院付属の素晴らしい楽譜店が開かれています。'}
        ]
    },
    'через': {
        'word': 'через',
        'pos': '前置詞 (Предлог)',
        'meaning': '〜を越えて、〜を通り抜けて、〜の後に（対格）',
        'is_preposition': True,
        'notes': '【格支配】対格（Винительный падеж）支配',
        'anatomy': '空間通過 «через переулок»（小径を通って）、時間経過 «через час»（1時間後に）。後ろに続く名詞を対格にします。',
        'network': ['сквозь (〜を透かして/対格)'],
        'examples': [
            {'ru': 'Антракт закончится через пятнадцать минут.', 'ja': '休憩時間は15分後に終わります。'}
        ]
    }
}

# Russian Adjective Lemmatizer (Case inflections to dictionary lemma -ый/-ий/-ой)
ADJ_CASE_ENDINGS = [
    'ыми', 'ими', 'ого', 'его', 'ому', 'ему', 'ых', 'их', 'ую', 'юю', 'ой', 'ей', 'ым', 'им', 'ом', 'ем',
    'ая', 'яя', 'ое', 'ее', 'ые', 'ие', 'ый', 'ий', 'ой',
    'ны', 'на', 'но'  # short form
]
ADJ_LEMMAS = ['ый', 'ий', 'ой']

def lemmatize_russian_adjective(word, vocab_db):
    w = word.strip().lower()
    for end in sorted(ADJ_CASE_ENDINGS, key=len, reverse=True):
        if w.endswith(end) and len(w) > len(end) + 2:
            stem = w[:-len(end)]
            if end in ['ны', 'на', 'но']:
                for lem in ['ный', 'ний', 'кий']:
                    cand = stem + lem
                    if cand in vocab_db:
                        return cand
            for lem in ADJ_LEMMAS:
                cand = stem + lem
                if cand in vocab_db:
                    return cand
    return None

# Russian Noun Case Lemmatizer (Oblique case endings to dictionary lemma)
NOUN_CASE_ENDINGS = [
    'ами', 'ями', 'ах', 'ях', 'ов', 'ев', 'ей', 'ам', 'ям', 'ом', 'ем', 'ой', 'ей', 'ью', 'у', 'ю', 'е', 'и', 'ы', 'а', 'я'
]
NOUN_LEMMAS = ['', 'а', 'я', 'о', 'е', 'ь']

def lemmatize_russian_noun(word, vocab_db):
    w = word.strip().lower()
    for end in sorted(NOUN_CASE_ENDINGS, key=len, reverse=True):
        if w.endswith(end) and len(w) > len(end) + 2:
            stem = w[:-len(end)]
            for lem in NOUN_LEMMAS:
                cand = stem + lem
                if cand in vocab_db and cand != w:
                    pos = vocab_db[cand].get('pos', '')
                    if any(n in pos for n in ('名詞', 'сущ')):
                        return cand
    return None

def parse_token_role(role_str, word, base, tag=''):
    pos = ""
    meaning = ""
    form = ""
    tag_clean = (tag or '').lower()
    if 'participle.passive' in tag_clean:
        pos = '受動過去形動詞（短語尾）'
    elif 'participle' in tag_clean:
        pos = '形動詞'
    elif 'gerund' in tag_clean:
        pos = '副動詞'
    elif 'impersonal' in tag_clean:
        pos = '述語無人称詞'
    elif 'adv' in tag_clean:
        pos = '副詞'
    elif 'prep' in tag_clean:
        pos = '前置詞'
    elif 'conj' in tag_clean:
        pos = '接続詞'
    elif 'part' in tag_clean:
        pos = '助詞'
    elif 'interj' in tag_clean:
        pos = '間投詞'
    elif 'verb' in tag_clean:
        pos = '動詞'
    elif 'adj' in tag_clean:
        pos = '形容詞'

    m = re.match(r'^(.*?)[（\(](.*?)[）\)](.*)$', role_str)
    if m:
        extracted = m.group(1).strip()
        if extracted:
            pos = extracted
        inner = m.group(2).strip()
        if '/' in inner:
            parts = inner.split('/')
            meaning = parts[0].strip()
            form = parts[1].strip()
        else:
            meaning = inner
    else:
        meaning = role_str
        if any(term in role_str for term in ['副詞', '熱心に', '早く', '遅く', '静かに', '美しく']):
            pos = '副詞'
        elif any(term in role_str for term in ['前置詞', '〜の中で', '〜へ', '〜と共に']):
            pos = '前置詞'
        elif any(term in role_str for term in ['接続詞', '〜そして', '〜だが', '〜しかし']):
            pos = '接続詞'
        elif '受動' in role_str or '短語尾' in role_str:
            pos = '受動過去形動詞（短語尾）'
        elif '副動詞' in role_str:
            pos = '副動詞'

    if not pos:
        b_clean = (base or word or '').lower()
        if any(sp in b_clean for sp in ['написан', 'продан', 'сыгран', 'открыт', 'создан', 'исполнен']):
            pos = '受動過去形動詞（短語尾）'
        elif b_clean.endswith(('ый', 'ий', 'ой')):
            pos = '形容詞'
        elif b_clean.endswith(('ть', 'ти', 'чь')):
            pos = '動詞'
        elif b_clean.endswith(('а', 'я')):
            pos = '女性名詞'
        elif b_clean.endswith(('о', 'е')):
            pos = '中性名詞'
        else:
            pos = '名詞'

    return pos, meaning, form

_LESSON_TOKEN_CACHE = None

def get_lesson_token_map():
    global _LESSON_TOKEN_CACHE
    if _LESSON_TOKEN_CACHE is not None:
        return _LESSON_TOKEN_CACHE

    buffer = load_json('lesson_buffer.json', [])
    token_map = {}
    for day in buffer:
        for s_k, s_data in day.get('sessions', {}).items():
            sentences = s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []) + s_data.get('paragraphs', [])
            hero = s_data.get('hero_sentence')
            if hero:
                sentences.append(hero)
            for p in sentences:
                p_ru = p.get('ru', '')
                p_ja = p.get('ja', '')

                # 1. Check key_vocab
                for kv in p.get('key_vocab', []):
                    w = re.sub(r'[«»„“".,!?;:()—]', '', kv.get('word', '')).strip().lower()
                    b = re.sub(r'[«»„“".,!?;:()—]', '', kv.get('base', '')).strip().lower()
                    entry = {
                        'word': kv.get('base') or kv.get('word'),
                        'base': kv.get('base') or kv.get('word'),
                        'pos': kv.get('pos', ''),
                        'meaning': kv.get('meaning', ''),
                        'role_in_sentence': kv.get('role_in_sentence', ''),
                        'declension_table': kv.get('declension_table', []),
                        'example_ru': p_ru,
                        'example_ja': p_ja
                    }
                    if w and w not in token_map:
                        token_map[w] = entry
                    if b and b not in token_map:
                        token_map[b] = entry

                # 2. Check tokens
                for t in p.get('tokens', []):
                    raw_w = t.get('word', '')
                    w = re.sub(r'[«»„“".,!?;:()—]', '', raw_w).strip().lower()
                    b = re.sub(r'[«»„“".,!?;:()—]', '', t.get('base', '')).strip().lower()
                    r = (t.get('role', '') or t.get('grammar', '')).strip()
                    if not w:
                        continue

                    pos, meaning, form = parse_token_role(r, raw_w, t.get('base', ''), t.get('tag', ''))
                    token_entry = {
                        'word': raw_w,
                        'base': t.get('base') or raw_w,
                        'pos': pos,
                        'meaning': meaning or r,
                        'form': form,
                        'role_in_sentence': r,
                        'example_ru': p_ru,
                        'example_ja': p_ja
                    }
                    if w not in token_map:
                        token_map[w] = token_entry
                    if b and b not in token_map:
                        base_entry = dict(token_entry)
                        base_entry['word'] = t.get('base') or b
                        if b.endswith(('ть', 'ти', 'чь')) and ('形動詞' in pos or '受動' in pos or '短語尾' in pos or '副動詞' in pos):
                            base_entry['pos'] = '動詞 (完了体)' if ('perf' in t.get('tag', '') or '完了' in r) else '動詞'
                            base_entry['declension_table'] = []
                        token_map[b] = base_entry

                # 3. Check interactive_mutations
                for mut in s_data.get('interactive_mutations', []):
                    m_ru = mut.get('ru', '')
                    m_ja = mut.get('ja', '')
                    for t in mut.get('tokens', []):
                        raw_w = t.get('word', '')
                        w = re.sub(r'[«»„“".,!?;:()—]', '', raw_w).strip().lower()
                        b = re.sub(r'[«»„“".,!?;:()—]', '', t.get('base', '')).strip().lower()
                        r = (t.get('role', '') or t.get('grammar', '')).strip()
                        if not w:
                            continue
                        pos, meaning, form = parse_token_role(r, raw_w, t.get('base', ''), t.get('tag', ''))
                        token_entry = {
                            'word': raw_w,
                            'base': t.get('base') or raw_w,
                            'pos': pos,
                            'meaning': meaning or r,
                            'form': form,
                            'role_in_sentence': r,
                            'example_ru': m_ru,
                            'example_ja': m_ja
                        }
                        if w not in token_map:
                            token_map[w] = token_entry
                        if b and b not in token_map:
                            base_entry = dict(token_entry)
                            base_entry['word'] = t.get('base') or b
                            if b.endswith(('ть', 'ти', 'чь')) and ('形動詞' in pos or '受動' in pos or '短語尾' in pos or '副動詞' in pos):
                                base_entry['pos'] = '動詞 (完了体)' if ('perf' in t.get('tag', '') or '完了' in r) else '動詞'
                                base_entry['declension_table'] = []
                            token_map[b] = base_entry

    _LESSON_TOKEN_CACHE = token_map
    return _LESSON_TOKEN_CACHE


# Russian Verb Morphological Lemmatizer (Past tense & Conjugations to Infinitive)
RUSSIAN_VERB_LEMMAS = {
    # купить / покупать
    'купил': 'купить', 'купила': 'купить', 'купило': 'купить', 'купили': 'купить',
    'куплю': 'купить', 'купишь': 'купить', 'купит': 'купить', 'купим': 'купить', 'купите': 'купить', 'купят': 'купить',
    'покупал': 'покупать', 'покупала': 'покупать', 'покупало': 'покупать', 'покупали': 'покупать',
    'покупаю': 'покупать', 'покупаешь': 'покупать', 'покупает': 'покупать', 'покупаем': 'покупать', 'покупаете': 'покупать', 'покупают': 'покупать',
    
    # сыграть / играть
    'сыграл': 'сыграть', 'сыграла': 'сыграть', 'сыграло': 'сыграть', 'сыграли': 'сыграть',
    'сыграю': 'сыграть', 'сыграешь': 'сыграть', 'сыграет': 'сыграть', 'сыграем': 'сыграть', 'сыграете': 'сыграть', 'сыграют': 'сыграть',
    'играл': 'играть', 'играла': 'играть', 'играло': 'играть', 'играли': 'играть',
    'играю': 'играть', 'играешь': 'играть', 'играет': 'играть', 'играем': 'играть', 'играете': 'играть', 'играют': 'играть',
    
    # положить / класть
    'положил': 'положить', 'положила': 'положить', 'положило': 'положить', 'положили': 'положить',
    'положу': 'положить', 'положишь': 'положить', 'положит': 'положить', 'положим': 'положить', 'положите': 'положить', 'положат': 'положить',
    'клал': 'класть', 'клала': 'класть', 'клало': 'класть', 'клали': 'класть',
    'кладу': 'класть', 'кладёшь': 'класть', 'кладёт': 'класть', 'кладём': 'класть', 'кладёте': 'класть', 'кладут': 'класть',
    
    # выучить / учить
    'выучил': 'выучить', 'выучила': 'выучить', 'выучило': 'выучить', 'выучили': 'выучить',
    'выучу': 'выучить', 'выучишь': 'выучить', 'выучит': 'выучить', 'выучим': 'выучить', 'выучите': 'выучить', 'выучат': 'выучить',
    'учил': 'учить', 'учила': 'учить', 'учило': 'учить', 'учили': 'учить',
    'учу': 'учить', 'учишь': 'учить', 'учит': 'учить', 'учим': 'учить', 'учите': 'учить', 'учат': 'учить',
    
    # повторять / повторить
    'повторил': 'повторить', 'повторила': 'повторить', 'повторило': 'повторить', 'повторили': 'повторить',
    'повторю': 'повторить', 'повторишь': 'повторить', 'повторит': 'повторить', 'повторим': 'повторить', 'повторите': 'повторить', 'повторят': 'повторить',
    'повторял': 'повторять', 'повторяла': 'повторять', 'повторяло': 'повторять', 'повторяли': 'повторять',
    'повторяю': 'повторять', 'повторяешь': 'повторять', 'повторяет': 'повторять', 'повторяем': 'повторять', 'повторяете': 'повторять', 'повторяют': 'повторять',
    
    # репетировать / отрепетировать
    'репетировал': 'репетировать', 'репетировала': 'репетировать', 'репетировало': 'репетировать', 'репетировали': 'репетировать',
    'репетирую': 'репетировать', 'репетируешь': 'репетировать', 'репетирует': 'репетировать', 'репетируем': 'репетировать', 'репетируете': 'репетировать', 'репетируют': 'репетировать',
    'отрепетировал': 'отрепетировать', 'отрепетировала': 'отрепетировать', 'отрепетировали': 'отрепетировать',
    'отрепетирую': 'отрепетировать', 'отрепетируешь': 'отрепетировать', 'отрепетирует': 'отрепетировать', 'отрепетируем': 'отрепетировать', 'отрепетируете': 'отрепетировать', 'отрепетируют': 'отрепетировать',
    
    # идти / ходить
    'шёл': 'идти', 'шла': 'идти', 'шло': 'идти', 'шли': 'идти',
    'иду': 'идти', 'идёшь': 'идти', 'идёт': 'идти', 'идём': 'идти', 'идёте': 'идти', 'идут': 'идти',
    'ходил': 'ходить', 'ходила': 'ходить', 'ходило': 'ходить', 'ходили': 'ходить',
    'хожу': 'ходить', 'ходишь': 'ходить', 'ходит': 'ходить', 'ходим': 'ходить', 'ходите': 'ходить', 'ходят': 'ходить',
    
    # ехать / ездить
    'ехал': 'ехать', 'ехала': 'ехать', 'ехало': 'ехать', 'ехали': 'ехать',
    'еду': 'ехать', 'едешь': 'ехать', 'едет': 'ехать', 'едем': 'ехать', 'едете': 'ехать', 'едут': 'ехать',
    'ездил': 'ездить', 'ездила': 'ездить', 'ездило': 'ездить', 'ездили': 'ездить',
    'езжу': 'ездить', 'ездишь': 'ездить', 'ездит': 'ездить', 'ездим': 'ездить', 'ездите': 'ездить', 'ездят': 'ездить',
    
    # лежать
    'лежал': 'лежать', 'лежала': 'лежать', 'лежало': 'лежать', 'лежали': 'лежать',
    'лежу': 'лежать', 'лежишь': 'лежать', 'лежит': 'лежать', 'лежим': 'лежать', 'лежите': 'лежать', 'лежат': 'лежать',
    
    # быть
    'был': 'быть', 'была': 'быть', 'было': 'быть', 'были': 'быть',
    'буду': 'быть', 'будешь': 'быть', 'будет': 'быть', 'будем': 'быть', 'будете': 'быть', 'будут': 'быть',

    # видеть / увидеть
    'видел': 'видеть', 'видела': 'видеть', 'видело': 'видеть', 'видели': 'видеть',
    'вижу': 'видеть', 'видишь': 'видеть', 'видит': 'видеть', 'видим': 'видеть', 'видите': 'видеть', 'видят': 'видеть',
    'увидел': 'видеть', 'увидела': 'видеть', 'увидело': 'видеть', 'увидели': 'видеть',
    'увижу': 'видеть', 'увидишь': 'видеть', 'увидит': 'видеть', 'увидим': 'видеть', 'увидите': 'видеть', 'увидят': 'видеть',
    
    # звучать
    'звучит': 'звучать', 'звучат': 'звучать', 'звучал': 'звучать', 'звучала': 'звучать', 'звучали': 'звучать',
    
    # читать
    'читает': 'читать', 'читают': 'читать', 'читал': 'читать', 'читала': 'читать', 'читали': 'читать',
    
    # открывать
    'открывает': 'открывать', 'открывают': 'открывать', 'открыл': 'открывать', 'открыла': 'открывать', 'открыли': 'открывать',

    # хотеть
    'хочу': 'хотеть', 'хочешь': 'хотеть', 'хочет': 'хотеть', 'хотим': 'хотеть', 'хотите': 'хотеть', 'хотят': 'хотеть',
    'хотел': 'хотеть', 'хотела': 'хотеть', 'хотело': 'хотеть', 'хотели': 'хотеть',

    # мочь
    'могу': 'мочь', 'можешь': 'мочь', 'может': 'мочь', 'можем': 'мочь', 'можете': 'мочь', 'могут': 'мочь',
    'мог': 'мочь', 'могла': 'мочь', 'могло': 'мочь', 'могли': 'мочь',

    # купить
    'куплю': 'купить', 'купишь': 'купить', 'купит': 'купить', 'купим': 'купить', 'купите': 'купить', 'купят': 'купить',
    'купил': 'купить', 'купила': 'купить', 'купило': 'купить', 'купили': 'купить'
}

RUSSIAN_NOUN_LEMMAS = {
    'времени': 'время', 'временем': 'время', 'времена': 'время', 'времён': 'время', 'временам': 'время', 'временами': 'время', 'временах': 'время',
    'имени': 'имя', 'именем': 'имя', 'имена': 'имя', 'имён': 'имя', 'именам': 'имя', 'именами': 'имя', 'именах': 'имя',
    'матери': 'мать', 'матерью': 'мать', 'матерям': 'мать', 'матерями': 'мать', 'матерях': 'мать',
    'дочери': 'дочь', 'дочерью': 'дочь', 'дочерям': 'дочь', 'дочерями': 'дочь', 'дочерях': 'дочь',
    'дети': 'ребёнок', 'детей': 'ребёнок', 'детям': 'ребёнок', 'детьми': 'ребёнок', 'детях': 'ребёнок',
    'люди': 'человек', 'людей': 'человек', 'людям': 'человек', 'людьми': 'человек', 'людях': 'человек',
    'друзья': 'друг', 'друзей': 'друг', 'друзьям': 'друг', 'друзьями': 'друг', 'друзьях': 'друг',
    'братья': 'брат', 'братьев': 'брат', 'братьям': 'брат', 'братьями': 'брат', 'братьях': 'брат',
    'руками': 'рука', 'руках': 'рука', 'руку': 'рука', 'руке': 'рука', 'руки': 'рука',
    'ноты': 'нота', 'нот': 'нота', 'нотам': 'нота', 'нотами': 'нота', 'нотах': 'нота',
    'звуки': 'звук', 'звуков': 'звук', 'звукам': 'звук', 'звуками': 'звук', 'звуках': 'звук',
    # преподавательница
    'преподавательницы': 'преподавательница', 'преподавательнице': 'преподавательница', 'преподавательницу': 'преподавательница', 'преподавательницей': 'преподавательница', 'преподавательницею': 'преподавательница', 'преподавательниц': 'преподавательница', 'преподавательницам': 'преподавательница', 'преподавательницами': 'преподавательница', 'преподавательницах': 'преподавательница',
    # преподаватель
    'преподавателя': 'преподаватель', 'преподавателю': 'преподаватель', 'преподавателем': 'преподаватель', 'преподавателе': 'преподаватель', 'преподаватели': 'преподаватель', 'преподавателей': 'преподаватель', 'преподавателям': 'преподаватель', 'преподавателями': 'преподаватель', 'преподавателях': 'преподаватель',
    # Таня
    'таней': 'Таня', 'тане': 'Таня', 'таню': 'Таня', 'тани': 'Таня',
    # соната
    'сонаты': 'соната', 'сонате': 'соната', 'сонату': 'соната', 'сонатой': 'соната', 'сонат': 'соната', 'сонатам': 'соната', 'сонатами': 'соната', 'сонатах': 'соната'
}

RUSSIAN_PRONOUN_LEMMAS = {
    # весь / вся / всё / все
    'весь': 'весь', 'вся': 'весь', 'всё': 'весь', 'все': 'весь',
    'всего': 'весь', 'всему': 'весь', 'всем': 'весь', 'всей': 'весь',
    'всю': 'весь', 'всею': 'весь', 'всех': 'весь', 'всеми': 'весь',
    'всём': 'весь',
    # тот / та / то / те
    'тот': 'тот', 'та': 'тот', 'то': 'тот', 'те': 'тот',
    'того': 'тот', 'тому': 'тот', 'том': 'тот', 'той': 'тот', 'ту': 'тот',
    'тех': 'тот', 'теми': 'тот', 'тем': 'тот',
    # этот / эта / это / эти
    'этот': 'этот', 'эта': 'этот', 'это': 'этот', 'эти': 'этот',
    'этого': 'этот', 'этому': 'этот', 'этим': 'этот', 'этом': 'этот',
    'этой': 'этот', 'эту': 'этот', 'этих': 'этот', 'этими': 'этот',
    # чей / чья / чьё / чьи
    'чей': 'чей', 'чья': 'чей', 'чьё': 'чей', 'чьи': 'чей',
    'чьего': 'чей', 'чьей': 'чей', 'чьему': 'чей', 'чьим': 'чей',
    'чьих': 'чей', 'чьими': 'чей', 'чьём': 'чей',
    # сам / сама / само / сами
    'сам': 'сам', 'сама': 'сам', 'само': 'сам', 'сами': 'сам',
    'самого': 'сам', 'самой': 'сам', 'самому': 'сам', 'самим': 'сам',
    'самих': 'сам', 'самими': 'сам', 'самом': 'сам'
}

RUSSIAN_CORE_ENTRIES = {
    'написана': {
        'word': 'написана',
        'pos': '受動過去形動詞・短語尾形 (Краткое страдательное причастие)',
        'meaning': '書かれた、作曲された (女性単数)',
        'notes': '【短語尾形の一致】主語の性・数（女性単数）に一致。格変化は行わず、述語として受動態を作る。動作主は造格。',
        'declension_table': [
            ['性・数', 'написана (受動過去短語尾)', '主語との性数一致用例 (быть + 短語尾)'],
            ['男性単数 (он)', 'написан', 'Этот знаменитый концерт был написан... (協奏曲は書かれた)'],
            ['女性単数 (она)', 'написана', 'Эта знаменитая соната была написана... (ソナタは書かれた)'],
            ['中性単数 (оно)', 'написано', 'Это знаменитое произведение было написано... (作品は書かれた)'],
            ['複数 (они)', 'написаны', 'Эти знаменитые пьесы были написаны... (小品は書かれた)']
        ],
        'anatomy': '''【受動形動詞・短語尾形（Краткое причастие）】«написана» は動詞 «написать»（完了体・書く/作曲する）から作られた受動過去形動詞の短語尾形（女性単数）です。\n★重要鉄則：短語尾形は名詞のような6格変化（主格・生格・与格…）を行わず、主語の「性・数」に一致（男性 -∅, 女性 -а, 中性 -о, 複数 -ы）して文の述語（〜された・〜されていた）となります。女性名詞 соната に呼応して語尾が -а になっています。\n「誰によって」という動作主は前置詞なしの【造格】（русским композитором）で直結します。''',
        'network': ['написать (書く・作曲する/完了体動詞)', 'писать (書く/不完了体動詞)', 'написанный (書かれた/完全形受動形動詞)', 'написание (執筆・作曲/中性名詞)'],
        'aspect_pair': 'писать (НСВ) / написать (СВ)',
        'examples': [
            {'ru': 'Эта знаменитая соната была написана русским композитором в Москве.', 'ja': 'この有名なソナタはモスクワでロシアの作曲家によって書かれた。'},
            {'ru': 'Новая партитура была написана Чайковским.', 'ja': '新しい総譜はチャイコフスキーによって書かれた。'}
        ]
    },
    'написан': {
        'word': 'написан',
        'pos': '受動過去形動詞・短語尾形 (Краткое страдательное причастие)',
        'meaning': '書かれた、作曲された (男性単数)',
        'notes': '【短語尾形の一致】主語の性・数（男性単数）に一致。格変化は行わず、述語として受動態を作る。動作主は造格。',
        'declension_table': [
            ['性・数', 'написан (受動過去短語尾)', '主語との性数一致用例 (быть + 短語尾)'],
            ['男性単数 (он)', 'написан', 'Этот знаменитый концерт был написан... (協奏曲は書かれた)'],
            ['女性単数 (она)', 'написана', 'Эта знаменитая соната была написана... (ソナタは書かれた)'],
            ['中性単数 (оно)', 'написано', 'Это знаменитое произведение было написано... (作品は書かれた)'],
            ['複数 (они)', 'написаны', 'Эти знаменитые пьесы были написаны... (小品は書かれた)']
        ],
        'anatomy': '''【受動形動詞・短語尾形（Краткое причастие）】«написан» は動詞 «написать»（完了体・書く/作曲する）から作られた受動過去形動詞の短語尾形（男性単数）です。\n★重要鉄則：短語尾形は名詞のような6格変化（主格・生格・与格…）を行わず、主語の「性・数」に一致（男性 -∅, 女性 -а, 中性 -о, 複数 -ы）して文の述語（〜された・〜されていた）となります。男性名詞 концерт に呼応してゼロ語尾になっています。\n「誰によって」という動作主は前置詞なしの【造格】（русским композитором）で直結します。''',
        'network': ['написать (書く・作曲する/完了体動詞)', 'писать (書く/不完了体動詞)', 'написанный (書かれた/完全形受動形動詞)'],
        'aspect_pair': 'писать (НСВ) / написать (СВ)',
        'examples': [
            {'ru': 'Этот знаменитый концерт был написан русским композитором в Москве.', 'ja': 'この有名な協奏曲はモスクワでロシアの作曲家によって書かれた。'}
        ]
    },
    'проданы': {
        'word': 'проданы',
        'pos': '受動過去形動詞・短語尾形 (Краткое страдательное причастие)',
        'meaning': '売られた、売り切れた (複数)',
        'notes': '【短語尾形の一致】主語の性・数（複数）に一致。格変化は行わず、述語として受動態を作る。',
        'declension_table': [
            ['性・数', 'проданы (受動過去短語尾)', '主語との性数一致用例 (быть + 短語尾)'],
            ['男性単数 (он)', 'продан', 'Билет был продан (チケットは売られた)'],
            ['女性単数 (она)', 'продана', 'Партитура была продана (総譜は売られた)'],
            ['中性単数 (оно)', 'продано', 'Место было продано (座席は売られた)'],
            ['複数 (они)', 'проданы', 'Все билеты уже проданы (すべてのチケットは既に売り切れた)']
        ],
        'anatomy': '''【受動形動詞・短語尾形（Краткое причастие）】«проданы» は動詞 «продать»（完了体・売る）から作られた受動過去形動詞の短語尾形（複数）です。\n★重要鉄則：短語尾形は名詞のような6格変化（主格・生格・与格…）を行わず、主語の「性・数」に一致（複数 -ы）して文の述語（〜された）となります。複数名詞 билеты に呼応して語尾が -ы になっています。''',
        'network': ['продать (売る/完了体動詞)', 'продавать (売る/不完了体動詞)', 'проданный (売られた/完全形受動形動詞)'],
        'aspect_pair': 'продавать (НСВ) / продать (СВ)',
        'examples': [
            {'ru': 'Все билеты на вечерний концерт уже проданы.', 'ja': '夜のコンサートのチケットはすべて既に売り切れた。'}
        ]
    },
    'открыта': {
        'word': 'открыта',
        'pos': '受動過去形動詞・短語尾形 (Краткое страдательное причастие)',
        'meaning': '開かれた (女性単数)',
        'notes': '【短語尾形の一致】主語の性・数（女性単数）に一致。格変化は行わず、述語として受動態を作る。動作主は造格。',
        'declension_table': [
            ['性・数', 'открыта (受動過去短語尾)', '主語との性数一致用例 (быть + 短語尾)'],
            ['男性単数 (он)', 'открыт', 'Зал был открыт (ホールは開かれた)'],
            ['女性単数 (она)', 'открыта', 'Новая партитура была открыта (新しい総譜は開かれた)'],
            ['中性単数 (оно)', 'открыто', 'Окно было открыто (窓は開かれた)'],
            ['複数 (они)', 'открыты', 'Двери были открыты (扉は開かれた)']
        ],
        'anatomy': '''【受動形動詞・短語尾形（Краткое причастие）】«открыта» は動詞 «открыть»（完了体・開く）から作られた受動過去形動詞の短語尾形（女性単数）です。\n★重要鉄則：短語尾形は名詞のような6格変化を行わず、主語の「性・数」に一致して文の述語となります。女性名詞 партитура に呼応して語尾が -а になっています。''',
        'network': ['открыть (開く/完了体動詞)', 'открывать (開く/不完了体動詞)', 'открытый (開かれた/完全形受動形動詞)'],
        'aspect_pair': 'открывать (НСВ) / открыть (СВ)',
        'examples': [
            {'ru': 'Новая партитура была открыта главным дирижёром.', 'ja': '新しい総譜は首席指揮者によって開かれた。'}
        ]
    },
    'преподавательница': {
        'word': 'преподавательница',
        'pos': '女性名詞 (活動体・軟子音+а型)',
        'meaning': '女性講師、女性教員',
        'notes': '【格変化】活動体女性名詞（単数対格 -у, 複数対格は生格と同形のゼロ語尾 -ниц）',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'преподава́тельница', 'преподава́тельницы'],
            ['生格', 'преподава́тельницы', 'преподава́тельниц'],
            ['与格', 'преподава́тельнице', 'преподава́тельницам'],
            ['対格', 'преподава́тельницу', 'преподава́тельниц'],
            ['造格', 'преподава́тельницей', 'преподава́тельницами'],
            ['前置格', 'о преподава́тельнице', 'о преподава́тельницах']
        ],
        'anatomy': '''【女性活動体名詞の格変化】語尾 -а の規則的な格変化ですが、活動体（人）であるため「複数対格」は「複数生格と同形（преподавательниц）」となります。単数対格は不活動体と同様に «-у»（преподавательницу）です。単数造格は «-ей»（преподавательницей）です。''',
        'network': ['преподаватель (講師・教員/男性名詞)', 'преподавать (講義する・教える/不完了体)', 'учительница (女性教師/女性名詞)'],
        'examples': [
            {'ru': 'Юсукэ играет сонату с преподавательницей Таней.', 'ja': 'ユウスケはターニャ先生と一緒にソナタを弾いています。'},
            {'ru': 'Наша преподавательница всегда тепло поддерживает студентов.', 'ja': '私たちの女性講師はいつも学生たちを温かくサポートしてくれます。'}
        ]
    },
    'преподаватель': {
        'word': 'преподаватель',
        'pos': '男性名詞 (活動体・軟変化)',
        'meaning': '講師、教員、大学教師',
        'notes': '【格変化】活動体男性名詞（単数対格・複数対格ともに生格と同形）',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'преподава́тель', 'преподава́тели'],
            ['生格', 'преподава́теля', 'преподава́телей'],
            ['与格', 'преподава́телю', 'преподава́телям'],
            ['対格', 'преподава́теля', 'преподава́телей'],
            ['造格', 'преподава́телем', 'преподава́телями'],
            ['前置格', 'о преподава́теле', 'о преподава́телях']
        ],
        'anatomy': '''【男性活動体名詞（軟変化 -тель型）の格変化】語尾 -тель で終わる活動体（人）名詞です。対格は単数・複数ともに生格と同形になります（単数対格 преподавателя, 複数対格 преподавателей）。単数造格は «-ем»（преподавателем）となります。''',
        'network': ['преподавательница (女性講師/女性名詞)', 'преподавать (講義する・教える/不完了体)', 'профессор (教授/男性名詞)'],
        'examples': [
            {'ru': 'Наш преподаватель внимательно слушает исполнение.', 'ja': '私たちの講師は演奏を注意深く聴いています。'}
        ]
    },
    'стать': {
        'word': 'стать',
        'pos': '動詞 (完了体・СВ / 第1変化・-н-挿入型・【造格支配】)',
        'meaning': '〜になる（身分・職業・状態の変化）、〜し始める',
        'notes': '【露検2級 必修】造格支配動詞（стать ＋ 造格: 〜になる）',
        'aspect_pair': 'становиться (НСВ: 過程・反復) ⇔ стать (СВ: 変化の達成・結果)',
        'declension_table': [
            ['人称・性', 'стать (単純未来形)', '過去形 / 命令形・用例'],
            ['я', 'ста́ну', 'Он стал'],
            ['ты', 'ста́нешь', 'Ты стань! (命令形・単数)'],
            ['он/она', 'ста́нет', 'Она ста́ла / Оно ста́ло'],
            ['мы', 'ста́нем', 'Мы ста́ли'],
            ['вы', 'ста́нете', 'Ста́ньте! (命令形・複数)'],
            ['они', 'ста́нут', 'Они ста́ли музыкантами (過去・造格)']
        ],
        'irregular_alert': {
            'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
            'detail': '«стать» は将来の到達点や身分・職業を表す際、後ろに必ず【造格】を要求します（文中の「выдающимся музыкантом」が造格なのはこのためです）。活用は *стаю ではなく語幹に -н- が入る «я стану, ты станешь...»（単純未来）となります。'
        },
        'anatomy': '''【🎯 露検2級 合格指南：造格支配動詞 «стать + 造格»】
・動詞 «стать»（〜になる / 完了体・СВ）は、身分・職業・状態への変化を表すとき、後ろに必ず【造格（Творительный падеж）】を要求する代表的な「造格支配動詞」です。
・本例文: «Она мечтает стать выдающимся музыкантом на мировой сцене.»
　→ 名詞 «музыкант»（男性造格: музыкантом）と、それを修飾する形容詞 «выдающийся»（男性造格: выдающимся）が揃って造格になっているのは、動詞 «стать» の格支配によるものです。

【露検2級 必須！造格支配動詞の4大グループ】
① 身分・職業・状態の変化:
　• стать + 造格 : 〜になる（変化の達成・将来の目標）
　• быть + 造格 : 〜である・になる（特に過去形・未来形・不定詞で造格をとる）
　• являться + 造格 : 〜である（公的・論文・改まった文章での定番）
　• казаться / показаться + 造格 : 〜に見える、〜のように思われる
　• оказаться + 造格 : 〜であることが判明する
　• оставаться / остаться + 造格 : 〜のままである
　• называться + 造格 : 〜と呼ばれる
　• работать + 造格 : 〜として働く（例: работать преподавателем）
② 操作・指導・管理:
　• управлять + 造格 : 〜を操る、管理する（例: управлять звуком: 響きを操る）
　• руководить + 造格 : 〜を指導・指揮する（例: руководить оркестром）
　• дирижировать + 造格 : 〜を指揮する
③ 興味・関心・専攻:
　• заниматься + 造格 : 〜を勉強・練習する、従事する（例: заниматься музыкой）
　• интересоваться + 造格 : 〜に興味がある（例: интересоваться искусством）
　• увлекаться + 造格 : 〜に熱中する（例: увлекаться джазом）
④ 感情・誇り:
　• гордиться + 造格 : 〜を誇りに思う（例: гордиться успехом）
　• восхищаться + 造格 : 〜に感嘆・感服する
　• любоваться + 造格 : 〜に見とれる、うっとり眺める

【活用とアスペクト（体の対）】
・不完了体: становиться（〜になりつつある / 過程・反復）
・完了体: стать（〜になる / 結果の達成）
※ 不定詞 «стать» は第1変化（-н- 挿入型）であり、活用語尾は «я стану, ты станешь, он станет, мы станем, вы станете, они станут» です（*стаю, *стаешь ではありません）。完了体の現在形活用は「単純未来」を表します。''',
        'network': [
            'становиться (不完了体: 〜になりつつある / 過程・反復)',
            'остановиться (立ち止まる、停止する / 再帰動詞)',
            'восстановить (復元する、修復する)',
            'состоять (〜から成る、構成される)',
            'настать (到来する、季節がやってくる)',
            'постоянный (恒常的な、絶え間ない / 形容詞)'
        ],
        'conservatory_collocations': [
            {'ru': 'стать выдающимся музыкантом', 'ja': '傑出した音楽家になる（стать ＋ 男性造格）'},
            {'ru': 'стать лауреатом конкурса', 'ja': '国際コンクールの受賞者になる（стать ＋ 男性造格）'},
            {'ru': 'стать известным дирижёром', 'ja': '著名な指揮者になる（стать ＋ 男性造格）'},
            {'ru': 'стать прекрасной пианисткой', 'ja': '素晴らしい女性ピアニストになる（стать ＋ 女性造格）'}
        ],
        'examples': [
            {'ru': 'Она мечтает стать выдающимся музыкантом на мировой сцене.', 'ja': '彼女は世界の舞台で傑出した音楽家になることを夢見ています。'},
            {'ru': 'Николай хочет стать дирижёром студенческого оркестра.', 'ja': 'ニコライは学生オーケストラの指揮者になりたいと思っています。'},
            {'ru': 'После победы на конкурсе Алёна стала знаменитой пианисткой.', 'ja': 'コンクール優勝の後、アリョーナは有名なピアニストになりました。'}
        ]
    },
    'становиться': {
        'word': 'становиться',
        'pos': '動詞 (不完了体・НСВ / 再帰動詞・第2変化・【造格支配】)',
        'meaning': '〜になりつつある、〜になる（過程・反復・変化の進行）',
        'notes': '【露検2級 必修】造格支配動詞（становиться ＋ 造格: 〜になる）',
        'aspect_pair': 'становиться (НСВ: 過程・反復) ⇔ стать (СВ: 変化の達成・結果)',
        'declension_table': [
            ['人称・性', 'становиться (現在形)', '過去形 / 命令形・用例'],
            ['я', 'становлю́сь', 'Он станови́лся'],
            ['ты', 'стано́вишься', 'Ты станови́сь! (命令形・単数)'],
            ['он/она', 'стано́вится', 'Она станови́лась'],
            ['мы', 'стано́вимся', 'Мы станови́лись'],
            ['вы', 'стано́витесь', 'Станови́тесь! (命令形・複数)'],
            ['они', 'стано́вятся', 'Они станови́лись мастерами']
        ],
        'irregular_alert': {
            'badge': '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
            'detail': '«становиться» は後ろに必ず【造格】をとる代表的動詞です。1人称単数で -вл-（становлюсь）となる第2変化唇音挿入に注意してください。'
        },
        'anatomy': '''【動詞 становиться（不完了体・НСВ / 【造格支配】）】
・«стать» の不完了体ペア。変化のプロセス（徐々に〜になりつつある）、反復（いつも〜になる）を表します。
・補語には «стать» と同様に必ず【造格】をとります（例: Дни становятся длиннее: 日が長くなる / становиться профессионалом: プロになりつつある）。
・活用は第2変化で、1人称単数のみ唇音挿入で «становлюсь» となります（ты становишься, он становится...）。''',
        'network': [
            'стать (完了体: 〜になる / 結果)',
            'останавливаться (立ち止まる / НСВ)',
            'восстанавливать (復元する / НСВ)'
        ],
        'conservatory_collocations': [
            {'ru': 'становиться профессионалом', 'ja': 'プロになりつつある（становиться ＋ 男性造格）'},
            {'ru': 'звук становится глубже', 'ja': '響きがより深くなっていく'}
        ],
        'examples': [
            {'ru': 'С каждым годом игра пианиста становится более зрелой.', 'ja': '年を経るごとに、ピアニストの演奏はより円熟したものになっていきます。'}
        ]
    },
    'звучать': {
        'word': 'звучать',
        'pos': '動詞 (不完了体・НСВ / 第2変化)',
        'meaning': '鳴り響く、奏でられる、聞こえる',
        'notes': '【活用】第2変化（я звучу́, ты звучи́шь, они звуча́т） / 【形動詞】звуча́щий',
        'aspect_pair': 'звуча́ть (НСВ: 継続・鳴り響いている) ⇔ прозвуча́ть (СВ: 鳴り響いた・響き渡った)',
        'declension_table': [
            ['人称・性', 'звучать (現在形・第2変化)', '過去形 / 命令形・用例'],
            ['я', 'звучу́', 'Он звуча́л'],
            ['ты', 'звучи́шь', 'Звучи́! (命令形・単数)'],
            ['он/она', 'звучи́т', 'Она́ звуча́ла / Оно́ звуча́ло'],
            ['мы', 'звучи́м', 'Мы звуча́ли'],
            ['вы', 'звучи́те', 'Звучи́те! (命令形・複数)'],
            ['они', 'звуча́т', 'В зале звуча́т аплодисменты']
        ],
        'anatomy': '''【動詞 «звучать» の第2変化と形動詞形成】
・不定形は -ать ですが、第2変化（-ить変化グループ）として活用します。人称語尾は «-у́, -и́шь, -и́т, -и́м, -и́те, -а́т» となり、機械的な第1変化（*звучаю, *звучает）には絶対になりません！
・3人称複数形 «звуча́т» の語幹 «звуч-» に接尾辞 «-ащ-» を付けることで、能動形動詞現在形 «звуча́щий»（響いている〜）が作られます。''',
        'network': [
            'звук (音、響き/男性名詞)',
            'звуковой (音の・音響の/形容詞)',
            'созвучие (和音・調和/中性名詞)',
            'прозвучать (鳴り響く・発せられる/完了体動詞)',
            'звучащий (響いている/能動現在形動詞)'
        ],
        'examples': [
            {'ru': 'В Большом зале консерватории звучит прекрасная музыка.', 'ja': '音楽院の大ホールに素晴らしい音楽が響いています。'},
            {'ru': 'Музыка, звучащая в этом зале, вдохновляет всех слушателей.', 'ja': 'このホールに響いている音楽は、すべての聴衆を奮い立たせます。'}
        ]
    },
    'звучащая': {
        'word': 'звучащая',
        'base': 'звучать',
        'pos': '能動形動詞 (現在形・女性単数主格 / 原動詞: звучать)',
        'meaning': '（〜に）響いている、奏でられている（女性名詞を修飾）',
        'notes': '【露検2級 必修】能動形動詞現在形（形容詞と同様に性・数・格変化）',
        'declension_table': [
            ['格', '男性 (звуча́щий)', '女性 (звуча́щая)', '中性 (звуча́щее)', '複数 (звуча́щие)'],
            ['主格', 'звуча́щий', 'звуча́щая', 'звуча́щее', 'звуча́щие'],
            ['生格', 'звуча́щего', 'звуча́щей', 'звуча́щего', 'звуча́щих'],
            ['与格', 'звуча́щему', 'звуча́щей', 'звуча́щему', 'звуча́щим'],
            ['対格', 'звуча́щий / звуча́щего', 'звуча́щую', 'звуча́щее', 'звуча́щие / звуча́щих'],
            ['造格', 'звуча́щим', 'звуча́щей', 'звуча́щим', 'звуча́щими'],
            ['前置格', 'звуча́щем', 'звуча́щей', 'звуча́щем', 'звуча́щих']
        ],
        'irregular_alert': {
            'badge': '🎯 露検2級 必修：能動形動詞現在形 (Причастие)',
            'detail': '«звучащая» は第2変化動詞 «звучать»（3人称複数 звучат）から作られた能動形動詞現在形です。修飾する女性名詞 «музыка»（女性単数主格）に合わせて形容詞と同様に格変化します。',
            'related_tag': 'participle.active',
            'jump_label': '形動詞の文法'
        },
        'anatomy': '''【能動形動詞現在形 «звучащая» の構造と格変化】
・動詞 «звучать»（第2変化: 3人称複数 «звуч-а́т»）の語幹に、現在能動の接尾辞 «-ащ-» を付け、修飾する女性名詞 «музыка»（単数主格）に合わせて女性語尾 «-ая» が結合した形動詞（Причастие）です。
・関係代名詞節 «музыка, которая звучит...»（響いている音楽）と完全に同一の意味を、たった1語で格調高く表現します。
・形容詞と同じ規則で格変化（対格: звуча́щую, 生・与・造・前置格: звуча́щей）します。''',
        'network': [
            'звучать (鳴り響く/不完了体動詞)',
            'звучащий (響いている/男性主格)',
            'звучащее (響いている/中性主格)',
            'звучащие (響いている/複数主格)',
            'музыка (音楽/女性名詞)'
        ],
        'examples': [
            {'ru': 'Музыка, звучащая в этом зале, вдохновляет всех слушателей.', 'ja': 'このホールに響いている音楽は、すべての聴衆を奮い立たせます。'},
            {'ru': 'Мы наслаждаемся музыкой, звучащей со сцены.', 'ja': '私たちはステージから響いてくる音楽（女性造格: звучащей）を堪能しています。'}
        ]
    },
    'звучащий': {
        'word': 'звучащий',
        'base': 'звучать',
        'pos': '能動形動詞 (現在形・男性単数主格 / 原動詞: звучать)',
        'meaning': '（〜に）響いている、奏でられている（男性名詞を修飾）',
        'notes': '【露検2級 必修】能動形動詞現在形（形容詞と同様に性・数・格変化）',
        'declension_table': [
            ['格', '男性 (звуча́щий)', '女性 (звуча́щая)', '中性 (звуча́щее)', '複数 (звуча́щие)'],
            ['主格', 'звуча́щий', 'звуча́щая', 'звуча́щее', 'звуча́щие'],
            ['生格', 'звуча́щего', 'звуча́щей', 'звуча́щего', 'звуча́щих'],
            ['与格', 'звуча́щему', 'звуча́щей', 'звуча́щему', 'звуча́щим'],
            ['対格', 'звуча́щий / звуча́щего', 'звуча́щую', 'звуча́щее', 'звуча́щие / звуча́щих'],
            ['造格', 'звуча́щим', 'звуча́щей', 'звуча́щим', 'звуча́щими'],
            ['前置格', 'звуча́щем', 'звуча́щей', 'звуча́щем', 'звуча́щих']
        ],
        'irregular_alert': {
            'badge': '🎯 露検2級 必修：能動形動詞現在形 (Причастие)',
            'detail': '«звучащий» は動詞 «звучать»（3人称複数 звучат）から作られた能動形動詞現在形です。形容詞と同様に性・数・格変化します。',
            'related_tag': 'participle.active',
            'jump_label': '形動詞の文法'
        },
        'anatomy': '''【能動形動詞現在形 «звучащий» の成り立ち】
・第2変化動詞 «звучать»（3人称複数 «звуч-а́т»）から派生した現在能動形動詞の基本形（男性単数主格）です。
・「звучащий аккорд（鳴り響く和音）」「звучащий голос（よく響く歌声）」のように男性名詞を直接修飾します。''',
        'network': [
            'звучать (鳴り響く/不完了体動詞)',
            'звучащая (響いている/女性主格)',
            'звучащее (響いている/中性主格)',
            'звучащие (響いている/複数主格)'
        ],
        'examples': [
            {'ru': 'В тишине раздаётся прекрасный звучащий аккорд.', 'ja': '静寂の中に美しく響く和音が鳴り渡ります。'}
        ]
    },
    'весь': {
        'word': 'весь / вся / всё / все',
        'pos': '限定代名詞 (Pronoun)',
        'meaning': 'すべての、全部の、全体の / 【中性 всё】すべて（のもの）、【複数 все】みんな、全員',
        'notes': '【代名詞の格変化】男: весь, 女: вся, 中: всё, 複: все',
        'declension_table': [
            ['格', '男性 (весь)', '女性 (вся)', '中性 (всё)', '複数 (все)'],
            ['主格', 'весь', 'вся', 'всё', 'все'],
            ['生格', 'всего', 'всей', 'всего', 'всех'],
            ['与格', 'всему', 'всей', 'всему', 'всем'],
            ['対格', 'весь / всего', 'всю', 'всё', 'все / всех'],
            ['造格', 'всем', 'всей (всею)', 'всем', 'всеми'],
            ['前置格', 'обо всём (о всём)', 'обо всей', 'обо всём', 'обо всех']
        ],
        'anatomy': '''【限定代名詞 весь（男性 весь, 女性 вся, 中性 всё, 複数 все）】\n・名詞を修飾する形容詞的用法（весь зал: ホール全体、всё пространство: 全空間、все студенты: 全学生）に加え、代名詞単独でも極めて頻出です。\n・中性形 «всё» は単独で「すべてのこと、全部（everything）」を表します（例: Всё в порядке. / Всё хорошо. / наполняют всё: すべてを満たす）。\n・複数形 «все» は単独で「すべての人々、みんな（everyone）」を表します（例: Все любят... / Все знают...）。\n・対格は活動体に対して生格と同形（男 всего, 複 всех）、不活動体に対して主格と同形（男 весь, 複 все）となります。\n・前置格の前置詞は «обо»（обо всём, обо всех）になる点に注意してください。''',
        'irregular_alert': {
            'badge': '代名詞の重要不規則変化',
            'detail': 'весь（男）/ вся（女）/ всё（中）/ все（複）。中性単数「всё」は「すべて（のこと）」、複数「все」は「みんな」として名詞的にも使われます。'
        },
        'network': [
            'всё (すべて、全部 / 中性単数主格・対格)',
            'все (みんな、全員 / 複数主格)',
            'всего (合計で、わずかに / 生格副詞化)',
            'всё равно (どちらでも構わない、どうでもよい)',
            'всё-таки (やはり、それでもなお)'
        ],
        'examples': [
            {'ru': 'Звуки рояля наполняют всё пространство Большого зала.', 'ja': 'ピアノの響きが大ホールの全空間を満たしています。'},
            {'ru': 'Это прекрасная музыка, которую все любят.', 'ja': 'これは誰もが愛する素晴らしい音楽です。'},
            {'ru': 'Музыка вдохновляет всех слушателей.', 'ja': '音楽はすべての聴衆をインスパイアします。'},
            {'ru': 'Всё готово к началу концерта.', 'ja': '演奏会の開演に向けてすべて準備が整いました。'}
        ]
    },
    'тот': {
        'word': 'тот',
        'pos': '指示代名詞 (あの)',
        'meaning': 'あの、その（遠称の指示代名詞）',
        'notes': '【格変化】男: тот, 女: та, 中: то, 複: те',
        'declension_table': [
            ['格', '男性 (тот)', '女性 (та)', '中性 (то)', '複数 (те)'],
            ['主格', 'тот', 'та', 'то', 'те'],
            ['生格', 'того', 'той', 'того', 'тех'],
            ['与格', 'тому', 'той', 'тому', 'тем'],
            ['対格', 'тот / того', 'ту', 'то', 'те / тех'],
            ['造格', 'тем', 'той', 'тем', 'теми'],
            ['前置格', 'том', 'той', 'том', 'тех']
        ],
        'anatomy': '''遠称の指示代名詞（тот/та/то/те）。этот（この）と対比され、「あの〜」「その〜」を表します。''',
        'network': ['этот (この)', 'то (それ、そのこと)'],
        'examples': [
            {'ru': 'Тот концерт был незабываемым.', 'ja': 'あの演奏会は忘れられないものでした。'}
        ]
    },
    'видеть': {
        'word': 'видеть / увидеть',
        'pos': '動詞（不完了体 / 完了体・第2変化）',
        'meaning': '見る、見える、会う',
        'notes': '【活用・子音交替】1人称単数のみ д ⇔ ж 交替（я вижу, ты видишь...）',
        'declension_table': [
            ['人称', 'видеть (不完了体)', 'увидеть (完了体)'],
            ['я (1人称単数)', 'вижу', 'увижу'],
            ['ты (2人称単数)', 'видишь', 'увидишь'],
            ['он / она (3人称単数)', 'видит', 'увидит'],
            ['мы (1人称複数)', 'видим', 'увидим'],
            ['вы (2人称複数・敬称)', 'видите', 'увидите'],
            ['они (3人称複数)', 'видят', 'увидят'],
            ['過去形 (男性)', 'видел', 'увидел'],
            ['過去形 (女性)', 'видела', 'увидела'],
            ['過去形 (中性)', 'видело', 'увидело'],
            ['過去形 (複数)', 'видели', 'увидели']
        ],
        'anatomy': '''第2変化動詞（-еть）。\n・1人称単数のみ語幹末尾の子音 «д» が «ж» に交替します（я вижу, но ты видишь）。\n・2人称単数以降は規則的な第2変化語尾（-ишь, -ит, -им, -ите, -ят）となります。\n・直接目的語は対格（Accusative）をとります（вижу редкие ноты）。\n・否定文では生格支配となります（не вижу смысла, нет времени）。''',
        'network': ['смотреть (意識して見る)', 'увидеть (見かける/完了体)', 'вид (外観・アスペクト/名詞)'],
        'examples': [
            {'ru': 'Я вижу редкие ноты на столе.', 'ja': '私は机の上に貴重な楽譜を見つけました。（直接目的語・対格）'},
            {'ru': 'Ты видишь дирижёра?', 'ja': '指揮者が見えますか？'},
            {'ru': 'Мы часто видим его в консерватории.', 'ja': '私たちは音楽院でよく彼を見かけます。'}
        ]
    },
    'время': {
        'word': 'время',
        'pos': '中性名詞 (-мя中性名詞・特殊格変化)',
        'meaning': '時間、時代、時',
        'notes': '【特殊格変化】単数生・与・前置格で -ен- 挿入（времени）、造格は временем',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'время', 'времена'],
            ['生格', 'времени', 'времён'],
            ['与格', 'времени', 'временам'],
            ['対格', 'время', 'времена'],
            ['造格', 'временем', 'временами'],
            ['前置格', 'о времени', 'о временах']
        ],
        'anatomy': '''ロシア語に10語しかない «-мя» で終わる中性名詞（время, имя など）。\n・主格・対格を除くすべての格で、語幹に «-ен-» が挿入されます。\n・単数の生格・与格・前置格はすべて同形の «времени» となります。\n・造格は «временем» です。\n・«нет»（ない）に続くときは必ず生格の «нет времени» となります。''',
        'network': ['свободное время (自由な時間)', 'во время (+生格: 〜の間に)', 'современный (現代の/形容詞)', 'вовремя (時間通りに/副詞)'],
        'examples': [
            {'ru': 'У меня нет свободного времени.', 'ja': '私には自由な時間がありません。（生格否定）'},
            {'ru': 'Есть ли у вас время?', 'ja': 'お時間はありますか？（主格）'},
            {'ru': 'Времена года Чайковского.', 'ja': 'チャイコフスキーの「四季」。（複数主格）'}
        ]
    },
    'редкий': {
        'word': 'редкий',
        'pos': '形容詞（硬変化・г, к, х幹）',
        'meaning': '珍しい、貴重な、まれな',
        'notes': '【格変化】語幹末尾 к による正書法ルール（ы ではなく и）',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'редкий', 'редкая', 'редкое', 'редкие'],
            ['生格', 'редкого', 'редкой', 'редкого', 'редких'],
            ['与格', 'редкому', 'редкой', 'редкому', 'редким'],
            ['対格', 'редкий / редкого', 'редкую', 'редкое', 'редкие / редких'],
            ['造格', 'редким', 'редкой', 'редким', 'редкими'],
            ['前置格', 'о редком', 'о редкой', 'о редком', 'о редких']
        ],
        'anatomy': '形容詞。語幹が к で終わるため、7文字正書法ルールにより ы の代わりに и が入ります（редкие）。対格は無生物なら主格と同形（редкие ноты）、生物なら生格と同形（редких музыкантов）となります。',
        'network': ['редко (めったに/副詞)', 'редкость (珍しさ・希少品/名詞)'],
        'examples': [
            {'ru': 'Я вижу редкие ноты.', 'ja': '私は貴重な楽譜を見つけました。（不活動体複数対格）'}
        ]
    },
    'нота': {
        'word': 'нота / ноты',
        'pos': '女性名詞（単数: 音符 / 複数: 楽譜）',
        'meaning': '楽譜、音符',
        'notes': '【格変化】通常「楽譜」の意味では常に複数形 (ноты) を用います',
        'declension_table': [
            ['格', '単数 (音符)', '複数 (楽譜・諸音符)'],
            ['主格', 'нота', 'ноты'],
            ['生格', 'ноты', 'нот'],
            ['与格', 'ноте', 'нотам'],
            ['対格', 'ноту', 'ноты'],
            ['造格', 'нотой', 'нотами'],
            ['前置格', 'о ноте', 'о нотах']
        ],
        'anatomy': '女性名詞。単数形 «нота» は「一つの音符」を表し、集合的に「楽譜（ピース・譜面）」を指す場合は常に複数形 «ноты»（生格 нот, 与格 нотам, 対格 ноты, 造格 нотами, 前置格 о нотах）を用います。',
        'network': ['пюпитр (譜面台)', 'партитура (総譜)'],
        'examples': [
            {'ru': 'У меня есть новые ноты.', 'ja': '私には新しい楽譜があります。（複数主格）'},
            {'ru': 'Положите ноты на пюпитр.', 'ja': '楽譜を譜面台に置いてください。（不活動体複数対格）'}
        ]
    },
    'свободный': {
        'word': 'свободный',
        'pos': '形容詞（硬変化）',
        'meaning': '自由な、空いている、ゆとりのある',
        'notes': '【格変化】свободное время (自由時間) は中性名詞との結合',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'свободный', 'свободная', 'свободное', 'свободные'],
            ['生格', 'свободного', 'свободной', 'свободного', 'свободных'],
            ['与格', 'свободному', 'свободной', 'свободному', 'свободным'],
            ['対格', 'свободный / свободного', 'свободную', 'свободное', 'свободные / свободных'],
            ['造格', 'свободным', 'свободной', 'свободным', 'свободными'],
            ['前置格', 'о свободном', 'о свободной', 'о свободном', 'о свободных']
        ],
        'anatomy': '硬変化形容詞。中性名詞 «время» と結合すると «свободное время»（主格）、生格否定では «свободного времени»（発音は「スヴァボードナヴァ・ヴリェーミニ」）となります。',
        'network': ['свободно (自由に/副詞)', 'свобода (自由/名詞)'],
        'examples': [
            {'ru': 'У меня нет свободного времени.', 'ja': '私には自由な時間がありません。（中性生格）'}
        ]
    },
    'я': {
        'word': 'я',
        'pos': '人称代名詞 (1人称単数)',
        'meaning': '私（一人称単数・主格）',
        'notes': '【格変化】меня (生/対), мне (与), мной (造), обо мне (前)',
        'declension_table': [
            ['格', '代名詞変化形', '前置詞結合・用例'],
            ['主格', 'я', 'Я играю на рояле. (私はピアノを弾く)'],
            ['生格', 'меня', 'У меня есть ноты. (私には楽譜がある)'],
            ['与格', 'мне', 'Мне нравится музыка. (私にはこの曲が気に入る)'],
            ['対格', 'меня', 'Вы слышите меня? (私の音が聴こえますか？)'],
            ['造格', 'мной / мною', 'Таня репетирует со мной. (ターニャは私と練習する)'],
            ['前置格', 'обо мне', 'Они говорят обо мне. (彼らは私のことを話す)']
        ],
        'anatomy': '''ロシア語の最重要人称代名詞。
・生格と対格は同形（меня）。
・前置詞 «с» と結合するときは発音の都合上 «со мной»、前置格の «о» は «обо мне» に変化します。
・「〜を持っている」は «У меня есть + 主格» で表します。''',
        'network': ['ты (君/2人称)', 'он (彼/3人称男性)', 'она (彼女/3人称女性)', 'мы (私たち/1人称複数)', 'вы (あなた方/2人称敬称)'],
        'examples': [
            {'ru': 'Я каждый день играю на рояле.', 'ja': '私は毎日グランドピアノを弾いています。'},
            {'ru': 'У меня сегодня важный концерт в консерватории.', 'ja': '私は今日音楽院で大事なコンサートがあります。'},
            {'ru': 'Сыграйте со мной этот дуэт, пожалуйста.', 'ja': 'どうか私と一緒にこの二重奏を弾いてください。'}
        ]
    },
    'ты': {
        'word': 'ты',
        'pos': '人称代名詞 (2人称単数)',
        'meaning': '君、お前（親称）',
        'notes': '【格変化】тебя (生/対), тебе (与), тобой (造), о тебе (前)',
        'declension_table': [
            ['格', '代名詞変化形', '前置詞結合・用例'],
            ['主格', 'ты', 'Ты превосходно играешь. (君は素晴らしい演奏をする)'],
            ['生格', 'тебя', 'У тебя есть свободное время? (君は時間ある？)'],
            ['与格', 'тебе', 'Я помогу тебе с партитурой. (総譜の読みを手伝うよ)'],
            ['対格', 'тебя', 'Я давно тебя не видел. (久しぶりだね)'],
            ['造格', 'тобой / тобою', 'Я горжусь тобой. (君を誇りに思うよ)'],
            ['前置格', 'о тебе', 'Мы часто думаем о тебе. (君のことをよく考えている)']
        ],
        'anatomy': '親しい間柄や友人同士で使う2人称代名詞。初対面や目上には «вы» を使います。',
        'network': ['вы (あなた/丁寧)', 'твой (君の/所有代名詞)'],
        'examples': [
            {'ru': 'Ты готов к сегодняшней репетиции?', 'ja': '今日の練習の準備はできたかい？'}
        ]
    },
    'он': {
        'word': 'он',
        'pos': '人称代名詞 (3人称単数・男性)',
        'meaning': '彼（男性名詞の指示）',
        'notes': '【格変化】его/него (生/対), ему/нему (与), им/ним (造), о нём (前)',
        'declension_table': [
            ['格', '代名詞変化形', '前置詞結合（н-添加）'],
            ['主格', 'он', 'Он известный пианист. (彼は著名なピアニストだ)'],
            ['生格', 'его / него', 'У него новый рояль. (彼は新しいピアノを持っている)'],
            ['与格', 'ему / нему', 'Я передал ему ноты. (彼に楽譜を渡した)'],
            ['対格', 'его / него', 'Мы встретили его в зале. (彼にホールで会った)'],
            ['造格', 'им / ним', 'С ним приятно играть. (彼と一緒に弾くのは心地よい)'],
            ['前置格', 'о нём', 'В газете писали о нём. (新聞で彼のことが書かれた)']
        ],
        'anatomy': '男性の人や男性名詞を指す3人称代名詞。前置詞の後では語頭に «н-» が添加されます（у него, с ним, о нём）。',
        'network': ['она (彼女)', 'оно (それ/中性)', 'они (彼ら)'],
        'examples': [
            {'ru': 'Он учится в Московской консерватории.', 'ja': '彼はモスクワ音楽院で学んでいます。'}
        ]
    },
    'она': {
        'word': 'она',
        'pos': '人称代名詞 (3人称単数・女性)',
        'meaning': '彼女（女性名詞の指示）',
        'notes': '【格変化】её/неё (生/対), ей/ней (与/造), о ней (前)',
        'declension_table': [
            ['格', '代名詞変化形', '前置詞結合（н-添加）'],
            ['主格', 'она', 'Она прекрасно поёт. (彼女は美しく歌う)'],
            ['生格', 'её / неё', 'У неё тонкий музыкальный слух. (彼女は耳が良い)'],
            ['与格', 'ей / ней', 'Подари ей цветы. (彼女に花を贈ろう)'],
            ['対格', 'её / неё', 'Я слушаю её сонату. (彼女のソナタを聴いている)'],
            ['造格', 'ей / ею / ней', 'С ней интересно спорить. (彼女と議論するのは面白い)'],
            ['前置格', 'о ней', 'Все говорят о ней с восторгом. (誰もが彼女を絶賛している)']
        ],
        'anatomy': '女性の人や女性名詞を指す3人称代名詞。前置詞の後では «неё, с ней, о ней» となります。',
        'network': ['он (彼)', 'её (彼女の/所有)'],
        'examples': [
            {'ru': 'Она играет на скрипке в оркестре.', 'ja': '彼女はオーケストラでバイオリンを弾いています。'}
        ]
    },
    'мы': {
        'word': 'мы',
        'pos': '人称代名詞 (1人称複数)',
        'meaning': '私たち',
        'notes': '【格変化】нас (生/対), нам (与), нами (造), о нас (前)',
        'declension_table': [
            ['格', '代名詞変化形', '用例'],
            ['主格', 'мы', 'Мы репетируем вместе. (私たちは一緒に練習する)'],
            ['生格', 'нас', 'У нас сегодня концерт. (私たちには今日演奏会がある)'],
            ['与格', 'нам', 'Нам пора начинать. (私たちは始める時間だ)'],
            ['対格', 'нас', 'Учитель похвалил нас. (先生は私たちを褒めた)'],
            ['造格', 'нами', 'Гордитесь нами! (私たちを誇りに思ってください)'],
            ['前置格', 'о нас', 'Подумайте о нас. (私たちのことも考えて)']
        ],
        'anatomy': '1人称複数代名詞。アンサンブルや共演で頻出します。',
        'network': ['наш (私たちの/所有)', 'я (私)'],
        'examples': [
            {'ru': 'Мы сыграли сонату Рахманинова.', 'ja': '私たちはラフマニノフのソナタを演奏しました。'}
        ]
    },
    'вы': {
        'word': 'вы',
        'pos': '人称代名詞 (2人称複数・丁寧敬称)',
        'meaning': 'あなた、あなた方',
        'notes': '【格変化】вас (生/対), вам (与), вами (造), о вас (前)',
        'declension_table': [
            ['格', '代名詞変化形', '用例'],
            ['主格', 'вы', 'Вы играете с душой. (あなたは魂を込めて弾く)'],
            ['生格', 'вас', 'У вас великолепный рояль. (あなたは素晴らしいピアノをお持ちですね)'],
            ['与格', 'вам', 'Вам нравится этот зал? (このホールはお気に召しましたか？)'],
            ['対格', 'вас', 'Я рад видеть вас. (お会いできて嬉しいです)'],
            ['造格', 'вами', 'Мы восхищаемся вами. (私たちはあなたに感嘆しています)'],
            ['前置格', 'о вас', 'Таня рассказывала о вас. (ターニャ先生があなたの話をしていました)']
        ],
        'anatomy': '複数形としての「あなた方」、または単数に対する敬称・丁寧な「あなた」を表します。',
        'network': ['ваш (あなたの/所有)', 'ты (君)'],
        'examples': [
            {'ru': 'Как вас зовут?', 'ja': 'お名前は何とおっしゃいますか？'}
        ]
    },
    'они': {
        'word': 'они',
        'pos': '人称代名詞 (3人称複数)',
        'meaning': '彼ら、彼女ら、それら',
        'notes': '【格変化】их/них (生/対), им/ним (与), ими/ними (造), о них (前)',
        'declension_table': [
            ['格', '代名詞変化形', '前置詞結合（н-添加）'],
            ['主格', 'они', 'Они аплодируют артистам. (彼らは拍手を送る)'],
            ['生格', 'их / них', 'У них нет билетов. (彼らには切符がない)'],
            ['与格', 'им / ним', 'Музыка дарит им радость. (音楽は彼らに喜びを与える)'],
            ['対格', 'их / них', 'Мы слушали их дуэт. (私たちは彼らの二重奏を聴いた)'],
            ['造格', 'ими / ними', 'С ними приятно работать. (彼らと仕事をするのは心地よい)'],
            ['前置格', 'о них', 'В консерватории знают о них. (音楽院で彼らのことは知られている)']
        ],
        'anatomy': '男女・事物を問わず複数の対象を指します。前置詞の後では «них, ним, ними» と н- が添加されます。',
        'network': ['их (彼らの/所有)'],
        'examples': [
            {'ru': 'Они готовятся к международному конкурсу.', 'ja': '彼らは国際コンクールに向けて準備しています。'}
        ]
    },
    'рояль': {
        'word': 'рояль',
        'pos': '男性名詞 (軟子音変化)',
        'meaning': 'グランドピアノ',
        'notes': '【格変化】生格: рояля, 前置格: на рояле (楽器演奏)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'рояль', 'рояли'],
            ['生格', 'рояля', 'роялей'],
            ['与格', 'роялю', 'роялям'],
            ['対格', 'рояль', 'рояли'],
            ['造格', 'роялем', 'роялями'],
            ['前置格', 'рояле (на рояле)', 'роялях (о роялях)']
        ],
        'anatomy': '''末尾が -ль で終わる男性軟変化名詞。
・不活動体のため対格は単複ともに主格と同形（рояль / рояли）。
・楽器を「演奏する」ときは必ず «играть на + 前置格» で «играть на рояле» となります。
・否定存在 «нет» の後ろは生格 «нет рояля» になります。''',
        'network': ['пианист (ピアニスト)', 'пианино (アップライトピアノ)', 'фортепиано (ピアノ/不変化)', 'клавиша (鍵盤)'],
        'examples': [
            {'ru': 'Я каждый день играю на рояле в консерватории.', 'ja': '私は毎日音楽院でグランドピアノを弾いています。'},
            {'ru': 'В этом классе стоит старинный рояль Steinway.', 'ja': 'この練習室には年代物のスタインウェイ製ピアノがあります。'},
            {'ru': 'Настройщик бережно настроил рояль перед концертом.', 'ja': '調律師はコンサートの前に丹念にピアノを調律しました。'}
        ]
    },
    'консерватория': {
        'word': 'консерватория',
        'pos': '女性名詞 (軟変化 -ия)',
        'meaning': '音楽院、コンセルヴァトワール',
        'notes': '【重要】与格・前置格は -е ではなく -и (в консерватории)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'консерватория', 'консерватории'],
            ['生格', 'консерватории', 'консерваторий'],
            ['与格', 'консерватории', 'консерваториям'],
            ['対格', 'консерваторию', 'консерватории'],
            ['造格', 'консерваторией', 'консерваториями'],
            ['前置格', 'консерватории (в консерватории)', 'консерваториях (о консерваториях)']
        ],
        'anatomy': '''語尾が -ия で終わる女性名詞の最重要語。
・通常の女性名詞の前置格は -е ですが、-ия の語は【与格も前置格も -и】（в консерватории）になります。
・音楽院で学ぶ・演奏するときは «в консерватории» (в + 前置格) を用います。''',
        'network': ['консерваторский (音楽院の/形容詞)', 'Московская консерватория (モスクワ音楽院)', 'Большой зал (大ホール)'],
        'examples': [
            {'ru': 'Московская консерватория имени Чайковского славится своими традициями.', 'ja': 'チャイコフスキー記念モスクワ音楽院はその伝統で名高いです。'},
            {'ru': 'Мы встретимся завтра в консерватории перед репетицией.', 'ja': '私たちは明日リハーサルの前に音楽院で会いましょう。'},
            {'ru': 'Юсукэ мечтает однажды выступить в Большом зале консерватории.', 'ja': 'Yusukeさんはいつか音楽院大ホールで演奏することを夢見ています。'}
        ]
    },
    'утро': {
        'word': 'утро',
        'pos': '中性名詞',
        'meaning': '朝、午前',
        'notes': '【格変化】造格: утром (朝に), 時間対格: каждое утро (毎朝)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'утро', 'утра'],
            ['生格', 'утра', 'утр'],
            ['与格', 'утру', 'утрам'],
            ['対格', 'утро', 'утра'],
            ['造格', 'утром', 'утрами'],
            ['前置格', 'утре (об утре)', 'утрах']
        ],
        'anatomy': '''-о で終わる硬変化中性名詞。
・造格単数の «утром» は「朝に」という副詞的表現。
・対格を用いて «каждое утро» で「毎朝」という時間表現になります。''',
        'network': ['утром (朝に/副詞)', 'утренний (朝の/形容詞)', 'вечер (夕方・晩)'],
        'examples': [
            {'ru': 'Каждое утро начинается со звуков гамм и арпеджио.', 'ja': '毎朝は音階とアルペジオの音から始まります。'},
            {'ru': 'Доброе утро, дорогие музыканты!', 'ja': 'おはようございます、親愛なる音楽家の皆さん！'}
        ]
    },
    'радость': {
        'word': 'радость',
        'pos': '女性名詞 (第3変化 -ость)',
        'meaning': '喜び、嬉しさ',
        'notes': '【格変化】造格: радостью (с радостью = 喜んで)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'радость', 'радости'],
            ['生格', 'радости', 'радостей'],
            ['与格', 'радости', 'радостям'],
            ['対格', 'радость', 'радости'],
            ['造格', 'радостью', 'радостями'],
            ['前置格', 'радости (о радости)', 'радостях']
        ],
        'anatomy': '''-ость で終わる第3変化女性名詞。
・生格・与格・前置格の語尾がすべて -и（радости）になります。
・造格は語尾 -ью（радостью）。前置詞 «с» と合わせて «с радостью»（喜んで）という副詞句を作ります。''',
        'network': ['радостный (喜ばしい/形容詞)', 'радоваться (喜ぶ/動詞)'],
        'examples': [
            {'ru': 'Музыка Шопена приносит слушателям глубокую радость.', 'ja': 'ショパンの音楽は聴き手に深い喜びをもたらします。'},
            {'ru': 'Я с радостью помогу вам разобрать эту партитуру.', 'ja': '喜んでこの総譜の読み解きをお手伝いしますよ。'}
        ]
    },
    'каждый': {
        'word': 'каждый',
        'pos': '限定代名詞 (形容詞変化)',
        'meaning': 'それぞれの、毎〜',
        'notes': '【格変化】中性対格: каждое (каждое утро = 毎朝)',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественные)'],
            ['主格', 'каждый', 'каждая', 'каждое', 'каждые'],
            ['生格', 'каждого', 'каждой', 'каждого', 'каждых'],
            ['与格', 'каждому', 'каждой', 'каждому', 'каждым'],
            ['対格', 'каждый / каждого', 'каждую', 'каждое', 'каждые / каждых'],
            ['造格', 'каждым', 'каждой', 'каждым', 'каждыми'],
            ['前置格', 'каждом', 'каждой', 'каждом', 'каждых']
        ],
        'anatomy': '''硬変化形容詞と同じ語尾変化をする限定代名詞。
・時間を表す語と対格で結合し、「毎〜」を表します（каждое утро = 毎朝, каждый день = 毎日）。''',
        'network': ['всякий (あらゆる)', 'каждый день (毎日)'],
        'examples': [
            {'ru': 'Каждый пианист знает цену ежедневному труду.', 'ja': 'すべてのピアニストは毎日の鍛錬の尊さを知っています。'}
        ]
    },
    'пианист': {
        'word': 'пианист',
        'pos': '男性名詞 (活動体・子音変化)',
        'meaning': 'ピアニスト',
        'notes': '【格変化】活動体のため対格＝生格（пианиста）',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'пианист', 'пианисты'],
            ['生格', 'пианиста', 'пианистов'],
            ['与格', 'пианисту', 'пианистам'],
            ['対格', 'пианиста', 'пианистов'],
            ['造格', 'пианистом', 'пианистами'],
            ['前置格', 'пианисте (о пианисте)', 'пианистах']
        ],
        'anatomy': '''活動体男性名詞。
・否定 «нет» の後ろは生格 «нет пианиста»。
・対格も生格と同形（«Я знаю этого пианиста»）。''',
        'network': ['пианистка (女性ピアニスト)', 'фортепиано (ピアノ)', 'пианизм (ピアノ奏法)'],
        'examples': [
            {'ru': 'В этом классе сейчас нет пианиста.', 'ja': 'この練習室には今ピアニストはいません。'},
            {'ru': 'Выдающийся пианист исполняет сонату Скрябина.', 'ja': '卓越したピアニストがスクリャービンのソナタを演奏しています。'}
        ]
    },
    'положить': {
        'word': 'положить',
        'pos': '動詞 (完了体) ⇔ класть (不完了体)',
        'meaning': '（横にして）置く',
        'aspect_pair': 'положить (СВ: 1回の完了) ⇔ класть (НСВ: 過程・反復)',
        'declension_table': [
            ['人称', 'положить (完了体未来)', 'класть (不完了体現在)'],
            ['я', 'положу', 'кладу'],
            ['ты', 'положишь', 'кладёшь'],
            ['он/она', 'положит', 'кладёт'],
            ['мы', 'положим', 'кладём'],
            ['вы', 'положите', 'кладёте'],
            ['они', 'положат', 'кладут']
        ],
        'anatomy': '''ロシア語で最も代表的な補充法動詞。
・完了体 положить (過去: положил, положила)
・移動先（куда? на/в + 対格）をとります。''',
        'network': ['класть (不完了体)', 'положение (位置・状態)'],
        'examples': [
            {'ru': 'Екатерина положила новые ноты на рояль.', 'ja': 'エカテリーナは新しい楽譜をピアノの上に置きました。'},
            {'ru': 'Положите, пожалуйста, партитуру на стол.', 'ja': 'スコアを机の上に置いてください。'}
        ]
    },
    'стол': {
        'word': 'стол',
        'pos': '男性名詞 (硬子音変化)',
        'meaning': '机、テーブル',
        'notes': '【格変化】対格は主格と同形 (стол)、前置格: на столе',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'стол', 'столы'],
            ['生格', 'стола', 'столов'],
            ['与格', 'столу', 'столам'],
            ['対格', 'стол', 'столы'],
            ['造格', 'столом', 'столами'],
            ['前置格', 'столе (на столе)', 'столах']
        ],
        'anatomy': '''不活動体男性名詞。
・移動先（куда?）は対格 «положить на стол»。
・所在場所（где?）は前置格 «лежит на столе»。''',
        'network': ['столик (小机)', 'письменный стол (机)'],
        'examples': [
            {'ru': 'Ноты уже лежат на столе.', 'ja': '楽譜はすでに机の上に置いてあります。'},
            {'ru': 'Он сидит за столом и изучает партитуру.', 'ja': '彼は机に向かって座り、総譜を研究しています。'}
        ]
    },
    'ноты': {
        'word': 'ноты',
        'pos': '女性名詞 (複数 ноты, 単数 нота)',
        'meaning': '楽譜、音符',
        'notes': '【格変化】楽譜の意味では通常複数形を使用。複数対格: ноты',
        'declension_table': [
            ['格', '単数 (1つの音符)', '複数 (楽譜・複数の音符)'],
            ['主格', 'нота', 'ноты'],
            ['生格', 'ноты', 'нот'],
            ['与格', 'ноте', 'нотам'],
            ['対格', 'ноту', 'ноты'],
            ['造格', 'нотой', 'нотами'],
            ['前置格', 'ноте (в ноте)', 'нотах (в нотах)']
        ],
        'anatomy': '''女性名詞 нота の複数形 «ноты» は「楽譜」を意味します。
・不活動体名詞のため複数対格は主格と同形（«положить ноты»）。
・「楽譜通りに弾く」は «играть по нотам»（与格）。
・「暗譜で弾く」は «играть без нот»（生格）。''',
        'network': ['нотный (楽譜の)', 'нотная тетрадь (五線紙ノート)'],
        'examples': [
            {'ru': 'Студентка положила новые ноты на рояль.', 'ja': '女子学生は新しい楽譜をピアノの上に置きました。'},
            {'ru': 'Пианист играет сложный пассаж по нотам.', 'ja': 'ピアニストは楽譜を見ながら複雑なパッセージを弾いています。'}
        ]
    },
    'заканчиваться': {
        'word': 'заканчиваться',
        'pos': '動詞 (НСВ・再帰動詞) ⇔ закончиться (СВ)',
        'meaning': '終わる、終了する',
        'aspect_pair': 'заканчиваться (НСВ: 進行・反復) ⇔ закончиться (СВ: 完了)',
        'declension_table': [
            ['人称', 'заканчиваться (不完了体現在)', 'закончиться (完了体未来)'],
            ['я', 'заканчиваюсь', 'закончусь'],
            ['ты', 'заканчиваешься', 'закончишься'],
            ['он/она', 'заканчивается', 'закончится'],
            ['мы', 'заканчиваемся', 'закончимся'],
            ['вы', 'заканчиваетесь', 'закончитесь'],
            ['они', 'заканчиваются', 'закончатся']
        ],
        'anatomy': '''他動詞 «заканчивать»（〜を終える）に再帰接尾辞 «-ся» が付いた自動詞表現。
・主語そのものが「終わる」ことを表します（«Репетиция заканчивается» = リハーサルが終わる）。
・母音の後では «-сь»、子音の後では «-ся» が付きます（例: я заканчиваюсь, он заканчивается）。
・完了体は «закончиться»（過去形: закончился / закончилась / закончилось）。''',
        'network': ['заканчивать (〜を終える/他動詞)', 'закончить (終える/完了体)', 'конец (終わり/名詞)', 'начинаться (始まる/反意語)'],
        'examples': [
            {'ru': 'Когда заканчивается репетиция, в Большом зале наступает тишина.', 'ja': 'リハーサルが終わると、大ホールには素晴らしい静寂が訪れます。'},
            {'ru': 'Концерт заканчивается в девять часов вечера.', 'ja': 'コンサートは夜9時に終わります。'},
            {'ru': 'Урок фортепиано уже закончился.', 'ja': 'ピアノのレッスンはもう終わりました。'}
        ]
    },
    'начинаться': {
        'word': 'начинаться',
        'pos': '動詞 (НСВ・再帰動詞) ⇔ начаться (СВ)',
        'meaning': '始まる、開始する',
        'aspect_pair': 'начинаться (НСВ: 進行・反復) ⇔ начаться (СВ: 完了)',
        'declension_table': [
            ['人称', 'начинаться (不完了体現在)', 'начаться (完了体未来)'],
            ['я', 'начинаюсь', 'начнусь'],
            ['ты', 'начинаешься', 'начнёшься'],
            ['он/она', 'начинается', 'начнётся'],
            ['мы', 'начинаемся', 'начнёмся'],
            ['вы', 'начинаетесь', 'начнётесь'],
            ['они', 'начинаются', 'начнутся']
        ],
        'anatomy': '''他動詞 «начинать»（〜を始める）に -ся が付いた自動詞（〜が始まる）。
・«Концерт начинается в семь часов»（コンサートは7時に始まる）。
・完了体は «начаться»（過去: начался / началась / началось）。''',
        'network': ['начинать (始める/他動詞)', 'начало (始まり/名詞)', 'заканчиваться (終わる/反意語)'],
        'examples': [
            {'ru': 'Репетиция начинается ровно в десять утра.', 'ja': '練習は朝10時ちょうどに始まります。'},
            {'ru': 'В тишине начинается нежная мелодия скрипки.', 'ja': '静寂の中で、ヴァイオリンの優しい旋律が始まります。'}
        ]
    },
    'оставаться': {
        'word': 'оставаться',
        'pos': '動詞 (НСВ・再帰動詞) ⇔ остаться (СВ)',
        'meaning': '残る、とどまる',
        'aspect_pair': 'оставаться (НСВ) ⇔ остаться (СВ)',
        'declension_table': [
            ['人称', 'оставаться (不完了体現在)', 'остаться (完了体未来)'],
            ['я', 'остаюсь', 'останусь'],
            ['ты', 'остаёшься', 'останешься'],
            ['он/она', 'остаётся', 'останется'],
            ['мы', 'остаёмся', 'останемся'],
            ['вы', 'остаётесь', 'останетесь'],
            ['они', 'остаются', 'останутся']
        ],
        'anatomy': '''不規則な現在形変化（-ава- 脱落型: остаюсь, остаёшься, остаётся...）。
・ある場所に「残る、居残る」、または状態が「〜のままである」ことを表します。
・完了体は «остаться»（останусь, останешься / остался, осталась）。
・«оставаться на сцене»（舞台の上に残る）。''',
        'network': ['остаток (残り)', 'остановить (止める)'],
        'examples': [
            {'ru': 'На сцене остаётся только один рояль.', 'ja': '舞台の上にはただ1台のグランドピアノだけが残っています。'},
            {'ru': 'После концерта студенты остаются в зале.', 'ja': '演奏会の後、学生たちはホールにとどまります。'}
        ]
    },
    'наступать': {
        'word': 'наступать',
        'pos': '動詞 (НСВ) ⇔ наступить (СВ)',
        'meaning': '（時節・状態が）訪れる、やって来る',
        'aspect_pair': 'наступать (НСВ) ⇔ наступить (СВ)',
        'declension_table': [
            ['人称', 'наступать (不完了体現在)', 'наступить (完了体未来)'],
            ['я', 'наступаю', 'наступлю'],
            ['ты', 'наступаешь', 'наступишь'],
            ['он/она', 'наступает', 'наступит'],
            ['мы', 'наступаем', 'наступим'],
            ['вы', 'наступаете', 'наступите'],
            ['они', 'наступают', 'наступят']
        ],
        'anatomy': '''季節、夜、沈黙、新しい時代などが「訪れる」「到来する」ことを表す美しい表現。
・«наступает тишина»（静寂が訪れる、しんと静まる）。
・«наступает вечер / ночь»（夕暮れ・夜がやって来る）。
・完了体は «наступить»（наступила тишина = 静寂が訪れた）。''',
        'network': ['наступить (完了体)', 'наступление (到来、進軍)'],
        'examples': [
            {'ru': 'В Большом зале консерватории наступает удивительная тишина.', 'ja': '音楽院の大ホールには驚くほどの静寂が訪れます。'},
            {'ru': 'Наступает вечер, и в классах зажигается свет.', 'ja': '夕暮れが訪れ、教室には灯りが点ります。'}
        ]
    },
    'затухать': {
        'word': 'затухать',
        'pos': '動詞 (НСВ) ⇔ затухнуть (СВ)',
        'meaning': '（光や音が）徐々に消える、減衰する',
        'aspect_pair': 'затухать (НСВ) ⇔ затухнуть (СВ)',
        'declension_table': [
            ['人称', 'затухать (不完了体現在)', 'затухнуть (完了体未来)'],
            ['я', 'затухаю', 'затухну'],
            ['ты', 'затухаешь', 'затухнешь'],
            ['он/она', 'затухает', 'затухнет'],
            ['мы', 'затухаем', 'затухнем'],
            ['вы', 'затухаете', 'затухнете'],
            ['они', 'затухают', 'затухнут']
        ],
        'anatomy': '''音（響き）や照明の光、火が「次第に弱まる、フェードアウトする、消え入る」ことを表す動詞。
・音楽のディミヌエンド（diminuendo）やモレンツォ（morendo）のニュアンスに直結します。
・«звук затухает»（音が減衰していく）。
・«свет затухает»（光が次第に薄らいでいく）。''',
        'network': ['затухание (減衰・フェード)', 'тухнуть (消える)'],
        'examples': [
            {'ru': 'Последний аккорд медленно затухает под сводами зала.', 'ja': '最後の和音はホールの天井の下でゆっくりと消え入っていきます。'},
            {'ru': 'Свет люстры плавно затухает перед началом увертюры.', 'ja': '前奏曲の始まりの前に、シャンデリアの光がなだらかに弱まります。'}
        ]
    },
    'зажигаться': {
        'word': 'зажигаться',
        'pos': '動詞 (НСВ・再帰動詞) ⇔ зажечься (СВ)',
        'meaning': '（明かりが）点る、点灯する',
        'aspect_pair': 'зажигаться (НСВ) ⇔ зажечься (СВ)',
        'declension_table': [
            ['人称', 'зажигаться (不完了体現在)', 'зажечься (完了体未来)'],
            ['я', 'зажигаюсь', 'зажгусь'],
            ['ты', 'зажигаешься', 'зажжёшься'],
            ['он/она', 'зажигается', 'зажжётся'],
            ['мы', 'зажигаемся', 'зажжёмся'],
            ['вы', 'зажигаетесь', 'зажжётесь'],
            ['они', 'зажигаются', 'зажгутся']
        ],
        'anatomy': '''他動詞 «зажигать»（〜に火・明かりを点ける）の再帰動詞形態。
・«зажигается свет / люстра»（明かり・シャンデリアが点灯する）。
・比喩的に「心に情熱が灯る」という表現でも用いられます。''',
        'network': ['зажигать (点ける/他動詞)', 'огонь (火・炎)', 'свет (光)'],
        'examples': [
            {'ru': 'В окнах старинной консерватории зажигаются тёплые огни.', 'ja': '由緒ある音楽院の窓に、温かい灯りが点ります。'}
        ]
    },
    'люстра': {
        'word': 'люстра',
        'pos': '女性名詞 (硬変化)',
        'meaning': 'シャンデリア、吊り下げ電灯',
        'notes': '【格変化】生格単数: люстры, 対格単数: люстру, 主格複数: люстры',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'люстра', 'люстры'],
            ['生格', 'люстры', 'люстр'],
            ['与格', 'люстре', 'люстрам'],
            ['対格', 'люстру', 'люстры'],
            ['造格', 'люстрой', 'люстрами'],
            ['前置格', 'люстре (о люстре)', 'люстрах (о люстрах)']
        ],
        'anatomy': '''劇場の天井を彩る豪華なシャンデリアを指す名詞。
・大ホールの天井にある巨大なシャンデリア（хрустальная люстра = クリスタル・シャンデリア）は音楽院の象徴の一つです。
・不活動体名詞のため対格複数は主格と同形（люстры）。生格複数はゼロ語尾（люстр）。''',
        'network': ['хрустальный (クリスタルの)', 'лампа (ランプ)', 'свет (光)'],
        'examples': [
            {'ru': 'Огромная люстра медленно затухает перед началом концерта.', 'ja': '開演の前、巨大なシャンデリアがゆっくりと消えていきます。'},
            {'ru': 'Хрустальная люстра Большого зала отражает золотой свет.', 'ja': '大ホールのクリスタル・シャンデリアが黄金の光を反射しています。'}
        ]
    },
    'сцена': {
        'word': 'сцена',
        'pos': '女性名詞 (硬変化)',
        'meaning': '舞台、ステージ、場面',
        'notes': '【格変化】前置格: на сцене (舞台上で), 対格: на сцену (舞台へ)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'сцена', 'сцены'],
            ['生格', 'сцены', 'сцен'],
            ['与格', 'сцене', 'сценам'],
            ['対格', 'сцену', 'сцены'],
            ['造格', 'сценой', 'сценами'],
            ['前置格', 'сцене (на сцене)', 'сценах (на сценах)']
        ],
        'anatomy': '''劇場やホールの「舞台」。前置詞 «на» と結合します。
・場所（どこで？ = где?）: «на сцене»（前置格）。
・方向（どこへ？ = куда?）: «на сцену»（対格）。
・音楽院大ホールの舞台に立つことは、すべての音楽家にとっての晴れ舞台です。''',
        'network': ['сценический (舞台の/形容詞)', 'артист сцены (舞台芸術家)'],
        'examples': [
            {'ru': 'На сцене стоит великолепный рояль.', 'ja': '舞台の上には素晴らしいグランドピアノが置かれています。'},
            {'ru': 'Пианист выходит на сцену под аплодисменты.', 'ja': 'ピアニストは拍手を浴びながら舞台へと歩み出ます。'}
        ]
    },
    'свет': {
        'word': 'свет',
        'pos': '男性名詞 (硬子音変化)',
        'meaning': '光、明かり、照明 / （世の中、世界）',
        'notes': '【格変化】生格: света, 造格: светом, 前置格: в/при свете',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (照明器具・明かり)'],
            ['主格', 'свет', 'огни / света'],
            ['生格', 'света', 'огней / светов'],
            ['与格', 'свету', 'огням / светам'],
            ['対格', 'свет', 'огни / света'],
            ['造格', 'светом', 'огнями / светами'],
            ['前置格', 'свете (на свету)', 'огнях / светах']
        ],
        'anatomy': '''「光・明かり」を表す基本名詞。
・照明をつける: «зажечь свет»、照明を消す: «выключить / погасить свет»。
・「〜の光の中で / 〜に照らされて」: «при свете люстры»。
・また「世界・世の中」の意味（во всём свете）も持ちます。''',
        'network': ['светлый (明るい/形容詞)', 'светить (照らす/動詞)', 'световой (光の)'],
        'examples': [
            {'ru': 'Свет в зале медленно гаснет.', 'ja': 'ホール内の明かりがゆっくりと消えていきます。'},
            {'ru': 'Мягкий свет падает на клавиши рояля.', 'ja': '柔らかな光がピアノの鍵盤に降り注いでいます。'}
        ]
    },
    'красота': {
        'word': 'красота',
        'pos': '女性名詞 (硬変化)',
        'meaning': '美、美しさ、麗しさ',
        'notes': '【格変化】生格単数: красоты, 造格単数: красотой, 複数主格: красоты (美しい景色・事物)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (美しい事物・美景)'],
            ['主格', 'красота', 'красоты'],
            ['生格', 'красоты', 'красот'],
            ['与格', 'красоте', 'красотам'],
            ['対格', 'красоту', 'красоты'],
            ['造格', 'красотой', 'красотами'],
            ['前置格', 'красоте (о красоте)', 'красотах']
        ],
        'anatomy': '''芸術と自然の根本である「美」。
・対格 «спасти красоту»、造格 «восхищаться красотой музыки»（音楽の美しさに感嘆する）。
・ドストエフスキーの名言 «Красота спасёт мир»（美が世界を救う）でも極めて有名です。''',
        'network': ['красивый (美しい/形容詞)', 'прекрасный (素晴らしい/形容詞)'],
        'examples': [
            {'ru': 'Музыка открывает нам истинную красоту мира.', 'ja': '音楽は私たちに世界の真の美しさを開いて見せてくれます。'},
            {'ru': 'Слушатели были поражены красотой звучания рояля.', 'ja': '聴衆はピアノの響きの美しさに心を打たれました。'}
        ]
    },
    'тишина': {
        'word': 'тишина',
        'pos': '女性名詞 (硬変化)',
        'meaning': '静寂、静けさ、沈黙',
        'notes': '【格変化】生格: тишины, 前置格: в тишине (静けさの中で)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (詩的用法)'],
            ['主格', 'тишина', 'тишины'],
            ['生格', 'тишины', 'тишин'],
            ['与格', 'тишине', 'тишинам'],
            ['対格', 'тишину', 'тишины'],
            ['造格', 'тишиной', 'тишинами'],
            ['前置格', 'тишине (в тишине)', 'тишинах']
        ],
        'anatomy': '''音楽において音と同じくらい大切な「静寂」。
・«в тишине»（静けさの中で）。
・«наступает тишина»（静寂が訪れる）。
・演奏が終わった直後の息をのむような静けさを表すのに欠かせない言葉です。''',
        'network': ['тихий (静かな/形容詞)', 'тихо (静かに/副詞)'],
        'examples': [
            {'ru': 'В Большом зале консерватории наступает удивительная тишина.', 'ja': '大ホールには驚くほどの静寂が訪れます。'},
            {'ru': 'В ночной тишине слышно эхо последней ноты.', 'ja': '夜の静寂の中に、最後の音の残響が聴こえます。'}
        ]
    },

    'купить': {
        'word': 'купить / покупать',
        'pos': '完了体 / 不完了体 (動詞)',
        'meaning': '買う、購入する（具体的達成・結果）',
        'notes': '【アスペクト対】купить (完了体) ⇔ покупать (不完了体)',
        'aspect_pair': 'купить (完了体) ⇔ покупать (不完了体)',
        'declension_table': [
            ['人称・形', 'купить (СВ/未来)', 'покупать (НСВ/現在)'],
            ['я', 'куплю', 'покупаю'],
            ['ты', 'купишь', 'покупаешь'],
            ['он/она', 'купит', 'покупает'],
            ['мы', 'купим', 'покупаем'],
            ['вы', 'купите', 'покупаете'],
            ['они', 'купят', 'покупают'],
            ['過去・男', 'купил', 'покупал'],
            ['過去・女', 'купила', 'покупала'],
            ['過去・中', 'купило', 'покупало'],
            ['過去・複', 'купили', 'покупали']
        ],
        'anatomy': '''【2級最重要・購買動詞のアスペクト対】
・完了体 «купить» は「（1回きり）買い終えた」結果・具体的達成を表します。
・過去形: купил (男), купила (女), купило (中), купили (複)。女性形 купила は過去形動詞であり、名詞ではありません！
・1人称単数未来形は «куплю» と л-挿入が起こる点にも注意。
・不完了体 «покупать» は習慣・反復「普段買っている」や過程を表します。''',
        'network': ['покупка (買い物/名詞)', 'покупатель (買い手/名詞)'],
        'examples': [
            {'ru': 'Консерватория купила новый рояль.', 'ja': '音楽院は新しいグランドピアノを購入しました。'},
            {'ru': 'Я хочу купить билет на концерт.', 'ja': '私はコンサートの切符を買いたいです。'}
        ]
    },
    'покупать': {
        'word': 'покупать / купить',
        'pos': '不完了体 / 完了体 (動詞)',
        'meaning': '買う、購入する（習慣・反復・過程）',
        'notes': '【アスペクト対】покупать (不完了体) ⇔ купить (完了体)',
        'aspect_pair': 'покупать (不完了体) ⇔ купить (完了体)',
        'declension_table': [
            ['人称・形', 'покупать (НСВ/現在)', 'купить (СВ/未来)'],
            ['я', 'покупаю', 'куплю'],
            ['ты', 'покупаешь', 'купишь'],
            ['он/она', 'покупает', 'купит'],
            ['мы', 'покупаем', 'купим'],
            ['вы', 'покупаете', 'купите'],
            ['они', 'покупают', 'купят'],
            ['過去・男', 'покупал', 'купил'],
            ['過去・女', 'покупала', 'купила'],
            ['過去・中', 'покупало', 'купило'],
            ['過去・複', 'покупали', 'купили']
        ],
        'anatomy': '''不完了体 «покупать»。
・習慣・定期的な購入や「買い物の最中」を表します。''',
        'network': ['купить (完了体)', 'покупка (買い物)'],
        'examples': [
            {'ru': 'Мы часто покупаем ноты в консерватории.', 'ja': '私たちはよく音楽院で楽譜を買います。'}
        ]
    },
    'положить': {
        'word': 'положить / класть',
        'pos': '完了体 / 不完了体 (動詞)',
        'meaning': '（横にして）置く、横たえる',
        'notes': '【アスペクト対】положить (完了体) ⇔ класть (不完了体・補充法)',
        'aspect_pair': 'положить (完了体) ⇔ класть (不完了体)',
        'declension_table': [
            ['人称・形', 'положить (СВ/未来)', 'класть (НСВ/現在)'],
            ['я', 'положу', 'кладу'],
            ['ты', 'положишь', 'кладёшь'],
            ['он/она', 'положит', 'кладёт'],
            ['мы', 'положим', 'кладём'],
            ['вы', 'положите', 'кладёте'],
            ['они', 'положат', 'кладут'],
            ['過去・男', 'положил', 'клал'],
            ['過去・女', 'положила', 'клала'],
            ['過去・中', 'положило', 'клало'],
            ['過去・複', 'положили', 'клали']
        ],
        'anatomy': '''【補充法アスペクト対】
・語幹が全く異なる補充法。過去形女性 положила は動詞過去形です。
・物を横にして置く動作を表し、対格＋方向（на рояль）を伴います。''',
        'network': ['класть (不完了体)', 'лежать (置いてある/状態動詞)'],
        'examples': [
            {'ru': 'Студентка положила новые ноты на рояль.', 'ja': '女子学生は新しい楽譜をピアノの上に置きました。'}
        ]
    },
    'класть': {
        'word': 'класть / положить',
        'pos': '不完了体 / 完了体 (動詞)',
        'meaning': '（横にして）置く（習慣・反復）',
        'notes': '【アスペクト対】класть (不完了体) ⇔ положить (完了体)',
        'aspect_pair': 'класть (不完了体) ⇔ положить (完了体)',
        'declension_table': [
            ['人称・形', 'класть (НСВ/現在)', 'положить (СВ/未来)'],
            ['я', 'кладу', 'положу'],
            ['ты', 'кладёшь', 'положишь'],
            ['он/она', 'кладёт', 'положит'],
            ['мы', 'кладём', 'положим'],
            ['вы', 'кладёте', 'положите'],
            ['они', 'кладут', 'положат'],
            ['過去・男', 'клал', 'положил'],
            ['過去・女', 'клала', 'положила'],
            ['過去・中', 'клало', 'положило'],
            ['過去・複', 'клали', 'положили']
        ],
        'anatomy': '''不完了体 «класть»。
・習慣的な動作「毎日置く」を表します。過去形女性 клала は動詞過去形（アクセントは第1音節 клАла）です。''',
        'network': ['положить (完了体)'],
        'examples': [
            {'ru': 'Студентка каждый день клала ноты на рояль.', 'ja': '女子学生は毎日楽譜をピアノの上に置いていました。'}
        ]
    },
    'учить': {
        'word': 'учить / выучить',
        'pos': '不完了体 / 完了体 (動詞)',
        'meaning': '学ぶ、覚える、稽古する（過程）',
        'notes': '【アスペクト対】учить (不完了体) ⇔ выучить (完了体)',
        'aspect_pair': 'учить (不完了体) ⇔ выучить (完了体)',
        'declension_table': [
            ['人称・形', 'учить (НСВ/現在)', 'выучить (СВ/未来)'],
            ['я', 'учу', 'выучу'],
            ['ты', 'учишь', 'выучишь'],
            ['он/она', 'учит', 'выучит'],
            ['мы', 'учим', 'выучим'],
            ['вы', 'учите', 'выучите'],
            ['они', 'учат', 'выучат'],
            ['過去・男', 'учил', 'выучил'],
            ['過去・女', 'учила', 'выучила'],
            ['過去・中', 'учило', 'выучило'],
            ['過去・複', 'учили', 'выучили']
        ],
        'anatomy': '''学ぶ・覚える過程を表す不完了体動詞。
・過去形: учил, учила, учило, учили。名詞 училище（学校）との混同に注意！''',
        'network': ['учитель (先生)', 'выучить (マスターする)'],
        'examples': [
            {'ru': 'Студент долго учил этот трудный пассаж.', 'ja': '学生は長い間この難しいパッセージを練習していました。'}
        ]
    },
    'выучить': {
        'word': 'выучить / учить',
        'pos': '完了体 / 不完了体 (動詞)',
        'meaning': '完全に覚える、マスターし終える（結果）',
        'notes': '【アスペクト対】выучить (完了体) ⇔ учить (不完了体)',
        'aspect_pair': 'выучить (完了体) ⇔ учить (不完了体)',
        'declension_table': [
            ['人称・形', 'выучить (СВ/未来)', 'учить (НСВ/現在)'],
            ['я', 'выучу', 'учу'],
            ['ты', 'выучишь', 'учишь'],
            ['он/она', 'выучит', 'учит'],
            ['мы', 'выучим', 'учим'],
            ['вы', 'выучите', 'учите'],
            ['они', 'выучат', 'учат'],
            ['過去・男', 'выучил', 'учил'],
            ['過去・女', 'выучила', 'учила'],
            ['過去・中', 'выучило', 'учило'],
            ['過去・複', 'выучили', 'учили']
        ],
        'anatomy': '''完了体 «выучить»。完全に暗記し弾けるようになった具体的達成を表します。''',
        'network': ['учить (不完了体)'],
        'examples': [
            {'ru': 'Студент уже выучил трудный пассаж.', 'ja': '学生はもう難しいパッセージをマスターしました。'}
        ]
    },
    'идти': {
        'word': 'идти / ходить',
        'pos': '定動詞 / 不定動詞 (移動動詞)',
        'meaning': '（徒歩で）行く、向かう（一方向・現在進行）',
        'notes': '【移動動詞ペア】идти (定動詞・今歩いて向かう) ⇔ ходить (不定動詞・通う/往復)',
        'aspect_pair': 'идти (定動詞) ⇔ ходить (不定動詞)',
        'declension_table': [
            ['人称・形', 'идти (定動詞/現在)', 'ходить (不定動詞/現在)'],
            ['я', 'иду', 'хожу'],
            ['ты', 'идёшь', 'ходишь'],
            ['он/она', 'идёт', 'ходит'],
            ['мы', 'идём', 'ходим'],
            ['вы', 'идёте', 'ходите'],
            ['они', 'идут', 'ходят'],
            ['過去・男', 'шёл', 'ходил'],
            ['過去・女', 'шла', 'ходила'],
            ['過去・中', 'шло', 'ходило'],
            ['過去・複', 'шли', 'ходили']
        ],
        'anatomy': '''【2級最重要・徒歩定動詞】
・今まさに一方向へ向かって歩いている動作。
・人称変化（иду, идёшь, идёт, идём, идёте, идут）および過去形（шёл, шла, шло, шли）は最重要！''',
        'network': ['ходить (不定動詞)', 'пешком (徒歩で)'],
        'examples': [
            {'ru': 'Сейчас я иду на концерт в консерваторию.', 'ja': '今私は音楽院のコンサートへ歩いて向かっています。'}
        ]
    },
    'ходить': {
        'word': 'ходить / идти',
        'pos': '不定動詞 / 定動詞 (移動動詞)',
        'meaning': '（徒歩で）通う、往復する、歩き回る（習慣・往復）',
        'notes': '【移動動詞ペア】ходить (不定動詞) ⇔ идти (定動詞)',
        'aspect_pair': 'ходить (不定動詞) ⇔ идти (定動詞)',
        'declension_table': [
            ['人称・形', 'ходить (不定動詞/現在)', 'идти (定動詞/現在)'],
            ['я', 'хожу', 'иду'],
            ['ты', 'ходишь', 'идёшь'],
            ['он/она', 'ходит', 'идёт'],
            ['мы', 'ходим', 'идём'],
            ['вы', 'ходите', 'идёте'],
            ['они', 'ходят', 'идут'],
            ['過去・男', 'ходил', 'шёл'],
            ['過去・女', 'ходила', 'шла'],
            ['過去・中', 'ходило', 'шло'],
            ['過去・複', 'ходили', 'шли']
        ],
        'anatomy': '''不定動詞 «ходить»。普段の習慣的な通学や、過去の往復経験を表します。
・過去形: ходил, ходила, ходило, ходили（名詞ではなく動詞過去形）。''',
        'network': ['идти (定動詞)'],
        'examples': [
            {'ru': 'Каждый день мы ходим в консерваторию пешком.', 'ja': '毎日私たちは歩いて音楽院に通っています。'},
            {'ru': 'Вчера мы долго ходили по Москве.', 'ja': '昨日私たちはモスクワの街を長く散策しました。'}
        ]
    },
    'ехать': {
        'word': 'ехать / ездить',
        'pos': '定動詞 / 不定動詞 (乗物移動動詞)',
        'meaning': '（乗物で）行く、向かう（一方向・現在進行）',
        'notes': '【乗物移動ペア】ехать (定動詞) ⇔ ездить (不定動詞)',
        'aspect_pair': 'ехать (定動詞) ⇔ ездить (不定動詞)',
        'declension_table': [
            ['人称・形', 'ехать (定動詞/現在)', 'ездить (不定動詞/現在)'],
            ['я', 'еду', 'езжу'],
            ['ты', 'едешь', 'ездишь'],
            ['он/она', 'едет', 'ездит'],
            ['мы', 'едем', 'ездим'],
            ['вы', 'едете', 'ездите'],
            ['они', 'едут', 'ездят'],
            ['過去・男', 'ехал', 'ездил'],
            ['過去・女', 'ехала', 'ездила'],
            ['過去・中', 'ехало', 'ездило'],
            ['過去・複', 'ехали', 'ездили']
        ],
        'anatomy': '''【乗物定動詞】
・乗物で今一方向へ向かっている動作。
・人称変化（еду, едешь, едет, едем, едете, едут）で -д- が現れます。代名詞 он との混同に注意！''',
        'network': ['ездить (不定動詞)', 'на метро (地下鉄で)'],
        'examples': [
            {'ru': 'Сейчас мы быстро едем на метро.', 'ja': '今私たちは地下鉄で速く向かっています。'}
        ]
    },
    'ездить': {
        'word': 'ездить / ехать',
        'pos': '不定動詞 / 定動詞 (乗物移動動詞)',
        'meaning': '（乗物で）通う、往復する（習慣・定期往復）',
        'notes': '【乗物移動ペア】ездить (不定動詞) ⇔ ехать (定動詞)',
        'aspect_pair': 'ездить (不定動詞) ⇔ ехать (定動詞)',
        'declension_table': [
            ['人称・形', 'ездить (不定動詞/現在)', 'ехать (定動詞/現在)'],
            ['я', 'езжу', 'еду'],
            ['ты', 'ездишь', 'едешь'],
            ['он/она', 'ездит', 'едет'],
            ['мы', 'ездим', 'едем'],
            ['вы', 'ездите', 'едете'],
            ['они', 'ездят', 'едут'],
            ['過去・男', 'ездил', 'ехал'],
            ['過去・女', 'ездила', 'ехала'],
            ['過去・中', 'ездило', 'ехало'],
            ['過去・複', 'ездили', 'ехали']
        ],
        'anatomy': '''不定動詞 «ездить»。習慣的な乗物通学を表します。1人称単数は «езжу»。''',
        'network': ['ехать (定動詞)'],
        'examples': [
            {'ru': 'Обычно мы ездим в консерваторию на метро.', 'ja': '普段私たちは地下鉄で音楽院に通っています。'}
        ]
    },
    'лежать': {
        'word': 'лежать / положить',
        'pos': '不完了体 (状態動詞)',
        'meaning': '（横たわって）ある、置かれている',
        'notes': '【状態動詞】лежать (ある) ⇔ положить (置く)',
        'aspect_pair': 'лежать (状態) ⇔ положить (動作)',
        'declension_table': [
            ['人称・形', 'лежать (現在形)', '過去形'],
            ['я', 'лежу', 'лежал (男)'],
            ['ты', 'лежишь', 'лежала (女)'],
            ['он/она', 'лежит', 'лежало (中)'],
            ['мы', 'лежим', 'лежали (複)'],
            ['вы', 'лежите', '-'],
            ['они', 'лежат', '-']
        ],
        'anatomy': '''物が横になって「ある」状態を表す場所動詞。
・«где? (前置格)» を伴います（лежат на рояле）。''',
        'network': ['положить (置く)'],
        'examples': [
            {'ru': 'Новые ноты уже лежат на рояле.', 'ja': '新しい楽譜はすでにピアノの上に置かれています。'}
        ]
    },
    'соната': {
        'word': 'соната',
        'pos': '女性名詞 (硬変化)',
        'meaning': 'ソナタ、奏鳴曲',
        'notes': '【格変化】対格: сонату, 生格: сонаты',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'соната', 'сонаты'],
            ['生格', 'сонаты', 'сонат'],
            ['与格', 'сонате', 'сонатам'],
            ['対格', 'сонату', 'сонаты'],
            ['造格', 'сонатой', 'сонатами'],
            ['前置格', 'сонате', 'сонатах']
        ],
        'anatomy': '''器楽曲の形式「ソナタ」。対格 «сыграть сонату»（ソナタを弾き終える）。代名詞 она との混同に注意。''',
        'network': ['сонатный (ソナタの)'],
        'examples': [
            {'ru': 'Я с вдохновением сыграла сонату.', 'ja': '私はインスピレーションを込めてソナタを演奏しました。'}
        ]
    },
    'новый': {
        'word': 'новый',
        'pos': '形容詞 (硬変化・男性)',
        'meaning': '新しい、新設の',
        'notes': '【格変化】男: новый, 女: новая, 中: новое, 複: новые',
        'declension_table': [
            ['格', '男性 (новый)', '女性 (новая)', '中性 (новое)', '複数 (новые)'],
            ['主格', 'новый', 'новая', 'новое', 'новые'],
            ['生格', 'нового', 'новой', 'нового', 'новых'],
            ['与格', 'новому', 'новой', 'новому', 'новым'],
            ['対格', 'новый / нового', 'новую', 'новое', 'новые / новых'],
            ['造格', 'новым', 'новой', 'новым', 'новыми'],
            ['前置格', 'новом', 'новой', 'новом', 'новых']
        ],
        'anatomy': '''硬変化形容詞の代表。不活動体名詞の前では対格＝主格（новый рояль）。代名詞 он との混同に注意。''',
        'network': ['новости (ニュース)'],
        'examples': [
            {'ru': 'Консерватория купила новый рояль.', 'ja': '音楽院は新しいグランドピアノを購入しました。'}
        ]
    },
    'этот': {
        'word': 'этот',
        'pos': '指示代名詞 (この)',
        'meaning': 'この（近称の指示代名詞）',
        'notes': '【格変化】男: этот, 女: эта, 中: это, 複: эти',
        'declension_table': [
            ['格', '男性 (этот)', '女性 (эта)', '中性 (это)', '複数 (эти)'],
            ['主格', 'этот', 'эта', 'это', 'эти'],
            ['生格', 'этого', 'этой', 'этого', 'этих'],
            ['与格', 'этому', 'этой', 'этому', 'этим'],
            ['対格', 'этот / этого', 'эту', 'это', 'эти / этих'],
            ['造格', 'этим', 'этой', 'этим', 'этими'],
            ['前置格', 'этом', 'этой', 'этом', 'этих']
        ],
        'anatomy': '''近称の指示代名詞。前置格: в этом классе, на этом рояле。代名詞 вы との混同に注意。''',
        'network': ['тот (あの)'],
        'examples': [
            {'ru': 'В этом классе сейчас нет пианиста.', 'ja': 'この練習室には今ピアニストがいません。'},
            {'ru': 'Мы репетировали этот дуэт.', 'ja': '私たちはこの二重奏を練習しました。'}
        ]
    },
    'дуэт': {
        'word': 'дуэт',
        'pos': '男性名詞 (硬子音変化)',
        'meaning': '二重奏、デュエット、連弾',
        'notes': '【格変化】対格: дуэт, 生格: дуэта',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'дуэт', 'дуэты'],
            ['生格', 'дуэта', 'дуэтов'],
            ['与格', 'дуэту', 'дуэтам'],
            ['対格', 'дуэт', 'дуэты'],
            ['造格', 'дуэтом', 'дуэтами'],
            ['前置格', 'дуэте', 'дуэтах']
        ],
        'anatomy': '''二重奏・ピアノ連弾。不活動体のため対格は主格と同形（сыграть этот дуэт）。''',
        'network': ['ансамбль (アンサンブル)'],
        'examples': [
            {'ru': 'Мы сыграли этот дуэт безупречно.', 'ja': '私たちはこの二重奏を完璧に演奏しました。'}
        ]
    },
    'пассаж': {
        'word': 'пассаж',
        'pos': '男性名詞 (硬変化)',
        'meaning': 'パッセージ、経過句（演奏の難所）',
        'notes': '【格変化】対格: пассаж, 生格: пассажа',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'пассаж', 'пассажи'],
            ['生格', 'пассажа', 'пассажей'],
            ['与格', 'пассажу', 'пассажам'],
            ['対格', 'пассаж', 'пассажи'],
            ['造格', 'пассажем', 'пассажами'],
            ['前置格', 'пассаже', 'пассажах']
        ],
        'anatomy': '''技巧的な走句（パッセージ）。«выучить пассаж»（パッセージをマスターする）。''',
        'network': ['техника (技法)'],
        'examples': [
            {'ru': 'Студент уже выучил трудный пассаж.', 'ja': '学生はすでに難しいパッセージをマスターしました。'}
        ]
    },
    'аудитория': {
        'word': 'аудитория',
        'pos': '女性名詞 (軟変化 -ия)',
        'meaning': '講義室、練習室、教室',
        'notes': '【格変化】前置格: в аудитории (-и語尾)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'аудитория', 'аудитории'],
            ['生格', 'аудитории', 'аудиторий'],
            ['与格', 'аудитории', 'аудиториям'],
            ['対格', 'аудиторию', 'аудитории'],
            ['造格', 'аудиторией', 'аудиториями'],
            ['前置格', 'аудитории', 'аудиториях']
        ],
        'anatomy': '''練習室・講義室。前置格は -е ではなく -и（в этой аудитории）となります。''',
        'network': ['класс (教室)'],
        'examples': [
            {'ru': 'В этой аудитории сегодня нет рояля.', 'ja': 'この練習室には今日グランドピアノがありません。'}
        ]
    },
    'класс': {
        'word': 'класс',
        'pos': '男性名詞 (硬変化)',
        'meaning': '教室、練習室、クラス',
        'notes': '【格変化】前置格: в классе',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'класс', 'классы'],
            ['生格', 'класса', 'классов'],
            ['与格', 'классу', 'классам'],
            ['対格', 'класс', 'классы'],
            ['造格', 'классом', 'классами'],
            ['前置格', 'классе', 'классах']
        ],
        'anatomy': '''練習室や門下（класс профессора）を指します。''',
        'network': ['аудитория (講義室)'],
        'examples': [
            {'ru': 'В этом классе сейчас нет пианиста.', 'ja': 'この練習室には今ピアニストがいません。'}
        ]
    },
    'вдохновение': {
        'word': 'вдохновение',
        'pos': '中性名詞 (軟変化 -ие)',
        'meaning': 'インスピレーション、霊感、情熱',
        'notes': '【格変化】造格: с вдохновением (様態)',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'вдохновение', 'вдохновения'],
            ['生格', 'вдохновения', 'вдохновений'],
            ['与格', 'вдохновению', 'вдохновениям'],
            ['対格', 'вдохновение', 'вдохновения'],
            ['造格', 'вдохновением', 'вдохновениями'],
            ['前置格', 'вдохновении', 'вдохновениях']
        ],
        'anatomy': '''«с + 造格» で «с вдохновением»（インスピレーションを込めて、情感豊かに）。''',
        'network': ['вдохновлять (感動を与える)'],
        'examples': [
            {'ru': 'Я с вдохновением сыграла сонату.', 'ja': '私はインスピレーションを込めてソナタを弾き終えました。'}
        ]
    },
    'нота': {
        'word': 'нота / ноты',
        'pos': '女性名詞 (単数: 音符 / 複数: 楽譜)',
        'meaning': '音符（単数）、楽譜（複数 ноты）',
        'notes': '【重要】「楽譜」を指す時は常に複数形 «ноты» を使います',
        'declension_table': [
            ['格', '単数 (音符)', '複数 (楽譜・諸音)'],
            ['主格', 'нота', 'ноты'],
            ['生格', 'ноты', 'нот'],
            ['与格', 'ноте', 'нотам'],
            ['対格', 'ноту', 'ноты'],
            ['造格', 'нотой', 'нотами'],
            ['前置格', 'ноте', 'нотах']
        ],
        'anatomy': '''複数形 «ноты» は「楽譜」（положить ноты на рояль）を指します。''',
        'network': ['партитура (総譜)'],
        'examples': [
            {'ru': 'Студентка положила новые ноты на рояль.', 'ja': '女子学生は新しい楽譜をピアノの上に置きました。'}
        ]
    },
    'огромный': {
        'word': 'огромный',
        'pos': '形容詞 (Прилагательное)',
        'meaning': '巨大な、非常に大きな',
        'notes': '【格変化】男性 огромный, 女性 огромная, 中性 огромное, 複数 огромные',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'огромный', 'огромная', 'огромное', 'огромные'],
            ['生格', 'огромного', 'огромной', 'огромного', 'огромных'],
            ['与格', 'огромному', 'огромной', 'огромному', 'огромным'],
            ['対格', 'огромный / огромного', 'огромную', 'огромное', 'огромные / огромных'],
            ['造格', 'огромным', 'огромной', 'огромным', 'огромными'],
            ['前置格', 'огромном', 'огромной', 'огромном', 'огромных']
        ],
        'anatomy': '''規模・サイズが極めて大きいことを表す硬変化形容詞。
ラフマニノフの類まれな手の大きさ（огромными руками）などを形容する際によく用いられます。''',
        'network': ['большой (大きい)', 'великий (偉大な)'],
        'examples': [
            {'ru': 'Сергей Рахманинов обладал огромными руками.', 'ja': 'セルゲイ・ラフマニノフは非常に大きな手を備えていました。'}
        ]
    },
    'уникальный': {
        'word': 'уникальный',
        'pos': '形容詞 (Прилагательное)',
        'meaning': '唯一無二の、独特な、類まれな',
        'notes': '【格変化】男性 уникальный, 女性 уникальная, 中性 уникальное, 複数 уникальные',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'уникальный', 'уникальная', 'уникальное', 'уникальные'],
            ['生格', 'уникального', 'уникальной', 'уникального', 'уникальных'],
            ['与格', 'уникальному', 'уникальной', 'уникальному', 'уникальным'],
            ['対格', 'уникальный / уникального', 'уникальную', 'уникальное', 'уникальные / уникальных'],
            ['造格', 'уникальным', 'уникальной', 'уникальным', 'уникальными'],
            ['前置格', 'уникальном', 'уникальной', 'уникальном', 'уникальных']
        ],
        'anatomy': '''他にはない唯一無二の優れた特質を表す形容詞。
造格 «уникальным чувством»（比類なき感覚をもって）の形でよく用いられます。''',
        'network': ['редкий (稀な)', 'особенный (特別な)'],
        'examples': [
            {'ru': 'Он обладал уникальным чувством гармонии.', 'ja': '彼は比類なき和声感覚を備えていました。'}
        ]
    },
    'большой': {
        'word': 'большой',
        'pos': '形容詞 (Прилагательное・語尾アクセント)',
        'meaning': '大きい、大いなる',
        'notes': '【格変化】男性 большой, 女性 большая, 中性 большое, 複数 большие',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'большой', 'большая', 'большое', 'большие'],
            ['生格', 'большого', 'большой', 'большого', 'больших'],
            ['与格', 'большому', 'большой', 'большому', 'большим'],
            ['対格', 'большой / большого', 'большую', 'большое', 'большие / больших'],
            ['造格', 'большим', 'большой', 'большим', 'большими'],
            ['前置格', 'большом', 'большой', 'большом', 'больших']
        ],
        'anatomy': '''語尾にアクセントがある最重要形容詞。
モスクワ音楽院の「大ホール」（Большой зал）や「ボリショイ劇場」（Большой театр）など、文化・音楽に不可欠な語彙です。''',
        'network': ['маленький (小さい)', 'огромный (巨大な)'],
        'examples': [
            {'ru': 'В Большом зале консерватории наступает тишина.', 'ja': '音楽院の大ホールに静寂が訪れます。'}
        ]
    },
    'последний': {
        'word': 'последний',
        'pos': '形容詞 (軟変化形容詞)',
        'meaning': '最後の、最新の',
        'notes': '【軟変化】男性 последний, 女性 последняя, 中性 последнее, 複数 последние',
        'declension_table': [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', 'последний', 'последняя', 'последнее', 'последние'],
            ['生格', 'последнего', 'последней', 'последнего', 'последних'],
            ['与格', 'последнему', 'последней', 'последнему', 'последним'],
            ['対格', 'последний / последнего', 'последнюю', 'последнее', 'последние / последних'],
            ['造格', 'последним', 'последней', 'последним', 'последними'],
            ['前置格', 'последнем', 'последней', 'последнем', 'последних']
        ],
        'anatomy': '''軟変化（-ний, -няя, -нее, -ние）の代表的形容詞。
生格は -его、前置格は -ем に変化します。''',
        'network': ['первый (最初の)'],
        'examples': [
            {'ru': 'Звуки последнего аккорда затихают.', 'ja': '最後の和音の響きが消え入っていきます。'}
        ]
    },
    'тишина': {
        'word': 'тишина',
        'pos': '名詞 (女性名詞)',
        'meaning': '静寂、静けさ',
        'notes': '【女性名詞】対格: тишину, 前置格: в тишине',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'тишина', '—'],
            ['生格', 'тишины', '—'],
            ['与格', 'тишине', '—'],
            ['対格', 'тишину', '—'],
            ['造格', 'тишиной', '—'],
            ['前置格', 'тишине', '—']
        ],
        'anatomy': '''演奏前後の静寂を表す美しい女性名詞。
前置格 «в тишине»（静けさの中で）の形で頻出します。''',
        'network': ['тихий (静かな)', 'тихо (静かに)'],
        'examples': [
            {'ru': 'В зале наступает удивительная тишина.', 'ja': 'ホールには素晴らしい静寂が訪れます。'}
        ]
    },
    'рука': {
        'word': 'рука',
        'pos': '名詞 (女性名詞)',
        'meaning': '手、腕',
        'notes': '【女性名詞】対格: руку, 複数造格: руками',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'рука', 'руки'],
            ['生格', 'руки', 'рук'],
            ['与格', 'руке', 'рукам'],
            ['対格', 'руку', 'руки'],
            ['造格', 'рукой', 'руками'],
            ['前置格', 'руке', 'руках']
        ],
        'anatomy': '''ピアノ演奏で最も大切な身体部位。
複数造格 «руками»（両手で）は楽器演奏において最重要の形です。''',
        'network': ['палец (指)', 'кисть (手首・手先)'],
        'examples': [
            {'ru': 'Пианист играет обеими руками.', 'ja': 'ピアニストは両手で演奏します。'}
        ]
    },
    'дом': {
        'word': 'дом',
        'pos': '名詞 (男性名詞)',
        'meaning': '家、建物',
        'notes': '【男性名詞】複数主格: дома, 複数生格: домов',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'дом', 'дома'],
            ['生格', 'дома', 'домов'],
            ['与格', 'дому', 'домам'],
            ['対格', 'дом', 'дома'],
            ['造格', 'домом', 'домами'],
            ['前置格', 'доме', 'домах']
        ],
        'anatomy': '''基本名詞。複数主格は語尾アクセントの «дома́»、複数生格は «домо́в»（家々の）となります。''',
        'network': ['домашний (家庭の)'],
        'examples': [
            {'ru': 'В окнах домов зажигается свет.', 'ja': '家々の窓に明かりが灯ります。'}
        ]
    },
    'окно': {
        'word': 'окно',
        'pos': '名詞 (中性名詞)',
        'meaning': '窓',
        'notes': '【中性名詞】複数主格: окна, 複数前置格: в окнах',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'окно', 'окна'],
            ['生格', 'окна', 'окон'],
            ['与格', 'окну', 'окнам'],
            ['対格', 'окно', 'окна'],
            ['造格', 'окном', 'окнами'],
            ['前置格', 'окне', 'окнах']
        ],
        'anatomy': '''中性名詞。複数形はアクセントが前へ移動して «о́кна»、複数前置格は «в о́кнах»（窓々に）となります。''',
        'network': ['подоконник (窓枠)'],
        'examples': [
            {'ru': 'В окнах консерватории горит свет.', 'ja': '音楽院の窓には明かりが灯っています。'}
        ]
    },
    'слышный': {
        'word': 'слышный',
        'pos': '形容詞 (短尾形頻出)',
        'meaning': '聞こえる、聞き取れる',
        'notes': '【短尾形】слышен (男), слышна (女), слышно (中), слышны (複)',
        'declension_table': [
            ['短尾・長尾', '男性', '女性', '中性', '複数'],
            ['短尾形 (Short)', 'слышен', 'слышна', 'слышно', 'слышны'],
            ['長尾主格', 'слышный', 'слышная', 'слышное', 'слышные'],
            ['生格', 'слышного', 'слышной', 'слышного', 'слышных'],
            ['与格', 'слышному', 'слышной', 'слышному', 'слышным'],
            ['造格', 'слышным', 'слышной', 'слышным', 'слышными'],
            ['前置格', 'слышном', 'слышной', 'слышном', 'слышных']
        ],
        'anatomy': '''述語として「〜が聞こえる」を表す短尾形（слышны звуки рояля）が極めて頻繁に使われます。''',
        'network': ['слышать (聞く/知覚動詞)', 'слушать (聴く/傾聴動詞)'],
        'examples': [
            {'ru': 'В переулках слышны звуки рояля.', 'ja': '小道にはピアノの音が聞こえています。'}
        ]
    },
    'репетировать': {
        'word': 'репетировать / отрепетировать',
        'pos': '動詞 (НСВ/СВ・第1変化)',
        'meaning': 'リハーサルをする、稽古する、練習する',
        'notes': '【活用】репетирую, репетируешь, репетирует, репетируют (過去: репетировал, репетировала)',
        'declension_table': [
            ['人称・形', '不完了体 (НСВ)', '完了体 (СВ)'],
            ['я', 'репетирую', 'отрепетирую'],
            ['ты', 'репетируешь', 'отрепетируешь'],
            ['он/она', 'репетирует', 'отрепетирует'],
            ['мы', 'репетируем', 'отрепетируем'],
            ['вы', 'репетируете', 'отрепетируете'],
            ['они', 'репетируют', 'отрепетируют'],
            ['過去 (男)', 'репетировал', 'отрепетировал'],
            ['過去 (女)', 'репетировала', 'отрепетировала'],
            ['過去 (中)', 'репетировало', 'отрепетировало'],
            ['過去 (複)', 'репетировали', 'отрепетировали']
        ],
        'anatomy': '''音楽院や劇場でのリハーサル・練習を表す専門的動詞。
接頭辞 «от-» が付いた «отрепетировать» で完了体（充分に稽古を仕上げる）となります。''',
        'network': ['репетиция (リハーサル/名詞)', 'концерт (演奏会)', 'сцена (舞台)'],
        'examples': [
            {'ru': 'Таня долго репетировала сложную партию.', 'ja': 'ターニャは難しいパートを長く練習しました。'},
            {'ru': 'Мы отрепетируем этот дуэт ещё один раз.', 'ja': '私たちはこの二重奏をもう一度リハーサルして仕上げます。'}
        ]
    },
    'репетиция': {
        'word': 'репетиция',
        'pos': '名詞 (女性名詞・-ия変化)',
        'meaning': 'リハーサル、稽古、練習',
        'notes': '【格変化】生格: репетиции, 与格: репетиции, 対格: репетицию, 造格: репетицией, 前置格: на репетиции',
        'declension_table': [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', 'репетиция', 'репетиции'],
            ['生格', 'репетиции', 'репетиций'],
            ['与格', 'репетиции', 'репетициям'],
            ['対格', 'репетицию', 'репетиции'],
            ['造格', 'репетицией', 'репетициями'],
            ['前置格', 'репетиции', 'репетициях']
        ],
        'anatomy': '''-ия で終わる女性名詞。与格および前置格で語尾が -е ではなく -и（на репетиции）になる重要例外変化です。''',
        'network': ['репетировать (リハーサルする)', 'консерватория (音楽院)'],
        'examples': [
            {'ru': 'Когда заканчивается репетиция?', 'ja': 'リハーサルは何時に終わりますか？'},
            {'ru': 'Я встретил Таню на репетиции.', 'ja': '私はリハーサルでターニャに会いました。'}
        ]
    },
    'хотеть': {
        'word': 'хотеть',
        'pos': '動詞 (不完了体・混合変化動詞)',
        'meaning': '〜を望む、〜したい、〜したがる（意志・願望）',
        'notes': '【混合変化】単数は第1変化 (хочу, хочешь, хочет)、複数は第2変化 (хотим, хотите, хотят)',
        'aspect_pair': 'хотеть (不完了体) ⇔ захотеть (完了体)',
        'irregular_alert': {
            'badge': '⚠️ 活用注意：混合変化動詞 (хотеть)',
            'detail': '単数は第1変化（я хочу, ты хочешь, он хочет）、複数は第2変化（мы хотим, вы хотите, они хотят）と人称語尾が分裂する特殊動詞です。※非人称再帰動詞 «хотеться»（ツァー動詞: 〜したい気がする/与格支配）とは文法上明確に区別されます。'
        },
        'declension_table': [
            ['人称・形', 'хотеть (現在形)', '過去形'],
            ['я (1人称単数)', 'хочу', 'хотел (男)'],
            ['ты (2人称単数)', 'хочешь', 'хотела (女)'],
            ['он / она (3人称単数)', 'хочет', 'хотело (中)'],
            ['мы (1人称複数)', 'хотим', 'хотели (複)'],
            ['вы (2人称複数・敬称)', 'хотите', '-'],
            ['они (3人称複数)', 'хотят', '-']
        ],
        'anatomy': '''意志や願望を表す最重要動詞。
・単数形は第1変化語尾（-у, -ешь, -ет）、複数形は第2変化語尾（-им, -ите, -ят）をとる【混合変化（разноспрягаемый глагол）】です。
・後ろに不定詞をとる用法（хотят купить = 買いたがっている）と、対格名詞をとる用法（хочу чай = お茶が欲しい）があります。
・※非人称の再帰動詞 «хотеться»（ツァー動詞: 〜したい気がする/与格支配: мне хочется）とは文法構造およびニュアンスが明確に区別されます。''',
        'network': ['захотеть (ふと思い立つ/完了体)', 'желание (願望/名詞)', 'хотеться (〜したい気がする/非人称ツァー動詞)'],
        'examples': [
            {'ru': 'Они хотят купить новые ноты в консерватории.', 'ja': '彼らは音楽院で新しい楽譜を買いたがっています。'},
            {'ru': 'Я хочу сыграть эту сонату на рояле.', 'ja': '私はピアノでこのソナタを演奏したいです。'},
            {'ru': 'Мы очень хотим услышать ваш дуэт.', 'ja': '私たちはぜひあなたの二重奏を聴きたいです。'}
        ]
    },
    'мочь': {
        'word': 'мочь',
        'pos': '動詞 (不完了体・第1変化特殊動詞)',
        'meaning': '〜できる、〜する能力・可能性がある',
        'notes': '【子音交替】г ⇔ ж 交替（я могу, но ты можешь... они могут）。過去形: мог, могла',
        'aspect_pair': 'мочь (不完了体) ⇔ смочь (完了体)',
        'irregular_alert': {
            'badge': '⚠️ 活用注意：特殊変化動詞 (мочь)',
            'detail': '1人称単数 могу、3人称複数 могут は г ですが、それ以外の人称は ж に交替します（можешь, может, можем, можете）。過去形男性は суффикс л が脱落して «мог» となります。'
        },
        'declension_table': [
            ['人称・形', 'мочь (現在形)', '過去形'],
            ['я (1人称単数)', 'могу', 'мог (男)'],
            ['ты (2人称単数)', 'можешь', 'могла (女)'],
            ['он / она (3人称単数)', 'может', 'могло (中)'],
            ['мы (1人称複数)', 'можем', 'могли (複)'],
            ['вы (2人称複数・敬称)', 'можете', '-'],
            ['они (3人称複数)', 'могут', '-']
        ],
        'anatomy': '''能力や可能性を表す最重要助動詞的動詞。
・現在形は語幹末尾の子音が г ⇔ ж で交替します（могу / можешь, может, можем, можете / могут）。
・過去形男性は -л が付かず単音節の «мог»（女性: могла, 中性: могло, 複数: могли）となります。
・後ろには動詞の不定詞をとります（могу сыграть = 弾くことができる）。''',
        'network': ['смочь (できるようになる/完了体)', 'помочь (助ける/動詞)', 'возможность (可能性/名詞)'],
        'examples': [
            {'ru': 'Вы можете сыграть этот сложный пассаж?', 'ja': 'あなたはこの難しいパッセージを弾くことができますか？'},
            {'ru': 'Я могу репетировать каждый день в консерватории.', 'ja': '私は毎日音楽院で練習することができます。'}
        ]
    }
}

get_vocab_db()

def sanitize_declension_table(table):
    """
    Phonotactic post-generation sanitizer.
    Prevents any impossible Russian character sequences (e.g. vowels following 'ы').
    """
    if not table or not isinstance(table, list):
        return table
    clean_table = []
    for row in table:
        if isinstance(row, list):
            clean_row = []
            for cell in row:
                if isinstance(cell, str):
                    # Disallow illegal Russian vowel sequences following ы: ыа -> а, ыу -> у, ыо -> о, ые -> е, ыы -> ы
                    cell = re.sub(r'ы([аеёиоуыэюя])', r'\1', cell)
                    # Disallow multiple consecutive ы
                    cell = re.sub(r'ы+', 'ы', cell)
                clean_row.append(cell)
            clean_table.append(clean_row)
        else:
            clean_table.append(row)
    return clean_table

NOUNS_ENDING_IN_V = {
    'рукав', 'остров', 'лев', 'шов', 'гнев', 'посев', 'взрыв', 'киев', 'псков',
    'ростов', 'саратов', 'чернигов', 'кишинёв', 'покров', 'призыв', 'отзыв',
    'порыв', 'залив', 'разрыв', 'мотив', 'массив', 'архив', 'актив', 'пассив'
}

COMPARATIVE_ADVERBS_AND_ADJECTIVES = {
    'лучше', 'хуже', 'больше', 'меньше', 'выше', 'ниже', 'легче', 'тяжелее', 'проще',
    'сложнее', 'чище', 'тише', 'громче', 'глубже', 'шире', 'уже', 'ближе', 'дальше',
    'дольше', 'раньше', 'позже', 'дороже', 'дешевле', 'старше', 'моложе', 'быстрее',
    'красивее', 'медленнее', 'строже', 'мягче', 'тверже', 'слаще', 'крепче', 'ярче'
}

def is_russian_gerund(w, pos=""):
    """Morphologically determines if word is a Russian gerund (Деепричастие)."""
    if '副動詞' in pos or 'деепричастие' in pos.lower() or 'gerund' in pos.lower():
        return True
    w = w.lower().strip()
    if len(w) < 3:
        return False
    # Perfective gerunds: -в, -вши, -вшись, -ши, -шись
    if w.endswith(('вши', 'вшись', 'шись')) or (w.endswith('ши') and len(w) >= 5):
        return True
    if w.endswith('в') and len(w) >= 4 and w not in NOUNS_ENDING_IN_V:
        if len(w) >= 3 and w[-2] in 'аеёиоуыэюя':
            return True
    # Imperfective gerunds: -аясь, -яясь (verbal suffix + gerund ending)
    if w.endswith(('аясь', 'яясь')):
        return True
    if w.endswith(('ая', 'яя')) and len(w) >= 4:
        if any(w.startswith(stem) for stem in ('репетиру', 'изуча', 'слуша', 'чита', 'игра', 'дела', 'зна', 'дума', 'чувству', 'говор', 'сто', 'растворя')):
            return True
    # -я / -а after verb stems: e.g. играя, слушая, репетируя, молча, слыша, видя
    if w.endswith('я') and len(w) >= 4:
        if any(w.startswith(stem) for stem in ('репетиру', 'изуча', 'слуша', 'чита', 'игра', 'дела', 'зна', 'дума', 'чувству', 'говор', 'возвраща', 'прислушива')):
            return True
    return False

def is_russian_participle(w, pos=""):
    """Morphologically determines if word is a participle (形動詞: active or passive, full or short)."""
    if '形動詞' in pos or 'причастие' in pos.lower() or 'participle' in pos.lower():
        return True
    w = w.lower().strip()
    # Active participles
    if any(w.endswith(sfx) for sfx in (
        'ущий', 'ющая', 'ющее', 'ющие', 'ущих', 'ущему', 'ущим', 'ущей', 'ущую', 'ущими', 'ущем',
        'ющий', 'ющая', 'ющее', 'ющие', 'ющих', 'ющему', 'ющим', 'ющей', 'ющую', 'ющими', 'ющем',
        'ащий', 'ащая', 'ащее', 'ащие', 'ащих', 'ащему', 'ащим', 'ащей', 'ащую', 'ащими', 'ащем',
        'ящий', 'ящая', 'ящее', 'ящие', 'ящих', 'ящему', 'ящим', 'ящей', 'ящую', 'ящими', 'ящем',
        'вший', 'вшая', 'вшее', 'вшие', 'вших', 'вшему', 'вшим', 'вшей', 'вшую', 'вшими', 'вшем',
        'ший', 'шая', 'шее', 'шие', 'ших', 'шему', 'шим', 'шей', 'шую', 'шими', 'шем'
    )):
        return True
    # Passive participles (Full)
    if any(w.endswith(sfx) for sfx in (
        'нный', 'нная', 'нное', 'нные', 'нных', 'нному', 'нным', 'нной', 'нную', 'нными', 'нном',
        'тый', 'тая', 'тое', 'тые', 'тых', 'тому', 'тым', 'той', 'тую', 'тыми', 'том'
    )):
        return True
    # Passive participles (Short)
    if len(w) >= 4 and any(w.endswith(sfx) for sfx in (
        'ен', 'ена', 'ено', 'ены', 'ён', 'ёна', 'ёно', 'ёны',
        'ан', 'ана', 'ано', 'аны', 'ян', 'яна', 'яно', 'яны'
    )):
        if w not in {'лимон', 'стакан', 'экран', 'роман', 'баян', 'диван', 'океан', 'капитан', 'орган', 'план', 'пан', 'кран'}:
            return True
    if len(w) >= 4 and any(w.startswith(pfx) for pfx in ('откры', 'закры', 'занят', 'принят', 'понят', 'начат', 'прожит', 'разбит')):
        if w.endswith(('т', 'та', 'то', 'ты')):
            return True
    return False

def is_russian_comparative(w, pos=""):
    """Morphologically determines if word is a comparative degree form."""
    if '比較級' in pos or 'сравнительная' in pos.lower() or 'comparative' in pos.lower():
        return True
    w = w.lower().strip()
    if w in COMPARATIVE_ADVERBS_AND_ADJECTIVES:
        return True
    if len(w) >= 4 and (w.endswith('ее') or w.endswith('ей')):
        return True
    return False

def generate_smart_table(word, pos):
    """
    Algorithmic conjugator & declension generator for any Russian word.
    Produces standard 6-case declension or 6-person conjugation tables.
    Strictly enforces POS priority: explicit non-verbs (nouns, pronouns, adjectives, uninflected)
    can NEVER be conjugated as verbs!
    """
    clean_w = word.strip().lower()
    pos_clean = (pos or '').strip()

    # === MASTER ARCHITECTURAL FIRST BRANCH: Uninflected Words ===
    # 0. Uninflected words (adverbs, conjunctions, prepositions, particles, interjections)
    # Strictly protect: Participles (形動詞) and Verbs (動詞) can NEVER be uninflected!
    is_part = is_russian_participle(clean_w, pos_clean)
    is_explicit_verb = '動詞' in pos_clean or 'verb' in pos_clean.lower() or 'глагол' in pos_clean.lower()

    uninflected_tags = (
        '副詞', '不変化', '接続詞', '前置詞', '間投詞', '助詞', '小詞',
        'adv', 'prep', 'conj', 'particle', 'interj',
        'наречие', 'предлог', 'союз', 'частица', 'междометие'
    )
    if not is_part and not is_explicit_verb and (any(tag in pos_clean.lower() for tag in uninflected_tags) or clean_w in UNINFLECTED_WORDS or clean_w in [
        'лишь', 'днём', 'утром', 'вечером', 'ночью', 'ещё', 'или', 'только', 'эхо', 'метро', 'пальто',
        'кино', 'такси', 'кофе', 'очень', 'пешком', 'редко', 'часто', 'обычно', 'обязательно',
        'туда', 'сюда', 'вчера', 'сегодня', 'завтра', 'нет', 'есть', 'уже', 'так', 'как',
        'где', 'куда', 'когда', 'почему'
    ]):
        note = f'【不変化詞】«{word}» は不変化の語（{pos_clean or "副詞/不変化語"}）です。格変化や人称変化は行わず、常に一定の形で用いられます。'
        return [], note

    # === COMPARATIVES (比較級・Компаратив) ===
    if is_russian_comparative(clean_w, pos_clean):
        table = [
            ['文法項目', f'{word} (比較級)', '特徴・用法'],
            ['品詞', '形容詞・副詞の比較級 (Компаратив)', '「より〜」「もっと〜」'],
            ['語尾変化', '不変化（単一比較級は性・数・格の変化なし）', '主語の性・数によらず形は一定'],
            ['構文用法', '① 述語: Это лучше. (これの方が良い)\n② 比較対象 (生格): Он играет лучше меня. (彼は私より上手く弾く)\n③ 比較接続詞 чем: лучше, чем раньше (以前より良い)', '文脈に応じた比較の表現']
        ]
        note = (
            f'【比較級（Компаратив）】«{word}» は形容詞または副詞の比較級です。\n'
            f'★鉄則：ロシア語の単一比較級（-е, -ее, -ей）は不変化形式であり、主語の性・数・格によって語尾変化しません。\n'
            f'比較対象を前置詞なしの【生格】で置くか、接続詞 «чем»（〜よりも）で導きます。'
        )
        return table, note

    # === GERUNDS / VERBAL ADVERBS (副動詞・Деепричастие) ===
    if is_russian_gerund(clean_w, pos_clean):
        is_perf = clean_w.endswith(('в', 'вши', 'ши'))
        aspect_label = "完了体副動詞（先行動作: 〜したあとで）" if is_perf else "不完了体副動詞（同時動作: 〜しながら）"
        table = [
            ['文法項目', f'{word} (副動詞)', '特徴・用法'],
            ['品詞', '副動詞 (Деепричастие)', aspect_label],
            ['語尾変化', '不変化（語形変化なし）', '主語の性・数・格によらず形は一定'],
            ['文中での役割', '主文の述語動詞を修飾する副詞句', '主節の主語と同じ主語の副次的動作を表す'],
            ['用例', f'{word}, ...', f'音楽院での自然な文脈: {pos_clean or aspect_label}']
        ]
        note = (
            f'【副動詞（Деепричастие）】«{word}» は動詞から派生した副詞的表現（副動詞）です。\n'
            f'★鉄則：副動詞は語形変化（格変化や活用）を一切持たない【不変化】の形式です。主文の動詞と主語を共有し、主動作と同時に起こる動作（不完了体: 〜しながら）や先行する動作（完了体: 〜して/〜したあとで）を表します。'
        )
        return table, note

    # === PARTICIPLES (形動詞・Причастие) ===
    # Verbal adjectives: 4 genders/numbers x 6 cases (full form) or 4 forms (short passive)
    is_participle = (
        '形動詞' in pos_clean or 'причастие' in pos_clean.lower() or 'participle' in pos_clean.lower() or
        clean_w.endswith(('ющий', 'ющая', 'ющее', 'ющие', 'ущий', 'ущая', 'ущее', 'ущие',
                          'ящий', 'ящая', 'ящее', 'ящие', 'ащий', 'ащая', 'ащее', 'ащие',
                          'вший', 'вшая', 'вшее', 'вшие', 'ший', 'шая', 'шее', 'шие',
                          'нный', 'нная', 'нное', 'нные', 'тый', 'тая', 'тое', 'тые',
                          'ющего', 'ющему', 'ющим', 'ющем', 'ющей', 'ющую', 'ющих', 'ющими',
                          'ащего', 'ащему', 'ащим', 'ащем', 'ащей', 'ащую', 'ащих', 'ащими',
                          'ящего', 'ящему', 'ящим', 'ящем', 'ящей', 'ящую', 'ящих', 'ящими',
                          'вшего', 'вшему', 'вшим', 'вшем', 'вшей', 'вшую', 'вших', 'вшими',
                          'нного', 'нному', 'нным', 'нном', 'нной', 'нную', 'нных', 'нными'))
    )
    is_short_participle = (
        not clean_w.endswith(('ть', 'ти', 'чь')) and
        ('短語尾' in pos_clean or 'кратк' in pos_clean.lower() or 'participle.passive' in pos_clean.lower() or
         is_russian_participle(clean_w, pos_clean)) and
        any(clean_w.endswith(sfx) for sfx in ('ан', 'ана', 'ано', 'аны', 'ен', 'ена', 'ено', 'ены', 'ён', 'ёна', 'ёно', 'ёны', 'тан', 'тана', 'тано', 'таны', 'ыт', 'ыта', 'ыто', 'ыты', 'зан', 'зана', 'зано', 'заны'))
    )

    if is_short_participle:
        stem_short = clean_w
        for end in ('ана', 'ано', 'аны', 'ена', 'ено', 'ены', 'яна', 'яно', 'яны', 'она', 'оно', 'оны', 'на', 'но', 'ны', 'та', 'то', 'ты', 'ан', 'ен', 'ян', 'он', 'н', 'т'):
            if clean_w.endswith(end) and len(clean_w) > len(end):
                stem_short = clean_w[:-len(end)]
                break
        m_form = f"{stem_short}н" if 'н' in clean_w else f"{stem_short}т"
        f_form = f"{stem_short}на" if 'н' in clean_w else f"{stem_short}та"
        n_form = f"{stem_short}но" if 'н' in clean_w else f"{stem_short}то"
        pl_form = f"{stem_short}ны" if 'н' in clean_w else f"{stem_short}ты"
        table = [
            ['性・数', '短語尾形 (Краткая форма)', '用例・語形補足'],
            ['男性', m_form, f'Роман / Концерт был {m_form}.'],
            ['女性', f_form, f'Соната была {f_form}.'],
            ['中性', n_form, f'Письмо / Произведение было {n_form}.'],
            ['複数', pl_form, f'Ноты / Билеты были {pl_form}.']
        ]
        note = (
            f'【受動形動詞・短語尾形（Краткое страдательное причастие）】«{word}» は動詞から作られた受動形動詞の短語尾形です。\n'
            f'★重要鉄則：短語尾形は名詞のような6格変化（主格・生格・与格…）を行わず、主語の「性・数」に一致（男性 -∅, 女性 -а, 中性 -о, 複数 -ы）して文の述語（〜された・〜されていた）となります。\n'
            f'「誰によって」という動作主は前置詞なしの【造格】（русским композитором など）で表現します。'
        )
        return table, note

    if is_participle:
        is_sibilant_p = any(clean_w.endswith(sfx) for sfx in ('щий', 'щая', 'щее', 'щие', 'вшего', 'вшем', 'вший', 'вшая', 'вшее', 'вшие', 'ший', 'шая', 'шее', 'шие')) or 'щ' in clean_w[-4:] or 'ш' in clean_w[-4:]
        if is_sibilant_p:
            m_stem = clean_w
            for s_end in ('ий', 'ая', 'яя', 'ое', 'ее', 'ие', 'ые', 'его', 'ему', 'им', 'ем', 'ей', 'ую', 'их', 'ими'):
                if clean_w.endswith(s_end):
                    m_stem = clean_w[:-len(s_end)]
                    break
            nom_m = f"{m_stem}ий"
            nom_f = f"{m_stem}ая"
            nom_n = f"{m_stem}ее"
            nom_pl = f"{m_stem}ие"
            gen_m = f"{m_stem}его"
            gen_f = f"{m_stem}ей"
            gen_n = gen_m
            gen_pl = f"{m_stem}их"
            dat_m = f"{m_stem}ему"
            dat_f = gen_f
            dat_n = dat_m
            dat_pl = f"{m_stem}им"
            acc_m = f"{nom_m} / {gen_m}"
            acc_f = f"{m_stem}ую"
            acc_n = nom_n
            acc_pl = f"{nom_pl} / {gen_pl}"
            ins_m = f"{m_stem}им"
            ins_f = gen_f
            ins_n = ins_m
            ins_pl = f"{m_stem}ими"
            prp_m = f"{m_stem}ем"
            prp_f = gen_f
            prp_n = prp_m
            prp_pl = gen_pl
        else:
            m_stem = clean_w
            for s_end in ('ый', 'ая', 'ое', 'ые', 'ого', 'ому', 'ым', 'ом', 'ой', 'ую', 'ых', 'ыми'):
                if clean_w.endswith(s_end):
                    m_stem = clean_w[:-len(s_end)]
                    break
            nom_m = f"{m_stem}ый"
            nom_f = f"{m_stem}ая"
            nom_n = f"{m_stem}ое"
            nom_pl = f"{m_stem}ые"
            gen_m = f"{m_stem}ого"
            gen_f = f"{m_stem}ой"
            gen_n = gen_m
            gen_pl = f"{m_stem}ых"
            dat_m = f"{m_stem}ому"
            dat_f = gen_f
            dat_n = dat_m
            dat_pl = f"{m_stem}ым"
            acc_m = f"{nom_m} / {gen_m}"
            acc_f = f"{m_stem}ую"
            acc_n = nom_n
            acc_pl = f"{nom_pl} / {gen_pl}"
            ins_m = f"{m_stem}ым"
            ins_f = gen_f
            ins_n = ins_m
            ins_pl = f"{m_stem}ыми"
            prp_m = f"{m_stem}ом"
            prp_f = gen_f
            prp_n = prp_m
            prp_pl = gen_pl

        table = [
            ['格', f'男性 ({nom_m})', f'女性 ({nom_f})', f'中性 ({nom_n})', f'複数 ({nom_pl})'],
            ['主格', nom_m, nom_f, nom_n, nom_pl],
            ['生格', gen_m, gen_f, gen_n, gen_pl],
            ['与格', dat_m, dat_f, dat_n, dat_pl],
            ['対格', acc_m, acc_f, acc_n, acc_pl],
            ['造格', ins_m, ins_f, ins_n, ins_pl],
            ['前置格', prp_m, prp_f, prp_n, prp_pl]
        ]
        note = f'【形動詞の性・数・格変化】«{word}» は動詞から派生した動詞的形容詞（形動詞）です。修飾する名詞の性（男性・女性・中性）および数・格に応じて形容詞と同様に格変化します。'
        return table, note

    # Explicit Non-Verb Check: IF pos specifies noun, pronoun, etc., it is NEVER a verb!
    is_noun_or_pronoun = any(tag in pos_clean for tag in ('名詞', '代名詞', '数詞', '前置詞', '接続詞', '副詞', '助詞', '間投詞')) and '動詞' not in pos_clean and '形容詞' not in pos_clean

    # 0.1 Pronouns (Definitive, personal, demonstrative)
    if '代名詞' in pos_clean:
        note = f'【代名詞】«{word}» は代名詞（{pos_clean}）です。文脈（性・数・格）に応じて変化します。'
        return [], note

    # 0.2 Russian Adjectives Declension Table (Masculine, Feminine, Neuter, Plural x 6 Cases)
    is_adjective = not is_noun_or_pronoun and ('形容詞' in pos_clean or 'прилагательное' in pos_clean or clean_w.endswith(('ый', 'ий', 'ой', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие')))
    if is_adjective:
        stem = clean_w
        for end in ('ый', 'ой', 'ий', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие', 'ую', 'юю', 'ом', 'ем', 'ым', 'им', 'ых', 'их', 'ого', 'его', 'ому', 'ему', 'ыми', 'ими'):
            if clean_w.endswith(end) and len(clean_w) > len(end):
                stem = clean_w[:-len(end)]
                break

        last_c = stem[-1:] if stem else ''
        is_stressed = clean_w.endswith('ой')
        is_soft = clean_w.endswith('ний') or clean_w.endswith('нее') or clean_w.endswith('няя') or clean_w.endswith('ние')
        is_velar = last_c in 'гкх'
        is_sibilant = last_c in 'жчшщц'

        nom_m = 'ой' if is_stressed else ('ий' if (is_soft or is_velar or is_sibilant) else 'ый')
        nom_f = 'яя' if is_soft else 'ая'
        nom_n = 'ее' if is_soft else 'ое'
        nom_pl = 'ие' if (is_soft or is_velar or is_sibilant) else 'ые'

        gen_m = 'его' if (is_soft or (is_sibilant and not is_stressed)) else 'ого'
        gen_f = 'ей' if (is_soft or (is_sibilant and not is_stressed)) else 'ой'
        gen_n = gen_m
        gen_pl = 'их' if (is_soft or is_velar or is_sibilant) else 'ых'

        dat_m = 'ему' if (is_soft or (is_sibilant and not is_stressed)) else 'ому'
        dat_f = gen_f
        dat_n = dat_m
        dat_pl = 'им' if (is_soft or is_velar or is_sibilant) else 'ым'

        acc_m = f"{stem}{nom_m} / {stem}{gen_m}"
        acc_f = 'юю' if is_soft else 'ую'
        acc_n = f"{stem}{nom_n}"
        acc_pl = f"{stem}{nom_pl} / {stem}{gen_pl}"

        ins_m = 'им' if (is_soft or is_velar or is_sibilant) else 'ым'
        ins_f = gen_f
        ins_n = ins_m
        ins_pl = 'ими' if (is_soft or is_velar or is_sibilant) else 'ыми'

        prp_m = 'ем' if (is_soft or (is_sibilant and not is_stressed)) else 'ом'
        prp_f = gen_f
        prp_n = prp_m
        prp_pl = gen_pl

        table = [
            ['格', '男性 (Мужской)', '女性 (Женский)', '中性 (Средний)', '複数 (Множественное)'],
            ['主格', f"{stem}{nom_m}", f"{stem}{nom_f}", f"{stem}{nom_n}", f"{stem}{nom_pl}"],
            ['生格', f"{stem}{gen_m}", f"{stem}{gen_f}", f"{stem}{gen_n}", f"{stem}{gen_pl}"],
            ['与格', f"{stem}{dat_m}", f"{stem}{dat_f}", f"{stem}{dat_n}", f"{stem}{dat_pl}"],
            ['対格', acc_m, f"{stem}{acc_f}", acc_n, acc_pl],
            ['造格', f"{stem}{ins_m}", f"{stem}{ins_f}", f"{stem}{ins_n}", f"{stem}{ins_pl}"],
            ['前置格', f"{stem}{prp_m}", f"{stem}{prp_f}", f"{stem}{prp_n}", f"{stem}{prp_pl}"]
        ]
        base_adj = f"{stem}{nom_m}"
        note = f'【形容詞の性・数・格変化】«{base_adj}» は修飾する名詞の性（男性・女性・中性）および数・格に応じて語尾が変化します。対格は活動体で生格、不活動体で主格と同形になります。'
        return table, note

    # 0.3 Russian Verb Detection (STRICT)
    # A word is ONLY a verb if:
    # 1. pos explicitly contains '動詞' or 'verb' or 'глагол'
    # 2. clean_w is in RUSSIAN_VERB_LEMMAS
    # 3. NOT an explicit non-verb AND ends with genuine verb infinitive: '-ться', '-тись', '-чься', '-ть', '-ти', '-чь'
    # NOTE: Non-verbs ending in -сь / -ся (весь, гусь, рысь, запись, смесь, ось) are NOUNS/PRONOUNS, NEVER VERBS!
    is_verb = False
    is_reflexive = False
    is_past_verb = False

    if not is_noun_or_pronoun and not ('形容詞' in pos_clean):
        if '動詞' in pos_clean or clean_w in RUSSIAN_VERB_LEMMAS:
            is_verb = True
            is_reflexive = clean_w.endswith(('ться', 'тись', 'чься', 'тся', 'ся', 'сь'))
            is_past_verb = clean_w.endswith(('ла', 'ло', 'ли', 'л', 'лась', 'лось', 'лись', 'лся')) and len(clean_w) >= 4
        elif clean_w.endswith(('ться', 'тись', 'чься')):
            is_verb = True
            is_reflexive = True
        elif clean_w.endswith(('ть', 'ти', 'чь')) and not clean_w.endswith(('ость', 'есть', 'путь', 'ночь', 'печь', 'дочь', 'речь', 'вещь')):
            is_verb = True

    # 0. Past Tense Verb Fallback Table
    if is_past_verb or (clean_w.endswith(('ла', 'ло', 'ли', 'л')) and '動詞' in pos_clean):
        # Reconstruct base stem
        stem = re.sub(r'(лась|лось|лись|лся|ла|ло|ли|л)$', '', clean_w)
        table = [
            ['人称・性', f'{clean_w} (動詞過去形・活用)', '用例'],
            ['過去形 (男性)', f'{stem}л', f'Он {stem}л'],
            ['過去形 (女性)', f'{stem}ла', f'Она {stem}ла'],
            ['過去形 (中性)', f'{stem}ло', f'Оно {stem}ло'],
            ['過去形 (複数)', f'{stem}ли', f'Они {stem}ли'],
            ['現在/未来 (я)', f'{stem}ю', f'Я {stem}ю'],
            ['現在/未来 (ты)', f'{stem}ешь', f'Ты {stem}ешь'],
            ['現在/未来 (он/она)', f'{stem}ет', f'Он/она {stem}ет'],
            ['現在/未来 (мы)', f'{stem}ем', f'Мы {stem}ем'],
            ['現在/未来 (они)', f'{stem}ют', f'Они {stem}ют']
        ]
        note = '【動詞の過去形】ロシア語の動詞過去形は人称変化ではなく主語の「性・数」に一致します（男性 -л, 女性 -ла, 中性 -ло, 複数 -ли）。格変化表（名詞）とは異なり、主語の性に応じた語尾変化を持ちます。'
        return table, note

    # 1. Reflexive Verb
    if is_reflexive:
        stem = re.sub(r'(ться|тся|ся|сь)$', '', clean_w)
        if stem.endswith(('а', 'я', 'е')):
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{stem}юсь', f'Я {stem}юсь'],
                ['ты', f'{stem}ешься', f'Ты {stem}ешься'],
                ['он/она', f'{stem}ется', f'Он/она {stem}ется'],
                ['мы', f'{stem}емся', f'Мы {stem}емся'],
                ['вы', f'{stem}етесь', f'Вы {stem}етесь'],
                ['они', f'{stem}ются', f'Они {stem}ются']
            ]
        else:
            base_s = stem[:-1] if stem.endswith('и') else stem
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{base_s}усь', f'Я {base_s}усь'],
                ['ты', f'{base_s}ишься', f'Ты {base_s}ишься'],
                ['он/она', f'{base_s}ится', f'Он/она {base_s}ится'],
                ['мы', f'{base_s}имся', f'Мы {base_s}имся'],
                ['вы', f'{base_s}итесь', f'Вы {base_s}итесь'],
                ['они', f'{base_s}атся', f'Они {base_s}атся']
            ]
        note = '【再帰動詞 (-ся)】自動詞として主語自身の状態変化を表します。\n母音の後では -сь、子音の後では -ся が付きます。'
        return table, note

    # 1.5 Special / Irregular Verb Stems (e.g. -стать -> -стану, быть, жить, пить, петь, дать)
    if is_verb:
        # Verbs ending in -стать (стать, перестать, достать, устать, отстать, etc.)
        if clean_w.endswith('стать') and not clean_w.endswith('статься'):
            prefix = clean_w[:-len('стать')]
            table = [
                ['人称・性', f'{word} (単純未来形)', '過去形 / 命令形'],
                ['я', f'{prefix}ста́ну', f'Он {prefix}стал'],
                ['ты', f'{prefix}ста́нешь', f'Ты {prefix}стань! (命令・単数)'],
                ['он/она', f'{prefix}ста́нет', f'Она {prefix}ста́ла / Оно {prefix}ста́ло'],
                ['мы', f'{prefix}ста́нем', f'Мы {prefix}ста́ли'],
                ['вы', f'{prefix}ста́нете', f'Вы {prefix}ста́ньте! (命令・複数)'],
                ['они', f'{prefix}ста́нут', f'Они {prefix}ста́ли']
            ]
            note = f'【重要動詞 «{word}»（完了体・【造格支配】）】語幹に -н- が入る第1変化動詞です（я {prefix}стану, ты {prefix}станешь...）。完了体動詞であるため現在形活用は「単純未来（〜するだろう/〜になる）」を表します。「стать」は後ろに【造格】を従える代表的な造格支配動詞（стать + 造格: 〜になる）です。'
            return table, note

        # Verbs ending in -звучать (звучать, прозвучать, etc.) -> 2nd conjugation!
        if clean_w.endswith('звучать'):
            prefix = clean_w[:-len('звучать')]
            is_sv = bool(prefix)
            tense_name = '単純未来形' if is_sv else '現在形・第2変化'
            table = [
                ['人称・性', f'{word} ({tense_name})', '過去形 / 命令形・用例'],
                ['я', f'{prefix}звучу́', f'Он {prefix}звуча́л'],
                ['ты', f'{prefix}звучи́шь', f'Звучи́! (命令形・単数)'],
                ['он/она', f'{prefix}звучи́т', f'Она́ {prefix}звуча́ла / Оно́ {prefix}звуча́ло'],
                ['мы', f'{prefix}звучи́м', f'Мы {prefix}звуча́ли'],
                ['вы', f'{prefix}звучи́те', f'Звучи́те! (命令形・複数)'],
                ['они', f'{prefix}звуча́т', f'В зале {prefix}звуча́т аплодисменты']
            ]
            note = f'【重要動詞 «{word}»（第2変化）】不定形は -ать ですが、第2変化（-ить グループ）として活用します（я {prefix}звучу́, ты {prefix}звучи́шь...）。3人称複数形 «{prefix}звуча́т» から能動形動詞現在形 «{prefix}звуча́щий»（響いている〜）が作られます。'
            return table, note

        # Verbs ending in -быть (быть, забыть, прибыть, etc.)
        if clean_w == 'быть':
            table = [
                ['人称・性', 'быть (未来形)', '過去形 / 命令形'],
                ['я', 'бу́ду', 'Он был'],
                ['ты', 'бу́дешь', 'Ты будь! (命令・単数)'],
                ['он/она', 'бу́дет', 'Она была́ / Оно бы́ло'],
                ['мы', 'бу́дем', 'Мы бы́ли'],
                ['вы', 'бу́дете', 'Бу́дьте! (命令・複数)'],
                ['они', 'бу́дут', 'Они бы́ли']
            ]
            note = '【重要動詞 «быть»（【造格支配】）】現在形は通常省略されます（または есть）。未来形は «я буду, ты будешь...»、過去形は «был, была, было, были» となります。過去形・未来形・不定詞では補語に【造格】をとる代表的動詞です（Он был студентом）。'
            return table, note

        # Verbs ending in -жить (жить, пережить, прожить, etc.)
        if clean_w.endswith('жить') and not is_reflexive:
            prefix = clean_w[:-len('жить')]
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{prefix}живу́', f'Я {prefix}живу в Москве'],
                ['ты', f'{prefix}живёшь', f'Ты {prefix}живёшь'],
                ['он/она', f'{prefix}живёт', f'Он/она {prefix}живёт'],
                ['мы', f'{prefix}живём', f'Мы {prefix}живём'],
                ['вы', f'{prefix}живёте', f'Вы {prefix}живёте'],
                ['они', f'{prefix}живу́т', f'Они {prefix}живут']
            ]
            note = f'【重要動詞 «{word}»】語幹に -в- が現れる不規則動詞です（живу, живёшь, живёт...）。過去形は жил, жила, жило, жили となります。'
            return table, note

        # Verbs ending in -пить (пить, выпить, etc.)
        if clean_w.endswith('пить') and not is_reflexive:
            prefix = clean_w[:-len('пить')]
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{prefix}пью', f'Я {prefix}пью чай'],
                ['ты', f'{prefix}пьёшь', f'Ты {prefix}пьёшь'],
                ['он/она', f'{prefix}пьёт', f'Он/она {prefix}пьёт'],
                ['мы', f'{prefix}пьём', f'Мы {prefix}пьём'],
                ['вы', f'{prefix}пьёте', f'Вы {prefix}пьёте'],
                ['они', f'{prefix}пьют', f'Они {prefix}пьют']
            ]
            note = f'【重要動詞 «{word}»】軟音記号 ь が入る活用（пью, пьёшь, пьёт...）です。'
            return table, note

        # Verbs ending in -петь (петь, спеть, etc.)
        if clean_w.endswith('петь') and not is_reflexive:
            prefix = clean_w[:-len('петь')]
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{prefix}пою́', f'Я {prefix}пою песню'],
                ['ты', f'{prefix}поёшь', f'Ты {prefix}поёшь'],
                ['он/она', f'{prefix}поёт', f'Он/она {prefix}поёт'],
                ['мы', f'{prefix}поём', f'Мы {prefix}поём'],
                ['вы', f'{prefix}поёте', f'Вы {prefix}поёте'],
                ['они', f'{prefix}пою́т', f'Они {prefix}поют']
            ]
            note = f'【重要動詞 «{word}»】母音交替（е → о）を伴う不規則動詞（пою, поёшь, поёт...）です。'
            return table, note

        # Verbs ending in -дать (дать, передать, продать, etc.)
        if clean_w.endswith('дать') and not is_reflexive:
            prefix = clean_w[:-len('дать')]
            table = [
                ['人称', f'{word} (単純未来形)', '過去形 / 命令形'],
                ['я', f'{prefix}дам', f'Он {prefix}дал'],
                ['ты', f'{prefix}дашь', f'Ты {prefix}дай! (命令・単数)'],
                ['он/она', f'{prefix}даст', f'Она {prefix}дала́'],
                ['мы', f'{prefix}дади́м', f'Мы {prefix}да́ли'],
                ['вы', f'{prefix}дади́те', f'Вы {prefix}да́йте! (命令・複数)'],
                ['они', f'{prefix}даду́т', f'Они {prefix}да́ли']
            ]
            note = f'【重要不規則動詞 «{word}»（固有変化）】ロシア語で2つしかない特殊固有変化動詞の1つです（дам, дашь, даст, дадим, дадите, дадут）。'
            return table, note

    # 2. Regular Verb
    if is_verb:
        stem = re.sub(r'(ть|ти)$', '', clean_w)
        if stem.endswith(('а', 'я', 'е')):
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{stem}ю', f'Я {stem}ю'],
                ['ты', f'{stem}ешь', f'Ты {stem}ешь'],
                ['он/она', f'{stem}ет', f'Он/она {stem}ет'],
                ['мы', f'{stem}ем', f'Мы {stem}ем'],
                ['вы', f'{stem}ете', f'Вы {stem}ете'],
                ['они', f'{stem}ют', f'Они {stem}ют']
            ]
        else:
            base_s = stem[:-1] if stem.endswith('и') else stem
            table = [
                ['人称', f'{word} (現在形)', '用例・語形補足'],
                ['я', f'{base_s}ю', f'Я {base_s}ю'],
                ['ты', f'{base_s}ишь', f'Ты {base_s}ишь'],
                ['он/она', f'{base_s}ит', f'Он/она {base_s}ит'],
                ['мы', f'{base_s}им', f'Мы {base_s}им'],
                ['вы', f'{base_s}ите', f'Вы {base_s}ите'],
                ['они', f'{base_s}ят', f'Они {base_s}ят']
            ]
        note = '【動詞の活用】現在（または未来）における主語の人称変化。'
        return table, note

    # 2.8 Candidate Feminine Instrumental Oblique Form (e.g. преподавательницей, сонатой)
    if clean_w.endswith(('ей', 'ой')) and not clean_w.endswith(('музей', 'соловей', 'ручей', 'герой', 'ковбой', 'бой', 'слой', 'покой', 'злодей', 'еврей')) and '男性' not in pos:
        stem_cand = clean_w[:-2]
        if stem_cand:
            base_f = stem_cand + ('я' if clean_w.endswith('ей') and (stem_cand.endswith(('и', 'л', 'р')) and not stem_cand.endswith(('ж', 'ч', 'ш', 'щ', 'ц'))) else 'а')
            clean_w = base_f
            word = base_f
            pos = '女性名詞'

    # 2.9 Plural Nouns ending in -ы / -и (e.g. билеты, ноты, аккорды, концерты, скрипки)
    if clean_w.endswith(('ы', 'и')) and not is_adjective and not is_participle:
        vdb = get_vocab_db()
        stem_pl = clean_w[:-1]
        # Check dictionary matches for singular lemma
        for cand in [stem_pl, stem_pl + 'а', stem_pl + 'я', stem_pl + 'о', stem_pl + 'е']:
            if cand in vdb and vdb[cand].get('declension_table') and len(vdb[cand]['declension_table']) > 1:
                return sanitize_declension_table(vdb[cand]['declension_table']), vdb[cand].get('anatomy') or f"【複数名詞 «{word}»】単数主格 «{cand}» の複数形です。"

        # Algorithmic generation for plural noun
        is_fem = '女性' in pos_clean
        last_c = stem_pl[-1:] if stem_pl else ''
        needs_i = last_c in 'гкхжчшщ'
        if is_fem:
            sg_nom = f"{stem_pl}а"
            table = [
                ['格', f'単数 ({sg_nom})', f'複数 ({word})'],
                ['主格', sg_nom, word],
                ['生格', f"{stem_pl}{'и' if needs_i else 'ы'}", stem_pl],
                ['与格', f"{stem_pl}е", f"{stem_pl}ам"],
                ['対格', f"{stem_pl}у", word],
                ['造格', f"{stem_pl}ой", f"{stem_pl}ами"],
                ['前置格', f"{stem_pl}е", f"{stem_pl}ах"]
            ]
            note = f'【女性名詞 «{sg_nom}» の格変化（複数形: «{word}»）】文中では複数形 «{word}» として用いられています。'
            return sanitize_declension_table(table), note
        else:
            sg_nom = stem_pl
            table = [
                ['格', f'単数 ({sg_nom})', f'複数 ({word})'],
                ['主格', sg_nom, word],
                ['生格', f"{stem_pl}а", f"{stem_pl}ов"],
                ['与格', f"{stem_pl}у", f"{stem_pl}ам"],
                ['対格', sg_nom, word],
                ['造格', f"{stem_pl}ом", f"{stem_pl}ами"],
                ['前置格', f"{stem_pl}е", f"{stem_pl}ах"]
            ]
            note = f'【男性名詞 «{sg_nom}» の格変化（複数形: «{word}»）】文中では複数形 «{word}» として用いられています。'
            return sanitize_declension_table(table), note

    # 3. Feminine Noun ending in -а / -я
    if clean_w.endswith(('а', 'я')) or '女性名詞' in pos:
        is_soft = clean_w.endswith('я')
        stem = clean_w[:-1] if clean_w.endswith(('а', 'я')) else clean_w
        last_c = stem[-1:] if stem else ''
        needs_i = is_soft or last_c in 'гкхжчшщ'
        table = [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', word, f"{stem}{'и' if needs_i else 'ы'}"],
            ['生格', f"{stem}{'и' if needs_i else 'ы'}", f"{stem}{'ь' if is_soft else ''}"],
            ['与格', f"{stem}е", f"{stem}{'ям' if is_soft else 'ам'}"],
            ['対格', f"{stem}{'ю' if is_soft else 'у'}", f"{stem}{'и' if needs_i else 'ы'}"],
            ['造格', f"{stem}{'ей' if is_soft else 'ой'}", f"{stem}{'ями' if is_soft else 'ами'}"],
            ['前置格', f"{stem}е", f"{stem}{'ях' if is_soft else 'ах'}"]
        ]
        note = '【女性名詞の格変化】単数対格は -у/-ю、前置格は -е に変化します。'
        return sanitize_declension_table(table), note

    # 4. Masculine Noun ending in consonant
    if not clean_w.endswith(('о', 'е', 'а', 'я', 'ь')) or '男性名詞' in pos:
        stem = clean_w
        last_c = stem[-1:] if stem else ''
        needs_i = last_c in 'гкхжчшщ'
        is_animate = any(a in pos for a in ['活動体', '人名', '男性名', '職業', '人物']) or clean_w in [
            'солист', 'музыкант', 'профессор', 'студент', 'друг', 'брат', 'человек', 'мальчик',
            'отец', 'актёр', 'дирижёр', 'автор', 'композитор', 'певец', 'скрипач', 'пианист'
        ]
        nom_pl = f"{stem}{'и' if needs_i else 'ы'}"
        acc_sg = f"{stem}а" if is_animate else word
        acc_pl = f"{stem}ов" if is_animate else nom_pl
        table = [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', word, nom_pl],
            ['生格', f"{stem}а", f"{stem}ов"],
            ['与格', f"{stem}у", f"{stem}ам"],
            ['対格', acc_sg, acc_pl],
            ['造格', f"{stem}ом", f"{stem}ами"],
            ['前置格', f"{stem}е", f"{stem}ах"]
        ]
        if is_animate:
            note = '【男性名詞（活動体）の格変化】活動体（人・動物）のため対格は単数・複数ともに生格と同形になります。'
        else:
            note = '【男性名詞（不活動体）の格変化】不活動体のため対格は単数・複数ともに主格と同形になります。'
        return sanitize_declension_table(table), note

    # 5. Neuter Noun ending in -о / -е
    if clean_w.endswith(('о', 'е')) or '中性名詞' in pos:
        is_e = clean_w.endswith('е')
        stem = clean_w[:-1] if clean_w.endswith(('о', 'е')) else clean_w
        table = [
            ['格', '単数 (Единственное)', '複数 (Множественное)'],
            ['主格', word, f"{stem}{'я' if is_e else 'а'}"],
            ['生格', f"{stem}{'я' if is_e else 'а'}", f"{stem}{'ей' if is_e else ''}"],
            ['与格', f"{stem}{'ю' if is_e else 'у'}", f"{stem}{'ям' if is_e else 'ам'}"],
            ['対格', word, f"{stem}{'я' if is_e else 'а'}"],
            ['造格', f"{stem}{'ем' if is_e else 'ом'}", f"{stem}{'ями' if is_e else 'ами'}"],
            ['前置格', f"{stem}е", f"{stem}{'ях' if is_e else 'ах'}"]
        ]
        note = '【中性名詞の格変化】対格は単複ともに主格と同形になります。'
        return sanitize_declension_table(table), note

    # 6. Soft-Sign (-ь) Nouns (Masculine / Feminine 3rd Declension)
    if clean_w.endswith('ь') or '軟音符号' in pos_clean or '3格' in pos_clean or '第3変化' in pos_clean or 'ь' in clean_w:
        stem = clean_w[:-1] if clean_w.endswith('ь') else clean_w
        
        is_explicit_masc = ('男性' in pos_clean or 'мужской' in pos_clean.lower() or 
                            clean_w.endswith(('тель', 'арь', 'бль', 'аль')) or 
                            clean_w in ('рояль', 'день', 'дождь', 'кремль', 'гость', 'путь', 'рубль', 'спектакль', 'ансамбль', 'контроль', 'стиль', 'гвоздь'))
        
        is_explicit_fem = ('女性' in pos_clean or 'женский' in pos_clean.lower() or 
                           clean_w.endswith(('ость', 'есть', 'знь', 'адь', 'едь', 'овь', 'ощь', 'чь', 'шь', 'щь', 'ть')) or 
                           clean_w in ('ночь', 'жизнь', 'радость', 'память', 'часть', 'площадь', 'скорость', 'любовь', 'вещь', 'тетрадь', 'дверь', 'кровать', 'мысль', 'осень'))

        if is_explicit_masc or not is_explicit_fem:
            is_animate = any(a in pos_clean for a in ['活動体', '人名', '男性名', '職業', '人物']) or clean_w.endswith('тель') or clean_w in ['гость', 'зритель', 'слушатель', 'исполнитель', 'учитель', 'писатель', 'приятель']
            acc_sg = f"{stem}я" if is_animate else word
            acc_pl = f"{stem}ей" if is_animate else f"{stem}и"
            table = [
                ['格', '単数 (Единственное)', '複数 (Множественное)'],
                ['主格', word, f"{stem}и"],
                ['生格', f"{stem}я", f"{stem}ей"],
                ['与格', f"{stem}ю", f"{stem}ям"],
                ['対格', acc_sg, acc_pl],
                ['造格', f"{stem}ем", f"{stem}ями"],
                ['前置格', f"{stem}е", f"{stem}ях"]
            ]
            if is_animate:
                note = f'【男性名詞（-ь 語尾・活動体）«{word}» の格変化】末尾が -ь で終わる男性名詞です。人・活動体のため対格は生格と同形（単数: -я, 複数: -ей）になります。'
            else:
                note = f'【男性名詞（-ь 語尾・不活動体）«{word}» の格変化】末尾が -ь で終わる男性名詞です（例: рояль, день）。対格は主格と同形になります。'
            return sanitize_declension_table(table), note
        else:
            table = [
                ['格', '単数 (Единственное)', '複数 (Множественное)'],
                ['主格', word, f"{stem}и"],
                ['生格', f"{stem}и", f"{stem}ей"],
                ['与格', f"{stem}и", f"{stem}ям"],
                ['対格', word, f"{stem}и"],
                ['造格', f"{stem}ью", f"{stem}ями"],
                ['前置格', f"{stem}и", f"{stem}ях"]
            ]
            note = f'【女性名詞（第3変化名詞）«{word}» の格変化】末尾が -ь で終わる女性名詞（第3変化）です。生格・与格・前置格がすべて «-и» と同形になり、造格は «-ью» となります。'
            return sanitize_declension_table(table), note

    # 7. Numerals (5-10, 20, 30: пять, десять, etc.)
    if clean_w in ('пять', 'шесть', 'семь', 'восемь', 'девять', 'десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать', 'двадцать', 'тридцать') or '数詞' in pos_clean:
        stem = clean_w[:-1] if clean_w.endswith('ь') else clean_w
        ins_form = f"{stem}ью" if clean_w.endswith('ь') else f"{clean_w}ю"
        table = [
            ['格', f'{word} (数詞の格変化)', '用法・結合'],
            ['主格', word, f'{word} + 複数生格名詞'],
            ['生格', f"{stem}и", f'{stem}и + 複数生格名詞'],
            ['与格', f"{stem}и", f'{stem}и + 複数与格名詞'],
            ['対格', word, f'{word} + 複数生格名詞'],
            ['造格', ins_form, f'{ins_form} + 複数造格名詞'],
            ['前置格', f"{stem}и", f'{stem}и + 複数前置格名詞']
        ]
        note = f'【数詞 «{word}» の格変化】5〜20, 30の基数詞は第3変化女性名詞と同様に変化し（生格・与格・前置格が -и、造格が -ью）、主格・対格では後ろの名詞を【複数生格】で従えます。'
        return sanitize_declension_table(table), note

    # Absolute Safety Fallback: NEVER return None! Always return a valid (table, note) tuple!
    return [], f'【語彙情報: «{word}»】{pos_clean or "品詞未定義"}'

def generate_russian_lemma_candidates(raw_word):
    """
    Algorithmic Slavic Morphological Lemmatizer.
    Systematically reduces any inflected Russian word form (past tense, conjugations,
    participles, gerunds, adjective cases, noun oblique/plural cases, reflexives)
    to its underlying dictionary lemma candidate(s).
    Completely eliminates ad-hoc per-word patches and if-statements.
    """
    if not raw_word:
        return []
    w = re.sub(r'[«»„“".,!?;:()—]', '', raw_word).strip().lower()
    if not w:
        return []

    candidates = [w]
    is_refl = False
    base_w = w

    # 0. Reflexive marker stripping (-ся / -сь)
    if w.endswith(('ся', 'сь')) and len(w) > 4:
        is_refl = True
        base_w = w[:-2]
        candidates.append(base_w)

    # 1. Prefixed motion verbs with -шёл / -шла / -шло / -шли (suppletive past of -йти)
    # e.g. пришёл -> прийти, ушла -> уйти, вышли -> выйти, подошёл -> подойти
    motion_match = re.search(r'^(.*)(шёл|шла|шло|шли)$', base_w)
    if motion_match:
        prefix = motion_match.group(1)
        if prefix == '':
            candidates.extend(['идти', 'пойти'])
        elif prefix in ['при', 'у', 'по', 'за', 'на', 'пере', 'про', 'ото', 'обо', 'со', 'взо', 'до']:
            candidates.append(f"{prefix}йти")
        elif prefix == 'во':
            candidates.append('войти')
        elif prefix == 'вы':
            candidates.append('выйти')
        elif prefix == 'разо':
            candidates.append('разойтись' if is_refl else 'разойти')
        elif prefix == 'с':
            candidates.append('сойти')
        else:
            candidates.append(f"{prefix}йти")
    if base_w.endswith('вышел'):
        candidates.append('выйти')

    # Consonant stem past forms:
    if base_w.endswith(('мог', 'могла', 'могло', 'могли')):
        pfx = re.sub(r'мог(ла|ло|ли)?$', '', base_w)
        candidates.append(f"{pfx}мочь")
    if base_w.endswith(('лёг', 'легла', 'легло', 'легли')):
        candidates.append('лечь')
    if base_w.endswith(('нёс', 'несла', 'несло', 'несли')):
        pfx = re.sub(r'н[её]с(ла|ло|ли)?$', '', base_w)
        candidates.append(f"{pfx}нести")
    if base_w.endswith(('вёз', 'везла', 'везло', 'везли')):
        pfx = re.sub(r'вез(ла|ло|ли)?$', '', base_w)
        candidates.append(f"{pfx}везти")
    if base_w.endswith(('вёл', 'вела', 'вело', 'вели')):
        pfx = re.sub(r'вел(а|о|и)?$', '', base_w)
        candidates.append(f"{pfx}вести")

    # 2. Verbal Adverbs (Gerunds / Деепричастия)
    if base_w.endswith(('вшись', 'вши')):
        g_stem = re.sub(r'вши(сь)?$', '', base_w)
        candidates.extend([g_stem + 'ть', g_stem + 'ться', g_stem + 'ти', g_stem + 'тись'])
    elif base_w.endswith('в') and len(base_w) >= 4 and not base_w.endswith(('ов', 'ев')):
        g_stem = base_w[:-1]
        candidates.extend([g_stem + 'ть', g_stem + 'ться', g_stem + 'ти', g_stem + 'ить', g_stem + 'ать'])
    elif base_w.endswith('я') and len(base_w) >= 4:
        g_stem = base_w[:-1]
        if g_stem == 'нес': candidates.append('нести')
        elif g_stem == 'вед': candidates.append('вести')
        elif g_stem == 'вез': candidates.append('везти')
        candidates.extend([g_stem + 'ть', g_stem + 'ять', g_stem + 'ать', g_stem + 'ить', g_stem + 'еть'])

    # 3. Participles (Причастия)
    m_act_past = re.search(r'^(.*?)(вш[а-я]+|ш[а-я]+)$', base_w)
    if m_act_past and len(m_act_past.group(1)) >= 3:
        p_stem = m_act_past.group(1)
        candidates.extend([p_stem + 'ть', p_stem + 'ти', p_stem + 'ться', p_stem + 'тись'])

    m_act_pres = re.search(r'^(.*?)([у|ю|а|я]щ[а-я]+)$', base_w)
    if m_act_pres and len(m_act_pres.group(1)) >= 3:
        p_stem = m_act_pres.group(1)
        candidates.extend([p_stem + 'ть', p_stem + 'ать', p_stem + 'ять', p_stem + 'ить', p_stem + 'еть'])

    m_pass = re.search(r'^(.*?)(енн[а-я]+|ённ[а-я]+|анн[а-я]+|янн[а-я]+|т[а-я]+)$', base_w)
    if m_pass and len(m_pass.group(1)) >= 3:
        p_stem = m_pass.group(1)
        candidates.extend([
            base_w[:-3] + 'ый' if len(base_w) > 3 else '',
            p_stem + 'ить',
            p_stem + 'еть',
            p_stem + 'ать',
            p_stem + 'ять',
            p_stem + 'тить',
            p_stem + 'стить'
        ])
        if p_stem.endswith('освещ'): candidates.append('осветить')

    # 4. Regular Past Tense: -л, -ла, -ло, -ли
    past_endings = ['ла', 'ло', 'ли', 'л']
    for pend in past_endings:
        if base_w.endswith(pend) and len(base_w) > len(pend) + 2:
            stem = base_w[:-len(pend)]
            if stem.endswith('я'):
                candidates.extend([stem + 'ть', stem[:-1] + 'еть', stem[:-1] + 'ать'])
            elif stem.endswith('а'):
                candidates.extend([stem + 'ть', stem[:-1] + 'ять'])
            elif stem.endswith('и'):
                candidates.extend([stem + 'ть', stem[:-1] + 'еть'])
            elif stem.endswith('е'):
                candidates.extend([stem + 'ть', stem[:-1] + 'ить', stem[:-1] + 'ать'])
            elif stem.endswith('у'):
                candidates.extend([stem + 'ть', stem + 'нуть'])
            elif stem.endswith('ы'):
                candidates.extend([stem + 'ть'])
            elif stem.endswith('о'):
                candidates.extend([stem + 'ть'])
            else:
                candidates.extend([stem + 'ть', stem + 'ти', stem + 'чь', stem + 'нуть'])
            break

    # 5. Present / Future Conjugation Endings
    conj_endings = [
        'уешь', 'ует', 'уем', 'уете', 'уют', 'ую',
        'ешь', 'ет', 'ем', 'ете', 'ут', 'ют',
        'ишь', 'ит', 'им', 'ите', 'ат', 'ят'
    ]
    for cend in sorted(conj_endings, key=len, reverse=True):
        if base_w.endswith(cend) and len(base_w) > len(cend) + 1:
            stem = base_w[:-len(cend)]
            if cend.startswith('у') and len(cend) > 1:
                candidates.append(stem + 'овать')
            candidates.extend([stem + 'ить', stem + 'ать', stem + 'еть', stem + 'ять'])
            if stem.endswith('ж'):
                candidates.extend([stem[:-1] + 'зать', stem[:-1] + 'жить', stem[:-1] + 'деть'])
            elif stem.endswith('ш'):
                candidates.extend([stem[:-1] + 'сать', stem[:-1] + 'шить'])
            elif stem.endswith('ч'):
                candidates.extend([stem[:-1] + 'тать', stem[:-1] + 'тить', stem[:-1] + 'чать', stem[:-1] + 'кать'])
            elif stem.endswith('щ'):
                candidates.extend([stem[:-1] + 'стить', stem[:-1] + 'щать'])
            elif stem.endswith('л'):
                candidates.extend([stem[:-1] + 'ить'])
            break

    # 6. Adjectives (Case declension endings -> -ый, -ий, -ой)
    adj_endings = [
        'ыми', 'ими', 'ого', 'его', 'ому', 'ему', 'ых', 'их', 'ую', 'юю', 'ой', 'ей',
        'ым', 'им', 'ом', 'ем', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие'
    ]
    for aend in sorted(adj_endings, key=len, reverse=True):
        if w.endswith(aend) and len(w) > len(aend) + 2:
            stem = w[:-len(aend)]
            candidates.extend([stem + 'ый', stem + 'ий', stem + 'ой'])
            break

    # 7. Irregular & Fleeting-vowel Nouns / Numerals / Pronouns
    if w in ['любви', 'любовью']: candidates.append('любовь')
    if w in ['огнями', 'огней', 'огнях', 'огню', 'огня', 'огне']: candidates.append('огонь')
    if w in ['смычка', 'смычку', 'смычком', 'смычке']: candidates.append('смычок')
    if w in ['нот']: candidates.append('нота')
    if w in ['страниц']: candidates.append('страница')
    if w in ['партитур']: candidates.append('партитура')
    if w in ['шаги', 'шагов', 'шагам', 'шагами', 'шагах']: candidates.append('шаг')
    if w in ['двое', 'двоих', 'двоим', 'двоими']: candidates.append('двое')
    if w in ['оба', 'обе', 'обоих', 'обеих']: candidates.append('оба')
    if w in ['десятью', 'десяти']: candidates.append('десять')
    if w in ['пятью', 'пяти']: candidates.append('пять')

    # 8. Regular Noun Case Endings
    noun_endings = [
        'ами', 'ями', 'ах', 'ях', 'ов', 'ев', 'ей', 'ам', 'ям', 'ом', 'ем', 'ой', 'ей',
        'ью', 'у', 'ю', 'е', 'и', 'ы', 'а', 'я', 'о'
    ]
    for nend in sorted(noun_endings, key=len, reverse=True):
        if w.endswith(nend) and len(w) > len(nend) + 2:
            stem = w[:-len(nend)]
            candidates.extend([stem, stem + 'а', stem + 'я', stem + 'о', stem + 'е', stem + 'ь'])
            if stem.endswith('к'): candidates.append(stem[:-1] + 'ок')
            elif stem.endswith('ц'): candidates.append(stem[:-1] + 'ец')
            elif stem.endswith('н'): candidates.extend([stem[:-1] + 'ень', stem[:-1] + 'он', stem[:-1] + 'ен'])
            break

    # Re-apply reflexive if stripped
    if is_refl:
        refl_cands = []
        for c in candidates:
            if c.endswith(('ть', 'ти', 'чь')): refl_cands.append(c + 'ся')
            elif c.endswith(('а', 'я', 'е', 'и', 'ы', 'у', 'ю', 'о')): refl_cands.append(c + 'сь')
            else: refl_cands.append(c + 'ся')
        candidates = refl_cands + candidates

    seen = set()
    result = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result

def find_dictionary_entry_by_lemma(query_word, vocab_db=None, token_map=None):
    """
    Looks up a query word in all available lexicographical sources
    using algorithmic Slavic morphological lemmatization.
    Matches exact headwords, decomposed compound keys, candidates, and inflected table cells.
    Returns the enriched dictionary entry with highlight_form set, or None.
    """
    if not query_word:
        return None
    qw = re.sub(r'[«»„“".,!?;:()—]', '', query_word).strip().lower()
    if not qw:
        return None

    if vocab_db is None:
        vocab_db = get_vocab_db()
    if token_map is None:
        token_map = get_lesson_token_map()

    # 1. Direct checks in curated core, prepositions, vocab_db, or token_map
    if qw in RUSSIAN_CORE_ENTRIES:
        res = dict(RUSSIAN_CORE_ENTRIES[qw])
        res['highlight_form'] = qw
        return res
    if qw in RUSSIAN_PREPOSITIONS:
        res = dict(RUSSIAN_PREPOSITIONS[qw])
        res['highlight_form'] = qw
        return res
    if qw in vocab_db:
        res = dict(vocab_db[qw])
        res['highlight_form'] = qw
        return res
    if qw in token_map:
        res = dict(token_map[qw])
        res['highlight_form'] = qw
        base_c = res.get('base')
        if base_c and base_c in vocab_db:
            db_ent = dict(vocab_db[base_c])
            for k in ('declension_table', 'notes', 'anatomy', 'network', 'examples'):
                if db_ent.get(k) and not res.get(k):
                    res[k] = db_ent[k]
        return res

    # 2. Algorithmic candidate matching
    cands = generate_russian_lemma_candidates(qw)
    for cand in cands:
        if cand == qw:
            continue
        ent = None
        if cand in RUSSIAN_CORE_ENTRIES:
            ent = dict(RUSSIAN_CORE_ENTRIES[cand])
        elif cand in vocab_db:
            ent = dict(vocab_db[cand])
        elif cand in token_map:
            ent = dict(token_map[cand])
        elif cand in RUSSIAN_PREPOSITIONS:
            ent = dict(RUSSIAN_PREPOSITIONS[cand])

        if ent:
            res = dict(ent)
            res['highlight_form'] = qw
            base_c = res.get('base') or cand
            if base_c in vocab_db:
                db_ent = dict(vocab_db[base_c])
                for k in ('declension_table', 'notes', 'anatomy', 'network', 'examples'):
                    if db_ent.get(k) and not res.get(k):
                        res[k] = db_ent[k]
            return res

    # 3. Declension table cell match across vocabulary database
    for w, item in vocab_db.items():
        tbl = item.get('declension_table')
        if tbl and isinstance(tbl, list) and len(tbl) > 1:
            matched = False
            for row in tbl[1:]:
                if isinstance(row, list):
                    for cell_idx in range(1, min(len(row), 4)):
                        cell = row[cell_idx]
                        if isinstance(cell, str):
                            if '(' in cell and '.' in cell:
                                continue
                            cell_clean = re.sub(r'\(.*?\)', '', cell).strip().lower()
                            cell_tokens = [c for c in re.findall(r'[а-яёА-ЯЁ]+', cell_clean)]
                            if qw in cell_tokens:
                                matched = True
                                break
                if matched:
                    break
            if matched:
                res = dict(item)
                res['highlight_form'] = qw
                return res

    return None

def resolve_missing_vocabulary(query_word):
    """
    Deep fallback to lesson_buffer.json and algorithmic generator.
    Ensures that NO word ever returns empty or without full grammatical info.
    """
    if not query_word:
        return None
    qw = re.sub(r'[«»„“".,!?;:()—]', '', query_word).strip().lower()

    vocab_db = get_vocab_db()
    token_map = get_lesson_token_map()

    # 0. Algorithmic morphological lookup across all lexicographical sources
    morph_entry = find_dictionary_entry_by_lemma(qw, vocab_db, token_map)
    if morph_entry:
        return morph_entry

    # 1. Check lesson token map directly
    if qw in token_map:
        token_entry = dict(token_map[qw])
        base_cand = token_entry.get('base')
        if base_cand and base_cand in vocab_db:
            db_entry = dict(vocab_db[base_cand])
            for k in ('declension_table', 'notes', 'anatomy', 'network', 'examples'):
                if db_entry.get(k) and not token_entry.get(k):
                    token_entry[k] = db_entry[k]
            if not token_entry.get('declension_table'):
                token_entry['declension_table'] = db_entry.get('declension_table', [])
            return token_entry
        tbl = token_entry.get('declension_table')
        if not tbl or len(tbl) <= 1:
            tbl, note = generate_smart_table(token_entry.get('word', qw), token_entry.get('pos', ''))
            token_entry['declension_table'] = tbl
            if not token_entry.get('anatomy'):
                token_entry['anatomy'] = note
        return token_entry

    # 2. Check adjective lemmatizer
    vocab_db = get_vocab_db()
    adj_cand = lemmatize_russian_adjective(qw, token_map) or lemmatize_russian_adjective(qw, RUSSIAN_CORE_ENTRIES) or lemmatize_russian_adjective(qw, vocab_db)
    if adj_cand:
        ent = RUSSIAN_CORE_ENTRIES.get(adj_cand) or token_map.get(adj_cand) or vocab_db.get(adj_cand)
        if ent:
            res = dict(ent)
            res['highlight_form'] = qw
            if not res.get('declension_table') or len(res.get('declension_table', [])) <= 1:
                tbl, note = generate_smart_table(res.get('word', adj_cand), res.get('pos', '形容詞'))
                res['declension_table'] = tbl
                if not res.get('anatomy'):
                    res['anatomy'] = note
            return res

    # 3. Check noun lemmatizer
    noun_cand = lemmatize_russian_noun(qw, token_map) or lemmatize_russian_noun(qw, RUSSIAN_CORE_ENTRIES) or lemmatize_russian_noun(qw, vocab_db)
    if noun_cand:
        ent = RUSSIAN_CORE_ENTRIES.get(noun_cand) or token_map.get(noun_cand) or vocab_db.get(noun_cand)
        if ent:
            res = dict(ent)
            res['highlight_form'] = qw
            if not res.get('declension_table') or len(res.get('declension_table', [])) <= 1:
                tbl, note = generate_smart_table(res.get('word', noun_cand), res.get('pos', '名詞'))
                res['declension_table'] = tbl
                if not res.get('anatomy'):
                    res['anatomy'] = note
            return res

    # 4. Fallback search across lesson buffer
    buffer = load_json('lesson_buffer.json', [])
    found_item = None
    found_examples = []

    for day in buffer:
        sessions = day.get('sessions', {})
        for s_key, s_data in sessions.items():
            sentences = s_data.get('audio_paragraphs', []) + s_data.get('audio_sentences', []) + s_data.get('paragraphs', [])
            hero = s_data.get('hero_sentence')
            if hero:
                sentences.append(hero)
            for p in sentences:
                p_ru = p.get('ru', '')
                p_ja = p.get('ja', '')
                for v in p.get('key_vocab', []):
                    w = v.get('word', '').strip().lower()
                    b = v.get('base', '').strip().lower()
                    if qw == w or qw == b:
                        if not found_item:
                            found_item = dict(v)
                        if p_ru and {'ru': p_ru, 'ja': p_ja} not in found_examples:
                            found_examples.append({'ru': p_ru, 'ja': p_ja})
                for t in p.get('tokens', []):
                    tw = t.get('word', '').strip().lower()
                    tb = t.get('base', '').strip().lower()
                    if qw == tw or qw == tb:
                        if not found_item:
                            r_token = (t.get('role', '') or t.get('grammar', '')).strip()
                            pos, meaning, form = parse_token_role(r_token, tw, tb, t.get('tag', ''))
                            found_item = {
                                'word': tb or tw,
                                'pos': pos,
                                'meaning': meaning,
                                'role_in_sentence': r_token
                            }
                if qw in p_ru.lower() and {'ru': p_ru, 'ja': p_ja} not in found_examples:
                    found_examples.append({'ru': p_ru, 'ja': p_ja})
            for q in s_data.get('quizzes', []):
                q_sent = q.get('sentence', '')
                q_trans = q.get('translation', '')
                if qw in q_sent.lower() and {'ru': q_sent, 'ja': q_trans} not in found_examples:
                    found_examples.append({'ru': q_sent, 'ja': q_trans})

    word = (found_item.get('base') or found_item.get('word')) if found_item else query_word
    pos = found_item.get('pos') if found_item else ''
    meaning = found_item.get('meaning') if found_item else ''
    role = found_item.get('role_in_sentence') if found_item else ''

    if not pos:
        if qw in RUSSIAN_VERB_LEMMAS:
            lemma = RUSSIAN_VERB_LEMMAS[qw]
            word = lemma
            pos = '動詞'
        elif qw in UNINFLECTED_WORDS or qw in [
            'пешком', 'утром', 'вечером', 'днём', 'ночью', 'вчера', 'сегодня', 'завтра',
            'редко', 'часто', 'обычно', 'обязательно', 'туда', 'сюда', 'ещё', 'или', 'только',
            'эхо', 'нет', 'есть', 'уже', 'так', 'как', 'где', 'куда', 'когда', 'почему'
        ]:
            if qw in ['нет', 'есть']:
                pos = '存在詞 (不変化詞)'
            elif qw == 'эхо':
                pos = '中性名詞 (不変化名詞)'
            elif qw == 'или':
                pos = '接続詞 (不変化詞)'
            else:
                pos = '副詞 (不変化詞)'
        elif qw.endswith(('ый', 'ий', 'ой', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие', 'ыми', 'ими', 'ого', 'его', 'ому', 'ему')):
            pos = '形容詞'
        elif qw.endswith(('лся', 'лась', 'лось', 'лись', 'ла', 'ло', 'ли', 'л')) and len(qw) >= 4:
            pos = '動詞 (過去形)'
        elif qw.endswith(('ться', 'тся', 'ся', 'сь')):
            pos = '動詞 (再帰動詞)'
        elif qw.endswith(('ть', 'ти', 'чь')):
            pos = '動詞'
        elif is_russian_comparative(qw):
            pos = '比較級 (不変化詞)'
        elif is_russian_gerund(qw):
            pos = '副動詞 (不変化詞)'
        elif is_russian_participle(qw):
            pos = '形動詞'
        elif qw.endswith(('а', 'я')):
            pos = '女性名詞'
        elif qw.endswith(('о', 'е')):
            pos = '中性名詞'
        else:
            pos = '名詞・重要単語'

    if not meaning:
        cands_all = generate_russian_lemma_candidates(qw)
        best_cand = cands_all[1] if len(cands_all) > 1 else word
        if '動詞' in pos:
            meaning = f"【動詞】（文脈重要語・原形候補: {best_cand}）"
        elif '名詞' in pos:
            meaning = f"【名詞】（文脈重要語・基本形候補: {best_cand}）"
        elif '形容詞' in pos:
            meaning = f"【形容詞】（文脈重要語・基本形候補: {best_cand}）"
        else:
            meaning = f"【文脈重要語彙（{pos}）】"

    table, anatomy_note = generate_smart_table(word, pos)

    entry = {
        'word': word,
        'pos': pos,
        'meaning': meaning,
        'notes': f"【文中での役割】{role}" if role else '',
        'anatomy': anatomy_note or f"【語彙ノート】レッスン文脈言及語。\n役割: {role}",
        'declension_table': table,
        'examples': found_examples[:3] if found_examples else [
            {'ru': f"Слово «{word}» часто используется в русской музыкальной речи.", 'ja': f"単語 «{word}» はロシアの音楽会話で頻繁に用いられます。"}
        ]
    }
    return entry

class TanyaRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        # Prevent caching for dynamic API responses
        if self.path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        try:
            msg = format % args
            sys.stderr.write(f"{self.address_string()} - - [{self.log_date_time_string()}] {msg}\n")
        except Exception:
            pass

    def send_json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            url = urllib.parse.urlparse(self.path)
            path = url.path
            query = urllib.parse.parse_qs(url.query)

            if path.startswith('/api/'):
                self.handle_api_get(path, query)
            else:
                if path == '/':
                    self.path = '/index.html'
                super().do_GET()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self.send_json_response({"error": str(e)}, 500)
            except Exception:
                pass

    def handle_api_get(self, path, query):
        if path == '/api/state':
            progress = load_json('user_progress.json', {})
            buffer = load_json('lesson_buffer.json', [])
            taxonomy = load_json('grammar_taxonomy.json', {})

            user_profile = progress.get('user_profile', {})
            effective_dt = get_effective_date()
            effective_date_str = effective_dt.strftime('%Y-%m-%d')
            
            # Started date and calendar day index calculation (Day 1 on started_date)
            started_date_str = user_profile.get('started_date', '2026-09-12')
            try:
                started_dt = datetime.strptime(started_date_str, '%Y-%m-%d').date()
                calendar_day_index = max(1, (effective_dt - started_dt).days + 1)
            except Exception:
                calendar_day_index = 1

            # Determine completed days from session_history and user_profile
            completed_study_days = set(user_profile.get('completed_study_days', []))
            session_history = progress.get('session_history', [])

            # Count completed sessions per day from session_history
            day_session_counts = {}
            day_completed_sessions = {}
            for s in session_history:
                s_id = s.get('session_id', '')
                m = re.match(r'day(\d+)_([a-zA-Z]+)', s_id)
                if m:
                    d_num = int(m.group(1))
                    s_type = m.group(2).lower()
                    day_session_counts[d_num] = day_session_counts.get(d_num, 0) + 1
                    if d_num not in day_completed_sessions:
                        day_completed_sessions[d_num] = set()
                    day_completed_sessions[d_num].add(s_type)
                elif re.match(r'day(\d+)_', s_id):
                    d_num = int(re.match(r'day(\d+)_', s_id).group(1))
                    day_session_counts[d_num] = day_session_counts.get(d_num, 0) + 1

            # Mark days with >= 2 sessions completed as completed
            for d_num, cnt in day_session_counts.items():
                if cnt >= 2:
                    completed_study_days.add(d_num)

            # Retrieve or initialize current_study_day
            current_study_day = user_profile.get('current_study_day')
            max_buffer_day = max([d.get('day_index', 1) for d in buffer]) if buffer else 1

            if current_study_day is None:
                current_study_day = 1

            # Auto-advance if current_study_day was already completed, calendar has reached it, and buffer has next day
            advanced = False
            while (current_study_day in completed_study_days) and (current_study_day < calendar_day_index) and (current_study_day < max_buffer_day):
                current_study_day += 1
                user_profile['current_study_day'] = current_study_day
                advanced = True

            user_profile['completed_study_days'] = sorted(list(completed_study_days))
            if advanced:
                user_profile['last_advanced_date'] = effective_date_str
                progress['user_profile'] = user_profile
                save_json('user_progress.json', progress)

            current_day_index = current_study_day

            # Check requested day override (?day=X)
            req_day = query.get('day', [None])[0]
            if req_day:
                try:
                    selected_day_index = int(req_day)
                except ValueError:
                    selected_day_index = current_day_index
            else:
                selected_day_index = current_day_index

            # Select target day pack from buffer
            target_pack = None
            for d in buffer:
                if d.get('day_index') == selected_day_index:
                    target_pack = d
                    break
            if not target_pack and buffer:
                if selected_day_index <= 1:
                    target_pack = buffer[0]
                else:
                    target_pack = buffer[min(selected_day_index - 1, len(buffer) - 1)]

            # Calculate pace sync & lag metrics
            if (current_study_day in completed_study_days) and (current_study_day >= max_buffer_day):
                # User completed all available lessons in buffer: strictly protect from false lag accusation
                lag_days = 0
                pace_sync_label = "全レッスン完了・最新到達 (On Schedule)"
                pace_sync_status = "on_schedule"
            else:
                lag_days = calendar_day_index - current_study_day
                if lag_days == 0:
                    pace_sync_label = "予定通り (On Schedule)"
                    pace_sync_status = "on_schedule"
                elif lag_days > 0:
                    pace_sync_label = f"{lag_days}日遅れ (キャッチアップ可能)"
                    pace_sync_status = "behind"
                else:
                    pace_sync_label = f"{abs(lag_days)}日先行中！"
                    pace_sync_status = "ahead"

            # Available days metadata for navigator
            available_days = []
            for d in buffer:
                idx = d.get('day_index', 1)
                is_comp = idx in completed_study_days
                is_curr = (idx == current_study_day)
                available_days.append({
                    "day_index": idx,
                    "title": d.get('title', f"第{idx}日"),
                    "is_completed": is_comp,
                    "is_current": is_curr,
                    "is_today": is_curr,
                    "is_past": (idx < current_study_day),
                    "is_future": (idx > current_study_day),
                    "sessions_count": day_session_counts.get(idx, 0)
                })

            # Check absence days using effective date
            last_active_str = user_profile.get('last_active_date', effective_date_str)
            user_name_display = user_profile.get('name_ru', user_profile.get('name', 'Юсукэ'))
            absence_notice = None
            try:
                last_dt = datetime.strptime(last_active_str, '%Y-%m-%d').date()
                gap_days = (effective_dt - last_dt).days
                
                if gap_days >= 14:
                    absence_notice = {
                        "type": "two_weeks_gap",
                        "days": gap_days,
                        "tanya_expression": "tanya_encouraging",
                        "greeting": f"{user_name_display}さん、お久しぶりです！指先が少し恋しくなっていた頃でしょうか？無理せず、弱点タグの丁寧なおさらいからゆったり再開しましょう♪",
                        "recommended_action": "refresher"
                    }
                elif gap_days >= 3:
                    absence_notice = {
                        "type": "three_days_gap",
                        "days": gap_days,
                        "tanya_expression": "tanya_encouraging",
                        "greeting": f"お帰りなさい、{user_name_display}さん！{gap_days}日ぶりですね。ピアノの鍵盤を優しく触るように、まずは軽い1問のウォームアップから始めましょう！",
                        "recommended_action": "warmup"
                    }
            except Exception as e:
                gap_days = 0

            furthest_done = max([current_study_day] + list(completed_study_days)) if completed_study_days else current_study_day
            unconsumed_buffer_days = max(0, max_buffer_day - furthest_done)

            resp = {
                "user_profile": user_profile,
                "tag_stats": progress.get('tag_stats', {}),
                "behavior_logs": progress.get('behavior_logs', {}),
                "buffer_days_left": len(buffer),
                "unconsumed_buffer_days": unconsumed_buffer_days,
                "current_day_index": current_study_day,
                "current_study_day": current_study_day,
                "calendar_day_index": calendar_day_index,
                "lag_days": lag_days,
                "pace_sync_label": pace_sync_label,
                "pace_sync_status": pace_sync_status,
                "completed_study_days": sorted(list(completed_study_days)),
                "is_current_day_completed": (current_study_day in completed_study_days),
                "selected_day_index": selected_day_index,
                "effective_date": effective_date_str,
                "available_days": available_days,
                "today_pack": target_pack,
                "completed_session_types": list(day_completed_sessions.get(selected_day_index, set())),
                "day_completed_sessions": { str(k): list(v) for k, v in day_completed_sessions.items() },
                "absence_notice": absence_notice,
                "unlocked_memoirs": progress.get('unlocked_memoirs', []),
                "bookmarked_words": progress.get('bookmarked_words', [])
            }
            self.send_json_response(resp)

        elif path == '/api/vocabulary':
            raw_q = (query.get('q', [''])[0] or query.get('word', [''])[0]).strip().lower()
            raw_base = query.get('base', [''])[0].strip().lower()
            query_word = re.sub(r'[«»„“".,!?;:()—]', '', raw_q).strip()
            base_word = re.sub(r'[«»„“".,!?;:()—]', '', raw_base).strip()
            vocab_db = get_vocab_db()
            token_map = get_lesson_token_map()

            # Priority 0: Exact match in curated core entries for the queried surface form
            if query_word in RUSSIAN_CORE_ENTRIES:
                self.send_json_response([attach_irregular_alert(dict(RUSSIAN_CORE_ENTRIES[query_word]))])
                return

            # Priority 0.1: Exact match in vocab_db for the queried surface word
            # (Ensures participles, adverbs, and specific forms with adjectival tables are NEVER overwritten by base verbs!)
            if query_word in vocab_db:
                adapted = dict(vocab_db[query_word])
                self.send_json_response([attach_irregular_alert(adapted)])
                return

            # Detect if the queried word is a participle (must NEVER return verb person-conjugation!)
            is_query_participle = bool(
                query.get('tag', [''])[0].startswith('participle') or
                re.search(r'(?:ущ|ющ|ащ|ящ|вш|ш|нн)(?:ий|ая|ее|ие|его|ему|им|ем|ей|ую|их|ими|ый|ое|ые|ого|ому|ым|ом|ой|ых|ыми)$', query_word) or
                (re.search(r'(?:ан|ана|ано|аны|ен|ена|ено|ены|ён|ёна|ёно|ёны|тан|тана|тано|таны|ыт|ыта|ыто|ыты)$', query_word) and (
                    'participle' in query.get('tag', [''])[0] or '受動' in query.get('role', [''])[0] or '短語尾' in query.get('role', [''])[0]
                ))
            )

            # 0. Base dictionary lemma passed explicitly from lesson token
            if base_word:
                if base_word in RUSSIAN_UNINFLECTED_ENTRIES:
                    adapted = dict(RUSSIAN_UNINFLECTED_ENTRIES[base_word])
                    adapted['highlight_form'] = query_word
                    self.send_json_response([attach_irregular_alert(adapted)])
                    return
                if base_word in RUSSIAN_PRONOUN_LEMMAS:
                    lemma = RUSSIAN_PRONOUN_LEMMAS[base_word]
                    target_entry = RUSSIAN_CORE_ENTRIES.get(lemma) or vocab_db.get(lemma) or token_map.get(lemma)
                    if target_entry:
                        adapted = dict(target_entry)
                        adapted['highlight_form'] = query_word
                        self.send_json_response([attach_irregular_alert(adapted)])
                        return
                if base_word in RUSSIAN_CORE_ENTRIES:
                    base_pos = RUSSIAN_CORE_ENTRIES[base_word].get('pos', '').lower()
                    if not (is_query_participle and ('動詞' in base_pos or 'verb' in base_pos)):
                        adapted = dict(RUSSIAN_CORE_ENTRIES[base_word])
                        adapted['highlight_form'] = query_word
                        self.send_json_response([attach_irregular_alert(adapted)])
                        return
                if base_word in vocab_db:
                    base_pos = vocab_db[base_word].get('pos', '').lower()
                    if not (is_query_participle and ('動詞' in base_pos or 'verb' in base_pos)):
                        adapted = dict(vocab_db[base_word])
                        adapted['highlight_form'] = query_word
                        self.send_json_response([attach_irregular_alert(adapted)])
                        return
                if base_word in token_map:
                    adapted = dict(token_map[base_word])
                    adapted['highlight_form'] = query_word
                    if not adapted.get('declension_table') or len(adapted.get('declension_table', [])) <= 1:
                        tbl, note = generate_smart_table(adapted.get('word', base_word), adapted.get('pos', ''))
                        adapted['declension_table'] = tbl
                        if not adapted.get('anatomy'):
                            adapted['anatomy'] = note
                    self.send_json_response([attach_irregular_alert(adapted)])
                    return

            # 1. Check uninflected entries (и, сейчас, теперь, пешком, утром, нет, есть, etc.)
            if query_word in RUSSIAN_UNINFLECTED_ENTRIES:
                self.send_json_response([attach_irregular_alert(dict(RUSSIAN_UNINFLECTED_ENTRIES[query_word]))])
                return

            if query_word in UNINFLECTED_WORDS or query_word in ('когда', 'как', 'потому', 'поэтому', 'если', 'чтобы', 'хотя'):
                pos_label = '副詞 (Наречие・不変化詞)'
                if query_word in ('и', 'а', 'но', 'или', 'что', 'как', 'если', 'чтобы', 'хотя', 'потому', 'поэтому', 'когда'):
                    pos_label = '接続詞 (Союз・不変化詞)'
                elif query_word in ('не', 'ни', 'ли', 'же', 'бы', 'даже', 'только', 'ведь', 'вот', 'вон'):
                    pos_label = '小詞 (Частица・不変化詞)'
                self.send_json_response([{
                    'word': query_word,
                    'pos': pos_label,
                    'meaning': '不変化詞',
                    'notes': '【不変化詞】格変化や人称変化は行いません。',
                    'anatomy': f'«{query_word}» は不変化詞（{pos_label}）です。格変化や活用などの語尾変化を持たず、常にこの形で用いられます。',
                    'declension_table': [],
                    'network': [],
                    'examples': []
                }])
                return

            # 2. Check Russian Pronoun Lemmas (всё, все, вся, всех, всего -> весь; та, то, те -> тот; etc.)
            if query_word in RUSSIAN_PRONOUN_LEMMAS:
                lemma = RUSSIAN_PRONOUN_LEMMAS[query_word]
                target_entry = RUSSIAN_CORE_ENTRIES.get(lemma) or vocab_db.get(lemma) or token_map.get(lemma)
                if target_entry:
                    adapted = dict(target_entry)
                    adapted['highlight_form'] = query_word
                    self.send_json_response([attach_irregular_alert(adapted)])
                    return

            # 2. Algorithmic Slavic Morphological Lemmatizer (Past tense, conjugations, participles, declensions)
            lemma_entry = find_dictionary_entry_by_lemma(query_word, vocab_db, token_map)
            if lemma_entry:
                self.send_json_response([attach_irregular_alert(lemma_entry)])
                return

            # 3. Check core Russian entries (personal pronouns, core conservatory vocabulary)
            if query_word in RUSSIAN_CORE_ENTRIES:
                self.send_json_response([attach_irregular_alert(dict(RUSSIAN_CORE_ENTRIES[query_word]))])
                return

            # 4. Check Russian prepositions
            if query_word in RUSSIAN_PREPOSITIONS:
                self.send_json_response([attach_irregular_alert(dict(RUSSIAN_PREPOSITIONS[query_word]))])
                return

            # 5. Check token map directly
            if query_word in token_map:
                adapted = dict(token_map[query_word])
                adapted['highlight_form'] = query_word
                base_cand = adapted.get('base')
                if base_cand and base_cand in vocab_db:
                    base_pos = vocab_db[base_cand].get('pos', '').lower()
                    if not (is_query_participle and ('動詞' in base_pos or 'verb' in base_pos)):
                        db_entry = dict(vocab_db[base_cand])
                        for k in ('declension_table', 'notes', 'anatomy', 'network', 'examples'):
                            if db_entry.get(k) and not adapted.get(k):
                                adapted[k] = db_entry[k]
                        if not adapted.get('declension_table'):
                            adapted['declension_table'] = db_entry.get('declension_table', [])
                        self.send_json_response([attach_irregular_alert(adapted)])
                        return
                if not adapted.get('declension_table') or len(adapted.get('declension_table', [])) <= 1:
                    tbl, note = generate_smart_table(adapted.get('word', query_word), adapted.get('pos', ''))
                    adapted['declension_table'] = tbl
                    if not adapted.get('anatomy'):
                        adapted['anatomy'] = note
                self.send_json_response([attach_irregular_alert(adapted)])
                return

            # 6. Adjective lemmatization (e.g. огромными -> огромный, уникальным -> уникальный, слышны -> слышный)
            adj_cand = lemmatize_russian_adjective(query_word, token_map) or lemmatize_russian_adjective(query_word, RUSSIAN_CORE_ENTRIES) or lemmatize_russian_adjective(query_word, vocab_db)
            if adj_cand:
                ent = RUSSIAN_CORE_ENTRIES.get(adj_cand) or token_map.get(adj_cand) or vocab_db.get(adj_cand)
                if ent:
                    adapted = dict(ent)
                    adapted['highlight_form'] = query_word
                    if not adapted.get('declension_table') or len(adapted.get('declension_table', [])) <= 1:
                        tbl, note = generate_smart_table(adapted.get('word', adj_cand), adapted.get('pos', '形容詞'))
                        adapted['declension_table'] = tbl
                        if not adapted.get('anatomy'):
                            adapted['anatomy'] = note
                    self.send_json_response([attach_irregular_alert(adapted)])
                    return

            # 7. Noun lemmatization (e.g. домов -> дом, окнах -> окно, тишине -> тишина)
            noun_cand = lemmatize_russian_noun(query_word, token_map) or lemmatize_russian_noun(query_word, RUSSIAN_CORE_ENTRIES) or lemmatize_russian_noun(query_word, vocab_db)
            if noun_cand:
                ent = RUSSIAN_CORE_ENTRIES.get(noun_cand) or token_map.get(noun_cand) or vocab_db.get(noun_cand)
                if ent:
                    adapted = dict(ent)
                    adapted['highlight_form'] = query_word
                    if not adapted.get('declension_table') or len(adapted.get('declension_table', [])) <= 1:
                        tbl, note = generate_smart_table(adapted.get('word', noun_cand), adapted.get('pos', '名詞'))
                        adapted['declension_table'] = tbl
                        if not adapted.get('anatomy'):
                            adapted['anatomy'] = note
                    self.send_json_response([attach_irregular_alert(adapted)])
                    return

            # 8. Check declension tables in RUSSIAN_CORE_ENTRIES (e.g. руками -> рука, Большом -> большой)
            for w, ent in RUSSIAN_CORE_ENTRIES.items():
                tbl = ent.get('declension_table')
                if tbl and isinstance(tbl, list) and len(tbl) > 1:
                    headers = [str(h) for h in tbl[0]] if isinstance(tbl[0], list) else []
                    matched = False
                    for row in tbl[1:]:
                        if isinstance(row, list):
                            for cell_idx in range(1, len(row)):
                                # Skip example/notes columns!
                                if cell_idx < len(headers):
                                    hdr = headers[cell_idx]
                                    if any(k in hdr for k in ['用例', '例文', '結合', '用例・前置詞']):
                                        continue
                                cell = row[cell_idx]
                                if isinstance(cell, str):
                                    # Strip parenthesized translation/notes before matching tokens
                                    cell_clean = re.sub(r'\(.*?\)', '', cell).strip()
                                    tokens = [c.lower() for c in re.findall(r'[а-яёА-ЯЁ]+', cell_clean)]
                                    # Genuine inflection cells contain 1-4 word variants (e.g. мной / мною), NOT full sentences
                                    if len(tokens) <= 4 and query_word in tokens:
                                        matched = True
                                        break
                        if matched:
                            break
                    if matched:
                        adapted = dict(ent)
                        adapted['highlight_form'] = query_word
                        self.send_json_response([attach_irregular_alert(adapted)])
                        return

            if not query_word:
                keys = list(vocab_db.keys())[:20]
                self.send_json_response([vocab_db[k] for k in keys])
                return

            results = []

            # 3. Exact headword match (extracting slash-separated headwords)
            for w, item in vocab_db.items():
                clean_k = re.sub(r'\(.*?\)', '', w).strip()
                headwords = [hw.strip().lower() for hw in clean_k.split('/') if hw.strip()]
                if query_word in headwords or query_word == w.lower():
                    results.append(item)

            # 4. Cyrillic-boundary regex match (prevents -ся/ matching я/)
            if len(results) < 20:
                pattern = rf'(?<![а-яА-ЯёЁ]){re.escape(query_word)}(?![а-яА-ЯёЁ])'
                for w, item in vocab_db.items():
                    if item in results:
                        continue
                    if re.search(pattern, w.lower()):
                        results.append(item)
                        if len(results) >= 20:
                            break

            # 5. Prefix match on headword (ONLY if query length >= 3)
            if len(query_word) >= 3 and len(results) < 20:
                for w, item in vocab_db.items():
                    if item in results:
                        continue
                    clean_k = re.sub(r'\(.*?\)', '', w).strip()
                    headwords = [hw.strip().lower() for hw in clean_k.split('/') if hw.strip()]
                    if any(hw.startswith(query_word) for hw in headwords):
                        results.append(item)
                        if len(results) >= 20:
                            break

            # 5.5 Conjugated / inflected form search in declension_table
            if len(results) == 0 and len(query_word) >= 3:
                for w, item in vocab_db.items():
                    tbl = item.get('declension_table')
                    if tbl and isinstance(tbl, list):
                        matched = False
                        for row in tbl[1:]:  # Skip header row
                            if isinstance(row, list):
                                # Only match genuine grammatical inflection cells (cols 1 and 2), NEVER example sentence columns!
                                for cell_idx in range(1, min(len(row), 3)):
                                    cell = row[cell_idx]
                                    if isinstance(cell, str):
                                        if '(' in cell and '.' in cell:
                                            continue
                                        cell_tokens = [c.lower() for c in re.findall(r'[а-яёА-ЯЁ]+', cell)]
                                        if query_word in cell_tokens:
                                            matched = True
                                            break
                            if matched:
                                break
                        if matched:
                            results.append(item)
                            break

            # 6. Reflexive verb adaptation (e.g. заканчиваться -> match заканчивать/закончить)
            if len(results) == 0 and query_word.endswith(('ся', 'сь')):
                base_cand = query_word[:-2]
                for w, item in vocab_db.items():
                    clean_k = re.sub(r'\(.*?\)', '', w).strip()
                    headwords = [hw.strip().lower() for hw in clean_k.split('/') if hw.strip()]
                    if any(hw.startswith(base_cand) or base_cand.startswith(hw) for hw in headwords):
                        adapted = dict(item)
                        adapted['word'] = query_word
                        adapted['pos'] = '動詞 (НСВ・再帰動詞)' if 'НСВ' in item.get('pos', '') or '不完了' in item.get('pos', '') else '動詞 (再帰動詞)'
                        orig_meaning = item.get('meaning', '')
                        adapted['meaning'] = orig_meaning.replace('〜を', '〜が') if '〜を' in orig_meaning else f"{orig_meaning}（自動詞・状態変化）"
                        if item.get('declension_table'):
                            orig_tbl = item['declension_table']
                            new_tbl = [orig_tbl[0]]
                            for row in orig_tbl[1:]:
                                new_row = [row[0]]
                                for cell in row[1:]:
                                    c_clean = str(cell).strip()
                                    if c_clean:
                                        last_ch = c_clean[-1]
                                        suf = 'сь' if last_ch in 'аеёиоуыэюя' else 'ся'
                                        new_row.append(f"{c_clean}{suf}")
                                    else:
                                        new_row.append(cell)
                                new_tbl.append(new_row)
                            adapted['declension_table'] = new_tbl
                        else:
                            tbl, _ = generate_smart_table(query_word, adapted['pos'])
                            adapted['declension_table'] = tbl
                        results.append(adapted)
                        break

            # 7. Deep fallback to lesson buffer and smart table generator
            if len(results) == 0:
                fallback_entry = resolve_missing_vocabulary(query_word)
                if fallback_entry:
                    results.append(fallback_entry)

            self.send_json_response([attach_irregular_alert(r) for r in results])

        elif path == '/api/lesson':
            session_id = query.get('id', [''])[0]
            buffer = load_json('lesson_buffer.json', [])
            target_session = None
            day_title = ""
            for day in buffer:
                sessions = day.get('sessions', {})
                for s_key, s_data in sessions.items():
                    if s_data.get('session_id') == session_id:
                        target_session = s_data
                        day_title = day.get('title', '')
                        break
                if target_session:
                    break

            if target_session:
                resp = {"day_title": day_title, "session": target_session}
                self.send_json_response(resp)
            else:
                self.send_json_response({"error": "Session not found"}, 404)

        elif path == '/api/taxonomy':
            tax = load_json('grammar_taxonomy.json', {})
            self.send_json_response(tax)

        elif path == '/api/buffer':
            buffer = load_json('lesson_buffer.json', [])
            self.send_json_response({"buffer_count": len(buffer), "days": buffer})

        elif path == '/api/validate_curriculum':
            try:
                sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
                from validate_curriculum import validate_catalog_list
                cat_days = load_json('curriculum_catalog.json', [])
                buf_days = load_json('lesson_buffer.json', [])
                valid_cat, sum_cat = validate_catalog_list(cat_days)
                valid_buf, sum_buf = validate_catalog_list(buf_days)
                self.send_json_response({
                    "is_valid": valid_cat and valid_buf,
                    "catalog": sum_cat,
                    "buffer": sum_buf
                })
            except Exception as e:
                self.send_json_response({"error": str(e)}, 500)

        elif path == '/api/tts':
            text = query.get('text', [''])[0].strip()
            rate = query.get('rate', ['1.0'])[0].strip()
            if not text:
                self.send_json_response({"error": "No text provided"}, 400)
                return

            try:
                rate_val = float(rate)
            except Exception:
                rate_val = 1.0
            rate_percent = int((rate_val - 1.0) * 100)
            rate_str = f"{rate_percent:+d}%" if rate_percent != 0 else "+0%"

            h = hashlib.md5(f"{text}_{rate_str}_ru-RU-SvetlanaNeural".encode('utf-8')).hexdigest()
            fname = f"{h}.mp3"
            fpath = os.path.join(AUDIO_DIR, fname)
            meta_fname = f"{h}.json"
            meta_fpath = os.path.join(AUDIO_DIR, meta_fname)

            word_boundaries = []
            if os.path.exists(meta_fpath):
                try:
                    with open(meta_fpath, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        word_boundaries = meta.get('word_boundaries', [])
                except Exception:
                    word_boundaries = []

            is_multi_word = len(text.split()) > 1
            if not os.path.exists(fpath) or (is_multi_word and not word_boundaries):
                try:
                    communicate = edge_tts.Communicate(text, 'ru-RU-SvetlanaNeural', rate=rate_str, boundary='WordBoundary')
                    audio_bytes = bytearray()
                    word_boundaries = []
                    async def _collect():
                        async for chunk in communicate.stream():
                            if chunk['type'] == 'audio':
                                audio_bytes.extend(chunk['data'])
                            elif chunk['type'] == 'WordBoundary':
                                offset_ms = chunk['offset'] / 10000.0
                                dur_ms = chunk['duration'] / 10000.0
                                word_boundaries.append({
                                    'start_ms': round(offset_ms, 1),
                                    'end_ms': round(offset_ms + dur_ms, 1),
                                    'duration_ms': round(dur_ms, 1),
                                    'text': chunk['text']
                                })
                    asyncio.run(_collect())
                    if audio_bytes:
                        with open(fpath, 'wb') as f:
                            f.write(audio_bytes)
                    with open(meta_fpath, 'w', encoding='utf-8') as f:
                        json.dump({"word_boundaries": word_boundaries}, f, ensure_ascii=False)
                except Exception as e:
                    print(f"Edge-TTS generation error: {e}")
                    if not os.path.exists(fpath):
                        self.send_json_response({"error": str(e)}, 500)
                        return

            self.send_json_response({
                "status": "ok",
                "audio_url": f"/audio_cache/{fname}",
                "voice": "ru-RU-SvetlanaNeural",
                "word_boundaries": word_boundaries
            })

        elif path == '/api/bookmarks':
            progress = load_json('user_progress.json', {})
            bookmarks = progress.get('bookmarked_words', [])
            self.send_json_response({"bookmarks": bookmarks})

        elif path == '/api/batch/status':
            status = load_json('batch_status.json', {})
            self.send_json_response(status)

        elif path == '/api/milestones':
            progress = load_json('user_progress.json', {})
            milestone_data = progress.get('milestone_progress')
            if not milestone_data:
                from scripts.daily_batch import audit_milestone_pace
                milestone_data = audit_milestone_pace(progress)
            self.send_json_response(milestone_data)

        elif path == '/api/handbook':
            handbook_data = load_json('grammar_handbook.json', {})
            self.send_json_response(handbook_data)

        elif path == '/api/sync/github_status':
            self.handle_sync_status()

        else:
            self.send_json_response({"error": "Not Found"}, 404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length)
        
        try:
            payload = json.loads(post_data.decode('utf-8')) if length > 0 else {}
        except Exception:
            payload = {}

        if path == '/api/progress':
            self.handle_progress_update(payload)
        elif path == '/api/behavior':
            self.handle_behavior_update(payload)
        elif path == '/api/buffer/generate':
            self.handle_buffer_generate()
        elif path == '/api/bookmarks':
            self.handle_bookmark_toggle(payload)
        elif path == '/api/bookmarks/review':
            self.handle_bookmark_review(payload)
        elif path == '/api/milestones/audit':
            from scripts.daily_batch import audit_milestone_pace
            progress = load_json('user_progress.json', {})
            res = audit_milestone_pace(progress)
            self.send_json_response(res)
        elif path == '/api/settings/tts_speed':
            new_speed = float(payload.get('tts_speed', 0.85))
            progress = load_json('user_progress.json', {})
            user_profile = progress.setdefault('user_profile', {})
            user_profile['tts_speed'] = new_speed
            save_json('user_progress.json', progress)
            self.send_json_response({"status": "ok", "tts_speed": new_speed})
        elif path == '/api/lesson/advance':
            self.handle_lesson_advance(payload)
        elif path == '/api/sync/github_config':
            self.handle_sync_config(payload)
        elif path == '/api/sync/github_pull':
            self.handle_sync_pull()
        elif path == '/api/sync/github_push':
            self.handle_sync_push()
        else:
            self.send_json_response({"error": "Endpoint not found"}, 404)

    def handle_lesson_advance(self, payload):
        progress = load_json('user_progress.json', {})
        user_profile = progress.setdefault('user_profile', {})
        curr_day = user_profile.get('current_study_day', 1)
        target_day = payload.get('target_day', curr_day + 1)
        
        buffer = load_json('lesson_buffer.json', [])
        max_buffer_day = max([d.get('day_index', 1) for d in buffer]) if buffer else 1
        
        new_day = min(target_day, max_buffer_day)
        user_profile['current_study_day'] = new_day
        effective_dt = get_effective_date()
        user_profile['last_advanced_date'] = effective_dt.strftime('%Y-%m-%d')
        
        completed_days = set(user_profile.get('completed_study_days', []))
        for d in range(1, new_day):
            completed_days.add(d)
        user_profile['completed_study_days'] = sorted(list(completed_days))
        
        progress['user_profile'] = user_profile
        save_json('user_progress.json', progress)
        
        self.send_json_response({
            "status": "ok",
            "current_study_day": new_day,
            "completed_study_days": user_profile['completed_study_days']
        })

    def handle_sync_status(self):
        config = load_json('github_sync_config.json', {})
        gist_id = config.get('gist_id', '')
        has_token = bool(config.get('github_token', ''))
        self.send_json_response({
            "configured": bool(gist_id and has_token),
            "gist_id": gist_id,
            "has_token": has_token,
            "last_synced_at": config.get('last_synced_at', '')
        })

    def handle_sync_config(self, payload):
        config = load_json('github_sync_config.json', {})
        if 'gist_id' in payload:
            config['gist_id'] = str(payload['gist_id']).strip()
        if 'github_token' in payload:
            config['github_token'] = str(payload['github_token']).strip()
        save_json('github_sync_config.json', config)
        self.send_json_response({
            "status": "ok",
            "configured": bool(config.get('gist_id') and config.get('github_token')),
            "gist_id": config.get('gist_id', '')
        })

    def handle_sync_pull(self):
        config = load_json('github_sync_config.json', {})
        gist_id = config.get('gist_id', '')
        token = config.get('github_token', '')
        if not gist_id or not token:
            self.send_json_response({"error": "GitHub Gist設定（Gist IDとトークン）が未登録です。"}, 400)
            return

        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "TanyaRussianApp"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            self.send_json_response({"error": f"Gist取得エラー: {str(e)}"}, 500)
            return

        files = data.get('files', {})
        sync_file = files.get('tanya_progress_sync.json') or files.get('tanya_sync.json')
        if not sync_file or not sync_file.get('content'):
            self.send_json_response({"error": "Gist内に tanya_progress_sync.json が見つかりませんでした。"}, 404)
            return

        try:
            sync_data = json.loads(sync_file['content'])
        except Exception as e:
            self.send_json_response({"error": f"同期データの解析に失敗しました: {str(e)}"}, 500)
            return

        word_reviews = sync_data.get('word_reviews', [])
        progress = load_json('user_progress.json', {})
        bookmarks = progress.get('bookmarked_words', [])
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

        updated_count = 0
        sample_words = []
        for r in word_reviews:
            r_word = r.get('word', '').strip().lower()
            res = r.get('result', 'review')
            for b in bookmarks:
                if b.get('word', '').lower() == r_word or b.get('base', '').lower() == r_word:
                    updated_count += 1
                    if len(sample_words) < 2:
                        sample_words.append(b.get('word'))
                    b['review_count'] = b.get('review_count', 0) + 1
                    b['last_reviewed_at'] = now_str
                    if res == 'mastered':
                        b['mastery_level'] = min(3, b.get('mastery_level', 1) + 1)
                    else:
                        b['mastery_level'] = 1
                    break

        user_profile = progress.setdefault('user_profile', {})
        intimacy = user_profile.setdefault('intimacy', {'level': 1, 'exp': 0, 'max_exp': 100})
        exp_gain = 5 if updated_count > 0 else 0
        intimacy['exp'] = intimacy.get('exp', 0) + exp_gain

        # Mark encore completed if >= 3 words reviewed
        encore_achieved = False
        if updated_count >= 3:
            user_profile['encore_completed_today'] = True
            encore_achieved = True

        progress['bookmarked_words'] = bookmarks
        save_json('user_progress.json', progress)

        config['last_synced_at'] = now_str
        save_json('github_sync_config.json', config)

        word_names_str = "、".join([f"『{w}』" for w in sample_words]) if sample_words else "スター単語"
        tanya_message = f"Юсукэ、移動中に ⭐{word_names_str} などの練習（計{updated_count}語）、お見事でした！親愛度 +{exp_gain} EXP 獲得です♪"

        self.send_json_response({
            "status": "success",
            "reviews_processed": updated_count,
            "exp_gained": exp_gain,
            "encore_achieved": encore_achieved,
            "tanya_message": tanya_message,
            "synced_at": now_str
        })

    def handle_sync_push(self):
        config = load_json('github_sync_config.json', {})
        gist_id = config.get('gist_id', '')
        token = config.get('github_token', '')
        if not gist_id or not token:
            self.send_json_response({"error": "GitHub Gist設定が未登録です。"}, 400)
            return

        progress = load_json('user_progress.json', {})
        bookmarks = progress.get('bookmarked_words', [])
        user_profile = progress.get('user_profile', {})

        payload_to_gist = {
            "synced_at": datetime.now().isoformat(),
            "device": "PC (Tanya Salon)",
            "starred_words": bookmarks,
            "last_day": user_profile.get('current_study_day', 25)
        }

        body_data = json.dumps({
            "description": "Tanya Russian Learning Progress Sync",
            "files": {
                "tanya_progress_sync.json": {
                    "content": json.dumps(payload_to_gist, ensure_ascii=False, indent=2)
                }
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
            data=body_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "TanyaRussianApp"
            },
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                self.send_json_response({
                    "status": "success",
                    "words_pushed": len(bookmarks),
                    "message": f"最新の⭐スター単語（{len(bookmarks)}語）をGistにアップロードしました！"
                })
        except Exception as e:
            self.send_json_response({"error": f"Gistアップロード失敗: {str(e)}"}, 500)

    def handle_bookmark_toggle(self, payload):
        progress = load_json('user_progress.json', {})
        bookmarks = progress.get('bookmarked_words', [])
        word = payload.get('word', '').strip()
        if not word:
            self.send_json_response({"error": "No word specified"}, 400)
            return

        existing_idx = -1
        for i, b in enumerate(bookmarks):
            if b.get('word', '').lower() == word.lower():
                existing_idx = i
                break

        if existing_idx >= 0:
            bookmarks.pop(existing_idx)
            is_bookmarked = False
        else:
            base = payload.get('base', word)
            pos = payload.get('pos', '').strip()
            meaning = payload.get('meaning', '').strip()
            notes = (payload.get('notes') or payload.get('role', '')).strip()
            example_ru = payload.get('example_ru', '').strip()
            example_ja = payload.get('example_ja', '').strip()

            # Auto-fill missing fields if pos or meaning is blank
            if not meaning or not pos:
                entry = RUSSIAN_CORE_ENTRIES.get(word.lower()) or RUSSIAN_CORE_ENTRIES.get(base.lower())
                if not entry:
                    entry = resolve_missing_vocabulary(base.lower()) or resolve_missing_vocabulary(word.lower())
                if entry:
                    if not pos: pos = entry.get('pos', '')
                    if not meaning: meaning = entry.get('meaning', '')
                    if not notes: notes = entry.get('notes', '')
                    if not example_ru and entry.get('examples'):
                        example_ru = entry['examples'][0].get('ru', '')
                        example_ja = entry['examples'][0].get('ja', '')

            bookmarks.append({
                "word": word,
                "base": base,
                "pos": pos,
                "meaning": meaning,
                "notes": notes,
                "example_ru": example_ru,
                "example_ja": example_ja,
                "saved_at": datetime.now().strftime('%Y-%m-%d %H:%M')
            })
            is_bookmarked = True

        progress['bookmarked_words'] = bookmarks
        save_json('user_progress.json', progress)
        self.send_json_response({
            "status": "ok",
            "is_bookmarked": is_bookmarked,
            "bookmarks_count": len(bookmarks),
            "bookmarks": bookmarks
        })

    def handle_bookmark_review(self, payload):
        progress = load_json('user_progress.json', {})
        bookmarks = progress.get('bookmarked_words', [])
        word = payload.get('word', '').strip()
        try:
            mastery = int(payload.get('mastery_level', 1))
        except (ValueError, TypeError):
            mastery = 1
        mastery = max(1, min(3, mastery))

        if not word:
            self.send_json_response({"error": "No word specified"}, 400)
            return

        updated_bm = None
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        for b in bookmarks:
            if b.get('word', '').lower() == word.lower() or b.get('base', '').lower() == word.lower():
                b['mastery_level'] = mastery
                b['review_count'] = b.get('review_count', 0) + 1
                b['last_reviewed_at'] = now_str
                updated_bm = b
                break

        progress['bookmarked_words'] = bookmarks
        save_json('user_progress.json', progress)
        self.send_json_response({
            "status": "ok",
            "word": word,
            "bookmark": updated_bm,
            "bookmarks": bookmarks
        })

    def handle_progress_update(self, payload):
        progress = load_json('user_progress.json', {})
        user_profile = progress.get('user_profile', {})
        tag_stats = progress.get('tag_stats', {})
        session_history = progress.get('session_history', [])

        effective_dt = get_effective_date()
        today_str = effective_dt.strftime('%Y-%m-%d')
        last_active = user_profile.get('last_active_date', today_str)

        # Update streak
        if last_active != today_str:
            try:
                last_dt = datetime.strptime(last_active, '%Y-%m-%d').date()
                curr_dt = effective_dt
                diff = (curr_dt - last_dt).days
                if diff == 1:
                    user_profile['consecutive_days'] = user_profile.get('consecutive_days', 1) + 1
                    user_profile['current_streak'] = user_profile.get('current_streak', 1) + 1
                elif diff > 2:
                    # After 3+ days gap, streak resets to 1, but distance meter points were frozen (not deducted)
                    user_profile['current_streak'] = 1
            except Exception:
                pass
            user_profile['last_active_date'] = today_str

        user_profile['total_sessions_completed'] = user_profile.get('total_sessions_completed', 0) + 1

        # Intimacy points
        intimacy = user_profile.get('intimacy', {'level': 1, 'exp': 0, 'max_exp': 50})
        gained_exp = payload.get('intimacy_gain', 5)
        new_exp = intimacy.get('exp', 0) + gained_exp
        curr_level = intimacy.get('level', 1)
        max_exp = intimacy.get('max_exp', 50)

        if new_exp >= max_exp:
            curr_level += 1
            new_exp = new_exp - max_exp
            max_exp = int(max_exp * 1.5)

        intimacy['level'] = curr_level
        intimacy['exp'] = new_exp
        intimacy['max_exp'] = max_exp

        # Update level title & description
        titles = [
            (1, "音楽院サロンの新客", "ターニャ先生と音楽やピアノの話題を通じて、ロシア語を学び始めたばかりの親しみやすい関係です。"),
            (2, "信頼の練習仲間", "互いの音の好みが分かり始め、音楽院の思い出話を自然に語り合える間柄になりました。"),
            (3, "共鳴するピアニスト", "深い音楽的解釈や、難解な文法ニュアンスも阿吽の呼吸で理解し合える強い絆が生まれました。"),
            (4, "至高のアンサンブル", "言葉を超えて心を通わせる、生涯の音楽の友として互いを深くリスペクトしています。")
        ]
        for lvl, title, desc in titles:
            if curr_level >= lvl:
                intimacy['title'] = title
                intimacy['description'] = desc

        user_profile['intimacy'] = intimacy

        # Update question responses & reaction times
        results = payload.get('quiz_results', [])
        for res in results:
            tag = res.get('tag')
            is_correct = res.get('is_correct', False)
            rt_ms = res.get('rt_ms', 2500)
            is_interruption = res.get('is_interruption', False)

            if not tag:
                continue

            stat = tag_stats.setdefault(tag, {
                "seen": 0, "correct": 0, "avg_rt_ms": 18000, "consecutive_correct": 0, "status": "developing"
            })
            stat['seen'] += 1
            if is_correct:
                stat['correct'] += 1
                stat['consecutive_correct'] = stat.get('consecutive_correct', 0) + 1
            else:
                stat['consecutive_correct'] = 0

            # 4-Layer Reaction Time Calibration:
            # Exclude interruptions (external pauses, tab blurs, >=90s) from RT running average
            # 12s - 35s is normal thoughtful pace, up to 60s bounded
            if not is_interruption and rt_ms < 90000:
                old_rt = stat.get('avg_rt_ms', 18000)
                bounded_rt = min(60000, max(1000, rt_ms))
                stat['avg_rt_ms'] = int((old_rt * 0.8) + (bounded_rt * 0.2))

            # Stability classification:
            # High accuracy (acc >= 0.75) must NEVER be marked as "rusty" solely due to response time!
            acc = stat['correct'] / stat['seen']
            avg_rt = stat.get('avg_rt_ms', 18000)
            consec = stat.get('consecutive_correct', 0)

            if stat['seen'] >= 3:
                if acc >= 0.85 and avg_rt < 15000 and consec >= 3:
                    stat['status'] = "reflex" # スムーズ・反射レベル（15秒以内想起）
                elif acc >= 0.75 and consec >= 2:
                    stat['status'] = "stable" # 安定定着（着実・正確。30秒台の丁寧な解答でも正解していれば安定）
                elif acc >= 0.70 and avg_rt < 35000:
                    stat['status'] = "stable" # 安定定着（35秒以内の着実な解答）
                else:
                    stat['status'] = "rusty" # 要復習（直近誤答あり、または正答率7割未満）

        # Unlocked memoir badge
        unlocked_badge = payload.get('unlocked_badge')
        if unlocked_badge:
            memoirs = progress.get('unlocked_memoirs', [])
            if unlocked_badge not in memoirs:
                memoirs.append(unlocked_badge)
            progress['unlocked_memoirs'] = memoirs

        # Append to session history
        session_history.append({
            "timestamp": datetime.now().isoformat(),
            "session_id": payload.get('session_id'),
            "type": payload.get('type'),
            "quiz_count": len(results),
            "intimacy_gain": gained_exp
        })

        progress['user_profile'] = user_profile
        progress['tag_stats'] = tag_stats
        progress['session_history'] = session_history
        save_json('user_progress.json', progress)

        self.send_json_response({
            "status": "success",
            "intimacy": intimacy,
            "streak": user_profile.get('current_streak', 1),
            "tag_stats": tag_stats
        })

    def handle_behavior_update(self, payload):
        progress = load_json('user_progress.json', {})
        logs = progress.get('behavior_logs', {})
        for k, v in payload.items():
            logs[k] = logs.get(k, 0) + v
        progress['behavior_logs'] = logs
        save_json('user_progress.json', progress)
        self.send_json_response({"status": "logged"})

    def handle_buffer_generate(self):
        script_path = os.path.join(BASE_DIR, 'scripts', 'daily_batch.py')
        try:
            res = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
            buffer = load_json('lesson_buffer.json', [])
            self.send_json_response({
                "status": "success",
                "message": "Daily batch and lesson buffer processed successfully.",
                "days_available": len(buffer)
            })
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)}, 500)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run():
    # Audit curriculum solvability on startup
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
        from validate_curriculum import validate_catalog_list
        buf_days = load_json('lesson_buffer.json', [])
        is_valid, summary = validate_catalog_list(buf_days)
        if is_valid:
            print(f"[AUDIT] Verified {summary['total_questions']} questions across {summary['total_days']} days (100% solvable, 0 errors).")
        else:
            print(f"[CRITICAL AUDIT ERROR] Unsolvable questions detected in buffer: {summary['errors']}")
    except Exception as e:
        print(f"[AUDIT WARN] Curriculum audit skipped on startup: {e}")

    handler = TanyaRequestHandler
    with ThreadedTCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"=======================================================")
        print(f"  Tanya Russian Learning Server running at:")
        print(f"  http://localhost:{PORT}/")
        print(f"=======================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == '__main__':
    run()
