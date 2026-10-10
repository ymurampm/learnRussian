/**
 * Tanya Russian Trainer - TTS & Synchronized Karaoke Player
 * Hybrid Engine:
 * Primary: Microsoft Azure Russian Neural Voice (ru-RU-SvetlanaNeural via /api/tts)
 * Fallback: Web Speech API (window.speechSynthesis)
 * Supports audio caching, speed adjustment, and synchronized karaoke word highlight.
 */

class TTSKaraokePlayer {
  constructor() {
    this.synth = window.speechSynthesis;
    this.currentVoice = null;
    this.currentRate = 1.0;
    this.isPlaying = false;
    this.audioElement = new Audio();
    this.activeTimeouts = [];
    this.animFrameId = null;
    this.lastHighlightedIndex = -1;
    this.onWordHighlightCallback = null;
    this.onEndCallback = null;
    this.useNeural = true;
    this.playToken = 0;
    this.ladderStepPauseMs = 400; // Snappy 400ms pause between ladder steps (shortened from 1200ms)

    this.setupAudioListeners();
    this.initFallbackVoices();
  }

  setupAudioListeners() {
    this.audioElement.addEventListener('ended', () => {
      this.isPlaying = false;
      this.clearSync();
      if (this.onWordHighlightCallback) {
        this.onWordHighlightCallback(-1);
      }
      if (this.onEndCallback) {
        const cb = this.onEndCallback;
        this.onEndCallback = null;
        cb();
      }
    });

    this.audioElement.addEventListener('pause', () => {
      if (this.audioElement.currentTime < this.audioElement.duration) {
        this.isPlaying = false;
        this.clearSync();
        if (this.onWordHighlightCallback) {
          this.onWordHighlightCallback(-1);
        }
      }
    });

    this.audioElement.addEventListener('error', (e) => {
      console.warn('HTML5 Audio error, falling back:', e);
      this.isPlaying = false;
      this.clearSync();
      if (this.onEndCallback) {
        const cb = this.onEndCallback;
        this.onEndCallback = null;
        cb();
      }
    });
  }

  initFallbackVoices() {
    if (!this.synth) return;
    const loadVoices = () => {
      const voices = this.synth.getVoices();
      const ruVoices = voices.filter(v => v.lang.startsWith('ru'));
      const preferred = ruVoices.find(v => 
        v.name.includes('Google') || 
        v.name.includes('Irina') || 
        v.name.includes('Svetlana')
      );
      this.currentVoice = preferred || ruVoices[0] || null;
    };
    loadVoices();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = loadVoices;
    }
  }

  setRate(rate) {
    this.currentRate = Math.min(1.30, Math.max(0.60, Math.round((parseFloat(rate) || 1.0) * 100) / 100));
    return this.currentRate;
  }

  stepRate(delta) {
    const newRate = Math.min(1.30, Math.max(0.60, Math.round((this.currentRate + delta) * 100) / 100));
    this.currentRate = newRate;
    return this.currentRate;
  }

  stopAudioOnly() {
    this.clearSync();
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    }
    if (this.synth) {
      this.synth.cancel();
    }
    this.isPlaying = false;
    if (this.onWordHighlightCallback) {
      this.onWordHighlightCallback(-1);
    }
  }

  stop() {
    this.playToken = (this.playToken || 0) + 1;
    this.isLadderPlaying = false;
    this.stopAudioOnly();
    if (this.onEndCallback) {
      const cb = this.onEndCallback;
      this.onEndCallback = null;
      cb();
    }
  }

  clearSync() {
    this.clearTimeouts();
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    this.lastHighlightedIndex = -1;
  }

  clearTimeouts() {
    this.activeTimeouts.forEach(t => clearTimeout(t));
    this.activeTimeouts = [];
  }

  /**
   * Internal sentence speaker with token guard
   */
  async speakSentenceInternal(text, tokens = [], onWordHighlight = null, onEnd = null, targetToken = null) {
    this.stopAudioOnly();
    if (!text) {
      if (onEnd) onEnd();
      return;
    }

    const myPlayToken = targetToken || ++this.playToken;
    this.onWordHighlightCallback = onWordHighlight;
    this.onEndCallback = onEnd;

    // Sanitize any slashes in sentence text to prevent TTS voicing "slash / drob"
    const cleanSentenceText = text.replace(/\s*\/\s*/g, ', ').trim();

    // Try Neural TTS via /api/tts
    if (this.useNeural) {
      try {
        const res = await fetch(`/api/tts?text=${encodeURIComponent(cleanSentenceText)}&rate=${this.currentRate}`);
        if (this.playToken !== myPlayToken) return;
        if (res.ok) {
          const data = await res.json();
          if (this.playToken !== myPlayToken) return;
          if (data.audio_url) {
            this.playNeuralAudio(data.audio_url, cleanSentenceText, tokens, data.word_boundaries || []);
            return;
          }
        }
      } catch (err) {
        console.warn('Neural TTS failed, falling back to Web Speech API:', err);
      }
    }

    if (this.playToken !== myPlayToken) return;

    // Fallback: Web Speech API
    this.speakFallback(cleanSentenceText, tokens);
  }

  /**
   * Speak full sentence with Neural TTS and synchronized karaoke highlighting
   */
  async speakSentence(text, tokens = [], onWordHighlight = null, onEnd = null) {
    this.stop();
    return this.speakSentenceInternal(text, tokens, onWordHighlight, onEnd);
  }

  /**
   * Ladder Listening Sequence (3-stage speed ladder: 0.75x -> 0.90x -> 1.00x)
   * Trains listening by starting slow to catch consonant clusters & vowel reduction,
   * then ramping up to conversational tempo.
   */
  async playLadderSequence(text, tokens = [], onStepChange = null, onWordHighlight = null, onComplete = null) {
    this.stop();
    if (!text) {
      if (onComplete) onComplete();
      return;
    }

    const ladderSteps = [
      { step: 1, rate: 0.75, title: 'Step 1/3 (0.75x)', desc: '音素・弱化・語境界の把握' },
      { step: 2, rate: 0.90, title: 'Step 2/3 (0.90x)', desc: '文のリズム・イントネーション' },
      { step: 3, rate: 1.00, title: 'Step 3/3 (1.00x)', desc: 'ネイティブ自然速度・直読直解' }
    ];

    const myLadderToken = ++this.playToken;
    this.isLadderPlaying = true;

    // Warm up / prefetch audio for all 3 ladder steps in background for instant playback
    if (this.useNeural) {
      ladderSteps.forEach(st => {
        fetch(`/api/tts?text=${encodeURIComponent(text)}&rate=${st.rate}`).catch(() => {});
      });
    }

    for (let i = 0; i < ladderSteps.length; i++) {
      if (this.playToken !== myLadderToken) {
        this.isLadderPlaying = false;
        return;
      }

      const st = ladderSteps[i];
      this.currentRate = st.rate;
      if (onStepChange) {
        onStepChange(st.step, ladderSteps.length, st.rate, st.title, st.desc);
      }

      // Play this step synchronously
      await new Promise((resolve) => {
        let stepDone = false;
        const finishStep = () => {
          if (!stepDone) {
            stepDone = true;
            resolve();
          }
        };

        this.speakSentenceInternal(
          text,
          tokens,
          onWordHighlight,
          () => finishStep(),
          myLadderToken
        );
      });

      if (this.playToken !== myLadderToken) {
        this.isLadderPlaying = false;
        return;
      }

      // Snappy interval pause (400ms) between steps
      if (i < ladderSteps.length - 1) {
        await new Promise((resolve) => {
          const pauseMs = (typeof this.ladderStepPauseMs === 'number') ? this.ladderStepPauseMs : 400;
          const timer = setTimeout(resolve, pauseMs);
          this.activeTimeouts.push(timer);
        });
      }
    }

    this.isLadderPlaying = false;
    if (this.playToken === myLadderToken && onComplete) {
      onComplete();
    }
  }

  speakSentenceAsync(text) {
    return new Promise((resolve) => {
      let done = false;
      let safetyTimer = null;
      const finish = () => {
        if (!done) {
          done = true;
          if (safetyTimer) {
            clearTimeout(safetyTimer);
            safetyTimer = null;
          }
          resolve();
        }
      };

      // Generous safety timeout (8000ms) only to catch network hang or headless issues
      safetyTimer = setTimeout(() => {
        console.warn('speakSentenceAsync safety timeout reached for:', text);
        finish();
      }, 8000);

      this.speakSentence(text, [], null, finish);
    });
  }

  playNeuralAudio(audioUrl, text, tokens = [], wordBoundaries = []) {
    this.clearSync();
    this.audioElement.src = audioUrl;
    // CRITICAL: Edge-TTS renders audio at this.currentRate already; HTML5 audio plays at 1.0x to avoid double slowdown!
    this.audioElement.playbackRate = 1.0;
    this.isPlaying = true;

    this.audioElement.play().then(() => {
      // Schedule word highlighting along the audio duration
      if (tokens && tokens.length > 0 && this.onWordHighlightCallback) {
        if (wordBoundaries && wordBoundaries.length > 0) {
          this.startPhoneticKaraoke(tokens, wordBoundaries);
        } else {
          this.scheduleKaraokeHighlights(tokens);
        }
      }
    }).catch(err => {
      console.warn('Audio play failed:', err);
      this.speakFallback(text, tokens);
    });
  }

  /**
   * Align token list to Edge-TTS microsecond WordBoundary items
   */
  alignTokensToBoundaries(tokens, wordBoundaries) {
    const cleanTokens = tokens.map((t, idx) => {
      const w = typeof t === 'string' ? t : (t.word || '');
      return {
        index: idx,
        clean: w.replace(/[.,!?;:()«»"—]/g, '').trim().toLowerCase()
      };
    }).filter(t => t.clean.length > 0);

    // Direct 1-to-1 match when token count equals word boundary count
    if (cleanTokens.length === wordBoundaries.length) {
      return cleanTokens.map((ct, i) => ({
        tokenIndex: ct.index,
        start_ms: wordBoundaries[i].start_ms,
        end_ms: wordBoundaries[i].end_ms
      }));
    }

    // Resilient sequential alignment for punctuation/hyphen differences
    const mapped = [];
    let bIdx = 0;
    for (let tIdx = 0; tIdx < cleanTokens.length && bIdx < wordBoundaries.length; tIdx++) {
      const ct = cleanTokens[tIdx];
      const wb = wordBoundaries[bIdx];
      const wbClean = (wb.text || '').replace(/[.,!?;:()«»"—]/g, '').trim().toLowerCase();

      if (wbClean === ct.clean || ct.clean.includes(wbClean) || wbClean.includes(ct.clean)) {
        mapped.push({
          tokenIndex: ct.index,
          start_ms: wb.start_ms,
          end_ms: wb.end_ms
        });
        bIdx++;
      } else {
        let found = false;
        for (let lookahead = 1; lookahead <= 2 && bIdx + lookahead < wordBoundaries.length; lookahead++) {
          const nextWbClean = (wordBoundaries[bIdx + lookahead].text || '').replace(/[.,!?;:()«»"—]/g, '').trim().toLowerCase();
          if (nextWbClean === ct.clean) {
            bIdx += lookahead;
            mapped.push({
              tokenIndex: ct.index,
              start_ms: wordBoundaries[bIdx].start_ms,
              end_ms: wordBoundaries[bIdx].end_ms
            });
            bIdx++;
            found = true;
            break;
          }
        }
        if (!found) {
          bIdx++;
        }
      }
    }
    return mapped;
  }

  /**
   * 60 FPS Audio Clock Synchronized Karaoke with 35ms perceptual lead-in
   */
  startPhoneticKaraoke(tokens, wordBoundaries) {
    this.clearSync();
    const mapped = this.alignTokensToBoundaries(tokens, wordBoundaries);
    if (!mapped || mapped.length === 0) {
      this.scheduleKaraokeHighlights(tokens);
      return;
    }

    // Lead-in compensation (35ms): visually highlights slightly ahead of auditory onset
    // matching human audiovisual perception latency
    const LEAD_IN_MS = 35;
    this.lastHighlightedIndex = -1;

    const tick = () => {
      if (!this.isPlaying || !this.audioElement) return;

      const currentMs = this.audioElement.currentTime * 1000;
      let activeTokenIdx = -1;

      for (let i = 0; i < mapped.length; i++) {
        const curr = mapped[i];
        const next = mapped[i + 1];
        const startTime = Math.max(0, curr.start_ms - LEAD_IN_MS);

        let endTime;
        if (next) {
          if (next.start_ms - curr.end_ms > 280) {
            // Significant pause between phrases: release highlight cleanly
            endTime = curr.end_ms + 60;
          } else {
            // Natural speech flow: keep highlighted until next word triggers
            endTime = Math.max(curr.end_ms, next.start_ms - LEAD_IN_MS);
          }
        } else {
          // Last word
          endTime = curr.end_ms + 100;
        }

        if (currentMs >= startTime && currentMs < endTime) {
          activeTokenIdx = curr.tokenIndex;
          break;
        }
      }

      if (activeTokenIdx !== this.lastHighlightedIndex) {
        this.lastHighlightedIndex = activeTokenIdx;
        if (this.onWordHighlightCallback) {
          this.onWordHighlightCallback(activeTokenIdx);
        }
      }

      if (this.isPlaying) {
        this.animFrameId = requestAnimationFrame(tick);
      }
    };

    this.animFrameId = requestAnimationFrame(tick);
  }

  scheduleKaraokeHighlights(tokens) {
    this.clearTimeouts();
    // Estimate relative weights based on word character length
    const totalChars = tokens.reduce((sum, t) => sum + (t.word || '').length, 0) || 1;
    
    // Once metadata is loaded, calculate timing
    const schedule = () => {
      // NOTE: audioElement.duration is already scaled; do NOT divide by currentRate
      const durationMs = (this.audioElement.duration || (totalChars * 0.18)) * 1000;
      let accumulatedTime = 0;

      tokens.forEach((t, idx) => {
        const wordLen = (t.word || '').length || 3;
        const wordShare = wordLen / totalChars;
        const wordDuration = Math.max(80, durationMs * wordShare);

        const timerId = setTimeout(() => {
          if (this.isPlaying && this.onWordHighlightCallback) {
            this.onWordHighlightCallback(idx);
          }
        }, accumulatedTime);

        this.activeTimeouts.push(timerId);
        accumulatedTime += wordDuration;
      });
    };

    if (this.audioElement.readyState >= 1) {
      schedule();
    } else {
      this.audioElement.addEventListener('loadedmetadata', schedule, { once: true });
    }
  }

  /**
   * Parse Russian word string into pronounceable units.
   * Handles slash-separated pairs (e.g., aspectual pairs: выступать/выступить),
   * reconstructs prefix shorthands (e.g., писать/на- -> писать, написать),
   * and strips grammatical government notations (e.g., (+a), (i/p), (к +d)).
   */
  parseWordUnits(rawWord) {
    if (!rawWord) return [];
    // 1. Remove parenthesized grammatical/government notes e.g. (+a), (i/p), (к +d)
    let cleaned = String(rawWord).replace(/\s*\([^)]*\)/g, '').replace(/[«»]/g, '').trim();
    if (!cleaned) return [];

    // Remove stray punctuation except slash and hyphen
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
        // Expand prefix shorthand e.g. "на-" + "писать" -> "написать"
        const prefix = part.slice(0, -1);
        units.push(prefix + baseWord);
      } else {
        units.push(part.replace(/-+$/, '').trim());
      }
    }
    return units.filter(Boolean);
  }

  /**
   * Speak Russian word(s) with clean pronunciation.
   * If the word is a slash-separated pair (aspect pair or alternative),
   * each word is spoken cleanly with a 1.0-second silence gap between them.
   */
  async speakWord(word, onEnd = null) {
    this.stop();
    if (!word) {
      if (onEnd) onEnd();
      return;
    }

    const units = this.parseWordUnits(word);
    if (units.length === 0) {
      if (onEnd) onEnd();
      return;
    }

    const myPlayToken = this.playToken;

    if (units.length === 1) {
      return this.speakSingleWord(units[0], myPlayToken, onEnd);
    }

    // Multi-part word pair (e.g. выступать/выступить):
    // Speak part 1 -> 1.0s clean pause -> Speak part 2 -> ...
    let idx = 0;
    const playNext = () => {
      if (this.playToken !== myPlayToken) return;
      if (idx >= units.length) {
        if (onEnd) onEnd();
        return;
      }

      const unitText = units[idx++];
      this.speakSingleWord(unitText, myPlayToken, () => {
        if (this.playToken !== myPlayToken) return;
        if (idx < units.length) {
          // Exactly 1.0 second pause between words
          const t = setTimeout(() => {
            if (this.playToken === myPlayToken) {
              playNext();
            }
          }, 1000);
          this.activeTimeouts.push(t);
        } else {
          if (onEnd) onEnd();
        }
      });
    };

    playNext();
  }

  async speakSingleWord(cleanWord, myPlayToken, onDone = null) {
    if (!cleanWord || this.playToken !== myPlayToken) {
      if (onDone) onDone();
      return;
    }

    const finish = () => {
      if (onDone) onDone();
    };

    if (this.useNeural) {
      try {
        const res = await fetch(`/api/tts?text=${encodeURIComponent(cleanWord)}&rate=1.0`);
        if (this.playToken !== myPlayToken) return;
        if (res.ok) {
          const data = await res.json();
          if (this.playToken !== myPlayToken) return;
          if (data.audio_url) {
            this.clearSync();
            this.audioElement.src = data.audio_url;
            this.audioElement.playbackRate = 0.95; // clear pronunciation
            this.isPlaying = true;
            this.onEndCallback = finish;
            this.audioElement.play().catch(e => {
              console.warn('Audio play failed:', e);
              finish();
            });
            return;
          }
        }
      } catch (e) {
        // Fallback below
      }
    }

    if (this.playToken !== myPlayToken) return;
    if (!this.synth) {
      finish();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(cleanWord);
    utterance.lang = 'ru-RU';
    if (this.currentVoice) utterance.voice = this.currentVoice;
    utterance.rate = 0.9;
    utterance.onend = finish;
    utterance.onerror = finish;
    this.synth.speak(utterance);
  }

  speakFallback(text, tokens) {
    if (!this.synth) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ru-RU';
    if (this.currentVoice) utterance.voice = this.currentVoice;
    utterance.rate = this.currentRate;
    utterance.pitch = 1.05;

    const tokenRanges = [];
    let searchIndex = 0;
    tokens.forEach((tok, idx) => {
      const word = (typeof tok === 'string' ? tok : tok.word || '').trim();
      const pos = text.indexOf(word, searchIndex);
      if (pos !== -1) {
        tokenRanges.push({ start: pos, end: pos + word.length, index: idx });
        searchIndex = pos + word.length;
      }
    });

    utterance.onboundary = (event) => {
      if (event.name === 'word') {
        const charIndex = event.charIndex;
        const match = tokenRanges.find(r => charIndex >= r.start && charIndex <= r.end + 1);
        if (match && this.onWordHighlightCallback) {
          this.onWordHighlightCallback(match.index);
        }
      }
    };

    utterance.onend = () => {
      this.isPlaying = false;
      if (this.onWordHighlightCallback) this.onWordHighlightCallback(-1);
      if (this.onEndCallback) {
        const cb = this.onEndCallback;
        this.onEndCallback = null;
        cb();
      }
    };

    utterance.onerror = () => {
      this.isPlaying = false;
      if (this.onEndCallback) {
        const cb = this.onEndCallback;
        this.onEndCallback = null;
        cb();
      }
    };

    this.isPlaying = true;
    this.synth.speak(utterance);
  }
}

window.TTSPlayer = new TTSKaraokePlayer();
