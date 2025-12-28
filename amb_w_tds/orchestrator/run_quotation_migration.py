import importlib

PIPELINE = [
    "quotation_amb_v14_01_extract",
    "quotation_amb_v14_02_normalize",
    "quotation_amb_v14_03_map_fields",
    "quotation_amb_v14_04_idempotency",
    "quotation_amb_v14_05_sales_partner_resolver",
    "quotation_amb_v14_06_create_header",
    "quotation_amb_v14_07_append_partner_child",
    "quotation_amb_v14_08_append_items",
    "quotation_amb_v14_09_append_taxes",
    "quotation_amb_v14_10_finalize_and_log",
]

def run_quotation_migration(legacy_id: str, dry_run=False):
    """
    Executes Quotation AMB migration flow.
    dry_run=True prevents DB writes after extract + normalize.
    """

    print(f"▶ Starting Quotation AMB migration for {legacy_id}")

    state = {"legacy_id": legacy_id}

    for step in PIPELINE:
        module = importlib.import_module(
            f"app_migrator.pipelines.quotation_amb.{step}"
        )

        func = getattr(module, "run")

        print(f" → executing: {step}")

        if dry_run and step not in [
            "quotation_amb_v14_01_extract",
            "quotation_amb_v14_02_normalize",
            "quotation_amb_v14_03_map_fields",
            "quotation_amb_v14_04_idempotency",
        ]:
            print(f"   (dry run: skipped execution)")
            continue

        state = func(state)

        if state.get("exists"):
            print(f"✓ idempotent existing quotation: {state['existing_name']}")
            return state

    print("✓ migration flow finished successfully")

    if dry_run:
        print("⚠ dry_run enabled: no data written")

    return state
