/**
 * Tanya Russian Trainer - Distance & Intimacy Meter Module
 * Tracks continuous day streaks, mentor affection level,
 * unlocks memoirs, and manages gentle absence recovery without penalties.
 */

class DistanceMeterManager {
  constructor() {
    this.intimacyData = { level: 1, exp: 0, max_exp: 50, title: "音楽院サロンの新客" };
    this.currentStreak = 1;
    this.absenceNotice = null;
    this.unlockedMemoirs = [];
  }

  updateState(stateData) {
    if (!stateData) return;
    const profile = stateData.user_profile || {};
    this.intimacyData = profile.intimacy || this.intimacyData;
    this.currentStreak = profile.current_streak || 1;
    this.absenceNotice = stateData.absence_notice || null;
    this.unlockedMemoirs = stateData.unlocked_memoirs || [];

    this.renderHeaderPill();
    this.checkAbsenceBanner();
  }

  renderHeaderPill() {
    const capsule = document.getElementById('tanyaCapsule');
    if (!capsule) return;

    capsule.innerHTML = `
      <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="tanya-avatar-small" id="headerTanyaAvatar">
      <div class="tanya-capsule-info">
        <div class="tanya-level-badge">Lv.${this.intimacyData.level} ${this.intimacyData.title}</div>
        <div class="tanya-streak">🔥 継続 ${this.currentStreak}日目</div>
      </div>
    `;
  }

  checkAbsenceBanner() {
    const bannerContainer = document.getElementById('absenceBannerContainer');
    if (!bannerContainer) return;

    if (!this.absenceNotice) {
      bannerContainer.innerHTML = '';
      bannerContainer.style.display = 'none';
      return;
    }

    bannerContainer.style.display = 'block';
    bannerContainer.innerHTML = `
      <div class="absence-banner">
        <img src="assets/images/tanya_encouraging.jpg" alt="ターニャ先生">
        <div class="absence-banner-text">
          <div class="absence-banner-title">🌸 ターニャ先生より「おかえりなさい！」</div>
          <div class="absence-banner-desc">${this.absenceNotice.greeting}</div>
        </div>
        <button class="absence-close-btn" id="absenceCloseBtn">了解 (Esc)</button>
      </div>
    `;

    const closeBtn = bannerContainer.querySelector('#absenceCloseBtn');
    if (closeBtn) {
      closeBtn.onclick = () => {
        bannerContainer.style.display = 'none';
      };
    }
  }

  addExp(gainPoints) {
    let exp = this.intimacyData.exp + gainPoints;
    let lvl = this.intimacyData.level;
    let max = this.intimacyData.max_exp;

    if (exp >= max) {
      lvl += 1;
      exp = exp - max;
      max = Math.round(max * 1.5);
    }

    this.intimacyData.level = lvl;
    this.intimacyData.exp = exp;
    this.intimacyData.max_exp = max;
    this.renderHeaderPill();
  }
}

window.DistanceMeter = new DistanceMeterManager();
