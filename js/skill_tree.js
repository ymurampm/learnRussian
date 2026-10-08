/**
 * Tanya Russian Trainer - Skill Tree & Weakness Map Module
 * Visualizes grammar categories and semantic clusters with heat-mapped status badges
 * based on reaction speed and stability index.
 */

class SkillTreeMap {
  constructor() {
    this.modal = null;
    this.container = null;
    this.taxonomyData = null;
    this.tagStats = {};
  }

  init(modalElement, containerElement) {
    this.modal = modalElement;
    this.container = containerElement;
  }

  async open(tagStats = {}) {
    this.tagStats = tagStats;
    if (!this.taxonomyData && window.API) {
      this.taxonomyData = await window.API.getTaxonomy();
    }
    this.render();
    if (this.modal) {
      this.modal.classList.add('open');
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('open');
    }
  }

  render() {
    if (!this.container || !this.taxonomyData) return;

    const categories = this.taxonomyData.categories || {};
    let html = `
      <div style="background:rgba(212,175,55,0.08); border:1px solid rgba(212,175,55,0.3); border-radius:6px; padding:10px 14px; margin-bottom:16px; font-size:0.83rem; color:var(--text-secondary); line-height:1.5;">
        💡 <strong>スキルツリーの使い方:</strong> あなたの文法タグごとの習熟度・定着状況マップです。各タグをクリックすると<strong>該当の文法ハンドブック解説へジャンプ</strong>できます。<br>
        <span style="color:var(--gold-light);">※文法ハンドブック（教科書）は、ホーム画面やヘッダーの「📖 文法書」ボタン、またはキーボードの [G] キーからいつでも直接開くこともできます！</span>
      </div>
    `;

    for (const [catKey, cat] of Object.entries(categories)) {
      html += `
        <div class="tree-category-group">
          <div class="tree-category-title">
            <span>📚 ${cat.name}</span>
            <span style="font-size:0.75rem; color:var(--text-muted); font-weight:normal;">- ${cat.description}</span>
          </div>
          <div class="tree-tags-grid">
            ${Object.entries(cat.tags || {}).map(([tagKey, tagInfo]) => {
              const stat = this.tagStats[tagKey] || { seen: 0, correct: 0, avg_rt_ms: 0, status: 'developing' };
              const statusClass = stat.status || 'developing';
              const statusLabel = {
                'reflex': '⚡ 条件反射',
                'stable': '🟢 安定',
                'developing': '🟡 習得中',
                'rusty': '🟠 要復習 (遅め)'
              }[statusClass] || '🟡 未着手';

              const rtText = stat.avg_rt_ms > 0 ? `${(stat.avg_rt_ms / 1000).toFixed(1)}秒` : '-';

              return `
                <div class="tree-tag-card" data-tag-key="${tagKey}" style="border-left-color: ${tagInfo.color || 'var(--border-color)'}; cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease;" title="クリックして文法解説（教科書）を開く">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div class="tree-tag-name">${tagInfo.name}</div>
                    <span style="font-size:0.68rem; color:var(--gold-light); background:rgba(212,175,55,0.12); padding:1px 6px; border-radius:4px;">📖 解説</span>
                  </div>
                  <div style="font-size:0.76rem; color:var(--text-secondary);">${tagInfo.core_usage}</div>
                  <div class="tree-tag-meta" style="margin-top:6px;">
                    <span class="status-badge ${statusClass}">${statusLabel}</span>
                    <span>平均反応: ${rtText}</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    this.container.innerHTML = html;

    // Attach click listeners to open Handbook
    this.container.querySelectorAll('.tree-tag-card').forEach(card => {
      card.onclick = () => {
        const tagKey = card.dataset.tagKey;
        if (tagKey && window.Handbook) {
          this.close();
          window.Handbook.openTag(tagKey);
        }
      };
    });
  }
}

window.SkillTreeMap = new SkillTreeMap();
