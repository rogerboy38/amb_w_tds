import json
from amb_w_tds.orchestrator.run_quotation_migration import run_quotation_migration

def read_failed():
    failed = []
    with open("sites/private/migration_state.jsonl") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("status") == "failed":
                failed.append(entry["legacy_id"])
    return failed

def resume_failed(limit=50, dry_run=False):
    failed = read_failed()[:limit]
    print(f"Resuming {len(failed)} failed migrations")

    for legacy_id in failed:
        try:
            run_quotation_migration(legacy_id, dry_run=dry_run)
        except Exception as e:
            print(f"❌ retry failed: {legacy_id} -> {e}")
            continue

    print("Resume complete.")
