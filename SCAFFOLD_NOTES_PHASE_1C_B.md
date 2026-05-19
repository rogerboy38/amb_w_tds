# Phase 1C-B scaffold notes (V14.3.0)

**STATE**: V14.3.0 promotion COMPLETE per cowork-ops 2026-05-19T02:34Z authorization (Phase 1C-A prod-green ratified, 5/5 comet UI-verify GREEN).

**Author**: claude-sandbox (vm3-ops)
**Date initial scaffold**: 2026-05-18T19:30Z
**Date V14.3.0 promotion**: 2026-05-19T~03:00Z (3 comet pre-commit adjustments applied)
**Branch**: V14.3.0 from V14.1.0 @ `b4dfeea` + this scaffold commit

## What's in V14.3.0 (vs original scaffold)

| File | Purpose | Lines |
|---|---|---|
| `amb_w_tds/public/js/phase_1c_tab.js` | Tree picker (3-level family→sub-group→QIP) + bulk-insert handler with dedupe + singleton/unassigned handling | ~536 |
| `amb_w_tds/public/css/phase_1c_tab.css` | Styling — family/sub-group nesting + Needs Categorization treatment | ~278 |
| `amb_w_tds/SCAFFOLD_NOTES_PHASE_1C_B.md` | This file (integration notes) | — |

## 3 comet pre-commit adjustments applied (vs original scaffold)

Per perplexity-comet's 2026-05-19T01:21Z prod QIP catalog audit:

1. **3-level hierarchy auto-detection** — Family (e.g., "Physicochemical LQD") → Sub-group (e.g., "pH") → QIP. Family detection is fully data-driven: `detectFamilies()` finds common prefixes (>=2 distinct group names share the prefix → that's a family). No hardcoded family names. Adapts to whatever shape the parameter_group catalog presents.

2. **Singleton handling** — Sub-groups with count=1 render inline at family level (no L3 sub-group header). Per comet: avoids "22 single-row sub-tabs each containing 1 QIP" awkwardness. Singletons display with context tag showing their full group name for clarity.

3. **Unassigned bucket** — QIPs with NULL/empty parameter_group render as a separate "Needs Categorization (N)" section at the end of the picker. Visual distinction: dashed orange border + "Alicia review" badge. Hidden in print view (curation queue, not specification content).

## Architectural decisions made in the scaffold

### 1. Used `public/js/` + `doctype_js` hook, NOT the doctype's canonical .js file

**Why**: existing `apps/amb_w_tds/amb_w_tds/amb_w_tds/doctype/tds_product_specification/tds_product_specification.js`
is 175 lines with active handlers (refresh, product_item, tds_version, item_code, before_save) and 8 KB of
helper functions. Replacing or appending in-place risks:
- Clobbering the existing logic (some refs `your_app.quality.doctype.tds_product_specification...`
  look placeholder but I don't know which active code paths use them on prod)
- Merge complexity at integration time

**The canonical Frappe pattern** for adding to an existing DocType's JS without touching its
in-doctype .js file is `doctype_js` hook in `hooks.py`. My scaffold places `phase_1c_tab.js` in
`public/js/` and the 1C-B execution registers via:

```python
# In amb_w_tds/hooks.py
doctype_js = {
    "TDS Product Specification": "public/js/phase_1c_tab.js",
}
```

Frappe loads BOTH `<doctype>.js` (in-doctype canonical) AND any `doctype_js`-registered files
when rendering the form. Calls to `frappe.ui.form.on('TDS Product Specification', {...})` MERGE.

### 2. Zero hardcoded choices (directive §12 architectural rule)

All dropdown options come from `frappe.db.get_doc('Quality Inspection Parameter', name).custom_choices`
split by `\n`. The JS NEVER embeds literal choice strings ("HAZY LIQUID", "CLEAR LIQUID", etc.).

**Verification**: `grep -E "HAZY LIQUID|CLEAR LIQUID|FREE FLOWING|GRANULAR|VISCOUS" public/js/phase_1c_tab.js`
returns **0 matches**.

### 3. Tab schema NOT applied via Customize Form

Per §0 gate, the tab structure (Tab Break + 2 Section Breaks + 2 HTML Fields named
`parameter_picker_html` + `parameter_picker_action_html`) is **NOT yet added to the TDS Product
Specification DocType**. The JS gracefully no-ops when those HTML fields don't exist:

```javascript
const pickerEl = document.getElementById('phase-1c-tree-picker');
if (!pickerEl) return;  // silent no-op
```

This lets the scaffold ship as-is without affecting current form rendering. Real 1C-B execution
adds the tab via Customize Form (or DocType JSON edit) at the actual implementation time.

### 4. Print view handling (§1.3) — partial

The CSS includes `@media print` rules to hide master controls + action bar + group toggles.
The actual title-row hiding in the IQI child table is a Print Format customization that
Frappe expects in the Print Format DocType (not pure CSS-side). **TODO** in the JS file
references this — deferred to 1C-B integration time.

## Integration checklist (for the agent who promotes to V14.3.0)

When Phase 1C-A is prod-green and 1C-B execution begins, the integration steps are:

1. **Branch**: `git checkout -b V14.3.0 V14.1.0` (from current canonical b4dfeea)
2. **Cherry-pick** OR copy this scaffold's 3 files into V14.3.0
3. **Add Tab Break + Section Breaks + HTML fields** to TDS Product Specification via:
   - Customize Form (preferred — exports as fixture)
   - OR DocType JSON edit (if direct manipulation needed)
   Fields per directive §1.1:
   - `parameter_selection_tab` (Tab Break, label `__("Parameter Selection")`)
   - `parameter_picker_section` (Section Break, label "")
   - `parameter_picker_html` (HTML Field, options=`<div id="phase-1c-tree-picker"></div>`)
   - `parameter_picker_action_section` (Section Break, label "")
   - `parameter_picker_action_html` (HTML Field, options=`<div id="phase-1c-action-bar"></div>`)
4. **Register the JS + CSS in `amb_w_tds/hooks.py`**:
   ```python
   doctype_js = {
       "TDS Product Specification": "public/js/phase_1c_tab.js",
   }
   app_include_css = [
       "/assets/amb_w_tds/css/phase_1c_tab.css",
       # ... existing entries
   ]
   ```
5. **Optional**: append the row-level value dropdown render hook (directive §1.2 Note A —
   when an IQI row's `specification` links to a QIP with `custom_choices`, render the row's
   `value` field as a `<select>` instead of `<input>`). This is a separate piece of work
   inside `phase_1c_tab.js` or as a sub-module.
6. **Test on rehearsal substrate** before V14.3.0 commit + push
7. **bench migrate + bench build --app amb_w_tds** to wire the asset paths
8. **Print Format customization** for the IQI table — handle `custom_is_title_row=1` rows
   as bold section headers OR hide them (Alicia's call)

## Open questions for execution time

| # | Question | Suggested answer |
|---|---|---|
| 1 | Tab placement: before or after existing "Parameters" tab? | Directive recommends BEFORE (natural left-to-right workflow). Sandbox's call at execution time. |
| 2 | Row-level value dropdown (§1.2 Note A vs B) | Recommend A (per-row dropdown rendering) for cleaner UX. B (custom modal) is fallback. |
| 3 | Print Format: hide title rows OR show as bold headers? | Alicia's call. Default suggestion: show as bold headers with no row number (clearer than hiding). |
| 4 | Should "Add Selected Parameters" auto-save? | Default NO (let Alicia review before save). Directive section §1.2 also says "frm.save() — optional". |

## Verification at scaffold completion (this session)

```bash
# Confirm scaffold files exist
ls -la apps/amb_w_tds/amb_w_tds/public/js/phase_1c_tab.js
ls -la apps/amb_w_tds/amb_w_tds/public/css/phase_1c_tab.css

# Confirm zero hardcoded choice strings
grep -E "HAZY LIQUID|CLEAR LIQUID|FREE FLOWING|GRANULAR|VISCOUS|FINE POWDER" \
  apps/amb_w_tds/amb_w_tds/public/js/phase_1c_tab.js
# Expected: 0 matches

# Confirm no Frappe API anti-patterns
grep -E "your_app\.quality\.doctype" apps/amb_w_tds/amb_w_tds/public/js/phase_1c_tab.js
# Expected: 0 matches (we don't repeat the existing tds_product_specification.js's
# placeholder Python module references)
```
