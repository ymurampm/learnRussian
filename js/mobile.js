/**
 * Tanya Russian Mobile Studio - Core JavaScript Engine
 * Single Page App (PWA) with Flashcards, Listening, and GitHub Gist Sync
 */

(function () {
  'use strict';

  const DEFAULT_GIST_ID = '489fc67d044b666cd983e20f60376cc0';

  // --- Audio Engine (Web Speech API) ---
  class MobileAudioPlayer {
    constructor() {
      this.synth = window.speechSynthesis;
      this.russianVoice = null;
      this.playId = 0;
      this.pauseTimer = null;
      this.initVoice();
      if (this.synth && this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.initVoice();
      }
    }

    initVoice() {
      if (!this.synth) return;
      const voices = this.synth.getVoices();
      // Look for Russian voice (Milena, Yuri, Katya on iOS)
      this.russianVoice = voices.find(v => v.lang.startsWith('ru') || v.lang.includes('RU')) || null;
    }

    /**
     * Parse Russian word/text into pronounceable units.
     * Handles slash-separated pairs (e.g. aspectual pairs: выступать/выступить),
     * reconstructs prefix shorthands (e.g. писать/на- -> писать, написать),
     * and strips grammatical annotations (e.g. (+a), (i/p), (к +d)).
     */
    parseSpeechUnits(text) {
      if (!text) return [];
      let cleaned = String(text).replace(/\s*\([^)]*\)/g, '').replace(/[«»]/g, '').trim();
      if (!cleaned) return [];

      cleaned = cleaned.replace(/[.,!?;:""'']/g, '').trim();
      if (!cleaned) return [];

      if (!cleaned.includes('/')) {
        const single = cleaned.replace(/-+$/, '').trim();
        return single ? [single] : [];
      }

      const rawParts = cleaned.split('/').map(p => p.trim()).filter(Boolean);
      if (rawParts.length <= 1) return rawParts;

      const units = [];
      const baseWord = rawParts[0].replace(/-+$/, '').trim();
      for (let i = 0; i < rawParts.length; i++) {
        const part = rawParts[i].trim();
        if (i > 0 && part.endsWith('-')) {
          const prefix = part.slice(0, -1);
          units.push(prefix + baseWord);
        } else {
          units.push(part.replace(/-+$/, '').trim());
        }
      }
      return units.filter(Boolean);
    }

    speak(text, rate = 1.0, onEnd = null) {
      this.stop();
      if (!this.synth || !text) {
        if (onEnd) onEnd();
        return;
      }

      const units = this.parseSpeechUnits(text);
      if (units.length === 0) {
        if (onEnd) onEnd();
        return;
      }

      const currentPlayId = ++this.playId;

      if (units.length === 1) {
        return this.speakSingle(units[0], rate, onEnd);
      }

      // Multi-part word pair separated by slash (e.g. выступать/выступить):
      // Clean speech with ~1-second pause, without voicing the slash symbol
      let idx = 0;
      const playNext = () => {
        if (this.playId !== currentPlayId) return;
        if (idx >= units.length) {
          if (onEnd) onEnd();
          return;
        }

        const unitText = units[idx++];
        this.speakSingle(unitText, rate, () => {
          if (this.playId !== currentPlayId) return;
          if (idx < units.length) {
            this.pauseTimer = setTimeout(() => {
              if (this.playId === currentPlayId) {
                playNext();
              }
            }, 1000);
          } else {
            if (onEnd) onEnd();
          }
        });
      };

      playNext();
    }

    speakSingle(clean, rate = 1.0, onEnd = null) {
      if (!this.synth || !clean) {
        if (onEnd) onEnd();
        return;
      }
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.lang = 'ru-RU';
      if (this.russianVoice) utterance.voice = this.russianVoice;
      utterance.rate = rate;
      utterance.pitch = 1.05; // Slightly pleasant pitch for Tanya
      if (onEnd) utterance.onend = onEnd;
      utterance.onerror = () => { if (onEnd) onEnd(); };
      this.synth.speak(utterance);
    }

    stop() {
      this.playId++;
      if (this.pauseTimer) {
        clearTimeout(this.pauseTimer);
        this.pauseTimer = null;
      }
      if (this.synth) this.synth.cancel();
    }

    speakSequence(items, rate = 1.0, onStep = null, onDone = null) {
      if (!items || items.length === 0) {
        if (onDone) onDone();
        return;
      }
      let idx = 0;
      const next = () => {
        if (idx >= items.length) {
          if (onDone) onDone();
          return;
        }
        const curIdx = idx;
        const text = items[idx++];
        if (onStep) onStep(curIdx, text);
        this.speak(text, rate, () => {
          setTimeout(next, 220);
        });
      };
      next();
    }
  }

  // --- Main Application Controller ---
  class TanyaMobileApp {
    constructor() {
      this.audio = new MobileAudioPlayer();
      this.currentTab = 'flashcard'; // 'flashcard' | 'listening'
      this.starredWords = [];
      this.currentIndex = 0;
      this.isFlipped = false;
      this.fermataSeconds = 0;
      this.fermataTimer = null;
      this.isAutoPlay = false;
      this.autoPlayTimer = null;
      this.isPlayingConjugation = false;
      this.isPlayingListening = false;
      this.listeningActiveIndex = -1;
      this.listeningRate = 1.0;

      // Pending sync reviews (stored in localStorage)
      this.pendingReviews = JSON.parse(localStorage.getItem('tanya_pending_reviews') || '[]');
      this.listenings = [];

      this.initData();
      this.bindEvents();
      this.render();
      this.updateSyncBadge();
    }

    initData() {
      // Auto-configure from URL query (?gist=...&token=...) or hash (#gist=...&token=...)
      try {
        const hashParams = window.location.hash ? new URLSearchParams(window.location.hash.slice(1)) : null;
        const searchParams = new URLSearchParams(window.location.search);

        const incomingGist = (hashParams && hashParams.get('gist')) || searchParams.get('gist');
        const incomingToken = (hashParams && hashParams.get('token')) || searchParams.get('token');

        if (incomingGist) localStorage.setItem('tanya_gist_id', incomingGist);
        if (incomingToken) localStorage.setItem('tanya_github_token', incomingToken);

        // Pre-fill default Gist ID if missing
        if (!localStorage.getItem('tanya_gist_id')) {
          localStorage.setItem('tanya_gist_id', DEFAULT_GIST_ID);
        }

        if (incomingGist || incomingToken) {
          history.replaceState(null, '', window.location.pathname);
          setTimeout(() => {
            this.showToast('✨ GitHub同期設定を自動登録しました！');
          }, 300);
        }
      } catch (e) {
        console.warn('URL auto-config failed:', e);
      }

      // 1. Load Seed Data from window.TANYA_MOBILE_SEED if available
      const seed = window.TANYA_MOBILE_SEED || {};
      const localWords = JSON.parse(localStorage.getItem('tanya_starred_words') || 'null');

      if (localWords && Array.isArray(localWords) && localWords.length > 0) {
        // Seamlessly merge new linguistic data (tips, declensions, examples) while preserving user review status
        const seedMap = new Map((seed.bookmarked_words || []).map(w => [(w.word || '').toLowerCase(), w]));
        this.starredWords = localWords.map(lw => {
          const sw = seedMap.get((lw.word || '').toLowerCase());
          if (sw) {
            return {
              ...sw,
              ...lw,
              declension_table: sw.declension_table || lw.declension_table,
              anatomy: sw.anatomy || lw.anatomy,
              notes: sw.notes || lw.notes,
              network: sw.network || lw.network,
              collocation_ru: sw.collocation_ru || lw.collocation_ru,
              collocation_ja: sw.collocation_ja || lw.collocation_ja,
              example_ru: sw.example_ru || lw.example_ru,
              example_ja: sw.example_ja || lw.example_ja
            };
          }
          return lw;
        });
        localStorage.setItem('tanya_starred_words', JSON.stringify(this.starredWords));
      } else if (seed.bookmarked_words && seed.bookmarked_words.length > 0) {
        this.starredWords = seed.bookmarked_words;
        localStorage.setItem('tanya_starred_words', JSON.stringify(this.starredWords));
      } else {
        // Fallback default sample
        this.starredWords = [
          {
            word: "вдохновение",
            base: "вдохновение",
            pos: "中性名詞",
            meaning: "ひらめき, インスピレーション",
            example_ru: "Музыка Чайковского дарит глубокое вдохновение.",
            example_ja: "チャイコフスキーの音楽は深いひらめきを与えてくれます。",
            collocation_ru: "глубокое вдохновение",
            collocation_ja: "深いひらめき",
            collocation_cloze: "глубокое [ ❓ ]"
          }
        ];
      }

      this.listenings = seed.listenings || [];
      if (this.listenings.length === 0) {
        this.listenings = [
          {
            day: 25,
            title: "四重奏の余韻、共に奏でた仲間たち",
            greeting: "Добрый вечер! 今日もお疲れさまでした。心安らぐロシア語の響きをどうぞ。",
            paragraphs: [
              { ru: "В уютном классе двое музыкантов тихо обсуждали сложный фиナル квартета.", ja: "居心地の良い教室で、2人の音楽家が四重奏の難解なフィナーレについて静かに語り合っていました。" },
              { ru: "Звук рояля мягко заполнял вечерний воздух консерватории.", ja: "グランドピアノの音が、音楽院の夕暮れの空気を柔らかく満たしていました。" }
            ]
          }
        ];
      }
    }

    bindEvents() {
      // Tab Navigation
      document.getElementById('tabBtnFlash').addEventListener('click', () => this.switchTab('flashcard'));
      document.getElementById('tabBtnListen').addEventListener('click', () => this.switchTab('listening'));

      // Card Flip (tap wrapper)
      const cardWrapper = document.getElementById('cardWrapper');
      cardWrapper.addEventListener('click', (e) => {
        // Ignore if clicking on buttons, chips, or interactive example
        if (e.target.closest('button') || e.target.closest('.hint-btn') || e.target.closest('#exampleBox') || e.target.closest('.declension-chip')) return;
        this.toggleFlip();
      });

      // Micro-Hints
      document.getElementById('btnHintStem').addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleStemHint();
      });
      document.getElementById('btnHintSound').addEventListener('click', (e) => {
        e.stopPropagation();
        this.primeHeadSound();
      });

      // Shuffle Button
      const btnShuffle = document.getElementById('btnShuffle');
      if (btnShuffle) {
        btnShuffle.addEventListener('click', (e) => {
          e.stopPropagation();
          this.shuffleCards();
        });
      }

      // Back Face Actions
      document.getElementById('btnReplayWord').addEventListener('click', (e) => {
        e.stopPropagation();
        const card = this.getCurrentCard();
        if (card) this.audio.speak(card.word, 1.0);
      });

      const btnPlayCollocation = document.getElementById('btnPlayCollocation');
      if (btnPlayCollocation) {
        btnPlayCollocation.addEventListener('click', (e) => {
          e.stopPropagation();
          this.playCollocation();
        });
      }

      document.getElementById('btnPlayConjugation').addEventListener('click', (e) => {
        e.stopPropagation();
        this.playConjugationRhythm();
      });

      const btnToggleDeclension = document.getElementById('btnToggleDeclension');
      if (btnToggleDeclension) {
        btnToggleDeclension.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleDeclensionDrawer();
        });
      }

      // Example Box Tap-to-Speak
      const exampleBox = document.getElementById('exampleBox');
      if (exampleBox) {
        exampleBox.addEventListener('click', (e) => {
          e.stopPropagation();
          this.playExampleSentence();
        });
      }


      // Thumb Buttons
      document.getElementById('btnRateReview').addEventListener('click', () => this.handleRate('review'));
      document.getElementById('btnRateMastered').addEventListener('click', () => this.handleRate('mastered'));

      // Autoplay Toggle (Rain / Hands-free)
      document.getElementById('btnAutoPlay').addEventListener('click', () => this.toggleAutoPlay());

      // Listening Day Picker
      const daySelect = document.getElementById('daySelectDropdown');
      daySelect.addEventListener('change', () => this.renderListening());

      // Listening Controls
      document.getElementById('btnPlayListening').addEventListener('click', () => this.toggleListeningPlay());
      document.querySelectorAll('.speed-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
          e.target.classList.add('active');
          this.listeningRate = parseFloat(e.target.dataset.rate || '1.0');
        });
      });

      // Sync Modal
      document.getElementById('btnOpenSync').addEventListener('click', () => this.openSyncModal());
      document.getElementById('btnCloseSync').addEventListener('click', () => this.closeSyncModal());
      document.getElementById('btnPushGist').addEventListener('click', () => this.pushToGist());
      document.getElementById('btnPullGist').addEventListener('click', () => this.pullFromGist());

      // Save credentials on input change
      document.getElementById('gistIdInput').addEventListener('input', (e) => {
        localStorage.setItem('tanya_gist_id', e.target.value.trim());
      });
      document.getElementById('githubTokenInput').addEventListener('input', (e) => {
        localStorage.setItem('tanya_github_token', e.target.value.trim());
      });

      const btnPasteToken = document.getElementById('btnPasteToken');
      if (btnPasteToken) {
        btnPasteToken.addEventListener('click', async () => {
          try {
            const text = await navigator.clipboard.readText();
            if (text && text.trim()) {
              const cleaned = text.trim();
              document.getElementById('githubTokenInput').value = cleaned;
              localStorage.setItem('tanya_github_token', cleaned);
              this.showToast('✅ トークンをペースト＆保存しました！');
            } else {
              this.showToast('クリップボードが空です');
            }
          } catch (e) {
            const val = prompt('GitHub Personal Access Token (ghp_...) を貼り付けてください:');
            if (val && val.trim()) {
              const cleaned = val.trim();
              document.getElementById('githubTokenInput').value = cleaned;
              localStorage.setItem('tanya_github_token', cleaned);
              this.showToast('✅ トークンを保存しました！');
            }
          }
        });
      }

      // Background Sleep/Tab Switch Auto-sync
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.tryBackgroundAutoSync();
        }
      });
    }

    switchTab(tab) {
      this.currentTab = tab;
      this.audio.stop();
      this.stopAutoPlay();
      this.isPlayingListening = false;

      document.getElementById('tabBtnFlash').classList.toggle('active', tab === 'flashcard');
      document.getElementById('tabBtnListen').classList.toggle('active', tab === 'listening');
      document.getElementById('flashTabContent').classList.toggle('active', tab === 'flashcard');
      document.getElementById('listenTabContent').classList.toggle('active', tab === 'listening');

      if (tab === 'flashcard') {
        this.renderCard();
      } else {
        this.renderListening();
      }
    }

    getCurrentCard() {
      if (this.starredWords.length === 0) return null;
      return this.starredWords[this.currentIndex % this.starredWords.length];
    }

    render() {
      this.renderDayOptions();
      this.renderCard();
    }

    // --- Flashcard Logic ---
    renderCard() {
      const card = this.getCurrentCard();
      const cardCountBadge = document.getElementById('cardCountBadge');
      if (cardCountBadge) {
        cardCountBadge.textContent = `${this.currentIndex + 1} / ${this.starredWords.length}`;
      }
      if (!card) return;

      this.isFlipped = false;
      document.getElementById('flipCard').classList.remove('flipped');
      document.getElementById('hintContentDrawer').style.display = 'none';

      // Front Face (Active Recall - Challenge without spoilers)
      document.getElementById('cardPosTag').textContent = card.pos || '重要語';
      document.getElementById('frontRuWord').textContent = card.collocation_cloze || '[ ❓ ]';
      document.getElementById('frontClozeLine').textContent = card.collocation_ja || card.meaning || '';

      // Reset Fermata Timer
      this.startFermataTimer();

      // Back Face
      document.getElementById('backRuWord').textContent = card.word || '';
      document.getElementById('backMeaningText').textContent = card.meaning || '';
      document.getElementById('exampleRuLine').textContent = card.example_ru || '';
      document.getElementById('exampleJaLine').textContent = card.example_ja || '';

      const collocBadge = document.getElementById('exampleCollocBadge');
      if (collocBadge) {
        collocBadge.textContent = card.collocation_ru ? `連語: ${card.collocation_ru}` : '';
      }

      this.renderDeclensionGrid(card);
      this.renderMemoryTips(card);

      const alenaContext = document.getElementById('alenaSceneCapsule');
      if (card.alena_scene) {
        alenaContext.textContent = `🎹 ${card.alena_scene}`;
        alenaContext.style.display = 'block';
      } else {
        alenaContext.style.display = 'none';
      }

      // Reset scroll position to top
      const backFace = document.querySelector('.card-face.back');
      if (backFace) backFace.scrollTop = 0;
    }

    shuffleCards() {
      if (this.starredWords.length <= 1) return;
      for (let i = this.starredWords.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [this.starredWords[i], this.starredWords[j]] = [this.starredWords[j], this.starredWords[i]];
      }
      this.currentIndex = 0;
      this.isFlipped = false;
      document.getElementById('flipCard')?.classList.remove('flipped');
      this.renderCard();
      this.showToast(`🔀 単語の並び順をシャッフルしました！ (全${this.starredWords.length}語)`);
    }

    playCollocation() {
      const card = this.getCurrentCard();
      if (!card) return;
      const colloc = card.collocation_ru || card.word;
      this.audio.speak(colloc, 0.95);
      this.showToast(`🔊 連語: «${colloc}»`);
    }

    playExampleSentence() {
      const card = this.getCurrentCard();
      if (!card || !card.example_ru) return;
      const box = document.getElementById('exampleBox');
      if (box) box.classList.add('speaking');
      this.audio.speak(card.example_ru, 0.9, () => {
        if (box) box.classList.remove('speaking');
      });
    }

    toggleDeclensionDrawer() {
      const drawer = document.getElementById('declensionDrawer');
      const btn = document.getElementById('btnToggleDeclension');
      if (!drawer) return;
      const isOpen = drawer.style.display !== 'none';
      drawer.style.display = isOpen ? 'none' : 'block';
      if (btn) {
        btn.classList.toggle('open', !isOpen);
        btn.innerHTML = isOpen ? '▼ 格変化' : '▲ 格変化';
      }
    }

    renderDeclensionGrid(card) {
      const grid = document.getElementById('declensionGrid');
      const drawer = document.getElementById('declensionDrawer');
      const toggleBtn = document.getElementById('btnToggleDeclension');
      if (!grid) return;
      grid.innerHTML = '';
      if (drawer) drawer.style.display = 'none';
      if (toggleBtn) {
        toggleBtn.classList.remove('open');
        toggleBtn.innerHTML = '▼ 格変化';
      }

      const table = card.declension_table;
      if (table && Array.isArray(table) && table.length > 1) {
        table.slice(1).forEach((row, idx) => {
          if (!Array.isArray(row) || row.length === 0) return;
          const label = row[0];
          const sg = row[1] || '';
          const pl = row[2] || '';
          const displayVal = pl ? `${sg} / ${pl}` : sg;
          const speechVal = sg || pl || card.word;

          const chip = document.createElement('div');
          chip.className = 'declension-chip';
          chip.dataset.formIndex = idx;
          chip.dataset.speech = speechVal;
          chip.innerHTML = `<span class="case-label">${label}</span><span class="case-val">${displayVal}</span>`;
          chip.onclick = (e) => {
            e.stopPropagation();
            this.audio.speak(speechVal, 0.95);
          };
          grid.appendChild(chip);
        });
      } else {
        const fallbackForms = this.generateSampleDeclensions(card.word, card.pos);
        fallbackForms.forEach((f, idx) => {
          const chip = document.createElement('div');
          chip.className = 'declension-chip';
          chip.dataset.formIndex = idx;
          chip.dataset.speech = f.val;
          chip.innerHTML = `<span class="case-label">${f.label}</span><span class="case-val">${f.val}</span>`;
          chip.onclick = (e) => {
            e.stopPropagation();
            this.audio.speak(f.val, 0.95);
          };
          grid.appendChild(chip);
        });
      }
    }

    renderMemoryTips(card) {
      const tipsCapsule = document.getElementById('memoryTipsCapsule');
      const tipsContent = document.getElementById('tipsContent');
      const tipsChipsRow = document.getElementById('tipsChipsRow');
      if (!tipsCapsule || !tipsContent || !tipsChipsRow) return;

      tipsChipsRow.innerHTML = '';
      let textParts = [];

      if (card.anatomy) {
        textParts.push(card.anatomy);
      }
      if (card.notes && card.notes !== card.anatomy) {
        textParts.push(card.notes);
      }

      if (card.network && Array.isArray(card.network) && card.network.length > 0) {
        card.network.forEach(item => {
          const chip = document.createElement('span');
          chip.className = 'tips-chip';
          chip.textContent = `🔗 ${item}`;
          tipsChipsRow.appendChild(chip);
        });
      }

      if (textParts.length > 0 || (card.network && card.network.length > 0)) {
        tipsContent.textContent = textParts.join('\n\n');
        tipsCapsule.style.display = 'block';
      } else {
        const fallbackTip = this.generateMorphologyTip(card);
        if (fallbackTip) {
          tipsContent.textContent = fallbackTip;
          tipsCapsule.style.display = 'block';
        } else {
          tipsCapsule.style.display = 'none';
        }
      }
    }

    generateMorphologyTip(card) {
      const w = (card.word || '').toLowerCase();
      const pos = card.pos || '';
      if (w.endsWith('ость') || w.endsWith('есть')) {
        return '・語尾 -ость / -есть: 性質や状態を表す第3変化女性名詞（生・与・前置格は -и、造格は -ью）。';
      }
      if (w.endsWith('ение') || w.endsWith('ание')) {
        return '・語尾 -ение / -ание: 動作や結果を表す中性名詞（前置格は -ии）。';
      }
      if (w.endsWith('тель')) {
        return '・接尾辞 -тель: 〜する人・装置を表す男性名詞（учитель, строитель）。';
      }
      if (pos.includes('動詞')) {
        return '・動詞変化: 完了体(СВ) / 不完了体(НСВ)のペアや前置詞との格支配に注目しましょう。';
      }
      return null;
    }

    startFermataTimer() {
      if (this.fermataTimer) clearInterval(this.fermataTimer);
      this.fermataSeconds = 0;
      const badge = document.getElementById('fermataBadge');
      badge.textContent = `𝄐 0s`;

      this.fermataTimer = setInterval(() => {
        this.fermataSeconds++;
        if (this.fermataSeconds >= 15 && this.fermataSeconds <= 35) {
          badge.textContent = `𝄐 ${this.fermataSeconds}s (熟成中)`;
          badge.style.color = '#fbbf24';
        } else {
          badge.textContent = `𝄐 ${this.fermataSeconds}s`;
          badge.style.color = '#a3b8cc';
        }
      }, 1000);
    }

    toggleFlip() {
      this.isFlipped = !this.isFlipped;
      document.getElementById('flipCard').classList.toggle('flipped', this.isFlipped);

      if (this.isFlipped) {
        if (this.fermataTimer) clearInterval(this.fermataTimer);
        const card = this.getCurrentCard();
        if (card && !this.isAutoPlay) {
          setTimeout(() => this.audio.speak(card.word, 1.0), 120);
        }
      } else {
        this.startFermataTimer();
      }
    }

    toggleStemHint() {
      const drawer = document.getElementById('hintContentDrawer');
      if (drawer.style.display === 'block') {
        drawer.style.display = 'none';
        return;
      }

      const card = this.getCurrentCard();
      if (!card) return;

      const prefixes = ['пере', 'пред', 'про', 'при', 'под', 'над', 'от', 'до', 'вы', 'по', 'за', 'на', 'об', 'из', 'ис', 'раз', 'рас', 'со', 'с', 'во', 'в', 'у', 'о'];
      let prefix = null;
      let core = (card.base || card.word).toLowerCase();

      for (const p of prefixes) {
        if (core.startsWith(p) && core.length > p.length + 2) {
          prefix = p;
          core = core.slice(p.length);
          break;
        }
      }
      const cleanCore = core.replace(/(ться|тся|ся|сь|ть|ти|ный|ная|ное|ные|а|я|о|е|ы|и)$/i, '');

      if (prefix) {
        drawer.innerHTML = `接頭辞: <strong>«${prefix}-»</strong> ＋ コア語幹: <strong>«${cleanCore}…»</strong>`;
      } else {
        drawer.innerHTML = `語幹: <strong>«${cleanCore}…»</strong> [${card.pos || ''}]`;
      }
      drawer.style.display = 'block';
    }

    primeHeadSound() {
      const card = this.getCurrentCard();
      if (!card) return;
      const word = (card.word || '').replace(/[^а-яёА-ЯЁ]/gi, '').toLowerCase();
      if (!word) return;
      const snippet = word.length <= 3 ? word : word.slice(0, 3);
      this.audio.speak(snippet, 0.9);
      this.showToast(`🔊 出だし音: «${snippet}…»`);
    }

    playConjugationRhythm() {
      const card = this.getCurrentCard();
      if (!card) return;
      const btn = document.getElementById('btnPlayConjugation');
      const drawer = document.getElementById('declensionDrawer');
      const toggleBtn = document.getElementById('btnToggleDeclension');
      btn.classList.add('playing');

      if (drawer && drawer.style.display === 'none') {
        drawer.style.display = 'block';
        if (toggleBtn) {
          toggleBtn.classList.add('open');
          toggleBtn.innerHTML = '▲ 格変化';
        }
      }

      const chips = Array.from(document.querySelectorAll('#declensionGrid .declension-chip'));
      const speechItems = chips.map(c => c.dataset.speech || card.word);
      if (speechItems.length === 0) {
        speechItems.push(card.word);
      }

      this.audio.speakSequence(
        speechItems,
        1.05,
        (stepIdx) => {
          chips.forEach((c, idx) => c.classList.toggle('active', idx === stepIdx));
        },
        () => {
          btn.classList.remove('playing');
          chips.forEach(c => c.classList.remove('active'));
        }
      );
    }

    generateSampleDeclensions(word, pos) {
      if (!word) return [];
      const clean = word.toLowerCase();
      if (clean.endsWith('ть') || clean.endsWith('ться')) {
        const isReflexive = clean.endsWith('ся') || clean.endsWith('сь');
        const base = clean.replace(/(ться|ть)$/, '');
        const ref = isReflexive ? 'сь' : '';
        const refS = isReflexive ? 'ся' : '';
        return [
          { label: 'я (1単)', val: `${base}ю${ref}` },
          { label: 'ты (2単)', val: `${base}ешь${refS}` },
          { label: 'он (3単)', val: `${base}ет${refS}` },
          { label: 'мы (1複)', val: `${base}ем${refS}` },
          { label: 'вы (2複)', val: `${base}ете${ref}` },
          { label: 'они (3複)', val: `${base}ют${refS}` }
        ];
      }
      if (clean.endsWith('ость') || clean.endsWith('есть')) {
        const stem = clean.slice(0, -1);
        return [
          { label: '主格', val: clean },
          { label: '生格', val: `${stem}и` },
          { label: '与格', val: `${stem}и` },
          { label: '対格', val: clean },
          { label: '造格', val: `${stem}ью` },
          { label: '前置格', val: `о ${stem}и` }
        ];
      }
      if (clean.endsWith('а')) {
        const stem = clean.slice(0, -1);
        return [
          { label: '主格', val: clean },
          { label: '生格', val: `${stem}ы` },
          { label: '与格', val: `${stem}е` },
          { label: '対格', val: `${stem}у` },
          { label: '造格', val: `${stem}ой` },
          { label: '前置格', val: `о ${stem}е` }
        ];
      }
      return [
        { label: '主格', val: clean },
        { label: '生格', val: `${clean}а` },
        { label: '与格', val: `${clean}у` },
        { label: '対格', val: clean },
        { label: '造格', val: `${clean}ом` },
        { label: '前置格', val: `о ${clean}е` }
      ];
    }

    handleRate(result) {
      const card = this.getCurrentCard();
      if (!card) return;

      // Record in pendingReviews
      this.pendingReviews.push({
        word: card.word,
        result: result, // 'mastered' | 'review'
        fermata_seconds: this.fermataSeconds,
        reviewed_at: new Date().toISOString()
      });
      localStorage.setItem('tanya_pending_reviews', JSON.stringify(this.pendingReviews));
      this.updateSyncBadge();

      this.showToast(result === 'mastered' ? '🌸 覚えた！（定着）' : '🌱 まだ（要復習）');

      // Advance to next card
      this.currentIndex = (this.currentIndex + 1) % this.starredWords.length;
      this.renderCard();

      if (this.isAutoPlay) {
        this.scheduleAutoPlayStep();
      }
    }

    toggleAutoPlay() {
      this.isAutoPlay = !this.isAutoPlay;
      const btn = document.getElementById('btnAutoPlay');
      btn.classList.toggle('active', this.isAutoPlay);

      if (this.isAutoPlay) {
        this.showToast('▶ 雨の日オート送り ON');
        this.scheduleAutoPlayStep();
      } else {
        this.stopAutoPlay();
        this.showToast('⏸ オート送り OFF');
      }
    }

    scheduleAutoPlayStep() {
      if (!this.isAutoPlay) return;
      this.stopAutoPlay();

      // Step 1: Wait 4 seconds on front (mental recall period), then flip
      this.autoPlayTimer = setTimeout(() => {
        if (!this.isAutoPlay) return;
        this.toggleFlip();

        const card = this.getCurrentCard();
        if (!card) return;

        // Step 2: Speak word on flip, and when finished (including 1.0s pause if slash pair),
        // follow up with collocation after a calm 500ms breath!
        this.audio.speak(card.word, 1.0, () => {
          if (!this.isAutoPlay || !this.isFlipped) return;
          if (card.collocation_ru) {
            this.autoPlayTimer = setTimeout(() => {
              if (!this.isAutoPlay || !this.isFlipped) return;
              this.audio.speak(card.collocation_ru, 0.95, () => {
                // Step 3: Wait 3.5 seconds on back for absorption, then auto-rate and advance
                if (!this.isAutoPlay) return;
                this.autoPlayTimer = setTimeout(() => {
                  if (!this.isAutoPlay) return;
                  this.handleRate('mastered');
                }, 3500);
              });
            }, 500);
          } else {
            this.autoPlayTimer = setTimeout(() => {
              if (!this.isAutoPlay) return;
              this.handleRate('mastered');
            }, 3500);
          }
        });
      }, 4000);
    }

    stopAutoPlay() {
      if (this.autoPlayTimer) {
        clearTimeout(this.autoPlayTimer);
        this.autoPlayTimer = null;
      }
    }

    // --- Listening Studio Logic ---
    renderDayOptions() {
      const dropdown = document.getElementById('daySelectDropdown');
      dropdown.innerHTML = '';
      this.listenings.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.day;
        opt.textContent = `第${l.day}日 (${l.title.slice(0, 10)}…)`;
        dropdown.appendChild(opt);
      });
    }

    getSelectedListening() {
      const dropdown = document.getElementById('daySelectDropdown');
      const selectedDay = parseInt(dropdown.value, 10);
      return this.listenings.find(l => l.day === selectedDay) || this.listenings[0];
    }

    renderListening() {
      const listening = this.getSelectedListening();
      if (!listening) return;

      document.getElementById('listeningTitle').textContent = listening.title;
      document.getElementById('listeningGreeting').textContent = listening.greeting;

      const feed = document.getElementById('transcriptFeed');
      feed.innerHTML = '';

      listening.paragraphs.forEach((p, idx) => {
        const card = document.createElement('div');
        card.className = 'sentence-card';
        card.dataset.index = idx;
        card.innerHTML = `
          <div class="sentence-ru-line">${p.ru}</div>
          <div class="sentence-ja-line">${p.ja}</div>
        `;
        card.addEventListener('click', () => {
          this.playSentenceAt(idx);
        });
        feed.appendChild(card);
      });
    }

    toggleListeningPlay() {
      if (this.isPlayingListening) {
        this.stopListening();
      } else {
        this.startListening();
      }
    }

    startListening() {
      this.isPlayingListening = true;
      document.getElementById('btnPlayListening').textContent = '⏸';
      this.playSentenceAt(0);
    }

    stopListening() {
      this.isPlayingListening = false;
      document.getElementById('btnPlayListening').textContent = '▶';
      this.audio.stop();
      this.clearActiveSentence();
    }

    playSentenceAt(idx) {
      const listening = this.getSelectedListening();
      if (!listening || idx >= listening.paragraphs.length) {
        this.stopListening();
        return;
      }

      this.listeningActiveIndex = idx;
      this.highlightSentence(idx);

      const p = listening.paragraphs[idx];
      this.audio.speak(p.ru, this.listeningRate, () => {
        if (this.isPlayingListening) {
          setTimeout(() => {
            this.playSentenceAt(idx + 1);
          }, 400);
        }
      });
    }

    highlightSentence(idx) {
      document.querySelectorAll('.sentence-card').forEach((card, i) => {
        const isActive = (i === idx);
        card.classList.toggle('active', isActive);
        if (isActive) {
          card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    }

    clearActiveSentence() {
      document.querySelectorAll('.sentence-card').forEach(card => card.classList.remove('active'));
    }

    // --- GitHub Gist Sync Engine ---
    getGistConfig() {
      const gistId = localStorage.getItem('tanya_gist_id') || DEFAULT_GIST_ID;
      const token = localStorage.getItem('tanya_github_token') || '';
      return { gistId, token };
    }

    openSyncModal() {
      const config = this.getGistConfig();
      document.getElementById('gistIdInput').value = config.gistId;
      document.getElementById('githubTokenInput').value = config.token;

      // Generate 8-char Spell of Restoration backup
      const passcode = this.generatePasscode();
      document.getElementById('passcodeDisplay').textContent = passcode;

      document.getElementById('syncModal').classList.add('open');
    }

    closeSyncModal() {
      document.getElementById('syncModal').classList.remove('open');
    }

    updateSyncBadge() {
      const btn = document.getElementById('btnOpenSync');
      const count = this.pendingReviews.length;
      if (count > 0) {
        btn.innerHTML = `☁️ 未同期 (${count})`;
        btn.classList.remove('synced');
      } else {
        const lastSync = localStorage.getItem('tanya_last_sync_time');
        btn.innerHTML = lastSync ? `✅ 同期済 (${lastSync})` : `☁️ 同期`;
        btn.classList.add('synced');
      }
    }

    async pushToGist() {
      const { gistId, token } = this.getGistConfig();
      if (!gistId || !token) {
        alert('Gist ID と Personal Access Token (PAT) を入力してください。');
        return;
      }

      const syncPayload = {
        synced_at: new Date().toISOString(),
        device: 'iPhone / Mobile',
        word_reviews: this.pendingReviews,
        starred_words: this.starredWords,
        last_day: 25
      };

      try {
        const res = await fetch(`https://api.github.com/gists/${gistId}`, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            description: 'Tanya Russian Learning Mobile Sync',
            files: {
              'tanya_progress_sync.json': {
                content: JSON.stringify(syncPayload, null, 2)
              }
            }
          })
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        // On success: clear pending and timestamp
        this.pendingReviews = [];
        localStorage.setItem('tanya_pending_reviews', '[]');
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        localStorage.setItem('tanya_last_sync_time', timeStr);
        this.updateSyncBadge();
        this.showToast('✅ GitHub Gist へ送信完了！');
        this.closeSyncModal();
      } catch (err) {
        console.error('Sync Error:', err);
        alert(`送信に失敗しました: ${err.message}`);
      }
    }

    async pullFromGist() {
      const { gistId, token } = this.getGistConfig();
      if (!gistId || !token) {
        alert('Gist ID と Personal Access Token を入力してください。');
        return;
      }

      try {
        const res = await fetch(`https://api.github.com/gists/${gistId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json'
          }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const file = data.files['tanya_progress_sync.json'];
        if (file && file.content) {
          const parsed = JSON.parse(file.content);
          if (parsed.starred_words && parsed.starred_words.length > 0) {
            this.starredWords = parsed.starred_words;
            localStorage.setItem('tanya_starred_words', JSON.stringify(this.starredWords));
            this.currentIndex = 0;
            this.renderCard();
          }
          this.showToast('📥 最新データを取得しました！');
          this.closeSyncModal();
        } else {
          alert('Gist に tanya_progress_sync.json が見つかりませんでした。');
        }
      } catch (err) {
        console.error('Pull Error:', err);
        alert(`取得に失敗しました: ${err.message}`);
      }
    }

    tryBackgroundAutoSync() {
      const { gistId, token } = this.getGistConfig();
      if (gistId && token && this.pendingReviews.length > 0) {
        this.pushToGist();
      }
    }

    generatePasscode() {
      const day = 25;
      const count = Math.min(this.pendingReviews.length, 99);
      const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
      let code = `D${day}-`;
      for (let i = 0; i < 4; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      return code;
    }

    showToast(message) {
      let toast = document.getElementById('toastNotice');
      if (!toast) return;
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => {
        toast.classList.remove('show');
      }, 2400);
    }
  }

  // Launch on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    window.TanyaApp = new TanyaMobileApp();
  });
})();
