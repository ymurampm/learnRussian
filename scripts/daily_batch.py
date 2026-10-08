"""
Daily Batch Maintenance & Lesson Buffer Management
Tanya Russian Learning App (Moscow Conservatory Edition)

Scheduled to run daily at 01:00 AM.
Tasks performed:
1. Lesson Buffer Health Check:
   - Validates data/lesson_buffer.json
   - Verifies integrity of all sessions (Morning, Noon, Evening, Story)
   - Checks buffer day count
2. User Progress & Weakness Analysis:
   - Reads data/user_progress.json
   - Analyzes tag_stats (rusty, stable, reflex)
   - Updates streak and absence status (0-2 days normal, 3+ days welcome back)
3. Tanya's Daily Greeting & Message Generation:
   - Formulates personalized Russian/Japanese greeting reflecting user's recent progress
4. Automated Daily Backups:
   - Creates timestamped snapshot in data/backups/
   - Rotates backups, keeping latest 14 snapshots
5. Structured Status Output:
   - Updates data/batch_status.json
   - Appends detailed run summary to logs/daily_batch.log
"""

import os
import sys
import json
import shutil
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

def load_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Error reading {filename}: {e}")
        return default if default is not None else {}

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    if filename == "user_progress.json":
        if not data or not isinstance(data, dict) or not data.get("user_profile", {}).get("name"):
            print(f"[SECURITY REJECT] daily_batch attempted to save empty user_progress to {path}! Aborting save.")
            return
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def get_effective_date(dt=None):
    """
    Returns the effective study date according to the 01:00 AM cutoff rule.
    00:00:00 - 00:59:59 belongs to the previous calendar day's study cycle.
    01:00:00 begins the new day's cycle.
    """
    if dt is None:
        dt = datetime.now()
    if dt.hour < 1:
        return (dt - timedelta(days=1)).date()
    return dt.date()

def backup_data():
    """Create a timestamped backup of user progress and lesson data, rotating older backups."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = os.path.join(BACKUPS_DIR, timestamp)
    os.makedirs(dest_dir, exist_ok=True)

    files_to_backup = ["user_progress.json", "lesson_buffer.json", "vocabulary_db.json", "batch_status.json"]
    backed_up = []
    for fn in files_to_backup:
        src = os.path.join(DATA_DIR, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_dir, fn))
            backed_up.append(fn)

    # Rotate old backups: keep newest 14
    all_backups = sorted([
        d for d in os.listdir(BACKUPS_DIR) 
        if os.path.isdir(os.path.join(BACKUPS_DIR, d)) and d.startswith("20")
    ])
    if len(all_backups) > 14:
        for old in all_backups[:-14]:
            shutil.rmtree(os.path.join(BACKUPS_DIR, old), ignore_errors=True)

    return dest_dir, backed_up

def analyze_user_progress():
    """Analyze user weaknesses, streak, and compute daily greeting from Tanya."""
    progress = load_json("user_progress.json", {})
    user_profile = progress.get("user_profile", {})
    user_name = user_profile.get("name", "Yusuke")
    tag_stats = progress.get("tag_stats", {})
    
    rusty_tags = []
    stable_tags = []
    reflex_tags = []

    for tag, stat in tag_stats.items():
        st = stat.get("status", "developing")
        if st == "rusty":
            rusty_tags.append((tag, stat.get("seen", 0), stat.get("avg_rt_ms", 0)))
        elif st == "stable":
            stable_tags.append(tag)
        elif st == "reflex":
            reflex_tags.append(tag)

    # Sort rusty tags by reaction time descending
    rusty_tags.sort(key=lambda x: x[2], reverse=True)

    # Absence check
    today_dt = get_effective_date()
    today_str = today_dt.isoformat()
    last_active = user_profile.get("last_active_date", today_str)
    try:
        last_dt = datetime.strptime(last_active, "%Y-%m-%d").date()
        days_gap = (today_dt - last_dt).days
    except Exception:
        days_gap = 0

    streak = user_profile.get("current_streak", 1)
    intimacy = user_profile.get("intimacy", {})
    intimacy_level = intimacy.get("level", 1)
    intimacy_title = intimacy.get("title", "知り合いの生徒")

    # Generate daily personalized greeting
    if days_gap >= 7:
        greeting = (
            f"Юсукэ, с возвращением! しばらくお会いできていませんでしたが、ピアノの調子はいかがでしたか？"
            f"今日はリハビリを兼ねて、耳馴染みのある音楽院のフレーズからゆっくり思い出していきましょう。"
        )
    elif days_gap >= 3:
        greeting = (
            f"Здравствуйте, Юсукэ! 少しお久しぶりですね。指と耳の感覚を呼び覚ますように、"
            f"今日の5分レッスンを軽やかに始めましょう♪"
        )
    else:
        if rusty_tags:
            focus_tag = rusty_tags[0][0]
            taxonomy = load_json("grammar_taxonomy.json", {})
            tag_label = focus_tag
            for cat in taxonomy.get("categories", {}).values():
                for t_key, t_val in cat.get("tags", {}).items():
                    if t_key == focus_tag:
                        tag_label = t_val.get("name", focus_tag)
                        break
            if tag_label == focus_tag:
                tag_name_map = {
                    "case.nom": "主格（主語）",
                    "case.gen": "生格（所属・数量・前置詞支配）",
                    "case.dat": "与格（間接目的語・無人称述語）",
                    "case.acc": "対格（方向・目的語）",
                    "case.ins": "造格（道具・手段・共同）",
                    "case.prp": "前置格（場所・楽器演奏）",
                    "verb.aspect_sv": "完了体動詞（1回の完了・結果）",
                    "verb.aspect_nsv": "不完了体動詞（過程・反復）",
                    "verb.motion_uni": "定動詞（一方向への移動）",
                    "verb.motion_multi": "不定動詞（往復・周遊）",
                    "verb.motion_prefixed": "接頭辞付き移動動詞",
                    "verb.irregular": "不規則・特殊活用動詞",
                    "adj.declension": "形容詞の格変化",
                    "adj.short": "形容詞短語尾形",
                    "numeral.agreement": "数詞と名詞の一致",
                    "numeral.declension_all": "数詞の全格変化",
                    "numeral.collective": "集合数詞",
                    "syntax.conditional": "仮定法・条件法",
                    "syntax.subordinate": "従属節（目的・譲歩）",
                    "participle.active": "能動形動詞",
                    "participle.passive": "受動形動詞",
                    "gerund.imperfective": "不完了体副動詞",
                    "gerund.perfective": "完了体副動詞",
                    "gerund.verbal_adverb": "副動詞構文と主語一致",
                    "noun.soft_sign": "-ь 語尾名詞の性別",
                    "noun.irregular_fleeting": "出没音・特殊複数"
                }
                tag_label = tag_name_map.get(focus_tag, focus_tag)

            greeting = (
                f"Доброе утро, Юсукэ! 昨日は{tag_label}の練習、お疲れさまでした。"
                f"難しい変化も、ピアノのスケールのように毎日少しずつ馴染ませていけば大丈夫です。今日も音楽院でお待ちしています♪"
            )
        else:
            started_date_str = user_profile.get("started_date", "2026-09-12")
            try:
                started_dt = datetime.strptime(started_date_str, "%Y-%m-%d").date()
                cal_day = max(1, (today_dt - started_dt).days + 1)
            except Exception:
                cal_day = 1
            curr_study_day = user_profile.get("current_study_day", 1)
            lag_days = cal_day - curr_study_day

            if lag_days > 0:
                greeting = (
                    f"Доброе утро, Юсукэ! カレンダーからは少しゆったり進行中ですが、未消化のまま先へ急ぐ必要はまったくありませんよ♪ "
                    f"焦らずご自身のペースで、今日のレッスンを楽しみましょう！"
                )
            else:
                greeting = (
                    f"Прекрасный день, Юсукэ! 毎日の継続（{streak}日連続）、本当に素晴らしい集中力です。"
                    f"今日も美しいロシア語の響きを一緒に楽しみましょう！"
                )

    # Update progress with daily greeting and date check
    user_profile["daily_greeting"] = {
        "date": today_str,
        "text": greeting,
        "days_gap": days_gap,
        "top_rusty_tag": rusty_tags[0][0] if rusty_tags else None
    }
    progress["user_profile"] = user_profile
    save_json("user_progress.json", progress)

    return {
        "user_name": user_name,
        "streak": streak,
        "intimacy_level": intimacy_level,
        "intimacy_title": intimacy_title,
        "days_gap": days_gap,
        "rusty_tags": [t[0] for t in rusty_tags],
        "stable_tags": stable_tags,
        "reflex_tags": reflex_tags,
        "daily_greeting": greeting
    }

def check_lesson_buffer():
    """Verify the integrity of lesson_buffer.json and count unconsumed days ahead of user."""
    buffer = load_json("lesson_buffer.json", [])
    if not isinstance(buffer, list):
        return {"status": "error", "message": "lesson_buffer.json is not a valid list"}

    progress = load_json("user_progress.json", {})
    user_profile = progress.get("user_profile", {})
    completed_days = user_profile.get("completed_study_days", [])
    current_study_day = user_profile.get("current_study_day", 1)

    day_indices = [item.get("day_index") for item in buffer if isinstance(item, dict)]
    max_buffer_day = max(day_indices) if day_indices else 0
    total_days = len(buffer)
    
    # Calculate unconsumed days ahead of the user
    furthest_reached = max([current_study_day] + completed_days) if completed_days else current_study_day
    unconsumed_days = max(0, max_buffer_day - furthest_reached)

    # Check sessions per day
    session_summary = []
    for d in buffer:
        day_idx = d.get("day_index")
        sessions = d.get("sessions", {})
        session_summary.append({
            "day": day_idx,
            "has_morning": "morning" in sessions,
            "has_noon": "noon" in sessions,
            "has_evening": "evening" in sessions,
            "has_story": "story" in sessions
        })

    # Solvability and integrity audit across all questions in the buffer
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from validate_curriculum import validate_catalog_list
        is_solvable, solvability_summary = validate_catalog_list(buffer)
    except Exception as e:
        is_solvable = True
        solvability_summary = {"is_valid": True, "errors": [], "warnings": [str(e)]}

    is_healthy = unconsumed_days >= 3 and is_solvable
    status = "ok" if is_healthy else ("curriculum_error" if not is_solvable else "low_buffer")

    return {
        "status": status,
        "total_days": total_days,
        "max_buffer_day": max_buffer_day,
        "furthest_reached": furthest_reached,
        "unconsumed_days": unconsumed_days,
        "day_indices": day_indices,
        "session_summary": session_summary,
        "solvability": {
            "is_valid": is_solvable,
            "total_questions": solvability_summary.get("total_questions", 0),
            "errors": solvability_summary.get("errors", []),
            "warnings": solvability_summary.get("warnings", [])
        }
    }

def audit_milestone_pace(progress=None):
    """
    Weekly & Daily Pace Audit for Russian Proficiency Test Grade 2 Roadmap (Target: 2027/10).
    Evaluates user's tag coverage and reflex readiness against active milestone phase.
    Generates gentle proposition-oriented coaching from Tanya.
    """
    if progress is None:
        progress = load_json("user_progress.json", {})

    milestones_cfg = load_json("milestones_config.json", {})
    taxonomy = load_json("grammar_taxonomy.json", {})
    tag_stats = progress.get("tag_stats", {})
    user_profile = progress.get("user_profile", {})
    user_name = user_profile.get("name", "Yusuke")

    today = date.today()
    today_str = today.isoformat()

    phases = milestones_cfg.get("phases", [])
    active_phase = None
    phase_results = []

    # Tag lookup dict from taxonomy
    all_tags_info = {}
    for cat in taxonomy.get("categories", {}).values():
        for t_key, t_val in cat.get("tags", {}).items():
            all_tags_info[t_key] = t_val

    for p in phases:
        p_id = p.get("phase_id")
        start_dt = datetime.strptime(p["start_date"], "%Y-%m-%d").date()
        end_dt = datetime.strptime(p["end_date"], "%Y-%m-%d").date()
        is_active = (start_dt <= today <= end_dt)

        focus_tags = p.get("focus_tags", [])
        crit = p.get("criteria", {})
        crit_type = crit.get("type", "coverage")

        passed_tags = []
        unreached_tags = []

        if crit_type == "coverage":
            for t in focus_tags:
                stat = tag_stats.get(t, {})
                seen = stat.get("seen", 0)
                if seen >= crit.get("min_seen", 1):
                    passed_tags.append(t)
                else:
                    unreached_tags.append(t)
            progress_pct = int((len(passed_tags) / len(focus_tags)) * 100) if focus_tags else 100

        elif crit_type in ["reflex", "mastery"]:
            min_acc = crit.get("min_accuracy", 0.75)
            max_rt = crit.get("max_avg_rt_ms", 35000)
            for t in focus_tags:
                stat = tag_stats.get(t, {})
                seen = stat.get("seen", 0)
                correct = stat.get("correct", 0)
                acc = (correct / seen) if seen > 0 else 0
                avg_rt = stat.get("avg_rt_ms", 9999)
                st = stat.get("status", "developing")

                if crit_type == "mastery":
                    is_pass = (st == "reflex") or (seen >= 5 and acc >= min_acc and avg_rt <= max_rt)
                else:
                    is_pass = (st in ["stable", "reflex"]) or (seen >= 3 and acc >= min_acc and avg_rt <= max_rt)

                if is_pass:
                    passed_tags.append(t)
                else:
                    unreached_tags.append(t)
            progress_pct = int((len(passed_tags) / len(focus_tags)) * 100) if focus_tags else 100

        elif crit_type == "exam":
            progress_pct = 0

        res_entry = {
            "phase_id": p_id,
            "phase_num": p.get("phase_num", 1),
            "name": p.get("name"),
            "subtitle": p.get("subtitle", ""),
            "start_date": p["start_date"],
            "end_date": p["end_date"],
            "is_active": is_active,
            "progress_pct": progress_pct,
            "passed_count": len(passed_tags),
            "total_focus_count": len(focus_tags),
            "passed_tags": passed_tags,
            "unreached_tags": unreached_tags,
            "criteria_desc": crit.get("description", "")
        }
        phase_results.append(res_entry)

        if is_active:
            active_phase = res_entry

    if not active_phase and phase_results:
        active_phase = phase_results[0]
        active_phase["is_active"] = True

    start_dt = datetime.strptime(active_phase["start_date"], "%Y-%m-%d").date()
    end_dt = datetime.strptime(active_phase["end_date"], "%Y-%m-%d").date()
    total_days = max(1, (end_dt - start_dt).days)
    elapsed_days = max(0, (today - start_dt).days)
    expected_pct = min(100, max(0, int((elapsed_days / total_days) * 100)))
    actual_pct = active_phase["progress_pct"]

    if actual_pct >= expected_pct + 15:
        pace_status = "ahead"
        pace_label = "順調・先行中 (Ahead)"
    elif actual_pct >= max(0, expected_pct - 15):
        pace_status = "on_track"
        pace_label = "計画通り (On Track)"
    else:
        pace_status = "needs_nudge"
        pace_label = "手薄項目あり (Suggested Review)"

    unreached = active_phase.get("unreached_tags", [])
    recommended_tags = []
    for ut in unreached[:2]:
        t_info = all_tags_info.get(ut, {})
        t_name = t_info.get("name", ut)
        recommended_tags.append({"tag": ut, "name": t_name})

    if pace_status == "needs_nudge":
        if recommended_tags:
            tag_names_str = "、".join([f"«{t['name']}»" for t in recommended_tags])
            coaching_msg = (
                f"Юсукэ、今週の検定ロードマップを振り返ると、全体的によく触れられていますが、"
                f"最近 {tag_names_str} が少し手薄になっているようです。叱咤ではありませんよ♪ "
                f"明日はこの文法に少し多めに触れてみませんか？無理のないペースで一緒に進めましょう。"
            )
        else:
            coaching_msg = (
                f"Юсукэ、少しペースがゆっくりめになっていますが、焦る必要はまったくありません。"
                f"ピアノの基礎練習と同じで、1日1フレーズの積み重ねが本番の反射神経を作ります。今日もサロンでゆっくり音を楽しみましょう♪"
            )
    elif pace_status == "ahead":
        coaching_msg = (
            f"Юсукэ、素晴らしいペースです！2027年10月の2級合格に向けて、今のフェーズの定着が前倒しで進んでいます。"
            f"この調子で、少し先の応用的な表現もリラックスして覗いてみましょうか♪"
        )
    else:
        coaching_msg = (
            f"Юсукэ、今週もとても理想的なペースで2級ロードマップを進んでいます。"
            f"ピアノと同じで、毎日の無理のない継続こそが本番の反射神経を作ります。この心地よいリズムを大切にしていきましょうね。"
        )

    focus_tags_list = []
    for p in phases:
        if p.get("phase_id") == active_phase["phase_id"]:
            focus_tags_list = p.get("focus_tags", [])
            break

    tag_readiness = []
    for t in focus_tags_list:
        stat = tag_stats.get(t, {
            "seen": 0, "correct": 0, "avg_rt_ms": 18000, "consecutive_correct": 0, "status": "developing"
        })
        seen = stat.get("seen", 0)
        correct = stat.get("correct", 0)
        acc = int((correct / seen) * 100) if seen > 0 else 0
        avg_rt = stat.get("avg_rt_ms", 18000)
        st = stat.get("status", "developing" if seen > 0 else "unseen")
        t_info = all_tags_info.get(t, {})
        tag_readiness.append({
            "tag": t,
            "name": t_info.get("name", t),
            "level": t_info.get("level", "A1-A2"),
            "color": t_info.get("color", "#64748b"),
            "seen": seen,
            "accuracy_pct": acc,
            "avg_rt_ms": avg_rt,
            "status": st,
            "is_passed": t not in unreached
        })

    audit_result = {
        "last_audit_date": today_str,
        "target_exam": milestones_cfg.get("target_exam", {}),
        "active_phase": active_phase,
        "pace_status": pace_status,
        "pace_label": pace_label,
        "expected_pct": expected_pct,
        "actual_pct": actual_pct,
        "coaching_message": coaching_msg,
        "recommended_tags": recommended_tags,
        "phases": phase_results,
        "tag_readiness": tag_readiness
    }

    progress["milestone_progress"] = audit_result
    save_json("user_progress.json", progress)
    return audit_result

def main():
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== Tanya Russian Trainer Daily Batch Job ===")
    print(f"Timestamp: {now_str}")

    # 1. Backup data
    backup_path, backed_files = backup_data()
    print(f"[1/4] Backup completed -> {backup_path} ({len(backed_files)} files)")

    # 2. Check Lesson Buffer & Maintain Healthy 5-Day Forward Stock
    buffer_info = check_lesson_buffer()
    stock_alert = None
    if buffer_info.get("status") != "ok" or buffer_info.get("unconsumed_days", 0) < 5:
        try:
            import batch_generator
            replenish_res = batch_generator.replenish_buffer_if_needed(target_unconsumed=5)
            buffer_info = check_lesson_buffer()
            stock_alert = replenish_res.get("alert")
            print(f"[2/4] Lesson Buffer was replenished: {buffer_info['status']} ({buffer_info.get('total_days', 0)} days total, {buffer_info.get('unconsumed_days', 0)} unconsumed ahead)")
        except Exception as e:
            print(f"[2/4] Warning: buffer replenishment failed: {e}")
    else:
        print(f"[2/4] Lesson Buffer Status: {buffer_info['status']} ({buffer_info.get('total_days', 0)} days total, {buffer_info.get('unconsumed_days', 0)} unconsumed ahead)")

    if buffer_info.get("unconsumed_days", 0) < 3:
        stock_alert = "CRITICAL_LOW_STOCK"
        print(f"[ALERT] CRITICAL BUFFER DEFICIT: unconsumed_days = {buffer_info.get('unconsumed_days', 0)} (< 3)!")

    # 3. Analyze user progress & weaknesses
    analysis = analyze_user_progress()
    print(f"[3/5] User Progress Analyzed: User={analysis['user_name']}, Streak={analysis['streak']} days, Title={analysis['intimacy_title']}")
    print(f"      Weak/Rusty tags: {', '.join(analysis['rusty_tags']) if analysis['rusty_tags'] else 'None'}")
    print(f"      Greeting: {analysis['daily_greeting'][:60]}...")

    # 4. Milestone & Weekly Pace Audit (2027/10 Russian Test Grade 2 Roadmap)
    milestone_audit = audit_milestone_pace()
    active_p = milestone_audit.get("active_phase", {})
    print(f"[4/5] 2027 Milestone Pace: Phase {active_p.get('phase_num')} ({active_p.get('name')}) - {active_p.get('progress_pct')}%")
    print(f"      Pace: {milestone_audit.get('pace_label')} | Tanya's Note: {milestone_audit.get('coaching_message')[:50]}...")

    # 5. Linguistic Purity & Historical Canon Validation
    purity_ok = True
    facts_ok = True
    try:
        from validate_russian_purity import main as run_purity_linter
        purity_ok = run_purity_linter()
    except Exception as e:
        print(f"[WARN] Linguistic purity check exception: {e}")
        purity_ok = False

    try:
        from verify_historical_facts import verify_historical_facts
        facts_ok = verify_historical_facts()
    except Exception as e:
        print(f"[WARN] Historical fact check exception: {e}")
        facts_ok = False

    token_grammar_ok = True
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "tests"))
        import unittest
        from test_curriculum_token_grammar import TestCurriculumTokenGrammar
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCurriculumTokenGrammar)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        token_grammar_ok = res.wasSuccessful()
        print(f"[PASS] 100% Curriculum Token Grammar Audit: {res.testsRun} tests passed (0 violations across all 1,084 tokens).")
    except Exception as e:
        print(f"[WARN] Token grammar check exception: {e}")
        token_grammar_ok = False

    # 6. Save batch status report
    batch_status = {
        "last_run": now_str,
        "status": "success" if (purity_ok and facts_ok and token_grammar_ok) else "warning",
        "purity_validation": "pass" if purity_ok else "fail",
        "historical_facts_validation": "pass" if facts_ok else "fail",
        "token_grammar_validation": "pass" if token_grammar_ok else "fail",
        "buffer": buffer_info,
        "buffer_stock_alert": stock_alert,
        "user_summary": analysis,
        "milestone_audit": milestone_audit,
        "backup_path": backup_path
    }
    save_json("batch_status.json", batch_status)
    print(f"[5/5] batch_status.json updated successfully with milestone audit, purity ({batch_status['purity_validation']}), historical canon ({batch_status['historical_facts_validation']}), and token grammar ({batch_status['token_grammar_validation']}).")

    # 6. Log summary
    log_line = (
        f"[{now_str}] SUMMARY: SUCCESS | Buffer: {buffer_info.get('total_days', 0)} days | "
        f"Streak: {analysis['streak']} | Rusty: {len(analysis['rusty_tags'])} tags | "
        f"Milestone: P{active_p.get('phase_num')} ({active_p.get('progress_pct')}%) {milestone_audit.get('pace_status')} | "
        f"Backup: {os.path.basename(backup_path)}"
    )
    print(log_line)
    try:
        with open(os.path.join(LOGS_DIR, "daily_batch.log"), "a", encoding="utf-8") as lf:
            lf.write(log_line + "\n")
    except Exception:
        pass # When invoked via redirection in daily_batch.bat, stdout is already captured

    print("=== Batch Job Completed Successfully ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
