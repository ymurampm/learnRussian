/**
 * Tanya Russian Trainer - Live Grammar Mutator Module
 * Allows in-place grammatical transformation of sentences (Case, Tense, Aspect)
 * with instant visual diff and audio feedback.
 */

class GrammarMutator {
  constructor() {
    this.container = null;
    this.currentMutations = [];
    this.activeMutationIndex = 0;
    this.onMutationChange = null;
  }

  init(containerElement, mutations = [], defaultSentence = null, onMutationChange = null) {
    this.container = containerElement;
    this.onMutationChange = onMutationChange;
    this.activeMutationIndex = 0;

    // Prepend original sentence as option 0
    this.currentMutations = [
      {
        id: "orig",
        label: "基本形 (Original)",
        ru: defaultSentence ? defaultSentence.ru : "",
        ja: defaultSentence ? defaultSentence.ja : "",
        diff_explain: "本日のコア例文です。"
      },
      ...mutations
    ];

    this.render();
  }

  render() {
    if (!this.container) return;

    if (this.currentMutations.length <= 1) {
      this.container.innerHTML = '';
      this.container.style.display = 'none';
      return;
    }

    this.container.style.display = 'block';
    const activeMut = this.currentMutations[this.activeMutationIndex];

    this.container.innerHTML = `
      <div class="phase2-mutator-row">
        <span class="phase2-mutator-label">⚡ 文法変換:</span>
        <div class="phase2-mutator-pills">
          ${this.currentMutations.map((m, idx) => `
            <button class="phase2-mut-pill ${idx === this.activeMutationIndex ? 'active' : ''}" data-index="${idx}">
              ${m.label}
            </button>
          `).join('')}
        </div>
        <div class="phase2-diff-text">💡 ${activeMut.diff_explain} <span style="font-size:0.75rem; color:var(--text-muted); margin-left:4px;">(Tabで切替)</span></div>
      </div>
    `;

    // Attach click listeners to pills
    const pillButtons = this.container.querySelectorAll('.phase2-mut-pill');
    pillButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.index, 10);
        this.selectMutation(idx);
      });
    });
  }

  selectMutation(index) {
    if (index < 0 || index >= this.currentMutations.length) return;
    this.activeMutationIndex = index;
    const mut = this.currentMutations[index];

    this.render();

    // Notify parent
    if (this.onMutationChange) {
      this.onMutationChange(mut);
    }

    // Play TTS audio of the mutated sentence
    if (window.TTSPlayer && mut.ru) {
      window.TTSPlayer.speakSentence(mut.ru);
    }

    // Log behavior
    if (window.API) {
      window.API.logBehavior({ grammar_mutations_count: 1 });
    }
  }

  cycleNext() {
    const nextIdx = (this.activeMutationIndex + 1) % this.currentMutations.length;
    this.selectMutation(nextIdx);
  }

  highlightDiff(text) {
    // Return text wrapped with safe highlighting
    return text;
  }
}

window.GrammarMutator = new GrammarMutator();
