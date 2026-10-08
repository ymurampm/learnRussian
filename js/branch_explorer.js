/**
 * Tanya Russian Trainer - Spatial Branch Explorer Module
 * Manages simultaneous multi-pane display:
 * 1. Declension / Conjugation Matrix
 * 2. Root Cluster & Semantic Network
 * 3. Tanya's Grammar Commentary & Conservatory Tips
 */

class BranchExplorer {
  constructor() {
    this.container = null;
    this.lessonData = null;
    this.selectedWord = null;
    this.isReciting = false;
    this.reciteColIdx = -1;
    this.reciteSessionId = 0;
  }

  init(containerElement, lessonData) {
    this.stopRecitation();
    this.container = containerElement;
    this.lessonData = lessonData;
    this.selectedWord = null;
    this.renderInitial();
  }

  stopRecitation() {
    const wasReciting = this.isReciting;
    this.reciteSessionId++;
    this.isReciting = false;
    this.reciteColIdx = -1;
    if (wasReciting && window.TTSPlayer) {
      window.TTSPlayer.stop();
      if (this.originalRate !== undefined) {
        window.TTSPlayer.setRate(this.originalRate);
        this.originalRate = undefined;
      }
    }
    const tableEl = this.container?.querySelector('#branchDeclensionTable');
    if (tableEl) {
      tableEl.querySelectorAll('tbody tr').forEach(r => {
        r.classList.remove('recite-active-row');
        r.querySelectorAll('td').forEach(c => c.classList.remove('recite-active-cell'));
      });
    }
    this.updateReciteButtonStates(-1, false);
  }

  detectIrregularAlert(branchData, tokenData = null) {
    if (!branchData && !tokenData) return null;
    if (branchData && branchData.irregular_alert) return branchData.irregular_alert;

    const w = (branchData.word || '').toLowerCase();
    const base = (branchData.base || '').toLowerCase();

    const irregularNouns = {
      'время': { badge: '⚠️ 格変化注意：-мя中性名詞 (-ен- 挿入)', detail: '生・与・前置格で времени、造格で временем と語幹に -ен- が現れます。' },
      'имя': { badge: '⚠️ 格変化注意：-мя中性名詞 (-ен- 挿入)', detail: '生・与・前置格で имени、造格で именем と語幹に -ен- が現れます。' },
      'мать': { badge: '⚠️ 格変化注意：特殊女性名詞 (-ер- 挿入)', detail: '主格・対格以外で матери, матерью など -ер- が現れます。' },
      'дочь': { badge: '⚠️ 格変化注意：特殊女性名詞 (-ер- 挿入)', detail: '主格・対格以外で дочери, дочерью など -ер- が現れます。' },
      'ребёнок': { badge: '⚠️ 格変化注意：補充法（複数形は дети）', detail: '単数は ребёнок ですが、複数形は全く別語源の дети, детей... に変化します。' },
      'человек': { badge: '⚠️ 格変化注意：補充法（複数形は люди）', detail: '単数は человек ですが、複数形は люди, людей... に変化します（数詞後を除く）。' },
      'друг': { badge: '⚠️ 格変化注意：特殊複数形 (друзья)', detail: '複数形は軟音化して друзья, друзей, друзьям, друзьями, о друзьях と変化します。' },
      'брат': { badge: '⚠️ 格変化注意：特殊複数形 (братья)', detail: '複数形は брать削除ではなく братья, братьев, братьям, братьями, о братьях と変化します。' }
    };

    if (irregularNouns[w]) return irregularNouns[w];
    if (irregularNouns[base]) return irregularNouns[base];

    // Special -ь noun alert
    if (w.endsWith('ь') || base.endsWith('ь')) {
      const g = window.getSoftSignNounGender ? window.getSoftSignNounGender(w, base, branchData.pos) : null;
      if (g === 'm') {
        return {
          badge: '🎯 露検2級 必修：-ь 語尾名詞の性別【男性名詞 ♂】',
          detail: `«${w || base}» は「-ь」で終わる男性名詞です（生格: -я, 造格: -ем）。語尾ルール（-тель, -арь, 月名など）や代表語彙をしっかり区別しましょう。`,
          related_tag: 'noun.soft_sign',
          jump_label: '-ь名詞の性別完全攻略'
        };
      } else if (g === 'f') {
        return {
          badge: '🎯 露検2級 必修：-ь 語尾名詞の性別【女性名詞 ♀ (第3変化)】',
          detail: `«${w || base}» は「-ь」で終わる第3変化女性名詞です（生格・与格・前置格すべて -и、造格は -ью）。語尾ルール（-ость/-есть, ヒソヒソ音+ь）をマスターしましょう。`,
          related_tag: 'noun.soft_sign',
          jump_label: '-ь名詞の性別完全攻略'
        };
      }
    }

    // Fleeting vowel alerts
    const fleetingVowelNouns = {
      'день': { badge: '⚠️ 出没音 (Беглые гласные e) に注意', detail: '単数主格 «день» に対し、生格以降は母音 e が脱落して «дня, дню, днём, о дне» と変化します。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'сон': { badge: '⚠️ 出没音 (Беглые гласные o) に注意', detail: '単数主格 «сон» に対し、生格以降は母音 o が脱落して «сна, сну, сном, о сне» と変化します。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'отец': { badge: '⚠️ 出没音 (Беглые гласные e) に注意', detail: '単数主格 «отец» に対し、生格以降は母音 e が脱落して «отца, отцу, отцом...» と変化します。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'песня': { badge: '⚠️ 出没音 (複数生格での e 挿入) に注意', detail: '複数主格 «песни» に対し、複数生格で子音間に e が現れて «песен» となります。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'девушка': { badge: '⚠️ 出没音 (複数生格での e 挿入) に注意', detail: '複数生格で子音間に e が現れて «девушек» となります。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'ручка': { badge: '⚠️ 出没音 (複数生格での e 挿入) に注意', detail: '複数生格で子音間に e が現れて «ручек» となります。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' },
      'окно': { badge: '⚠️ 出没音 (複数生格での o 挿入) に注意', detail: '複数主格 «окна» に対し、複数生格で子音間に o が現れて «окон» となります。', related_tag: 'noun.irregular_fleeting', jump_label: '出没音と特殊複数' }
    };
    if (fleetingVowelNouns[w]) return fleetingVowelNouns[w];
    if (fleetingVowelNouns[base]) return fleetingVowelNouns[base];

    // Prefixed motion verbs
    const prefixedMotionRegex = /^(?:по|в|во|вы|при|у|под|подо|от|ото|до|пере|про|за|об|обо|раз|разо|с|со)(?:йти|ехать|бежать|ходить|ездить|летать|лететь|плыть|плавать|нести|носить|вести|водить|везти|возить)/;
    if (prefixedMotionRegex.test(w) || prefixedMotionRegex.test(base)) {
      return {
        badge: '🎯 露検2級 必修：接頭辞付き移動動詞 (空間ベクトル)',
        detail: `«${w || base}» は接頭辞によって空間的な移動の方向や完了アスペクトが定まります。16大接頭辞マップで位置関係を整理しましょう。`,
        related_tag: 'verb.motion_prefixed',
        jump_label: '移動動詞の16大接頭辞マップ'
      };
    }

    // Passive participle agent (動作主の造格)
    if (tokenData && (tokenData.role?.includes('造格') || tokenData.tag?.includes('ins'))) {
      const heroTokens = this.lessonData?.hero_sentence?.tokens || [];
      const hasPassiveParticiple = heroTokens.some(t => t.tag?.includes('participle.passive') || t.role?.includes('受動形動詞') || (t.word && /(?:нный|нная|нное|нные|тый|тая|тое|тые)[,.]?$/i.test(t.word)));
      if (hasPassiveParticiple) {
        return {
          badge: '🎯 露検2級 必修：受動文と【動作主の造格】',
          detail: '受動文において「誰によって（動作主）」を表す語句は、前置詞（by等）を付けずに【単独の造格】で表現します。修飾する形容詞も名詞の性・数・格と完全に一致します。',
          related_tag: 'participle.passive',
          jump_label: '受動形動詞と動作主の造格'
        };
      }
    }

    if (tokenData && (tokenData.tag?.includes('participle.passive') || tokenData.role?.includes('受動形動詞'))) {
      return {
        badge: '🎯 露検2級 必修：受動形動詞 (Причастие) と動作主の造格',
        detail: `«${w || base}» は動詞から作られた受動過去形動詞です。修飾する名詞の性・数・格に一致して語尾が変化し、「誰によって」の動作主は【前置詞なしの造格】で直結します。`,
        related_tag: 'participle.passive',
        jump_label: '受動形動詞の用法'
      };
    }

    // Participles (Причастие)
    if (w.endsWith('щий') || w.endsWith('щая') || w.endsWith('щее') || w.endsWith('щие') ||
        w.endsWith('нный') || w.endsWith('нная') || w.endsWith('нное') || w.endsWith('нные') ||
        w.endsWith('мый') || w.endsWith('мая') ||
        (branchData.pos && branchData.pos.includes('形動詞')) ||
        (branchData.notes && branchData.notes.includes('【形動詞】'))) {
      return {
        badge: '🎯 露検2級 必修：形動詞 (Причастие) の機能と格変化',
        detail: `«${w || base}» は動詞から作られた「動詞的形容詞」です。修飾する名詞の性・数・格に合わせて形容詞と同様に格変化し、関係代名詞節（который節）を一語で格調高くまとめます。`,
        related_tag: 'participle.active',
        jump_label: '形動詞の文法'
      };
    }

    const tbl = branchData.declension_table;
    if (tbl && tbl.length >= 3 && tbl[0][0] === '人称') {
      const fYa = tbl[1][1] || '';
      const fTy = tbl[2][1] || '';
      if (fYa.includes('шу') && fTy.includes('шешь')) {
        return { badge: '⚠️ 活用注意：語幹子音交替 (с ⇔ ш)', detail: '全人称で語幹子音 с が ш に交替します（я пишу, ты пишешь...）。' };
      }
      if (fYa.includes('жу') && fTy.includes('дишь')) {
        return { badge: '⚠️ 活用注意：1人称単数の子音交替 (д ⇔ ж)', detail: '1人称単数のみ д が ж に交替します（я вижу, но ты видишь）。' };
      }
      if (fYa.includes('лю') && ['блю', 'плю', 'влю', 'млю'].some(s => fYa.includes(s))) {
        return { badge: '⚠️ 活用注意：1人称単数での л 挿入 (唇音変化)', detail: '1人称単数のみ語幹に л が挿入されます（я люблю, но ты любишь）。' };
      }
      if (w === 'хотеть' || fYa.includes('хочу')) {
        return { badge: '⚠️ 活用注意：混合変化動詞 (хотеть)', detail: '単数は第1変化 (хочу, хочешь, хочет)、複数は第2変化 (хотим, хотите, хотят) に分かれます。' };
      }
      if (w === 'бежать' || fYa.includes('бегу')) {
        return { badge: '⚠️ 活用注意：混合変化動詞 (бежать)', detail: '1人称単数 бегу, 3人称複数 бегут ですが、他は бежишь, бежит, бежим と変化します。' };
      }
      if (w === 'идти' || w === 'пойти' || fYa.includes('иду')) {
        return { badge: '⚠️ 活用注意：不規則幹・アクセント移動 (идти)', detail: '語尾母音にアクセント（иду́, идёшь...）。過去形は全く異なる語幹 шёл, шла, шли になります。' };
      }
      if (w === 'ехать' || w === 'поехать' || fYa.includes('еду')) {
        return { badge: '⚠️ 活用注意：特殊語幹交替 (ехать ⇔ еду)', detail: '不定形 ехать に対して、活用形は語幹に д が現れます（еду, едешь, едут）。' };
      }
      if (w === 'стать' || w.endsWith('стать') || fYa.includes('стану')) {
        return {
          badge: '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
          detail: '«стать» は将来の到達点や身分・職業を表す際、後ろに必ず【造格】を要求します（文中の「выдающимся музыкантом」が造格なのはこのためです）。活用は語幹に -н- が入る «я стану, ты станешь...»（単純未来）となります。',
          related_tag: 'verb.government',
          jump_label: '動詞の格支配'
        };
      }
    }

    // Direct fallback for Government Verbs
    if (w === 'стать' || w.endsWith('стать') || base === 'стать') {
      return {
        badge: '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        detail: '«стать» は将来の到達点や身分・職業を表す際、後ろに必ず【造格】を要求します（文中の「выдающимся музыкантом」が造格なのはこのためです）。活用は語幹に -н- が入る «я стану, ты станешь...»（単純未来）となります。',
        related_tag: 'verb.government',
        jump_label: '動詞の格支配'
      };
    }
    if (w === 'управлять' || base === 'управлять') {
      return {
        badge: '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        detail: '«управлять»（〜を操る・指揮する）は目的語に必ず【造格】を要求します（例: управлять звуком）。',
        related_tag: 'verb.government',
        jump_label: '動詞の格支配'
      };
    }
    if (w === 'заниматься' || base === 'заниматься') {
      return {
        badge: '🎯 露検2級 必修：動詞の格支配【造格支配 (+ 造格)】',
        detail: '«заниматься»（〜を勉強・練習する・専攻する）は対象に必ず【造格】を要求します（例: заниматься музыкой）。',
        related_tag: 'verb.government',
        jump_label: '動詞の格支配'
      };
    }
    if (w.startsWith('довольн') || base === 'доволен' || base === 'довольный') {
      return {
        badge: '🎯 露検2級 必修：形容詞短尾形の格支配【+ 造格】',
        detail: '«доволен»（満足している）は、満足の対象に必ず【造格】を要求します（例: доволен результатом, довольна выступлением）。',
        related_tag: 'adj.short_government',
        jump_label: '形容詞短尾形の格支配'
      };
    }
    if (w.startsWith('готов') || base === 'готов' || base === 'готовый') {
      return {
        badge: '🎯 露検2級 必修：形容詞短尾形の格支配【к + 与格】',
        detail: '«готов»（準備ができている）は名詞を続ける場合必ず前置詞 «к + 与格» を用います（例: готов к экзамену）。',
        related_tag: 'adj.short_government',
        jump_label: '形容詞短尾形の格支配'
      };
    }
    if (w === 'за' || base === 'за') {
      return {
        badge: '🎯 露検2級 必修：前置詞の格支配【造格 ⇔ 対格の使い分け】',
        detail: '【静止位置・目的は造格】（сидеть за столом / пойти за хлебом）、【移動方向・期間・代償は対格】（сесть за стол / выучить за неделю / заплатить за билет）。',
        related_tag: 'prep.multi_case',
        jump_label: '多格支配前置詞の使い分け'
      };
    }
    if (w === 'два' || w === 'две' || w === 'три' || w === 'четыре') {
      return {
        badge: '🎯 露検2級 必修：数詞と名詞の一致【主格直後は単数生格】',
        detail: '主格および不活動対格の直後は必ず【名詞の単数生格】が来ます（два рояля, две книги, три билета）。',
        related_tag: 'numeral.agreement',
        jump_label: '数詞と名詞の一致'
      };
    }

    return null;
  }

  renderInitial() {
    if (!this.container) return;

    // Pick first branch from lesson data or default
    const branches = this.lessonData?.branches || [];
    const firstBranch = branches.length > 0 ? branches[0] : null;

    this.renderPanes(firstBranch);
  }

  isUninflected(tag = '', role = '', pos = '') {
    const combined = `${tag} ${role} ${pos}`.toLowerCase();
    // Participles (形動詞・Причастие) decline like adjectives: NEVER uninflected!
    if (/participle|形動詞|причастие/i.test(combined)) return false;
    // Verbs (動詞: 活用) conjugate: NEVER uninflected!
    if (/(?:^|[^\w])(?:verb|глагол)(?:[^\w]|$)|動詞/i.test(combined)) return false;

    return /\badv\b|副詞|наречие/i.test(combined) ||
           /\bprep\b|前置詞|предлог/i.test(combined) ||
           /\bconj\b|接続詞|союз/i.test(combined) ||
           /\bparticle\b|助詞|小詞|частица/i.test(combined) ||
           /\binterj\b|間投詞|междометие/i.test(combined) ||
           /不変化/i.test(combined);
  }

  async selectWord(wordText, tokenData = null) {
    if (!wordText) return;
    this.stopRecitation();
    const cleanWord = (tokenData?.clean || wordText || '').replace(/[.,!?;:«»""'']/g, '').trim();
    this.selectedWord = cleanWord;
    
    // Play pronunciation
    if (window.TTSPlayer) {
      window.TTSPlayer.speakWord(cleanWord || wordText);
    }

    // === MASTER ARCHITECTURAL FIRST BRANCH: Part of Speech ===
    // If the word/token is an uninflected part of speech (副詞・前置詞・接続詞・助詞・間投詞),
    // it is a linguistic axiom that it CANNOT have declension (格変化) or conjugation (活用).
    const tokenRole = tokenData?.role || tokenData?.grammar || '';
    const isUninflectedWord = this.isUninflected(tokenData?.tag, tokenRole);
    const isParticipleToken = Boolean(
      (tokenData && (tokenData.tag?.includes('participle') || tokenRole.includes('形動詞') || tokenRole.includes('短語尾'))) ||
      /(?:ущ|ющ|ащ|ящ|вш|ш|нн|дан|дана|дано|даны)[а-яё]*$/i.test(cleanWord)
    );
    const isPrep = (tokenData?.tag === 'syntax.prep') || (tokenRole && tokenRole.includes('前置詞')) ||
                   ['на', 'в', 'с', 'к', 'по', 'о', 'из', 'до', 'от', 'у', 'за', 'под', 'при', 'через', 'перед', 'без'].includes(cleanWord.toLowerCase());

    // Check if lesson data already has this branch (exact word > table cell match > base match)
    const branches = this.lessonData?.branches || [];
    const target = cleanWord.toLowerCase();
    let match = branches.find(b => (b.word || '').toLowerCase().replace(/[.,!?;:«»""'']/g, '') === target);
    if (!match) {
      match = branches.find(b => {
        if (b.declension_table && Array.isArray(b.declension_table)) {
          return b.declension_table.some(row => 
            Array.isArray(row) && row.some(cell => {
              if (typeof cell !== 'string') return false;
              const words = cell.toLowerCase().split(/[\s,()«»/]+/).filter(Boolean);
              return words.includes(target);
            })
          );
        }
        return false;
      });
    }
    // Only fall back to base branch if NOT a participle (participles must never inherit base verb conjugations!)
    const cleanBase = (tokenData?.base || '').replace(/[.,!?;:«»""'']/g, '').trim();
    if (!match && cleanBase && !isParticipleToken) {
      match = branches.find(b => (b.word || '').toLowerCase() === cleanBase.toLowerCase());
    }

    // If word is uninflected, enforce that it NEVER carries any declension or conjugation table
    if (match && (isUninflectedWord || this.isUninflected('', '', match.pos))) {
      match.declension_table = null;
      match.declension_html = null;
    }

    // Enrich from VOCAB_DB only for INFLECTED words (never for uninflected)
    if (match && (!match.declension_table && !match.declension_html) && !isPrep && !isUninflectedWord && !this.isUninflected('', '', match.pos)) {
      if (window.API) {
        const queryTerm = match.word || cleanWord;
        const baseParam = isParticipleToken ? '' : cleanBase;
        const results = await window.API.searchVocabulary(queryTerm, baseParam);
        if (results && results.length > 0) {
          const entry = results[0];
          match.pos = match.pos || entry.pos;
          match.meaning = match.meaning || entry.meaning;
          if (!this.isUninflected('', '', match.pos)) {
            match.declension_table = match.declension_table || entry.declension_table;
            match.declension_html = match.declension_html || entry.declension_html;
          }
          match.irregular_alert = match.irregular_alert || entry.irregular_alert;
          if (!match.derivatives || match.derivatives.length === 0) {
            match.derivatives = entry.network || [];
          }
          if (!match.conservatory_collocations || match.conservatory_collocations.length === 0) {
            match.conservatory_collocations = entry.examples ? entry.examples.filter(e => e.ru).map(e => ({ ru: e.ru, ja: e.ja || '' })) : [];
          }
        }
      }
    }

    if (!match) {
      // Query Anki Vocabulary DB via API
      if (window.API) {
        const queryTerm = cleanWord;
        const baseParam = isParticipleToken ? '' : cleanBase;
        const results = await window.API.searchVocabulary(queryTerm, baseParam);
        if (results && results.length > 0) {
          const entry = results[0];
          const entryIsUninflected = isUninflectedWord || this.isUninflected(tokenData?.tag, tokenData?.role, entry.pos);
          let finalPos = entry.pos;
          if (isUninflectedWord) {
            if (/adv|副詞/i.test(`${tokenData?.tag} ${tokenData?.role}`)) {
              finalPos = '副詞 (Наречие・不変化詞)';
            } else if (/prep|前置詞/i.test(`${tokenData?.tag} ${tokenData?.role}`)) {
              finalPos = '前置詞 (Предлог・不変化詞)';
            } else if (/conj|接続詞/i.test(`${tokenData?.tag} ${tokenData?.role}`)) {
              finalPos = '接続詞 (Союз・不変化詞)';
            } else if (/part|助詞|小詞/i.test(`${tokenData?.tag} ${tokenData?.role}`)) {
              finalPos = '小詞 (Частица・不変化詞)';
            }
          }
          match = {
            word: entry.word,
            pos: finalPos,
            meaning: entry.meaning,
            is_preposition: entry.is_preposition,
            declension_table: entryIsUninflected ? null : entry.declension_table,
            declension_html: entryIsUninflected ? null : entry.declension_html,
            notes: entry.notes,
            anatomy: entry.anatomy,
            irregular_alert: entry.irregular_alert,
            derivatives: entry.network || [],
            aspect_pair: entry.aspect_pair || ((entry.pos && /動詞|verb|глагол/i.test(entry.pos)) ? (entry.notes || "") : ""),
            conservatory_collocations: (entry.conservatory_collocations && entry.conservatory_collocations.length > 0)
              ? entry.conservatory_collocations
              : (entry.examples ? entry.examples.filter(e => e.ru).map(e => ({ ru: e.ru, ja: e.ja || '' })) : [])
          };
        }
      }
    }

    if (!match) {
      let detectedPos = tokenRole || '重要単語';
      if (/participle.passive|受動|短語尾/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '受動過去形動詞（短語尾）';
      else if (/gerund|副動詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '副動詞 (Деепричастие)';
      else if (/adv|副詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '副詞 (Наречие・不変化詞)';
      else if (/prep|前置詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '前置詞 (Предлог・不変化詞)';
      else if (/conj|接続詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '接続詞 (Союз・不変化詞)';
      else if (/part|助詞|小詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '小詞 (Частица・不変化詞)';
      else if (/verb|動詞/i.test(`${tokenData?.tag} ${tokenRole}`)) detectedPos = '動詞';

      match = {
        word: wordText,
        pos: detectedPos,
        meaning: tokenRole || (isUninflectedWord ? '不変化詞' : ''),
        notes: tokenRole || '',
        anatomy: `«${wordText}» は文中で「${tokenRole || '修飾語'}」として機能しています。`,
        declension_table: null,
        declension_html: null,
        derivatives: [],
        conservatory_collocations: []
      };
    }

    this.renderPanes(match, wordText, tokenData, isPrep);

    if (window.API) {
      window.API.logBehavior({ branches_opened_count: 1 });
    }
  }

  renderPanes(branchData, clickedWord = "", tokenData = null, isPrep = false) {
    if (!this.container) return;
    this.stopRecitation();

    const displayWord = branchData ? branchData.word : (clickedWord || "単語をクリック");
    const grammarFocus = this.lessonData?.grammar_focus || {};
    const fmt = window.formatRussianClickable || (t => t);

    this.currentBranchData = branchData;
    const tokenRole = tokenData?.role || tokenData?.grammar || '';
    const isPreposition = isPrep || (branchData && (branchData.is_preposition || (branchData.pos && branchData.pos.includes('前置詞'))));
    const isShortParticiple = Boolean(
      (tokenRole && (tokenRole.includes('短語尾') || tokenRole.includes('кратк'))) ||
      (tokenData && (tokenData.tag === 'participle.passive_short' || tokenData.tag === 'participle.short')) ||
      (branchData && (branchData.pos?.includes('短語尾') || branchData.pos?.includes('кратк') || (branchData.declension_table && branchData.declension_table[0] && String(branchData.declension_table[0][1]).includes('短語尾'))))
    );
    const isParticiple = Boolean(
      !isShortParticiple && (
        (tokenData && (tokenData.tag?.includes('participle') || tokenRole.includes('形動詞'))) ||
        (branchData && (branchData.pos?.includes('形動詞') || branchData.pos?.includes('participle') || branchData.notes?.includes('【形動詞】') || (branchData.word && /(?:щий|щая|щее|щие|вший|вшая|вшее|вшие|нный|нная|нное|нные|мый|мая|мое|мые)$/i.test(branchData.word))))
      )
    );
    const isExplicitNonVerb = Boolean(branchData?.pos && /名詞|形容詞|前置詞|副詞|代名詞|形動詞/.test(branchData.pos));
    const isVerb = Boolean(!isParticiple && !isShortParticiple && !isExplicitNonVerb && branchData && (
      (branchData.pos && (branchData.pos.includes('動詞') || branchData.pos.includes('不完了') || branchData.pos.includes('完了体') || branchData.pos.includes('verb'))) ||
      Boolean(branchData.aspect_pair) ||
      (branchData.declension_table && branchData.declension_table[0] && String(branchData.declension_table[0][0]).includes('人称'))
    ));
    this.isCurrentVerb = isVerb;

    // Irregular alert evaluation
    const irregularAlert = this.detectIrregularAlert(branchData, tokenData);
    const alertBannerHtml = irregularAlert ? `
      <div class="irregular-alert-banner">
        <div class="irregular-alert-badge">${irregularAlert.badge}</div>
        <div class="irregular-alert-detail">${irregularAlert.detail}</div>
        ${irregularAlert.related_tag ? `
          <div style="margin-top:8px;">
            <button class="branch-handbook-jump-btn" data-tag="${irregularAlert.related_tag}" style="background:rgba(212,168,83,0.18); border:1px solid rgba(212,168,83,0.5); color:var(--gold-light); font-size:0.75rem; border-radius:4px; padding:4px 10px; cursor:pointer; font-weight:600; display:inline-flex; align-items:center; gap:4px;">
              <span>📖 教科書で${irregularAlert.jump_label || '関連文法解説'}（${irregularAlert.related_tag}）を読む →</span>
            </button>
          </div>
        ` : ''}
      </div>
    ` : '';

    // 1. Left Pane: Declension / Conjugation Matrix / Preposition Card
    let tableHtml = `<div style="color:var(--text-muted); font-size:0.88rem; padding:10px 0;">単語をクリックすると格変化・活用表が展開されます。</div>`;

    // === MASTER ARCHITECTURAL FIRST BRANCH: Part of Speech Division ===
    // 1. 不変化詞 (Uninflected): 前置詞, 副詞, 接続詞, 助詞/小詞, 間投詞
    //    -> 語形変化を持たない。格変化表・動詞活用表は絶対に表示しない。
    // 2. 活用詞 (Verbs): 動詞
    //    -> 人称変化 (現在/未来6人称), 過去形, 命令形等の活用表を表示。
    // 3. 格変化詞 (Declension Words): 名詞, 形容詞, 代名詞, 数詞
    //    -> 6格 (主・生・与・対・造・前) の格変化表を表示。

    const isUninflected = this.isUninflected(tokenData?.tag, tokenData?.role, branchData?.pos);

    if (isPreposition) {
      // 1-A. Preposition Governance Card
      const notes = branchData?.notes || `【格支配】${tokenData?.role || '前置格支配'}`;
      const anatomy = branchData?.anatomy || '前置詞自身は変化（格変化・活用）しませんが、後続の名詞に特定の格を要求（格支配）します。';
      tableHtml = `
        ${alertBannerHtml}
        <div class="preposition-pane-card">
          <div style="font-size:0.95rem; font-weight:700; color:var(--gold-light); margin-bottom:6px; display:flex; align-items:center; gap:6px;">
            <span>📌 前置詞 «${displayWord}» の格支配ノート</span>
          </div>
          <div style="font-size:0.85rem; color:#ffe599; font-weight:600; margin-bottom:6px;">
            ${fmt(notes)}
          </div>
          <div class="commentary-text" style="margin-bottom:8px;">
            ${window.formatCommentaryHtml ? window.formatCommentaryHtml(anatomy) : fmt(anatomy)}
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); border-top:1px dashed var(--border-color); padding-top:6px;">
            💡 前置詞自体は変化しません。後ろに置く名詞の語尾（格）に注目しましょう！
          </div>
        </div>
      `;
    } else if (isUninflected) {
      // 1-B. Uninflected Card (Adverb, Conjunction, Particle, Interjection)
      if (branchData) {
        branchData.declension_table = null;
        branchData.declension_html = null;
      }
      const posText = branchData?.pos || (tokenData?.tag?.includes('adv') ? '副詞 (Наречие)' : (tokenData?.tag?.includes('conj') ? '接続詞 (Союз)' : '不変化詞'));
      const meaningText = branchData?.meaning || tokenData?.role || '';
      tableHtml = `
        ${alertBannerHtml}
        <div class="uninflected-card">
          <div style="font-size:0.95rem; font-weight:700; color:#38bdf8; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
            <span>💡 不変化詞ノート «${displayWord}»</span>
          </div>
          <div style="font-size:0.85rem; color:#ffe599; font-weight:600; margin-bottom:6px;">
            品詞：${posText} ${meaningText ? `(${meaningText})` : ''}
          </div>
          <div style="font-size:0.84rem; color:var(--text-secondary); line-height:1.6; margin-bottom:8px;">
            ロシア語の文法上、この単語は格変化や人称活用などの語尾変化を持たない<strong>不変化詞（Неизменяемое слово）</strong>です。<br>
            文の主語や時制が変わっても形は不変で、そのまま文章のリズムやニュアンスを作ります。
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); border-top:1px dashed var(--border-color); padding-top:6px;">
            📌 複雑な格変化表を覚える必要はありません！そのままの響きで記憶しましょう。
          </div>
        </div>
      `;
    } else if (branchData) {
      if (branchData.declension_table && branchData.declension_table.length > 0) {
        let rows = branchData.declension_table;

        // If word is a participle, NEVER display a verb conjugation table (with 人称)!
        if ((isParticiple || isShortParticiple) && rows[0] && String(rows[0][0]).includes('人称')) {
          rows = this.generateParticipleTable(branchData.word || displayWord, isShortParticiple);
          branchData.declension_table = rows;
        }

        // Auto-expand 1-row or 4-row adjective/participle tables to full 6 cases
        if (isParticiple || branchData.pos?.includes('形容詞')) {
          if (rows.length === 2 && Array.isArray(rows[0]) && rows[0].some(h => String(h).includes('男性'))) {
            rows = this.expandAdjectiveTable(rows);
            branchData.declension_table = rows;
          } else if (rows.length >= 5 && String(rows[0][0]).includes('性・数')) {
            rows = this.expandGenderRowsToSixCases(rows);
            branchData.declension_table = rows;
          }
        }

        // Recitation toolbar for verbs and nouns/adjectives/participles
        let recitationToolbarHtml = '';
        if (rows && rows.length > 1) {
          const numCols = rows[0].length;
          const header0 = String(rows[0][0] || '');
          const isVerbTable = isVerb || (header0.includes('人称') && !isParticiple && !isShortParticiple) || header0.includes('時制');

          if (isVerbTable) {
            if (numCols === 2) {
              recitationToolbarHtml = `
                <div class="conjugation-recite-toolbar">
                  <span style="font-size:0.80rem; color:var(--gold-light); font-weight:600; margin-right:auto;">動詞活用表 (Спряжение)</span>
                  <button class="conjugation-recite-btn" id="reciteBtnCol1" data-col="1" data-col-name="6活用" data-default-label="🔊 6活用を連続朗読" title="6つの人称活用を順に読み上げます">
                    <span class="recite-label">🔊 6活用を連続朗読</span>
                    <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:3px;">Я, Ты, Он...</kbd>
                  </button>
                </div>
              `;
            } else if (numCols >= 3) {
              const rawCol1 = (rows[0][1] || '').trim();
              const rawCol2 = (rows[0][2] || '').trim();
              let labelCol1 = '現在形';
              let labelCol2 = '過去形';
              let toolbarTitle = '時制別 活用表 (現在・過去)';

              if (rawCol1.includes('НСВ') || rawCol2.includes('СВ')) {
                labelCol1 = 'НСВ (不完了)';
                labelCol2 = 'СВ (完了)';
                toolbarTitle = 'アスペクト別 活用表';
              } else {
                if (rawCol1.includes('現在')) labelCol1 = '現在形';
                else labelCol1 = rawCol1.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim().slice(0, 8);

                if (rawCol2.includes('過去')) labelCol2 = '過去形';
                else labelCol2 = rawCol2.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim().slice(0, 8);
              }

              recitationToolbarHtml = `
                <div class="conjugation-recite-toolbar">
                  <span style="font-size:0.80rem; color:var(--gold-light); font-weight:600; margin-right:auto;">${toolbarTitle}</span>
                  <button class="conjugation-recite-btn" id="reciteBtnCol1" data-col="1" data-col-name="${labelCol1}" data-default-label="🔊 ${labelCol1} 朗読" title="${labelCol1} の活用を順に読み上げます">
                    <span class="recite-label">🔊 ${labelCol1} 朗読</span>
                  </button>
                  <button class="conjugation-recite-btn" id="reciteBtnCol2" data-col="2" data-col-name="${labelCol2}" data-default-label="🔊 ${labelCol2} 朗読" title="${labelCol2} の活用を順に読み上げます">
                    <span class="recite-label">🔊 ${labelCol2} 朗読</span>
                  </button>
                </div>
              `;
            }
          } else if (isShortParticiple) {
            recitationToolbarHtml = `
              <div class="conjugation-recite-toolbar">
                <span style="font-size:0.80rem; color:var(--gold-light); font-weight:600; margin-right:auto;">受動形動詞 短語尾形（性・数一致）</span>
                <button class="conjugation-recite-btn" id="reciteBtnCol1" data-col="1" data-col-name="性数4形" data-default-label="🔊 4つの性・数を連続朗読" title="男性・女性・中性・複数の4形を順に読み上げます">
                  <span class="recite-label">🔊 4つの性・数を連続朗読</span>
                  <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:3px;">-∅, -а, -о, -ы</kbd>
                </button>
              </div>
            `;
          } else {
            // Nouns / Adjectives / Participles / Pronouns declension table recitation
            const colButtons = [];
            for (let c = 1; c < numCols; c++) {
              let colHeader = (rows[0][c] || `列${c}`).trim();
              let shortName = colHeader.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim();
              if (shortName.length > 8) shortName = shortName.slice(0, 8);
              const label = shortName ? `🔊 ${shortName} 6格朗読` : `🔊 列${c} 朗読`;
              colButtons.push(`
                <button class="conjugation-recite-btn" id="reciteBtnCol${c}" data-col="${c}" data-col-name="${shortName}" data-default-label="${label}" title="${shortName}の格変化を順に読み上げます">
                  <span class="recite-label">${label}</span>
                </button>
              `);
            }
            const tableTitle = isParticiple 
              ? '形動詞 格変化表 (Склонение причастия)' 
              : (branchData?.pos?.includes('形容詞') ? '形容詞 格変化表 (Склонение прилагательного)' : '格変化表 (Склонение)');
            recitationToolbarHtml = `
              <div class="conjugation-recite-toolbar">
                <span style="font-size:0.80rem; color:var(--gold-light); font-weight:600; margin-right:auto;">${tableTitle}</span>
                ${colButtons.join('')}
              </div>
            `;
          }
        }

        tableHtml = `
          ${alertBannerHtml}
          ${recitationToolbarHtml}
          <div style="overflow-x:auto;">
            <table class="declension-table" id="branchDeclensionTable">
              <thead>
                <tr>${rows[0].map(h => `<th>${h}</th>`).join('')}</tr>
              </thead>
              <tbody>
                ${rows.slice(1).map(r => {
                  const isMatch = clickedWord && r.some(cell => cell && cell.toLowerCase().includes(clickedWord.toLowerCase()));
                  const rowRuSentence = r.slice(0, 2).join(' ');
                  return `
                    <tr class="${isMatch ? 'highlight-cell' : ''}" data-row-ru="${rowRuSentence}" title="クリックでこの活用を発音 🔊">
                      ${r.map((cell, colI) => {
                        const cleanCell = (colI === 0 && typeof cell === 'string') 
                          ? cell.replace(/\s*\([A-Za-z]+\)/g, '').trim() 
                          : cell;
                        return `<td data-col-idx="${colI}">${cleanCell}</td>`;
                      }).join('')}
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else if (branchData.declension_html) {
        let cleanHtml = branchData.declension_html;
        cleanHtml = cleanHtml.replace(/<details>/gi, '<details open>');
        cleanHtml = cleanHtml.replace(/background-color\s*:\s*#[a-fA-F0-9]{3,6}/gi, 'background-color:transparent');
        cleanHtml = cleanHtml.replace(/background-color\s*:\s*rgb\([^)]+\)/gi, 'background-color:transparent');
        cleanHtml = cleanHtml.replace(/border\s*:\s*1px\s+solid\s+#ccc/gi, 'border:1px solid #3d312e');
        tableHtml = `
          ${alertBannerHtml}
          <div class="declension-html-wrap">${cleanHtml}</div>
        `;
      } else if (branchData.declension_summary) {
        tableHtml = `
          ${alertBannerHtml}
          <div style="background:var(--bg-secondary); padding:10px; border-radius:6px; font-size:0.88rem; line-height:1.6; border:1px solid var(--border-color);">
            <div style="color:var(--gold-light); font-weight:600; margin-bottom:4px;">📊 変化の要約</div>
            <div>${branchData.declension_summary}</div>
            ${branchData.tip ? `<div style="color:var(--text-muted); margin-top:6px; font-size:0.82rem;">💡 ${branchData.tip}</div>` : ''}
          </div>
        `;
      } else {
        // Uninflected word fallback card (adverbs, conjunctions, particles)
        const posText = branchData.pos || (tokenData?.tag?.includes('adv') ? '副詞 (Наречие)' : (tokenData?.tag?.includes('conj') ? '接続詞 (Союз)' : '不変化詞'));
        const meaningText = branchData.meaning || tokenData?.role || '';
        tableHtml = `
          ${alertBannerHtml}
          <div class="uninflected-card">
            <div style="font-size:0.95rem; font-weight:700; color:#38bdf8; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
              <span>💡 不変化詞ノート «${displayWord}»</span>
            </div>
            <div style="font-size:0.85rem; color:#ffe599; font-weight:600; margin-bottom:6px;">
              品詞：${posText} ${meaningText ? `(${meaningText})` : ''}
            </div>
            <div style="font-size:0.84rem; color:var(--text-secondary); line-height:1.6; margin-bottom:8px;">
              ロシア語の文法上、この単語は格変化や人称活用などの語尾変化を持たない<strong>不変化詞（Неизменяемое слово）</strong>です。<br>
              文の主語や時制が変わっても形は不変で、そのまま文章のリズムやニュアンスを作ります。
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); border-top:1px dashed var(--border-color); padding-top:6px;">
              📌 複雑な格変化表を覚える必要はありません！そのままの響きで記憶しましょう。
            </div>
          </div>
        `;
      }
    }

    // Helper: format each derivative cleanly without parenthesis bugs or split lines
    const formatDerivative = (raw) => {
      if (!raw || typeof raw !== 'string') return '';
      let str = raw.replace(/^[•\-\*\s]+/, '').replace(/\s+/g, ' ').trim().replace(/[,]+$/, '');
      if (!str) return '';
      const m = str.match(/^([а-яА-ЯёЁ\s\-–—/«»]+)(?:\s*\((.*)\))?$/);
      if (m) {
        const ru = m[1].trim();
        const ja = m[2] ? m[2].replace(/[)]+$/, '').trim() : '';
        const ruPart = fmt(ru);
        const jaPart = ja ? `<span style="color:var(--text-muted); font-size:0.82rem;">(${ja})</span>` : '';
        return `${ruPart} ${jaPart}`.trim();
      }
      if (str.endsWith(')') && !str.includes('(')) {
        str = str.replace(/[)]+$/, '').trim();
      }
      return fmt(str);
    };

    // 2. Center Pane: Root Cluster & Derivatives
    let branchListHtml = '';
    if (branchData) {
      if (branchData.aspect_pair) {
        branchListHtml += `
          <div class="branch-item">
            <div class="branch-item-title">🔄 アスペクトのペア (Видовая пара)</div>
            <div class="branch-item-desc">${fmt(branchData.aspect_pair)}</div>
          </div>
        `;
      }
      if (branchData.derivatives && branchData.derivatives.length > 0) {
        const cleanDerivatives = branchData.derivatives
          .filter(d => typeof d === 'string' && d.trim().length > 0)
          .map(d => formatDerivative(d))
          .filter(Boolean);

        if (cleanDerivatives.length > 0) {
          branchListHtml += `
            <div class="branch-item">
              <div class="branch-item-title">🌲 語根と派生語 (Семья слов)</div>
              <div class="branch-item-desc" style="display:flex; flex-direction:column; gap:6px;">
                ${cleanDerivatives.map(d => `<div>• ${d}</div>`).join('')}
              </div>
            </div>
          `;
        }
      }
      if (branchData.conservatory_collocations && branchData.conservatory_collocations.length > 0) {
        const renderedCollocs = branchData.conservatory_collocations.slice(0, 3).map(item => {
          const ruText = (item.ru || '').trim();
          const jaText = (item.ja || '').trim().replace(/^\(|\)$/g, '');
          const ruPart = fmt(ruText);
          const jaPart = jaText ? `<span style="color:var(--text-muted); font-size:0.82rem;">(${jaText})</span>` : '';
          return `<div style="margin-bottom:6px; line-height:1.5;">${ruPart} ${jaPart}</div>`;
        }).join('');
        branchListHtml += `
          <div class="branch-item">
            <div class="branch-item-title">🎹 音楽院コロケーション・表現例</div>
            <div class="branch-item-desc">${renderedCollocs}</div>
          </div>
        `;
      }
    }

    // 3. Right Pane: Tanya's Commentary & Context
    let contextualNoteHtml = '';
    const activeRole = tokenRole || (branchData && branchData.pos) || '';
    if (activeRole) {
      const heroTokens = this.lessonData?.hero_sentence?.tokens || [];
      const hasPassiveParticiple = heroTokens.some(t => {
        const tr = t.role || t.grammar || '';
        return t.tag?.includes('participle.passive') || tr.includes('受動') || (t.word && /(?:нный|нная|нное|нные|тый|тая|тое|тые)[,.]?$/i.test(t.word));
      });

      const hasImpersonalPredicate = heroTokens.some(t => {
        const w = (t.word || '').toLowerCase().replace(/[.,!?;:]/g, '');
        const r = t.role || t.grammar || '';
        return ['нельзя', 'можно', 'нужно', 'надо', 'пора', 'холодно', 'трудно', 'легко', 'жаль', 'необходимо', 'хочется', 'удалось', 'приходится', 'пришлось'].includes(w) ||
               t.tag?.includes('syntax.impersonal') || r.includes('無人称') || r.includes('禁止') || r.includes('許可') || r.includes('義務');
      });

      if (hasImpersonalPredicate && (activeRole.includes('与格') || tokenData?.tag?.includes('case.dat') || tokenData?.tag === 'syntax.impersonal')) {
        const curWord = branchData?.word || displayWord;
        const predTok = heroTokens.find(t => {
          const w = (t.word || '').toLowerCase().replace(/[.,!?;:]/g, '');
          const r = t.role || t.grammar || '';
          return ['нельзя', 'можно', 'нужно', 'надо', 'пора', 'холодно', 'трудно', 'легко', 'жаль', 'необходимо', 'хочется', 'удалось', 'приходится', 'пришлось'].includes(w) ||
                 t.tag?.includes('syntax.impersonal') || r.includes('無人称述語');
        });
        const predWord = predTok ? predTok.word : '無人称述語';
        contextualNoteHtml = `
          <div class="contextual-case-note" style="background:rgba(212,168,83,0.12); border-left:3px solid var(--gold); padding:10px 14px; border-radius:6px; margin-bottom:14px; line-height:1.6;">
            <div style="font-weight:700; color:var(--gold-light); font-size:0.92rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
              <span>🎯 なぜ与格（Дательный падеж）なのか？【無人称文の論理的主語】</span>
            </div>
            <div style="font-size:0.86rem; color:var(--text-primary); margin-bottom:6px;">
              この文の述語は<strong>«${predWord}»（無人称述語詞）</strong>です。ロシア語では「〜してはならない」「〜する必要がある」「〜できる」といった義務・許可・禁止や心理・感覚状態を表す際、<strong>その動作・状態の体験者（誰にとってなのか）を必ず【与格】で表します</strong>。
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
              • <strong>主格（1格）は置けない絶対ルール</strong>：日本語の「ソリスト<strong>は</strong>動揺してはならない」につられて主格 «солист» を置いてはいけません。無人称文には文法上の主格主語が存在せず、人物は必ず与格 «${curWord}»（ソリストにとって）になります。<br>
              • <strong>基本構文</strong>：<code>与格（人・主体） ＋ ${predWord} ＋ 動詞不定形</code>（例: Мне нужно, Нам можно, Солисту нельзя）。
            </div>
          </div>
        `;
      } else if (hasPassiveParticiple && (activeRole.includes('造格') || tokenData?.tag?.includes('ins') || (branchData && branchData.pos && branchData.pos.includes('造格')))) {
        contextualNoteHtml = `
          <div class="contextual-case-note" style="background:rgba(212,168,83,0.12); border-left:3px solid var(--gold); padding:10px 14px; border-radius:6px; margin-bottom:14px; line-height:1.6;">
            <div style="font-weight:700; color:var(--gold-light); font-size:0.92rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
              <span>🎯 なぜ造格（Творительный падеж）なのか？</span>
            </div>
            <div style="font-size:0.86rem; color:var(--text-primary); margin-bottom:6px;">
              この文では、受動文にかかる<strong>【動作主の造格（Творительный действующего лица）】</strong>として使われています。
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
              • <strong>前置詞不要の鉄則</strong>：英語の <em>by</em> や日本語の「〜によって」に惑わされて前置詞（от や с）を付けてはいけません。ロシア語では名詞そのものを造格にします。<br>
              • <strong>形容詞の一致</strong>：修飾先の名詞と性・数・格を完全に一致させて造格語尾をとります。
            </div>
          </div>
        `;
      } else if (isShortParticiple || activeRole.includes('受動') || activeRole.includes('短語尾') || tokenData?.tag?.includes('participle.passive')) {
        const curWord = branchData?.word || displayWord;
        contextualNoteHtml = `
          <div class="contextual-case-note" style="background:rgba(212,168,83,0.12); border-left:3px solid var(--gold); padding:10px 14px; border-radius:6px; margin-bottom:14px; line-height:1.6;">
            <div style="font-weight:700; color:var(--gold-light); font-size:0.92rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
              <span>🪶 受動過去形動詞・短語尾形（Краткое причастие）の構文的役割</span>
            </div>
            <div style="font-size:0.86rem; color:var(--text-primary); margin-bottom:6px;">
              «${curWord}» は完了体動詞から作られた<strong>受動過去形動詞の短語尾形</strong>です。文の述語として「〜された」「〜してある」状態を表します。
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
              • <strong>格変化をしない絶対鉄則</strong>：短語尾形は名詞のような6格変化（主格・生格・与格…）を持ちません。主語の性・数（男 -∅, 女 -а, 中 -о, 複 -ы）に一致して文の述語になります。<br>
              • <strong>動作主は前置詞なしの造格</strong>：誰によって行われたかを表す動作主は、前置詞なしの造格で直結します。
            </div>
          </div>
        `;
      } else if (tokenData?.tag?.includes('participle') || activeRole.includes('形動詞') || isParticiple) {
        const curWord = branchData?.word || displayWord;
        contextualNoteHtml = `
          <div class="contextual-case-note" style="background:rgba(212,168,83,0.12); border-left:3px solid var(--gold); padding:10px 14px; border-radius:6px; margin-bottom:14px; line-height:1.6;">
            <div style="font-weight:700; color:var(--gold-light); font-size:0.92rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
              <span>🪶 形動詞（動詞的形容詞）の構文構造</span>
            </div>
            <div style="font-size:0.86rem; color:var(--text-primary); margin-bottom:6px;">
              «${curWord}» は動詞から派生した<strong>形動詞（Причастие）</strong>です。修飾する名詞の性・数・格に合わせて形容詞と同様に格変化します。
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.5;">
              • <strong>動作主の造格を従える</strong>：受動形動詞の動作主（誰によって行われたか）は前置詞なしの【造格】で直結します。<br>
              • <strong>関係代名詞節との置き換え</strong>：который節を一語で引き締め、格調高い複文を作ります。
            </div>
          </div>
        `;
      }
    }

    const commentaryTitle = grammarFocus.title || "ターニャの文法解剖ノート";
    const commentaryText = branchData?.anatomy || grammarFocus.commentary || "例文中の文法構造と、音楽表現における自然な語感を解説します。";

    // Bookmark status check
    const currentWord = branchData ? branchData.word : (clickedWord || "");
    const isBookmarked = window.bookmarkedWordsSet && currentWord && window.bookmarkedWordsSet.has(currentWord.toLowerCase());
    const bookmarkBtnHtml = currentWord ? `
      <button class="word-bookmark-btn ${isBookmarked ? 'bookmarked' : ''}" id="paneBookmarkBtn" title="${isBookmarked ? 'マークを解除' : '単語をマーク保存'}">
        <span>${isBookmarked ? '★ マーク済み' : '☆ マーク'}</span>
      </button>
    ` : '';

    this.container.innerHTML = `
      <div class="multipane-grid">
        <!-- Pane 1: Declension Table -->
        <div class="pane-card">
          <div class="pane-card-header">
            <span>${isPreposition ? '📌 前置詞の役割' : (isShortParticiple ? '🪶 受動形動詞 短語尾形（性・数一致）' : (isParticiple ? '🪶 能動形動詞の格変化表 (Причастие)' : (isVerb ? '🎹 動詞の活用表' : '📊 格変化表')))}</span>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="pane-badge ru-text">${(clickedWord && clickedWord !== displayWord) ? `${clickedWord} (← ${displayWord})` : displayWord}</span>
              ${(!isVerb && !isParticiple && window.renderSoftSignGenderBadge) ? window.renderSoftSignGenderBadge(displayWord, branchData?.word, branchData?.pos, tokenData?.role) : ''}
              ${bookmarkBtnHtml}
            </div>
          </div>
          ${tableHtml}
        </div>

        <!-- Pane 2: Vocabulary Network & Derivatives -->
        <div class="pane-card">
          <div class="pane-card-header">
            <span>🌲 語根・関連語ネットワーク</span>
            <span class="pane-badge">枝分かれ探索</span>
          </div>
          <div>
            ${branchListHtml || '<div style="color:var(--text-muted); font-size:0.82rem;">単語を選択すると関連語・アスペクト対がここに展開します。</div>'}
          </div>
        </div>

        <!-- Pane 3: Tanya's Commentary -->
        <div class="pane-card tanya-commentary-pane">
          <div class="pane-card-header">
            <span>💬 ターニャ先生の解説</span>
            <span class="pane-badge">音楽院の視点</span>
          </div>
          <div class="tanya-mini-header">
            <img src="assets/images/tanya_explaining.jpg" alt="ターニャ先生">
            <div>
              <div style="font-size:0.86rem; font-weight:700; color:var(--gold-light);">${commentaryTitle}</div>
              <div style="font-size:0.72rem; color:var(--text-muted);">モスクワ音楽院での実践より</div>
            </div>
          </div>
          <div class="commentary-text">
            ${contextualNoteHtml}
            ${window.formatCommentaryHtml ? window.formatCommentaryHtml(commentaryText) : fmt(commentaryText)}
          </div>
        </div>
      </div>
    `;

    // Wire Bookmark toggle button
    const bookmarkBtn = this.container.querySelector('#paneBookmarkBtn');
    if (bookmarkBtn && currentWord) {
      bookmarkBtn.onclick = async () => {
        if (window.API) {
          const res = await window.API.toggleBookmark({
            word: currentWord,
            base: tokenData?.base || currentWord,
            pos: branchData?.pos || tokenData?.role || '',
            meaning: branchData?.meaning || tokenData?.role || ''
          });
          if (res && res.status === 'ok') {
            if (!window.bookmarkedWordsSet) {
              window.bookmarkedWordsSet = new Set();
            }
            if (res.is_bookmarked) {
              window.bookmarkedWordsSet.add(currentWord.toLowerCase());
            } else {
              window.bookmarkedWordsSet.delete(currentWord.toLowerCase());
            }
            bookmarkBtn.classList.toggle('bookmarked', res.is_bookmarked);
            bookmarkBtn.innerHTML = `<span>${res.is_bookmarked ? '★ マーク済み' : '☆ マーク'}</span>`;
            bookmarkBtn.title = res.is_bookmarked ? 'マークを解除' : '単語をマーク保存';

            if (window.App && window.App.updateBookmarkBadge) {
              window.App.updateBookmarkBadge(res.bookmarks_count);
            }
          }
        }
      };
    }

    // Wire handbook jump button from alert banner
    this.container.querySelectorAll('.branch-handbook-jump-btn').forEach(btn => {
      btn.onclick = () => {
        const tag = btn.dataset.tag;
        if (tag && window.Handbook) {
          window.Handbook.openTag(tag);
        }
      };
    });

    // Wire all recitation buttons (Verbs, Nouns, Adjectives)
    this.container.querySelectorAll('.conjugation-recite-btn').forEach(btn => {
      const col = parseInt(btn.dataset.col, 10);
      if (col) {
        btn.onclick = () => this.reciteConjugation(col);
      }
    });

    // Wire individual row clicks in declension/conjugation table
    const tableEl = this.container.querySelector('#branchDeclensionTable');
    if (tableEl) {
      const rows = tableEl.querySelectorAll('tbody tr');
      const isVerbTable = this.isVerbTable(tableEl, Array.from(rows));

      rows.forEach((r, rowIdx) => {
        r.onclick = (e) => {
          this.stopRecitation();
          rows.forEach(x => {
            x.classList.remove('recite-active-row');
            x.querySelectorAll('td').forEach(c => c.classList.remove('recite-active-cell'));
          });
          r.classList.add('recite-active-row');
          const targetTd = e.target ? e.target.closest('td') : null;
          const clickedColIdx = targetTd ? parseInt(targetTd.dataset.colIdx, 10) : 1;
          const cells = r.querySelectorAll('td');
          const colToSpeak = (clickedColIdx >= 1 && clickedColIdx < cells.length) ? clickedColIdx : 1;
          if (cells[colToSpeak]) {
            cells[colToSpeak].classList.add('recite-active-cell');
          }

          if (window.TTSPlayer) {
            if (isVerbTable) {
              const rawPerson = (cells[0]?.textContent || '').trim();
              let verb = (cells[colToSpeak]?.textContent || '').trim().replace(/\(.*?\)/g, '').replace(/（.*?）/g, '');
              verb = verb.replace(/[^а-яёА-ЯЁ\s-]/g, '').trim();
              const cleanPerson = this.resolveVerbPronoun(rawPerson, rowIdx, cells[colToSpeak]?.textContent || '');
              if (verb && verb !== '-') {
                const phrase = (cleanPerson && !verb.startsWith(cleanPerson)) ? `${cleanPerson} ${verb}` : verb;
                window.TTSPlayer.speakSentence(phrase);
              }
            } else {
              // Noun / Adjective / Pronoun: speak ONLY the clean Russian noun/adj word!
              // NEVER speak case abbreviations like "Nom", "Gen", "主格"!
              const rawText = (cells[colToSpeak]?.textContent || '').trim();
              let cleanWord = rawText.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim();
              if (cleanWord.includes('/')) {
                cleanWord = cleanWord.split('/')[0].trim();
              }
              cleanWord = cleanWord.replace(/[^а-яёА-ЯЁ\s-]/g, '').trim();
              if (cleanWord && cleanWord !== '-' && cleanWord !== '—') {
                window.TTSPlayer.speakSentence(cleanWord);
              }
            }
          }
        };
      });

      // Pre-warm audio in the background so 1st click is instant
      this.prewarmConjugationAudio(tableEl);
    }
  }

  isVerbTable(tableEl, rows = null) {
    if (!tableEl) return Boolean(this.isCurrentVerb);
    const theadTh0 = (tableEl.querySelector('thead th')?.textContent || '').trim();
    const tableHeader0 = (this.currentBranchData?.declension_table && this.currentBranchData.declension_table[0] && this.currentBranchData.declension_table[0][0])
      ? String(this.currentBranchData.declension_table[0][0]).trim()
      : '';

    // If header explicitly mentions case ("格"), it is definitely a noun/adjective table, NEVER a verb table
    if (theadTh0.includes('格') || tableHeader0.includes('格')) return false;

    const trList = rows || Array.from(tableEl.querySelectorAll('tbody tr'));
    if (trList.length > 0) {
      const firstColTexts = trList.map(r => r.querySelector('td')?.textContent?.trim() || '');
      // If table rows contain case labels, it's a declension table
      if (firstColTexts.some(t => /主格|生格|与格|対格|造格|前格|前置格|Именительный|Родительный|Дательный|Винительный|Творительный|Предложный|Nom|Gen|Dat|Acc|Inst|Prep/i.test(t))) {
        return false;
      }
      // If table rows contain person or verb gender labels
      if (firstColTexts.some(t => /^(я|ты|он|она|оно|мы|вы|они)\b/i.test(t) || /人称|過去・|過去 \(|男性|女性|中性/.test(t))) {
        return true;
      }
    }

    if (/人称|時制|動詞|Спряжение/i.test(theadTh0) || /人称|時制|動詞|Спряжение/i.test(tableHeader0)) {
      return true;
    }

    if (this.currentBranchData?.pos && /名詞|形容詞|前置詞|副詞|代名詞/.test(this.currentBranchData.pos)) {
      return false;
    }

    return Boolean(this.isCurrentVerb);
  }

  resolveVerbPronoun(personText, rowIdx = 0, formText = '') {
    let p = (personText || '').replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim();
    if (p.includes('/')) p = p.split('/')[0].trim();
    if (p.includes(',')) p = p.split(',')[0].trim();

    const lower = p.toLowerCase();
    // Check Cyrillic pronouns ('они' before 'он' to prevent substring collision)
    if (lower.startsWith('они')) return 'они';
    if (lower.startsWith('оно')) return 'оно';
    if (lower.startsWith('она')) return 'она';
    if (lower.startsWith('он')) return 'он';
    if (lower.startsWith('мы')) return 'мы';
    if (lower.startsWith('вы')) return 'вы';
    if (lower.startsWith('ты')) return 'ты';
    if (lower.startsWith('я')) return 'я';

    // Japanese labels in personText or formText
    const combined = `${personText} ${formText}`;
    if (combined.includes('複') || combined.includes('複数')) return 'они';
    if (combined.includes('中') || combined.includes('中性')) return 'оно';
    if (combined.includes('女') || combined.includes('女性')) return 'она';
    if (combined.includes('男') || combined.includes('男性')) return 'он';
    if (combined.includes('1人称') || combined.includes('一人称')) return combined.includes('複') ? 'мы' : 'я';
    if (combined.includes('2人称') || combined.includes('二人称')) return combined.includes('複') ? 'вы' : 'ты';
    if (combined.includes('3人称') || combined.includes('三人称')) return combined.includes('複') ? 'они' : 'он';

    // Standard 6-row fallback (я, ты, он, мы, вы, они)
    const defaultPronouns = ['я', 'ты', 'он', 'мы', 'вы', 'они'];
    if (rowIdx >= 0 && rowIdx < defaultPronouns.length) return defaultPronouns[rowIdx];
    return 'он';
  }

  extractChantItems(rows, colIdx, isVerbTable = null) {
    if (!rows || rows.length === 0) return { items: [], tokens: [] };
    const items = [];
    const tokens = [];

    // Table type detection: does header or structure indicate verb conjugation (人称/時制)?
    if (isVerbTable === null) {
      const tableEl = this.container?.querySelector('#branchDeclensionTable');
      isVerbTable = this.isVerbTable(tableEl, rows);
    }

    rows.forEach((tr, rowIdx) => {
      const cells = tr.querySelectorAll('td');
      if (!cells || cells.length <= colIdx) return;

      const personText = (cells[0]?.textContent || '').trim();
      const formText = (cells[colIdx]?.textContent || '').trim();

      // Clean form: remove any Japanese or notes in parentheses
      let cleanForm = formText.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim();
      if (!cleanForm || cleanForm === '-' || cleanForm === '—') return;

      if (cleanForm.includes('/')) {
        cleanForm = cleanForm.split('/')[0].trim();
      }
      cleanForm = cleanForm.replace(/[^а-яёА-ЯЁ\s-]/g, '').trim();
      if (!cleanForm) return;

      let phrase = '';
      let person = '';

      if (isVerbTable) {
        person = this.resolveVerbPronoun(personText, rowIdx, formText);
        phrase = (person && !cleanForm.startsWith(person)) ? `${person} ${cleanForm}` : cleanForm;
      } else {
        // Noun / Adjective / Pronoun declension table: chant ONLY Russian form (NEVER "Nom", "Gen", etc.)
        phrase = cleanForm;
      }

      items.push({
        rowIdx,
        tr,
        person: isVerbTable ? person : '',
        form: cleanForm,
        phrase
      });

      // Split words into tokens with rowIdx mapping for real-time synchronized karaoke
      phrase.split(/\s+/).filter(Boolean).forEach(w => {
        tokens.push({ word: w, rowIdx });
      });
    });

    return { items, tokens };
  }

  prewarmConjugationAudio(tableEl) {
    if (!tableEl) return;
    try {
      const rows = Array.from(tableEl.querySelectorAll('tbody tr'));
      if (rows.length === 0) return;

      const numCols = tableEl.querySelectorAll('thead th').length || 3;
      for (let col = 1; col < Math.min(numCols, 5); col++) {
        const { items } = this.extractChantItems(rows, col);
        if (items.length > 0) {
          const fullText = items.map(it => it.phrase).join(', ') + '.';
          setTimeout(() => {
            fetch(`/api/tts?text=${encodeURIComponent(fullText)}&rate=1.12`, { priority: 'low' }).catch(() => {});
          }, (col - 1) * 200);
        }
      }
    } catch (err) {
      console.warn('Prewarming audio error:', err);
    }
  }

  async reciteConjugation(colIdx) {
    // If clicking the button of currently reciting column -> stop recitation
    if (this.isReciting && this.reciteColIdx === colIdx) {
      this.stopRecitation();
      return;
    }

    // Stop active recitation immediately (exclusive cutoff)
    this.stopRecitation();

    // Small tick to ensure prior loop cleanly cancels and halts
    await new Promise(r => setTimeout(r, 60));

    const tableEl = this.container?.querySelector('#branchDeclensionTable');
    if (!tableEl) return;

    const rows = Array.from(tableEl.querySelectorAll('tbody tr'));
    if (rows.length === 0) return;

    const { items, tokens } = this.extractChantItems(rows, colIdx);
    if (items.length === 0) return;

    const currentSessionId = ++this.reciteSessionId;
    this.isReciting = true;
    this.reciteColIdx = colIdx;
    this.updateReciteButtonStates(colIdx, true);

    // Natural classroom recitation cadence: brisk tempo (1.12x)
    const reciteRate = 1.12;
    if (window.TTSPlayer) {
      if (this.originalRate === undefined) {
        this.originalRate = window.TTSPlayer.currentRate || 1.0;
      }
      window.TTSPlayer.setRate(reciteRate);
    }

    const highlightRow = (rowIdx) => {
      if (!this.isReciting || this.reciteSessionId !== currentSessionId) return;
      rows.forEach(r => {
        r.classList.remove('recite-active-row');
        r.querySelectorAll('td').forEach(c => c.classList.remove('recite-active-cell'));
      });
      const targetTr = rows[rowIdx];
      if (targetTr) {
        targetTr.classList.add('recite-active-row');
        const cells = targetTr.querySelectorAll('td');
        if (cells[colIdx]) {
          cells[colIdx].classList.add('recite-active-cell');
        }
        targetTr.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    };

    // Full natural classroom chant: comma-separated sequence produces ~100ms brisk human breath pauses
    // "я хочу, ты хочешь, он хочет, мы хотим, вы хотите, они хотят."
    const fullChantText = items.map(it => it.phrase).join(', ') + '.';

    // Highlight 1st row immediately
    highlightRow(items[0].rowIdx);

    if (window.TTSPlayer) {
      await new Promise((resolve) => {
        let completed = false;
        const finish = () => {
          if (!completed) {
            completed = true;
            if (this.reciteSessionId === currentSessionId) {
              this.stopRecitation();
            }
            resolve();
          }
        };

        window.TTSPlayer.speakSentence(
          fullChantText,
          tokens,
          (tokenIdx) => {
            if (!this.isReciting || this.reciteSessionId !== currentSessionId) return;
            const t = tokens[tokenIdx];
            if (t && t.rowIdx !== undefined) {
              highlightRow(t.rowIdx);
            }
          },
          finish
        );
      });
    } else {
      this.stopRecitation();
    }
  }

  updateReciteButtonStates(activeColIdx, isReciting) {
    if (!this.container) return;
    const btns = this.container.querySelectorAll('.conjugation-recite-btn');
    btns.forEach(btn => {
      const col = parseInt(btn.dataset.col, 10);
      const labelSpan = btn.querySelector('.recite-label');
      if (isReciting && col === activeColIdx) {
        btn.classList.add('active');
        if (labelSpan) labelSpan.textContent = '⏹ 朗読を停止';
      } else {
        btn.classList.remove('active');
        if (labelSpan) {
          const colName = btn.dataset.colName || (col === 1 ? 'НСВ' : 'СВ');
          labelSpan.textContent = btns.length === 1 ? '🔊 6活用を連続朗読' : `🔊 ${colName} 朗読`;
        }
      }
    });
  }

  expandAdjectiveTable(rows) {
    if (!rows || rows.length !== 2) return rows;
    const vals = rows[1];
    let m = vals[0] || '', f = vals[1] || '', n = vals[2] || '', pl = vals[3] || '';
    if (vals.length === 3) {
      pl = vals[2];
      const stem = m.replace(/́/g, '').slice(0, -2);
      n = stem + (f.endsWith('яя') ? 'ее' : 'ое');
    }
    m = m.trim().replace(/́/g, '');
    f = f.trim().replace(/́/g, '');
    n = n.trim().replace(/́/g, '');
    pl = pl.trim().replace(/́/g, '');

    const stem = m.slice(0, -2);
    const lastCons = stem.slice(-1);

    if (m === 'третий' || (m.endsWith('ий') && f.endsWith('ья'))) {
      return [
        ['格', `男性 (${m})`, `女性 (${f})`, `中性 (${n})`, `複数 (${pl})`],
        ['主格', m, f, n, pl],
        ['生格', `${stem}ьего`, `${stem}ьей`, `${stem}ьего`, `${stem}ьих`],
        ['与格', `${stem}ьему`, `${stem}ьей`, `${stem}ьему`, `${stem}ьим`],
        ['対格', `${m} / ${stem}ьего`, `${stem}ью`, n, `${pl} / ${stem}ьих`],
        ['造格', `${stem}ьим`, `${stem}ьей`, `${stem}ьим`, `${stem}ьими`],
        ['前置格', `${stem}ьем`, `${stem}ьей`, `${stem}ьем`, `${stem}ьих`]
      ];
    }

    if (f.endsWith('яя') && n.endsWith('ее')) {
      return [
        ['格', `男性 (${m})`, `女性 (${f})`, `中性 (${n})`, `複数 (${pl})`],
        ['主格', m, f, n, pl],
        ['生格', `${stem}его`, `${stem}ей`, `${stem}его`, `${stem}их`],
        ['与格', `${stem}ему`, `${stem}ей`, `${stem}ему`, `${stem}им`],
        ['対格', `${m} / ${stem}его`, `${stem}юю`, n, `${pl} / ${stem}их`],
        ['造格', `${stem}им`, `${stem}ей`, `${stem}им`, `${stem}ими`],
        ['前置格', `${stem}ем`, `${stem}ей`, `${stem}ем`, `${stem}их`]
      ];
    }

    if (['ж', 'ч', 'ш', 'щ', 'ц'].includes(lastCons) && n.endsWith('ее')) {
      return [
        ['格', `男性 (${m})`, `女性 (${f})`, `中性 (${n})`, `複数 (${pl})`],
        ['主格', m, f, n, pl],
        ['生格', `${stem}его`, `${stem}ей`, `${stem}его`, `${stem}их`],
        ['与格', `${stem}ему`, `${stem}ей`, `${stem}ему`, `${stem}им`],
        ['対格', `${m} / ${stem}его`, `${stem}ую`, n, `${pl} / ${stem}их`],
        ['造格', `${stem}им`, `${stem}ей`, `${stem}им`, `${stem}ими`],
        ['前置格', `${stem}ем`, `${stem}ей`, `${stem}ем`, `${stem}их`]
      ];
    }

    if (['г', 'к', 'х'].includes(lastCons) || (['ж', 'ч', 'ш', 'щ'].includes(lastCons) && m.endsWith('ой'))) {
      return [
        ['格', `男性 (${m})`, `女性 (${f})`, `中性 (${n})`, `複数 (${pl})`],
        ['主格', m, f, n, pl],
        ['生格', `${stem}ого`, `${stem}ой`, `${stem}ого`, `${stem}их`],
        ['与格', `${stem}ому`, `${stem}ой`, `${stem}ому`, `${stem}им`],
        ['対格', `${m} / ${stem}ого`, `${stem}ую`, n, `${pl} / ${stem}их`],
        ['造格', `${stem}им`, `${stem}ой`, `${stem}им`, `${stem}ими`],
        ['前置格', `${stem}ом`, `${stem}ой`, `${stem}ом`, `${stem}их`]
      ];
    }

    return [
      ['格', `男性 (${m})`, `女性 (${f})`, `中性 (${n})`, `複数 (${pl})`],
      ['主格', m, f, n, pl],
      ['生格', `${stem}ого`, `${stem}ой`, `${stem}ого`, `${stem}ых`],
      ['与格', `${stem}ому`, `${stem}ой`, `${stem}ому`, `${stem}ым`],
      ['対格', `${m} / ${stem}ого`, `${stem}ую`, n, `${pl} / ${stem}ых`],
      ['造格', `${stem}ым`, `${stem}ой`, `${stem}ым`, `${stem}ыми`],
      ['前置格', `${stem}ом`, `${stem}ой`, `${stem}ом`, `${stem}ых`]
    ];
  }

  expandGenderRowsToSixCases(rows) {
    if (!rows || rows.length < 5) return rows;
    let m = '', f = '', n = '', pl = '';
    for (let i = 1; i < rows.length; i++) {
      const r = rows[i];
      const gName = String(r[0] || '');
      const val = String(r[1] || '').trim();
      if (gName.includes('男')) m = val;
      else if (gName.includes('女')) f = val;
      else if (gName.includes('中')) n = val;
      else if (gName.includes('複')) pl = val;
    }
    if (m && f) {
      return this.expandAdjectiveTable([
        ['男性', '女性', '中性', '複数'],
        [m, f, n || (m.replace(/́/g, '').slice(0, -2) + 'ое'), pl || (m.replace(/́/g, '').slice(0, -2) + 'ые')]
      ]);
    }
    return rows;
  }

  generateParticipleTable(word, isShort = false) {
    let clean = (word || '').replace(/[.,!?;:«»""'']/g, '').trim().toLowerCase();
    if (isShort) {
      // If an infinitive was passed (e.g. продать), derive the short passive stem
      if (clean.endsWith('ть') || clean.endsWith('ти')) {
        if (clean.endsWith('дать')) clean = clean.slice(0, -4) + 'дан';
        else if (clean.endsWith('ать') || clean.endsWith('ять')) clean = clean.slice(0, -3) + 'ан';
        else if (clean.endsWith('ить') || clean.endsWith('еть')) clean = clean.slice(0, -3) + 'ен';
        else clean = clean.slice(0, -2) + 'т';
      }
      const stem = clean.replace(/(?:ана|ано|аны|ена|ено|ены|на|но|ны|та|то|ты|ан|ен|н|т)$/, '');
      const isT = clean.endsWith('т') || clean.endsWith('та') || clean.endsWith('то') || clean.endsWith('ты');
      const sfx = isT ? 'т' : 'н';
      const m = `${stem}${sfx}`;
      const f = `${stem}${sfx}а`;
      const n = `${stem}${sfx}о`;
      const pl = `${stem}${sfx}ы`;
      return [
        ['性・数', '短語尾形 (Краткая форма)', '用例・語形補足'],
        ['男性', m, `Концерт был ${m}.`],
        ['女性', f, `Соната была ${f}.`],
        ['中性', n, `Произведение было ${n}.`],
        ['複数', pl, `Все билеты были ${pl}.`]
      ];
    }
    // Full participle
    let stem = clean;
    for (const end of ['ющий', 'ющая', 'ющее', 'ющие', 'ущий', 'ущая', 'ущее', 'ущие',
                       'ящий', 'ящая', 'ящее', 'ящие', 'ащий', 'ащая', 'ащее', 'ащие',
                       'вший', 'вшая', 'вшее', 'вшие', 'ший', 'шая', 'шее', 'шие',
                       'нный', 'нная', 'нное', 'нные', 'тый', 'тая', 'тое', 'тые',
                       'его', 'ему', 'им', 'ем', 'ей', 'ую', 'их', 'ими', 'ого', 'ому', 'ым', 'ом', 'ой', 'ых', 'ыми',
                       'ый', 'ий', 'ая', 'яя', 'ое', 'ее', 'ые', 'ие']) {
      if (clean.endsWith(end)) {
        stem = clean.slice(0, -end.length);
        break;
      }
    }
    const isSibilant = clean.includes('щ') || clean.includes('ш');
    const nom_m = `${stem}${isSibilant ? 'ий' : 'ый'}`;
    const nom_f = `${stem}ая`;
    const nom_n = `${stem}${isSibilant ? 'ее' : 'ое'}`;
    const nom_pl = `${stem}${isSibilant ? 'ие' : 'ые'}`;
    return this.expandAdjectiveTable([
      ['男性', '女性', '中性', '複数'],
      [nom_m, nom_f, nom_n, nom_pl]
    ]);
  }
}

window.BranchExplorer = new BranchExplorer();
