/**
 * Tanya Russian Trainer - Typing-Free Quiz Engine Module
 * Supports 6 task types without text typing:
 * 1. Grammaticality Judgment (True/False keys 1/2)
 * 2. Fill-in-the-blank (2-4 choices keys 1-4)
 * 3. Sentence Builder (Ordered token clicks)
 * 4. Error Spotter (Click wrong word)
 * 5. Matching (Connect pairs)
 * 6. Listening Check (Audio + choices)
 * Measures reaction time in milliseconds.
 * NO buzzer sounds, NO harsh red X marks.
 */

class QuizEngine {
  constructor() {
    this.container = null;
    this.quizItems = [];
    this.currentIndex = 0;
    this.results = [];
    this.startTime = 0;
    this.onQuizComplete = null;
    this.isAnswered = false;
    this.selectedBuilderTokens = [];

    // Reaction Time 4-Layer Calibration State
    this.isPaused = false;
    this.pauseStartTime = 0;
    this.accumulatedPauseMs = 0;
    this.wasTabHiddenOrBlurred = false;
    this.liveTimerInterval = null;
    this._listenersBound = false;

    this.bindVisibilityListeners();
  }

  bindVisibilityListeners() {
    if (this._listenersBound) return;
    this._listenersBound = true;

    const onHidden = () => {
      if (!this.isAnswered && this.startTime > 0 && !this.isPaused) {
        this.isPaused = true;
        this.pauseStartTime = performance.now();
        this.wasTabHiddenOrBlurred = true;
      }
    };

    const onVisible = () => {
      if (!this.isAnswered && this.isPaused) {
        this.accumulatedPauseMs += (performance.now() - this.pauseStartTime);
        this.isPaused = false;
      }
    };

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) onHidden();
      else onVisible();
    });

    window.addEventListener('blur', () => onHidden());
    window.addEventListener('focus', () => onVisible());
  }

  startLiveTimer() {
    this.stopLiveTimer();
    const liveTimer = this.container.querySelector('#rtLiveTimer');
    if (!liveTimer) return;

    this.liveTimerInterval = setInterval(() => {
      if (this.isAnswered) {
        this.stopLiveTimer();
        return;
      }
      if (this.isPaused) {
        liveTimer.innerHTML = `⏸ <span style="color:#94a3b8;">一時停止中 (フォーカス外)</span>`;
        return;
      }
      const rawElapsed = performance.now() - this.startTime;
      const currentMs = Math.max(0, Math.round(rawElapsed - this.accumulatedPauseMs));
      const sec = (currentMs / 1000).toFixed(1);
      if (currentMs >= 90000) {
        liveTimer.innerHTML = `⏸ <span style="color:#94a3b8;">${sec}秒 (熟考・平常速度統計除外)</span>`;
      } else if (currentMs < 35000) {
        // Standard comfortable thinking zone (12s - 35s is normal and encouraged)
        liveTimer.innerHTML = `⏱ <span style="color:#38bdf8;">${sec}秒</span>`;
      } else if (currentMs < 60000) {
        liveTimer.innerHTML = `⏱ <span style="color:#a78bfa;">${sec}秒 (丁寧な検討)</span>`;
      } else {
        liveTimer.innerHTML = `⏱ <span style="color:#fbbf24;">${sec}秒 (構造精査)</span>`;
      }
    }, 100);
  }

  stopLiveTimer() {
    if (this.liveTimerInterval) {
      clearInterval(this.liveTimerInterval);
      this.liveTimerInterval = null;
    }
  }

  init(containerElement, items = [], onQuizComplete = null) {
    this.container = containerElement;
    this.quizItems = items;
    this.currentIndex = 0;
    this.results = [];
    this.onQuizComplete = onQuizComplete;
    this.isAnswered = false;
    this.selectedBuilderTokens = [];

    if (this.quizItems.length === 0) {
      if (this.onQuizComplete) this.onQuizComplete([]);
      return;
    }

    this.renderCurrentQuestion();
  }

  renderCurrentQuestion() {
    if (!this.container) return;
    if (this.currentIndex >= this.quizItems.length) {
      if (this.onQuizComplete) this.onQuizComplete(this.results);
      return;
    }

    const item = this.quizItems[this.currentIndex];
    this.isAnswered = false;
    this.startTime = performance.now();
    this.isPaused = false;
    this.pauseStartTime = 0;
    this.accumulatedPauseMs = 0;
    this.wasTabHiddenOrBlurred = false;

    const progressFraction = `${this.currentIndex + 1} / ${this.quizItems.length}`;
    
    let questionBodyHtml = '';

    switch (item.type) {
      case 'grammaticality':
        questionBodyHtml = this.renderGrammaticality(item);
        break;
      case 'fill_in_blank':
      case 'single_choice':
        questionBodyHtml = this.renderFillInBlank(item);
        break;
      case 'sentence_builder':
        questionBodyHtml = this.renderSentenceBuilder(item);
        break;
      case 'error_spotter':
        questionBodyHtml = this.renderErrorSpotter(item);
        break;
      case 'matching':
        questionBodyHtml = this.renderMatching(item);
        break;
      case 'listening_check':
        questionBodyHtml = this.renderListeningCheck(item);
        break;
      default:
        questionBodyHtml = this.renderFillInBlank(item);
        break;
    }

    const sData = window.LessonPlayer?.sessionData;
    const dayNum = sData?.day_index || sData?.day || (sData?.session_id?.match(/day(\d+)_/)?.[1]) || (window.App?.selectedDay) || 15;
    const sType = sData?.typeKey || (sData?.session_id?.match(/day\d+_([a-z]+)/)?.[1]) || 'noon';
    const timeMap = { morning: '朝', noon: '昼', evening: '夜', story: '回想録' };
    const timeLabel = timeMap[sType] || '昼';
    const dayContext = `Day ${dayNum} ［${timeLabel}］`;

    this.container.innerHTML = `
      <div class="quiz-container">
        <div class="quiz-header">
          <span class="quiz-progress-text">📅 ${dayContext} 確かめる (第${this.currentIndex + 1}問 / 全${this.quizItems.length}問)</span>
          <span class="rt-timer-badge" id="rtLiveTimer">⏱ 計測中...</span>
        </div>

        ${questionBodyHtml}

        <div id="quizFeedbackArea"></div>

        <div class="quiz-footer" id="quizFooterArea" style="display: none;">
          <button class="quiz-next-btn" id="quizNextBtn">
            <span>次へ進む</span>
            <kbd class="kbd-badge">Enter / N / J</kbd>
          </button>
        </div>
      </div>
    `;

    this.attachQuestionEvents(item);
    this.startLiveTimer();
  }

  // 1. Grammaticality Judgment
  renderGrammaticality(item) {
    return `
      <div class="quiz-prompt-card">
        <div class="quiz-prompt-tag">文法性判断 (正しいロシア語文ですか？)</div>
        <div class="quiz-prompt-ru ru-text">${item.ru}</div>
      </div>
      <div class="quiz-binary-group">
        <button class="quiz-choice-btn" id="btnTrue" data-val="true">
          <span>⭕ 正しい (Да)</span>
          <kbd class="kbd-badge">1</kbd>
        </button>
        <button class="quiz-choice-btn" id="btnFalse" data-val="false">
          <span>❌ 誤りがある (Нет)</span>
          <kbd class="kbd-badge">2</kbd>
        </button>
      </div>
    `;
  }

  // 2. Fill in the Blank / Single Choice
  renderFillInBlank(item) {
    const rawStem = item.ru_stem || item.ru || (item.prompt ? item.prompt.replace(/\n/g, '<br>') : "") || "";
    const promptTag = item.prompt_tag || (item.type === 'single_choice' ? '選択問題 (適切な形を選んでください)' : '穴埋め選択 (空欄に入る適切な形を選んでください)');
    return `
      <div class="quiz-prompt-card">
        <div class="quiz-prompt-tag">${promptTag}</div>
        <div class="quiz-prompt-ru ru-text">${rawStem}</div>
        ${item.translation ? `<div class="quiz-prompt-ja" style="margin-top:6px; font-size:0.9rem; color:var(--text-muted);">${item.translation}</div>` : ''}
      </div>
      <div class="quiz-options-grid">
        ${(item.options || []).map((opt, idx) => `
          <button class="quiz-choice-btn" data-opt-idx="${idx}">
            <span class="ru-text">${opt}</span>
            <kbd class="kbd-badge">${idx + 1}</kbd>
          </button>
        `).join('')}
      </div>
    `;
  }

  // 3. Sentence Builder
  renderSentenceBuilder(item) {
    this.selectedBuilderTokens = [];

    // Scramble tokens so they never start in the answer order
    const original = (item.tokens || []).map((t, idx) => ({ token: t, origIdx: idx }));
    let shuffled = [...original];

    if (shuffled.length > 1) {
      let attempts = 0;
      do {
        for (let i = shuffled.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        attempts++;
      } while (attempts < 10 && shuffled.every((s, i) => s.origIdx === i));
    }
    this.shuffledBuilderList = shuffled;

    return `
      <div class="quiz-prompt-card">
        <div class="quiz-prompt-tag">並べ替え (数字キーまたはクリックで文を組み立ててください)</div>
        <div class="quiz-prompt-ja">${item.translation || "日本語訳に合わせて組み立ててください"}</div>
      </div>
      <div class="sentence-builder-tray" id="builderTray">
        <span style="color:var(--text-muted); font-size:0.86rem;">下の単語を順に選んでください（数字キー 1〜${shuffled.length}）</span>
      </div>
      <div class="sentence-builder-bank" id="builderBank">
        ${shuffled.map((entry, bankIdx) => `
          <button class="builder-token-badge ru-text" data-token="${entry.token}" data-bank-idx="${bankIdx}">
            <kbd class="kbd-badge" style="font-size:0.75rem; padding:1px 6px; margin-right:4px;">${bankIdx + 1}</kbd>
            <span>${entry.token}</span>
          </button>
        `).join('')}
      </div>
      <div style="text-align:center; margin-top:8px;">
        <button id="builderUndoBtn" style="background:transparent; border:1px solid var(--border-color); color:var(--text-muted); padding:4px 10px; border-radius:4px; font-size:0.78rem; cursor:pointer;">
          ↩ ひとつ戻す (Backspace)
        </button>
      </div>
    `;
  }

  // 4. Error Spotter
  renderErrorSpotter(item) {
    return `
      <div class="quiz-prompt-card">
        <div class="quiz-prompt-tag">誤り探し (文法的に間違っている単語の数字キーまたはクリックしてください)</div>
        <div class="error-spotter-tokens">
          ${item.sentence_tokens.map((tok, idx) => `
            <button class="spotter-token ru-text" data-spot-idx="${idx}">
              <kbd class="kbd-badge" style="font-size:0.72rem; padding:1px 6px; margin-bottom:2px;">${idx + 1}</kbd>
              <span>${tok.text}</span>
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  // 5. Interactive Two-Column Matching Pairs
  renderMatching(item) {
    const pairs = item.pairs || [];
    this.matchingPairs = pairs.map((p, idx) => ({ id: `${idx}`, left: p.left, right: p.right }));
    
    // Strip parenthesized Japanese translation/notes so cards test Russian without dead giveaways,
    // while preserving Russian disambiguation annotations such as (слушать) or (женщина)
    const cleanRu = (text) => {
      if (!text) return '';
      const hasJapanese = /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/;
      return text.replace(/\s*\(([^\)]*)\)/g, (match, p1) => {
        if (hasJapanese.test(p1)) return '';
        return ` (${p1.trim()})`;
      }).trim();
    };

    // Left items in original order
    const leftItems = this.matchingPairs.map((p, idx) => ({ id: p.id, text: cleanRu(p.left), key: `${idx + 1}` }));
    
    // Right items pseudo-randomly shuffled
    const rightShuffled = [...this.matchingPairs].sort((a, b) => {
      return ((parseInt(a.id, 10) * 7 + 3) % 11) - ((parseInt(b.id, 10) * 7 + 3) % 11);
    });
    const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
    const rightItems = rightShuffled.map((p, idx) => {
      return { id: p.id, text: cleanRu(p.right), key: letters[idx] || `${idx + 5}` };
    });

    let col1Title = '語句 (左側)';
    let col2Title = '対応形 (右側)';

    const prompt = item.prompt || '';
    if (prompt.includes('体') || prompt.includes('НСВ') || prompt.includes('完了')) {
      col1Title = '不完了体 (НСВ: 過程・反復)';
      col2Title = '完了体 (СВ: 達成・結果)';
    } else if (prompt.includes('移動') || prompt.includes('接頭')) {
      col1Title = '接頭辞つき移動動詞';
      col2Title = '意味・ニュアンス';
    } else if (prompt.includes('命令')) {
      col1Title = '主語・動詞 (原形)';
      col2Title = '命令形 (Императив)';
    } else if (prompt.includes('条件法')) {
      col1Title = '主語 (代名詞・性)';
      col2Title = '条件法 (過去形 + бы)';
    } else if (prompt.includes('形動詞')) {
      col1Title = '被修飾名詞 (性・数)';
      col2Title = '能動形動詞 (一致形)';
    } else if (prompt.includes('造格') || prompt.includes('前置詞 с')) {
      col1Title = '名詞 (主格)';
      col2Title = '前置詞 с + 造格';
    } else if (prompt.includes('比較級')) {
      col1Title = '原級 (形容詞)';
      col2Title = '比較級';
    } else if (prompt.includes('関係代名詞')) {
      col1Title = '先行詞 (名詞)';
      col2Title = '関係詞節 (который)';
    } else if (prompt.includes('数詞')) {
      col1Title = '数詞';
      col2Title = '結合名詞 (格変化)';
    } else if (prompt.includes('否定') || prompt.includes('生格')) {
      col1Title = '肯定表現 (主格/対格)';
      col2Title = '否定表現 (нет + 生格)';
    } else if (prompt.includes('形容詞と名詞')) {
      col1Title = '修飾形容詞';
      col2Title = '被修飾名詞';
    } else if (prompt.includes('動詞') || prompt.includes('主語')) {
      col1Title = '主語 (代名詞)';
      col2Title = '動詞活用形';
    }

    return `
      <div class="quiz-prompt-card" style="padding:10px 16px; margin-bottom:12px;">
        <div class="quiz-prompt-tag">🎹 マッチング (${item.prompt || "対応するペアを結びつけましょう"})</div>
        <div style="font-size:0.86rem; color:var(--text-secondary); margin-top:4px;">
          左列の単語（1〜4）を選び、対応する右列のペア（A〜D または クリック）を結びつけてください。
        </div>
      </div>
      <div class="matching-board">
        <div class="matching-col">
          <div class="matching-col-header">${col1Title}</div>
          ${leftItems.map(p => `
            <div class="matching-card matching-left" data-pair-id="${p.id}" data-key="${p.key}">
              <span class="matching-card-text ru-text">${p.text}</span>
              <kbd class="kbd-badge">${p.key}</kbd>
            </div>
          `).join('')}
        </div>
        <div class="matching-col">
          <div class="matching-col-header">${col2Title}</div>
          ${rightItems.map(p => `
            <div class="matching-card matching-right" data-pair-id="${p.id}" data-key="${p.key}">
              <span class="matching-card-text ru-text">${p.text}</span>
              <kbd class="kbd-badge">${p.key}</kbd>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // 6. Listening Check
  renderListeningCheck(item) {
    return `
      <div class="quiz-prompt-card">
        <div class="quiz-prompt-tag">リスニング判定 (音声を聴いて適切なものを選んでください)</div>
        <button class="play-audio-btn" id="listenPromptBtn" style="margin: 10px auto;">
          <span>▶ 音声を聴く</span>
          <kbd class="kbd-badge">Space</kbd>
        </button>
      </div>
      <div class="quiz-options-grid">
        ${item.options.map((opt, idx) => `
          <button class="quiz-choice-btn" data-opt-idx="${idx}">
            <span>${opt}</span>
            <kbd class="kbd-badge">${idx + 1}</kbd>
          </button>
        `).join('')}
      </div>
    `;
  }

  attachQuestionEvents(item) {
    if (item.type === 'grammaticality') {
      const btnT = this.container.querySelector('#btnTrue');
      const btnF = this.container.querySelector('#btnFalse');
      if (btnT) btnT.onclick = () => this.handleAnswer(true === item.is_correct, item);
      if (btnF) btnF.onclick = () => this.handleAnswer(false === item.is_correct, item);
    } else if (item.type === 'fill_in_blank' || item.type === 'single_choice' || (item.options && item.options.length > 0)) {
      const btns = this.container.querySelectorAll('[data-opt-idx]');
      const correctIdx = item.correct_index !== undefined ? item.correct_index : item.answer_index;
      btns.forEach(btn => {
        btn.onclick = () => {
          const idx = parseInt(btn.dataset.optIdx, 10);
          this.handleAnswer(idx === correctIdx, item, btn);
        };
      });
    } else if (item.type === 'sentence_builder') {
      const bank = this.container.querySelector('#builderBank');
      const tray = this.container.querySelector('#builderTray');
      const undoBtn = this.container.querySelector('#builderUndoBtn');

      bank.querySelectorAll('.builder-token-badge').forEach(btn => {
        btn.onclick = () => {
          if (this.isAnswered) return;
          const token = btn.dataset.token;
          btn.style.visibility = 'hidden';
          this.selectedBuilderTokens.push({ token, btn });

          // Update tray
          tray.innerHTML = this.selectedBuilderTokens.map(t => `
            <span class="builder-token-badge ru-text" style="background:var(--bg-highlight);">${t.token}</span>
          `).join('');

          // Check if complete
          if (this.selectedBuilderTokens.length === item.tokens.length) {
            const builtRu = this.selectedBuilderTokens.map(t => t.token).join(' ');
            const targetRu = item.tokens.join(' ');
            this.handleAnswer(builtRu === targetRu, item);
          }
        };
      });

      if (undoBtn) {
        undoBtn.onclick = () => {
          if (this.selectedBuilderTokens.length > 0) {
            const last = this.selectedBuilderTokens.pop();
            last.btn.style.visibility = 'visible';
            tray.innerHTML = this.selectedBuilderTokens.map(t => `
              <span class="builder-token-badge ru-text" style="background:var(--bg-highlight);">${t.token}</span>
            `).join('') || '<span style="color:var(--text-muted); font-size:0.86rem;">下の単語を順にクリックしてください</span>';
          }
        };
      }
    } else if (item.type === 'error_spotter') {
      const tokens = this.container.querySelectorAll('.spotter-token');
      tokens.forEach(tok => {
        tok.onclick = () => {
          const idx = parseInt(tok.dataset.spotIdx, 10);
          const isErr = item.sentence_tokens[idx].has_error;
          this.handleAnswer(isErr, item, tok);
        };
      });
    } else if (item.type === 'matching') {
      this.selectedLeftCard = null;
      this.matchedCount = 0;
      const totalPairs = (item.pairs || []).length;
      
      const leftCards = this.container.querySelectorAll('.matching-left');
      const rightCards = this.container.querySelectorAll('.matching-right');

      leftCards.forEach(card => {
        card.onclick = () => {
          if (card.classList.contains('matched')) return;
          leftCards.forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          this.selectedLeftCard = card;
          const rawText = card.querySelector('.matching-card-text')?.textContent || '';
          const speechRu = this.extractRussianSpeechText(rawText);
          if (window.TTSPlayer && speechRu) window.TTSPlayer.speakWord(speechRu);
        };
      });

      rightCards.forEach(card => {
        card.onclick = () => {
          if (card.classList.contains('matched')) return;

          const rightRaw = card.querySelector('.matching-card-text')?.textContent || '';
          const rightSpeechRu = this.extractRussianSpeechText(rightRaw);

          if (!this.selectedLeftCard) {
            // Prompt user to select left card first, but speak the right word if clicked
            card.classList.add('selected');
            setTimeout(() => card.classList.remove('selected'), 300);
            if (window.TTSPlayer && rightSpeechRu) window.TTSPlayer.speakWord(rightSpeechRu);
            return;
          }

          const leftPairId = this.selectedLeftCard.dataset.pairId;
          const rightPairId = card.dataset.pairId;

          if (leftPairId === rightPairId) {
            // MATCH!
            const matchedLeft = this.selectedLeftCard;
            matchedLeft.classList.remove('selected');
            matchedLeft.classList.add('matched');
            card.classList.add('matched');

            const leftBadge = matchedLeft.querySelector('.kbd-badge');
            if (leftBadge) leftBadge.textContent = '✓';
            const rightBadge = card.querySelector('.kbd-badge');
            if (rightBadge) rightBadge.textContent = '✓';

            const leftRaw = matchedLeft.querySelector('.matching-card-text')?.textContent || '';
            const leftSpeechRu = this.extractRussianSpeechText(leftRaw);

            // Pair matched: Speak the right card (inflected/corresponding form) prioritized over left base form
            const pairSpeechRu = rightSpeechRu || leftSpeechRu;
            if (window.TTSPlayer && pairSpeechRu) window.TTSPlayer.speakWord(pairSpeechRu);

            this.selectedLeftCard = null;
            this.matchedCount++;

            if (this.matchedCount >= totalPairs) {
              // ALL MATCHED!
              setTimeout(() => {
                this.handleAnswer(true, item);
              }, 400);
            }
          } else {
            // MISMATCH!
            const prevLeft = this.selectedLeftCard;
            prevLeft.classList.add('error');
            card.classList.add('error');
            if (window.TTSPlayer && rightSpeechRu) window.TTSPlayer.speakWord(rightSpeechRu);
            setTimeout(() => {
              prevLeft.classList.remove('error', 'selected');
              card.classList.remove('error');
            }, 500);
            this.selectedLeftCard = null;
          }
        };
      });
    } else if (item.type === 'listening_check') {
      const listenBtn = this.container.querySelector('#listenPromptBtn');
      if (listenBtn && item.audio_text && window.TTSPlayer) {
        listenBtn.onclick = () => window.TTSPlayer.speakSentence(item.audio_text);
        // Autoplay once
        window.TTSPlayer.speakSentence(item.audio_text);
      }
      const btns = this.container.querySelectorAll('[data-opt-idx]');
      btns.forEach(btn => {
        btn.onclick = () => {
          const idx = parseInt(btn.dataset.optIdx, 10);
          this.handleAnswer(idx === item.correct_index, item, btn);
        };
      });
    }

    const nextBtn = this.container.querySelector('#quizNextBtn');
    if (nextBtn) {
      nextBtn.onclick = () => this.advanceToNext();
    }
  }

  handleAnswer(isCorrect, item, targetElement = null) {
    if (this.isAnswered) return;
    this.isAnswered = true;
    this.stopLiveTimer();

    const rawElapsed = performance.now() - this.startTime;
    let effectiveRtMs = Math.round(rawElapsed - this.accumulatedPauseMs);
    if (this.isPaused) {
      effectiveRtMs = Math.round(this.pauseStartTime - this.startTime - this.accumulatedPauseMs);
    }
    effectiveRtMs = Math.max(0, effectiveRtMs);

    // Interruption heuristic: tab was hidden/blurred OR response took >= 90.0 seconds
    const isInterruption = this.wasTabHiddenOrBlurred || effectiveRtMs >= 90000;

    // Update live timer badge
    const liveTimer = this.container.querySelector('#rtLiveTimer');
    if (liveTimer) {
      if (isInterruption) {
        liveTimer.innerHTML = `⏸ <span style="color:#94a3b8;">${(effectiveRtMs / 1000).toFixed(1)}秒 (熟考・平常速度統計除外)</span>`;
      } else if (effectiveRtMs < 12000) {
        liveTimer.innerHTML = `⚡ <span style="color:#10b981;">${(effectiveRtMs / 1000).toFixed(1)}秒 (スムーズ想起)</span>`;
      } else if (effectiveRtMs < 35000) {
        liveTimer.innerHTML = `💡 <span style="color:#38bdf8;">${(effectiveRtMs / 1000).toFixed(1)}秒 (着実な解答)</span>`;
      } else if (effectiveRtMs < 60000) {
        liveTimer.innerHTML = `📖 <span style="color:#a78bfa;">${(effectiveRtMs / 1000).toFixed(1)}秒 (丁寧な構造精査)</span>`;
      } else {
        liveTimer.innerHTML = `⏳ <span style="color:#fbbf24;">${(effectiveRtMs / 1000).toFixed(1)}秒 (じっくり熟考)</span>`;
      }
    }

    // Record result
    this.results.push({
      id: item.id,
      tag: item.tag || 'general',
      is_correct: isCorrect,
      rt_ms: effectiveRtMs,
      is_interruption: isInterruption
    });

    // Gentle visual feedback (NO harsh X or punishment)
    if (targetElement) {
      if (isCorrect) {
        targetElement.classList.add('correct-feedback');
      } else {
        targetElement.classList.add('gentle-feedback');
      }
    }

    // Determine full correct Russian sentence and wrong sentence (if any)
    let fullCorrectSentence = "";
    let wrongSentence = "";

    if (item.type === 'grammaticality') {
      if (item.is_correct === false) {
        wrongSentence = item.ru;
        fullCorrectSentence = item.correct_ru || item.ru;
      } else {
        fullCorrectSentence = item.ru;
      }
    } else if ((item.type === 'fill_in_blank' || item.type === 'single_choice' || item.options) && item.options) {
      const correctIdx = item.correct_index !== undefined ? item.correct_index : item.answer_index;
      if (item.ru_stem && item.ru_stem.includes('___') && correctIdx !== undefined && item.options[correctIdx]) {
        fullCorrectSentence = item.ru_stem.replace(/___/g, item.options[correctIdx]);
      } else if (correctIdx !== undefined && item.options[correctIdx]) {
        fullCorrectSentence = item.ru || (item.ru_stem ? item.ru_stem.replace(/___/g, item.options[correctIdx]) : item.options[correctIdx]);
      } else {
        fullCorrectSentence = item.ru || item.ru_stem || "";
      }
    } else if (item.type === 'sentence_builder' && item.tokens) {
      fullCorrectSentence = item.tokens.join(' ');
    } else if (item.type === 'error_spotter' && item.sentence_tokens) {
      fullCorrectSentence = item.sentence_tokens.map(t => t.correct || t.text).join(' ');
      wrongSentence = item.sentence_tokens.map(t => t.text).join(' ');
    } else if (item.type === 'matching' && item.pairs) {
      fullCorrectSentence = item.pairs.map(p => `${p.left} ⇔ ${p.right}`).join(', ');
      const ruList = item.pairs
        .map(p => {
          const l = this.extractRussianSpeechText(p.left);
          const r = this.extractRussianSpeechText(p.right);
          if (l && r) return `${l} — ${r}`;
          return l || r;
        })
        .filter(Boolean);
      this.lastSpokenSentence = ruList.join('. ');
    } else {
      fullCorrectSentence = item.ru || "";
      this.lastSpokenSentence = fullCorrectSentence;
    }

    const fmt = window.formatRussianClickable || (t => t);
    const parsed = this.parseExplanation(item.explanation);
    const handbookTag = this.getCurrentQuestionTag();

    // Build Russian sentence header HTML
    let sentenceHeaderHtml = '';
    if (wrongSentence && wrongSentence !== fullCorrectSentence) {
      sentenceHeaderHtml = `
        <div style="margin-bottom:8px; display:flex; flex-direction:column; gap:4px;">
          <div style="display:flex; align-items:baseline; gap:8px;">
            <span class="tag-badge" style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid #10b981; font-size:0.75rem; font-weight:700;">✔ 正しいロシア語文</span>
            <div class="quiz-feedback-ru ru-text" style="font-size:1.25rem; font-weight:700; color:#a7f3d0;">
              ${fmt(fullCorrectSentence)}
            </div>
          </div>
          <div style="display:flex; align-items:baseline; gap:8px; font-size:0.92rem; color:var(--text-muted); padding-left:2px;">
            <span class="tag-badge" style="background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid #ef4444; font-size:0.72rem; font-weight:600;">✖ 提示文（誤文）</span>
            <span class="ru-text" style="text-decoration:line-through; opacity:0.75;">
              ${fmt(wrongSentence)}
            </span>
          </div>
        </div>
      `;
    } else if (fullCorrectSentence && !fullCorrectSentence.includes('⇔')) {
      sentenceHeaderHtml = `
        <div class="quiz-feedback-ru ru-text" style="font-size:1.25rem; font-weight:700; color:#ffffff; margin-bottom:4px;">
          ${fmt(fullCorrectSentence)}
        </div>
      `;
    }

    // Build transparent RT badge
    let rtBadgeHtml = '';
    if (isInterruption) {
      rtBadgeHtml = `<span class="tag-badge" style="background:rgba(148,163,184,0.18); color:#cbd5e1; border:1px solid #64748b; font-size:0.75rem; font-weight:600;" title="90秒以上の熟考や画面離脱が検知されたため、平常時の速度統計からは除外されます（ペナルティなし）">⏸ 熟考・離脱判定 (${(effectiveRtMs / 1000).toFixed(1)}s・統計除外)</span>`;
    } else if (effectiveRtMs < 12000) {
      rtBadgeHtml = `<span class="tag-badge" style="background:rgba(16,185,129,0.18); color:#10b981; border:1px solid #10b981; font-size:0.75rem; font-weight:700;">⚡ スムーズ想起 (${(effectiveRtMs / 1000).toFixed(1)}s)</span>`;
    } else if (effectiveRtMs < 35000) {
      rtBadgeHtml = `<span class="tag-badge" style="background:rgba(56,189,248,0.18); color:#38bdf8; border:1px solid #38bdf8; font-size:0.75rem; font-weight:600;">💡 着実な解答 (${(effectiveRtMs / 1000).toFixed(1)}s)</span>`;
    } else if (effectiveRtMs < 60000) {
      rtBadgeHtml = `<span class="tag-badge" style="background:rgba(167,139,250,0.18); color:#a78bfa; border:1px solid #a78bfa; font-size:0.75rem; font-weight:600;">📖 丁寧な構造精査 (${(effectiveRtMs / 1000).toFixed(1)}s)</span>`;
    } else {
      rtBadgeHtml = `<span class="tag-badge" style="background:rgba(251,191,36,0.18); color:#fbbf24; border:1px solid #fbbf24; font-size:0.75rem; font-weight:600;">⏳ じっくり熟考 (${(effectiveRtMs / 1000).toFixed(1)}s)</span>`;
    }

    // Display gentle explanation card
    const feedbackArea = this.container.querySelector('#quizFeedbackArea');
    if (feedbackArea) {
      const title = isCorrect 
        ? (isInterruption 
            ? "✨ 正解です！じっくり確認できましたね。" 
            : (effectiveRtMs >= 35000 
                ? "✨ 正解です！文構造を丁寧に読み解けましたね。" 
                : (effectiveRtMs >= 12000 
                    ? "✨ 正解です！着実にしっかり身についていますね。" 
                    : "✨ 正解です！とてもスムーズな判断です。"))) 
        : "💡 ワンポイント解説 (確認して次に進みましょう)";
      feedbackArea.innerHTML = `
        <div class="gentle-explanation-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <div class="explanation-title">${title}</div>
              ${rtBadgeHtml}
            </div>
            <button class="quiz-replay-btn" id="quizFeedbackReplayBtn" title="音声をもう一度聴く (R)">
              <span>🔊 音声を聴く</span>
              <kbd class="kbd-badge" style="font-size:0.72rem; padding:1px 5px; margin-left:4px;">R</kbd>
            </button>
          </div>
          ${sentenceHeaderHtml}
          ${item.translation ? `
            <div class="quiz-feedback-ja" style="font-size:0.95rem; color:#ffe599; font-weight:600; margin-bottom:6px;">
              🇯🇵 ${item.translation}
            </div>
          ` : ''}
          ${parsed.general ? `
            <div class="quiz-feedback-explain" style="font-size:0.88rem; color:#ded6c5; line-height:1.6; border-top:1px dashed var(--border-color); padding-top:6px;">
              ${fmt(parsed.general)}
            </div>
          ` : ''}
          ${parsed.thoughtStep ? `
            <div class="quiz-thought-step-card">
              <div class="step-title">💡 思考ステップ (思考回路の定着)</div>
              <div>${fmt(parsed.thoughtStep)}</div>
            </div>
          ` : ''}
          ${parsed.trapAnalysis ? `
            <div class="quiz-trap-analysis-card">
              <div class="trap-title">⚠️ 誤答トラップ・落とし穴分析</div>
              <div>${fmt(parsed.trapAnalysis)}</div>
            </div>
          ` : ''}
          ${item.vocab_notes ? `
            <div class="quiz-feedback-vocab" style="font-size:0.82rem; color:var(--emerald-light); margin-top:6px;">
              📖 単語メモ: ${fmt(item.vocab_notes)}
            </div>
          ` : ''}
          ${handbookTag ? `
            <div style="margin-top:10px;">
              <div class="handbook-link-badge" id="quizFeedbackHandbookLink" data-tag="${handbookTag}" title="文法ハンドブックを開く (H)">
                <span>📖 文法ハンドブックで確認: <strong>${this.getHandbookTagTitle(handbookTag)}</strong> →</span>
                <kbd class="kbd-badge" style="font-size:0.7rem; padding:1px 5px; margin-left:4px;">H</kbd>
              </div>
            </div>
          ` : ''}
        </div>
      `;

      const replayBtn = feedbackArea.querySelector('#quizFeedbackReplayBtn');
      if (replayBtn) {
        replayBtn.onclick = () => this.replayLastSentence();
      }

      const hbBtn = feedbackArea.querySelector('#quizFeedbackHandbookLink');
      if (hbBtn && handbookTag) {
        hbBtn.onclick = () => {
          if (window.Handbook) {
            window.Handbook.openTag(handbookTag);
          }
        };
      }
    }

    // Show Next button
    const footer = this.container.querySelector('#quizFooterArea');
    if (footer) {
      footer.style.display = 'flex';
    }

    // Auto play audio of the correct Russian sentence for hearing reinforcement
    if (window.TTSPlayer && fullCorrectSentence && !fullCorrectSentence.includes('⇔')) {
      window.TTSPlayer.speakSentence(fullCorrectSentence);
    }
  }

  parseExplanation(text) {
    if (!text) return { general: "文脈と語尾の結びつきに注目してください。", thoughtStep: null, trapAnalysis: null };

    const raw = String(text);
    const stepRegex = /(?:💡\s*)?(?:思考ステップ|思考プロセス)[：:]/;
    const trapRegex = /(?:⚠️\s*)?(?:誤答トラップ|ここが落とし穴|落とし穴|注意点)[：:]/;

    const stepMatch = raw.search(stepRegex);
    const trapMatch = raw.search(trapRegex);

    let general = raw;
    let thoughtStep = null;
    let trapAnalysis = null;

    if (stepMatch !== -1 && trapMatch !== -1) {
      if (stepMatch < trapMatch) {
        general = raw.substring(0, stepMatch).trim();
        thoughtStep = raw.substring(stepMatch, trapMatch).replace(stepRegex, '').trim();
        trapAnalysis = raw.substring(trapMatch).replace(trapRegex, '').trim();
      } else {
        general = raw.substring(0, trapMatch).trim();
        trapAnalysis = raw.substring(trapMatch, stepMatch).replace(trapRegex, '').trim();
        thoughtStep = raw.substring(stepMatch).replace(stepRegex, '').trim();
      }
    } else if (stepMatch !== -1) {
      general = raw.substring(0, stepMatch).trim();
      thoughtStep = raw.substring(stepMatch).replace(stepRegex, '').trim();
    } else if (trapMatch !== -1) {
      general = raw.substring(0, trapMatch).trim();
      trapAnalysis = raw.substring(trapMatch).replace(trapRegex, '').trim();
    }

    return { general, thoughtStep, trapAnalysis };
  }

  getHandbookTagTitle(tag) {
    if (!tag) return '文法解説';
    const tagMap = {
      'noun.soft_sign': '「-ь」語尾名詞の性別完全攻略',
      'noun.irregular_fleeting': '出没音 (e/o) と特殊複数 (-ья)',
      'verb.motion_prefixed': '移動動詞の16大接頭辞 空間ベクトルマップ',
      'verb.government': '動詞の格支配 (露検2級 最重要合否分水嶺)',
      'verb.aspect_nsv': '動詞のアスペクト（体）：不完了体 vs 完了体',
      'verb.aspect_sv': '動詞のアスペクト（体）：不完了体 vs 完了体',
      'verb.motion_uni': '移動動詞：単一方向 vs 多方向',
      'verb.motion_multi': '移動動詞：単一方向 vs 多方向',
      'verb.irregular': '重要不規則動詞の活用',
      'verb.imperative': '命令形の用法と活用',
      'case.nom': '主格 (Именительный падеж)',
      'case.gen': '生格 (Родительный падеж)',
      'case.dat': '与格 (Дательный падеж)',
      'case.acc': '対格 (Винительный падеж)',
      'case.ins': '造格 (Творительный падеж)',
      'case.prp': '前置格 (Предложный падеж)',
      'prep.multi_case': '多格支配前置詞の使い分け',
      'adj.declension': '形容詞の性・数・格変化',
      'adj.short_government': '形容詞短尾形の格支配',
      'numeral.agreement': '数詞と名詞の一致ルール',
      'numeral.declension_all': '数詞の全格変化',
      'numeral.collective': '集合数詞 (двое, трое) と оба / обе',
      'syntax.relative': '関係代名詞 который',
      'syntax.conditional': '条件法・仮定法 (бы)',
      'syntax.subordinate': '目的・譲歩・複文の従属節 (чтобы, хотя)',
      'syntax.impersonal': '無人称構文・心理状態述語 (Мне нужно, можно)',
      'pronoun.indefinite': '不定代名詞 (-то, -нибудь, кое-)',
      'pronoun.indef': '不定代名詞 (-то, -нибудь, кое-)',
      'pronoun.negative': '否定代名詞・否定副詞 (никто, некого)',
      'pronoun.neg': '否定代名詞・否定副詞 (никто, некого)',
      'participle.active': '能動形動詞 (Действительные причастия)',
      'participle.passive': '受動形動詞 (Страдательные причастия)',
      'gerund.imperfective': '不完了体副動詞 (同時性: 〜しながら)',
      'gerund.perfective': '完了体副動詞 (先行性: 〜した後に)',
      'gerund.verbal_adverb': '副動詞構文と主語一致原則 (Деепричастия)',
      'adverbial_participle': '副動詞 (Деепричастия)',
      'syntax.adverbial': '副動詞構文 (Деепричастия)'
    };
    if (tagMap[tag]) return tagMap[tag];
    for (const k of Object.keys(tagMap)) {
      if (tag.startsWith(k) || k.startsWith(tag)) return tagMap[k];
    }
    return tag;
  }

  extractRussianSpeechText(rawText) {
    if (!rawText || typeof rawText !== 'string') return '';
    const cyrillicMatches = rawText.match(/[а-яА-ЯёЁ\u0301]+(?:[\s\-]+[а-яА-ЯёЁ\u0301]+)*/g);
    if (cyrillicMatches && cyrillicMatches.length > 0) {
      return cyrillicMatches.join(' ').trim();
    }
    return '';
  }

  getCurrentQuestionTag() {
    const item = this.quizItems[this.currentIndex];
    if (!item) return null;
    return item.tag || item.grammar_tag || (this.currentLesson && (this.currentLesson.grammar_tag || (Array.isArray(this.currentLesson.grammar_tags) && this.currentLesson.grammar_tags[0])));
  }

  replayLastSentence() {
    if (window.TTSPlayer && this.lastSpokenSentence) {
      window.TTSPlayer.speakSentence(this.lastSpokenSentence);
    }
  }

  advanceToNext() {
    this.currentIndex++;
    this.renderCurrentQuestion();
  }

  handleKeyShortcut(key) {
    const k = key.toLowerCase();

    if (this.isAnswered) {
      if (k === 'r') {
        this.replayLastSentence();
        return true;
      }
      if (k === 'h') {
        const tag = this.getCurrentQuestionTag();
        if (tag && window.Handbook) {
          window.Handbook.openTag(tag);
          return true;
        }
      }
      if (key === 'Enter' || key === ' ' || k === 'n' || k === 'j') {
        this.advanceToNext();
        return true;
      }
      return false;
    }

    const item = this.quizItems[this.currentIndex];
    if (!item) return false;

    // 'r' to replay question prompt audio
    if (k === 'r') {
      if (window.TTSPlayer) {
        const sentenceToHear = item.audio_text || item.ru || item.ru_stem || "";
        if (sentenceToHear && !sentenceToHear.includes('___')) {
          window.TTSPlayer.speakSentence(sentenceToHear);
        }
      }
      return true;
    }

    if (item.type === 'grammaticality') {
      if (key === '1') {
        const btn = this.container.querySelector('#btnTrue');
        if (btn) btn.click();
        return true;
      } else if (key === '2') {
        const btn = this.container.querySelector('#btnFalse');
        if (btn) btn.click();
        return true;
      }
    } else if (item.type === 'fill_in_blank' || item.type === 'single_choice' || item.type === 'listening_check' || (item.options && item.options.length > 0)) {
      const num = parseInt(key, 10);
      if (num >= 1 && num <= (item.options ? item.options.length : 4)) {
        const btns = this.container.querySelectorAll('.quiz-choice-btn');
        if (btns[num - 1]) {
          btns[num - 1].click();
          return true;
        }
      }
    } else if (item.type === 'matching') {
      // 1, 2, 3, 4 selects Left cards
      if (['1', '2', '3', '4'].includes(key)) {
        const card = this.container.querySelector(`.matching-left[data-key="${key}"]`);
        if (card && !card.classList.contains('matched')) {
          card.click();
          return true;
        }
      }
      // A, B, C, D (or 5, 6, 7, 8) selects Right cards
      const letterMap = { 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D', '5': 'A', '6': 'B', '7': 'C', '8': 'D' };
      const rightKey = letterMap[k];
      if (rightKey) {
        const card = this.container.querySelector(`.matching-right[data-key="${rightKey}"]`);
        if (card && !card.classList.contains('matched')) {
          card.click();
          return true;
        }
      }
    } else if (item.type === 'sentence_builder') {
      if (key === 'Backspace') {
        const undoBtn = this.container.querySelector('#builderUndoBtn');
        if (undoBtn) undoBtn.click();
        return true;
      }
      const num = parseInt(key, 10);
      const bankLen = this.shuffledBuilderList ? this.shuffledBuilderList.length : (item.tokens || []).length;
      if (num >= 1 && num <= bankLen) {
        const btn = this.container.querySelector(`.builder-token-badge[data-bank-idx="${num - 1}"]`);
        if (btn && btn.style.visibility !== 'hidden') {
          btn.click();
          return true;
        }
      }
    } else if (item.type === 'error_spotter') {
      const num = parseInt(key, 10);
      if (num >= 1 && num <= item.sentence_tokens.length) {
        const btn = this.container.querySelector(`.spotter-token[data-spot-idx="${num - 1}"]`);
        if (btn) {
          btn.click();
          return true;
        }
      }
    }

    return false;
  }
}

window.QuizEngine = new QuizEngine();
