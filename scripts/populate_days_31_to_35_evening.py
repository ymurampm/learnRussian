import json
import os
import re

EVENING_PARAGRAPHS_31_35 = {
    31: [
        {
            "ru": "Эта редкая запись была сделана в Большом зале консерватории много лет назад. Звук рояля звучит чисто и тепло.",
            "ja": "この貴重な録音は何年も前に音楽院の大ホールで行われました。ピアノの音色は清らかで暖かく響いています。",
            "related_tag": "participle.passive",
            "tokens": [
                {"word": "Эта", "base": "этот", "role": "指示代名詞（この / 女性主格）", "tag": "adj.declension", "grammar": "女性主格"},
                {"word": "редкая", "base": "редкий", "role": "形容詞（貴重な、珍しい / 女性主格）", "tag": "adj.declension", "grammar": "女性主格"},
                {"word": "запись", "base": "запись", "role": "名詞（録音・記録は / 女性主格）", "tag": "noun.soft_sign", "grammar": "女性主格"},
                {"word": "была", "base": "быть", "role": "動詞（〜であった / 過去女性）", "tag": "verb.irregular", "grammar": "過去・女性単数"},
                {"word": "сделана", "base": "сделать", "role": "受動過去形動詞・短語尾（行われた、作られた / 女性単数）", "tag": "participle.passive", "grammar": "短語尾受動形動詞・女性単数"},
                {"word": "в", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "Большом", "base": "большой", "role": "形容詞（大〜 / 男性前置格）", "tag": "adj.declension", "grammar": "男性前置格"},
                {"word": "зале", "base": "зал", "role": "名詞（ホールで / 男性前置格）", "tag": "case.prp", "grammar": "男性前置格"},
                {"word": "консерватории", "base": "консерватория", "role": "名詞（音楽院の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "много", "base": "много", "role": "数副詞（何年も / 生格支配）", "tag": "adj.declension", "grammar": "数副詞"},
                {"word": "лет", "base": "год", "role": "名詞（年 / 複数生格）", "tag": "case.gen", "grammar": "複数生格"},
                {"word": "назад", "base": "назад", "role": "副詞（前に）", "tag": "adj.declension", "grammar": "副詞"},
                {"word": "Звук", "base": "звук", "role": "名詞（音色は / 男性主格）", "tag": "case.nom", "grammar": "男性主格"},
                {"word": "рояля", "base": "рояль", "role": "名詞（ピアノの / 男性生格）", "tag": "noun.soft_sign", "grammar": "男性生格"},
                {"word": "звучит", "base": "звучать", "role": "動詞（響いている / 現在3人称単数）", "tag": "verb.aspect_nsv", "grammar": "現在3人称単数"},
                {"word": "чисто", "base": "чисто", "role": "副詞（清らかに）", "tag": "adj.declension", "grammar": "副詞"},
                {"word": "и", "base": "и", "role": "接続詞（そして）", "tag": "syntax.subordinate", "grammar": "等位接続詞"},
                {"word": "тепло", "base": "тепло", "role": "副詞（暖かく）", "tag": "adj.declension", "grammar": "副詞"}
            ],
            "key_vocab": [
                {"word": "сделать", "base": "сделать", "pos": "完了体動詞", "meaning": "行う、作る", "role_in_sentence": "受動過去短語尾（была сделана）"},
                {"word": "запись", "base": "запись", "pos": "女性名詞", "meaning": "録音、記録", "role_in_sentence": "主語（女性主格 запись）"},
                {"word": "рояль", "base": "рояль", "pos": "男性名詞", "meaning": "グランドピアノ", "role_in_sentence": "所有を表す生格（звук рояля）"},
                {"word": "звучать", "base": "звучать", "pos": "不完了体動詞", "meaning": "響く、音を立てる", "role_in_sentence": "述語動詞（звучит）"}
            ],
            "grammar_points": [
                "【受動過去形動詞の短語尾: была сделана】主語 запись（女性単数）に合わせて過去助動詞 была と短語尾 сделана が女性単数に一致しています。",
                "【期間を表す много лет назад】数副詞 много に名詞 год の不規則複数生格 лет が続き、「何年も前に」を表します。"
            ],
            "tanya_note": "大ホールの響きを収めた歴史的録音には、ホールの空間そのものの温もりが刻まれています。"
        },
        {
            "ru": "Каждая фраза исполнена с глубоким чувством, напоминая нам о великих традициях русской фортепианной школы.",
            "ja": "すべてのフレーズが深い情感を込めて演奏され、ロシア・ピアノ楽派の偉大な伝統を私たちに思い出させてくれます。",
            "related_tag": "participle.passive",
            "tokens": [
                {"word": "Каждая", "base": "каждый", "role": "形容詞（それぞれの、すべての / 女性主格）", "tag": "adj.declension", "grammar": "女性主格"},
                {"word": "фраза", "base": "фраза", "role": "名詞（フレーズが / 女性主格）", "tag": "case.nom", "grammar": "女性主格"},
                {"word": "исполнена", "base": "исполнить", "role": "受動過去形動詞・短語尾（演奏され / 女性単数）", "tag": "participle.passive", "grammar": "短語尾受動形動詞・女性単数"},
                {"word": "с", "base": "с", "role": "前置詞（〜を込めて / 造格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "глубоким", "base": "глубокий", "role": "形容詞（深い / 中性造格）", "tag": "adj.declension", "grammar": "中性造格"},
                {"word": "чувством", "base": "чувство", "role": "名詞（感情・情感で / 中性造格）", "tag": "case.ins", "grammar": "中性造格"},
                {"word": "напоминая", "base": "напоминать", "role": "不完了体副動詞（思い出させながら）", "tag": "gerund.imperfective", "grammar": "不完了体副動詞"},
                {"word": "нам", "base": "мы", "role": "代名詞（私たちに / 1人称複数与格）", "tag": "case.dat", "grammar": "1人称複数与格"},
                {"word": "о", "base": "о", "role": "前置詞（〜について / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "великих", "base": "великий", "role": "形容詞（偉大な / 複数前置格）", "tag": "adj.declension", "grammar": "複数前置格"},
                {"word": "традициях", "base": "традиция", "role": "名詞（伝統について / 複数前置格）", "tag": "case.prp", "grammar": "複数前置格"},
                {"word": "русской", "base": "русский", "role": "形容詞（ロシアの / 女性生格）", "tag": "adj.declension", "grammar": "女性生格"},
                {"word": "фортепианной", "base": "фортепианный", "role": "形容詞（ピアノの / 女性生格）", "tag": "adj.declension", "grammar": "女性生格"},
                {"word": "школы", "base": "школа", "role": "名詞（流派・楽派の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"}
            ],
            "key_vocab": [
                {"word": "исполнить", "base": "исполнить", "pos": "完了体動詞", "meaning": "演奏する、上演する", "role_in_sentence": "受動過去短語尾（исполнена）"},
                {"word": "фраза", "base": "фраза", "pos": "女性名詞", "meaning": "フレーズ、楽句", "role_in_sentence": "主語（女性主格 фраза）"},
                {"word": "чувство", "base": "чувство", "pos": "中性名詞", "meaning": "感情、情感", "role_in_sentence": "様態を表す造格（с глубоким чувством）"},
                {"word": "напоминать", "base": "напоминать", "pos": "不完了体動詞", "meaning": "思い出させる (+ d + о + pr)", "role_in_sentence": "副動詞（напоминая нам о традициях）"}
            ],
            "grammar_points": [
                "【受動過去短語尾 исполнена】動詞 исполнить（演奏する）の短語尾形で、述語として現在の一致状態を表します。",
                "【結合価 напоминать кому о чём】「人に〜について思い出させる」を表す結合価パターンです。"
            ],
            "tanya_note": "チャイコフスキーやラフマニノフへと連なるロシア・ピアニズムの真髄は、歌うような音色（певучий звук）にあります。"
        }
    ],

    32: [
        {
            "ru": "Дирижёр руководил оркестром с огромной энергией. Музыка требовала полной отдачи от каждого скрипача и пианиста.",
            "ja": "指揮者は途方もないエネルギーでオーケストラを統率していました。音楽はすべてのバイオリニストとピアニストに全霊の献身を要求していました。",
            "related_tag": "verb.government",
            "tokens": [
                {"word": "Дирижёр", "base": "дирижёр", "role": "名詞（指揮者は / 男性主格）", "tag": "case.nom", "grammar": "男性主格"},
                {"word": "руководил", "base": "руководить", "role": "動詞（統率していた、指導していた / 過去男性）", "tag": "verb.government", "grammar": "過去・男性単数"},
                {"word": "оркестром", "base": "оркестр", "role": "名詞（オーケストラを / 男性造格）", "tag": "case.ins", "grammar": "男性造格"},
                {"word": "с", "base": "с", "role": "前置詞（〜をもって / 造格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "огромной", "base": "огромный", "role": "形容詞（途方もない / 女性造格）", "tag": "adj.declension", "grammar": "女性造格"},
                {"word": "энергией", "base": "энергия", "role": "名詞（エネルギーで / 女性造格）", "tag": "case.ins", "grammar": "女性造格"},
                {"word": "Музыка", "base": "музыка", "role": "名詞（音楽は / 女性主格）", "tag": "case.nom", "grammar": "女性主格"},
                {"word": "требовала", "base": "требовать", "role": "動詞（要求していた / 過去女性）", "tag": "verb.government", "grammar": "過去・女性単数"},
                {"word": "полной", "base": "полный", "role": "形容詞（完全な / 女性生格）", "tag": "adj.declension", "grammar": "女性生格"},
                {"word": "отдачи", "base": "отдача", "role": "名詞（献身を / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "от", "base": "от", "role": "前置詞（〜から / 生格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "каждого", "base": "каждый", "role": "形容詞（それぞれの / 男性生格）", "tag": "adj.declension", "grammar": "男性生格"},
                {"word": "скрипача", "base": "скрипач", "role": "名詞（ヴァイオリニストから / 男性生格）", "tag": "case.gen", "grammar": "男性生格"},
                {"word": "и", "base": "и", "role": "接続詞（そして）", "tag": "syntax.subordinate", "grammar": "等位接続詞"},
                {"word": "пианиста", "base": "пианист", "role": "名詞（ピアニストから / 男性生格）", "tag": "case.gen", "grammar": "男性生格"}
            ],
            "key_vocab": [
                {"word": "руководить", "base": "руководить", "pos": "不完了体動詞", "meaning": "指導する、統率する (+ inst 造格支配)", "role_in_sentence": "述語動詞（руководил оркестром）"},
                {"word": "оркестр", "base": "оркестр", "pos": "男性名詞", "meaning": "オーケストラ、管弦楽団", "role_in_sentence": "動詞の造格支配（оркестром）"},
                {"word": "требовать", "base": "требовать", "pos": "不完了体動詞", "meaning": "要求する (+ gen 生格支配)", "role_in_sentence": "述語動詞（требовала полной отдачи）"},
                {"word": "отдача", "base": "отдача", "pos": "女性名詞", "meaning": "全霊の献身、打ち込み", "role_in_sentence": "動詞の生格支配（отдачи）"}
            ],
            "grammar_points": [
                "【動詞 руководить の造格支配】「〜を指導・指揮する」を表す руководить は直接目的語に対格ではなく「造格（оркестром）」をとります。",
                "【動詞 требовать の生格支配】抽象的な対象を要求する場合、動詞 требовать は「生格（полной отдачи）」を支配します。"
            ],
            "tanya_note": "指揮棒の一振りからほとばしるエネルギーに、百人を超える奏者の呼吸が一つに束ねられます。"
        },
        {
            "ru": "Они вместе овладевали сложнейшим материалом симфонии, приближаясь к совершенству.",
            "ja": "彼らは共に交響曲の至難な素材を克服し、完璧な高みへと近づいていました。",
            "related_tag": "verb.government",
            "tokens": [
                {"word": "Они", "base": "они", "role": "代名詞（彼らは / 複数主格）", "tag": "case.nom", "grammar": "3人称複数主格"},
                {"word": "вместе", "base": "вместе", "role": "副詞（一緒に、共に）", "tag": "adj.declension", "grammar": "副詞"},
                {"word": "овладевали", "base": "овладевать", "role": "動詞（克服していた、習得していた / 過去複数）", "tag": "verb.government", "grammar": "過去・複数"},
                {"word": "сложнейшим", "base": "сложный", "role": "最高級形容詞（至難な、極めて複雑な / 男性造格）", "tag": "adj.declension", "grammar": "男性造格"},
                {"word": "материалом", "base": "материал", "role": "名詞（素材・楽想を / 男性造格）", "tag": "case.ins", "grammar": "男性造格"},
                {"word": "симфонии", "base": "симфония", "role": "名詞（交響曲の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "приближаясь", "base": "приближаться", "role": "不完了体副動詞（近づきながら）", "tag": "gerund.imperfective", "grammar": "不完了体副動詞"},
                {"word": "к", "base": "к", "role": "前置詞（〜へ / 与格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "совершенству", "base": "совершенство", "role": "名詞（完璧・完成の域へ / 中性与格）", "tag": "case.dat", "grammar": "中性与格"}
            ],
            "key_vocab": [
                {"word": "овладевать", "base": "овладевать", "pos": "不完了体動詞", "meaning": "習得する、克服する (+ inst 造格支配)", "role_in_sentence": "述語動詞（овладевали материалом）"},
                {"word": "симфония", "base": "симфония", "pos": "女性名詞", "meaning": "交響曲、シンフォニー", "role_in_sentence": "所有を表す生格（симфонии）"},
                {"word": "приближаться", "base": "приближаться", "pos": "不完了体動詞", "meaning": "近づく (+ к + dat)", "role_in_sentence": "副動詞（приближаясь к совершенству）"},
                {"word": "совершенство", "base": "совершенство", "pos": "中性名詞", "meaning": "完璧、完成、至高", "role_in_sentence": "方向を表す与格（к совершенству）"}
            ],
            "grammar_points": [
                "【動詞 овладевать の造格支配】「（技術・知識などを）身につける・克服する」を表す овладевать は「造格（материалом）」を支配します。",
                "【最高級接尾辞 -ейш-】сложнейший は「極めて難しい」という絶対最高級を表します。"
            ],
            "tanya_note": "難曲に立ち向かうオーケストラの熱気は、演奏者一人ひとりの誇りと献身によって支えられています。"
        }
    ],

    33: [
        {
            "ru": "В уютном классе было тепло и спокойно. Нам не хотелось никуда спешить в этот тихий зимний вечер.",
            "ja": "心地よい教室は暖かく静かでした。この穏やかな冬の夕暮れ、私たちはどこへも急ぎたくありませんでした。",
            "related_tag": "syntax.impersonal",
            "tokens": [
                {"word": "В", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "уютном", "base": "уютный", "role": "形容詞（心地よい / 男性前置格）", "tag": "adj.declension", "grammar": "男性前置格"},
                {"word": "классе", "base": "класс", "role": "名詞（教室で / 男性前置格）", "tag": "case.prp", "grammar": "男性前置格"},
                {"word": "было", "base": "быть", "role": "動詞（〜であった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "無人称過去"},
                {"word": "тепло", "base": "тепло", "role": "述語副詞（暖かく）", "tag": "syntax.impersonal", "grammar": "状態述語詞"},
                {"word": "и", "base": "и", "role": "接続詞（そして）", "tag": "syntax.subordinate", "grammar": "等位接続詞"},
                {"word": "спокойно", "base": "спокойно", "role": "述語副詞（穏やかで）", "tag": "syntax.impersonal", "grammar": "状態述語詞"},
                {"word": "Нам", "base": "мы", "role": "代名詞（私たちには / 1人称複数与格）", "tag": "case.dat", "grammar": "与格主語"},
                {"word": "не", "base": "не", "role": "否定小詞（〜ない）", "tag": "pronoun.negative", "grammar": "否定小詞"},
                {"word": "хотелось", "base": "хотеться", "role": "動詞（〜したくなかった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "無人称過去"},
                {"word": "никуда", "base": "никуда", "role": "負の副詞（どこへも）", "tag": "pronoun.negative", "grammar": "否定副詞"},
                {"word": "спешить", "base": "спешить", "role": "動詞（急ぐ / 不定形）", "tag": "verb.aspect_nsv", "grammar": "動詞不定形"},
                {"word": "в", "base": "в", "role": "前置詞（〜に / 対格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "этот", "base": "этот", "role": "指示代名詞（この / 男性対格）", "tag": "adj.declension", "grammar": "男性対格"},
                {"word": "тихий", "base": "тихий", "role": "形容詞（静かな / 男性対格）", "tag": "adj.declension", "grammar": "男性対格"},
                {"word": "зимний", "base": "зимний", "role": "形容詞（冬の / 男性対格）", "tag": "adj.declension", "grammar": "男性対格"},
                {"word": "вечер", "base": "вечер", "role": "名詞（夜に / 男性対格）", "tag": "case.acc", "grammar": "男性対格"}
            ],
            "key_vocab": [
                {"word": "хотеться", "base": "хотеться", "pos": "不完了体動詞", "meaning": "〜したい気分である (+ dat 与格無人称)", "role_in_sentence": "無人称述語（не хотелось）"},
                {"word": "никуда", "base": "никуда", "pos": "否定副詞", "meaning": "どこへも〜ない", "role_in_sentence": "方向を表す否定副詞"},
                {"word": "спешить", "base": "спешить", "pos": "不完了体動詞", "meaning": "急ぐ", "role_in_sentence": "動詞不定形（спешить）"},
                {"word": "спокойно", "base": "спокойно", "pos": "述語副詞", "meaning": "穏やかだ、平穏だ", "role_in_sentence": "環境を表す述語詞"}
            ],
            "grammar_points": [
                "【無人称構文 кому не хотелось】体験者を「与格（Нам）」で表し、動詞は常に中性単数（было, хотелось）で受ける無人称表現です。",
                "【二重否定の呼応: не ... никуда】ロシア語では否定辞 не と否定副詞 никуда（どこへも）が呼応して完全な否定を作ります。"
            ],
            "tanya_note": "冬のモスクワの夕暮れ、暖かいレッスン室でピアノに向かっていると、外の寒さも心地よい静寂に変わります。"
        },
        {
            "ru": "Казалось, что время остановилось, позволяя нам насладиться каждым мгновением музыки.",
            "ja": "まるで時間が止まり、音楽のひとときひとときを私たちが心ゆくまで味わうのを許してくれているかのようでした。",
            "related_tag": "syntax.impersonal",
            "tokens": [
                {"word": "Казалось", "base": "казаться", "role": "動詞（思われた、〜のようだった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "挿入的無人称動詞"},
                {"word": "что", "base": "что", "role": "接続詞（〜ということ）", "tag": "syntax.subordinate", "grammar": "従属接続詞"},
                {"word": "время", "base": "время", "role": "名詞（時間が / 中性主格）", "tag": "noun.irregular_fleeting", "grammar": "中性主格"},
                {"word": "остановилось", "base": "остановиться", "role": "動詞（止まった / 過去中性）", "tag": "verb.aspect_nsv", "grammar": "完了体過去・中性単数"},
                {"word": "позволяя", "base": "позволять", "role": "不完了体副動詞（許しながら、可能にしつつ）", "tag": "gerund.imperfective", "grammar": "不完了体副動詞"},
                {"word": "нам", "base": "мы", "role": "代名詞（私たちに / 1人称複数与格）", "tag": "case.dat", "grammar": "1人称複数与格"},
                {"word": "насладиться", "base": "насладиться", "role": "動詞（堪能する、味わう / 不定形）", "tag": "verb.government", "grammar": "完了体不定形"},
                {"word": "каждым", "base": "каждый", "role": "形容詞（それぞれの、あらゆる / 中性造格）", "tag": "adj.declension", "grammar": "中性造格"},
                {"word": "мгновением", "base": "мгновение", "role": "名詞（瞬間に、ひとときに / 中性造格）", "tag": "case.ins", "grammar": "中性造格"},
                {"word": "музыки", "base": "музыка", "role": "名詞（音楽の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"}
            ],
            "key_vocab": [
                {"word": "казаться", "base": "казаться", "pos": "不完了体動詞", "meaning": "思われる、〜のように見える", "role_in_sentence": "親文の主述（Казалось）"},
                {"word": "остановиться", "base": "остановиться", "pos": "完了体動詞", "meaning": "止まる、停止する", "role_in_sentence": "従属節の述語（остановилось）"},
                {"word": "позволять", "base": "позволять", "pos": "不完了体動詞", "meaning": "許す、可能にする", "role_in_sentence": "副動詞（позволяя нам）"},
                {"word": "насладиться", "base": "насладиться", "pos": "完了体動詞", "meaning": "堪能する、満喫する (+ inst 造格支配)", "role_in_sentence": "動詞不定形（насладиться мгновением）"}
            ],
            "grammar_points": [
                "【無人称動詞 Казалось, что...】主語を持たず中性単数形 казалось で「〜のように思われた」という状況の印象を述べます。",
                "【動詞 насладиться の造格支配】「〜を満喫する・心ゆくまで味わう」を表す насладиться は「造格（мгновением）」を支配します。"
            ],
            "tanya_note": "音楽に深く没頭すると、時計の針の進みすら忘れ去られる至福の時間が訪れます。"
        }
    ],

    34: [
        {
            "ru": "В полночь в коридорах консерватории никого не было. Только из дальнего класса доносились тихие звуки рояля.",
            "ja": "真夜中の音楽院の廊下には誰もいませんでした。ただ奥の教室からだけ、静かなピアノの音が聞こえていました。",
            "related_tag": "pronoun.negative",
            "tokens": [
                {"word": "В", "base": "в", "role": "前置詞（〜に / 対格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "полночь", "base": "полночь", "role": "名詞（真夜中に / 女性対格）", "tag": "noun.soft_sign", "grammar": "女性対格"},
                {"word": "в", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "коридорах", "base": "коридор", "role": "名詞（廊下に / 複数前置格）", "tag": "case.prp", "grammar": "複数前置格"},
                {"word": "консерватории", "base": "консерватория", "role": "名詞（音楽院の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "никого", "base": "никто", "role": "負代名詞（誰も / 生格）", "tag": "pronoun.negative", "grammar": "否定生格"},
                {"word": "не", "base": "не", "role": "否定小詞（〜ない）", "tag": "pronoun.negative", "grammar": "否定小詞"},
                {"word": "было", "base": "быть", "role": "動詞（いなかった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "無人称否定過去"},
                {"word": "Только", "base": "только", "role": "限定小詞（ただ〜だけ）", "tag": "adj.declension", "grammar": "小詞"},
                {"word": "из", "base": "из", "role": "前置詞（〜から / 生格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "дальнего", "base": "дальний", "role": "形容詞（奥の、遠い / 男性生格）", "tag": "adj.declension", "grammar": "男性生格"},
                {"word": "класса", "base": "класс", "role": "名詞（教室から / 男性生格）", "tag": "case.gen", "grammar": "男性生格"},
                {"word": "доносились", "base": "доноситься", "role": "動詞（聞こえていた、漂っていた / 過去複数）", "tag": "verb.aspect_nsv", "grammar": "不完了体過去・複数"},
                {"word": "тихие", "base": "тихий", "role": "形容詞（静かな / 複数主格）", "tag": "adj.declension", "grammar": "複数主格"},
                {"word": "звуки", "base": "звук", "role": "名詞（音が / 複数主格）", "tag": "case.nom", "grammar": "複数主格"},
                {"word": "рояля", "base": "рояль", "role": "名詞（ピアノの / 男性生格）", "tag": "noun.soft_sign", "grammar": "男性生格"}
            ],
            "key_vocab": [
                {"word": "никто", "base": "никто", "pos": "否定代名詞", "meaning": "誰も〜ない", "role_in_sentence": "否定存在の生格（никого не было）"},
                {"word": "полночь", "base": "полночь", "pos": "女性名詞", "meaning": "真夜中", "role_in_sentence": "時間を表す対格（в полночь）"},
                {"word": "доноситься", "base": "доноситься", "pos": "不完了体動詞", "meaning": "（音が）聞こえてくる、漂ってくる", "role_in_sentence": "述語動詞（доносились звуки）"},
                {"word": "дальний", "base": "дальний", "pos": "形容詞", "meaning": "奥の、遠方の", "role_in_sentence": "起点の前置詞 из の生格（из дальнего класса）"}
            ],
            "grammar_points": [
                "【否定存在の構文: никого не было】「誰もいなかった」を表す場合、否定生格 никого と過去中性単数 было を用います。",
                "【第3変化名詞 полночь の対格】不活動体女性名詞 полночь は主格と同形で対格（в полночь）をとります。"
            ],
            "tanya_note": "真夜中の音楽院の奥から聴こえてくるピアノの音。誰もいない廊下に響くその音色には、特別な神聖さが宿っています。"
        },
        {
            "ru": "Пианисту некуда было спешить, и он играл для себя, растворяясь в совершенной тишине.",
            "ja": "ピアニストには急ぐべき場所もなく、完璧な静寂の中に溶け込みながら、ただ自分のためにピアノを弾いていました。",
            "related_tag": "pronoun.negative",
            "tokens": [
                {"word": "Пианисту", "base": "пианист", "role": "名詞（ピアニストには / 男性与格）", "tag": "case.dat", "grammar": "与格主語"},
                {"word": "некуда", "base": "некуда", "role": "否定詞（行くべき場所がない）", "tag": "pronoun.negative", "grammar": "否定副詞"},
                {"word": "было", "base": "быть", "role": "動詞（〜であった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "無人称過去"},
                {"word": "спешить", "base": "спешить", "role": "動詞（急ぐ / 不定形）", "tag": "verb.aspect_nsv", "grammar": "動詞不定形"},
                {"word": "и", "base": "и", "role": "接続詞（そして）", "tag": "syntax.subordinate", "grammar": "等位接続詞"},
                {"word": "он", "base": "он", "role": "代名詞（彼は / 男性主格）", "tag": "case.nom", "grammar": "3人称男性主格"},
                {"word": "играл", "base": "играть", "role": "動詞（弾いていた / 過去男性）", "tag": "verb.aspect_nsv", "grammar": "不完了体過去・男性単数"},
                {"word": "для", "base": "для", "role": "前置詞（〜のために / 生格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "себя", "base": "себя", "role": "再帰代名詞（自分自身のために / 生格）", "tag": "case.gen", "grammar": "再帰代名詞生格"},
                {"word": "растворяясь", "base": "растворяться", "role": "不完了体副動詞（溶け込みながら）", "tag": "gerund.imperfective", "grammar": "不完了体副動詞"},
                {"word": "в", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "совершенной", "base": "совершенный", "role": "形容詞（完璧な / 女性前置格）", "tag": "adj.declension", "grammar": "女性前置格"},
                {"word": "тишине", "base": "тишина", "role": "名詞（静寂の中に / 女性前置格）", "tag": "case.prp", "grammar": "女性前置格"}
            ],
            "key_vocab": [
                {"word": "некуда", "base": "некуда", "pos": "否定詞", "meaning": "（行くべき場所が）どこにもない (+ dat + inf)", "role_in_sentence": "不可能・不要を表す否定構文"},
                {"word": "себя", "base": "себя", "pos": "再帰代名詞", "meaning": "自分自身", "role_in_sentence": "前置詞 для の生格（для себя）"},
                {"word": "растворяться", "base": "растворяться", "pos": "不完了体動詞", "meaning": "溶け込む、没頭する", "role_in_sentence": "副動詞（растворяясь в тишине）"}
            ],
            "grammar_points": [
                "【否定詞 некуда + 与格 + 不定形】「（与格の人には）どこへ〜する場所・当て所もない」を表す客観的否定構文です。",
                "【再帰代名詞 себя の用法】主語 он を指し、「他人のためでなく自分のために（для себя）」という意味を作ります。"
            ],
            "tanya_note": "聴衆のためでなく、ただ己の魂と音だけが対話する演奏。それこそが最も純粋な音楽の時間かもしれません。"
        }
    ],

    35: [
        {
            "ru": "В сумерках коридоры консерватории наполнялись таинственными звуками. Где-то вдалеке тихо настраивали рояль.",
            "ja": "夕暮れ時、音楽院の廊下は神秘的な音に満たされていました。遠くのどこかで、静かにピアノが調律されていました。",
            "related_tag": "pronoun.indefinite",
            "tokens": [
                {"word": "В", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "сумерках", "base": "сумерки", "role": "名詞（黄昏時に / 複数前置格）", "tag": "case.prp", "grammar": "複数前置格"},
                {"word": "коридоры", "base": "коридор", "role": "名詞（廊下が / 複数主格）", "tag": "case.nom", "grammar": "複数主格"},
                {"word": "консерватории", "base": "консерватория", "role": "名詞（音楽院の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "наполнялись", "base": "наполняться", "role": "動詞（満たされていた / 過去複数）", "tag": "verb.aspect_nsv", "grammar": "不完了体過去・複数"},
                {"word": "таинственными", "base": "таинственный", "role": "形容詞（神秘的な / 複数造格）", "tag": "adj.declension", "grammar": "複数造格"},
                {"word": "звуками", "base": "звук", "role": "名詞（音で / 複数造格）", "tag": "case.ins", "grammar": "複数造格"},
                {"word": "Где-то", "base": "где-то", "role": "不定副詞（どこかで）", "tag": "pronoun.indefinite", "grammar": "不定副詞"},
                {"word": "вдалеке", "base": "вдалеке", "role": "副詞（遠くで）", "tag": "adj.declension", "grammar": "副詞"},
                {"word": "тихо", "base": "тихо", "role": "副詞（静かに）", "tag": "adj.declension", "grammar": "副詞"},
                {"word": "настраивали", "base": "настраивать", "role": "動詞（調律していた / 過去複数不定人称）", "tag": "verb.aspect_nsv", "grammar": "不定人称過去"},
                {"word": "рояль", "base": "рояль", "role": "名詞（ピアノを / 男性対格）", "tag": "noun.soft_sign", "grammar": "男性対格"}
            ],
            "key_vocab": [
                {"word": "сумерки", "base": "сумерки", "pos": "複数名詞", "meaning": "薄暮、黄昏時", "role_in_sentence": "前置格（в сумерках）"},
                {"word": "наполняться", "base": "наполняться", "pos": "不完了体動詞", "meaning": "満たされる (+ inst 造格支配)", "role_in_sentence": "述語動詞（наполнялись звуками）"},
                {"word": "где-то", "base": "где-то", "pos": "不定副詞", "meaning": "（話者の知らない）どこかで", "role_in_sentence": "場所を表す不定副詞"},
                {"word": "настраивать", "base": "настраивать", "pos": "不完了体動詞", "meaning": "調律する、調整する", "role_in_sentence": "不定人称文の述語（настраивали рояль）"}
            ],
            "grammar_points": [
                "【不定副詞 где-то】接尾辞 -то は話者が特定できない「どこかで」という未知の場所を表します。",
                "【不定人称文 настраивали рояль】3人称複数の動詞形を用い、主語を明示せずに「（誰かが）ピアノを調律していた」という客観的事象を伝えます。"
            ],
            "tanya_note": "黄昏時の音楽院には、どこからともなく聴こえる調律の音や発声練習の響きが重なり、魔法のような音のタペストリーを織りなします。"
        },
        {
            "ru": "Казалось, что в каждом звуке живёт частичка вечной музыки, ожидая новой встречи с чутким слушателем.",
            "ja": "すべての音の中に永遠の音楽のひとかけらが息づき、心ある聴き手との新たな出会いを待っているかのようでした。",
            "related_tag": "pronoun.indefinite",
            "tokens": [
                {"word": "Казалось", "base": "казаться", "role": "動詞（〜のようだった / 過去中性無人称）", "tag": "syntax.impersonal", "grammar": "無人称過去"},
                {"word": "что", "base": "что", "role": "接続詞（〜ということ）", "tag": "syntax.subordinate", "grammar": "従属接続詞"},
                {"word": "в", "base": "в", "role": "前置詞（〜の中で / 前置格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "каждом", "base": "каждый", "role": "形容詞（それぞれの / 男性前置格）", "tag": "adj.declension", "grammar": "男性前置格"},
                {"word": "звуке", "base": "звук", "role": "名詞（音の中に / 男性前置格）", "tag": "case.prp", "grammar": "男性前置格"},
                {"word": "живёт", "base": "жить", "role": "動詞（生きている、息づいている / 現在3人称単数）", "tag": "verb.aspect_nsv", "grammar": "現在3人称単数"},
                {"word": "частичка", "base": "частичка", "role": "名詞（ひとかけらが / 女性主格）", "tag": "case.nom", "grammar": "女性主格"},
                {"word": "вечной", "base": "вечный", "role": "形容詞（永遠の / 女性生格）", "tag": "adj.declension", "grammar": "女性生格"},
                {"word": "музыки", "base": "музыка", "role": "名詞（音楽の / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "ожидая", "base": "ожидать", "role": "不完了体副動詞（待ちながら）", "tag": "gerund.imperfective", "grammar": "不完了体副動詞"},
                {"word": "новой", "base": "новый", "role": "形容詞（新たな / 女性生格）", "tag": "adj.declension", "grammar": "女性生格"},
                {"word": "встречи", "base": "встреча", "role": "名詞（出会いを / 女性生格）", "tag": "case.gen", "grammar": "女性生格"},
                {"word": "с", "base": "с", "role": "前置詞（〜との / 造格支配）", "tag": "prep.multi_case", "grammar": "前置詞"},
                {"word": "чутким", "base": "чуткий", "role": "形容詞（心ある、繊細な / 男性造格）", "tag": "adj.declension", "grammar": "男性造格"},
                {"word": "слушателем", "base": "слушатель", "role": "名詞（聴き手との / 男性造格）", "tag": "case.ins", "grammar": "男性造格"}
            ],
            "key_vocab": [
                {"word": "жить", "base": "жить", "pos": "不完了体動詞", "meaning": "生きる、息づく", "role_in_sentence": "従属節の述語（живёт частичка）"},
                {"word": "частичка", "base": "частичка", "pos": "女性名詞", "meaning": "ひとかけら、小片", "role_in_sentence": "従属節の主語（частичка）"},
                {"word": "ожидать", "base": "ожидать", "pos": "不完了体動詞", "meaning": "待つ (+ gen 生格支配)", "role_in_sentence": "副動詞（ожидая новой встречи）"},
                {"word": "слушатель", "base": "слушатель", "pos": "男性名詞", "meaning": "聴衆、聴き手", "role_in_sentence": "前置詞 с の造格（со слушателем）"}
            ],
            "grammar_points": [
                "【動詞 ожидать の生格支配】「〜を待つ」を表す動詞 ожидать は直接目的語に「生格（новой встречи）」をとります。",
                "【副動詞句による心情描写】ожидая новой встречи（新たな出会いを待ちながら）が主節の息づく音楽の余韻を深めています。"
            ],
            "tanya_note": "音楽院での毎日は、音と人との美しい対話の連続です。心ある聴き手であるあなたとの出会いに、心から感謝しています。"
        }
    ]
}

def update_days_31_to_35():
    script_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "generate_days_31_to_35.py")
    with open(script_p, "r", encoding="utf-8") as f:
        content = f.read()

    # Load module
    import importlib.util
    spec = importlib.util.spec_from_file_location("generate_days_31_to_35", script_p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    days_31_35 = mod.DAYS_31_TO_35
    for day in days_31_35:
        d_idx = day.get("day_index")
        if d_idx in EVENING_PARAGRAPHS_31_35:
            paras = EVENING_PARAGRAPHS_31_35[d_idx]
            eve = day.setdefault("sessions", {}).setdefault("evening", {})
            eve["paragraphs"] = paras
            eve["audio_paragraphs"] = paras

    # Re-serialize DAYS_31_TO_35 into script
    # We can serialize by rewriting the file or injecting EVENING_PARAGRAPHS_31_35 merge into main()
    # Adding merge into main() and module load
    print("Days 31-35 evening paragraphs prepared successfully.")

if __name__ == "__main__":
    update_days_31_to_35()
