/**
 * Russian Typing Dojo Engine
 * - Optimized for ThinkPad JIS 109 Keyboard & Windows Russian Layout
 * - Level 0: Step-by-step key acquisition with meaningful words and phrases
 * - Level 1: A1 Mixed practical sentences & spell checks
 * - Web Audio sound feedback & Edge-TTS native pronunciation
 * - 33-Cyrillic-key mastery matrix & heatmap persistence
 */

(function () {
  'use strict';

  // --- Audio Synth for subtle tactile feedback ---
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  function playClickSound(success = true) {
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (success) {
      // Pleasant mechanical keyboard click
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(600, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(150, audioCtx.currentTime + 0.04);
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.04);
    } else {
      // Gentle thud for mistake
      osc.type = 'sine';
      osc.frequency.setValueAtTime(140, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(60, audioCtx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.08);
    }
  }

  // --- ThinkPad JIS 109 Keyboard Layout Matrix for Russian ---
  const KEYBOARD_ROWS = [
    // Row 0: Number row
    [
      { code: 'Backquote', ru: 'ё', en: '`', jis: '半角', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'Digit1', ru: '1', en: '1', jis: 'ぬ', shiftRu: '!', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'Digit2', ru: '2', en: '2', jis: 'ふ', shiftRu: '"', finger: 'finger-l-ring', fingerName: '左手・薬指' },
      { code: 'Digit3', ru: '3', en: '3', jis: 'あ', shiftRu: '№', finger: 'finger-l-middle', fingerName: '左手・中指' },
      { code: 'Digit4', ru: '4', en: '4', jis: 'う', shiftRu: ';', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'Digit5', ru: '5', en: '5', jis: 'え', shiftRu: '%', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'Digit6', ru: '6', en: '6', jis: 'お', shiftRu: ':', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'Digit7', ru: '7', en: '7', jis: 'や', shiftRu: '?', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'Digit8', ru: '8', en: '8', jis: 'ゆ', shiftRu: '*', finger: 'finger-r-middle', fingerName: '右手・中指' },
      { code: 'Digit9', ru: '9', en: '9', jis: 'よ', shiftRu: '(', finger: 'finger-r-ring', fingerName: '右手・薬指' },
      { code: 'Digit0', ru: '0', en: '0', jis: 'わ', shiftRu: ')', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Minus', ru: '-', en: '-', jis: 'ほ', shiftRu: '_', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Equal', ru: '=', en: '^', jis: 'へ', shiftRu: '+', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'IntlYen', ru: '\\', en: '¥', jis: 'ー', shiftRu: '/', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Backspace', ru: '⌫', en: 'BS', jis: '', wide: 'key-wide-1-5', finger: 'finger-r-pinky', fingerName: '右手・小指' }
    ],
    // Row 1: Upper (QWERTY) row
    [
      { code: 'Tab', ru: '⇥', en: 'Tab', jis: '', wide: 'key-wide-1-5', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyQ', ru: 'й', en: 'Q', jis: 'た', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyW', ru: 'ц', en: 'W', jis: 'て', finger: 'finger-l-ring', fingerName: '左手・薬指' },
      { code: 'KeyE', ru: 'у', en: 'E', jis: 'い', finger: 'finger-l-middle', fingerName: '左手・中指' },
      { code: 'KeyR', ru: 'к', en: 'R', jis: 'す', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyT', ru: 'е', en: 'T', jis: 'か', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyY', ru: 'н', en: 'Y', jis: 'ん', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'KeyU', ru: 'г', en: 'U', jis: 'な', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'KeyI', ru: 'ш', en: 'I', jis: 'に', finger: 'finger-r-middle', fingerName: '右手・中指' },
      { code: 'KeyO', ru: 'щ', en: 'O', jis: 'ら', finger: 'finger-r-ring', fingerName: '右手・薬指' },
      { code: 'KeyP', ru: 'з', en: 'P', jis: 'せ', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'BracketLeft', ru: 'х', en: '@', jis: '゛', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'BracketRight', ru: 'ъ', en: '[', jis: '゜', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Enter', ru: '↵', en: 'Enter', jis: '', wide: 'key-wide-1-5', finger: 'finger-r-pinky', fingerName: '右手・小指' }
    ],
    // Row 2: Home (ASDF) row
    [
      { code: 'CapsLock', ru: '⇪', en: 'Caps', jis: '', wide: 'key-wide-1-5', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyA', ru: 'ф', en: 'A', jis: 'ち', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyS', ru: 'ы', en: 'S', jis: 'と', finger: 'finger-l-ring', fingerName: '左手・薬指' },
      { code: 'KeyD', ru: 'в', en: 'D', jis: 'し', finger: 'finger-l-middle', fingerName: '左手・中指' },
      { code: 'KeyF', ru: 'а', en: 'F', jis: 'は', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyG', ru: 'п', en: 'G', jis: 'き', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyH', ru: 'р', en: 'H', jis: 'く', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'KeyJ', ru: 'о', en: 'J', jis: 'ま', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'KeyK', ru: 'л', en: 'K', jis: 'の', finger: 'finger-r-middle', fingerName: '右手・中指' },
      { code: 'KeyL', ru: 'д', en: 'L', jis: 'り', finger: 'finger-r-ring', fingerName: '右手・薬指' },
      { code: 'Semicolon', ru: 'ж', en: ';', jis: 'れ', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Quote', ru: 'э', en: ':', jis: 'け', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'Backslash', ru: 'ё', en: ']', jis: 'む', finger: 'finger-r-pinky', fingerName: '右手・小指' }
    ],
    // Row 3: Bottom (ZXCV) row
    [
      { code: 'ShiftLeft', ru: '⇧', en: 'Shift', jis: '', wide: 'key-wide-2', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyZ', ru: 'я', en: 'Z', jis: 'つ', finger: 'finger-l-pinky', fingerName: '左手・小指' },
      { code: 'KeyX', ru: 'ч', en: 'X', jis: 'さ', finger: 'finger-l-ring', fingerName: '左手・薬指' },
      { code: 'KeyC', ru: 'с', en: 'C', jis: 'そ', finger: 'finger-l-middle', fingerName: '左手・中指' },
      { code: 'KeyV', ru: 'м', en: 'V', jis: 'ひ', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyB', ru: 'и', en: 'B', jis: 'こ', finger: 'finger-l-index', fingerName: '左手・人差し指' },
      { code: 'KeyN', ru: 'т', en: 'N', jis: 'み', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'KeyM', ru: 'ь', en: 'M', jis: 'も', finger: 'finger-r-index', fingerName: '右手・人差し指' },
      { code: 'Comma', ru: 'б', en: ',', jis: 'ね', finger: 'finger-r-middle', fingerName: '右手・中指' },
      { code: 'Period', ru: 'ю', en: '.', jis: 'る', finger: 'finger-r-ring', fingerName: '右手・薬指' },
      { code: 'Slash', ru: '.', en: '/', jis: 'め', shiftRu: ',', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'IntlRo', ru: '\\', en: '_', jis: 'ろ', shiftRu: '/', finger: 'finger-r-pinky', fingerName: '右手・小指' },
      { code: 'ShiftRight', ru: '⇧', en: 'Shift', jis: '', wide: 'key-wide-2', finger: 'finger-r-pinky', fingerName: '右手・小指' }
    ],
    // Row 4: Space row
    [
      { code: 'Space', ru: 'Space', en: 'Space', jis: '', wide: 'key-space', finger: 'finger-thumb', fingerName: '親指' }
    ]
  ];

  // 33 Russian Alphabet letters
  const RUSSIAN_ALPHABET = [
    'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й',
    'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф',
    'х', 'ц', 'ч', 'ш', 'щ', 'ъ', 'ы', 'ь', 'э', 'ю', 'я'
  ];

  // Map each char to keyboard key object
  const CHAR_TO_KEY_MAP = {};
  KEYBOARD_ROWS.forEach(row => {
    row.forEach(key => {
      if (key.ru && key.ru.length === 1) {
        CHAR_TO_KEY_MAP[key.ru.toLowerCase()] = key;
        CHAR_TO_KEY_MAP[key.ru.toUpperCase()] = { ...key, needShift: true };
      }
      if (key.shiftRu) {
        CHAR_TO_KEY_MAP[key.shiftRu] = { ...key, needShift: true };
      }
    });
  });
  CHAR_TO_KEY_MAP[' '] = { code: 'Space', ru: ' ', finger: 'finger-thumb', fingerName: '親指' };
  CHAR_TO_KEY_MAP['!'] = { code: 'Digit1', ru: '!', needShift: true, finger: 'finger-l-pinky', fingerName: '左手・小指' };
  CHAR_TO_KEY_MAP['?'] = { code: 'Digit7', ru: '?', needShift: true, finger: 'finger-r-index', fingerName: '右手・人差し指' };
  CHAR_TO_KEY_MAP[','] = { code: 'Slash', ru: ',', needShift: true, finger: 'finger-r-pinky', fingerName: '右手・小指' };
  CHAR_TO_KEY_MAP['.'] = { code: 'Slash', ru: '.', needShift: false, finger: 'finger-r-pinky', fingerName: '右手・小指' };
  CHAR_TO_KEY_MAP['-'] = { code: 'Minus', ru: '-', needShift: false, finger: 'finger-r-pinky', fingerName: '右手・小指' };

  // --- State ---
  let curriculumData = null;
  let currentMode = 'level0'; // 'level0' or 'level1'
  let currentStageId = 'stage-0-1';
  let currentCategory = 'all';
  let currentPlaylist = [];
  let playlistIndex = 0;
  let currentItem = null;
  let targetChars = [];
  let currentCharIndex = 0;

  // Stats
  let sessionKeystrokes = 0;
  let sessionErrors = 0;
  let sessionStartTime = null;
  let keyHitStats = JSON.parse(localStorage.getItem('ru_typing_key_hits') || '{}');

  // DOM Elements
  const elKeyboard = document.getElementById('kbContainer');
  const elTargetText = document.getElementById('targetText');
  const elTranslation = document.getElementById('translationText');
  const elNoteBox = document.getElementById('noteBox');
  const elBadge = document.getElementById('categoryBadge');
  const elNextCharBadge = document.getElementById('nextCharBadge');
  const elFingerName = document.getElementById('fingerName');
  const elFingerDesc = document.getElementById('fingerDesc');
  const elWpm = document.getElementById('valWpm');
  const elAccuracy = document.getElementById('valAccuracy');
  const elTotalKeys = document.getElementById('valTotalKeys');
  const elMasteryPct = document.getElementById('valMasteryPct');
  const elProgressBarFill = document.getElementById('progressBarFill');
  const elMatrixGrid = document.getElementById('matrixGrid');
  const elWarningOverlay = document.getElementById('warningOverlay');
  const elStageSelect = document.getElementById('stageSelect');
  const elAudioBtn = document.getElementById('btnPlayAudio');
  const elTanyaAvatar = document.getElementById('tanyaAvatarImg');
  const elTanyaSpeech = document.getElementById('tanyaSpeechText');

  // Cursive mode DOM elements
  const elBtnToggleCursive = document.getElementById('btnToggleCursive');
  const elCursiveStatusLabel = document.getElementById('cursiveStatusLabel');
  const elBtnOpenCursiveGuide = document.getElementById('btnOpenCursiveGuide');
  const elBtnCloseCursiveGuide = document.getElementById('btnCloseCursiveGuide');
  const elCursiveModal = document.getElementById('cursiveModal');
  let isCursiveMode = localStorage.getItem('ru_typing_cursive') === 'true';

  let itemMistakes = 0;
  let consecutiveMistakes = 0;

  function applyCursiveMode(enabled) {
    isCursiveMode = enabled;
    localStorage.setItem('ru_typing_cursive', enabled ? 'true' : 'false');
    if (elCursiveStatusLabel) {
      elCursiveStatusLabel.textContent = enabled ? 'ON' : 'OFF';
    }
    if (elBtnToggleCursive) {
      elBtnToggleCursive.classList.toggle('active', enabled);
    }
    document.body.classList.toggle('cursive-mode', enabled);
  }

  function setTanyaGuide(mood, message) {
    if (elTanyaAvatar) {
      const images = {
        smiling: '/assets/images/tanya_smiling.jpg',
        explaining: '/assets/images/tanya_explaining.jpg',
        encouraging: '/assets/images/tanya_encouraging.jpg',
        delighted: '/assets/images/tanya_delighted.jpg',
        thoughtful: '/assets/images/tanya_thoughtful.jpg'
      };
      if (images[mood]) {
        elTanyaAvatar.src = images[mood];
      }
    }
    if (elTanyaSpeech && message) {
      elTanyaSpeech.textContent = message;
    }
  }

  // --- Init ---
  async function init() {
    applyCursiveMode(isCursiveMode);
    renderKeyboard();
    renderMasteryMatrix();
    updateMasteryStats();

    try {
      const res = await fetch('/data/typing_curriculum.json');
      curriculumData = await res.json();
      setupStageSelector();
      loadPlaylist();
      nextItem();
    } catch (e) {
      console.error('Failed to load typing curriculum:', e);
    }

    setupEventListeners();
  }

  // --- Render ThinkPad Keyboard ---
  function renderKeyboard() {
    elKeyboard.innerHTML = '';
    const brand = document.createElement('div');
    brand.className = 'keyboard-brand';
    brand.innerHTML = 'ThinkPad <span class="red-dot">●</span> JIS 109';
    elKeyboard.appendChild(brand);

    KEYBOARD_ROWS.forEach((row, rIdx) => {
      const rowDiv = document.createElement('div');
      rowDiv.className = 'kb-row';
      rowDiv.dataset.row = rIdx;

      row.forEach(key => {
        const keyDiv = document.createElement('div');
        keyDiv.className = `kb-key ${key.finger} ${key.wide || ''}`;
        keyDiv.id = `key-${key.code}`;

        if (key.jis) {
          const jisSpan = document.createElement('span');
          jisSpan.className = 'key-jis';
          jisSpan.textContent = key.jis;
          keyDiv.appendChild(jisSpan);
        }

        const ruSpan = document.createElement('span');
        ruSpan.className = 'key-ru';
        ruSpan.textContent = key.ru || '';
        keyDiv.appendChild(ruSpan);

        if (key.en) {
          const enSpan = document.createElement('span');
          enSpan.className = 'key-en';
          enSpan.textContent = key.en;
          keyDiv.appendChild(enSpan);
        }

        rowDiv.appendChild(keyDiv);
      });
      elKeyboard.appendChild(rowDiv);
    });

    // Add ThinkPad Red TrackPoint between G, H, B (п, р, и)
    const keyG = document.getElementById('key-KeyG');
    const keyH = document.getElementById('key-KeyH');
    if (keyG && keyH) {
      const trackPoint = document.createElement('div');
      trackPoint.className = 'trackpoint-container';
      trackPoint.style.top = '112px';
      trackPoint.style.left = '49.2%';
      elKeyboard.appendChild(trackPoint);
    }
  }

  // --- Render 33 Keys Mastery Matrix ---
  function renderMasteryMatrix() {
    elMatrixGrid.innerHTML = '';
    RUSSIAN_ALPHABET.forEach(char => {
      const count = keyHitStats[char] || 0;
      const chip = document.createElement('div');
      chip.className = 'matrix-chip';
      chip.id = `matrix-${char}`;

      if (count >= 20) {
        chip.classList.add('mastered');
      } else if (count > 0) {
        chip.classList.add('learning');
      }

      chip.innerHTML = `
        <span>${char.toUpperCase()}</span>
        <span class="matrix-count">${count}</span>
      `;
      elMatrixGrid.appendChild(chip);
    });
  }

  function updateMasteryStats() {
    let masteredCount = 0;
    RUSSIAN_ALPHABET.forEach(char => {
      const count = keyHitStats[char] || 0;
      if (count >= 20) masteredCount++;

      const chip = document.getElementById(`matrix-${char}`);
      if (chip) {
        chip.className = 'matrix-chip';
        if (count >= 20) {
          chip.classList.add('mastered');
        } else if (count > 0) {
          chip.classList.add('learning');
        }
        chip.querySelector('.matrix-count').textContent = count;
      }

      // Update keyboard key heat styling
      const keyObj = CHAR_TO_KEY_MAP[char];
      if (keyObj) {
        const keyEl = document.getElementById(`key-${keyObj.code}`);
        if (keyEl) {
          keyEl.classList.remove('heat-1', 'heat-2', 'heat-3');
          if (count >= 20) keyEl.classList.add('heat-3');
          else if (count >= 8) keyEl.classList.add('heat-2');
          else if (count > 0) keyEl.classList.add('heat-1');
        }
      }
    });

    const pct = Math.round((masteredCount / RUSSIAN_ALPHABET.length) * 100);
    elMasteryPct.textContent = `${pct}%`;
    elProgressBarFill.style.width = `${pct}%`;
  }

  // --- Stage & Playlist Management ---
  function setupStageSelector() {
    elStageSelect.innerHTML = '';
    if (currentMode === 'level0') {
      curriculumData.level0.stages.forEach(stage => {
        const opt = document.createElement('option');
        opt.value = stage.id;
        opt.textContent = stage.name;
        elStageSelect.appendChild(opt);
      });
      elStageSelect.value = currentStageId;
    } else {
      const optAll = document.createElement('option');
      optAll.value = 'all';
      optAll.textContent = '🌟 全カテゴリ・シャッフルミックス';
      elStageSelect.appendChild(optAll);

      curriculumData.level1.categories.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat.id;
        opt.textContent = cat.name;
        elStageSelect.appendChild(opt);
      });
      elStageSelect.value = currentCategory;
    }
  }

  function loadPlaylist() {
    if (currentMode === 'level0') {
      const stage = curriculumData.level0.stages.find(s => s.id === currentStageId) || curriculumData.level0.stages[0];
      currentPlaylist = stage.items ? [...stage.items] : [];
    } else {
      if (currentCategory === 'all') {
        let combined = [];
        curriculumData.level1.categories.forEach(cat => {
          cat.items.forEach(it => {
            combined.push({ ...it, badge: cat.badge });
          });
        });
        // Shuffle
        currentPlaylist = combined.sort(() => Math.random() - 0.5);
      } else {
        const cat = curriculumData.level1.categories.find(c => c.id === currentCategory);
        currentPlaylist = cat ? cat.items.map(it => ({ ...it, badge: cat.badge })) : [];
      }
    }
    playlistIndex = 0;
  }

  function nextItem() {
    if (playlistIndex >= currentPlaylist.length) {
      playlistIndex = 0;
    }
    currentItem = currentPlaylist[playlistIndex++];
    renderCurrentPrompt();
  }

  function renderCurrentPrompt() {
    if (!currentItem) return;

    // Display text
    const text = currentItem.ru;
    targetChars = Array.from(text);
    currentCharIndex = 0;

    // Badge
    elBadge.textContent = currentItem.badge || (currentMode === 'level0' ? 'Level 0 運指ドリル' : 'A1実戦');
    elTranslation.textContent = currentItem.ja || '';

    // Note / Spelling gap memo
    if (currentItem.note) {
      elNoteBox.style.display = 'flex';
      elNoteBox.innerHTML = `<strong>💡 ポイント:</strong> <span>${currentItem.note}</span>`;
    } else {
      elNoteBox.style.display = 'none';
    }

    // Build target text character boxes
    elTargetText.innerHTML = '';
    targetChars.forEach((ch, idx) => {
      const span = document.createElement('span');
      if (ch === ' ') {
        span.className = 'char-box char-space';
        span.textContent = ' ';
      } else {
        span.className = 'char-box';
        span.textContent = ch;
        span.title = `標準活字体: ${ch}`;

        // In cursive mode, show subtle block print sub-hint for shape-shifting trap letters
        if (isCursiveMode && ['т', 'д', 'и', 'п', 'г', 'в', 'ч'].includes(ch.toLowerCase())) {
          const subHint = document.createElement('span');
          subHint.className = 'cursive-sub-hint';
          subHint.textContent = ch;
          span.appendChild(subHint);
        }
      }
      span.id = `char-box-${idx}`;
      elTargetText.appendChild(span);
    });

    // Reset mistake counters for current item
    itemMistakes = 0;
    consecutiveMistakes = 0;

    // Set Tanya guidance message
    if (currentMode === 'level0') {
      const hint = currentItem.note || 'ピアノを弾くように、指の力を抜いて画面のガイドを見て打ってみてね♪';
      setTanyaGuide('explaining', hint);
    } else {
      const hint = currentItem.note ? `【注目】${currentItem.note}` : 'ロシア人の友人とチャットするイメージで打ってみてね♪';
      setTanyaGuide('smiling', hint);
    }

    highlightCurrentTarget();
    playTtsAudio(currentItem.ru, false); // Warm audio cache in background
  }

  // --- Target Highlighting & On-Screen Key Guide ---
  function highlightCurrentTarget() {
    // Clear all target classes from character boxes
    targetChars.forEach((_, idx) => {
      const box = document.getElementById(`char-box-${idx}`);
      if (box) {
        box.classList.remove('char-current', 'char-error');
      }
    });

    // Clear active key highlight on keyboard
    document.querySelectorAll('.kb-key.key-active-target').forEach(k => {
      k.classList.remove('key-active-target');
    });

    if (currentCharIndex >= targetChars.length) {
      // Completed current item!
      onItemCompleted();
      return;
    }

    // Highlight current character in prompt
    const currentBox = document.getElementById(`char-box-${currentCharIndex}`);
    if (currentBox) {
      currentBox.classList.add('char-current');
    }

    // Next character details
    const targetChar = targetChars[currentCharIndex];
    const keyInfo = CHAR_TO_KEY_MAP[targetChar] || CHAR_TO_KEY_MAP[targetChar.toLowerCase()];

    if (targetChar === ' ') {
      elNextCharBadge.textContent = '␣';
      elFingerName.textContent = '親指 (Space)';
      elFingerDesc.textContent = 'スペースキーを押してください';
    } else {
      elNextCharBadge.textContent = targetChar;
      if (keyInfo) {
        const shiftNote = keyInfo.needShift ? ' [Shift + キー]' : '';
        elFingerName.textContent = `${keyInfo.fingerName}${shiftNote}`;
        elFingerDesc.textContent = `キー: ${keyInfo.ru.toUpperCase()} (${keyInfo.en || ''})`;
      } else {
        elFingerName.textContent = 'キー入力';
        elFingerDesc.textContent = targetChar;
      }
    }

    // Highlight key on keyboard
    if (keyInfo) {
      const keyEl = document.getElementById(`key-${keyInfo.code}`);
      if (keyEl) {
        keyEl.classList.add('key-active-target');
      }
      if (keyInfo.needShift) {
        const shiftLeft = document.getElementById('key-ShiftLeft');
        if (shiftLeft) shiftLeft.classList.add('key-active-target');
      }
    }
  }

  // --- Input Processing ---
  function handleKeyPress(e) {
    // If modal is open, Escape closes it
    if (e.key === 'Escape') {
      if (elCursiveModal && elCursiveModal.classList.contains('open')) {
        elCursiveModal.classList.remove('open');
        return;
      }
    }

    // Ignore function keys, Tab, Enter, etc. if not targeted
    if (e.key === 'F5' || e.key === 'F12' || (e.ctrlKey && e.key === 'r')) return;

    // Detect Latin / English input mode and warn
    if (/^[a-zA-Z]$/.test(e.key) && !/^[a-zA-Z]$/.test(targetChars[currentCharIndex])) {
      showWarningOverlay('⚠️ ロシア語入力に切り替えてください [Alt+Shift または Win+Space]');
      e.preventDefault();
      return;
    }

    // Ignore modifiers themselves
    if (['Shift', 'Control', 'Alt', 'Meta', 'CapsLock'].includes(e.key)) return;

    e.preventDefault();

    if (!sessionStartTime) {
      sessionStartTime = Date.now();
    }
    sessionKeystrokes++;

    const inputChar = e.key;
    const targetChar = targetChars[currentCharIndex];

    // Check match (strict Russian case or exact match)
    if (inputChar === targetChar) {
      // Correct!
      playClickSound(true);
      consecutiveMistakes = 0;
      const box = document.getElementById(`char-box-${currentCharIndex}`);
      if (box) {
        box.classList.remove('char-current', 'char-error');
        box.classList.add('char-correct');
      }

      // Record hit for 33 letters
      const lowerChar = targetChar.toLowerCase();
      if (RUSSIAN_ALPHABET.includes(lowerChar)) {
        keyHitStats[lowerChar] = (keyHitStats[lowerChar] || 0) + 1;
        localStorage.setItem('ru_typing_key_hits', JSON.stringify(keyHitStats));
        updateMasteryStats();
      }

      // Physical key press visual feedback
      animateKeyPress(e.code);

      currentCharIndex++;
      highlightCurrentTarget();
    } else {
      // Mistake!
      playClickSound(false);
      sessionErrors++;
      itemMistakes++;
      consecutiveMistakes++;

      if (consecutiveMistakes >= 2) {
        setTanyaGuide('encouraging', '焦らなくて大丈夫よ！キーボードを手探りせず、画面で光っているキーを見てね。');
      }

      const box = document.getElementById(`char-box-${currentCharIndex}`);
      if (box) {
        box.classList.add('char-error');
        setTimeout(() => box.classList.remove('char-error'), 300);
      }

      // Anti-Hunting Guard: Pulse target key more vigorously
      const keyInfo = CHAR_TO_KEY_MAP[targetChar] || CHAR_TO_KEY_MAP[targetChar.toLowerCase()];
      if (keyInfo) {
        const keyEl = document.getElementById(`key-${keyInfo.code}`);
        if (keyEl) {
          keyEl.classList.add('key-active-target');
        }
      }
    }

    updateSessionStats();
  }

  function animateKeyPress(code) {
    const keyEl = document.getElementById(`key-${code}`);
    if (keyEl) {
      keyEl.classList.add('key-pressed');
      setTimeout(() => keyEl.classList.remove('key-pressed'), 120);
    }
  }

  function onItemCompleted() {
    // Tanya praise reaction
    if (itemMistakes === 0) {
      setTanyaGuide('delighted', 'Прекрасно! （完璧よ！）ピアノの美しいパッセージのように流れるタイピングね♪');
    } else {
      setTanyaGuide('smiling', 'Хорошо! （よくできました！）この調子でどんどん指に馴染ませていきましょう♪');
    }

    // Play native TTS pronunciation upon finishing sentence
    if (currentItem && currentItem.ru) {
      playTtsAudio(currentItem.ru, true);
    }

    // Briefly show completion and move to next
    setTimeout(() => {
      nextItem();
    }, 1100);
  }

  // --- Stats Calculation ---
  function updateSessionStats() {
    elTotalKeys.textContent = sessionKeystrokes;

    const accuracy = sessionKeystrokes > 0
      ? Math.round(((sessionKeystrokes - sessionErrors) / sessionKeystrokes) * 100)
      : 100;
    elAccuracy.textContent = `${accuracy}%`;

    if (sessionStartTime) {
      const minutes = (Date.now() - sessionStartTime) / 60000;
      if (minutes > 0.05) {
        // Average Russian word length ~ 5 characters
        const wpm = Math.round((sessionKeystrokes / 5) / minutes);
        elWpm.textContent = wpm;
      }
    }
  }

  // --- Warning Overlay ---
  let warningTimer = null;
  function showWarningOverlay(msg) {
    setTanyaGuide('thoughtful', 'あら、英語入力モードになっているわ。[Alt+Shift] または [Win+Space] でロシア語に切り替えてね！');
    elWarningOverlay.textContent = msg;
    elWarningOverlay.style.display = 'flex';
    clearTimeout(warningTimer);
    warningTimer = setTimeout(() => {
      elWarningOverlay.style.display = 'none';
    }, 3000);
  }

  // --- Audio / TTS Integration ---
  let currentAudio = null;
  function playTtsAudio(text, autoPlay = true) {
    if (!text) return;
    const url = `/api/tts?text=${encodeURIComponent(text)}&rate=1.0`;

    if (autoPlay) {
      if (currentAudio) {
        currentAudio.pause();
      }
      currentAudio = new Audio(url);
      currentAudio.play().catch(e => {
        // Autoplay may be restricted before first click
        console.log('Audio autoplay prevented:', e);
      });
    }
  }

  // --- Event Listeners ---
  function setupEventListeners() {
    window.addEventListener('keydown', handleKeyPress);

    // Audio Play Button
    elAudioBtn.addEventListener('click', () => {
      if (currentItem && currentItem.ru) {
        playTtsAudio(currentItem.ru, true);
      }
    });

    // Mode Tabs
    document.querySelectorAll('.mode-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentMode = tab.dataset.mode;
        setupStageSelector();
        loadPlaylist();
        nextItem();
      });
    });

    // Stage Selector
    elStageSelect.addEventListener('change', (e) => {
      if (currentMode === 'level0') {
        currentStageId = e.target.value;
      } else {
        currentCategory = e.target.value;
      }
      loadPlaylist();
      nextItem();
    });

    // Cursive Toggle Button
    if (elBtnToggleCursive) {
      elBtnToggleCursive.addEventListener('click', () => {
        applyCursiveMode(!isCursiveMode);
        if (isCursiveMode) {
          setTanyaGuide('explaining', '✍️ 筆記体モードをONにしたわ！特に т (m) や д (g)、и (u) に気をつけて打ってみてね♪');
        } else {
          setTanyaGuide('smiling', '標準のブロック体表示に戻したわ。リラックスして練習を続けましょう♪');
        }
        renderCurrentPrompt();
      });
    }

    // Cursive Guide Modal Open/Close
    if (elBtnOpenCursiveGuide && elCursiveModal) {
      elBtnOpenCursiveGuide.addEventListener('click', () => {
        elCursiveModal.classList.add('open');
      });
    }
    if (elBtnCloseCursiveGuide && elCursiveModal) {
      elBtnCloseCursiveGuide.addEventListener('click', () => {
        elCursiveModal.classList.remove('open');
      });
    }
    if (elCursiveModal) {
      elCursiveModal.addEventListener('click', (e) => {
        if (e.target === elCursiveModal) {
          elCursiveModal.classList.remove('open');
        }
      });
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
