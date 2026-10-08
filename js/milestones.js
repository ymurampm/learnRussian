/**
 * Milestones & Scheduling Engine (2027 Russian Proficiency Test Grade 2 Roadmap)
 * Manages phased timeline, tag reflex readiness, and Tanya's weekly proposition coaching.
 */

class MilestonesEngine {
  constructor() {
    this.data = null;
    this.selectedPhaseId = null;
    this.modal = document.getElementById('milestonesModal');
    this.body = document.getElementById('milestonesBody');
    this.headerBadge = document.getElementById('milestoneHeaderBadge');
    this.closeBtn = document.getElementById('milestonesClose');

    if (this.closeBtn && this.modal) {
      this.closeBtn.onclick = () => this.close();
    }
  }

  async open() {
    if (!this.modal) return;
    this.modal.classList.add('open');
    await this.loadAndRender();
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('open');
    }
  }

  async loadAndRender() {
    if (!this.body) return;
    this.body.innerHTML = `
      <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-muted);">
        <span>ロードマップ指標と学習ログを照合中...</span>
      </div>
    `;

    try {
      const res = await fetch('/api/milestones');
      if (!res.ok) throw new Error('Failed to fetch milestones');
      this.data = await res.json();
      if (!this.selectedPhaseId && this.data.active_phase) {
        this.selectedPhaseId = this.data.active_phase.phase_id;
      }
      this.render();
    } catch (err) {
      this.body.innerHTML = `
        <div style="color:var(--crimson-soft); padding:20px; text-align:center;">
          ロードマップデータの取得に失敗しました: ${err.message}
        </div>
      `;
    }
  }

  async runAudit() {
    const btn = document.getElementById('btnRunMilestoneAudit');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '診断中...';
    }
    try {
      const res = await fetch('/api/milestones/audit', { method: 'POST' });
      if (!res.ok) throw new Error('Audit failed');
      this.data = await res.json();
      this.render();
    } catch (err) {
      alert('ペース診断に失敗しました: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '🔄 ペース再診断';
      }
    }
  }

  render() {
    if (!this.data || !this.body) return;

    const { target_exam, active_phase, pace_status, pace_label, coaching_message, recommended_tags, phases, tag_readiness } = this.data;

    if (this.headerBadge && active_phase) {
      this.headerBadge.textContent = `Phase ${active_phase.phase_num} (${active_phase.name}) - ${pace_label}`;
    }

    const selectedPhase = phases.find(p => p.phase_id === this.selectedPhaseId) || active_phase || phases[0];

    // Pace badge color
    let paceBadgeBg = 'rgba(16,185,129,0.15)';
    let paceBadgeColor = 'var(--emerald-light)';
    let paceBadgeBorder = 'rgba(16,185,129,0.3)';
    if (pace_status === 'needs_nudge') {
      paceBadgeBg = 'rgba(245,158,11,0.15)';
      paceBadgeColor = 'var(--gold-light)';
      paceBadgeBorder = 'rgba(245,158,11,0.3)';
    }

    this.body.innerHTML = `
      <div class="milestones-container">
        <!-- Scope Clarification Header Banner -->
        <div class="milestone-scope-banner">
          <div class="scope-box app-scope">
            <div class="scope-icon">⚡</div>
            <div class="scope-info">
              <div class="scope-title">${target_exam.scope_app?.title || '本アプリの担当領域'}</div>
              <div class="scope-desc">${target_exam.scope_app?.description || '文法・語彙・聴取の反射的定着（タイピングなし・瞬時判断）'}</div>
            </div>
            <span class="scope-badge">本アプリ</span>
          </div>

          <div class="scope-box italki-scope">
            <div class="scope-icon">🗣️</div>
            <div class="scope-info">
              <div class="scope-title">${target_exam.scope_italki?.title || 'italkiの担当領域'}</div>
              <div class="scope-desc">${target_exam.scope_italki?.description || '和文露訳・口頭作文（実践的文構築・発話演習）'}</div>
            </div>
            <span class="scope-badge italki">italki</span>
          </div>
        </div>

        <!-- Tanya's Weekly Proposition Coaching Card -->
        <div class="milestone-tanya-coaching">
          <div class="tanya-coach-avatar-box">
            <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="tanya-coach-avatar">
          </div>
          <div class="tanya-coach-content">
            <div class="tanya-coach-header">
              <span class="tanya-coach-name">🎹 ターニャ先生の週次ペース診断・提案</span>
              <span class="tanya-pace-badge" style="background:${paceBadgeBg}; color:${paceBadgeColor}; border:1px solid ${paceBadgeBorder};">
                ${pace_label}
              </span>
              <button class="audit-refresh-btn" id="btnRunMilestoneAudit" title="最新の学習ログで再評価">
                🔄 ペース再診断
              </button>
            </div>
            <div class="tanya-coach-bubble">
              ${coaching_message}
            </div>
            ${recommended_tags && recommended_tags.length > 0 ? `
              <div class="tanya-recommend-row">
                <span class="recommend-label">💡 次回おすすめの重点文法:</span>
                ${recommended_tags.map(t => `<span class="recommend-tag-pill">${t.name}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Phased Roadmap Timeline (5 Phases) -->
        <div class="milestone-timeline-section">
          <div class="timeline-heading">
            <h4>📅 2027年10月合格までの期間別マイルストーン (全5フェーズ)</h4>
            <span class="timeline-subhint">※ フェーズをクリックすると基準と該当文法タグを表示します</span>
          </div>
          <div class="milestone-timeline-grid">
            ${phases.map(p => this.renderPhaseTimelineCard(p, p.phase_id === this.selectedPhaseId)).join('')}
          </div>
        </div>

        <!-- Selected Phase Detail & Tag Reflex Readiness Matrix -->
        <div class="milestone-phase-detail-card">
          <div class="phase-detail-header">
            <div>
              <span class="phase-detail-num">Phase ${selectedPhase.phase_num}</span>
              <span class="phase-detail-title">${selectedPhase.name}</span>
              <span class="phase-detail-dates">（${selectedPhase.start_date.replace(/-/g, '/')} 〜 ${selectedPhase.end_date.replace(/-/g, '/')}）</span>
            </div>
            <div class="phase-detail-criteria">
              🎯 <strong>到達基準:</strong> ${selectedPhase.criteria_desc || ''}
            </div>
          </div>

          <div class="tag-readiness-grid">
            ${this.renderTagReadinessGrid(tag_readiness, selectedPhase)}
          </div>
        </div>
      </div>
    `;

    // Attach event listeners
    const auditBtn = document.getElementById('btnRunMilestoneAudit');
    if (auditBtn) {
      auditBtn.onclick = () => this.runAudit();
    }

    this.body.querySelectorAll('.timeline-phase-card').forEach(card => {
      card.onclick = () => {
        const pid = card.dataset.phaseId;
        if (pid) {
          this.selectedPhaseId = pid;
          this.render();
        }
      };
    });

    this.body.querySelectorAll('.tag-readiness-card').forEach(card => {
      card.onclick = () => {
        const tagKey = card.dataset.tagKey;
        if (tagKey && window.Handbook) {
          this.close();
          window.Handbook.openTag(tagKey);
        }
      };
    });
  }

  renderPhaseTimelineCard(phase, isSelected) {
    const isActive = phase.is_active;
    let cardClass = 'timeline-phase-card';
    if (isSelected) cardClass += ' selected';
    if (isActive) cardClass += ' active-phase';

    let statusLabel = '予定';
    let statusColor = 'var(--text-muted)';
    if (isActive) {
      statusLabel = '進行中';
      statusColor = 'var(--gold-light)';
    } else if (phase.progress_pct >= 100) {
      statusLabel = '達成';
      statusColor = 'var(--emerald-light)';
    }

    return `
      <div class="${cardClass}" data-phase-id="${phase.phase_id}">
        <div class="phase-card-top">
          <span class="phase-pill">P${phase.phase_num}</span>
          <span class="phase-status-badge" style="color:${statusColor};">${statusLabel}</span>
        </div>
        <div class="phase-card-name">${phase.name}</div>
        <div class="phase-card-dates">${phase.start_date.slice(2, 7).replace('-', '/')}〜${phase.end_date.slice(2, 7).replace('-', '/')}</div>
        <div class="phase-progress-bar-wrap">
          <div class="phase-progress-bar-fill" style="width:${Math.min(100, phase.progress_pct)}%;"></div>
        </div>
        <div class="phase-card-pct">${phase.progress_pct}% 達成</div>
      </div>
    `;
  }

  renderTagReadinessGrid(tagReadiness, selectedPhase) {
    if (selectedPhase.phase_id === 'phase5') {
      return `
        <div style="padding:26px; text-align:center; color:var(--text-secondary); line-height:1.7;">
          <div style="font-size:1.8rem; margin-bottom:8px;">🎓</div>
          <strong style="color:var(--gold-light); font-size:1rem;">ロシア語能力検定2級 受験本番</strong><br>
          本アプリで条件反射レベルに定着させた文法・語彙・リスニング力と、<br>
          italkiで積み上げた和文露訳・口頭作文の表現力を結実させ、合格を勝ち取ります！
        </div>
      `;
    }

    if (!tagReadiness || tagReadiness.length === 0) {
      return `
        <div style="padding:20px; text-align:center; color:var(--text-muted);">
          このフェーズの文法タグデータは準備中です。
        </div>
      `;
    }

    return tagReadiness.map(t => {
      const isPass = t.is_passed;
      let statusBadge = '';
      let statusColor = '#94a3b8';

      if (t.status === 'reflex') {
        statusBadge = '⚡ 条件反射';
        statusColor = 'var(--emerald-light)';
      } else if (t.status === 'stable') {
        statusBadge = '⭕ 安定';
        statusColor = '#38bdf8';
      } else if (t.status === 'rusty') {
        statusBadge = '⏳ 要復習';
        statusColor = 'var(--crimson-soft)';
      } else if (t.status === 'developing') {
        statusBadge = '🛠️ 練習中';
        statusColor = 'var(--gold-light)';
      } else {
        statusBadge = '⚪ 未着手';
        statusColor = '#64748b';
      }

      return `
        <div class="tag-readiness-card ${isPass ? 'passed' : ''}" data-tag-key="${t.tag}" style="cursor:pointer;" title="クリックして文法書（教科書）の該当項目を開く">
          <div class="tag-readiness-top">
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="tag-color-dot" style="background:${t.color || '#64748b'};"></span>
              <span class="tag-name-label">${t.name}</span>
              <span style="font-size:0.65rem; color:var(--gold-light); background:rgba(212,175,55,0.12); padding:1px 4px; border-radius:3px;">📖</span>
            </div>
            <span class="tag-status-pill" style="color:${statusColor}; border-color:${statusColor};">
              ${statusBadge}
            </span>
          </div>

          <div class="tag-readiness-metrics">
            <div class="metric-item">
              <span class="metric-label">接触</span>
              <span class="metric-val">${t.seen} 回</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">正答率</span>
              <span class="metric-val">${t.accuracy_pct}%</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">反応速度</span>
              <span class="metric-val">${t.avg_rt_ms ? (t.avg_rt_ms / 1000).toFixed(1) + 's' : '-'}</span>
            </div>
            <div class="metric-item check-item">
              ${isPass ? '<span class="pass-check" title="到達基準達成">✓ 基準達成</span>' : '<span class="unreached-badge">目標未達</span>'}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }
}

// Global instance
window.milestonesEngine = new MilestonesEngine();
