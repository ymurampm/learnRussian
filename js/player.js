/**
 * Tanya Russian Trainer - 4-Phase Lesson Player Module
 * Orchestrates:
 * Phase 1: 出会う (Encounter / Input & Audio)
 * Phase 2: 触る (Explore / Spatial Multi-Pane & Live Mutator)
 * Phase 3: 確かめる (Verify / Typing-free Checks & Reaction Time)
 * Phase 4: 積み上がる (Record & Intimacy Wrap-up)
 */

class LessonPlayer {
  constructor() {
    this.container = null;
    this.sessionData = null;
    this.currentPhase = 1;
    this.isNonGraded = false;
    this.quizResults = [];
    this.onFinishCallback = null;
  }

  init(containerElement, sessionData, isNonGraded = false, onFinishCallback = null) {
    this.container = containerElement;
    this.sessionData = sessionData;
    this.currentPhase = 1;
    this.isNonGraded = isNonGraded;
    this.quizResults = [];
    this.onFinishCallback = onFinishCallback;

    const userSpeed = (window.App && window.App.userProfile && window.App.userProfile.tts_speed) ? window.App.userProfile.tts_speed : 0.85;
    if (window.TTSPlayer) {
      window.TTSPlayer.setRate(userSpeed);
    }

    // If story memoir session, render dedicated story view
    if (sessionData.type === 'memoir') {
      this.renderMemoirSession();
      return;
    }

    // If evening listening bath session, render dedicated bath view
    if (sessionData.type === 'listening_bath') {
      this.renderListeningBathSession();
      return;
    }

    this.renderPhase();
  }

  setPhase(phaseNum) {
    this.currentPhase = phaseNum;
    this.renderPhase();
  }

  renderPhase() {
    if (!this.container || !this.sessionData) return;

    const dayNum = this.sessionData.day_index || this.sessionData.day || (this.sessionData.session_id?.match(/day(\d+)_/)?.[1]) || (window.App?.selectedDay) || 15;
    const sessionType = this.sessionData.typeKey || (this.sessionData.session_id?.match(/(?:day\d+_|s_\d+_)?([a-z]+)/)?.[1]) || (this.sessionData.title?.includes('昼') ? 'noon' : (this.sessionData.title?.includes('夜') ? 'evening' : (this.sessionData.title?.includes('回想') ? 'story' : 'morning')));
    const timeLabelMap = { morning: '朝', noon: '昼', evening: '夜', story: '回想録', memoir: '回想録' };
    const timeLabel = timeLabelMap[sessionType] || '朝';
    const phaseNames = {
      1: '出会う',
      2: '触る',
      3: '確かめる',
      4: '積み上がる'
    };

    // Update global header capsule
    const headerDayBadge = document.getElementById('headerDayBadge');
    const headerSessionBadge = document.getElementById('headerSessionBadge');
    if (headerDayBadge) headerDayBadge.textContent = `📅 Day ${dayNum} ［${timeLabel}］`;
    if (headerSessionBadge) headerSessionBadge.textContent = `Phase ${this.currentPhase}: ${phaseNames[this.currentPhase] || ''}`;

    this.container.innerHTML = `
      <div class="player-view">
        <!-- Player Header & Stepper -->
        <div class="player-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="player-back-btn" id="playerExitBtn">← サロン (Esc)</button>
            <div class="player-day-indicator">
              <span class="day-tag">📅 Day ${dayNum} ［${timeLabel}］</span>
              <span class="phase-tag">Phase ${this.currentPhase}: ${phaseNames[this.currentPhase] || ''}</span>
            </div>
          </div>
          <div class="phase-stepper">
            <div class="phase-step ${this.currentPhase === 1 ? 'active' : (this.currentPhase > 1 ? 'completed' : '')}" id="step1">
              <span class="phase-step-num">1</span>
              <span>出会う (インプット)</span>
            </div>
            <div class="phase-step ${this.currentPhase === 2 ? 'active' : (this.currentPhase > 2 ? 'completed' : '')}" id="step2">
              <span class="phase-step-num">2</span>
              <span>触る (探索)</span>
            </div>
            <div class="phase-step ${this.currentPhase === 3 ? 'active' : (this.currentPhase > 3 ? 'completed' : '')}" id="step3">
              <span class="phase-step-num">3</span>
              <span>確かめる (チェック)</span>
            </div>
            <div class="phase-step ${this.currentPhase === 4 ? 'active' : ''}" id="step4">
              <span class="phase-step-num">4</span>
              <span>積み上がる (記録)</span>
            </div>
          </div>
          <div style="font-size:0.8rem; color:var(--gold-light); font-weight:600; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${this.sessionData.title}">
            ${this.sessionData.title}
          </div>
        </div>

        <!-- Dynamic Phase Content Area -->
        <div id="playerPhaseBody"></div>
      </div>
    `;

    const exitBtn = this.container.querySelector('#playerExitBtn');
    if (exitBtn) {
      exitBtn.onclick = () => {
        if (window.TTSPlayer) window.TTSPlayer.stop();
        if (this.onFinishCallback) this.onFinishCallback();
      };
    }

    // Allow clicking phase steps to jump between phases
    [1, 2, 3, 4].forEach(pNum => {
      const stepEl = this.container.querySelector(`#step${pNum}`);
      if (stepEl) {
        stepEl.style.cursor = 'pointer';
        stepEl.onclick = () => this.setPhase(pNum);
      }
    });

    const body = this.container.querySelector('#playerPhaseBody');
    if (this.currentPhase === 1) {
      this.renderPhase1(body);
    } else if (this.currentPhase === 2) {
      this.renderPhase2(body);
    } else if (this.currentPhase === 3) {
      this.renderPhase3(body);
    } else if (this.currentPhase === 4) {
      this.renderPhase4(body);
    }
  }

  // --------------------------------------------------------------------------
  // Speed HUD Toast & Ladder Listening Helpers
  // --------------------------------------------------------------------------
  showSpeedHudToast(icon, badge, text, durationMs = 2200) {
    let toast = document.getElementById('speedHudToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'speedHudToast';
      toast.className = 'speed-hud-toast';
      document.body.appendChild(toast);
    }
    toast.innerHTML = `
      <span class="speed-hud-icon">${icon}</span>
      <span class="speed-hud-badge">${badge}</span>
      <span class="speed-hud-desc">${text}</span>
    `;
    toast.classList.add('show');
    if (this.speedHudTimer) clearTimeout(this.speedHudTimer);
    this.speedHudTimer = setTimeout(() => {
      toast.classList.remove('show');
    }, durationMs);
  }

  syncSpeedDisplay(newRate) {
    const rateStr = `${newRate.toFixed(2)}x`;
    document.querySelectorAll('.speed-stepper-val').forEach(el => {
      el.textContent = rateStr;
    });
    document.querySelectorAll('.speed-gear-btn, .speed-pill-btn').forEach(btn => {
      const btnSpd = parseFloat(btn.dataset.speed);
      if (Math.abs(btnSpd - newRate) < 0.03) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  async adjustSpeedAndReplay(delta, customRu = null, customTokens = null, absoluteRate = null) {
    let newRate;
    if (absoluteRate !== null) {
      newRate = window.TTSPlayer ? window.TTSPlayer.setRate(absoluteRate) : absoluteRate;
    } else {
      newRate = window.TTSPlayer ? window.TTSPlayer.stepRate(delta) : 1.0;
    }

    const icon = newRate < 0.85 ? '🐢' : (newRate > 1.05 ? '🐇' : '🎵');
    const deltaStr = absoluteRate !== null ? '標準' : (delta > 0 ? `+${delta.toFixed(2)}` : `${delta.toFixed(2)}`);
    this.showSpeedHudToast(icon, `${newRate.toFixed(2)}x`, `リスニング速度変更 (${deltaStr}) ＆ 再生`);

    this.syncSpeedDisplay(newRate);

    // Save preference
    if (window.App && window.App.userProfile) {
      window.App.userProfile.tts_speed = newRate;
    }
    try {
      fetch('/api/settings/tts_speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tts_speed: newRate })
      }).catch(() => {});
    } catch (_) {}

    // Check if Bath Explain Modal is open
    const explainModal = document.getElementById('bathExplainModal');
    const isModalOpen = explainModal && explainModal.classList.contains('open');
    if (isModalOpen && this.currentExplainingParagraph) {
      const mPlayBtn = document.getElementById('modalSentencePlayBtn');
      if (mPlayBtn) {
        mPlayBtn.click();
        return;
      }
    }

    // Check if in Evening Bath session
    if (this.sessionData && this.sessionData.type === 'listening_bath') {
      const paras = this.bathParagraphs || [];
      const pIdx = this.activeBathParagraphIdx || 0;
      const targetP = paras[pIdx] || paras[0];
      if (targetP) {
        const paraEl = this.container.querySelector(`.bath-paragraph[data-idx="${pIdx}"]`);
        if (paraEl) {
          paraEl.click();
          return;
        }
      }
      const playAllBtn = this.container.querySelector('#bathPlayAllBtn');
      if (playAllBtn) playAllBtn.click();
      return;
    }

    // Phase 1: Replay hero sentence
    if (this.currentPhase === 1) {
      const playBtn = this.container.querySelector('#p1PlayBtn');
      if (playBtn) {
        if (window.TTSPlayer && window.TTSPlayer.isPlaying) {
          window.TTSPlayer.stop();
        }
        playBtn.click();
      }
      return;
    }

    // Phase 2: Replay active sentence
    if (this.currentPhase === 2 && this.currentActiveSentenceRu) {
      if (window.TTSPlayer) {
        window.TTSPlayer.speakSentence(this.currentActiveSentenceRu);
      }
      return;
    }
  }

  startLadderListening(customRu = null, customTokens = null) {
    if (!window.TTSPlayer) return;

    let targetRu = customRu;
    let targetTokens = customTokens;
    let tokenEls = [];

    const explainModal = document.getElementById('bathExplainModal');
    const isModalOpen = explainModal && explainModal.classList.contains('open');

    if (isModalOpen && this.currentExplainingParagraph) {
      targetRu = this.currentExplainingParagraph.ru;
      targetTokens = this.currentExplainingParagraph.tokens || [];
      tokenEls = Array.from(document.querySelectorAll('#modalHeroTokens .bath-word-token'));
    } else if (this.sessionData && this.sessionData.type === 'listening_bath') {
      const paras = this.bathParagraphs || [];
      const pIdx = this.activeBathParagraphIdx || 0;
      const targetP = paras[pIdx] || paras[0];
      if (targetP) {
        targetRu = targetP.ru;
        targetTokens = targetP.tokens || [];
        const paraEl = this.container.querySelector(`.bath-paragraph[data-idx="${pIdx}"]`);
        if (paraEl) {
          tokenEls = Array.from(paraEl.querySelectorAll('.bath-word-token'));
        }
      }
    } else if (this.currentPhase === 1 && this.currentHeroSentence) {
      targetRu = this.currentHeroSentence.ru;
      targetTokens = this.currentHeroSentence.tokens || [];
      tokenEls = Array.from(this.container.querySelectorAll('.word-token'));
    } else if (this.currentActiveSentenceRu) {
      targetRu = this.currentActiveSentenceRu;
    }

    if (!targetRu) {
      this.showSpeedHudToast('⚠️', '対象文なし', '再生する文が選択されていません');
      return;
    }

    // Set active style on all ladder buttons
    document.querySelectorAll('.ladder-play-btn, .bath-inline-ladder-btn').forEach(b => b.classList.add('active'));

    const highlightHandler = (idx) => {
      tokenEls.forEach((el, i) => {
        if (i === idx) el.classList.add('karaoke-active');
        else el.classList.remove('karaoke-active');
      });
    };

    window.TTSPlayer.playLadderSequence(
      targetRu,
      targetTokens,
      (step, total, rate, title, desc) => {
        this.showSpeedHudToast('🪜', title, desc, 2600);
        this.syncSpeedDisplay(rate);
      },
      highlightHandler,
      () => {
        tokenEls.forEach(el => el.classList.remove('karaoke-active'));
        document.querySelectorAll('.ladder-play-btn, .bath-inline-ladder-btn').forEach(b => b.classList.remove('active'));
        this.showSpeedHudToast('✨', 'ラダー特訓完了', '耳が自然速度に慣れました！', 2500);
        const savedSpeed = (window.App && window.App.userProfile && window.App.userProfile.tts_speed) ? window.App.userProfile.tts_speed : 0.85;
        if (window.TTSPlayer) window.TTSPlayer.setRate(savedSpeed);
        this.syncSpeedDisplay(savedSpeed);
      }
    );
  }

  // --------------------------------------------------------------------------
  // Phase 1: 出会う (Encounter / Input)
  // --------------------------------------------------------------------------
  ensureHeroTokens(hero) {
    if (!hero) return [];
    if (Array.isArray(hero.tokens) && hero.tokens.length > 0) {
      return hero.tokens;
    }
    if (!hero.ru) return [];
    console.warn('[Player] hero_sentence.tokens was missing or empty! Auto-generating fallback tokens for ru:', hero.ru);
    const rawWords = hero.ru.trim().split(/\s+/);
    return rawWords.map((w) => {
      const cleanWord = w.replace(/^[«"'(]+|[.,!?;:»"')]+$/g, '');
      return {
        word: cleanWord || w,
        base: cleanWord || w,
        role: '',
        tag: '',
        grammar: ''
      };
    });
  }

  renderPhase1(targetEl) {
    const s = this.sessionData;
    const hero = s.hero_sentence || { ru: "", ja: "", tokens: [] };
    if (!hero.tokens || hero.tokens.length === 0) {
      hero.tokens = this.ensureHeroTokens(hero);
    }
    this.currentHeroSentence = hero;
    const currentSpeed = (window.App && window.App.userProfile && window.App.userProfile.tts_speed) ? window.App.userProfile.tts_speed : 0.85;
    const VALID_EXPRESSIONS = ['tanya_smiling', 'tanya_explaining', 'tanya_encouraging', 'tanya_delighted', 'tanya_thoughtful'];
    const expr = VALID_EXPRESSIONS.includes(s.tanya_expression) ? s.tanya_expression : 'tanya_explaining';
    const exprImg = `assets/images/${expr}.jpg`;

    targetEl.innerHTML = `
      <div style="display: grid; grid-template-columns: 240px 1fr; gap: 20px; align-items: start;">
        <div class="tanya-portrait-box">
          <img src="${exprImg}" alt="ターニャ先生" class="tanya-portrait-img" onerror="this.onerror=null; this.src='assets/images/tanya_explaining.jpg';">
          <div class="tanya-expression-tag">モスクワ音楽院の視点</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div class="dialogue-bubble">
            <div class="dialogue-speaker">🎹 ターニャ先生の語りかけ</div>
            <div>${s.tanya_greeting || s.description || (window.App?.state?.today_pack?.daily_storyline) || "Доброе утро! 今日も一緒に美しいロシア語の世界を響かせましょう♪"}</div>
          </div>

          <!-- Hero Sentence Card -->
          <div class="hero-sentence-card">
            <div class="hero-sentence-ru ru-text" id="heroSentenceRu">
              ${(hero.tokens && hero.tokens.length > 0) ? hero.tokens.map((t, idx) => {
                const roleText = t.role || t.grammar || '';
                let caseTag = t.tag ? t.tag.replace('case.', '') : '';
                if (!caseTag && roleText) {
                  if (roleText.includes('主格')) caseTag = 'nom';
                  else if (roleText.includes('生格')) caseTag = 'gen';
                  else if (roleText.includes('与格')) caseTag = 'dat';
                  else if (roleText.includes('対格')) caseTag = 'acc';
                  else if (roleText.includes('造格')) caseTag = 'ins';
                  else if (roleText.includes('前置格')) caseTag = 'prp';
                }
                return `
                <div class="word-token" data-token-idx="${idx}" data-case="${caseTag}" title="${roleText}">
                  <span class="word-token-text">${t.word}</span>
                  <span class="word-token-sub">${roleText}</span>
                </div>
              `;}).join('') : `<span class="hero-fallback-text" style="font-size:1.35rem; font-weight:600;">${hero.ru || ''}</span>`}
            </div>
            <div class="hero-sentence-ja">${hero.ja || ''}</div>
          </div>

          <!-- Audio Player Bar with Speed Stepper & Ladder Listening -->
          <div class="audio-control-bar" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div class="audio-controls-left" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <button class="play-audio-btn" id="p1PlayBtn">
                <span>▶ 発音を聴く</span>
                <kbd class="kbd-badge">Space / R</kbd>
              </button>
              <button class="ladder-play-btn" id="p1LadderBtn" title="3段階で速度を上げて耳を慣らす（0.75x → 0.90x → 1.00x）">
                <span>🪜 ラダー特訓</span>
                <kbd class="kbd-badge">L</kbd>
              </button>
              <div class="speed-stepper" id="p1SpeedStepper" title="リスニング速度を0.05x刻みで微調整 (ショートカット: [ / ])">
                <button class="speed-stepper-btn" id="p1SpeedDownBtn" title="速度ダウン (-0.05x) [キー: []">-</button>
                <span class="speed-stepper-val" id="p1SpeedVal">${currentSpeed.toFixed(2)}x</span>
                <button class="speed-stepper-btn" id="p1SpeedUpBtn" title="速度アップ (+0.05x) [キー: ]]">+</button>
              </div>
              <div class="speed-gear-group">
                <button class="speed-gear-btn ${Math.abs(currentSpeed - 0.75) < 0.02 ? 'active' : ''}" data-speed="0.75">0.75x</button>
                <button class="speed-gear-btn ${Math.abs(currentSpeed - 0.85) < 0.02 ? 'active' : ''}" data-speed="0.85">0.85x</button>
                <button class="speed-gear-btn ${Math.abs(currentSpeed - 1.0) < 0.02 ? 'active' : ''}" data-speed="1.0">1.0x</button>
              </div>
            </div>
            <span class="audio-hint-text">[ / ] 速度微調整＆即リプレイ | L ラダー特訓</span>
          </div>

          <div style="display:flex; justify-content:flex-end; margin-top:8px;">
            <button class="quiz-next-btn" id="p1NextBtn">
              <span>Phase 2: 触る (探索) へ進む</span>
              <kbd class="kbd-badge">Enter / N / J</kbd>
            </button>
          </div>
        </div>
      </div>
    `;

    // Audio Play Button
    const playBtn = targetEl.querySelector('#p1PlayBtn');
    const ladderBtn = targetEl.querySelector('#p1LadderBtn');
    const tokenEls = targetEl.querySelectorAll('.word-token');

    playBtn.onclick = () => {
      if (!hero.ru) {
        console.warn('No hero sentence audio configured for this session.');
        return;
      }
      if (window.TTSPlayer.isPlaying) {
        window.TTSPlayer.stop();
        playBtn.innerHTML = '<span>▶ 発音を聴く</span><kbd class="kbd-badge">Space / R</kbd>';
      } else {
        playBtn.innerHTML = '<span>⏸ 停止</span><kbd class="kbd-badge">Space / R</kbd>';
        window.TTSPlayer.speakSentence(
          hero.ru,
          hero.tokens,
          (idx) => {
            tokenEls.forEach((el, i) => {
              if (i === idx) el.classList.add('karaoke-active');
              else el.classList.remove('karaoke-active');
            });
          },
          () => {
            playBtn.innerHTML = '<span>▶ 発音を聴く</span><kbd class="kbd-badge">Space / R</kbd>';
          }
        );
      }
    };

    // Ladder Button
    if (ladderBtn) {
      ladderBtn.onclick = () => {
        this.startLadderListening(hero.ru, hero.tokens);
      };
    }

    // Speed Stepper Buttons
    const speedDownBtn = targetEl.querySelector('#p1SpeedDownBtn');
    const speedUpBtn = targetEl.querySelector('#p1SpeedUpBtn');
    if (speedDownBtn) {
      speedDownBtn.onclick = () => this.adjustSpeedAndReplay(-0.05);
    }
    if (speedUpBtn) {
      speedUpBtn.onclick = () => this.adjustSpeedAndReplay(+0.05);
    }

    // Word tokens click to play
    tokenEls.forEach((el, idx) => {
      el.onclick = () => {
        const token = hero.tokens[idx];
        if (window.TTSPlayer && token) {
          window.TTSPlayer.speakWord(token.word);
        }
      };
    });

    // Speed gears
    targetEl.querySelectorAll('.speed-gear-btn').forEach(btn => {
      btn.onclick = () => {
        const spd = parseFloat(btn.dataset.speed);
        this.adjustSpeedAndReplay(0, null, null, spd);
      };
    });

    // Next Phase button
    targetEl.querySelector('#p1NextBtn').onclick = () => this.setPhase(2);

    // Auto play audio once on enter
    setTimeout(() => {
      if (playBtn && hero.ru) playBtn.click();
    }, 400);
  }

  // --------------------------------------------------------------------------
  // Phase 2: 触る (Explore / Spatial Multi-Pane & Mutator)
  // --------------------------------------------------------------------------
  renderPhase2(targetEl) {
    const s = this.sessionData;
    const hero = s.hero_sentence || { ru: "", ja: "", tokens: [] };
    if (!hero.tokens || hero.tokens.length === 0) {
      hero.tokens = this.ensureHeroTokens(hero);
    }
    this.currentActiveSentenceRu = hero.ru;
    this.currentFocusedTokenIdx = -1;

    targetEl.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px;">
        <!-- Compact Unified Top Console -->
        <div class="phase2-console">
          <div class="phase2-top-row">
            <div class="phase2-tokens-wrap ru-text" id="p2TokensContainer">
              ${(hero.tokens && hero.tokens.length > 0) ? hero.tokens.map((t, idx) => {
                const roleText = t.role || t.grammar || '';
                let caseTag = t.tag ? t.tag.replace('case.', '') : '';
                if (!caseTag && roleText) {
                  if (roleText.includes('主格')) caseTag = 'nom';
                  else if (roleText.includes('生格')) caseTag = 'gen';
                  else if (roleText.includes('与格')) caseTag = 'dat';
                  else if (roleText.includes('対格')) caseTag = 'acc';
                  else if (roleText.includes('造格')) caseTag = 'ins';
                  else if (roleText.includes('前置格')) caseTag = 'prp';
                }
                const gBadge = window.renderSoftSignGenderBadge ? window.renderSoftSignGenderBadge(t.word, t.base, t.tag, roleText) : '';
                return `
                <div class="word-token" data-token-idx="${idx}" data-case="${caseTag}" title="${roleText}">
                  <span class="word-token-text" style="font-size:1.25rem;">${t.word}</span>
                  <span class="word-token-sub">${roleText}${gBadge}</span>
                </div>
              `;}).join('') : `<span class="hero-fallback-text" style="font-size:1.25rem; font-weight:600;">${hero.ru || ''}</span>`}
            </div>
            <button class="phase2-play-btn" id="p2PlayBtn" title="音声再生 (Space / R)">
              <span>▶ 例文再生</span>
              <kbd class="kbd-badge" style="font-size:0.72rem; padding:2px 6px;">Space / R</kbd>
            </button>
          </div>
          <div class="phase2-translation-row">
            <div id="p2JaTranslation" style="font-size:0.92rem; color:#ffe599;">${hero.ja}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">※単語をクリックすると下のペインで格変化・語根を展開</div>
          </div>
          <!-- Live Grammar Mutator Bar -->
          <div id="mutatorMountPoint" class="mutator-container" style="margin-top:2px;"></div>
        </div>

        <!-- Spatial Multi-Pane Inspector Mount Point -->
        <div id="branchExplorerMountPoint"></div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
          <button class="player-back-btn" id="p2PrevBtn">← Phase 1へ戻る</button>
          <button class="quiz-next-btn" id="p2NextBtn">
            <span>Phase 3: 確かめる (チェック) へ進む</span>
            <kbd class="kbd-badge">Enter / N / J</kbd>
          </button>
        </div>
      </div>
    `;

    // Audio Play Button
    const playBtn = targetEl.querySelector('#p2PlayBtn');
    if (playBtn) {
      playBtn.onclick = () => {
        if (window.TTSPlayer && this.currentActiveSentenceRu) {
          window.TTSPlayer.speakSentence(this.currentActiveSentenceRu);
        }
      };
    }

    const bindTokens = () => {
      const tokens = targetEl.querySelectorAll('#p2TokensContainer .word-token');
      tokens.forEach((tEl, idx) => {
        tEl.onclick = () => {
          this.currentFocusedTokenIdx = idx;
          tokens.forEach(el => el.classList.remove('selected'));
          tEl.classList.add('selected');
          const token = hero.tokens[idx];
          if (window.BranchExplorer && token) {
            window.BranchExplorer.selectWord(token.word, token);
          } else if (window.TTSPlayer && token) {
            const cleanWord = (token.clean || token.word || '').replace(/[.,!?;:«»""'']/g, '').trim();
            window.TTSPlayer.speakWord(cleanWord || token.word);
          }
        };
      });
    };

    // Mount Grammar Mutator
    const mutatorMount = targetEl.querySelector('#mutatorMountPoint');
    if (window.GrammarMutator && mutatorMount) {
      window.GrammarMutator.init(mutatorMount, s.interactive_mutations || [], hero, (mut) => {
        this.currentActiveSentenceRu = mut.ru;
        const tokensContainer = targetEl.querySelector('#p2TokensContainer');
        const jaEl = targetEl.querySelector('#p2JaTranslation');

        if (mut.id === 'orig') {
          this.currentFocusedTokenIdx = -1;
          tokensContainer.innerHTML = (hero.tokens || []).map((t, idx) => {
            const roleText = t.role || t.grammar || '';
            let caseTag = t.tag ? t.tag.replace('case.', '') : '';
            if (!caseTag && roleText) {
              if (roleText.includes('主格')) caseTag = 'nom';
              else if (roleText.includes('生格')) caseTag = 'gen';
              else if (roleText.includes('与格')) caseTag = 'dat';
              else if (roleText.includes('対格')) caseTag = 'acc';
              else if (roleText.includes('造格')) caseTag = 'ins';
              else if (roleText.includes('前置格')) caseTag = 'prp';
            }
            const gBadge = window.renderSoftSignGenderBadge ? window.renderSoftSignGenderBadge(t.word, t.base, t.tag, roleText) : '';
            return `
            <div class="word-token" data-token-idx="${idx}" data-case="${caseTag}" title="${roleText}">
              <span class="word-token-text">${t.word}</span>
              <span class="word-token-sub">${roleText}${gBadge}</span>
            </div>
          `;}).join('');
          bindTokens();
          if (jaEl) jaEl.textContent = hero.ja;
        } else {
          this.currentFocusedTokenIdx = -1;
          const heroTokenMap = new Map();
          if (hero.tokens) {
            hero.tokens.forEach(ht => {
              const c = (ht.word || '').replace(/[.,!?;:«»""'']/g, '').trim().toLowerCase();
              if (c && !heroTokenMap.has(c)) heroTokenMap.set(c, ht);
            });
          }

          const mutTokens = (mut.tokens && mut.tokens.length > 0)
            ? mut.tokens.map(t => {
                const clean = (t.word || '').replace(/[.,!?;:«»""'']/g, '').trim();
                const roleText = t.role || t.grammar || '';
                return {
                  word: t.word,
                  clean: clean,
                  base: t.base || clean,
                  tag: t.tag || '',
                  role: roleText
                };
              })
            : (mut.ru || '').split(/\s+/).filter(w => w.trim().length > 0).map(w => {
                const clean = w.replace(/[.,!?;:«»""'']/g, '').trim();
                const matchedHero = heroTokenMap.get(clean.toLowerCase());
                if (matchedHero) {
                  return {
                    word: w,
                    clean: clean,
                    base: matchedHero.base || clean,
                    tag: matchedHero.tag || '',
                    role: matchedHero.role || matchedHero.grammar || ''
                  };
                }
                return {
                  word: w,
                  clean: clean,
                  base: clean.toLowerCase(),
                  tag: '',
                  role: '変化・活用形'
                };
              });

          tokensContainer.innerHTML = mutTokens.map((t, idx) => {
            const gBadge = window.renderSoftSignGenderBadge ? window.renderSoftSignGenderBadge(t.word, t.base, t.tag, t.role) : '';
            return `
            <div class="word-token" data-token-idx="${idx}" data-case="${t.tag ? t.tag.replace('case.', '') : ''}" title="${t.role || 'クリックで文法・変化表を展開 🔍'}">
              <span class="word-token-text">${t.word}</span>
              <span class="word-token-sub">${t.role || ''}${gBadge}</span>
            </div>
          `;}).join('');

          // Bind tokens for mutated sentence
          const tokensEls = tokensContainer.querySelectorAll('.word-token');
          tokensEls.forEach(tEl => {
            tEl.onclick = () => {
              const idx = parseInt(tEl.dataset.tokenIdx, 10);
              tokensEls.forEach(el => el.classList.remove('selected'));
              tEl.classList.add('selected');
              const token = mutTokens[idx];
              if (window.BranchExplorer && token) {
                window.BranchExplorer.selectWord(token.clean || token.word, token);
              } else if (window.TTSPlayer && token) {
                const cleanWord = (token.clean || token.word || '').replace(/[.,!?;:«»""'']/g, '').trim();
                window.TTSPlayer.speakWord(cleanWord || token.word);
              }
            };
          });

          if (jaEl) jaEl.textContent = mut.ja;
        }
      });
    }

    // Mount Branch Explorer
    const branchMount = targetEl.querySelector('#branchExplorerMountPoint');
    if (window.BranchExplorer && branchMount) {
      window.BranchExplorer.init(branchMount, s);
    }

    bindTokens();

    targetEl.querySelector('#p2PrevBtn').onclick = () => this.setPhase(1);
    targetEl.querySelector('#p2NextBtn').onclick = () => this.setPhase(3);
  }

  // --------------------------------------------------------------------------
  // Phase 3: 確かめる (Verify / Typing-Free Check)
  // --------------------------------------------------------------------------
  renderPhase3(targetEl) {
    const s = this.sessionData;
    const items = s.quiz_items || [];

    // If Non-Graded mode is chosen by user or session is non-graded
    if (this.isNonGraded || items.length === 0) {
      targetEl.innerHTML = `
        <div class="quiz-container" style="text-align:center; padding:40px 20px;">
          <div class="quiz-prompt-card">
            <div style="font-size:2.5rem; margin-bottom:12px;">☕</div>
            <div class="quiz-prompt-ru">判定なしリラックスモード</div>
            <div class="quiz-prompt-ja" style="max-width:500px; margin:10px auto;">
              本日は採点や正誤判定を行わず、耳と目で自然にフレーズを味わうリラックス設定です。
            </div>
          </div>
          <div style="margin-top:20px;">
            <button class="quiz-next-btn" id="skipQuizBtn" style="margin:0 auto;">
              <span>Phase 4: 本日のまとめへ進む</span>
              <kbd class="kbd-badge">Enter</kbd>
            </button>
          </div>
        </div>
      `;
      const skipBtn = targetEl.querySelector('#skipQuizBtn');
      if (skipBtn) {
        skipBtn.onclick = () => {
          this.quizResults = [];
          this.setPhase(4);
        };
        setTimeout(() => skipBtn.focus(), 50);
      }
      return;
    }

    targetEl.innerHTML = `<div id="quizEngineMount"></div>`;
    const mount = targetEl.querySelector('#quizEngineMount');

    if (window.QuizEngine && mount) {
      window.QuizEngine.init(mount, items, (results) => {
        this.quizResults = results;
        this.setPhase(4);
      });
    }
  }

  // --------------------------------------------------------------------------
  // Phase 4: 積み上がる (Record & Wrap-up)
  // --------------------------------------------------------------------------
  async renderPhase4(targetEl) {
    const s = this.sessionData;
    const closing = s.closing || {};
    const VALID_EXPRESSIONS = ['tanya_smiling', 'tanya_explaining', 'tanya_encouraging', 'tanya_delighted', 'tanya_thoughtful'];
    const closingExpr = VALID_EXPRESSIONS.includes(closing.tanya_expression) ? closing.tanya_expression : 'tanya_delighted';
    const exprImg = `assets/images/${closingExpr}.jpg`;
    const message = closing.message || closing.tanya_speech || "今日も素晴らしい練習でしたね！";
    const intimacyGain = closing.intimacy_gain || 5;

    // Post results to backend
    if (window.API) {
      await window.API.postProgress({
        session_id: s.session_id,
        type: s.type,
        intimacy_gain: intimacyGain,
        quiz_results: this.quizResults,
        unlocked_badge: s.unlocked_badge || null
      });
    }

    if (window.DistanceMeter) {
      window.DistanceMeter.addExp(intimacyGain);
    }

    targetEl.innerHTML = `
      <div class="wrapup-card">
        <img src="${exprImg}" alt="ターニャ先生" class="wrapup-portrait">
        <div class="wrapup-content">
          <div class="wrapup-title">🎉 レッスン完了！ (Урок окончен)</div>
          <div class="wrapup-message">
            ${message}
          </div>
          <div class="wrapup-gains-row">
            <div class="gain-badge">
              <span>💖 親密度 +${closing.intimacy_gain || 5} EXP</span>
            </div>
            <div class="gain-badge">
              <span>📝 チェック完了: ${this.quizResults.length}問</span>
            </div>
            ${s.unlocked_badge ? `
              <div class="gain-badge" style="border-color:var(--gold);">
                <span>🏆 バッジ獲得: ${s.unlocked_badge}</span>
              </div>
            ` : ''}
          </div>
          <div style="margin-top:16px;">
            <button class="wrapup-finish-btn" id="wrapupFinishBtn">
              <span>サロンへ戻る</span>
              <kbd class="kbd-badge" style="background:#1a1514; color:var(--gold-light); margin-left:6px;">Esc</kbd>
            </button>
          </div>
        </div>
      </div>
    `;

    targetEl.querySelector('#wrapupFinishBtn').onclick = () => {
      if (this.onFinishCallback) this.onFinishCallback();
    };
  }

  // --------------------------------------------------------------------------
  // Dedicated View: Listening Bath (夜のリスニング浴び)
  // --------------------------------------------------------------------------
  renderListeningBathSession() {
    const s = this.sessionData;
    const paragraphs = s.audio_paragraphs || s.paragraphs || s.audio_sentences || [];
    this.bathParagraphs = paragraphs;
    this.currentBathParagraphIdx = 0;
    const currentSpeed = (window.App && window.App.userProfile && window.App.userProfile.tts_speed) ? window.App.userProfile.tts_speed : 0.85;

    if (window.TTSPlayer) {
      window.TTSPlayer.setRate(currentSpeed);
    }

    if (this.bathAssistMode === undefined) {
      this.bathAssistMode = true; // default ON for supportive learning
    }

    const dayNum = s.day_index || s.day || (s.session_id?.match(/day(\d+)_/)?.[1]) || (window.App?.selectedDay) || 15;

    // Update global header capsule
    const headerDayBadge = document.getElementById('headerDayBadge');
    const headerSessionBadge = document.getElementById('headerSessionBadge');
    if (headerDayBadge) headerDayBadge.textContent = `📅 Day ${dayNum} ［夜］`;
    if (headerSessionBadge) headerSessionBadge.textContent = 'リスニング浴び';

    this.container.innerHTML = `
      <div class="player-view">
        <div class="player-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="player-back-btn" id="bathExitBtn">← サロン (Esc)</button>
            <div class="player-day-indicator">
              <span class="day-tag">📅 Day ${dayNum} ［夜］</span>
              <span class="phase-tag">リスニング浴び</span>
            </div>
          </div>
          <div style="font-size:0.88rem; color:var(--gold-light); font-weight:600;">🌙 ${s.title}</div>
          <div style="display:flex; align-items:center; gap:10px;">
            <button class="bath-assist-toggle ${this.bathAssistMode ? 'active' : ''}" id="bathAssistToggle" title="単語ハイライトと解説ボタンの表示切替">
              <span>💡 お助けモード: ${this.bathAssistMode ? 'ON' : 'OFF'}</span>
            </button>
            <span class="buffer-badge">浴びるリスニング (判定なし)</span>
          </div>
        </div>

        <div style="display:grid; grid-template-columns:260px 1fr; gap:24px;">
          <div class="tanya-portrait-box">
            <img src="assets/images/tanya_thoughtful.jpg" alt="ターニャ先生" class="tanya-portrait-img">
            <div class="tanya-expression-tag">夜の静寂とともに</div>
          </div>
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div class="dialogue-bubble">
              <div class="dialogue-speaker">✨ ターニャ先生の語りかけ</div>
              <div>${s.tanya_greeting || "今夜は音楽院の静けさの中で、美しいロシア語の音を心ゆくまで味わってください。"}</div>
            </div>

            <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; gap:12px;">
              ${paragraphs.map((p, idx) => {
                const tokens = p.tokens || p.ru.split(/\s+/).map(w => ({ word: w, role: '', base: w }));
                return `
                  <div class="bath-paragraph" data-idx="${idx}">
                    <div class="bath-paragraph-top">
                      <div class="ru-text bath-ru-tokens" style="font-size:1.15rem; color:var(--text-primary); line-height:1.45;">
                        ${tokens.map((t, tIdx) => `
                          <span class="bath-word-token" data-p-idx="${idx}" data-t-idx="${tIdx}" title="${t.role || t.base || ''}">${t.word}</span>
                        `).join(' ')}
                      </div>
                      <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
                        <button class="bath-inline-ladder-btn" data-p-idx="${idx}" title="この文を3段階ラダーリスニング（0.75x → 0.90x → 1.00x）で反復特訓">
                          <span>🪜 ラダー</span>
                        </button>
                        <button class="bath-explain-btn" data-p-idx="${idx}" style="${this.bathAssistMode ? '' : 'display:none;'}" title="この文の構造・文法解説ウインドウを開く [${idx + 1}]">
                          <span>💡 構造・文法解説</span>
                          <kbd class="kbd-badge">${idx + 1}</kbd>
                        </button>
                      </div>
                    </div>
                    <div style="font-size:0.86rem; color:var(--text-muted);">${p.ja}</div>
                  </div>
                `;
              }).join('')}
            </div>

            <div class="audio-control-bar" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
              <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <button class="play-audio-btn" id="bathPlayAllBtn">
                  <span>▶ 全文を続けて聴く</span>
                  <kbd class="kbd-badge">Space</kbd>
                </button>
                <button class="ladder-play-btn" id="bathLadderBtn" title="現在の文を3段階で速度を上げて特訓（0.75x → 0.90x → 1.00x）">
                  <span>🪜 ラダー特訓</span>
                  <kbd class="kbd-badge">L</kbd>
                </button>
                <div class="speed-stepper" id="bathSpeedStepper" title="リスニング速度を0.05x刻みで微調整 (ショートカット: [ / ])">
                  <button class="speed-stepper-btn" id="bathSpeedDownBtn" title="速度ダウン (-0.05x) [キー: []">-</button>
                  <span class="speed-stepper-val" id="bathSpeedVal">${currentSpeed.toFixed(2)}x</span>
                  <button class="speed-stepper-btn" id="bathSpeedUpBtn" title="速度アップ (+0.05x) [キー: ]]">+</button>
                </div>
                <div class="speed-pill-group" id="bathSpeedPills">
                  <button class="speed-pill-btn ${Math.abs(currentSpeed - 0.75) < 0.02 ? 'active' : ''}" data-speed="0.75">0.75x</button>
                  <button class="speed-pill-btn ${Math.abs(currentSpeed - 0.85) < 0.02 ? 'active' : ''}" data-speed="0.85">0.85x (標準)</button>
                  <button class="speed-pill-btn ${Math.abs(currentSpeed - 1.0) < 0.02 ? 'active' : ''}" data-speed="1.0">1.0x</button>
                  <button class="speed-pill-btn ${Math.abs(currentSpeed - 1.15) < 0.02 ? 'active' : ''}" data-speed="1.15">1.15x</button>
                </div>
              </div>
              <span class="audio-hint-text">[ / ] 速度微調整＆再生 | L ラダー特訓 | 1〜${paragraphs.length} 文法解説</span>
            </div>

            <div style="display:flex; justify-content:flex-end;">
              <button class="wrapup-finish-btn" id="bathCompleteBtn">
                <span>セッションを完了する (+6 EXP)</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.container.querySelector('#bathExitBtn').onclick = () => {
      if (window.TTSPlayer) window.TTSPlayer.stop();
      if (this.onFinishCallback) this.onFinishCallback();
    };

    // Assist mode toggle listener
    const assistToggle = this.container.querySelector('#bathAssistToggle');
    if (assistToggle) {
      assistToggle.onclick = () => {
        this.bathAssistMode = !this.bathAssistMode;
        assistToggle.classList.toggle('active', this.bathAssistMode);
        assistToggle.querySelector('span').textContent = `💡 お助けモード: ${this.bathAssistMode ? 'ON' : 'OFF'}`;
        this.container.querySelectorAll('.bath-explain-btn').forEach(btn => {
          btn.style.display = this.bathAssistMode ? 'inline-flex' : 'none';
        });
      };
    }

    // Ladder Button
    const bathLadderBtn = this.container.querySelector('#bathLadderBtn');
    if (bathLadderBtn) {
      bathLadderBtn.onclick = () => {
        this.startLadderListening();
      };
    }

    // Speed Stepper Buttons
    const bathSpeedDownBtn = this.container.querySelector('#bathSpeedDownBtn');
    const bathSpeedUpBtn = this.container.querySelector('#bathSpeedUpBtn');
    if (bathSpeedDownBtn) {
      bathSpeedDownBtn.onclick = () => this.adjustSpeedAndReplay(-0.05);
    }
    if (bathSpeedUpBtn) {
      bathSpeedUpBtn.onclick = () => this.adjustSpeedAndReplay(+0.05);
    }

    // Inline ladder buttons on each paragraph
    this.container.querySelectorAll('.bath-inline-ladder-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const pIdx = parseInt(btn.dataset.pIdx, 10);
        this.activeBathParagraphIdx = pIdx;
        const targetP = paragraphs[pIdx];
        if (targetP) {
          this.startLadderListening(targetP.ru, targetP.tokens || []);
        }
      };
    });

    // Speed pills listener
    const pillGroup = this.container.querySelector('#bathSpeedPills');
    if (pillGroup) {
      pillGroup.querySelectorAll('.speed-pill-btn').forEach(btn => {
        btn.onclick = () => {
          const speed = parseFloat(btn.dataset.speed);
          this.adjustSpeedAndReplay(0, null, null, speed);
        };
      });
    }

    // Attach explain window buttons
    this.container.querySelectorAll('.bath-explain-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const pIdx = parseInt(btn.dataset.pIdx, 10);
        const targetP = paragraphs[pIdx];
        if (targetP) {
          this.openParagraphExplainer(targetP, pIdx, paragraphs);
        }
      };
    });

    // Word token click to speak individual word
    this.container.querySelectorAll('.bath-word-token').forEach(tokenEl => {
      tokenEl.onclick = (e) => {
        e.stopPropagation();
        const word = tokenEl.innerText.replace(/[.,!?;:()«»"—]/g, '').trim();
        if (window.TTSPlayer && word) {
          window.TTSPlayer.speakWord(word);
        }
      };
    });

    const paraEls = this.container.querySelectorAll('.bath-paragraph');
    const clearAllKaraoke = () => {
      this.container.querySelectorAll('.bath-word-token').forEach(t => t.classList.remove('karaoke-active'));
      paraEls.forEach(p => {
        p.classList.remove('playing');
        p.style.borderColor = 'var(--border-color)';
      });
    };

    // Paragraph click to play with real-time karaoke highlight
    paraEls.forEach((el, idx) => {
      el.onclick = (e) => {
        if (e.target.closest('.bath-explain-btn') || e.target.closest('.bath-word-token') || e.target.closest('.bath-inline-ladder-btn')) {
          return;
        }
        this.activeBathParagraphIdx = idx;
        clearAllKaraoke();
        el.classList.add('playing');
        el.style.borderColor = 'var(--emerald)';

        const targetTokens = paragraphs[idx].tokens || paragraphs[idx].ru.split(/\s+/).map(w => ({ word: w }));
        const tokenSpans = el.querySelectorAll('.bath-word-token');

        window.TTSPlayer.speakSentence(
          paragraphs[idx].ru,
          targetTokens,
          (wIdx) => {
            tokenSpans.forEach((span, i) => {
              if (i === wIdx) span.classList.add('karaoke-active');
              else span.classList.remove('karaoke-active');
            });
          },
          () => {
            tokenSpans.forEach(span => span.classList.remove('karaoke-active'));
            el.classList.remove('playing');
            el.style.borderColor = 'var(--border-color)';
          }
        );
      };
    });

    // Play all sequentially with real-time karaoke highlight
    const playAllBtn = this.container.querySelector('#bathPlayAllBtn');
    playAllBtn.onclick = () => {
      if (window.TTSPlayer.isPlaying) {
        window.TTSPlayer.stop();
        clearAllKaraoke();
        playAllBtn.innerHTML = '<span>▶ 全文を続けて聴く</span><kbd class="kbd-badge">Space</kbd>';
        return;
      }

      let pIdx = 0;
      const playNext = () => {
        if (pIdx >= paragraphs.length) {
          clearAllKaraoke();
          playAllBtn.innerHTML = '<span>▶ 全文を続けて聴く</span><kbd class="kbd-badge">Space</kbd>';
          return;
        }
        clearAllKaraoke();
        const currEl = paraEls[pIdx];
        if (currEl) {
          currEl.classList.add('playing');
          currEl.style.borderColor = 'var(--emerald)';
          currEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        const targetTokens = paragraphs[pIdx].tokens || paragraphs[pIdx].ru.split(/\s+/).map(w => ({ word: w }));
        const tokenSpans = currEl ? currEl.querySelectorAll('.bath-word-token') : [];

        window.TTSPlayer.speakSentence(
          paragraphs[pIdx].ru,
          targetTokens,
          (wIdx) => {
            tokenSpans.forEach((span, i) => {
              if (i === wIdx) span.classList.add('karaoke-active');
              else span.classList.remove('karaoke-active');
            });
          },
          () => {
            tokenSpans.forEach(span => span.classList.remove('karaoke-active'));
            if (currEl) {
              currEl.classList.remove('playing');
              currEl.style.borderColor = 'var(--border-color)';
            }
            pIdx++;
            setTimeout(playNext, 600);
          }
        );
      };
      playAllBtn.innerHTML = '<span>⏸ 朗読中... (再押下で停止)</span><kbd class="kbd-badge">Space</kbd>';
      playNext();
    };

    this.container.querySelector('#bathCompleteBtn').onclick = async () => {
      if (window.API) {
        await window.API.postProgress({
          session_id: s.session_id,
          type: s.type,
          intimacy_gain: 6
        });
      }
      if (window.DistanceMeter) window.DistanceMeter.addExp(6);
      if (this.onFinishCallback) this.onFinishCallback();
    };
  }

  clearBathExplainingActive() {
    if (this.container) {
      this.container.querySelectorAll('.bath-paragraph').forEach(el => el.classList.remove('explaining-active'));
    }
  }

  navigateBathExplainer(delta) {
    if (!this.bathParagraphs || this.bathParagraphs.length === 0) return;
    const total = this.bathParagraphs.length;
    let nextIdx = (this.currentBathParagraphIdx + delta + total) % total;
    this.openParagraphExplainer(this.bathParagraphs[nextIdx], nextIdx, this.bathParagraphs);
  }

  /**
   * Dedicated Sentence Anatomy & Vocab Explainer Window (お助けウインドウ)
   */
  openParagraphExplainer(p, pIdx = 0, paragraphs = null) {
    if (window.TTSPlayer) window.TTSPlayer.stop();
    const modal = document.getElementById('bathExplainModal');
    const body = document.getElementById('bathExplainBody');
    const closeBtn = document.getElementById('bathExplainClose');
    if (!modal || !body) return;

    if (!paragraphs) {
      paragraphs = this.bathParagraphs || (this.sessionData ? (this.sessionData.audio_paragraphs || this.sessionData.paragraphs || this.sessionData.audio_sentences) : []) || [p];
    }
    this.bathParagraphs = paragraphs;
    this.currentBathParagraphIdx = pIdx;

    if (closeBtn) {
      closeBtn.onclick = () => {
        if (window.TTSPlayer) window.TTSPlayer.stop();
        modal.classList.remove('open');
        this.clearBathExplainingActive();
      };
    }

    // Highlight active sentence in the background list
    this.currentExplainingParagraph = p;
    const mainParas = this.container ? this.container.querySelectorAll('.bath-paragraph') : [];
    mainParas.forEach((el, idx) => {
      if (idx === pIdx) {
        el.classList.add('explaining-active');
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        el.classList.remove('explaining-active');
      }
    });

    const fmt = window.formatRussianClickable || (t => t);
    const keyVocab = p.key_vocab || [];
    const grammarPoints = p.grammar_points || [];
    const tokens = (p.tokens && p.tokens.length > 0) ? p.tokens : (p.ru ? p.ru.split(/\s+/).filter(Boolean).map((w, idx) => {
      const clean = w.replace(/[.,!?;:()«»"—]/g, '').trim();
      return { word: w, clean: clean, base: clean, role: '' };
    }) : []);

    body.innerHTML = `
      <!-- Sentence Navigation Bar -->
      <div class="explain-nav-bar">
        <button class="explain-nav-btn prev-btn" id="modalPrevSentenceBtn" title="前の文へ (ショートカット: P または K)">
          <kbd class="kbd-badge">P / K</kbd>
          <span>← 前の文</span>
        </button>
        <div class="explain-nav-center">
          <span class="explain-nav-counter">第 ${pIdx + 1} / ${paragraphs.length} 文</span>
          <div class="explain-nav-pills" id="modalSentencePills">
            ${paragraphs.map((_, i) => `
              <button class="explain-pill-btn ${i === pIdx ? 'active' : ''}" data-p-idx="${i}" title="第${i + 1}文へジャンプ (ショートカット: ${i + 1})">
                <span>第${i + 1}文</span>
                <kbd class="kbd-badge">${i + 1}</kbd>
              </button>
            `).join('')}
          </div>
        </div>
        <button class="explain-nav-btn next-btn" id="modalNextSentenceBtn" title="次の文へ (ショートカット: N または J)">
          <span>次の文 →</span>
          <kbd class="kbd-badge">N / J</kbd>
        </button>
      </div>

      <div class="explain-hero-card">
        <div class="explain-ru-text ru-text" id="modalHeroTokens">
          ${tokens.map((t, idx) => `
            <span class="bath-word-token ru-speakable" data-t-idx="${idx}" data-ru="${t.word}" title="${t.role ? t.role + ' (クリックで辞書・解説)' : 'クリックで辞書・解説'}">${t.word}</span>
          `).join(' ')}
        </div>
        <div class="explain-ja-text">${p.ja}</div>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:6px; display:flex; align-items:center; gap:6px;">
          <span>💡</span>
          <span>文中の単語をクリックすると、発音と同時に語彙解説へジャンプまたは詳細辞書を展開します。</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:14px;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <button class="play-audio-btn" id="modalSentencePlayBtn" style="padding:5px 14px; font-size:0.82rem;">
              <span>🔊 この文を聴く</span>
              <kbd class="kbd-badge">Space / R</kbd>
            </button>
            <button class="ladder-play-btn" id="modalLadderBtn" style="padding:5px 12px; font-size:0.80rem;" title="3段階で速度を上げて特訓（0.75x → 0.90x → 1.00x）">
              <span>🪜 ラダー特訓</span>
              <kbd class="kbd-badge">L</kbd>
            </button>
            <div class="speed-stepper" id="modalSpeedStepper" style="padding:1px 4px;">
              <button class="speed-stepper-btn" id="modalSpeedDownBtn" title="速度ダウン (-0.05x) [キー: []">-</button>
              <span class="speed-stepper-val" id="modalSpeedVal">${((window.TTSPlayer && window.TTSPlayer.currentRate) || 0.85).toFixed(2)}x</span>
              <button class="speed-stepper-btn" id="modalSpeedUpBtn" title="速度アップ (+0.05x) [キー: ]]">+</button>
            </div>
          </div>
          ${p.related_tag ? `
            <button class="handbook-related-btn" id="modalHandbookBtn" style="font-size:0.78rem; padding:4px 12px;" data-tag="${p.related_tag}">
              📖 教科書で関連文法（${p.related_tag}）を読む
            </button>
          ` : ''}
        </div>
      </div>

      <!-- On-Demand Dynamic Inspector Container -->
      <div id="modalOndemandContainer"></div>

      <!-- Key Vocab Cards -->
      <div class="explain-section-title">
        <span>📚 主要な単語・格変化の分解 ${keyVocab.length > 0 ? `(${keyVocab.length}語)` : ''}</span>
      </div>
      <div class="explain-vocab-grid">
        ${keyVocab.length > 0 ? keyVocab.map(v => {
          const targetWord = v.base || v.word || '';
          const isBm = window.bookmarkedWordsSet?.has((targetWord || '').toLowerCase());
          const cleanWord = (targetWord || '').replace(/"/g, '&quot;');
          const cleanPos = (v.pos || '').replace(/"/g, '&quot;');
          const cleanMeaning = (v.meaning || '').replace(/"/g, '&quot;');
          const cleanRole = (v.role_in_sentence || '').replace(/"/g, '&quot;');
          return `
            <div class="explain-vocab-card" data-vocab-word="${(v.word || '').toLowerCase()}" data-vocab-base="${(v.base || '').toLowerCase()}">
              <div class="vocab-card-top">
                <span class="vocab-word-ru ru-speakable" data-ru="${v.word}" title="クリックで発音 🔊">${v.word}</span>
                <span class="vocab-pos-badge">${v.pos}</span>
              </div>
              <div class="vocab-meaning">${v.meaning}</div>
              <div class="vocab-role">【文中での役割】${v.role_in_sentence}</div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; border-top:1px dashed rgba(255,255,255,0.08); padding-top:6px;">
                <span style="font-size:0.72rem; color:var(--text-muted);">原形: ${v.base}</span>
                <button class="bookmark-toggle-btn" 
                  data-word="${cleanWord}" 
                  data-base="${cleanWord}" 
                  data-pos="${cleanPos}" 
                  data-meaning="${cleanMeaning}" 
                  data-role="${cleanRole}"
                  style="background:transparent; border:none; cursor:pointer; font-size:0.78rem; color:${isBm ? 'var(--gold-light)' : 'var(--text-muted)'};" title="単語帳にマーク (☆)">
                  ${isBm ? '★ マーク済み' : '☆ マーク'}
                </button>
              </div>
            </div>
          `;
        }).join('') : `
          <div style="grid-column: 1 / -1; padding: 14px; background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); border: 1px dashed var(--border-color); color: var(--text-secondary); font-size: 0.85rem; text-align: center;">
            💡 上のロシア語文の単語をクリックすると、発音とともに即座に辞書・文法情報を照会できます。
          </div>
        `}
      </div>

      <!-- Grammar Points -->
      ${grammarPoints.length > 0 ? `
        <div class="explain-section-title">
          <span>🎯 文法・2級検定の急所ポイント</span>
        </div>
        <div class="explain-grammar-box">
          <div class="explain-grammar-list">
            ${grammarPoints.map(pt => `<div>• ${fmt(pt)}</div>`).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Tanya's Note -->
      ${p.tanya_note ? `
        <div class="explain-tanya-box">
          <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="explain-tanya-img">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <div style="font-weight:700; color:var(--gold-light); font-size:0.88rem;">🎹 ターニャ先生の鑑賞ノート</div>
            <div class="explain-tanya-text">${p.tanya_note}</div>
          </div>
        </div>
      ` : ''}
    `;

    // Sentence navigation buttons
    const prevSentenceBtn = body.querySelector('#modalPrevSentenceBtn');
    if (prevSentenceBtn) {
      prevSentenceBtn.onclick = (e) => {
        e.stopPropagation();
        this.navigateBathExplainer(-1);
      };
    }

    const nextSentenceBtn = body.querySelector('#modalNextSentenceBtn');
    if (nextSentenceBtn) {
      nextSentenceBtn.onclick = (e) => {
        e.stopPropagation();
        this.navigateBathExplainer(1);
      };
    }

    body.querySelectorAll('.explain-pill-btn').forEach(pill => {
      pill.onclick = (e) => {
        e.stopPropagation();
        const targetIdx = parseInt(pill.dataset.pIdx, 10);
        if (paragraphs[targetIdx]) {
          this.openParagraphExplainer(paragraphs[targetIdx], targetIdx, paragraphs);
        }
      };
    });

    body.scrollTop = 0;

    // Audio Play inside Modal with word highlight
    const modalPlayBtn = body.querySelector('#modalSentencePlayBtn');
    const modalTokens = body.querySelectorAll('#modalHeroTokens .bath-word-token');
    const ondemandContainer = body.querySelector('#modalOndemandContainer');

    if (modalPlayBtn) {
      modalPlayBtn.onclick = () => {
        if (window.TTSPlayer && window.TTSPlayer.isPlaying) {
          window.TTSPlayer.stop();
          modalTokens.forEach(span => span.classList.remove('karaoke-active'));
          return;
        }
        modalTokens.forEach(t => {
          t.classList.remove('karaoke-active');
          t.classList.remove('inspect-active');
        });
        window.TTSPlayer.speakSentence(
          p.ru,
          tokens,
          (wIdx) => {
            modalTokens.forEach((span, i) => {
              if (i === wIdx) span.classList.add('karaoke-active');
              else span.classList.remove('karaoke-active');
            });
          },
          () => {
            modalTokens.forEach(span => span.classList.remove('karaoke-active'));
          }
        );
      };
    }

    const modalLadderBtn = body.querySelector('#modalLadderBtn');
    if (modalLadderBtn) {
      modalLadderBtn.onclick = () => {
        this.startLadderListening(p.ru, tokens);
      };
    }

    const modalSpeedDownBtn = body.querySelector('#modalSpeedDownBtn');
    const modalSpeedUpBtn = body.querySelector('#modalSpeedUpBtn');
    if (modalSpeedDownBtn) {
      modalSpeedDownBtn.onclick = () => this.adjustSpeedAndReplay(-0.05, p.ru, tokens);
    }
    if (modalSpeedUpBtn) {
      modalSpeedUpBtn.onclick = () => this.adjustSpeedAndReplay(+0.05, p.ru, tokens);
    }

    // Attach Interactive Token Inspection (Proposal ②: Jump to card or On-demand Lookup)
    modalTokens.forEach(tokenSpan => {
      tokenSpan.style.cursor = 'pointer';
      tokenSpan.addEventListener('click', async (e) => {
        e.stopPropagation();
        const rawWord = tokenSpan.dataset.ru || tokenSpan.textContent || '';
        const cleanWord = rawWord.replace(/[.,!?;:()«»"—]/g, '').trim();
        if (!cleanWord) return;

        // Speak clicked word immediately
        if (window.TTSPlayer) {
          window.TTSPlayer.stop();
          window.TTSPlayer.speakWord(cleanWord);
        }

        // Active highlight state on token
        modalTokens.forEach(t => {
          t.classList.remove('karaoke-active');
          t.classList.remove('inspect-active');
        });
        tokenSpan.classList.add('inspect-active');

        // Check if token matches existing key_vocab card
        const cleanLower = cleanWord.toLowerCase();
        const tokenIdx = parseInt(tokenSpan.dataset.tIdx, 10);
        const tokenObj = (tokens && tokens[tokenIdx]) ? tokens[tokenIdx] : null;
        const tokenBase = (tokenObj && tokenObj.base) ? tokenObj.base.toLowerCase() : '';

        let matchedCard = null;
        const cards = body.querySelectorAll('.explain-vocab-card');
        for (const card of cards) {
          const w = card.dataset.vocabWord;
          const b = card.dataset.vocabBase;
          if ((w && (w === cleanLower || (tokenBase && w === tokenBase))) || 
              (b && (b === cleanLower || (tokenBase && b === tokenBase)))) {
            matchedCard = card;
            break;
          }
        }

        if (matchedCard) {
          // Render matched card content right into ondemandContainer directly below the sentence
          // so user stays focused on the sentence without any jarring downward scroll jump!
          if (ondemandContainer) {
            ondemandContainer.innerHTML = matchedCard.outerHTML;
            const bmBtn = ondemandContainer.querySelector('.bookmark-toggle-btn');
            if (bmBtn) {
              bmBtn.onclick = (eBm) => {
                eBm.stopPropagation();
                const origBm = matchedCard.querySelector('.bookmark-toggle-btn');
                if (origBm) origBm.click();
              };
            }
          }
          matchedCard.classList.remove('card-pulse-active');
          void matchedCard.offsetWidth; // force CSS reflow
          matchedCard.classList.add('card-pulse-active');
          setTimeout(() => {
            matchedCard.classList.remove('card-pulse-active');
          }, 3500);
          return;
        }

        // Not in key_vocab -> On-demand lookup via API
        if (!ondemandContainer) return;
        ondemandContainer.innerHTML = `
          <div class="ondemand-vocab-card">
            <div style="font-size:0.85rem; color:var(--text-muted); display:flex; align-items:center; gap:8px;">
              <span>🔍</span>
              <span>「<strong style="color:var(--gold-light);">${cleanWord}</strong>」の文法・辞書情報を照会中...</span>
            </div>
          </div>
        `;

        try {
          const results = window.API ? await window.API.searchVocabulary(cleanWord, tokenBase) : [];
          if (!results || results.length === 0) {
            ondemandContainer.innerHTML = `
              <div class="ondemand-vocab-card" style="border-left-color:var(--text-muted);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div style="font-size:0.85rem; color:var(--text-secondary);">
                    「<strong style="color:var(--text-primary);">${cleanWord}</strong>」: 辞書登録準備中（基本単語・固有名詞等）
                  </div>
                  <button class="ondemand-close-btn" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem;">✕</button>
                </div>
              </div>
            `;
            const closeBtn = ondemandContainer.querySelector('.ondemand-close-btn');
            if (closeBtn) {
              closeBtn.onclick = () => {
                ondemandContainer.innerHTML = '';
                tokenSpan.classList.remove('inspect-active');
              };
            }
            return;
          }

          const entry = results[0];
          const entryWord = entry.word || (tokenObj && tokenObj.base) || cleanWord || '';
          const entryPos = entry.pos || (tokenObj && tokenObj.pos) || '品詞未定義';
          const entryMeaning = entry.meaning || (tokenObj && tokenObj.meaning) || (tokenObj && tokenObj.role ? tokenObj.role : '意味情報なし');
          const entryAnatomy = entry.anatomy || entry.notes || '';
          const metaCombined = `${entryPos} ${entryAnatomy} ${(tokenObj && (tokenObj.role || tokenObj.tag)) || ''}`;
          const isUninflected = !/participle|形動詞|причастие|動詞|\bverb\b|глагол/i.test(metaCombined) &&
                                /(?:副詞|наречие|\badv\b|前置詞|предлог|\bprep\b|接続詞|союз|\bconj\b|助詞|小詞|частица|\bparticle\b|間投詞|\binterj\b|不変化)/i.test(metaCombined);
          const hasTable = !isUninflected && ((entry.declension_table && Array.isArray(entry.declension_table) && entry.declension_table.length > 1) || !!entry.declension_html);
          const isBm = window.bookmarkedWordsSet?.has((entryWord || '').toLowerCase());

          const cleanWordAttr = (entryWord || '').replace(/"/g, '&quot;');
          const cleanPosAttr = (entryPos || '').replace(/"/g, '&quot;');
          const cleanMeaningAttr = (entryMeaning || '').replace(/"/g, '&quot;');
          const cleanRoleAttr = (cleanWord || '').replace(/"/g, '&quot;');

          let tableContentHtml = '';
          if (entry.declension_table && Array.isArray(entry.declension_table) && entry.declension_table.length > 0) {
            tableContentHtml = `
              <table>
                ${entry.declension_table.map((row, rIdx) => `
                  <tr>
                    ${row.map((cell, cIdx) => {
                      const cleanCell = (cIdx === 0 && typeof cell === 'string') 
                        ? cell.replace(/\s*\([A-Za-z]+\)/g, '').trim() 
                        : cell;
                      if (rIdx === 0) return `<th>${cleanCell}</th>`;
                      const isRussian = /[а-яёА-ЯЁ]/.test(cleanCell) && !cleanCell.includes('格') && !cleanCell.includes('人称');
                      return isRussian 
                        ? `<td class="ru-speakable" data-ru="${cleanCell}" title="クリックで発音 🔊">${cleanCell}</td>`
                        : `<td>${cleanCell}</td>`;
                    }).join('')}
                  </tr>
                `).join('')}
              </table>
            `;
          } else if (entry.declension_html) {
            tableContentHtml = entry.declension_html;
          }

          ondemandContainer.innerHTML = `
            <div class="ondemand-vocab-card">
              <div class="ondemand-card-top">
                <div class="ondemand-word-info">
                  <span class="ondemand-word-text ru-speakable" data-ru="${cleanWordAttr}" title="クリックで発音 🔊">${entryWord}</span>
                  ${cleanWord.toLowerCase() !== entryWord.toLowerCase() ? `<span style="font-size:0.8rem; color:var(--text-muted);">(文中: ${cleanWord})</span>` : ''}
                  <span class="vocab-pos-badge" style="background:rgba(16,185,129,0.2); border:1px solid rgba(16,185,129,0.4); color:#6ee7b7;">${entryPos}</span>
                  ${window.renderSoftSignGenderBadge ? window.renderSoftSignGenderBadge(entryWord, cleanWord, entryPos, entryMeaning) : ''}
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <button class="bookmark-toggle-btn ondemand-bm-btn"
                    data-word="${cleanWordAttr}" 
                    data-base="${cleanWordAttr}" 
                    data-pos="${cleanPosAttr}" 
                    data-meaning="${cleanMeaningAttr}" 
                    data-role="${cleanRoleAttr}"
                    style="background:transparent; border:none; cursor:pointer; font-size:0.78rem; color:${isBm ? 'var(--gold-light)' : 'var(--text-muted)'};" title="単語帳にマーク (☆)">
                    ${isBm ? '★ マーク済み' : '☆ マーク'}
                  </button>
                  <button class="ondemand-close-btn" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem; padding:0 4px;" title="閉じる">✕</button>
                </div>
              </div>
              <div class="ondemand-meaning">${entryMeaning}</div>
              ${entryAnatomy ? `<div class="ondemand-anatomy">【文法解剖】${fmt(entryAnatomy)}</div>` : ''}
              ${hasTable ? `
                <div style="margin-top:10px;">
                  <button class="ondemand-table-toggle-btn" id="ondemandToggleTableBtn">📊 変化・活用表を表示 ▼</button>
                  <div class="ondemand-table-box" id="ondemandTableBox" style="display:none;">
                    ${tableContentHtml}
                  </div>
                </div>
              ` : ''}
            </div>
          `;

          // Word pronunciation
          const wordTextEl = ondemandContainer.querySelector('.ondemand-word-text');
          if (wordTextEl) {
            wordTextEl.onclick = (eText) => {
              eText.stopPropagation();
              if (window.TTSPlayer) {
                window.TTSPlayer.stop();
                window.TTSPlayer.speakWord(entryWord);
              }
            };
          }

          // Close button
          const closeBtn = ondemandContainer.querySelector('.ondemand-close-btn');
          if (closeBtn) {
            closeBtn.onclick = (eClose) => {
              eClose.stopPropagation();
              ondemandContainer.innerHTML = '';
              tokenSpan.classList.remove('inspect-active');
            };
          }

          // Table toggle button
          const tableBtn = ondemandContainer.querySelector('#ondemandToggleTableBtn');
          const tableBox = ondemandContainer.querySelector('#ondemandTableBox');
          if (tableBtn && tableBox) {
            tableBtn.onclick = (eTbl) => {
              eTbl.stopPropagation();
              const isHidden = tableBox.style.display === 'none';
              tableBox.style.display = isHidden ? 'block' : 'none';
              tableBtn.textContent = isHidden ? '📊 変化・活用表を隠す ▲' : '📊 変化・活用表を表示 ▼';
            };
          }

          // Bookmark button
          const bmBtn = ondemandContainer.querySelector('.ondemand-bm-btn');
          if (bmBtn) {
            bmBtn.onclick = async (eBm) => {
              eBm.stopPropagation();
              const w = bmBtn.dataset.word;
              if (w && window.API) {
                const res = await window.API.toggleBookmark({
                  word: w,
                  base: bmBtn.dataset.base || w,
                  pos: bmBtn.dataset.pos || '',
                  meaning: bmBtn.dataset.meaning || '',
                  role: bmBtn.dataset.role || '',
                  notes: entryAnatomy || '',
                  example_ru: p.ru || '',
                  example_ja: p.ja || ''
                });
                if (res && res.status === 'ok') {
                  bmBtn.textContent = res.is_bookmarked ? '★ マーク済み' : '☆ マーク';
                  bmBtn.style.color = res.is_bookmarked ? 'var(--gold-light)' : 'var(--text-muted)';
                  if (window.App) {
                    window.App.updateBookmarkBadge(res.bookmarks_count);
                  }
                }
              }
            };
          }

        } catch (err) {
          console.error('On-demand lookup failed:', err);
          ondemandContainer.innerHTML = `
            <div class="ondemand-vocab-card" style="border-left-color:var(--coral);">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="font-size:0.85rem; color:var(--coral);">照会中にエラーが発生しました: ${err.message}</div>
                <button class="ondemand-close-btn" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem;">✕</button>
              </div>
            </div>
          `;
          const closeBtn = ondemandContainer.querySelector('.ondemand-close-btn');
          if (closeBtn) {
            closeBtn.onclick = () => {
              ondemandContainer.innerHTML = '';
              tokenSpan.classList.remove('inspect-active');
            };
          }
        }
      });
    });

    // Attach handbook jump
    const modalHbBtn = body.querySelector('#modalHandbookBtn');
    if (modalHbBtn) {
      modalHbBtn.onclick = () => {
        if (window.TTSPlayer) window.TTSPlayer.stop();
        modal.classList.remove('open');
        const tag = modalHbBtn.dataset.tag;
        if (tag && window.Handbook) {
          window.Handbook.openTag(tag);
        }
      };
    }

    // Attach bookmark buttons
    body.querySelectorAll('.bookmark-toggle-btn:not(.ondemand-bm-btn)').forEach(btn => {
      btn.onclick = async () => {
        const w = btn.dataset.word;
        if (w && window.API) {
          const res = await window.API.toggleBookmark({
            word: w,
            base: btn.dataset.base || w,
            pos: btn.dataset.pos || '',
            meaning: btn.dataset.meaning || '',
            role: btn.dataset.role || '',
            notes: btn.dataset.role || '',
            example_ru: p.ru || '',
            example_ja: p.ja || ''
          });
          if (res && res.status === 'ok') {
            btn.textContent = res.is_bookmarked ? '★ マーク済み' : '☆ マーク';
            btn.style.color = res.is_bookmarked ? 'var(--gold-light)' : 'var(--text-muted)';
            if (window.App) {
              window.App.updateBookmarkBadge(res.bookmarks_count);
            }
          }
        }
      };
    });

    modal.classList.add('open');

    // Autoplay: Automatically start reading this sentence when explainer dialog opens
    if (modalPlayBtn) {
      setTimeout(() => {
        if (modal.classList.contains('open') && window.TTSPlayer) {
          modalTokens.forEach(t => {
            t.classList.remove('karaoke-active');
            t.classList.remove('inspect-active');
          });
          window.TTSPlayer.speakSentence(
            p.ru,
            tokens,
            (wIdx) => {
              modalTokens.forEach((span, i) => {
                if (i === wIdx) span.classList.add('karaoke-active');
                else span.classList.remove('karaoke-active');
              });
            },
            () => {
              modalTokens.forEach(span => span.classList.remove('karaoke-active'));
            }
          );
        }
      }, 120);
    }
  }

  // --------------------------------------------------------------------------
  // Dedicated View: Story Memoir (ストーリー専用回)
  // --------------------------------------------------------------------------
  renderMemoirSession() {
    const s = this.sessionData;
    const dayNum = s.day_index || s.day || (s.session_id?.match(/day(\d+)_/)?.[1]) || (window.App?.selectedDay) || 15;

    // Update global header capsule
    const headerDayBadge = document.getElementById('headerDayBadge');
    const headerSessionBadge = document.getElementById('headerSessionBadge');
    if (headerDayBadge) headerDayBadge.textContent = `📅 Day ${dayNum} ［回想録］`;
    if (headerSessionBadge) headerSessionBadge.textContent = '音楽院ストーリー';

    this.container.innerHTML = `
      <div class="player-view">
        <div class="player-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="player-back-btn" id="memoirExitBtn">← サロン (Esc)</button>
            <div class="player-day-indicator">
              <span class="day-tag">📅 Day ${dayNum} ［回想録］</span>
              <span class="phase-tag">音楽院ストーリー</span>
            </div>
          </div>
          <div style="font-size:0.88rem; color:var(--gold-light); font-weight:600;">📖 ${s.title}</div>
          <span class="session-badge story">回想録ストーリー専用回</span>
        </div>

        <div style="display:grid; grid-template-columns:300px 1fr; gap:28px;">
          <div class="tanya-portrait-box">
            <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="tanya-portrait-img">
            <div class="tanya-expression-tag">モスクワ音楽院の回想</div>
          </div>
          <div style="display:flex; flex-direction:column; gap:20px;">
            <div class="dialogue-bubble">
              <div class="dialogue-speaker">✨ ターニャより</div>
              <div>${s.tanya_greeting || "モスクワ音楽院で紡がれる、音楽と言葉の物語をお届けします。"}</div>
            </div>

            <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:28px; line-height:1.85; font-size:1.02rem; color:var(--text-primary); box-shadow:var(--shadow-md);">
              ${s.content_html}
            </div>

            ${s.cultural_column ? `
              <div class="memoir-culture-card">
                <div class="memoir-culture-title">${s.cultural_column.title || '🏛️ ロシア音楽・文化サロンコラム'}</div>
                ${s.cultural_column.lead ? `<div style="font-size:0.90rem; font-weight:600; color:#ffe599; margin-bottom:8px; line-height:1.6;">${s.cultural_column.lead}</div>` : ''}
                <div class="memoir-culture-body">${s.cultural_column.body || s.cultural_column.text || ''}</div>
                ${s.cultural_column.historical_context ? `<div class="memoir-culture-context">📜 時代背景・音楽史メモ: ${s.cultural_column.historical_context}</div>` : ''}
              </div>
            ` : ''}

            ${s.musical_nuances && s.musical_nuances.length > 0 ? `
              <div class="memoir-phrase-section">
                <div style="font-size:0.92rem; font-weight:700; color:var(--gold-light); margin-bottom:12px; display:flex; align-items:center; gap:6px;">
                  <span>🎹 本日の音楽院ロシア語ニュアンス・生きた表現</span>
                </div>
                <div class="memoir-vocab-grid">
                  ${s.musical_nuances.map(item => {
                    const ruText = item.phrase || item.ru || '';
                    const jaText = item.meaning || item.ja || '';
                    const noteText = item.nuance || item.note || '';
                    return `
                      <div class="memoir-phrase-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                          <div class="memoir-phrase-ru ru-text">${ruText}</div>
                          <button class="phrase-audio-btn" data-ru="${ruText}" title="発音を聞く 🔊">🔊</button>
                        </div>
                        <div class="memoir-phrase-ja">${jaText}</div>
                        ${noteText ? `<div class="memoir-phrase-note">💡 ${noteText}</div>` : ''}
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
            ` : ''}

            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:0.84rem; color:var(--gold-light);">🏆 読了記念バッジ獲得 (+10 EXP)</span>
              <button class="wrapup-finish-btn" id="memoirFinishBtn">
                <span>読了してサロンへ戻る</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Wire audio buttons for musical nuances
    this.container.querySelectorAll('.phrase-audio-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const ruText = btn.dataset.ru;
        if (ruText && window.TTSPlayer) {
          window.TTSPlayer.speakSentence(ruText);
        }
      };
    });

    let memoirCompleted = false;
    const completeMemoir = async () => {
      if (memoirCompleted) return;
      memoirCompleted = true;
      if (window.TTSPlayer) window.TTSPlayer.stop();
      if (window.API) {
        await window.API.postProgress({
          session_id: s.session_id,
          type: s.type,
          intimacy_gain: 10,
          unlocked_badge: s.unlocked_badge || null
        });
      }
      if (window.DistanceMeter) window.DistanceMeter.addExp(10);
      if (this.onFinishCallback) this.onFinishCallback();
    };

    this.container.querySelector('#memoirExitBtn').onclick = completeMemoir;
    this.container.querySelector('#memoirFinishBtn').onclick = completeMemoir;
  }

  handleKeyShortcut(e) {
    if (['INPUT', 'TEXTAREA'].includes(e.target?.tagName)) return false;

    const explainModal = document.getElementById('bathExplainModal');
    const isModalOpen = explainModal && explainModal.classList.contains('open');

    // 1) When Bath Explain Modal is OPEN:
    if (isModalOpen) {
      if (e.key === 'Escape') {
        if (window.TTSPlayer) window.TTSPlayer.stop();
        explainModal.classList.remove('open');
        this.clearBathExplainingActive();
        return true;
      }
      if (e.key === ' ' || e.key.toLowerCase() === 'r') {
        e.preventDefault();
        const mPlayBtn = document.getElementById('modalSentencePlayBtn');
        if (mPlayBtn) mPlayBtn.click();
        return true;
      }
      // Speed stepping & replay in modal: [ or , or - to slow down, ] or . or + to speed up, 0 to reset
      if (e.key === '[' || e.key === ',' || e.key === '-') {
        e.preventDefault();
        this.adjustSpeedAndReplay(-0.05);
        return true;
      }
      if (e.key === ']' || e.key === '.' || e.key === '+' || e.key === '=') {
        e.preventDefault();
        this.adjustSpeedAndReplay(+0.05);
        return true;
      }
      if (e.key === '0') {
        e.preventDefault();
        this.adjustSpeedAndReplay(0, null, null, 1.0);
        return true;
      }
      if (e.key.toLowerCase() === 'l') {
        e.preventDefault();
        this.startLadderListening();
        return true;
      }
      // C or T: Toggle declension table in modal
      if (e.key.toLowerCase() === 'c' || e.key.toLowerCase() === 't') {
        e.preventDefault();
        const tblBtn = document.getElementById('ondemandToggleTableBtn');
        if (tblBtn) tblBtn.click();
        return true;
      }
      // N or J: Next sentence explanation
      if (e.key.toLowerCase() === 'n' || e.key.toLowerCase() === 'j') {
        e.preventDefault();
        this.navigateBathExplainer(1);
        return true;
      }
      // P or K: Previous sentence explanation
      if (e.key.toLowerCase() === 'p' || e.key.toLowerCase() === 'k') {
        e.preventDefault();
        this.navigateBathExplainer(-1);
        return true;
      }
      // 1, 2, 3, etc.: Jump directly to sentence index
      if (/^[1-9]$/.test(e.key)) {
        const targetIdx = parseInt(e.key, 10) - 1;
        if (this.bathParagraphs && targetIdx >= 0 && targetIdx < this.bathParagraphs.length) {
          e.preventDefault();
          this.openParagraphExplainer(this.bathParagraphs[targetIdx], targetIdx, this.bathParagraphs);
          return true;
        }
      }
      // Trap all other keys while modal is open so background actions aren't triggered
      return true;
    }

    // 2) When in listening_bath session (modal is closed):
    if (this.sessionData && this.sessionData.type === 'listening_bath') {
      // Speed stepping & replay in listening bath
      if (e.key === '[' || e.key === ',' || e.key === '-') {
        e.preventDefault();
        this.adjustSpeedAndReplay(-0.05);
        return true;
      }
      if (e.key === ']' || e.key === '.' || e.key === '+' || e.key === '=') {
        e.preventDefault();
        this.adjustSpeedAndReplay(+0.05);
        return true;
      }
      if (e.key === '0') {
        e.preventDefault();
        this.adjustSpeedAndReplay(0, null, null, 1.0);
        return true;
      }
      if (e.key.toLowerCase() === 'l') {
        e.preventDefault();
        this.startLadderListening();
        return true;
      }
      // 1, 2, 3, etc. -> Open structural & grammar explanation dialog
      if (/^[1-9]$/.test(e.key)) {
        const targetIdx = parseInt(e.key, 10) - 1;
        if (this.bathParagraphs && targetIdx >= 0 && targetIdx < this.bathParagraphs.length) {
          e.preventDefault();
          this.openParagraphExplainer(this.bathParagraphs[targetIdx], targetIdx, this.bathParagraphs);
          return true;
        }
      }
      // Space or R -> Play/stop sequential audio
      if (e.key === ' ' || e.key.toLowerCase() === 'r') {
        e.preventDefault();
        const playBtn = this.container.querySelector('#bathPlayAllBtn');
        if (playBtn) playBtn.click();
        return true;
      }
      // Enter -> Complete session
      if (e.key === 'Enter') {
        e.preventDefault();
        const bathBtn = this.container.querySelector('#bathCompleteBtn');
        if (bathBtn) bathBtn.click();
        return true;
      }
      if (e.key === 'Escape') {
        if (window.TTSPlayer) window.TTSPlayer.stop();
        if (this.onFinishCallback) this.onFinishCallback();
        return true;
      }
      return false;
    }

    // 3) When in memoir session (music story):
    if (this.sessionData && this.sessionData.type === 'memoir') {
      const k = e.key.toLowerCase();
      if (e.key === 'Escape' || e.key === 'Enter' || k === 'n' || k === 'j') {
        e.preventDefault();
        const finishBtn = this.container.querySelector('#memoirFinishBtn') || this.container.querySelector('#memoirExitBtn');
        if (finishBtn) finishBtn.click();
        else if (this.onFinishCallback) this.onFinishCallback();
        return true;
      }
      return false;
    }

    if (this.currentPhase === 3 && window.QuizEngine) {
      const handled = window.QuizEngine.handleKeyShortcut(e.key);
      if (handled) return true;
    }

    const key = e.key.toLowerCase();

    // Universal speed stepping & Ladder Listening across Phase 1 / Phase 2
    if (e.key === '[' || e.key === ',' || e.key === '-') {
      e.preventDefault();
      this.adjustSpeedAndReplay(-0.05);
      return true;
    }
    if (e.key === ']' || e.key === '.' || e.key === '+' || e.key === '=') {
      e.preventDefault();
      this.adjustSpeedAndReplay(+0.05);
      return true;
    }
    if (e.key === '0') {
      e.preventDefault();
      this.adjustSpeedAndReplay(0, null, null, 1.0);
      return true;
    }
    if (key === 'l') {
      e.preventDefault();
      this.startLadderListening();
      return true;
    }

    if (e.key === 'Escape') {
      if (this.onFinishCallback) this.onFinishCallback();
      return true;
    } else if (e.key === ' ' || key === 'r') {
      // Space or R -> Play/pause audio
      if (this.currentPhase === 2) {
        const p2Btn = this.container.querySelector('#p2PlayBtn');
        if (p2Btn) {
          p2Btn.click();
        } else if (window.TTSPlayer && this.currentActiveSentenceRu) {
          window.TTSPlayer.speakSentence(this.currentActiveSentenceRu);
        }
      } else if (this.currentPhase === 3 && (this.isNonGraded || (this.sessionData.quiz_items || []).length === 0)) {
        const skipBtn = this.container.querySelector('#skipQuizBtn');
        if (skipBtn) skipBtn.click();
      } else {
        const playBtn = this.container.querySelector('.play-audio-btn') || this.container.querySelector('#bathPlayAllBtn');
        if (playBtn) playBtn.click();
      }
      return true;
    } else if (e.key === 'Enter' || key === 'n' || key === 'j') {
      // Enter, N, J -> Next
      if (this.currentPhase === 1) {
        const nextBtn = this.container.querySelector('#p1NextBtn');
        if (nextBtn) nextBtn.click();
      } else if (this.currentPhase === 2) {
        const nextBtn = this.container.querySelector('#p2NextBtn');
        if (nextBtn) nextBtn.click();
      } else if (this.currentPhase === 3) {
        const skipBtn = this.container.querySelector('#skipQuizBtn') || this.container.querySelector('#quizNextBtn') || this.container.querySelector('.quiz-next-btn');
        if (skipBtn) skipBtn.click();
      } else if (this.currentPhase === 4) {
        const finishBtn = this.container.querySelector('#wrapupFinishBtn');
        if (finishBtn) finishBtn.click();
      } else if (this.sessionData.type === 'memoir') {
        const memBtn = this.container.querySelector('#memoirFinishBtn');
        if (memBtn) memBtn.click();
      }
      return true;
    } else if (e.key === 'Tab') {
      e.preventDefault();
      if (this.currentPhase === 2 && window.GrammarMutator) {
        window.GrammarMutator.cycleNext();
      }
      return true;
    } else if (key === 'f') {
      if (this.currentPhase === 2) {
        if (e.shiftKey) {
          this.cyclePrevToken();
        } else {
          this.cycleNextToken();
        }
      }
      return true;
    } else if (key === 'd') {
      if (this.currentPhase === 2) {
        this.cyclePrevToken();
      }
      return true;
    } else if (key === 'c' || key === 't') {
      if (this.currentPhase === 2) {
        const reciteBtn = this.container.querySelector('.conjugation-recite-btn');
        if (reciteBtn) {
          reciteBtn.click();
          return true;
        }
      }
      return false;
    }
    return false;
  }

  cycleNextToken() {
    const tokens = this.container.querySelectorAll('#p2TokensContainer .word-token');
    if (!tokens || tokens.length === 0) return;

    if (this.currentFocusedTokenIdx === undefined || this.currentFocusedTokenIdx === null || this.currentFocusedTokenIdx < 0) {
      this.currentFocusedTokenIdx = 0;
    } else {
      this.currentFocusedTokenIdx = (this.currentFocusedTokenIdx + 1) % tokens.length;
    }

    const targetToken = tokens[this.currentFocusedTokenIdx];
    if (targetToken) {
      targetToken.click();
      targetToken.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }

  cyclePrevToken() {
    const tokens = this.container.querySelectorAll('#p2TokensContainer .word-token');
    if (!tokens || tokens.length === 0) return;

    if (this.currentFocusedTokenIdx === undefined || this.currentFocusedTokenIdx === null || this.currentFocusedTokenIdx <= 0) {
      this.currentFocusedTokenIdx = tokens.length - 1;
    } else {
      this.currentFocusedTokenIdx = this.currentFocusedTokenIdx - 1;
    }

    const targetToken = tokens[this.currentFocusedTokenIdx];
    if (targetToken) {
      targetToken.click();
      targetToken.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }
}

window.LessonPlayer = new LessonPlayer();
