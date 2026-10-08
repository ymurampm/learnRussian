"""
Batch Lesson Generator and Buffer Replenisher for Tanya Russian Learning App
Maintains a robust multi-day buffer of rich 5-minute lessons:
- Morning (New Input + Exploration + Mutator)
- Noon (Weakness / Speed Check with Hero Sentence & Focus)
- Evening (Listening Immersion / Non-graded bath)
- Story (Tanya's Moscow Conservatory Memoir)

Saves to data/lesson_buffer.json
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "lesson_buffer.json")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "curriculum_catalog.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "data", "user_progress.json")

def load_json_file(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading {path}: {e}")
    return default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def replenish_buffer_if_needed(target_unconsumed=5):
    """
    Checks unconsumed buffer days relative to the user's progress.
    If unconsumed days < target_unconsumed, populates from catalog.
    Returns dict with replenishment report.
    """
    buffer = load_json_file(DATA_PATH, [])
    catalog = load_json_file(CATALOG_PATH, [])
    progress = load_json_file(PROGRESS_PATH, {})

    user_profile = progress.get("user_profile", {}) if isinstance(progress, dict) else {}
    current_study_day = user_profile.get("current_study_day", 1)
    completed_days = user_profile.get("completed_study_days", [])

    furthest_done = max([current_study_day] + completed_days) if completed_days else current_study_day

    buffer_indices = {d.get("day_index") for d in buffer if isinstance(d, dict)}
    max_buffer_day = max(buffer_indices) if buffer_indices else 0
    unconsumed = max(0, max_buffer_day - furthest_done)

    # Import automated solvability validator
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from validate_curriculum import validate_day_data
    except ImportError:
        validate_day_data = None

    replenished = []
    rejected = []
    for day in catalog:
        day_idx = day.get("day_index")
        if day_idx not in buffer_indices:
            if validate_day_data:
                is_valid, errors, _ = validate_day_data(day, day_idx)
                if not is_valid:
                    print(f"[BLOCKED] Day {day_idx} failed solvability validation and was blocked from buffer: {errors}")
                    rejected.append({"day": day_idx, "errors": errors})
                    continue

            buffer.append(day)
            buffer_indices.add(day_idx)
            replenished.append(day_idx)

    if replenished:
        buffer.sort(key=lambda d: d.get("day_index", 0))
        save_json_file(DATA_PATH, buffer)
        max_buffer_day = max(buffer_indices)
        unconsumed = max(0, max_buffer_day - furthest_done)

    # If unconsumed is still below target, scan candidate generator modules in scripts/
    if unconsumed < target_unconsumed:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_days = []
        for fn in sorted(os.listdir(scripts_dir)):
            if fn.startswith("generate_days_") and fn.endswith(".py"):
                mod_name = fn[:-3]
                try:
                    import importlib
                    mod = importlib.import_module(mod_name)
                    for attr in dir(mod):
                        val = getattr(mod, attr)
                        if isinstance(val, list) and val and isinstance(val[0], dict) and "day_index" in val[0]:
                            for d in val:
                                d_idx = d.get("day_index")
                                if d_idx and d_idx not in buffer_indices:
                                    candidate_days.append(d)
                except Exception as e:
                    print(f"[WARN] Could not inspect generator module {mod_name}: {e}")

        # Validate candidate days before applying
        catalog_indices = {d.get("day_index") for d in catalog if isinstance(d, dict)}
        newly_added = []
        for c_day in candidate_days:
            c_idx = c_day.get("day_index")
            if c_idx not in buffer_indices:
                if validate_day_data:
                    is_valid, errors, _ = validate_day_data(c_day, c_idx)
                    if not is_valid:
                        print(f"[BLOCKED] Candidate Day {c_idx} failed validation: {errors}")
                        rejected.append({"day": c_idx, "errors": errors})
                        continue

                buffer.append(c_day)
                buffer_indices.add(c_idx)
                replenished.append(c_idx)
                newly_added.append(c_day)
                if c_idx not in catalog_indices:
                    catalog.append(c_day)
                    catalog_indices.add(c_idx)

        if newly_added:
            catalog.sort(key=lambda d: d.get("day_index", 0))
            buffer.sort(key=lambda d: d.get("day_index", 0))
            save_json_file(CATALOG_PATH, catalog)
            save_json_file(DATA_PATH, buffer)
            max_buffer_day = max(buffer_indices)
            unconsumed = max(0, max_buffer_day - furthest_done)
            print(f"[AUTO-REPLENISH] Discovered and integrated {len(newly_added)} days into catalog and buffer.")

    # Low-stock early warning invariant
    alert = None
    if unconsumed < 3:
        alert = "CRITICAL_LOW_STOCK"
        print(f"[ALERT] CRITICAL LOW BUFFER STOCK: Only {unconsumed} unconsumed days remaining ahead of Day {furthest_done}! Target is >= {target_unconsumed}.")

    return {
        "total_buffer_days": len(buffer),
        "max_buffer_day": max_buffer_day,
        "furthest_reached": furthest_done,
        "unconsumed_days": unconsumed,
        "replenished_days": replenished,
        "rejected_days": rejected,
        "is_healthy": unconsumed >= 3 and len(rejected) == 0,
        "alert": alert
    }

def main():
    report = replenish_buffer_if_needed(target_unconsumed=5)
    print(f"=== Buffer Generator Status ===")
    print(f"Total buffer days: {report['total_buffer_days']} (max day: {report['max_buffer_day']})")
    print(f"User furthest day: {report['furthest_reached']}")
    print(f"Unconsumed days ahead: {report['unconsumed_days']}")
    if report['replenished_days']:
        print(f"Replenished days: {report['replenished_days']}")
    if report.get('rejected_days'):
        print(f"❌ BLOCKED/REJECTED DAYS: {report['rejected_days']}")
    print(f"Health: {'HEALTHY' if report['is_healthy'] else 'WARNING'}")
    return 0 if report['is_healthy'] else 1

if __name__ == "__main__":
    sys.exit(main())
