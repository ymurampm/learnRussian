/**
 * Tanya Russian Trainer - Grammar Handbook (教科書ビュー) Engine
 * Interactive reference manual for Russian grammar featuring Moscow Conservatory examples,
 * declension/conjugation tables, Tanya/Alyona audio dialogues, and exam pitfall tips.
 */

class GrammarHandbook {
  constructor() {
    this.data = null;
    this.activeTagId = 'case.nom';
    this.modal = document.getElementById('handbookModal');
    this.sidebar = document.getElementById('handbookSidebar');
    this.reader = document.getElementById('handbookReader');
    this.closeBtn = document.getElementById('handbookClose');

    if (this.closeBtn && this.modal) {
      this.closeBtn.onclick = () => this.close();
    }
  }

  init(modalElement, sidebarElement, readerElement) {
    if (modalElement) this.modal = modalElement;
    if (sidebarElement) this.sidebar = sidebarElement;
    if (readerElement) this.reader = readerElement;
    this.closeBtn = document.getElementById('handbookClose');
    if (this.closeBtn && this.modal) {
      this.closeBtn.onclick = () => this.close();
    }
  }

  async open(tagId = null) {
    if (!this.modal) return;
    this.modal.classList.add('open');
    if (!this.data) {
      await this.loadData();
    }
    if (tagId) {
      this.activeTagId = tagId;
    }
    this.render();
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('open');
    }
    if (window.TTSPlayer) {
      window.TTSPlayer.stop();
    }
  }

  async openTag(tagId) {
    // Close other modals if open
    const openModals = document.querySelectorAll('.modal-overlay.open');
    openModals.forEach(m => {
      if (m.id !== 'handbookModal') m.classList.remove('open');
    });

    await this.open(tagId);
  }

  async loadData() {
    if (this.reader) {
      this.reader.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-muted);">
          <span>モスクワ音楽院 文法ハンドブックを読み込み中...</span>
        </div>
      `;
    }
    try {
      const res = await fetch('/api/handbook');
      if (!res.ok) throw new Error('Failed to load handbook');
      this.data = await res.json();
    } catch (e) {
      if (this.reader) {
        this.reader.innerHTML = `<div style="color:var(--crimson-soft); padding:20px;">文法データの読み込みに失敗しました: ${e.message}</div>`;
      }
    }
  }

  getAllChapters() {
    if (!this.data || !this.data.categories) return [];
    const chapters = [];
    this.data.categories.forEach(cat => {
      (cat.chapters || []).forEach(ch => {
        chapters.push({ ...ch, category_name: cat.category_name });
      });
    });
    return chapters;
  }

  resolveTagId(rawTag) {
    if (!rawTag) return null;
    const tag = rawTag.trim().toLowerCase();
    const chapters = this.getAllChapters();

    // 1. Direct exact match
    let match = chapters.find(c => c.tag_id.toLowerCase() === tag);
    if (match) return match.tag_id;

    // 2. Comprehensive grammar taxonomy alias mappings
    const ALIAS_MAP = {
      // Pronouns (代名詞体系 - 露検2級最重要)
      'pronoun.indefinite': 'pronoun.indefinite',
      'pronoun.indef': 'pronoun.indefinite',
      'pronoun.negative': 'pronoun.negative',
      'pronoun.neg': 'pronoun.negative',
      'pronoun.each': 'adj.declension',
      'pronoun.all': 'adj.declension',
      'pronoun.demo': 'adj.declension',
      'pronoun.poss': 'adj.declension',
      'pronoun.pers': 'case.nom',

      // Gerunds & Adverbial Participles (副動詞 - 露検2級最重要)
      'gerund.imperfective': 'gerund.imperfective',
      'gerund.perfective': 'gerund.perfective',
      'gerund.verbal_adverb': 'gerund.verbal_adverb',
      'gerund': 'gerund.verbal_adverb',
      'adverbial_participle': 'gerund.verbal_adverb',
      'adverbial_participle.imperfective': 'gerund.imperfective',
      'adverbial_participle.perfective': 'gerund.perfective',
      'verb.adverbial_nsv': 'gerund.imperfective',
      'verb.adverbial_sv': 'gerund.perfective',
      'verb.gerund_nsv': 'gerund.imperfective',
      'verb.gerund_sv': 'gerund.perfective',
      'verb.gerund': 'gerund.verbal_adverb',
      'syntax.adverbial': 'gerund.verbal_adverb',
      'gerund_perfective': 'gerund.perfective',
      'gerund_imperfective': 'gerund.imperfective',

      // Participles (形動詞)
      'participle.passive': 'participle.passive',
      'participle.passive_past': 'participle.passive',
      'participle.passive_pres': 'participle.passive',
      'participle.passive_short': 'participle.passive',
      'participle.short': 'participle.passive',
      'participle.active': 'participle.active',
      'participle.active_pres': 'participle.active',
      'participle.active_past': 'participle.active',
      'participle': 'participle.active',

      // Verb aspect
      'verb.aspect': 'verb.aspect_nsv',
      'verb.aspect_nsv': 'verb.aspect_nsv',
      'verb.aspect_sv': 'verb.aspect_nsv',
      'pos.verb': 'verb.aspect_nsv',
      'verb.past': 'verb.aspect_nsv',
      'verb.pres': 'verb.aspect_nsv',
      'verb.inf': 'verb.aspect_nsv',
      'verb.imperative': 'verb.irregular',
      'verb.reflexive': 'verb.aspect_nsv',

      // Motion verbs
      'verb.motion_uni': 'verb.motion_uni',
      'verb.motion_multi': 'verb.motion_uni',
      'verb.motion_determ': 'verb.motion_uni',
      'verb.motion_indeterm': 'verb.motion_uni',
      'verb.motion': 'verb.motion_uni',
      'verb.motion_prefixed': 'verb.motion_prefixed',

      // Verb government
      'verb.government': 'verb.government',

      // Noun special topics
      'noun.soft_sign': 'noun.soft_sign',
      'noun.irregular_fleeting': 'noun.irregular_fleeting',
      'noun.fleeting': 'noun.irregular_fleeting',

      // Cases
      'case.nom': 'case.nom',
      'case.gen': 'case.gen',
      'case.dat': 'case.dat',
      'case.acc': 'case.acc',
      'case.acc_inanimate': 'case.acc',
      'case.acc_animate': 'case.acc',
      'case.ins': 'case.ins',
      'case.prp': 'case.prp',
      'prep.multi_case': 'prep.multi_case',

      // Adjectives & Numerals
      'adj.declension': 'adj.declension',
      'adj.short': 'adj.short_government',
      'adj.comparative': 'adj.declension',
      'adj.short_government': 'adj.short_government',
      'numeral': 'numeral.agreement',
      'numeral.agreement': 'numeral.agreement',
      'numeral.declension_all': 'numeral.declension_all',
      'numeral.collective': 'numeral.collective',
      'numeral.coll': 'numeral.collective',
      'numeral.oba': 'numeral.collective',

      // Syntax & Clauses
      'syntax.impersonal': 'syntax.impersonal',
      'impersonal': 'syntax.impersonal',
      'predicative': 'syntax.impersonal',
      'syntax.pred': 'syntax.impersonal',
      'syntax.relative': 'syntax.relative',
      'syntax.conditional': 'syntax.conditional',
      'syntax.subordinate': 'syntax.subordinate',
      'syntax.subord': 'syntax.subordinate',
      'syntax.chtoby': 'syntax.subordinate',
      'syntax.conjunction': 'syntax.relative',
      'syntax.conj': 'syntax.relative',
      'pos.conj': 'syntax.relative',
      'syntax.prep': 'prep.multi_case',
      'pos.prep': 'prep.multi_case',
      'syntax.particle': 'pronoun.negative',
      'syntax.neg': 'pronoun.negative',
      'pos.particle': 'pronoun.negative',
      'syntax.adverb': 'adj.declension',
      'syntax.adv': 'adj.declension',
      'pos.adv': 'adj.declension'
    };

    if (ALIAS_MAP[tag]) {
      const aliasTarget = ALIAS_MAP[tag];
      match = chapters.find(c => c.tag_id === aliasTarget);
      if (match) return match.tag_id;
    }

    // 3. Keyword / partial heuristic resolution
    // A. Pronouns (不定代名詞・否定代名詞)
    if (tag.includes('indef') || tag.includes('不定代名詞')) {
      match = chapters.find(c => c.tag_id === 'pronoun.indefinite');
      if (match) return match.tag_id;
    }
    if (tag.includes('neg') || tag.includes('否定代名詞') || tag.includes('否定副詞')) {
      match = chapters.find(c => c.tag_id === 'pronoun.negative');
      if (match) return match.tag_id;
    }

    // B. Impersonal (無人称構文)
    if (tag.includes('impersonal') || tag.includes('無人称')) {
      match = chapters.find(c => c.tag_id === 'syntax.impersonal');
      if (match) return match.tag_id;
    }

    // B2. Collective numerals & Subordinate clauses
    if (tag.includes('collective') || tag.includes('集合数詞') || tag.includes('оба') || tag.includes('обе')) {
      match = chapters.find(c => c.tag_id === 'numeral.collective');
      if (match) return match.tag_id;
    }
    if (tag.includes('subordinate') || tag.includes('従属節') || tag.includes('чтобы') || tag.includes('хотя')) {
      match = chapters.find(c => c.tag_id === 'syntax.subordinate');
      if (match) return match.tag_id;
    }

    // C. Specific Gerund (副動詞) heuristics MUST precede generic participle matching!
    if ((tag.includes('perfective') || tag.includes('完了体') || tag.includes(' св') || tag.endsWith('_sv')) &&
        (tag.includes('gerund') || tag.includes('adverbial') || tag.includes('副動詞') || tag.includes('деепричастие'))) {
      match = chapters.find(c => c.tag_id === 'gerund.perfective');
      if (match) return match.tag_id;
    }
    if ((tag.includes('imperfective') || tag.includes('不完了体') || tag.includes(' нсв') || tag.endsWith('_nsv')) &&
        (tag.includes('gerund') || tag.includes('adverbial') || tag.includes('副動詞') || tag.includes('деепричастие'))) {
      match = chapters.find(c => c.tag_id === 'gerund.imperfective');
      if (match) return match.tag_id;
    }
    if (tag.includes('完了体副動詞')) {
      match = chapters.find(c => c.tag_id === 'gerund.perfective');
      if (match) return match.tag_id;
    }
    if (tag.includes('不完了体副動詞')) {
      match = chapters.find(c => c.tag_id === 'gerund.imperfective');
      if (match) return match.tag_id;
    }
    if (tag.includes('gerund') || tag.includes('деепричастие') || tag.includes('副動詞') || tag.includes('adverbial')) {
      match = chapters.find(c => c.tag_id === 'gerund.verbal_adverb') ||
              chapters.find(c => c.tag_id === 'gerund.perfective') ||
              chapters.find(c => c.tag_id === 'gerund.imperfective');
      if (match) return match.tag_id;
    }

    // D. Participles (形動詞)
    if (tag.includes('passive') || tag.includes('受動')) {
      match = chapters.find(c => c.tag_id === 'participle.passive');
      if (match) return match.tag_id;
    }
    if (tag.includes('participle') || tag.includes('形動詞')) {
      match = chapters.find(c => c.tag_id === 'participle.active');
      if (match) return match.tag_id;
    }
    if (tag.includes('motion_prefixed') || tag.includes('接頭辞')) {
      match = chapters.find(c => c.tag_id === 'verb.motion_prefixed');
      if (match) return match.tag_id;
    }
    if (tag.includes('motion') || tag.includes('移動動詞')) {
      match = chapters.find(c => c.tag_id === 'verb.motion_uni');
      if (match) return match.tag_id;
    }
    if (tag.includes('aspect') || tag.includes('体')) {
      match = chapters.find(c => c.tag_id === 'verb.aspect_nsv');
      if (match) return match.tag_id;
    }
    if (tag.includes('government') || tag.includes('格支配')) {
      match = chapters.find(c => c.tag_id === 'verb.government');
      if (match) return match.tag_id;
    }
    if (tag.includes('fleeting') || tag.includes('出没音')) {
      match = chapters.find(c => c.tag_id === 'noun.irregular_fleeting');
      if (match) return match.tag_id;
    }
    if (tag.includes('soft_sign') || tag.includes('-ь')) {
      match = chapters.find(c => c.tag_id === 'noun.soft_sign');
      if (match) return match.tag_id;
    }

    // Case heuristics
    const caseMatch = tag.match(/case\.(nom|gen|dat|acc|ins|prp)/);
    if (caseMatch) {
      const cTag = `case.${caseMatch[1]}`;
      match = chapters.find(c => c.tag_id === cTag);
      if (match) return match.tag_id;
    }

    // 4. Prefix or containment fallback
    match = chapters.find(c => tag.startsWith(c.tag_id) || c.tag_id.startsWith(tag));
    if (match) return match.tag_id;

    return null;
  }

  render() {
    if (!this.data || !this.sidebar || !this.reader) return;

    const chapters = this.getAllChapters();
    const resolved = this.resolveTagId(this.activeTagId);
    if (resolved) {
      this.activeTagId = resolved;
    } else if (chapters.length > 0 && !chapters.some(c => c.tag_id === this.activeTagId)) {
      console.warn(`[GrammarHandbook] Tag '${this.activeTagId}' not resolved to any chapter. Falling back to '${chapters[0].tag_id}'.`);
      this.activeTagId = chapters[0].tag_id;
    }

    this.renderSidebar();
    this.renderReader();

    // Auto-scroll sidebar active chapter into view and reset reader scroll
    setTimeout(() => {
      const activeItem = this.sidebar.querySelector(`.handbook-chap-item[data-tag-id="${this.activeTagId}"]`);
      if (activeItem) {
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (this.reader) {
        this.reader.scrollTop = 0;
      }
    }, 50);
  }

  renderSidebar(filterQuery = '') {
    const q = filterQuery.toLowerCase().trim();
    let html = `
      <div class="handbook-search-wrap">
        <input type="text" id="handbookSearchInput" class="handbook-search-input" placeholder="🔍 文法・格を検索..." value="${filterQuery}">
      </div>
      <div class="handbook-tree-list">
    `;

    (this.data.categories || []).forEach(cat => {
      const matchingChapters = (cat.chapters || []).filter(ch => {
        if (!q) return true;
        return ch.title.toLowerCase().includes(q) ||
               ch.subtitle.toLowerCase().includes(q) ||
               (ch.question && ch.question.toLowerCase().includes(q)) ||
               ch.tag_id.toLowerCase().includes(q);
      });

      if (matchingChapters.length === 0) return;

      html += `
        <div class="handbook-cat-group">
          <div class="handbook-cat-header">${cat.category_name}</div>
          <div class="handbook-chap-list">
            ${matchingChapters.map(ch => {
              const isActive = ch.tag_id === this.activeTagId;
              return `
                <div class="handbook-chap-item ${isActive ? 'active' : ''}" data-tag-id="${ch.tag_id}">
                  <span class="chap-item-title">${ch.title}</span>
                  <span class="chap-item-sub">${ch.question || ch.subtitle}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    });

    html += `</div>`;
    this.sidebar.innerHTML = html;

    // Attach search input listener
    const searchInput = this.sidebar.querySelector('#handbookSearchInput');
    if (searchInput) {
      searchInput.oninput = (e) => {
        this.renderSidebar(e.target.value);
        const newInp = this.sidebar.querySelector('#handbookSearchInput');
        if (newInp) {
          newInp.focus();
          newInp.setSelectionRange(newInp.value.length, newInp.value.length);
        }
      };
    }

    // Attach chapter click listeners
    this.sidebar.querySelectorAll('.handbook-chap-item').forEach(item => {
      item.onclick = () => {
        const tagId = item.dataset.tagId;
        if (tagId) {
          this.activeTagId = tagId;
          this.render();
        }
      };
    });
  }

  renderReader() {
    const chapters = this.getAllChapters();
    const resolved = this.resolveTagId(this.activeTagId);
    let current = chapters.find(c => c.tag_id === (resolved || this.activeTagId));
    if (!current && chapters.length > 0) {
      current = chapters[0];
      this.activeTagId = current.tag_id;
    }

    if (!current) {
      this.reader.innerHTML = `<div style="padding:30px; text-align:center; color:var(--text-muted);">章を選択してください。</div>`;
      return;
    }

    this.reader.innerHTML = `
      <div class="handbook-article">
        <!-- Article Top Banner -->
        <div class="handbook-article-header">
          <div style="display:flex; align-items:baseline; gap:10px; flex-wrap:wrap;">
            <span class="handbook-tag-pill">${current.tag_id}</span>
            <h2 class="handbook-article-title">${current.title}</h2>
            ${current.question ? `<span class="handbook-question-badge">${current.question}</span>` : ''}
          </div>
          <div class="handbook-article-subtitle">${current.subtitle}</div>
        </div>

        <!-- Tanya Concept Guidance -->
        <div class="handbook-tanya-box">
          <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="handbook-tanya-img">
          <div class="handbook-tanya-content">
            <div class="handbook-tanya-name">🎹 ターニャ先生のレクチャー</div>
            <div class="handbook-tanya-text">${current.tanya_intro}</div>
          </div>
        </div>

        <!-- Formation Guide & Step-by-Step Advice (作り方のアドバイス) -->
        ${current.formation_guide_html ? `
          <div class="handbook-section">
            ${current.formation_guide_html}
          </div>
        ` : ''}

        <!-- Declension / Conjugation Table -->
        <div class="handbook-section">
          <h3 class="handbook-section-heading">📊 基本語尾・変化一覧表</h3>
          <div class="handbook-table-wrap">
            ${current.table_html || '<p>表は準備中です</p>'}
          </div>
        </div>

        <!-- Moscow Conservatory Authentic Examples -->
        <div class="handbook-section">
          <h3 class="handbook-section-heading">🎼 モスクワ音楽院の実例（音声付き）</h3>
          <div class="handbook-examples-list">
            ${(current.conservatory_examples || []).map((ex, idx) => `
              <div class="handbook-example-card">
                <div class="example-top-row">
                  <span class="example-speaker-badge">🎹 ${ex.speaker || 'ターニャ'}</span>
                  ${ex.focus ? `<span class="example-focus-tag">${ex.focus}</span>` : ''}
                  <button class="example-play-btn" data-ru="${encodeURIComponent(ex.ru)}" title="音声を聴く (Svetlana)">
                    🔊 発音を聴く
                  </button>
                </div>
                <div class="example-ru-text">${ex.ru}</div>
                <div class="example-ja-text">${ex.ja}</div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Learner Pitfalls / Exam Traps -->
        ${current.pitfalls ? `
          <div class="handbook-pitfall-box">
            <div class="pitfall-header">
              <span class="pitfall-icon">⚠️</span>
              <span class="pitfall-title">日本人学習者の落とし穴・検定2級の急所</span>
            </div>
            <div class="pitfall-body">${current.pitfalls}</div>
          </div>
        ` : ''}

        <!-- Related Grammar Links -->
        ${current.related_tags && current.related_tags.length > 0 ? `
          <div class="handbook-related-box">
            <span class="related-label">🔗 関連する文法章:</span>
            <div class="related-buttons-row">
              ${current.related_tags.map(rt => {
                const relChapter = chapters.find(c => c.tag_id === rt);
                const label = relChapter ? relChapter.title : rt;
                return `
                  <button class="handbook-related-btn" data-tag-id="${rt}">
                    ${label} →
                  </button>
                `;
              }).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;

    // Attach example audio playback
    this.reader.querySelectorAll('.example-play-btn').forEach(btn => {
      btn.onclick = () => {
        const ru = decodeURIComponent(btn.dataset.ru || '');
        if (window.TTSPlayer && ru) {
          window.TTSPlayer.speakSentence(ru);
        }
      };
    });

    // Attach related tag click listeners
    this.reader.querySelectorAll('.handbook-related-btn').forEach(btn => {
      btn.onclick = () => {
        const tagId = btn.dataset.tagId;
        if (tagId) {
          this.activeTagId = tagId;
          this.render();
          this.reader.scrollTop = 0;
        }
      };
    });
  }
}

window.Handbook = new GrammarHandbook();
