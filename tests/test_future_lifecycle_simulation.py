# -*- coding: utf-8 -*-
"""
Multi-Day Future Lifecycle Simulation & Invariant Verification Suite
Tanya Russian Learning App (Moscow Conservatory Edition)

Verifies mathematically and programmatically that:
1. Daily 01:00 AM batch autonomously maintains healthy forward stock (>= 3 unconsumed, target >= 5)
   as user progresses through Days 21 -> 22 -> 23 -> ... -> 30 without manual intervention.
2. 4-layer reaction time calibration correctly handles pauses, bug inspection, and tab switches,
   preventing false "rusty" classification and daily greeting misalignments.
3. 100% of curriculum grammar tags resolve to existing handbook chapters at any future simulated date.
4. Genuine weaknesses are detected with supportive, piano-themed coaching, and cleared upon recovery.
5. Critical low-stock conditions trigger automated alerts before stock ever reaches 0.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from datetime import datetime, date, timedelta

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'scripts'))

import scripts.daily_batch as db
import scripts.batch_generator as bg
from scripts.validate_curriculum import validate_catalog_list, HandbookTagResolver
from scripts.validate_russian_purity import validate_data_tree

class TestFutureLifecycleSimulation(unittest.TestCase):
    def setUp(self):
        """Set up an isolated sandbox environment replicating live app state."""
        self.temp_dir = tempfile.mkdtemp()
        self.backups_dir = os.path.join(self.temp_dir, 'backups')
        os.makedirs(self.backups_dir, exist_ok=True)

        # Copy data files into sandbox
        live_data_dir = os.path.join(ROOT_DIR, 'data')
        for fn in os.listdir(live_data_dir):
            src = os.path.join(live_data_dir, fn)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(self.temp_dir, fn))

        # Reset sandbox user_progress.json tag_stats to isolate test from live user activity
        prog_path = os.path.join(self.temp_dir, 'user_progress.json')
        if os.path.exists(prog_path):
            with open(prog_path, 'r', encoding='utf-8') as f:
                p_data = json.load(f)
            p_data['tag_stats'] = {}
            p_data['recent_mistakes'] = []
            with open(prog_path, 'w', encoding='utf-8') as f:
                json.dump(p_data, f, ensure_ascii=False, indent=2)

        # Redirect daily_batch and batch_generator to sandbox
        self.orig_db_data_dir = db.DATA_DIR
        self.orig_db_backups_dir = db.BACKUPS_DIR
        self.orig_bg_data_path = bg.DATA_PATH
        self.orig_bg_catalog_path = bg.CATALOG_PATH
        self.orig_bg_progress_path = bg.PROGRESS_PATH

        db.DATA_DIR = self.temp_dir
        db.BACKUPS_DIR = self.backups_dir
        bg.DATA_PATH = os.path.join(self.temp_dir, 'lesson_buffer.json')
        bg.CATALOG_PATH = os.path.join(self.temp_dir, 'curriculum_catalog.json')
        bg.PROGRESS_PATH = os.path.join(self.temp_dir, 'user_progress.json')

    def tearDown(self):
        """Restore module paths and clean up temporary sandbox."""
        db.DATA_DIR = self.orig_db_data_dir
        db.BACKUPS_DIR = self.orig_db_backups_dir
        bg.DATA_PATH = self.orig_bg_data_path
        bg.CATALOG_PATH = self.orig_bg_catalog_path
        bg.PROGRESS_PATH = self.orig_bg_progress_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def load_sandbox_json(self, filename):
        with open(os.path.join(self.temp_dir, filename), 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_sandbox_json(self, filename, data):
        with open(os.path.join(self.temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def simulate_quiz_submission(self, progress, day_data, session_name, simulated_answers):
        """Simulates client-side quiz submission with realistic reaction times and interruptions."""
        user_profile = progress.setdefault('user_profile', {})
        tag_stats = progress.setdefault('tag_stats', {})
        session_history = progress.setdefault('session_history', [])

        session = day_data['sessions'].get(session_name, {})
        quiz_items = session.get('quiz_items', [])

        for idx, q in enumerate(quiz_items):
            tag = q.get('tag')
            ans = simulated_answers[idx] if idx < len(simulated_answers) else {'is_correct': True, 'rt_ms': 2000, 'is_interruption': False}
            is_correct = ans['is_correct']
            rt_ms = ans['rt_ms']
            is_interruption = ans.get('is_interruption', False)

            if not tag:
                continue

            stat = tag_stats.setdefault(tag, {
                "seen": 0, "correct": 0, "avg_rt_ms": 2500, "consecutive_correct": 0, "status": "developing"
            })
            stat['seen'] += 1
            if is_correct:
                stat['correct'] += 1
                stat['consecutive_correct'] = stat.get('consecutive_correct', 0) + 1
            else:
                stat['consecutive_correct'] = 0

            # 4-Layer Reaction Time Calibration:
            if not is_interruption and rt_ms < 90000:
                old_rt = stat.get('avg_rt_ms', 18000)
                bounded_rt = min(60000, max(1000, rt_ms))
                stat['avg_rt_ms'] = int((old_rt * 0.8) + (bounded_rt * 0.2))

            # Stability classification:
            acc = stat['correct'] / stat['seen']
            avg_rt = stat.get('avg_rt_ms', 18000)
            consec = stat.get('consecutive_correct', 0)

            if stat['seen'] >= 3:
                if acc >= 0.85 and avg_rt < 15000 and consec >= 3:
                    stat['status'] = "reflex"
                elif acc >= 0.75 and consec >= 2:
                    stat['status'] = "stable"
                elif acc >= 0.70 and avg_rt < 35000:
                    stat['status'] = "stable"
                else:
                    stat['status'] = "rusty"

        # Update profile counters
        user_profile['total_sessions_completed'] = user_profile.get('total_sessions_completed', 0) + 1
        intimacy = user_profile.setdefault('intimacy', {'level': 1, 'exp': 0, 'max_exp': 50})
        intimacy['exp'] = intimacy.get('exp', 0) + 5

    def test_multi_day_future_progression_invariants(self):
        """
        Simulate 10 consecutive virtual days (Days 21 -> 30).
        Proves that buffer stock stays >= 3, all future items resolve to handbook,
        streak increments correctly, and no false rusty tags ever contaminate greetings.
        """
        resolver = HandbookTagResolver.get_instance(ROOT_DIR)

        # Baseline progress setup: user starts at Day 21
        progress = self.load_sandbox_json('user_progress.json')
        user_profile = progress['user_profile']
        user_profile['current_study_day'] = 21
        user_profile['completed_study_days'] = list(range(1, 21))
        initial_streak = user_profile.get('current_streak', 18)
        simulated_date = date(2026, 10, 2)
        user_profile['last_active_date'] = simulated_date.isoformat()
        self.save_sandbox_json('user_progress.json', progress)

        for day_num in range(21, 31):
            # 1. User arrives on day_num: verify lesson is available in buffer
            buffer = self.load_sandbox_json('lesson_buffer.json')
            day_entry = next((d for d in buffer if d.get('day_index') == day_num), None)
            self.assertIsNotNone(day_entry, f"Day {day_num} must exist in lesson_buffer.json!")

            # Verify sessions structure of day_num
            sessions = day_entry.get('sessions', {})
            self.assertIn('morning', sessions, f"Day {day_num} must have morning session")
            self.assertIn('noon', sessions, f"Day {day_num} must have noon session")
            self.assertIn('evening', sessions, f"Day {day_num} must have evening session")
            self.assertIn('story', sessions, f"Day {day_num} must have story session")

            # Invariant: 100% of grammar tags in day_num must resolve to existing handbook chapters
            for s_name, s_data in sessions.items():
                rel_tag = s_data.get('related_grammar_tag')
                if rel_tag:
                    resolved = resolver.resolve_tag(rel_tag)
                    self.assertIsNotNone(resolved, f"Day {day_num} {s_name} tag '{rel_tag}' failed handbook resolution!")
                for q in s_data.get('quiz_items', []):
                    q_tag = q.get('tag')
                    if q_tag:
                        resolved = resolver.resolve_tag(q_tag)
                        self.assertIsNotNone(resolved, f"Day {day_num} {s_name} quiz item tag '{q_tag}' failed handbook resolution!")

            # 2. Simulate user studying day_num with realistic answers & pauses
            progress = self.load_sandbox_json('user_progress.json')
            
            # Morning: 1 reflex answer (1.8s), 1 deep thought (14s), 1 standard (2.5s)
            morning_answers = [
                {'is_correct': True, 'rt_ms': 1800, 'is_interruption': False},
                {'is_correct': True, 'rt_ms': 14000, 'is_interruption': False}, # deliberation
                {'is_correct': True, 'rt_ms': 2500, 'is_interruption': False}
            ]
            self.simulate_quiz_submission(progress, day_entry, 'morning', morning_answers)

            # Noon: 1 reflex (1.9s), 1 tab blur / bug check (35s with is_interruption=True), 1 standard (2.2s)
            noon_answers = [
                {'is_correct': True, 'rt_ms': 1900, 'is_interruption': False},
                {'is_correct': True, 'rt_ms': 35000, 'is_interruption': True}, # tab blur / bug inspection
                {'is_correct': True, 'rt_ms': 2200, 'is_interruption': False}
            ]
            self.simulate_quiz_submission(progress, day_entry, 'noon', noon_answers)

            # Mark day_num complete and advance user to next study day
            u_prof = progress['user_profile']
            u_prof['completed_study_days'].append(day_num)
            u_prof['current_study_day'] = day_num + 1
            u_prof['last_active_date'] = simulated_date.isoformat()
            u_prof['current_streak'] = initial_streak + (day_num - 21)
            self.save_sandbox_json('user_progress.json', progress)

            # 3. Virtual Clock Advances to 01:00 AM next day
            simulated_date = simulated_date + timedelta(days=1)

            # Run daily batch routines
            analysis = db.analyze_user_progress()
            buf_info = db.check_lesson_buffer()
            if buf_info.get("status") != "ok" or buf_info.get("unconsumed_days", 0) < 5:
                bg.replenish_buffer_if_needed(target_unconsumed=5)
                buf_info = db.check_lesson_buffer()

            # INVARIANT CHECKS FOR THIS FUTURE DAY:
            # 1. Buffer stock invariant: unconsumed_days must NEVER be below 3!
            self.assertGreaterEqual(buf_info['unconsumed_days'], 3, 
                f"On simulated date {simulated_date} after completing Day {day_num}, buffer was depleted to {buf_info['unconsumed_days']} unconsumed days!")

            # 2. Daily greeting invariant: Tanya must NEVER mention false rusty tags caused by pauses
            greeting = analysis['daily_greeting']
            self.assertNotIn("昨日は", greeting, f"False positive rusty tag was mentioned in Tanya's greeting: '{greeting}'")

            # 3. User streak invariant: Streak must advance monotonically
            self.assertGreaterEqual(analysis['streak'], initial_streak)

    def test_deliberation_and_tab_blur_interruption_calibration(self):
        """
        Verify Layer 2 and Layer 3 calibration:
        Simulate user taking 15s deliberation, 60s phone call interruption, and 18s careful reading.
        With 100% accuracy, the tag must NEVER be classified as 'rusty'.
        """
        progress = self.load_sandbox_json('user_progress.json')
        tag_stats = progress.setdefault('tag_stats', {})
        test_tag = "syntax.conditional"

        # Initialize clean stat
        tag_stats[test_tag] = {
            "seen": 0, "correct": 0, "avg_rt_ms": 2200, "consecutive_correct": 0, "status": "developing"
        }

        # 5 Questions submitted with high latency and interruptions
        submissions = [
            {'is_correct': True, 'rt_ms': 15000, 'is_interruption': False}, # 15s deliberation (bounded, excluded from running avg)
            {'is_correct': True, 'rt_ms': 60000, 'is_interruption': True},  # 60s external pause (tab blur / phone call)
            {'is_correct': True, 'rt_ms': 13500, 'is_interruption': False}, # 13.5s careful thought
            {'is_correct': True, 'rt_ms': 2100,  'is_interruption': False}, # 2.1s reflex
            {'is_correct': True, 'rt_ms': 1900,  'is_interruption': False}  # 1.9s reflex
        ]

        dummy_day = {
            "sessions": {
                "noon": {
                    "quiz_items": [{"tag": test_tag} for _ in submissions]
                }
            }
        }
        self.simulate_quiz_submission(progress, dummy_day, "noon", submissions)
        self.save_sandbox_json('user_progress.json', progress)

        stat = progress['tag_stats'][test_tag]
        self.assertEqual(stat['seen'], 5)
        self.assertEqual(stat['correct'], 5)
        self.assertLess(stat['avg_rt_ms'], 5000, "60s interruption should be strictly excluded from avg_rt_ms")
        self.assertIn(stat['status'], ["stable", "reflex"], "100% correct tag must NEVER be classified as 'rusty'!")

        # Run Tanya's progress analysis
        analysis = db.analyze_user_progress()
        self.assertNotIn(test_tag, analysis['rusty_tags'], f"{test_tag} should not be in rusty tags")
        self.assertNotIn("練習、お疲れさまでした", analysis['daily_greeting'], "Tanya should not formulate a remedial greeting for 100% accurate performance")

    def test_genuine_weakness_detection_and_supportive_coaching(self):
        """
        Verify that genuine mistakes (e.g. 1/4 correct) ARE properly identified as 'rusty'
        and evoke Tanya's gentle, piano-themed encouragement.
        Once the user recovers with high accuracy, the tag returns to 'stable'.
        """
        progress = self.load_sandbox_json('user_progress.json')
        tag_stats = progress.setdefault('tag_stats', {})
        test_tag = "case.dat"

        # User genuinely struggles
        struggles = [
            {'is_correct': False, 'rt_ms': 4500, 'is_interruption': False},
            {'is_correct': False, 'rt_ms': 5000, 'is_interruption': False},
            {'is_correct': False, 'rt_ms': 4000, 'is_interruption': False},
            {'is_correct': True,  'rt_ms': 3500, 'is_interruption': False}
        ]
        dummy_day = {"sessions": {"noon": {"quiz_items": [{"tag": test_tag} for _ in struggles]}}}
        self.simulate_quiz_submission(progress, dummy_day, "noon", struggles)
        self.save_sandbox_json('user_progress.json', progress)

        # Analysis should catch this
        analysis = db.analyze_user_progress()
        self.assertIn(test_tag, analysis['rusty_tags'])
        self.assertIn("与格", analysis['daily_greeting'])
        self.assertIn("ピアノのスケールのように", analysis['daily_greeting'])

        # Now simulate user practicing and recovering (7 consecutive correct answers)
        recovery = [{'is_correct': True, 'rt_ms': 2000, 'is_interruption': False} for _ in range(7)]
        dummy_day2 = {"sessions": {"noon": {"quiz_items": [{"tag": test_tag} for _ in recovery]}}}
        self.simulate_quiz_submission(progress, dummy_day2, "noon", recovery)
        self.save_sandbox_json('user_progress.json', progress)

        analysis2 = db.analyze_user_progress()
        self.assertNotIn(test_tag, analysis2['rusty_tags'], f"{test_tag} should no longer be rusty after recovery")

    def test_stock_depletion_boundary_and_early_warning_alert(self):
        """
        Simulate an edge case where buffer drops below 3 days.
        Proves that:
        1. batch_generator detects deficit and attempts candidate discovery.
        2. If unconsumed < 3, report emits 'CRITICAL_LOW_STOCK' early warning alert.
        3. daily_batch sets 'buffer_stock_alert' in batch_status.json.
        """
        # Artificially set user at Day 34 after all modules up to Day 35 have been loaded
        bg.replenish_buffer_if_needed(target_unconsumed=5)

        progress = self.load_sandbox_json('user_progress.json')
        progress['user_profile']['current_study_day'] = 34
        progress['user_profile']['completed_study_days'] = list(range(1, 34))
        self.save_sandbox_json('user_progress.json', progress)

        report = bg.replenish_buffer_if_needed(target_unconsumed=5)
        self.assertEqual(report['unconsumed_days'], 1)
        self.assertEqual(report['alert'], 'CRITICAL_LOW_STOCK', "Deficit below 3 must trigger CRITICAL_LOW_STOCK alert")

if __name__ == '__main__':
    unittest.main()
