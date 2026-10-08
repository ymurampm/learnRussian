/**
 * Tanya Russian Trainer - Main App Controller
 * Coordinates Views, Modals, State, and Global Keybindings
 */

const App = {
  state: null,
  activeView: 'dashboard', // 'dashboard' | 'player'
  studyMode: 'graded', // 'graded' | 'non_graded'
  selectedDay: null,

  async init() {
    this.bindGlobalKeys();
    this.setupModals();
    this.setupHeaderControls();
    this.setupRealtimeSync();
    await this.loadState();
  },

  setupRealtimeSync() {
    // 1. Re-sync when user returns to or focuses the tab
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        this.checkDateSync();
      }
    });
    window.addEventListener('focus', () => {
      this.checkDateSync();
    });

    // 2. Periodic sync check every 60 seconds (for 01:00 AM cutoff transitions)
    setInterval(() => {
      this.checkDateSync();
    }, 60000);
  },

  async checkDateSync() {
    try {
      const freshState = await window.API.getState();
      if (!freshState) return;

      const dateChanged = this.state && this.state.effective_date !== freshState.effective_date;
      const dayChanged = this.state && this.state.current_study_day !== freshState.current_study_day;

      if (dateChanged || dayChanged) {
        console.log('[Realtime Sync] Date or Day transition detected! Refreshing dashboard...', {
          oldDate: this.state?.effective_date,
          newDate: freshState.effective_date,
          oldDay: this.state?.current_study_day,
          newDay: freshState.current_study_day
        });
        await this.loadState();
      }
    } catch (e) {
      console.warn('Realtime sync check failed:', e);
    }
  },

  async loadState(day = null) {
    this.state = await window.API.getState(day);
    if (!this.state) {
      console.warn('Could not load state from backend.');
      return;
    }

    this.selectedDay = this.state.selected_day_index || this.state.current_day_index || 1;

    window.bookmarkedWordsSet = new Set((this.state.bookmarked_words || []).map(b => b.word.toLowerCase()));
    this.updateBookmarkBadge((this.state.bookmarked_words || []).length);

    if (window.DistanceMeter) {
      window.DistanceMeter.updateState(this.state);
    }

    this.renderDashboard();
  },

  setupHeaderControls() {
    // Mode toggles
    const gradedBtn = document.getElementById('modeGradedBtn');
    const nonGradedBtn = document.getElementById('modeNonGradedBtn');

    if (gradedBtn && nonGradedBtn) {
      gradedBtn.onclick = () => {
        this.studyMode = 'graded';
        gradedBtn.classList.add('active');
        nonGradedBtn.classList.remove('active');
      };
      nonGradedBtn.onclick = () => {
        this.studyMode = 'non_graded';
        nonGradedBtn.classList.add('active');
        gradedBtn.classList.remove('active');
      };
    }

    // Nav buttons
    const navSalon = document.getElementById('navSalon');
    const navSkillTree = document.getElementById('navSkillTree');
    const navParallel = document.getElementById('navParallel');
    const navBookmarks = document.getElementById('navBookmarks');
    const navFlashcard = document.getElementById('navFlashcard');
    const navMilestones = document.getElementById('navMilestones');
    const navHandbook = document.getElementById('navHandbook');
    const navFeaturesMap = document.getElementById('navFeaturesMap');

    if (navSalon) {
      navSalon.onclick = () => this.showDashboard();
    }
    if (navSkillTree) {
      navSkillTree.onclick = () => {
        if (window.SkillTreeMap) {
          window.SkillTreeMap.open(this.state?.tag_stats || {});
        }
      };
    }
    if (navParallel) {
      navParallel.onclick = () => this.openParallelModal();
    }
    if (navBookmarks) {
      navBookmarks.onclick = () => this.openBookmarksModal();
    }
    if (navFlashcard) {
      navFlashcard.onclick = () => window.SalonFlashcard?.startSession();
    }
    if (navMilestones) {
      navMilestones.onclick = () => window.milestonesEngine?.open();
    }
    if (navHandbook) {
      navHandbook.onclick = () => window.Handbook?.open();
    }
    if (navFeaturesMap) {
      navFeaturesMap.onclick = () => this.toggleFeaturesMapModal();
    }
    const navMobileSync = document.getElementById('navMobileSync');
    if (navMobileSync) {
      navMobileSync.onclick = () => this.openMobileSyncModal();
    }
  },

  setupModals() {
    const featuresMapModal = document.getElementById('featuresMapModal');
    const featuresMapClose = document.getElementById('featuresMapClose');
    if (featuresMapClose && featuresMapModal) {
      featuresMapClose.onclick = () => this.closeFeaturesMapModal();
    }
    if (featuresMapModal) {
      featuresMapModal.onclick = (e) => {
        if (e.target === featuresMapModal) this.closeFeaturesMapModal();
      };
    }

    const mapHandbook = document.getElementById('mapBtnHandbook');
    const mapParallel = document.getElementById('mapBtnParallel');
    const mapSkillTree = document.getElementById('mapBtnSkillTree');
    const mapDaily = document.getElementById('mapBtnDaily');
    const mapFlashcard = document.getElementById('mapBtnFlashcard');
    const mapTyping = document.getElementById('mapBtnTyping');
    const mapBookmarks = document.getElementById('mapBtnBookmarks');
    const mapMilestones = document.getElementById('mapBtnMilestones');

    if (mapHandbook) mapHandbook.onclick = () => { this.closeFeaturesMapModal(); window.Handbook?.open(); };
    if (mapParallel) mapParallel.onclick = () => { this.closeFeaturesMapModal(); this.openParallelModal(); };
    if (mapSkillTree) mapSkillTree.onclick = () => { this.closeFeaturesMapModal(); window.SkillTreeMap?.open(this.state?.tag_stats || {}); };
    if (mapDaily) mapDaily.onclick = () => { this.closeFeaturesMapModal(); this.showDashboard(); };
    if (mapFlashcard) mapFlashcard.onclick = () => { this.closeFeaturesMapModal(); window.SalonFlashcard?.startSession(); };
    if (mapTyping) mapTyping.onclick = () => { this.closeFeaturesMapModal(); window.location.href = '/typing.html'; };
    if (mapBookmarks) mapBookmarks.onclick = () => { this.closeFeaturesMapModal(); this.openBookmarksModal(); };
    if (mapMilestones) mapMilestones.onclick = () => { this.closeFeaturesMapModal(); window.milestonesEngine?.open(); };

    const treeModal = document.getElementById('skillTreeModal');
    const treeClose = document.getElementById('skillTreeClose');
    const treeBody = document.getElementById('skillTreeBody');
    if (window.SkillTreeMap) {
      window.SkillTreeMap.init(treeModal, treeBody);
    }
    if (treeClose) {
      treeClose.onclick = () => window.SkillTreeMap.close();
    }

    const parallelModal = document.getElementById('parallelModal');
    const parallelClose = document.getElementById('parallelClose');
    if (parallelClose && parallelModal) {
      parallelClose.onclick = () => parallelModal.classList.remove('open');
    }

    const bookmarksModal = document.getElementById('bookmarksModal');
    const bookmarksClose = document.getElementById('bookmarksClose');
    if (bookmarksClose && bookmarksModal) {
      bookmarksClose.onclick = () => bookmarksModal.classList.remove('open');
    }

    const bmStartFlashBtn = document.getElementById('bmStartFlashBtn');
    if (bmStartFlashBtn) {
      bmStartFlashBtn.onclick = () => window.SalonFlashcard?.startSession();
    }

    const handbookModal = document.getElementById('handbookModal');
    const handbookClose = document.getElementById('handbookClose');
    const handbookSidebar = document.getElementById('handbookSidebar');
    const handbookReader = document.getElementById('handbookReader');
    const handbookSearch = document.getElementById('handbookSearch');
    if (window.Handbook) {
      window.Handbook.init(handbookModal, handbookSidebar, handbookReader, handbookSearch);
    }
    if (handbookClose && handbookModal) {
      handbookClose.onclick = () => window.Handbook?.close();
    }

    const mobileSyncModal = document.getElementById('mobileSyncModal');
    const mobileSyncClose = document.getElementById('mobileSyncClose');
    if (mobileSyncClose && mobileSyncModal) {
      mobileSyncClose.onclick = () => mobileSyncModal.classList.remove('open');
    }
    if (mobileSyncModal) {
      mobileSyncModal.onclick = (e) => {
        if (e.target === mobileSyncModal) mobileSyncModal.classList.remove('open');
      };
    }

    const btnSavePcSyncConfig = document.getElementById('btnSavePcSyncConfig');
    if (btnSavePcSyncConfig) {
      btnSavePcSyncConfig.onclick = async () => {
        const gistId = document.getElementById('pcGistIdInput')?.value.trim();
        const token = document.getElementById('pcGithubTokenInput')?.value.trim();
        await fetch('/api/sync/github_config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ gist_id: gistId, github_token: token })
        });
        const notice = document.getElementById('pcConfigSavedNotice');
        if (notice) {
          notice.style.display = 'inline';
          setTimeout(() => notice.style.display = 'none', 3000);
        }
      };
    }

    const btnPcPullGist = document.getElementById('btnPcPullGist');
    if (btnPcPullGist) {
      btnPcPullGist.onclick = async () => {
        btnPcPullGist.disabled = true;
        btnPcPullGist.textContent = '⏳ 受信中...';
        try {
          const res = await fetch('/api/sync/github_pull', { method: 'POST' });
          const data = await res.json();
          const toast = document.getElementById('pcSyncResultToast');
          if (res.ok && data.status === 'success') {
            if (toast) {
              toast.textContent = `✅ ${data.tanya_message || '進捗を取り込みました！'}`;
              toast.style.display = 'block';
            }
            await this.loadState();
          } else {
            alert(data.error || '同期に失敗しました。');
          }
        } catch (e) {
          alert('通信エラー: ' + e.message);
        } finally {
          btnPcPullGist.disabled = false;
          btnPcPullGist.textContent = '📥 スマホの進捗を受信 (Pull)';
        }
      };
    }

    const btnPcPushGist = document.getElementById('btnPcPushGist');
    if (btnPcPushGist) {
      btnPcPushGist.onclick = async () => {
        btnPcPushGist.disabled = true;
        btnPcPushGist.textContent = '⏳ 送信中...';
        try {
          const res = await fetch('/api/sync/github_push', { method: 'POST' });
          const data = await res.json();
          const toast = document.getElementById('pcSyncResultToast');
          if (res.ok && data.status === 'success') {
            if (toast) {
              toast.textContent = `✅ ${data.message || 'Gistへ最新スター単語を送信しました！'}`;
              toast.style.display = 'block';
            }
          } else {
            alert(data.error || '送信に失敗しました。');
          }
        } catch (e) {
          alert('通信エラー: ' + e.message);
        } finally {
          btnPcPushGist.disabled = false;
          btnPcPushGist.textContent = '📤 最新の⭐単語を送信 (Push)';
        }
      };
    }
  },

  async openMobileSyncModal() {
    const modal = document.getElementById('mobileSyncModal');
    if (!modal) return;
    try {
      const res = await fetch('/api/sync/github_status');
      const data = await res.json();
      if (data.gist_id) {
        const input = document.getElementById('pcGistIdInput');
        if (input) input.value = data.gist_id;
      }
    } catch (e) {
      console.warn('Sync status fetch failed:', e);
    }
    modal.classList.add('open');
  },

  renderDashboard() {
    this.activeView = 'dashboard';
    if (window.scrollX !== 0) {
      window.scrollTo({ left: 0, top: window.scrollY });
    }
    const main = document.getElementById('appMainContent');
    if (!main || !this.state) return;

    const profile = this.state.user_profile || {};
    const todayPack = this.state.today_pack || {};
    const sessions = todayPack.sessions || {};
    const bufferDays = this.state.buffer_days_left || 0;
    const milestone = this.state.milestone_progress || {};
    const activePhase = milestone.active_phase || {};
    const currentDay = this.state.current_study_day || this.state.current_day_index || 1;
    const calendarDay = this.state.calendar_day_index || currentDay;
    const selectedDay = this.state.selected_day_index || currentDay;
    const availableDays = this.state.available_days || [];
    const isViewingToday = (selectedDay === currentDay);
    const lagDays = this.state.lag_days ?? 0;
    const paceSyncLabel = this.state.pace_sync_label || '予定通り (On Schedule)';
    const isCurrentDayCompleted = this.state.is_current_day_completed ?? false;

    // Completed session tracking for selected day
    const completedTypes = this.state.completed_session_types || [];
    const isMorningCompleted = completedTypes.includes('morning');
    const isNoonCompleted = completedTypes.includes('noon');
    const isEveningCompleted = completedTypes.includes('evening');
    const isStoryCompleted = completedTypes.includes('story');
    const completedCount = [isMorningCompleted, isNoonCompleted, isEveningCompleted, isStoryCompleted].filter(Boolean).length;

    // Update Top App Header Day Capsule
    const headerDayBadge = document.getElementById('headerDayBadge');
    const headerSessionBadge = document.getElementById('headerSessionBadge');
    if (headerDayBadge) headerDayBadge.textContent = `📅 第${selectedDay}日`;
    if (headerSessionBadge) headerSessionBadge.textContent = isViewingToday ? '音楽院サロン (本日)' : `音楽院サロン (第${selectedDay}日 復習)`;

    let paceColor = 'var(--emerald-light)';
    if (lagDays > 0) {
      paceColor = '#fbbf24';
    } else if (lagDays < 0) {
      paceColor = '#818cf8';
    }

    main.innerHTML = `
      <div class="dashboard-view">
        <!-- Hero Dialogue Card -->
        <div class="salon-hero">
          <div class="tanya-portrait-box">
            <img src="assets/images/tanya_smiling.jpg" alt="ターニャ先生" class="tanya-portrait-img">
            <div class="tanya-expression-tag">笑顔の音楽院サロン</div>
          </div>
          <div class="salon-dialogue-box">
            <div>
              <div class="dialogue-bubble">
                <div class="dialogue-speaker">🎹 ターニャ先生の今日の一言 ${!isViewingToday ? `<span class="review-tag">【第${selectedDay}日 復習中】</span>` : ''}</div>
                <div>${todayPack.daily_storyline || "Yusukeさん、モスクワ音楽院サロンへようこそ！今日も美しいピアノの音色のように、心地よいリズムでロシア語に触れていきましょう♪"}</div>
              </div>
            </div>

            <div class="salon-metrics-row">
              <div class="metric-card">
                <div class="metric-card-label">ターニャ先生との絆</div>
                <div class="metric-card-value">Lv.${profile.intimacy?.level || 1} ${profile.intimacy?.title || "音楽仲間"}</div>
                <div class="intimacy-progress-bar">
                  <div class="intimacy-progress-fill" style="width: ${Math.min(100, Math.round((profile.intimacy?.exp || 0) / (profile.intimacy?.max_exp || 50) * 100))}%;"></div>
                </div>
              </div>

              <div class="metric-card">
                <div class="metric-card-label">連続学習</div>
                <div class="metric-card-value">🔥 ${profile.current_streak || 1} 日継続中</div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">休止期間も凍結保護されます</div>
              </div>

              <div class="metric-card">
                <div class="metric-card-label">事前生成バッファ</div>
                <div class="metric-card-value">📦 ${bufferDays} 日分ストック</div>
                <div style="font-size:0.72rem; color:var(--emerald-light); margin-top:4px;">● バッファ健全</div>
              </div>

              <div class="metric-card" id="metricCardMilestone" style="cursor:pointer;" title="クリックで検定ロードマップを表示 (M)">
                <div class="metric-card-label" style="display:flex; justify-content:space-between; align-items:center;">
                  <span>🎯 2027検定目標</span>
                  <kbd class="kbd-badge" style="font-size:0.65rem; padding:1px 5px;">M</kbd>
                </div>
                <div class="metric-card-value" style="font-size:1.02rem;">
                  P${activePhase.phase_num || 1} (${activePhase.progress_pct ?? 63}%)
                </div>
                <div style="font-size:0.72rem; color:var(--emerald-light); margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                  ● ${milestone.pace_label || '順調・先行中 (Ahead)'}
                </div>
              </div>

              <div class="metric-card" id="metricCardSchedule" title="カレンダー日付と学習進度の同期状況">
                <div class="metric-card-label" style="display:flex; justify-content:space-between; align-items:center;">
                  <span style="font-weight:600;">📅 進度ペース</span>
                  <span style="font-size:0.65rem; color:var(--text-muted);">Day ${currentDay} (暦:${calendarDay})</span>
                </div>
                <div class="metric-card-value" style="font-size:1.02rem; color:${paceColor};">
                  ${lagDays === 0 ? '予定通り (同期)' : (lagDays > 0 ? `${lagDays}日分遅れ` : `${Math.abs(lagDays)}日分先行`)}
                </div>
                <div style="font-size:0.72rem; color:${paceColor}; margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                  ● ${paceSyncLabel}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Daily 4-Session Grid with Day Switcher -->
        <div class="daily-sessions-container">
          <div class="daily-nav-bar">
            <div class="daily-nav-title">
              <h2><span>📅 ${isViewingToday ? '本日のマイクロセッション (1回5分)' : `第${selectedDay}日のマイクロセッション (復習・閲覧)`}</span></h2>
              <span class="cutoff-notice" title="深夜0:00〜0:59の勉強は前日分にカウントされ、午前1:00に翌日レッスンへ自動進行します">⏰ 日付切替: 毎朝 01:00</span>
            </div>

            <!-- Day Switcher Scrollable Track -->
            <div class="day-nav-track-wrapper">
              <button class="day-scroll-arrow day-scroll-left" id="btnScrollDaysLeft" title="前の日を表示">◀</button>
              <div class="day-switcher-pills" id="daySwitcherPills">
                ${availableDays.map(d => {
                  const isSelected = (d.day_index === selectedDay);
                  const isCurrent = (d.day_index === currentDay);
                  const isCompleted = d.is_completed;
                  let pillClass = '';
                  let pillPrefix = '';
                  let pillSuffix = '';

                  if (isCompleted) {
                    pillClass = 'pill-completed';
                    pillPrefix = '✓ ';
                    pillSuffix = isCurrent ? ' (本日/済)' : '';
                  } else if (isCurrent) {
                    pillClass = 'pill-today';
                    pillPrefix = '★ ';
                    pillSuffix = ' (本日)';
                  } else if (d.day_index < currentDay) {
                    pillClass = 'pill-uncompleted';
                    pillPrefix = '⏳ ';
                    pillSuffix = ' (未了)';
                  } else {
                    pillClass = 'pill-future';
                    pillSuffix = '';
                  }

                  return `
                    <button class="day-pill-btn ${isSelected ? 'active' : ''} ${pillClass}" 
                            data-day="${d.day_index}" 
                            title="${d.title} (${d.sessions_count || 0}セッション完了)">
                      ${pillPrefix}第${d.day_index}日${pillSuffix}
                    </button>
                  `;
                }).join('')}
              </div>
              <button class="day-scroll-arrow day-scroll-right" id="btnScrollDaysRight" title="次の日を表示">▶</button>
            </div>
          </div>

          <div class="active-day-banner">
            <span class="active-day-badge">Day ${todayPack.day_index || selectedDay}</span>
            <span class="active-day-heading">${todayPack.title || ""}</span>
            ${!isViewingToday ? `<button class="back-to-today-btn" id="btnBackToToday">★ 今日のレッスン (Day ${currentDay}) に戻る</button>` : ''}
          </div>

          <!-- Daily Progress & Session Completion Summary -->
          <div class="daily-progress-summary-bar">
            <div class="daily-progress-info">
              <span class="progress-title">🎯 ${isViewingToday ? '本日の学習達成状況' : `第${selectedDay}日の達成状況`}</span>
              <span class="progress-count-pill ${completedCount >= 3 ? 'all-done' : ''}">${completedCount} / 4 セッション完了</span>
            </div>
            <div class="daily-session-status-chips">
              <span class="status-chip ${isMorningCompleted ? 'done' : 'pending'}">${isMorningCompleted ? '✔' : '⏳'} 🌅 朝: ${isMorningCompleted ? '完了' : '未了'}</span>
              <span class="status-chip ${isNoonCompleted ? 'done' : 'pending'}">${isNoonCompleted ? '✔' : '⏳'} ☀️ 昼: ${isNoonCompleted ? '完了' : '未了'}</span>
              <span class="status-chip ${isEveningCompleted ? 'done' : 'pending'}">${isEveningCompleted ? '✔' : '⏳'} 🌙 夜: ${isEveningCompleted ? '完了' : '未了'}</span>
              <span class="status-chip ${isStoryCompleted ? 'done' : 'pending'}">${isStoryCompleted ? '✔' : '⏳'} 📖 回想録: ${isStoryCompleted ? '完了' : '未了'}</span>
            </div>
          </div>

          <div class="sessions-grid">
            <!-- Morning Session -->
            ${this.renderSessionCard('morning', sessions.morning, '朝', '新規インプット & 探索', 1, isMorningCompleted)}

            <!-- Noon Session -->
            ${this.renderSessionCard('noon', sessions.noon, '昼', '弱点タグのスピードチェック', 2, isNoonCompleted)}

            <!-- Evening Session -->
            ${this.renderSessionCard('evening', sessions.evening, '夜', 'リスニング浴び (判定なし)', 3, isEveningCompleted)}

            <!-- Story Session -->
            ${this.renderSessionCard('story', sessions.story, '回想録', '音楽院の物語 (ストーリー専用)', 4, isStoryCompleted)}
          </div>

          <!-- Day Completion & Catch-up Action Banner -->
          ${(isViewingToday && isCurrentDayCompleted) ? `
            <div class="day-advance-banner">
              <div class="day-advance-info">
                <span class="advance-trophy">🎉</span>
                <div>
                  <div style="font-weight:700; color:var(--gold-light); font-size:0.92rem;">
                    第${currentDay}日の学習目標を達成しました！
                  </div>
                  <div style="font-size:0.78rem; color:var(--text-secondary); margin-top:2px;">
                    ${lagDays > 0 
                      ? `カレンダー進行より${lagDays}日分遅れています。本日さらに進んでキャッチアップしますか？`
                      : `明日の朝 AM 1:00 に自動的に第${currentDay + 1}日へ進みます。今すぐ先行して進めることも可能です。`}
                  </div>
                </div>
              </div>
              <button class="day-advance-btn" id="btnAdvanceNextDay" data-next-day="${currentDay + 1}">
                🚀 第${currentDay + 1}日のレッスンへ進む
              </button>
            </div>
          ` : ''}

          <!-- Optional 3-Minute Encore Section (ターニャ先生の3分アンコール: 任意・お気に入り単語のみ) -->
          ${(isViewingToday && (isCurrentDayCompleted || completedCount >= 3)) ? `
            <div class="salon-encore-card">
              <div class="encore-decor">☕🎹</div>
              <div class="encore-content">
                <div class="encore-header-row">
                  <span class="encore-badge">🎹 本日の任意アンコール</span>
                  <span class="encore-intimacy-pill">💖 親密度 +5 EXP</span>
                </div>
                <div class="encore-title">ターニャ先生の3分アンコールサロン</div>
                <div class="encore-desc">
                  本日の日課達成おめでとうございます！もし余力があれば、ご自身でブックマークしたお気に入り単語（⭐）をサロンで3分サクサク奏でてみませんか？<br>
                  <span class="encore-subnote">※ 完全任意です。自動収集は行わず、あなたが選んだ単語のみを復習します。忙しい日はスキップしてゆっくりお休みくださいね☕</span>
                </div>
                <div class="encore-actions">
                  <button class="encore-start-btn" id="btnDashboardEncore" onclick="window.SalonFlashcard?.startSession(6)">
                    <span>☕ お気に入り単語のアンコールを開く (5〜7語)</span>
                    <kbd class="kbd-badge" style="font-size:0.75rem; margin-left:6px;">F</kbd>
                  </button>
                </div>
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    `;

    // Attach metric card click handler
    const metricMilestone = document.getElementById('metricCardMilestone');
    if (metricMilestone) {
      metricMilestone.onclick = () => window.milestonesEngine?.open();
    }

    // Day Switcher track scroll buttons & auto-scroll to active day
    const pillsTrack = main.querySelector('#daySwitcherPills');
    const scrollLeftBtn = main.querySelector('#btnScrollDaysLeft');
    const scrollRightBtn = main.querySelector('#btnScrollDaysRight');

    if (pillsTrack) {
      if (scrollLeftBtn) {
        scrollLeftBtn.onclick = () => pillsTrack.scrollBy({ left: -260, behavior: 'smooth' });
      }
      if (scrollRightBtn) {
        scrollRightBtn.onclick = () => pillsTrack.scrollBy({ left: 260, behavior: 'smooth' });
      }
      // Auto-scroll track so active day is centered within its container (prevents horizontal window scroll)
      setTimeout(() => {
        const activePill = pillsTrack.querySelector('.day-pill-btn.active') || pillsTrack.querySelector('.day-pill-btn.pill-today');
        if (activePill) {
          const scrollTarget = activePill.offsetLeft - (pillsTrack.clientWidth / 2) + (activePill.clientWidth / 2);
          pillsTrack.scrollTo({ left: Math.max(0, scrollTarget), behavior: 'smooth' });
        }
      }, 50);
    }

    // Attach day pill switchers
    main.querySelectorAll('.day-pill-btn').forEach(btn => {
      btn.onclick = async () => {
        const targetDay = parseInt(btn.dataset.day, 10);
        if (targetDay && targetDay !== this.selectedDay) {
          await this.loadState(targetDay);
        }
      };
    });

    // Advance to next day button
    const advanceBtn = document.getElementById('btnAdvanceNextDay');
    if (advanceBtn) {
      advanceBtn.onclick = async () => {
        const nextDay = parseInt(advanceBtn.dataset.nextDay, 10);
        if (nextDay) {
          advanceBtn.disabled = true;
          advanceBtn.textContent = '進行中...';
          try {
            const res = await fetch('/api/lesson/advance', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ target_day: nextDay })
            }).then(r => r.json());
            if (res && res.status === 'ok') {
              await this.loadState(nextDay);
            }
          } catch (err) {
            console.error('Failed to advance lesson:', err);
            advanceBtn.disabled = false;
            advanceBtn.textContent = `🚀 第${nextDay}日のレッスンへ進む`;
          }
        }
      };
    }

    // Back to today button
    const backToTodayBtn = document.getElementById('btnBackToToday');
    if (backToTodayBtn) {
      backToTodayBtn.onclick = async () => {
        await this.loadState(currentDay);
      };
    }

    // Attach card click handlers
    main.querySelectorAll('.session-card').forEach(card => {
      card.onclick = () => {
        const sType = card.dataset.sessionType;
        const sData = sessions[sType];
        if (sData) {
          this.startLesson(sData, sType);
        }
      };
    });
  },

  renderSessionCard(typeKey, sessionData, timeLabel, badgeSubtitle, keyNum = null, isCompleted = false) {
    if (!sessionData) {
      return `
        <div class="session-card" style="opacity:0.5;">
          <div class="session-title">${timeLabel}: 準備中</div>
        </div>
      `;
    }

    const tags = sessionData.grammar_tags || [];
    const statusPill = isCompleted
      ? `<span class="session-status-pill completed">✔ 完了</span>`
      : `<span class="session-status-pill pending">⏳ 未了</span>`;

    const startBtnText = isCompleted
      ? `<span>🔄 復習する (完了済)</span>`
      : `<span>レッスンを開始</span>`;

    return `
      <div class="session-card ${isCompleted ? 'is-completed' : ''}" data-session-type="${typeKey}">
        <div>
          <div class="session-card-header">
            <div style="display:flex; align-items:center;">
              <span class="session-badge ${typeKey}">${timeLabel}</span>
              ${statusPill}
            </div>
            <span class="session-duration">⏱ 5分</span>
          </div>
          <div class="session-title">${sessionData.title}</div>
          <div class="session-desc">${sessionData.tanya_greeting || ""}</div>
          <div class="session-tags-row">
            ${tags.map(t => `<span class="tag-badge">${t}</span>`).join('')}
          </div>
        </div>
        <button class="session-start-btn ${isCompleted ? 'completed' : ''}">
          ${startBtnText}
          ${keyNum ? `<kbd class="kbd-badge" style="font-size:0.75rem; padding:2px 8px; margin-left:auto; background:#1b1514; color:var(--gold-light);">${keyNum}</kbd>` : '<span>→</span>'}
        </button>
      </div>
    `;
  },

  startLesson(sessionData, typeKey = null) {
    this.activeView = 'player';
    const main = document.getElementById('appMainContent');
    if (!main || !window.LessonPlayer) return;

    const detectedType = typeKey || sessionData.typeKey || sessionData.session_id?.match(/(?:day\d+_|s_\d+_)?([a-z]+)/)?.[1] || (sessionData.title?.includes('昼') ? 'noon' : (sessionData.title?.includes('夜') ? 'evening' : (sessionData.title?.includes('回想') ? 'story' : 'morning')));
    sessionData.day_index = this.selectedDay || this.state?.selected_day_index || 15;
    sessionData.typeKey = detectedType;
    const timeLabelMap = { morning: '朝', noon: '昼', evening: '夜', story: '回想録', memoir: '回想録' };
    const timeLabel = timeLabelMap[detectedType] || '';

    // Update Top App Header Day Capsule
    const headerDayBadge = document.getElementById('headerDayBadge');
    const headerSessionBadge = document.getElementById('headerSessionBadge');
    if (headerDayBadge) headerDayBadge.textContent = `📅 Day ${sessionData.day_index} ［${timeLabel}］`;
    if (headerSessionBadge) headerSessionBadge.textContent = sessionData.title || 'レッスン中';

    window.LessonPlayer.init(main, sessionData, this.studyMode === 'non_graded', () => {
      this.loadState(this.selectedDay);
    });
  },

  showDashboard() {
    this.activeView = 'dashboard';
    this.renderDashboard();
  },

  openFeaturesMapModal() {
    const modal = document.getElementById('featuresMapModal');
    if (modal) modal.classList.add('open');
  },

  closeFeaturesMapModal() {
    const modal = document.getElementById('featuresMapModal');
    if (modal) modal.classList.remove('open');
  },

  toggleFeaturesMapModal() {
    const modal = document.getElementById('featuresMapModal');
    if (!modal) return;
    if (modal.classList.contains('open')) {
      this.closeFeaturesMapModal();
    } else {
      this.openFeaturesMapModal();
    }
  },

  openParallelModal() {
    const modal = document.getElementById('parallelModal');
    if (!modal) return;
    modal.classList.add('open');
  },

  updateBookmarkBadge(count) {
    const badge = document.getElementById('bookmarkCountBadge');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
  },

  async openBookmarksModal() {
    const modal = document.getElementById('bookmarksModal');
    const body = document.getElementById('bookmarksBody');
    const countBadge = document.getElementById('bmModalCountBadge');
    if (!modal || !body) return;

    modal.classList.add('open');
    body.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding:40px; width:100%;">読み込み中...</div>';

    const data = await window.API.getBookmarks();
    const bookmarks = data?.bookmarks || [];

    // Sync window.bookmarkedWordsSet
    window.bookmarkedWordsSet = new Set(bookmarks.map(b => b.word.toLowerCase()));
    this.updateBookmarkBadge(bookmarks.length);
    if (countBadge) countBadge.textContent = `${bookmarks.length}語`;

    if (bookmarks.length === 0) {
      body.innerHTML = `
        <div style="text-align:center; padding:50px 20px; color:var(--text-muted); width:100%;">
          <div style="font-size:2.5rem; margin-bottom:12px;">📖</div>
          <div style="font-size:1.05rem; color:var(--gold-light); font-weight:600; margin-bottom:8px;">まだマークされた単語はありません</div>
          <div style="font-size:0.86rem; line-height:1.6; max-width:480px; margin:0 auto;">
            Phase 2 (触る) で気になる単語を選び、ペイン右上の「☆ マーク」を押すとここに保存されます。<br>
            登録した単語はここでいつでも格変化・活用表や用例をじっくり確認できます。
          </div>
        </div>
      `;
      return;
    }

    // Two-pane split container
    body.innerHTML = `
      <div class="bm-split-container">
        <!-- Left: Word List -->
        <div class="bm-list-pane">
          <div class="bm-list-header">
            <span>保存語一覧</span>
            <span style="color:var(--gold-light); font-weight:600;">${bookmarks.length}語</span>
          </div>
          <div class="bm-list-scroll" id="bmListScroll">
            ${bookmarks.map((b, idx) => `
              <div class="bm-list-item ${idx === 0 ? 'active' : ''}" data-idx="${idx}" data-word="${b.word}">
                <div class="bm-list-item-main">
                  <div class="bm-list-word ru-text">${b.word}</div>
                  <div class="bm-list-sub">${b.meaning || b.pos || '（解説付き）'}</div>
                </div>
                <button class="bm-item-del-btn" data-word="${b.word}" title="単語帳から削除">🗑️</button>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Right: Word Detail Inspector -->
        <div class="bm-detail-pane" id="bmDetailPane">
          <div style="color:var(--text-muted); text-align:center; padding:40px;">詳細を読み込み中...</div>
        </div>
      </div>
    `;

    this.currentSelectedBmIdx = 0;
    this.currentBookmarksList = bookmarks;

    // Load first item detail
    this.renderBookmarkDetail(bookmarks[0]);

    // Wire item selection clicks
    const listItems = body.querySelectorAll('.bm-list-item');
    listItems.forEach(item => {
      item.onclick = (e) => {
        if (e.target.closest('.bm-item-del-btn')) return;
        const idx = parseInt(item.dataset.idx, 10);
        this.currentSelectedBmIdx = idx;
        listItems.forEach(el => el.classList.remove('active'));
        item.classList.add('active');
        const bookmark = bookmarks[idx];
        this.renderBookmarkDetail(bookmark);
        if (window.TTSPlayer && bookmark?.word) {
          window.TTSPlayer.speakWord(bookmark.word);
        }
      };
    });

    // Wire delete buttons
    body.querySelectorAll('.bm-item-del-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const word = btn.dataset.word;
        if (word && window.API) {
          const res = await window.API.toggleBookmark({ word });
          if (res && res.status === 'ok') {
            this.openBookmarksModal();
          }
        }
      };
    });
  },

  async renderBookmarkDetail(bookmarkItem) {
    const detailPane = document.getElementById('bmDetailPane');
    if (!detailPane || !bookmarkItem) return;

    detailPane.innerHTML = '<div style="color:var(--text-muted); padding:30px;">詳細を読み込み中...</div>';

    // Fetch full vocabulary entry
    let entry = null;
    if (window.API) {
      const results = await window.API.searchVocabulary(bookmarkItem.base || bookmarkItem.word);
      if (results && results.length > 0) {
        entry = results.find(r => r.word.toLowerCase() === bookmarkItem.word.toLowerCase() || (bookmarkItem.base && r.word.toLowerCase() === bookmarkItem.base.toLowerCase())) || results[0];
      }
    }

    const wordText = bookmarkItem.word;
    let pos = entry?.pos || bookmarkItem.pos || '';
    let meaning = entry?.meaning || bookmarkItem.meaning || '';
    let notes = entry?.notes || bookmarkItem.notes || bookmarkItem.role || '';
    let anatomy = entry?.anatomy || '';
    let table = entry?.declension_table || null;
    const derivatives = entry?.derivatives || entry?.network || [];
    let collocations = entry?.conservatory_collocations || (entry?.examples ? entry.examples.filter(e => e.ru).map(e => ({ ru: e.ru, ja: e.ja || '' })) : []);
    const fmt = window.formatRussianClickable || (t => t);

    // If meaning or pos is still empty, search window.App.state?.today_pack
    if (!meaning || !pos) {
      const todayPack = window.App?.state?.today_pack;
      if (todayPack?.sessions) {
        const checkWord = (w) => (w || '').toLowerCase();
        const targetW = checkWord(wordText);
        const targetB = checkWord(bookmarkItem.base);
        for (const sKey of Object.keys(todayPack.sessions)) {
          const sess = todayPack.sessions[sKey];
          const paras = (sess.audio_paragraphs || sess.audio_sentences || []).concat(sess.paragraphs || []);
          for (const p of paras) {
            for (const kv of (p.key_vocab || [])) {
              if (checkWord(kv.word) === targetW || checkWord(kv.base) === targetW || (targetB && (checkWord(kv.word) === targetB || checkWord(kv.base) === targetB))) {
                if (!meaning) meaning = kv.meaning;
                if (!pos) pos = kv.pos;
                if (!notes) notes = kv.role_in_sentence;
                if (p.ru && collocations.length === 0) {
                  collocations.push({ ru: p.ru, ja: p.ja || '' });
                }
              }
            }
          }
        }
      }
    }

    if (!pos) pos = '重要単語';
    if (!meaning) meaning = '音楽院重要語彙（文脈キーワード）';

    // If collocations empty and example_ru provided
    if (collocations.length === 0 && bookmarkItem.example_ru) {
      collocations.push({ ru: bookmarkItem.example_ru, ja: bookmarkItem.example_ja || '' });
    }

    // Dynamic smart table generation ONLY for inflected words (never for uninflected parts of speech)
    const combinedMeta = `${pos} ${notes} ${bookmarkItem.role || ''}`;
    const isUninflected = !/participle|形動詞|причастие|動詞|\bverb\b|глагол/i.test(combinedMeta) &&
                          /(?:副詞|наречие|\badv\b|前置詞|предлог|\bprep\b|接続詞|союз|\bconj\b|助詞|小詞|частица|\bparticle\b|間投詞|\binterj\b|不変化)/i.test(combinedMeta);
    if (isUninflected) {
      table = null;
    } else if (!table && !entry?.is_preposition) {
      const cleanW = wordText.toLowerCase();
      const isReflexive = cleanW.endsWith('ся') || cleanW.endsWith('сь');
      const isVerb = isReflexive || cleanW.endsWith('ть') || cleanW.endsWith('ти') || pos.includes('動詞');

      if (isReflexive) {
        const stem = cleanW.replace(/(ться|тся|ся|сь)$/, '');
        if (stem.endsWith('а') || stem.endsWith('я') || stem.endsWith('е')) {
          table = [
            ['人称', `${wordText} (現在形)`, '用例・語形補足'],
            ['я', `${stem}юсь`, `Я ${stem}юсь`],
            ['ты', `${stem}ешься`, `Ты ${stem}ешься`],
            ['он/она', `${stem}ется`, `Он/она ${stem}ется`],
            ['мы', `${stem}емся`, `Мы ${stem}емся`],
            ['вы', `${stem}етесь`, `Вы ${stem}етесь`],
            ['они', `${stem}ются`, `Они ${stem}ются`]
          ];
        } else {
          const bStem = stem.endsWith('и') ? stem.slice(0, -1) : stem;
          table = [
            ['人称', `${wordText} (現在形)`, '用例・語形補足'],
            ['я', `${bStem}усь`, `Я ${bStem}усь`],
            ['ты', `${bStem}ишься`, `Ты ${bStem}ишься`],
            ['он/она', `${bStem}ится`, `Он/она ${bStem}ится`],
            ['мы', `${bStem}имся`, `Мы ${bStem}имся`],
            ['вы', `${bStem}итесь`, `Вы ${bStem}итесь`],
            ['они', `${bStem}атся`, `Они ${bStem}атся`]
          ];
        }
        if (!anatomy) {
          anatomy = `【再帰動詞 (-ся)】自動詞として主語自身の動作・状態変化を表します。\n母音の後では -сь、子音の後では -ся が結合します。`;
        }
      } else if (isVerb) {
        const stem = cleanW.replace(/(ть|ти)$/, '');
        if (stem.endsWith('а') || stem.endsWith('я') || stem.endsWith('е')) {
          table = [
            ['人称', `${wordText} (現在形)`, '用例・語形補足'],
            ['я', `${stem}ю`, `Я ${stem}ю`],
            ['ты', `${stem}ешь`, `Ты ${stem}ешь`],
            ['он/она', `${stem}ет`, `Он/она ${stem}ет`],
            ['мы', `${stem}ем`, `Мы ${stem}ем`],
            ['вы', `${stem}ете`, `Вы ${stem}ете`],
            ['они', `${stem}ют`, `Они ${stem}ют`]
          ];
        } else {
          const bStem = stem.endsWith('и') ? stem.slice(0, -1) : stem;
          table = [
            ['人称', `${wordText} (現在形)`, '用例・語形補足'],
            ['я', `${bStem}ю`, `Я ${bStem}ю`],
            ['ты', `${bStem}ишь`, `Ты ${bStem}ишь`],
            ['он/она', `${bStem}ит`, `Он/она ${bStem}ит`],
            ['мы', `${bStem}им`, `Мы ${bStem}им`],
            ['вы', `${bStem}ите`, `Вы ${bStem}ите`],
            ['они', `${bStem}ят`, `Они ${bStem}ят`]
          ];
        }
        if (!anatomy) {
          anatomy = `【動詞の現在人称変化】主語の人称・数に応じた語尾変化に注意しましょう。`;
        }
      } else if (cleanW.endsWith('а') || cleanW.endsWith('я') || pos.includes('女性名詞')) {
        const isSoft = cleanW.endsWith('я');
        const stem = (cleanW.endsWith('а') || cleanW.endsWith('я')) ? cleanW.slice(0, -1) : cleanW;
        const lastC = stem.slice(-1);
        const needsI = isSoft || 'гкхжчшщ'.includes(lastC);
        table = [
          ['格', '単数 (Единственное)', '複数 (Множественное)'],
          ['主格', wordText, `${stem}${needsI ? 'и' : 'ы'}`],
          ['生格', `${stem}${needsI ? 'и' : 'ы'}`, `${stem}${isSoft ? 'ь' : ''}`],
          ['与格', `${stem}е`, `${stem}${isSoft ? 'ям' : 'ам'}`],
          ['対格', `${stem}${isSoft ? 'ю' : 'у'}`, `${stem}${needsI ? 'и' : 'ы'}`],
          ['造格', `${stem}${isSoft ? 'ей' : 'ой'}`, `${stem}${isSoft ? 'ями' : 'ами'}`],
          ['前置格', `${stem}е`, `${stem}${isSoft ? 'ях' : 'ах'}`]
        ];
        if (!anatomy) {
          anatomy = `【女性名詞の格変化】単数対格は -у/-ю、前置格は -е に変化します。`;
        }
      } else if (!cleanW.endsWith('о') && !cleanW.endsWith('е') && !cleanW.endsWith('ь')) {
        const stem = cleanW;
        const lastC = stem.slice(-1);
        const needsI = 'гкхжчшщ'.includes(lastC);
        table = [
          ['格', '単数 (Единственное)', '複数 (Множественное)'],
          ['主格', wordText, `${stem}${needsI ? 'и' : 'ы'}`],
          ['生格', `${stem}а`, `${stem}ов`],
          ['与格', `${stem}у`, `${stem}ам`],
          ['対格', wordText, `${stem}${needsI ? 'и' : 'ы'}`],
          ['造格', `${stem}ом`, `${stem}ами`],
          ['前置格', `${stem}е`, `${stem}ах`]
        ];
        if (!anatomy) {
          anatomy = `【男性名詞（不活動体）の格変化】不活動体のため対格は単数・複数ともに主格と同形になります。`;
        }
      }
    }

    // Build Table HTML
    let tableHtml = '';
    let reciteSentence = '';
    if (table && table.length > 0) {
      const isVerb = (pos.includes('動詞') || pos.includes('不完了') || pos.includes('完了') || table[0][0] === '人称');
      let reciteBtnHtml = '';
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
          reciteSentence = recitePhrases.join(', ') + '.';
          reciteBtnHtml = `
            <button class="conjugation-recite-btn" id="bmReciteBtn" style="padding:3px 10px; font-size:0.75rem;" title="6つの活用を連続で朗読">
              <span>🔊 6活用連続朗読</span>
              <kbd class="kbd-badge" style="font-size:0.68rem; padding:1px 4px; margin-left:3px;">Я, Ты, Он...</kbd>
            </button>
          `;
        }
      }

      tableHtml = `
        <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div class="bm-detail-section-title" style="margin:0;">
              <span>${isVerb ? '🎹 動詞の活用表 (Спряжение)' : '📊 格変化表 (Склонение)'}</span>
            </div>
            ${reciteBtnHtml}
          </div>
          <table class="declension-table" id="bmDetailTable">
            <thead>
              <tr>${table[0].map(h => `<th>${h}</th>`).join('')}</tr>
            </thead>
            <tbody>
              ${table.slice(1).map(r => `
                <tr data-row-ru="${r.slice(0, 2).join(' ')}" title="クリックで発音 🔊">
                  ${r.map((c, colI) => {
                    const cleanC = (colI === 0 && typeof c === 'string') 
                      ? c.replace(/\s*\([A-Za-z]+\)/g, '').trim() 
                      : c;
                    return `<td>${cleanC}</td>`;
                  }).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } else if (entry?.is_preposition) {
      tableHtml = `
        <div class="preposition-pane-card">
          <div style="font-size:0.95rem; font-weight:700; color:var(--gold-light); margin-bottom:6px;">
            📌 前置詞 «${wordText}» の格支配ノート
          </div>
          <div style="font-size:0.86rem; color:#ffe599; font-weight:600; margin-bottom:6px;">
            ${fmt(notes || meaning)}
          </div>
          <div class="commentary-text">
            ${window.formatCommentaryHtml ? window.formatCommentaryHtml(anatomy) : fmt(anatomy)}
          </div>
        </div>
      `;
    } else {
      const isUninflected = pos.includes('副詞') || pos.includes('接続詞') || pos.includes('前置詞') || pos.includes('不変化');
      if (isUninflected) {
        tableHtml = `
          <div class="uninflected-card">
            <div style="font-size:0.92rem; font-weight:700; color:#38bdf8; margin-bottom:4px;">
              💡 不変化詞ノート «${wordText}»
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6;">
              ロシア語文法上、この単語は格変化や活用などの語尾変化を持たない不変化詞（Неизменяемое слово）です。文脈での配置や前置詞・接続詞としての役割に注意しましょう。
            </div>
          </div>
        `;
      } else {
        tableHtml = `
          <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
            <div class="bm-detail-section-title">📖 語彙・用法メモ</div>
            <div class="commentary-text">
              ${window.formatCommentaryHtml ? window.formatCommentaryHtml(notes || anatomy || 'ロシア語能力検定2級および音楽院の文脈で用いられる重要単語です。') : fmt(notes || anatomy || 'ロシア語能力検定2級および音楽院の文脈で用いられる重要単語です。')}
            </div>
          </div>
        `;
      }
    }

    // Build Derivatives HTML
    let derivativesHtml = '';
    if (derivatives && derivatives.length > 0) {
      derivativesHtml = `
        <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
          <div class="bm-detail-section-title">🌲 語根と派生語 (Семья слов)</div>
          <div style="font-size:0.85rem; color:var(--text-secondary); display:flex; flex-direction:column; gap:4px;">
            ${derivatives.map(d => `<div>• ${fmt(d)}</div>`).join('')}
          </div>
        </div>
      `;
    }

    // Build Collocations HTML
    let collocationsHtml = '';
    if (collocations && collocations.length > 0) {
      collocationsHtml = `
        <div style="background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
          <div class="bm-detail-section-title">🎹 音楽院コロケーション・表現例</div>
          <div style="font-size:0.85rem; display:flex; flex-direction:column; gap:6px;">
            ${collocations.map(c => `
              <div>
                <div style="color:#ffffff; font-weight:600;">${fmt(c.ru || '')}</div>
                ${c.ja ? `<div style="color:var(--text-muted); font-size:0.78rem;">${c.ja}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Build Commentary HTML
    let commentaryHtml = '';
    const displayCommentary = anatomy || notes || `ターニャ先生の鑑賞・学習ノート: «${wordText}» は音楽院のレッスンや会話で登場する重要な単語です。例文と音声で繰り返し馴染ませましょう。`;
    if (displayCommentary) {
      commentaryHtml = `
        <div style="background:rgba(212,175,55,0.06); border:1px solid rgba(212,175,55,0.25); border-radius:var(--radius-sm); padding:12px;">
          <div class="bm-detail-section-title" style="color:#ffe599;">💬 ターニャ先生の解説ノート</div>
          <div class="commentary-text">
            ${window.formatCommentaryHtml ? window.formatCommentaryHtml(displayCommentary) : fmt(displayCommentary)}
          </div>
        </div>
      `;
    }

    detailPane.innerHTML = `
      <div class="bm-detail-header">
        <div>
          <div class="bm-detail-title-row">
            <span class="bm-detail-word ru-text ru-speakable" data-ru="${wordText}" title="クリックで発音 🔊">${wordText}</span>
            <span class="tag-badge" style="font-size:0.78rem;">${pos}</span>
          </div>
          <div class="bm-detail-meaning">${meaning}</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <button class="bookmark-play-btn" id="bmDetailSpeakBtn" title="発音を聴く (Space / R)">
            <span>🔊 発音を聴く</span>
          </button>
          <button class="bookmark-remove-btn" id="bmDetailRemoveBtn" title="単語帳から削除">
            <span>🗑️ 解除</span>
          </button>
        </div>
      </div>

      ${tableHtml}
      ${derivativesHtml}
      ${collocationsHtml}
      ${commentaryHtml}
    `;

    // Wire speak button
    const speakBtn = detailPane.querySelector('#bmDetailSpeakBtn');
    if (speakBtn) {
      speakBtn.onclick = () => {
        if (window.TTSPlayer) window.TTSPlayer.speakWord(wordText);
      };
    }

    // Wire remove button
    const removeBtn = detailPane.querySelector('#bmDetailRemoveBtn');
    if (removeBtn) {
      removeBtn.onclick = async () => {
        if (window.API) {
          const res = await window.API.toggleBookmark({ word: wordText });
          if (res && res.status === 'ok') {
            this.openBookmarksModal();
          }
        }
      };
    }

    // Wire recitation button
    if (reciteSentence) {
      const rBtn = detailPane.querySelector('#bmReciteBtn');
      if (rBtn) {
        rBtn.onclick = () => {
          if (window.TTSPlayer) window.TTSPlayer.speakSentence(reciteSentence);
        };
      }
    }

    // Wire table row clicks
    const tableEl = detailPane.querySelector('#bmDetailTable');
    if (tableEl) {
      tableEl.querySelectorAll('tbody tr').forEach(row => {
        row.onclick = () => {
          const text = row.dataset.rowRu;
          if (text && window.TTSPlayer) window.TTSPlayer.speakSentence(text);
        };
      });
    }
  },

  bindGlobalKeys() {
    window.addEventListener('keydown', (e) => {
      // If Salon Flashcard mode is active, let it handle its shortcuts first
      if (window.SalonFlashcard && window.SalonFlashcard.isOpen) {
        if (window.SalonFlashcard.handleKeyShortcut(e)) {
          return;
        }
      }

      // If modal is open, Escape closes it
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal-overlay.open');
        if (openModal) {
          if (window.TTSPlayer) window.TTSPlayer.stop();
          openModal.classList.remove('open');
          if (openModal.id === 'bathExplainModal' && window.LessonPlayer) {
            window.LessonPlayer.clearBathExplainingActive();
          }
          return;
        }
      }

      // If bookmarks modal is open, handle arrow keys and space/r for audio
      const bookmarksModal = document.getElementById('bookmarksModal');
      if (bookmarksModal && bookmarksModal.classList.contains('open')) {
        if (e.key === ' ' || e.key === 'r' || e.key === 'R') {
          e.preventDefault();
          const speakBtn = document.getElementById('bmDetailSpeakBtn');
          if (speakBtn) speakBtn.click();
          return;
        }
        if (e.key === 'ArrowDown' || e.key === 'j' || e.key === 'J') {
          e.preventDefault();
          if (this.currentBookmarksList && this.currentBookmarksList.length > 0) {
            this.currentSelectedBmIdx = (this.currentSelectedBmIdx + 1) % this.currentBookmarksList.length;
            const items = document.querySelectorAll('.bm-list-item');
            items.forEach((item, idx) => {
              item.classList.toggle('active', idx === this.currentSelectedBmIdx);
              if (idx === this.currentSelectedBmIdx) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            const selBm = this.currentBookmarksList[this.currentSelectedBmIdx];
            this.renderBookmarkDetail(selBm);
            if (window.TTSPlayer && selBm?.word) {
              window.TTSPlayer.speakWord(selBm.word);
            }
          }
          return;
        }
        if (e.key === 'ArrowUp' || e.key === 'k' || e.key === 'K') {
          e.preventDefault();
          if (this.currentBookmarksList && this.currentBookmarksList.length > 0) {
            this.currentSelectedBmIdx = (this.currentSelectedBmIdx - 1 + this.currentBookmarksList.length) % this.currentBookmarksList.length;
            const items = document.querySelectorAll('.bm-list-item');
            items.forEach((item, idx) => {
              item.classList.toggle('active', idx === this.currentSelectedBmIdx);
              if (idx === this.currentSelectedBmIdx) item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            });
            const selBm = this.currentBookmarksList[this.currentSelectedBmIdx];
            this.renderBookmarkDetail(selBm);
            if (window.TTSPlayer && selBm?.word) {
              window.TTSPlayer.speakWord(selBm.word);
            }
          }
          return;
        }
      }

      // If in Player view (e.g. matching quiz or lesson navigation), give LessonPlayer first priority!
      if (this.activeView === 'player' && window.LessonPlayer) {
        if (window.LessonPlayer.handleKeyShortcut(e)) {
          return;
        }
      }

      // 'B' key toggles Bookmarks modal
      if ((e.key === 'b' || e.key === 'B') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        if (this.activeView === 'player') {
          return; // Prevent modal popup during active lessons or matching quizzes
        }
        const bookmarksModal = document.getElementById('bookmarksModal');
        if (bookmarksModal && bookmarksModal.classList.contains('open')) {
          bookmarksModal.classList.remove('open');
        } else {
          this.openBookmarksModal();
        }
        return;
      }

      // 'F' key starts 3-Minute Salon Flashcard session
      if ((e.key === 'f' || e.key === 'F') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        if (this.activeView === 'player' && !window.SalonFlashcard?.isOpen) {
          return; // Prevent modal popup during active lesson
        }
        window.SalonFlashcard?.startSession();
        return;
      }

      // 'M' key toggles Milestones modal
      if ((e.key === 'm' || e.key === 'M') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        const milestonesModal = document.getElementById('milestonesModal');
        if (milestonesModal && milestonesModal.classList.contains('open')) {
          milestonesModal.classList.remove('open');
        } else {
          window.milestonesEngine?.open();
        }
        return;
      }

      // 'G' key toggles Handbook (文法書/教科書) modal
      if ((e.key === 'g' || e.key === 'G') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        const handbookModal = document.getElementById('handbookModal');
        if (handbookModal && handbookModal.classList.contains('open')) {
          window.Handbook?.close();
        } else {
          window.Handbook?.open();
        }
        return;
      }

      // 'T' key opens Russian Typing Dojo
      if ((e.key === 't' || e.key === 'T') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        window.location.href = '/typing.html';
        return;
      }

      // 'H' key toggles Features Map modal (全機能マップ & ガイド)
      if ((e.key === 'h' || e.key === 'H' || e.key === '?') && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        this.toggleFeaturesMapModal();
        return;
      }

      if (this.activeView === 'dashboard') {
        if (e.key === 's' || e.key === 'S') {
          const navTree = document.getElementById('navSkillTree');
          if (navTree) navTree.click();
        } else if (e.key === 'p' || e.key === 'P') {
          this.openParallelModal();
        } else if (['1', '2', '3', '4'].includes(e.key)) {
          const typeKeys = ['morning', 'noon', 'evening', 'story'];
          const chosenKey = typeKeys[parseInt(e.key, 10) - 1];
          const todayPack = this.state?.today_pack || {};
          const session = todayPack.sessions?.[chosenKey];
          if (session) {
            this.startLesson(session, chosenKey);
          }
        }
      }
    });

    // Global Click-to-Speak listener for Russian words in commentary/explanations
    document.addEventListener('click', (e) => {
      const speakable = e.target.closest('.ru-speakable');
      if (speakable) {
        const text = speakable.dataset.ru || speakable.innerText || speakable.textContent;
        const clean = text.replace(/[«»„“”\(\)\[\]]/g, '').trim();
        if (clean && window.TTSPlayer) {
          window.TTSPlayer.speakWord(clean);
        }
      }
    });
  }
};

window.formatRussianClickable = function(text) {
  if (!text || typeof text !== 'string') return '';
  // Match Cyrillic words or hyphenated words
  return text.replace(/([а-яА-ЯёЁ«»—]+(?:[\s\-]+[а-яА-ЯёЁ«»—]+)*)/g, (match) => {
    if (!/[а-яА-ЯёЁ]/.test(match)) return match;
    const cleanWord = match.replace(/[«»„“”\(\)\[\]]/g, '').trim();
    return `<span class="ru-speakable" data-ru="${cleanWord}" title="クリックで発音 🔊">${match}</span>`;
  });
};

window.formatCommentaryHtml = function(rawText) {
  if (!rawText || typeof rawText !== 'string') return '';
  const fmtRu = window.formatRussianClickable || (t => t);

  // 1. Normalize line breaks
  let text = rawText.replace(/\r\n/g, '\n').trim();

  // 2. Separate inline bullets/numbers attached to end of sentences or brackets
  text = text.replace(/([。！？.!?」』）\)])\s*([①②③④⑤⑥⑦⑧⑨⑩])/g, '$1\n$2');
  text = text.replace(/([。！？.!?」』）\)])\s*([・•])/g, '$1\n$2');
  text = text.replace(/([。！？.!?」』）\)])\s*(※|⚠️|【注意】)/g, '$1\n$2');
  text = text.replace(/([。！？.!?」』）\)])\s*(\d+[\.、\)]\s+)/g, '$1\n$2');
  text = text.replace(/(^|[」』）\) \t])\s*・\s*/gm, '$1\n・');
  text = text.replace(/\s*(発展表現[:：]|類語[:：]|対義語[:：]|対比語?[:：])/g, '\n$1');

  // 3. Convert markdown bold **text** -> <strong class="commentary-bold">text</strong>
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="commentary-bold">$1</strong>');

  const lines = text.split('\n');
  const blocks = [];

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();
    if (!line) {
      blocks.push('<div class="commentary-spacer"></div>');
      continue;
    }

    // A. Note / Warning: starts with ※, ⚠️, 注:, 注意:, 【注意】
    if (/^(?:※|⚠️|注[:：]|注意[:：]|【注意】)/.test(line)) {
      const clean = line.replace(/^(?:※|⚠️|注[:：]|注意[:：]|【注意】)\s*/, '');
      blocks.push(`<div class="commentary-note-line"><span class="note-icon">💡</span><span class="note-text">${fmtRu(clean)}</span></div>`);
      continue;
    }

    // B. Sub-headers: 発展表現:, 類語:, 対比:, etc.
    const subHeaderMatch = line.match(/^(発展表現|類語|対義語|対比語?|補足)[:：]\s*(.*)$/);
    if (subHeaderMatch) {
      const tag = subHeaderMatch[1];
      const rest = subHeaderMatch[2];
      blocks.push(`<div class="commentary-header-line"><span class="section-tag">🏷️ ${tag}:</span><span class="section-body">${fmtRu(rest)}</span></div>`);
      continue;
    }

    // C. Numbered items: ①, ②, ③... or 1., 2., or (1), (2)
    const numMatch = line.match(/^([①②③④⑤⑥⑦⑧⑨⑩]|\d+[\.、\)]|\(\d+\))\s*(.*)$/);
    if (numMatch) {
      const badge = numMatch[1];
      const rest = numMatch[2];
      blocks.push(`<div class="commentary-numbered-line"><span class="numbered-badge">${badge}</span><span class="numbered-text">${fmtRu(rest)}</span></div>`);
      continue;
    }

    // D. Bullet items: ・, -, *, •, ⁃
    const bulletMatch = line.match(/^(?:・|\-|\*|•|⁃)\s*(.*)$/);
    if (bulletMatch) {
      const rest = bulletMatch[1];
      blocks.push(`<div class="commentary-bullet-line"><span class="bullet-icon">✦</span><span class="bullet-text">${fmtRu(rest)}</span></div>`);
      continue;
    }

    // E. Section header: 【...】
    const headerMatch = line.match(/^【(.*?)】\s*(.*)$/);
    if (headerMatch) {
      const tag = headerMatch[1];
      const rest = headerMatch[2];
      blocks.push(`<div class="commentary-header-line"><span class="section-tag">【${tag}】</span><span class="section-body">${fmtRu(rest)}</span></div>`);
      continue;
    }

    // F. Regular paragraph
    blocks.push(`<p class="commentary-para">${fmtRu(line)}</p>`);
  }

  return blocks.join('');
};

window.getSoftSignNounGender = function(word, base = '', pos = '', role = '') {
  const w = (word || '').toLowerCase().trim().replace(/[.,!?;:«»""'']/g, '');
  const b = (base || '').toLowerCase().trim().replace(/[.,!?;:«»""'']/g, '');
  const combinedMeta = `${pos} ${role}`.toLowerCase();

  // STRICT GUARD: Verbs, participles, adjectives, adverbs, prepositions, conjunctions CANNOT be -ь nouns!
  if (/(?:動詞|verb|глагол|participle|形動詞|деепричастие|副動詞|形容詞|\badj\b|前置詞|prep|副詞|\badv\b|接続詞|conj)/i.test(combinedMeta)) {
    return null;
  }

  // The base or word MUST end in 'ь' to qualify as a soft sign noun
  if (!w.endsWith('ь') && !b.endsWith('ь')) {
    return null;
  }

  // If explicit in pos/role
  if (/(?:男性|муж|masc|\bm\b|\(男\))/i.test(combinedMeta) && !/女性/i.test(combinedMeta)) {
    return 'm';
  }
  if (/(?:女性|жен|fem|\bf\b|\(女\))/i.test(combinedMeta) && !/男性/i.test(combinedMeta)) {
    return 'f';
  }

  // Known dictionary of -ь nouns
  const knownMasc = new Set([
    'рояль', 'день', 'путь', 'дождь', 'гость', 'рубль', 'автомобиль', 'спектакль',
    'контроль', 'стиль', 'шампунь', 'пароль', 'зверь', 'медведь', 'палец', 'огонь',
    'конь', 'камень', 'уголь', 'вихорь', 'январь', 'февраль', 'апрель', 'июнь',
    'июль', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь', 'учитель', 'писатель',
    'преподаватель', 'водитель', 'читатель', 'слушатель', 'словарь', 'секретарь',
    'календарь', 'богатырь', 'вратарь', 'государь', 'слесарь', 'токарь', 'локоть',
    'лебедь', 'гвоздь', 'корень', 'парень', 'уровень', 'вихрь', 'выхлоп'
  ]);

  const knownFem = new Set([
    'память', 'жизнь', 'любовь', 'площадь', 'кровать', 'тетрадь', 'дверь', 'печь',
    'осень', 'лошадь', 'кость', 'пыль', 'соль', 'цель', 'связь', 'кровь', 'мать',
    'дочь', 'мысль', 'роль', 'деталь', 'честь', 'власть', 'смерть', 'сибирь',
    'мелочь', 'подпись', 'болезнь', 'ступень', 'ночь', 'вещь', 'помощь', 'ложь',
    'рожь', 'молодежь', 'молодёжь', 'глушь', 'тишь', 'сушь', 'тушь', 'печать',
    'очередь', 'нить', 'ткань', 'ветвь', 'обувь', 'грязь', 'медь', 'сталь',
    'нефть', 'шерсть', 'зависть', 'жалость', 'повесть', 'радость', 'свежесть',
    'новость', 'возможность', 'музыкальность', 'трудность', 'скорость', 'крепость',
    'слабость', 'гордость', 'глупость', 'смелость', 'зрелость', 'бедность'
  ]);

  const testWords = [b, w].filter(Boolean);
  for (const tw of testWords) {
    if (knownMasc.has(tw)) return 'm';
    if (knownFem.has(tw)) return 'f';

    // 100% Suffix Rules
    // Feminine: -ость, -есть
    if (tw.endsWith('ость') || tw.endsWith('есть')) return 'f';
    // Feminine: -чь, -шь, -щь, -жь
    if (tw.endsWith('чь') || tw.endsWith('шь') || tw.endsWith('щь') || tw.endsWith('жь')) return 'f';
    // Masculine: -тель, -арь
    if (tw.endsWith('тель') || tw.endsWith('арь')) return 'm';
    // Masculine: calendar months in -ь
    if (['январь','февраль','апрель','июнь','июль','сентябрь','октябрь','ноябрь','декабрь'].includes(tw)) return 'm';
  }

  // If pos indicates noun and base ends in ь
  if ((w.endsWith('ь') || b.endsWith('ь')) && /名詞|сущ/i.test(combinedMeta)) {
    if (/男性|муж/i.test(combinedMeta)) return 'm';
    if (/女性|жен/i.test(combinedMeta)) return 'f';
  }

  return null;
};

window.renderSoftSignGenderBadge = function(word, base = '', pos = '', role = '') {
  const gender = window.getSoftSignNounGender(word, base, pos, role);
  if (gender === 'm') {
    return `<span class="badge-gender-m" title="男性名詞 ♂ (軟子音変化)">m ♂</span>`;
  } else if (gender === 'f') {
    return `<span class="badge-gender-f" title="女性名詞 ♀ (第3変化名詞)">f ♀</span>`;
  }
  return '';
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
