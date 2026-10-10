/**
 * Tanya Russian Trainer - Salon Flashcard & Reflex Drill Engine
 * 
 * 音楽院サロンの世界観で、音・情景・コロケーション・シャドーイングを味わいながら
 * ノルマや罪悪感ゼロで3分（5〜7語）サクサクめくるフラッシュカード。
 * さらに、露検2級（B1）最重要の「-ь 名詞の性別仕分け特訓」モードを完全統合。
 * 完全PCキーボード操作対応（矢印キー、1/2/3、Space、Enter、R、C、S、H）。
 */

class SalonFlashcard {
  constructor() {
    this.mode = 'salon'; // 'salon' | 'soft_sign'
    this.sessionCards = [];
    this.currentIndex = 0;
    this.isFlipped = false;
    this.sessionRatings = {};
    this.isOpen = false;
    this.isComplete = false;

    // Cognitive enhancement states
    this.showStemHint = false;
    this.cardStartTime = 0;
    this.fermaataCount = 0;
    this.isReciting = false;
    this.sessionExpAwarded = false;
    this.acousticPrimingTimer = null;

    // Soft-sign drill state
    this.drillCards = [];
    this.drillIndex = 0;
    this.drillAnswered = false;
    this.drillChosen = null;
    this.drillScore = 0;
    this.drillHistory = [];

    this.tanyaEncouragements = [
      "大丈夫、何十回も忘れていいの！ピアノの鍵盤と同じで、触れるたびに指と耳が覚えていくからね♪",
      "焦らなくて大丈夫。音の響きをそのまま身体に染み込ませていきましょう☕",
      "響きを声に出してみて！ロシア語の音楽的なリズムが口に馴染んできた証拠よ✨",
      "アリョーナも最初の頃は何度も楽譜を見返していたのよ。一歩ずつ、音を楽しんで♪",
      "忘れるのは脳が新しい音を受け入れる準備をしている証拠。いつでもまた出会えばいいのよ！",
      "今日の練習室の光、とても綺麗ね。ピアノの余韻と一緒に言葉の響きを味わって☕",
      "素晴らしい集中力！このペースで、心地よく音と触れ合っていきましょうね🎹",
      "耳を澄ませて、アリョーナのピアノの響きと一緒に言葉を口ずさんでみて♪"
    ];

    // Curated high-frequency / 2027 Grade 2 -ь nouns bank
    this.softSignDrillBank = [
      {
        word: "рояль",
        gender: "m",
        meaning: "グランドピアノ",
        rule: "音楽院の主役 «рояль» は男性名詞！生格は рояля、造格は роялем と軟子音格変化します。",
        scene: "大ホールの舞台中央に置かれた漆黒のスタインウェイ・グランドピアノ"
      },
      {
        word: "память",
        gender: "f",
        meaning: "記憶、想い出",
        rule: "«память» は女性名詞！第3変化名詞として生・与・前置格すべて -и、造格は памятью となります。",
        scene: "ラフマニノフが愛した旋律を胸の内に呼び起こす静かな時間"
      },
      {
        word: "радость",
        gender: "f",
        meaning: "喜び",
        rule: "【100%の鉄則】語尾 -ость / -есть は例外なく100%女性名詞！",
        scene: "難曲のパッセージを弾き終えた瞬間に溢れ出るアリョーナの笑み"
      },
      {
        word: "словарь",
        gender: "m",
        meaning: "辞書、語彙集",
        rule: "【100%の鉄則】語尾 -тель / -арь は例外なく100%男性名詞！",
        scene: "譜面台の脇に開かれた厚い露和音楽用語辞典"
      },
      {
        word: "преподаватель",
        gender: "m",
        meaning: "大学・音楽院の教員・講師",
        rule: "【100%の鉄則】行為者を表す -тель 語尾は100%男性名詞！",
        scene: "熱心に指のタッチと呼吸を指導するターニャ先生の真剣な眼差し"
      },
      {
        word: "ночь",
        gender: "f",
        meaning: "夜",
        rule: "【100%の鉄則】ヒソヒソ音（ж, ч, ш, щ）の後に軟音記号 -ь がつく単語は100%女性名詞！",
        scene: "静まり返ったモスクワ音楽院の窓の外に広がる深い夜の気配"
      },
      {
        word: "вещь",
        gender: "f",
        meaning: "物、事柄、作品",
        rule: "【100%の鉄則】ヒソヒソ音 щ ＋ ь は100%女性名詞！",
        scene: "アリョーナが大切に楽譜ケースにしまっている宝物の自筆譜"
      },
      {
        word: "путь",
        gender: "m",
        meaning: "道、歩み、途上",
        rule: "【超重要例外】格変化語尾は女性第3変化型（пути, путём）ですが、性は【男性名詞】！2級必出の要注意語。",
        scene: "音楽家として生涯をかけて極めていく長く美しい芸術の道"
      },
      {
        word: "жизнь",
        gender: "f",
        meaning: "人生、生活、命",
        rule: "«жизнь» は女性名詞！生格 жизни, 造格 жизнью。日常生活から哲学まで最頻出語彙です。",
        scene: "一音一音に魂を吹き込み、作品に新たな命を吹き込むピアニスト"
      },
      {
        word: "день",
        gender: "m",
        meaning: "日、昼",
        rule: "«день» は男性名詞！生格以降は出没音 e が脱落して «дня, дню, днём» と変化します。",
        scene: "朝の光が練習室のピアノの鍵盤を白く照らし出す新しい一日"
      },
      {
        word: "любовь",
        gender: "f",
        meaning: "愛、慈しみ",
        rule: "«любовь» は女性名詞！生格以降は出没音 o が脱落して «любви, любовью» となります。",
        scene: "チャイコフスキーが音楽へのあふれる愛情を込めて紡いだ旋律"
      },
      {
        word: "дождь",
        gender: "m",
        meaning: "雨",
        rule: "天候の «дождь» は男性名詞！生格 дождя, 造格 дождём。",
        scene: "モスクワの古い街並みと音楽院の屋根を静かに濡らす秋の雨音"
      },
      {
        word: "площадь",
        gender: "f",
        meaning: "広場、面積",
        rule: "«Красная площадь (赤の広場)» でおなじみの女性名詞！生格 площади, 造格 площадью。",
        scene: "クレムリンの鐘の音が響き渡るモスクワの中心、赤の広場"
      },
      {
        word: "январь",
        gender: "m",
        meaning: "1月",
        rule: "【100%の鉄則】ロシア語の月名（-ьで終わるもの）はすべて100%男性名詞！",
        scene: "窓ガラスに氷の結晶が花のように咲く凍てつくモスクワの1月"
      },
      {
        word: "дверь",
        gender: "f",
        meaning: "ドア、扉",
        rule: "«дверь» は女性名詞！生・与・前置格 двери, 造格 дверью。",
        scene: "練習室の重い防音扉の向こうから漏れ聴こえるラフマニノフの協奏曲"
      },
      {
        word: "рубль",
        gender: "m",
        meaning: "ルーブル (ロシア通貨)",
        rule: "通貨の «рубль» は男性名詞！生格 рубля, 造格 рублём。",
        scene: "音楽院近くの古本屋で古い楽譜を買うときに支払う銀のコイン"
      },
      {
        word: "тетрадь",
        gender: "f",
        meaning: "ノート、五線譜ノート",
        rule: "«нотная тетрадь (楽譜ノート)» は女性名詞！生格 тетради, 造格 тетрадью。",
        scene: "アリョーナの手書きの運指やターニャ先生の赤ペンが並ぶ五線譜ノート"
      },
      {
        word: "спектакль",
        gender: "m",
        meaning: "演劇、公演、舞台",
        rule: "芸術・舞台の «спектакль» は男性名詞！生格 спектакля, 造格 спектаклем。",
        scene: "ボリショイ劇場の幕が上がり、熱気あふれる拍手に包まれる舞台"
      },
      {
        word: "гость",
        gender: "m",
        meaning: "客、来客",
        rule: "«гость» は男性名詞！生格 гостя, 造格 гостем。複数は гости, гостей。",
        scene: "演奏会終演後、楽屋へ花束を持って駆けつけてくれた温かい聴衆"
      },
      {
        word: "свежесть",
        gender: "f",
        meaning: "新鮮さ、清々しさ",
        rule: "【100%の鉄則】接尾辞 -ость / -есть は100%女性名詞！",
        scene: "雨上がりのサロンに吹き抜ける、菩提樹の若葉の清々しい風"
      },
      {
        word: "автомобиль",
        gender: "m",
        meaning: "自動車",
        rule: "乗り物の «автомобиль» は男性名詞！生格 автомобиля, 造格 автомобилем。",
        scene: "雪の降るモスクワの大通りをライトを点けて走り去る車"
      },
      {
        word: "осень",
        gender: "f",
        meaning: "秋",
        rule: "四季の «осень» は女性名詞！生格 осени, 造格 осенью (副詞的に「秋に」)。",
        scene: "黄金色に染まった落ち葉が音楽院の中庭を美しく舞う秋の午後"
      },
      {
        word: "стиль",
        gender: "m",
        meaning: "スタイル、様式、流儀",
        rule: "音楽様式の «стиль» は男性名詞！生格 стиля, 造格 стилем。",
        scene: "古典派からロマン派、ロシア近代音楽へと受け継がれる演奏の流儀"
      },
      {
        word: "помощь",
        gender: "f",
        meaning: "助け、支援、援助",
        rule: "【100%の鉄則】ヒソヒソ音 щ ＋ ь は100%女性名詞！",
        scene: "弾き方に悩んだとき、そっと隣で連弾して導いてくれるターニャ先生の助け"
      }
    ];
  }

  /**
   * Switch between Salon Flashcard and Soft-Sign Reflex Drill modes
   */
  switchMode(newMode) {
    if (newMode === 'soft_sign') {
      this.startSoftSignDrill(10);
    } else {
      this.startSession(6);
    }
  }

  /**
   * Start a new flashcard session with 5-7 prioritized words
   */
  async startSession(count = 6) {
    this.mode = 'salon';
    const modal = document.getElementById('flashcardModal');
    if (!modal) return;

    // Close bookmarks modal if currently open
    const bookmarksModal = document.getElementById('bookmarksModal');
    if (bookmarksModal && bookmarksModal.classList.contains('open')) {
      bookmarksModal.classList.remove('open');
    }

    this.modal = modal;
    modal.classList.add('open');
    this.isOpen = true;
    this.isComplete = false;
    this.isFlipped = false;
    this.currentIndex = 0;
    this.sessionRatings = {};

    // Reset cognitive states
    this.showStemHint = false;
    this.cardStartTime = 0;
    this.fermaataCount = 0;
    this.isReciting = false;
    this.sessionExpAwarded = false;

    const container = document.getElementById('flashcardContainer');
    if (container) {
      container.innerHTML = '<div class="flash-loading">サロンの楽譜を準備しています...☕</div>';
    }

    // Fetch bookmarks
    const data = await window.API.getBookmarks();
    const bookmarks = data?.bookmarks || [];

    if (!bookmarks || bookmarks.length === 0) {
      this.renderEmptyState(container);
      return;
    }

    const sorted = [...bookmarks].sort((a, b) => {
      const levelA = a.mastery_level || 1;
      const levelB = b.mastery_level || 1;
      if (levelA !== levelB) return levelA - levelB;

      const revA = a.review_count || 0;
      const revB = b.review_count || 0;
      if (revA !== revB) return revA - revB;

      const timeA = a.last_reviewed_at || '';
      const timeB = b.last_reviewed_at || '';
      return timeA.localeCompare(timeB);
    });

    const pool = sorted.slice(0, Math.min(12, sorted.length));
    const shuffled = pool.sort(() => 0.5 - Math.random());
    this.sessionCards = shuffled.slice(0, Math.min(count, shuffled.length));

    // Enrich sampled session cards with dictionary data, anatomy, smart table, and cloze
    await Promise.all(this.sessionCards.map(async (card) => {
      try {
        if (window.API) {
          const results = await window.API.searchVocabulary(card.word, card.base || '');
          if (results && results.length > 0) {
            const entry = results.find(r => r.word.toLowerCase() === card.word.toLowerCase() || (card.base && r.word.toLowerCase() === card.base.toLowerCase())) || results[0];
            if (entry) {
              if (!card.anatomy && entry.anatomy) card.anatomy = entry.anatomy;
              if (!card.declension_table && entry.declension_table) card.declension_table = entry.declension_table;
              if (!card.network && entry.network) card.network = entry.network;
              if (!card.collocation_ru && entry.examples && entry.examples.length > 0) {
                card.collocation_ru = entry.examples[0].ru;
                card.collocation_ja = entry.examples[0].ja;
              }
            }
          }
        }
      } catch (err) {
        console.warn('Enriching card error for', card.word, err);
      }

      if (!card.collocation_ru && card.example_ru) {
        card.collocation_ru = card.example_ru;
        card.collocation_ja = card.example_ja;
      }

      if (!card.collocation_cloze) {
        const sourceText = card.collocation_ru || card.example_ru || card.word || '';
        const safeWord = String(card.word || '').trim();
        const escaped = safeWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        try {
          if (escaped && sourceText.toLowerCase().includes(safeWord.toLowerCase())) {
            card.collocation_cloze = sourceText.replace(new RegExp(escaped, 'gi'), '[ ❓ ]');
          } else {
            card.collocation_cloze = `« [ ❓ ] »`;
          }
        } catch (_) {
          card.collocation_cloze = `« [ ❓ ] »`;
        }
      }
    }));

    this.renderCurrentCard();
  }

  /**
   * Start the -ь Noun Gender Reflex Drill
   */
  startSoftSignDrill(count = 10) {
    this.mode = 'soft_sign';
    const modal = document.getElementById('flashcardModal');
    if (!modal) return;

    const bookmarksModal = document.getElementById('bookmarksModal');
    if (bookmarksModal && bookmarksModal.classList.contains('open')) {
      bookmarksModal.classList.remove('open');
    }

    modal.classList.add('open');
    this.isOpen = true;
    this.isComplete = false;
    this.drillIndex = 0;
    this.drillAnswered = false;
    this.drillChosen = null;
    this.drillScore = 0;
    this.drillHistory = [];

    // Shuffle and sample
    const pool = [...this.softSignDrillBank].sort(() => 0.5 - Math.random());
    this.drillCards = pool.slice(0, Math.min(count, pool.length));

    this.renderSoftSignCard();
  }

  getCurrentDrillCard() {
    return this.drillCards[this.drillIndex] || null;
  }

  renderModeTabsHtml() {
    return `
      <div class="flash-mode-tabs">
        <button class="flash-mode-tab ${this.mode === 'salon' ? 'active' : ''}" onclick="window.SalonFlashcard.switchMode('salon')">
          ☕ 音楽院サロン (単語帳 5〜7語)
        </button>
        <button class="flash-mode-tab ${this.mode === 'soft_sign' ? 'active' : ''}" onclick="window.SalonFlashcard.switchMode('soft_sign')">
          ⚡ -ь 名詞の性別仕分け特訓 (2級直結)
        </button>
      </div>
    `;
  }

  renderEmptyState(container) {
    if (!container) return;
    container.innerHTML = `
      <div class="flash-empty-state">
        ${this.renderModeTabsHtml()}
        <div class="flash-empty-icon">⚡</div>
        <div class="flash-empty-title">単語帳はまだ空ですが、特訓を今すぐ始められます！</div>
        <div class="flash-empty-desc">
          露検2級（B1）最難関の<strong>「-ь 語尾名詞の性別仕分け特訓」</strong>は、<br>
          単語帳の登録に関係なく、今すぐテンポよく反射神経を鍛えられます。
        </div>
        <div style="display:flex; justify-content:center; gap:12px; margin-top:16px;">
          <button class="action-btn flash-restart-btn" onclick="window.SalonFlashcard.startSoftSignDrill(10)">
            <span>⚡ -ь 性別仕分け特訓を開始する (10問)</span>
            <kbd class="kbd-badge" style="font-size:0.75rem; margin-left:6px;">Enter / 1</kbd>
          </button>
          <button class="action-btn flash-close-btn-action" onclick="window.SalonFlashcard.close()">
            閉じる [Esc]
          </button>
        </div>
      </div>
    `;
  }

  getCurrentCard() {
    return this.sessionCards[this.currentIndex] || null;
  }

  getRandomTanyaMessage() {
    const idx = Math.floor(Math.random() * this.tanyaEncouragements.length);
    return this.tanyaEncouragements[idx];
  }

  /**
   * Render the current card (front or back) for Salon mode
   */
  renderCurrentCard() {
    const container = document.getElementById('flashcardContainer');
    if (!container) return;

    this.stopTableRecitation();
    this.showStemHint = false;
    this.cardStartTime = Date.now();

    const card = this.getCurrentCard();
    if (!card) {
      this.renderCompletionScreen();
      return;
    }

    const total = this.sessionCards.length;
    const progressPercent = Math.round(((this.currentIndex) / total) * 100);
    const tanyaMsg = card._tanyaMsg || (card._tanyaMsg = this.getRandomTanyaMessage());

    const masteryBadge = (level) => {
      if (level === 3) return '<span class="mastery-pill level-3">🌸 染み込み</span>';
      if (level === 2) return '<span class="mastery-pill level-2">🌿 耳慣れ</span>';
      return '<span class="mastery-pill level-1">🌱 馴染み中</span>';
    };

    const softSignBadge = window.renderSoftSignGenderBadge
      ? window.renderSoftSignGenderBadge(card.word, card.base, card.pos, card.meaning)
      : '';

    container.innerHTML = `
      <div class="flash-card-wrapper">
        ${this.renderModeTabsHtml()}

        <!-- Progress Header -->
        <div class="flash-header-row">
          <div class="flash-salon-title">
            <span class="flash-salon-icon">☕</span>
            <span class="flash-salon-name">音楽院サロン・フラッシュ</span>
            <span class="flash-step-indicator">第 ${this.currentIndex + 1} / ${total} 語</span>
          </div>
          <div class="flash-header-actions">
            <button class="flash-nav-btn" onclick="window.SalonFlashcard.prevCard()" title="前のカード (P)">◀ [P]</button>
            <button class="flash-nav-btn" onclick="window.SalonFlashcard.nextCard()" title="スキップ (N)">[N] ▶</button>
            <button class="modal-close-btn" onclick="window.SalonFlashcard.close()" title="終了 (Esc)">&times;</button>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="flash-progress-bar-bg">
          <div class="flash-progress-bar-fill" style="width: ${progressPercent}%;"></div>
        </div>

        <!-- Main 3D Card Box -->
        <div class="flash-card-box ${this.isFlipped ? 'flipped' : ''}">
          
          <!-- FRONT FACE -->
          <div class="flash-face flash-front ${!this.isFlipped ? 'active' : ''}">
            <div class="flash-scene-badge">
              <span class="scene-icon">🏛️</span>
              <span class="scene-text">${card.alena_scene || 'モスクワ音楽院の練習室にて'}</span>
            </div>

            <div class="flash-front-meta">
              <span class="flash-pos-badge">${card.pos || '重要語彙'}</span>
              ${masteryBadge(card.mastery_level || 1)}
            </div>

            <div class="flash-cloze-box">
              <div class="flash-cloze-heading ru-text">${card.collocation_cloze || '[ ❓ ]'}</div>
              <div class="flash-cloze-hint">${card.collocation_ja || card.meaning || ''}</div>
            </div>

            <!-- Micro-Hints Bar (Generation Clues: 語根 & 音の頭出し) -->
            <div class="flash-microhints-bar">
              <button class="flash-hint-toggle-btn ${this.showStemHint ? 'active' : ''}" id="flashStemHintBtn" onclick="window.SalonFlashcard.toggleStemHint()" title="語根・形態素ヒント (H)">
                <span>💡 語根ヒント</span>
                <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:2px;">H</kbd>
              </button>
              <button class="flash-priming-btn" id="flashPrimingBtn" onclick="window.SalonFlashcard.primeAcousticSound()" title="音の出だしをチラ聴き (A)">
                <span>🔊 音の頭出し</span>
                <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:2px;">A</kbd>
              </button>
              <div id="flashAcousticBadgeContainer"></div>
            </div>

            <!-- Collapsible Stem / Morphology Hint Box -->
            <div class="flash-stem-hint-box" id="flashStemHintBox" style="display: ${this.showStemHint ? 'block' : 'none'};">
              <div class="flash-stem-hint-header">
                <span>💡 語根・形態素ヒント (Generation Clue)</span>
                <button class="hint-close-mini" onclick="window.SalonFlashcard.toggleStemHint(false)">&times;</button>
              </div>
              <div class="flash-stem-hint-body">
                ${this.getStemHintHtml(card)}
              </div>
            </div>

            <div class="flash-front-actions">
              <button class="flash-action-audio-btn" onclick="window.SalonFlashcard.speakCurrentWord()">
                <span class="audio-icon">🔊</span>
                <span>単語の発音を聴く</span>
                <span class="shortcut-key">R</span>
              </button>
              
              <button class="flash-action-flip-btn" onclick="window.SalonFlashcard.flip()">
                <span class="flip-icon">🔄</span>
                <span>情景と答えをひらく</span>
                <span class="shortcut-key">Space / Enter</span>
              </button>
            </div>
          </div>

          <!-- BACK FACE -->
          <div class="flash-face flash-back ${this.isFlipped ? 'active' : ''}">
            <!-- Word Header -->
            <div class="flash-back-header">
              <div class="flash-word-title-row">
                <span class="flash-word-main ru-text">${card.word}</span>
                ${softSignBadge}
                <button class="flash-mini-speaker-btn" onclick="window.SalonFlashcard.speakCurrentWord()" title="単語を再試聴 (R)">🔊 [R]</button>
              </div>
              <div class="flash-word-meaning-row">
                <span class="flash-back-pos">${card.pos || ''}</span>
                <span class="flash-back-meaning">${card.meaning || ''}</span>
              </div>
            </div>

            <!-- Collocation Chunk -->
            <div class="flash-collocation-showcase">
              <div class="flash-col-ru ru-text">${card.collocation_ru || card.word}</div>
              <div class="flash-col-ja">${card.collocation_ja || card.meaning || ''}</div>
              <button class="flash-col-speaker-btn" onclick="window.SalonFlashcard.speakCollocation()" title="コロケーションを聴く (C)">
                <span>🔊 フレーズを聴く</span>
                <span class="shortcut-key" style="margin-left: 4px;">C</span>
              </button>
            </div>

            <!-- Alena's Scene & Sentence -->
            <div class="flash-alena-scene-box">
              <div class="flash-alena-tag">
                <span class="alena-avatar">🎹</span>
                <span class="alena-label">アリョーナの情景</span>
                <button class="flash-sentence-speaker-btn" onclick="window.SalonFlashcard.speakSentence()" title="例文を聴く (S)">
                  <span>🔊 例文を聴く</span>
                  <span class="shortcut-key" style="margin-left: 4px;">S</span>
                </button>
              </div>
              <div class="flash-alena-quote ru-text">«${card.example_ru || card.word}»</div>
              <div class="flash-alena-trans">「${card.example_ja || card.meaning}」</div>
            </div>

            <!-- Vocal Shadowing & Trinity Recitation Bar -->
            <div class="flash-trinity-finish-bar">
              <div class="trinity-vocal-prompt">
                <span class="vocal-icon">🗣️</span>
                <span class="vocal-text">声に出して調音（口の動き）と音の響きを身体に馴染ませましょう</span>
              </div>
              <div class="trinity-buttons-row">
                <button class="flash-recite-table-btn ${this.isReciting ? 'playing' : ''}" id="flashReciteTableBtn" onclick="window.SalonFlashcard.toggleTableRecitation()" title="活用・格変化を連続朗読 (T)">
                  <span class="recite-icon">${this.isReciting ? '⏸' : '🎹'}</span>
                  <span>${this.isReciting ? '朗読停止' : '活用・格変化を連続朗読'}</span>
                  <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:4px;">T</kbd>
                </button>
              </div>
              <div id="flashReciteLiveBannerContainer"></div>
            </div>

            <!-- Tanya's Warm Encouragement Bubble -->
            <div class="flash-tanya-bubble">
              <div class="tanya-bubble-header">
                <span class="tanya-avatar">👩‍🏫</span>
                <span class="tanya-name">ターニャ先生</span>
              </div>
              <div class="tanya-bubble-text">${tanyaMsg}</div>
            </div>

            <!-- Self Rating Buttons (1, 2, 3) -->
            <div class="flash-rating-container">
              <div class="flash-rating-intro">
                <span>馴染み度を選んで次へ（キー 1, 2, 3 または N）:</span>
                <span class="rate-default-pill">※ [N] は自動で「1: 馴染み中」になります</span>
              </div>
              <div class="flash-rating-grid">
                <button class="flash-rate-card-btn rate-btn-1" onclick="window.SalonFlashcard.rateAndAdvance(1)" title="キー 1 または N で次へ">
                  <div class="rate-top">
                    <span class="rate-badge-key">1 / N</span>
                    <span class="rate-badge-label">🌱 馴染み中</span>
                  </div>
                  <div class="rate-bottom-desc">基本はここ（何十回も忘れてOK）</div>
                </button>

                <button class="flash-rate-card-btn rate-btn-2" onclick="window.SalonFlashcard.rateAndAdvance(2)" title="キー 2 で次へ">
                  <div class="rate-top">
                    <span class="rate-badge-key">2</span>
                    <span class="rate-badge-label">🌿 耳慣れてきた</span>
                  </div>
                  <div class="rate-bottom-desc">少しずつ身体に染みてきた</div>
                </button>

                <button class="flash-rate-card-btn rate-btn-3" onclick="window.SalonFlashcard.rateAndAdvance(3)" title="キー 3 で次へ">
                  <div class="rate-top">
                    <span class="rate-badge-key">3</span>
                    <span class="rate-badge-label">🌸 染み込んだ！</span>
                  </div>
                  <div class="rate-bottom-desc">自然に音と意味が浮かぶ</div>
                </button>
              </div>
            </div>

          </div>

        </div>

        <!-- Footer Key Navigation Hint -->
        <div class="flash-footer-hint">
          <span>[Space / Enter]: ${this.isFlipped ? '次へ進む' : 'めくる'}</span>
          <span>[H]: 語根ヒント</span>
          <span>[A]: 音頭出し</span>
          <span>[R]: 単語</span>
          <span>[C]: フレーズ</span>
          <span>[S]: 例文</span>
          <span>[T]: 活用朗読</span>
          <span>[1-3]: 馴染み度セレクト</span>
          <span>[P / N]: 前後移動</span>
          <span>[Esc]: サロンへ戻る</span>
        </div>
      </div>
    `;

    if (!this.isFlipped) {
      this.speakCurrentWord();
    }
  }

  /**
   * Render the current card for -ь Noun Gender Reflex Drill
   */
  renderSoftSignCard() {
    const container = document.getElementById('flashcardContainer');
    if (!container) return;

    const card = this.getCurrentDrillCard();
    if (!card) {
      this.renderSoftSignCompletionScreen();
      return;
    }

    const total = this.drillCards.length;
    const progressPercent = Math.round(((this.drillIndex) / total) * 100);

    const isAnswered = this.drillAnswered;
    const chosen = this.drillChosen;
    const isCorrect = isAnswered && (chosen === card.gender);

    container.innerHTML = `
      <div class="flash-card-wrapper">
        ${this.renderModeTabsHtml()}

        <!-- Progress Header -->
        <div class="flash-header-row">
          <div class="flash-salon-title">
            <span class="flash-salon-icon">⚡</span>
            <span class="flash-salon-name">-ь 名詞の性別仕分け特訓</span>
            <span class="flash-step-indicator">第 ${this.drillIndex + 1} / ${total} 語 (正解: ${this.drillScore})</span>
          </div>
          <div class="flash-header-actions">
            <button class="modal-close-btn" onclick="window.SalonFlashcard.close()" title="終了 (Esc)">&times;</button>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="flash-progress-bar-bg">
          <div class="flash-progress-bar-fill" style="width: ${progressPercent}%;"></div>
        </div>

        <!-- Main Card Box -->
        <div class="flash-card-box">
          <div class="flash-face flash-front active" style="min-height: 380px;">
            <div class="flash-scene-badge">
              <span class="scene-icon">🏛️</span>
              <span class="scene-text">${card.scene}</span>
            </div>

            <!-- Target Word -->
            <div style="text-align:center; margin: 18px 0 10px;">
              <div style="display:flex; justify-content:center; align-items:center; gap:12px;">
                <span class="ru-text" style="font-size:2.6rem; font-weight:800; color:#ffffff; letter-spacing:0.02em;">
                  ${card.word}
                </span>
                <button class="flash-mini-speaker-btn" onclick="window.SalonFlashcard.speakCurrentWord()" title="発音を聴く (R)" style="font-size:1.1rem; padding:4px 8px;">
                  🔊 <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:2px;">R</kbd>
                </button>
              </div>
              <div style="font-size:1.05rem; color:#ffe599; font-weight:600; margin-top:6px;">
                🇯🇵 ${card.meaning}
              </div>
            </div>

            ${!isAnswered ? `
              <!-- Choice Buttons (Unanswered) -->
              <div style="text-align:center; margin-top:10px; font-size:0.92rem; color:var(--text-muted);">
                Q: この名詞の性はどっち？ 瞬時に判断してみましょう！
              </div>
              <div class="flash-drill-choice-grid">
                <button class="flash-drill-choice-btn choice-m" onclick="window.SalonFlashcard.submitSoftSignAnswer('m')">
                  <span>男性名詞 (m ♂)</span>
                  <span class="choice-kbd">[1] または [◀ 左矢印]</span>
                </button>
                <button class="flash-drill-choice-btn choice-f" onclick="window.SalonFlashcard.submitSoftSignAnswer('f')">
                  <span>女性名詞 (f ♀)</span>
                  <span class="choice-kbd">[2] または [右矢印 ▶]</span>
                </button>
              </div>
            ` : `
              <!-- Feedback & Rule Card (Answered) -->
              ${isCorrect ? `
                <div class="quiz-thought-step-card" style="margin-top:12px;">
                  <div class="step-title">
                    <span>✨ 正解！【${card.gender === 'm' ? '男性名詞 (m ♂)' : '女性名詞 (f ♀)'}】</span>
                  </div>
                  <div>${card.rule}</div>
                </div>
              ` : `
                <div class="quiz-trap-analysis-card" style="margin-top:12px;">
                  <div class="trap-title">
                    <span>⚠️ 惜しい！実は【${card.gender === 'm' ? '男性名詞 (m ♂)' : '女性名詞 (f ♀)'}】です</span>
                  </div>
                  <div>${card.rule}</div>
                </div>
              `}

              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; flex-wrap:wrap; gap:8px;">
                <div class="handbook-link-badge" onclick="window.Handbook && window.Handbook.openTag('noun.soft_sign')" title="文法ハンドブックを開く (H)">
                  <span>📖 文法ハンドブック「-ь 語尾名詞の性別」で確認 →</span>
                  <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:4px;">H</kbd>
                </div>
                <button class="quiz-next-btn" onclick="window.SalonFlashcard.nextSoftSignCard()" style="min-width:180px; justify-content:center;">
                  <span>次へ進む</span>
                  <kbd class="kbd-badge">Space / Enter / N</kbd>
                </button>
              </div>
            `}

          </div>
        </div>

        <!-- Footer Key Navigation Hint -->
        <div class="flash-footer-hint">
          ${!isAnswered ? `
            <span>[1 / ◀ 左]: 男性名詞</span>
            <span>[2 / ▶ 右]: 女性名詞</span>
            <span>[R]: 音声再試聴</span>
            <span>[Esc]: 終了</span>
          ` : `
            <span>[Space / Enter / N]: 次へ進む</span>
            <span>[H]: ハンドブック</span>
            <span>[R]: 音声</span>
            <span>[Esc]: 終了</span>
          `}
        </div>
      </div>
    `;

    if (!isAnswered) {
      this.speakCurrentWord();
    }
  }

  /**
   * Submit an answer for soft-sign noun drill
   */
  submitSoftSignAnswer(chosenGender) {
    if (this.drillAnswered) return;
    const card = this.getCurrentDrillCard();
    if (!card) return;

    this.drillChosen = chosenGender;
    this.drillAnswered = true;
    const isCorrect = (chosenGender === card.gender);
    if (isCorrect) {
      this.drillScore++;
    }
    this.drillHistory.push({ card, chosen: chosenGender, isCorrect });

    if (window.TTSPlayer) {
      window.TTSPlayer.speakWord(card.word);
    }

    this.renderSoftSignCard();
  }

  /**
   * Advance to next card in soft-sign drill
   */
  nextSoftSignCard() {
    if (this.drillIndex < this.drillCards.length - 1) {
      this.drillIndex++;
      this.drillAnswered = false;
      this.drillChosen = null;
      this.renderSoftSignCard();
    } else {
      this.renderSoftSignCompletionScreen();
    }
  }

  /**
   * Render Tea Time Completion for Soft-Sign Drill
   */
  renderSoftSignCompletionScreen() {
    this.isComplete = true;
    const container = document.getElementById('flashcardContainer');
    if (!container) return;

    const total = this.drillCards.length;
    const percent = Math.round((this.drillScore / total) * 100);

    let quoteMsg = "";
    if (percent === 100) {
      quoteMsg = "«Браво! 完璧な反射神経ね！» -ь名詞の性別の響きが、あなたの耳と身体にしっかり染み込んでいますよ♪";
    } else if (percent >= 70) {
      quoteMsg = "«Прекрасно! 素晴らしい判断力です！» 迷いやすい重要名詞も、この調子で音と一緒に定着させていきましょう☕";
    } else {
      quoteMsg = "«大丈夫、何十回も忘れていいの！» ピアノの難所と同じで、触れるたびに指と耳が覚えていきます。温かい紅茶を淹れて、少し休みましょうね☕";
    }

    container.innerHTML = `
      <div class="flash-complete-wrapper">
        ${this.renderModeTabsHtml()}

        <div class="tea-atmosphere-icon">⚡🎹</div>
        <h2 class="tea-complete-title">モスクワ音楽院サロンのティータイム（-ь 性別特訓 完了）</h2>
        
        <div style="text-align:center; font-size:1.25rem; font-weight:700; color:var(--gold-light); margin-bottom:12px;">
          本日特訓の結果: <strong>${total}問中 ${this.drillScore}問 正解！ (${percent}%)</strong>
        </div>

        <div class="tea-tanya-message-box">
          <div class="tanya-avatar-lg">👩‍🏫</div>
          <div class="tea-tanya-content">
            <div class="tanya-label">ターニャ先生より</div>
            <div class="tanya-tea-quote">${quoteMsg}</div>
          </div>
        </div>

        <div class="tea-summary-section">
          <div class="tea-summary-header">本日特訓した -ь 名詞の性別一覧</div>
          <div class="tea-summary-grid">
            ${this.drillCards.map(c => {
              const hist = this.drillHistory.find(h => h.card.word === c.word);
              const isCorrect = hist ? hist.isCorrect : false;
              const gBadge = c.gender === 'm'
                ? '<span class="badge-gender-m">m ♂ (男性)</span>'
                : '<span class="badge-gender-f">f ♀ (女性)</span>';

              return `
                <div class="tea-word-card" style="border-left: 3px solid ${isCorrect ? 'var(--emerald)' : 'var(--crimson)'};">
                  <div class="tea-word-top">
                    <span class="tea-word-ru ru-text">${c.word}</span>
                    ${gBadge}
                    <button class="tea-word-play-btn" onclick="window.TTSPlayer && window.TTSPlayer.speakWord('${c.word}')">🔊</button>
                  </div>
                  <div class="tea-word-ja" style="margin-top:4px;">${c.meaning}</div>
                  <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px; line-height:1.4;">
                    ${isCorrect ? '✔ 正解' : '⚠️ 要復習'}: ${c.rule.slice(0, 40)}...
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <div class="tea-complete-actions">
          <button class="action-btn flash-restart-btn" onclick="window.SalonFlashcard.startSoftSignDrill(10)">
            <span>⚡ もう10問特訓する</span>
            <span class="shortcut-key">F / Enter</span>
          </button>
          <button class="action-btn" onclick="window.Handbook && window.Handbook.openTag('noun.soft_sign')" style="background:rgba(99,102,241,0.2); border:1px solid #6366f1; color:#c7d2fe;">
            <span>📖 文法ハンドブックで復習</span>
            <span class="shortcut-key">H</span>
          </button>
          <button class="action-btn flash-back-bm-btn" onclick="window.SalonFlashcard.close(true)">
            <span>単語帳一覧に戻る</span>
            <span class="shortcut-key">Esc</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Flip card to back & trigger Trinity auto-play
   */
  flip() {
    if (this.isFlipped) return;
    this.isFlipped = true;
    this.renderCurrentCard();
    // Auto-play collocation phrase for trinity finish
    setTimeout(() => {
      this.speakCollocation();
    }, 120);
  }

  /**
   * Speak current card word via TTS
   */
  speakCurrentWord() {
    const card = this.mode === 'soft_sign' ? this.getCurrentDrillCard() : this.getCurrentCard();
    if (!card || !window.TTSPlayer) return;
    const btn = document.querySelector('.flash-mini-speaker-btn') || document.querySelector('.flash-action-audio-btn');
    if (btn) btn.classList.add('speaking');
    window.TTSPlayer.speakWord(card.word, () => {
      if (btn) btn.classList.remove('speaking');
    });
  }

  /**
   * Speak current card Russian example sentence
   */
  speakSentence() {
    const card = this.getCurrentCard();
    if (!card || !window.TTSPlayer) return;
    const sent = card.example_ru || card.collocation_ru || card.word;
    const btn = document.querySelector('.flash-sentence-speaker-btn');
    if (btn) btn.classList.add('speaking');
    window.TTSPlayer.speakSentence(sent, [], null, () => {
      if (btn) btn.classList.remove('speaking');
    });
  }

  /**
   * Speak current card Russian collocation chunk
   */
  speakCollocation() {
    const card = this.getCurrentCard();
    if (!card || !window.TTSPlayer) return;
    if (card.collocation_ru) {
      const btn = document.querySelector('.flash-col-speaker-btn');
      if (btn) btn.classList.add('speaking');
      window.TTSPlayer.speakSentence(card.collocation_ru, [], null, () => {
        if (btn) btn.classList.remove('speaking');
      });
    } else {
      this.speakCurrentWord();
    }
  }

  /**
   * Rate current card and advance to next with Fermaata Deep Consolidation evaluation
   */
  async rateAndAdvance(rating = 1) {
    const card = this.getCurrentCard();
    if (card) {
      const elapsedSec = Math.round((Date.now() - (this.cardStartTime || Date.now())) / 1000);
      const isFermaata = (elapsedSec >= 12 && elapsedSec <= 45);
      if (isFermaata) {
        card._fermaataConsolidated = true;
        card._elapsedSec = elapsedSec;
        this.fermaataCount = (this.fermaataCount || 0) + 1;
        if (window.DistanceMeter) {
          window.DistanceMeter.addExp(1);
        }
        this.showFermaataToast(elapsedSec);
      } else {
        card._elapsedSec = elapsedSec;
      }

      this.sessionRatings[card.word] = {
        rating,
        elapsedSec,
        fermaata: isFermaata
      };
      card.mastery_level = rating;
      card.review_count = (card.review_count || 0) + 1;

      if (window.API) {
        window.API.reviewBookmark({
          word: card.word,
          mastery_level: rating
        });
      }
    }

    this.nextCard();
  }

  /**
   * Go to next card (defaults unrated cards to rating 1: 馴染み中 / 再復習ストック)
   */
  nextCard() {
    const card = this.getCurrentCard();
    if (card && !this.sessionRatings[card.word]) {
      this.rateAndAdvance(1);
      return;
    }
    if (this.currentIndex < this.sessionCards.length - 1) {
      this.currentIndex++;
      this.isFlipped = false;
      this.renderCurrentCard();
    } else {
      this.renderCompletionScreen();
    }
  }

  /**
   * Go to previous card
   */
  prevCard() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.isFlipped = false;
      this.renderCurrentCard();
    }
  }

  /**
   * Render Tea Time completion screen (Salon Mode with Tanya's Personal Echo)
   */
  renderCompletionScreen() {
    this.isComplete = true;
    this.stopTableRecitation();
    const container = document.getElementById('flashcardContainer');
    if (!container) return;

    const total = this.sessionCards.length;

    // Award +5 EXP for salon completion once per session
    if (!this.sessionExpAwarded) {
      this.sessionExpAwarded = true;
      if (window.DistanceMeter) {
        window.DistanceMeter.addExp(5);
      }
      if (window.API) {
        window.API.postProgress({
          session_id: 'flashcard_salon_' + Date.now(),
          type: 'salon',
          intimacy_gain: 5
        });
      }
    }

    // Tanya's Personalized Echo: Pick key card & evaluate fermaata
    const focusCard = this.sessionCards.find(c => {
      const res = this.sessionRatings[c.word];
      const r = res ? res.rating : (c.mastery_level || 1);
      return r === 1;
    }) || this.sessionCards.find(c => {
      const res = this.sessionRatings[c.word];
      const r = res ? res.rating : (c.mastery_level || 1);
      return r === 2;
    }) || this.sessionCards[0];

    const fermaataText = (this.fermaataCount > 0)
      ? `𝄐 今回は <strong>${this.fermaataCount} 語</strong> でフェルマータのように音の余韻をじっくり味わいましたね。<br>急いで答えを出すよりも、音と情景を心に響かせる時間こそが何よりの深層定着です♪`
      : `音のリズムを声に出しながら、軽やかに耳を澄ませていくのが一番の上達法です☕`;

    const tanyaQuote = `
      「本日のサロン・フラッシュ、大変お疲れさまでした！<br>
      全部で <strong>${total} フレーズ</strong> の豊かな響きに触れましたね。<br>
      特に <strong>«${focusCard?.word || ''}»</strong>${focusCard?.meaning ? `（${focusCard.meaning}）` : ''} の情景、ピアノの旋律のように深みがありました。<br>
      ${fermaataText}<br>
      ピアノの鍵盤と同じで、触れるたびに指と耳が自然と覚えていきます。<br>
      温かい紅茶を淹れて、少し耳と頭を休めましょう☕」
    `;

    container.innerHTML = `
      <div class="flash-complete-wrapper">
        ${this.renderModeTabsHtml()}

        <div class="tea-atmosphere-icon">☕🎹</div>
        <h2 class="tea-complete-title">モスクワ音楽院サロンのティータイム</h2>

        <div class="tea-intimacy-reward">💖 ターニャ先生との親密度 +5 EXP 獲得！</div>

        <div class="tea-tanya-message-box">
          <div class="tanya-avatar-lg">👩‍🏫</div>
          <div class="tea-tanya-content">
            <div class="tanya-label">ターニャ先生より（パーソナル・エコー）</div>
            <div class="tanya-tea-quote">${tanyaQuote}</div>
          </div>
        </div>

        ${this.fermaataCount > 0 ? `
          <div style="text-align:center; font-size:0.95rem; font-weight:700; color:var(--gold-light); margin-bottom:12px;">
            𝄐 フェルマータ熟成定着: <strong>${this.fermaataCount} 語</strong>（深層記憶へ刻印）
          </div>
        ` : ''}

        <div class="tea-summary-section">
          <div class="tea-summary-header">本日触れたロシア語の響き（復習・習得度）</div>
          <div class="tea-rating-tally" style="display:flex; justify-content:center; gap:12px; margin:8px 0 16px 0; font-size:0.86rem; flex-wrap:wrap;">
            <span style="color:#ffaa7a; background:rgba(220,100,50,0.12); padding:3px 10px; border-radius:6px; border:1px solid rgba(220,100,50,0.3);">🌱 馴染み中 (Lv.1): <strong>${this.sessionCards.filter(c => ((this.sessionRatings[c.word]?.rating || c.mastery_level || 1) === 1)).length} 語</strong>（再復習ストック）</span>
            <span style="color:#6ee7b7; background:rgba(16,185,129,0.12); padding:3px 10px; border-radius:6px; border:1px solid rgba(16,185,129,0.3);">🌿 耳慣れてきた (Lv.2): <strong>${this.sessionCards.filter(c => ((this.sessionRatings[c.word]?.rating || c.mastery_level || 1) === 2)).length} 語</strong></span>
            <span style="color:#fbcfe8; background:rgba(244,114,182,0.12); padding:3px 10px; border-radius:6px; border:1px solid rgba(244,114,182,0.3);">🌸 染み込んだ！ (Lv.3): <strong>${this.sessionCards.filter(c => ((this.sessionRatings[c.word]?.rating || c.mastery_level || 1) === 3)).length} 語</strong></span>
          </div>
          <div class="tea-summary-grid">
            ${this.sessionCards.map(c => {
              const res = this.sessionRatings[c.word];
              const rating = res ? (res.rating || 1) : (c.mastery_level || 1);
              let badgeHtml = '<span class="rate-chip level-1">🌱 馴染み中</span>';
              if (rating === 2) badgeHtml = '<span class="rate-chip level-2">🌿 耳慣れてきた</span>';
              if (rating === 3) badgeHtml = '<span class="rate-chip level-3">🌸 染み込んだ！</span>';

              const softSignBadge = window.renderSoftSignGenderBadge
                ? window.renderSoftSignGenderBadge(c.word, c.base, c.pos, c.meaning)
                : '';

              const fermaataPill = (c._fermaataConsolidated || res?.fermaata)
                ? '<div class="fermaata-pill">𝄐 熟成定着 (+1 EXP)</div>'
                : '';

              return `
                <div class="tea-word-card">
                  <div class="tea-word-top">
                    <span class="tea-word-ru ru-text">${c.word}</span>
                    ${softSignBadge}
                    <button class="tea-word-play-btn" onclick="window.TTSPlayer && window.TTSPlayer.speakWord('${c.word}')">🔊</button>
                  </div>
                  <div class="tea-word-col ru-text">${c.collocation_ru || ''}</div>
                  <div class="tea-word-ja">${c.collocation_ja || c.meaning || ''}</div>
                  <div class="tea-word-badge">
                    ${badgeHtml}
                    ${fermaataPill}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <div class="tea-complete-actions">
          <button class="action-btn flash-restart-btn" onclick="window.SalonFlashcard.startSession(6)">
            <span>🎹 もう1セッション（別のフレーズ）</span>
            <span class="shortcut-key">F</span>
          </button>
          <button class="action-btn" onclick="window.SalonFlashcard.startSoftSignDrill(10)" style="background:rgba(212,175,55,0.2); border:1px solid var(--gold); color:var(--gold-light);">
            <span>⚡ -ь 名詞の性別特訓へ</span>
          </button>
          <button class="action-btn flash-back-bm-btn" onclick="window.SalonFlashcard.close(true)">
            <span>📖 単語帳一覧に戻る</span>
            <span class="shortcut-key">Esc</span>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Toggle Stem / Anatomy Micro-Hint (H key)
   */
  toggleStemHint(forceState) {
    this.showStemHint = (typeof forceState === 'boolean') ? forceState : !this.showStemHint;
    const box = document.getElementById('flashStemHintBox');
    const toggleBtn = document.getElementById('flashStemHintBtn');
    if (box) {
      box.style.display = this.showStemHint ? 'block' : 'none';
    }
    if (toggleBtn) {
      toggleBtn.classList.toggle('active', this.showStemHint);
    }
  }

  /**
   * Mask target word and its inflected forms in hint text to prevent spoilers
   * Uses Cyrillic-aware boundaries so Russian characters are properly matched.
   */
  maskSecretWord(text, word, base) {
    if (!text) return '';
    let res = text;
    const targets = new Set();
    if (word && word.length >= 2) {
      targets.add(word);
      const stem = word.replace(/(ться|тся|ся|сь|ть|ти|ный|ная|ное|ные|ого|ому|а|я|у|ю|о|е|ы|и|ой|ей)$/i, '');
      if (stem && stem.length >= 3) targets.add(stem);
    }
    if (base && base.length >= 2) {
      targets.add(base);
      const stemBase = base.replace(/(ться|тся|ся|сь|ть|ти|ный|ная|ное|ные|ого|ому|а|я|у|ю|о|е|ы|и|ой|ей)$/i, '');
      if (stemBase && stemBase.length >= 3) targets.add(stemBase);
    }

    const sorted = Array.from(targets).sort((a, b) => b.length - a.length);
    for (const t of sorted) {
      const esc = t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      // Quoted occurrences: «слово» -> « [ ❓ ] »
      res = res.replace(new RegExp(`«${esc}[а-яёА-ЯЁ]*»`, 'gi'), '« [ ❓ ] »');
      res = res.replace(new RegExp(`"${esc}[а-яёА-ЯЁ]*"`, 'gi'), '"[ ❓ ]"');
      // Cyrillic-aware boundary matching:
      res = res.replace(new RegExp(`(^|[^а-яёА-ЯЁ])${esc}[а-яёА-ЯЁ]*`, 'gi'), '$1[ ❓ ]');
    }
    return res;
  }

  /**
   * Format stem hint HTML with strict spoiler masking and root morpheme focus
   */
  getStemHintHtml(card) {
    if (!card) return '';
    let content = '';

    // 1. Morphological decomposition (prefix + root vs stem)
    const prefixes = ['пере', 'пред', 'про', 'при', 'под', 'над', 'от', 'до', 'вы', 'по', 'за', 'на', 'об', 'из', 'ис', 'раз', 'рас', 'со', 'с', 'во', 'в', 'у', 'о'];
    let detectedPrefix = null;
    let baseLower = (card.base || card.word).toLowerCase();
    for (const p of prefixes) {
      if (baseLower.startsWith(p) && baseLower.length > p.length + 2) {
        detectedPrefix = p;
        baseLower = baseLower.slice(p.length);
        break;
      }
    }
    const cleanCore = baseLower.replace(/(ться|тся|ся|сь|ть|ти|ный|ной|кий|ость|тель|арь|а|я|о|е|ы|и)$/i, '');
    const cleanStem = (card.base || card.word).replace(/(ться|тся|ся|сь|ть|ти|ный|ной|кий|ость|тель|арь|а|я|о|е|ы|и)$/i, '');

    const maskedNotes = card.notes ? `(${this.maskSecretWord(card.notes, card.word, card.base)})` : '';

    if (detectedPrefix) {
      content += `
        <div class="hint-stem-line" style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed rgba(245, 158, 11, 0.3);">
          <span style="font-size:0.8rem; color:#fef08a;">形態素分析:</span>
          <span style="font-size:0.86rem; color:#d8c6aa; margin-left: 6px;">接頭辞: <strong class="ru-text" style="color:var(--gold-light);">«${detectedPrefix}-»</strong> ＋ コア語幹: <strong class="ru-text" style="color:var(--gold-light);">«${cleanCore}…»</strong></span>
          <span style="font-size:0.78rem; color:#d8c6aa; margin-left: 10px;">[${card.pos || '重要語'}] ${maskedNotes}</span>
        </div>
      `;
    } else {
      content += `
        <div class="hint-stem-line" style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed rgba(245, 158, 11, 0.3);">
          <span style="font-size:0.8rem; color:#fef08a;">語幹 (Stem):</span>
          <strong class="ru-text" style="color:var(--gold-light); font-size:1.15rem; margin-left: 6px;">«${cleanStem}…»</strong>
          <span style="font-size:0.78rem; color:#d8c6aa; margin-left: 10px;">[${card.pos || '重要語'}] ${maskedNotes}</span>
        </div>
      `;
    }

    // 2. Anatomical dictionary clue (strictly masked so target word is replaced with [ ❓ ])
    if (card.anatomy) {
      const maskedAnatomy = this.maskSecretWord(card.anatomy, card.word, card.base);
      content += `<div class="hint-anatomy-text" style="font-size:0.88rem; line-height:1.55; color:#fef9c3;">${maskedAnatomy.replace(/\n/g, '<br>')}</div>`;
    }

    // 3. Related network words (filter out exact target word so it doesn't give away the answer)
    if (card.network && card.network.length > 0) {
      const cleanNetwork = card.network
        .filter(n => !n.toLowerCase().includes(card.word.toLowerCase()) && !(card.base && n.toLowerCase().includes(card.base.toLowerCase())))
        .slice(0, 3);
      if (cleanNetwork.length > 0) {
        content += `<div class="hint-network-line" style="margin-top: 8px; font-size:0.82rem; color:#fde68a;">🌱 関連・派生語: <span class="ru-text">${cleanNetwork.join(', ')}</span></div>`;
      }
    }
    return content;
  }

  /**
   * Prime acoustic head sound (A key)
   */
  primeAcousticSound() {
    const card = this.getCurrentCard();
    if (!card) return;

    const clean = (card.word || '').replace(/[^а-яёА-ЯЁ]/gi, '').toLowerCase();
    if (!clean) return;

    let snippet = '';
    if (clean.length <= 3) {
      snippet = clean;
    } else if (clean.startsWith('ис') || clean.startsWith('от') || clean.startsWith('по') || clean.startsWith('на') || clean.startsWith('за') || clean.startsWith('вы') || clean.startsWith('до') || clean.startsWith('не')) {
      snippet = clean.slice(0, 2);
    } else {
      snippet = clean.slice(0, 3);
    }

    if (window.TTSPlayer) {
      window.TTSPlayer.speakWord(snippet);
    }

    const badgeContainer = document.getElementById('flashAcousticBadgeContainer');
    if (badgeContainer) {
      badgeContainer.innerHTML = `<span class="acoustic-priming-badge">🔊 出だし音: «${snippet}…»</span>`;
      if (this.acousticPrimingTimer) clearTimeout(this.acousticPrimingTimer);
      this.acousticPrimingTimer = setTimeout(() => {
        if (badgeContainer) badgeContainer.innerHTML = '';
      }, 2000);
    }
  }

  /**
   * Show Fermaata deep consolidation toast
   */
  showFermaataToast(elapsedSec) {
    const modal = document.getElementById('flashcardModal');
    if (!modal) return;

    const existing = modal.querySelector('.fermaata-toast-banner');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'fermaata-toast-banner';
    toast.innerHTML = `
      <div class="fermaata-toast-icon">𝄐</div>
      <div>
        <div class="fermaata-toast-title">フェルマータ深層熟成！ (+1 EXP)</div>
        <div class="fermaata-toast-desc">${elapsedSec}秒かけて音と情景を味わいました♪</div>
      </div>
    `;
    modal.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(-10px)';
      setTimeout(() => toast.remove(), 400);
    }, 2500);
  }

  /**
   * Toggle Conjugation / Declension Table Recitation (C / T key)
   */
  toggleTableRecitation() {
    if (this.isReciting) {
      this.stopTableRecitation();
      return;
    }

    const card = this.getCurrentCard();
    if (!card || !window.TTSPlayer) return;

    const reciteText = this.buildRecitationSentence(card);
    if (!reciteText) {
      this.speakCollocation();
      return;
    }

    this.isReciting = true;
    this.updateReciteButtonUI();
    this.showReciteLiveBanner(reciteText);

    window.TTSPlayer.speakSentence(reciteText, [], null, () => {
      this.isReciting = false;
      this.updateReciteButtonUI();
      this.hideReciteLiveBanner();
    });
  }

  /**
   * Stop table recitation
   */
  stopTableRecitation() {
    this.isReciting = false;
    if (window.TTSPlayer) {
      window.TTSPlayer.stop();
    }
    this.updateReciteButtonUI();
    this.hideReciteLiveBanner();
  }

  /**
   * Build recitation sentence from table or phrases
   */
  buildRecitationSentence(card) {
    if (!card) return '';

    const table = card.declension_table;
    const pos = (card.pos || '');
    const isVerb = pos.includes('動詞') || pos.includes('不完了') || pos.includes('完了') || (table && table[0] && table[0][0] === '人称');

    if (table && table.length > 1) {
      if (isVerb) {
        const recitePhrases = [];
        for (let r = 1; r < table.length; r++) {
          const row = table[r];
          const person = row[0];
          const form = row[1];
          if (person && form) {
            let cleanPerson = person.replace(/[()]/g, '').trim();
            if (cleanPerson.includes('он') || cleanPerson.includes('она')) cleanPerson = 'он';
            const cleanForm = form.replace(/[()]/g, '').trim();
            recitePhrases.push(`${cleanPerson} ${cleanForm}`);
          }
        }
        if (recitePhrases.length > 0) {
          return recitePhrases.join(', ') + '.';
        }
      } else {
        // Noun or adjective cases
        const recitePhrases = [];
        for (let r = 1; r < table.length; r++) {
          const row = table[r];
          const singForm = row[1];
          if (singForm) {
            const cleanForm = singForm.replace(/\(.*?\)/g, '').replace(/（.*?）/g, '').trim();
            if (cleanForm && cleanForm !== '-') {
              recitePhrases.push(cleanForm);
            }
          }
        }
        if (recitePhrases.length > 0) {
          return recitePhrases.join(', ') + '.';
        }
      }
    }

    // Fallback: collocation phrase or example
    return card.collocation_ru || card.example_ru || card.word;
  }

  /**
   * Update recitation button visual state
   */
  updateReciteButtonUI() {
    const btn = document.getElementById('flashReciteTableBtn');
    if (!btn) return;
    btn.classList.toggle('playing', this.isReciting);
    btn.innerHTML = `
      <span class="recite-icon">${this.isReciting ? '⏸' : '🎹'}</span>
      <span>${this.isReciting ? '朗読停止' : '活用・格変化を連続朗読'}</span>
      <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 4px; margin-left:4px;">T</kbd>
    `;
  }

  /**
   * Show live recitation banner
   */
  showReciteLiveBanner(text) {
    const bannerContainer = document.getElementById('flashReciteLiveBannerContainer');
    if (!bannerContainer) return;
    const cleanDisplay = text.length > 60 ? text.slice(0, 58) + '...' : text;
    bannerContainer.innerHTML = `
      <div class="flash-recite-live-banner">
        <span>🎵 リズム朗読中: «${cleanDisplay}»</span>
      </div>
    `;
  }

  /**
   * Hide live recitation banner
   */
  hideReciteLiveBanner() {
    const bannerContainer = document.getElementById('flashReciteLiveBannerContainer');
    if (bannerContainer) {
      bannerContainer.innerHTML = '';
    }
  }

  /**
   * Close flashcard modal
   */
  close(reopenBookmarks = false) {
    this.stopTableRecitation();
    const modal = document.getElementById('flashcardModal');
    if (modal) {
      modal.classList.remove('open');
    }
    this.isOpen = false;
    this.isComplete = false;
    if (window.TTSPlayer) {
      window.TTSPlayer.stop();
    }

    if (reopenBookmarks && window.app) {
      window.app.openBookmarksModal();
    }
  }

  /**
   * Handle keyboard shortcuts
   */
  handleKeyShortcut(e) {
    if (!this.isOpen) return false;

    // ESC to close
    if (e.key === 'Escape') {
      e.preventDefault();
      this.close(true);
      return true;
    }

    // --- Mode: soft_sign (Reflex Drill) ---
    if (this.mode === 'soft_sign') {
      if (this.isComplete) {
        if (e.key === 'f' || e.key === 'F' || e.key === 'Enter') {
          e.preventDefault();
          this.startSoftSignDrill(10);
          return true;
        }
        if (e.key === 'h' || e.key === 'H') {
          e.preventDefault();
          if (window.Handbook) window.Handbook.openTag('noun.soft_sign');
          return true;
        }
        return false;
      }

      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        this.speakCurrentWord();
        return true;
      }

      if (!this.drillAnswered) {
        if (e.key === '1' || e.key === 'ArrowLeft') {
          e.preventDefault();
          this.submitSoftSignAnswer('m');
          return true;
        }
        if (e.key === '2' || e.key === 'ArrowRight') {
          e.preventDefault();
          this.submitSoftSignAnswer('f');
          return true;
        }
      } else {
        if (e.key === 'h' || e.key === 'H') {
          e.preventDefault();
          if (window.Handbook) window.Handbook.openTag('noun.soft_sign');
          return true;
        }
        if (e.key === ' ' || e.key === 'Enter' || e.key === 'n' || e.key === 'N' || e.key === 'ArrowRight') {
          e.preventDefault();
          this.nextSoftSignCard();
          return true;
        }
      }

      return false;
    }

    // --- Mode: salon (Bookmarks Flashcard) ---
    // Audio replay (word): 'r' or 'R'
    if (e.key === 'r' || e.key === 'R') {
      e.preventDefault();
      this.speakCurrentWord();
      return true;
    }

    // Example sentence audio replay: 's', 'S', 'e', or 'E'
    if (e.key === 's' || e.key === 'S' || e.key === 'e' || e.key === 'E') {
      e.preventDefault();
      this.speakSentence();
      return true;
    }

    // Completion screen shortcuts
    if (this.isComplete) {
      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        this.startSession(6);
        return true;
      }
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        this.close(true);
        return true;
      }
      return false;
    }

    // Previous card: 'p' or 'P' or 'k' or 'K'
    if (e.key === 'p' || e.key === 'P' || e.key === 'k' || e.key === 'K') {
      e.preventDefault();
      this.prevCard();
      return true;
    }

    // Next / Skip card: 'n' or 'N' or 'j' or 'J'
    if (e.key === 'n' || e.key === 'N' || e.key === 'j' || e.key === 'J') {
      e.preventDefault();
      this.nextCard();
      return true;
    }

    // If on Front Face:
    if (!this.isFlipped) {
      // 'H': Toggle Stem Micro-Hint
      if (e.key === 'h' || e.key === 'H') {
        e.preventDefault();
        this.toggleStemHint();
        return true;
      }

      // 'A': Prime Acoustic Sound
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        this.primeAcousticSound();
        return true;
      }

      // Space / Enter: Flip card
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        this.flip();
        return true;
      }
    } else {
      // If on Back Face:
      // 'C': Collocation phrase audio replay
      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        this.speakCollocation();
        return true;
      }

      // 'T': Toggle Table Recitation
      if (e.key === 't' || e.key === 'T') {
        e.preventDefault();
        this.toggleTableRecitation();
        return true;
      }

      // Ratings 1, 2, 3
      if (e.key === '1') {
        e.preventDefault();
        this.rateAndAdvance(1);
        return true;
      }
      if (e.key === '2') {
        e.preventDefault();
        this.rateAndAdvance(2);
        return true;
      }
      if (e.key === '3') {
        e.preventDefault();
        this.rateAndAdvance(3);
        return true;
      }
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        const card = this.getCurrentCard();
        this.rateAndAdvance(card?.mastery_level || 1);
        return true;
      }
    }

    return false;
  }
}

// Global Singleton
window.SalonFlashcard = new SalonFlashcard();
