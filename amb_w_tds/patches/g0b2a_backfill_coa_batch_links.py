"""G-0b-2a leg C — link submitted COAs to their lot root, and the root back.

Batch-driven, per A1 R4: iterate ROOT Batch AMB rows (`parent_batch_amb` blank)
that carry a golden, and find the submitted COAs that belong to them. The
inverse -- iterating COAs and hunting a batch -- is what produced the "9 of 11
ambiguous" reading, because a golden matches many Batch AMB *rows* and exactly
one *lot*.

Rules that are deliberate, not incidental:
  * docstatus == 1 only. Drafts and cancelled COAs are never touched.
  * `batch_reference` is written only where it is BLANK. A COA already pointing
    somewhere is reported and left alone -- including one pointing at a SUBLOT,
    which is a judgement call for Hugh by name, not a silent re-parent.
  * `coa_amb` on the root is written only where blank; `coa_reference` is never
    written (it is the older field, read as a fallback by the reader only).
  * COA AMB2 carries no golden field at all, so it can only be reached by an
    existing `batch_reference`; the golden branch is guarded by doctype.

`db.set_value` bypasses `save_version`, so this log IS the audit record (A1 R5).
It is returned and written to a file so the DoD can carry its sha.
"""
import frappe

FIELDS = ["name", "creation", "batch_reference"]


def _roots_with_golden():
    return frappe.get_all("Batch AMB",
                          filters={"parent_batch_amb": ["in", ["", None]],
                                   "custom_golden_number": ["is", "set"]},
                          fields=["name", "custom_golden_number"])


def plan():
    """Compute the write plan without touching anything. Apply must produce
    exactly this -- 'dry-run == apply plan' is a card assertion, so the two
    cannot be allowed to drift into separate code paths."""
    writes, skipped = [], []
    for root in _roots_with_golden():
        golden = root.custom_golden_number
        cands = {}
        for r in frappe.get_all("COA AMB",
                                filters={"docstatus": 1, "custom_golden_number": golden},
                                fields=FIELDS):
            cands[("COA AMB", r.name)] = r
        for dt in ("COA AMB", "COA AMB2"):
            for r in frappe.get_all(dt, filters={"docstatus": 1, "batch_reference": root.name},
                                    fields=FIELDS):
                cands[(dt, r.name)] = r
        if not cands:
            continue

        for (dt, name), r in sorted(cands.items()):
            if not r.batch_reference:
                writes.append((dt, name, "batch_reference", None, root.name))
            elif r.batch_reference != root.name:
                # points at something else -- very often a SUBLOT of this same
                # lot. Listed by name, never moved.
                skipped.append((dt, name, "batch_reference", r.batch_reference,
                                f"already set (root would be {root.name})"))

        if not frappe.db.get_value("Batch AMB", root.name, "coa_amb"):
            newest = sorted(cands.values(), key=lambda r: r.creation, reverse=True)[0]
            writes.append(("Batch AMB", root.name, "coa_amb", None, newest.name))
    return writes, skipped


def execute(apply=False, log_path=None, commit=False):
    writes, skipped = plan()
    lines = [f"{dt} {name} · {field} · {old!r} -> {new!r}"
             for dt, name, field, old, new in writes]
    lines += [f"SKIPPED {dt} {name} · {field} · {old!r} · {why}"
              for dt, name, field, old, why in skipped]

    if apply:
        for dt, name, field, _old, new in writes:
            frappe.db.set_value(dt, name, field, new)
        # NEVER commit implicitly. This ran inside a caller's
        # begin()/rollback() during testing and the commit punched straight
        # through it, persisting 7 rows into the shared sandbox that the test
        # believed it had rolled back. The caller owns the transaction; a patch
        # that decides to commit on its own removes the only safety a test has.
        if commit:
            frappe.db.commit()

    report = "\n".join([f"# g0b2a backfill — {'APPLY' if apply else 'DRY-RUN'}",
                        f"# writes={len(writes)} skipped={len(skipped)}"] + lines)
    if log_path:
        with open(log_path, "w") as fh:
            fh.write(report + "\n")
    print(report)
    return {"writes": len(writes), "skipped": len(skipped), "log": report}
