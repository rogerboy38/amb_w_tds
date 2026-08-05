"""Lane 6 — the substrate discriminator.

ONE predicate for powder/liquid, sourced from the 2023 Quality catalogue.

WHY THIS EXISTS
    Four other predicates were in use and they disagree:
      * the print template's name tokens (POWDER | SPRAY DRIED | 200:1) --
        measured to misclassify 214 of 810 TDS rows (26%), every sampled
        disagreement powder -> liquid.  Its inputs are also mutable by an
        unrelated action: the Item -> TDS client script rewrites item_name and
        item_code, so renaming an Item can flip a certificate's family.
      * Item.substrate -- correct where populated, empty on 722 of 1774 Items.
      * Item.custom_concentration_type -- never contradicts substrate, but is a
        refinement, not a phase signal (PWD appears with 200X and with empty).
      * item_group -- some groups are phase-pure, some are not.

    v3.0 instructed "lift the discriminator from COA AMB FoxPro".  That
    instruction was withdrawn on the 26% measurement: the template is the copy
    that should eventually be lifted TO, not FROM.

THE RULE (from the catalogue's own meta, and verified against its data)
    familia 07                  -> LIQUIDO      (all 16 of its codes)
    every other familia 03-13   -> POLVO        (508 codes)
    familia 02                  -> DEPRECATED   -> raise
    familias 14+                -> per Item Group, NEVER by prefix -> raise
                                   (1607 is Products Liquid inside powder
                                    family 16 -- one counterexample is enough)

DESIGN CONSTRAINTS, from the Lane 6 order
    * Read the published JSON.  Do NOT hardcode the 524 codes -- if the
      catalogue is regenerated this module must not need editing.
    * Family bands explicit, else: RAISE.  Never guess, never fall back to a
      name heuristic; an unresolved code is a question for Quality, not a
      default.

Source of truth: Nuevos Codigos 2023.xlsx (Alicia / Calidad).
Catalogue artefact sha256:
  b31282b84ef9a543f05423dc29ee930174a84671000663e89a593309ce2fea92
"""

import json
import os

import frappe

POWDER = "POLVO"
LIQUID = "LIQUIDO"

# Family bands, explicit. Anything outside these bands raises.
LIQUID_FAMILIES = {"07"}
POWDER_FAMILIES = {"03", "04", "05", "06", "08", "09", "10", "11", "12", "13"}
DEPRECATED_FAMILIES = {"02"}

_CACHE = {}


class SubstrateUnresolved(Exception):
	"""Raised when a code cannot be classified from the catalogue.

	Deliberately an exception rather than a default: a wrong classification is
	invisible on a certificate, an exception is not.
	"""


def _catalogue():
	if "codes" not in _CACHE:
		path = os.path.join(
			os.path.dirname(os.path.abspath(__file__)), "..", "data", "catalogo_2023.json"
		)
		with open(os.path.abspath(path), encoding="utf-8") as fh:
			doc = json.load(fh)
		_CACHE["codes"] = doc["codes"]
		_CACHE["meta"] = doc.get("meta", {})
	return _CACHE["codes"]


def catalogue_meta():
	_catalogue()
	return dict(_CACHE.get("meta") or {})


def product_code(value):
	"""The 4-character product code at the head of an item code or product key.

	'0307'                     -> '0307'
	'0307-ABSARA'              -> '0307'
	'0227-1X- Fair Trade-...'  -> '0227'
	'0722002251'               -> None      <- NOT '0722'

	That last case is the whole point. A 10-digit lot code begins with four
	digits that look exactly like a product code, and blindly truncating it
	yields a confident wrong answer: 0722002251 -> '0722' -> family 07 ->
	LIQUIDO, on a row whose substrate is PWDF. Measured on three live Items
	before this guard existed.

	So: the four digits must be the WHOLE token -- either the entire string, or
	followed by a non-digit separator. A fifth digit means this is not a product
	code and we do not know what it is, which is a raise, not a guess.
	"""
	if not value:
		return None
	s = str(value).strip()
	head = s[:4]
	if not (len(head) == 4 and head.isdigit()):
		return None
	if len(s) > 4 and s[4].isdigit():
		return None  # 5+ leading digits -> a lot code, not a product code
	return head


def classify_code(code):
	"""POLVO / LIQUIDO for a 4-digit product code. Raises if unresolved."""
	code = product_code(code)
	if not code:
		raise SubstrateUnresolved("not a 4-digit product code: %r" % code)

	entry = _catalogue().get(code)
	if entry and entry.get("fase"):
		return entry["fase"]

	family = code[:2]
	if family in DEPRECATED_FAMILIES:
		raise SubstrateUnresolved(
			"code %s is family %s (deprecated); classification is a business ruling, not a lookup"
			% (code, family)
		)
	if family in LIQUID_FAMILIES:
		return LIQUID
	if family in POWDER_FAMILIES:
		return POWDER
	raise SubstrateUnresolved(
		"code %s is family %s: families 14+ are assigned per Item Group, never by prefix "
		"(1607 is Products Liquid inside powder family 16). Resolve from the Item, or raise to Quality."
		% (code, family)
	)


def classify_item(item_code):
	"""Classify an Item. Prefers the catalogue; falls back to NOTHING."""
	if not item_code:
		raise SubstrateUnresolved("no item_code given")
	pk = frappe.db.get_value("Item", item_code, "product_key") if frappe.db.exists("Item", item_code) else None
	for candidate in (pk, item_code):
		code = product_code(candidate)
		if code:
			return classify_code(code)
	raise SubstrateUnresolved("cannot derive a 4-digit product code from %r" % item_code)


def is_powder(value):
	return classify_code(value) == POWDER
