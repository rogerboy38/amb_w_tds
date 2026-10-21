"""E-4 (ED2 flip): the pH rule of record is a LINEAR kg-weighted average.

Producción/Alicia ruled 2026-09-07 that pH is combined as a linear mass-weighted
average, so `hplus_avg` stops being the rule and becomes informational. This patch
moves the live rows; the Select option itself stays (Hugh: retire it in a later card,
after these rows are re-verified at zero).

Scope is exactly the three `specification` spellings that mean pH. Anything else is
out of scope by ruling, including `Physicochemical`, which is a group heading.
"""

import frappe

PH_SPECIFICATIONS = (
	"pH",
	"pH (0.5% solution)",
	"Ph* *Determined In A 0.5% Total Solids Solution.",
)


def execute():
	before = frappe.db.count(
		"Item Quality Inspection Parameter",
		{"specification": ("in", PH_SPECIFICATIONS), "custom_blend_method": "hplus_avg"},
	)

	if before:
		frappe.db.sql(
			"""
			UPDATE `tabItem Quality Inspection Parameter`
			SET custom_blend_method = 'mass_avg'
			WHERE specification IN (%s, %s, %s)
			  AND custom_blend_method = 'hplus_avg'
			""",
			PH_SPECIFICATIONS,
		)

	after = frappe.db.count(
		"Item Quality Inspection Parameter",
		{"specification": ("in", PH_SPECIFICATIONS), "custom_blend_method": "hplus_avg"},
	)

	print(f"e4_ph_blend_method_mass_avg: hplus_avg on pH rows {before} -> {after}")

	if after:
		frappe.throw(
			f"E-4 pH flip incomplete: {after} rows still carry hplus_avg on {PH_SPECIFICATIONS}"
		)

	# hplus_avg is single-parameter by measurement (PRE P2: 794 rows, all on 'pH').
	# If it survives anywhere else, the ruling's scope was wrong and that is a stop.
	stray = frappe.db.count(
		"Item Quality Inspection Parameter", {"custom_blend_method": "hplus_avg"}
	)
	if stray:
		frappe.throw(
			f"E-4 pH flip: {stray} hplus_avg rows outside the three pH specifications — "
			"scope of the ruling does not match the data"
		)
