"""13.11.2 BOM naming that counts amendments: the logic half, DB-free."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from amb_w_tds.formulation.bom_naming import next_bom_name  # noqa: E402

# the measured shape: 003 and 006 are amendments that took plain numbers; three hand-named BOMs;
# another item whose code starts with the same digits; a -N amend-counter name.
NAMES = ["BOM-0307-001", "BOM-0307-002", "BOM-0307-003", "BOM-0307-004", "BOM-0307-005", "BOM-0307-006",
	"BOM-0307-FG-FINAL", "BOM-0307-CUNETE-PACK", "BOM-0307-MIX-A030X", "BOM-03071-009", "BOM-0307-004-1"]


class TestNextBomName(unittest.TestCase):
	def test_counts_amendments_so_006_is_not_reproposed(self):
		self.assertEqual(next_bom_name("0307", NAMES), "BOM-0307-007")

	def test_ignores_hand_names_other_items_and_amend_suffixes(self):
		# FG-FINAL etc. are not BOM-0307-<digits>; BOM-03071-009 is another item; -004-1 is an amendment suffix
		self.assertEqual(next_bom_name("0307", ["BOM-0307-FG-FINAL", "BOM-03071-009", "BOM-0307-004-1"]), "BOM-0307-001")

	def test_first_bom_and_width(self):
		self.assertEqual(next_bom_name("X1", []), "BOM-X1-001")
		self.assertEqual(next_bom_name("X1", ["BOM-X1-0099"]), "BOM-X1-0100")

	def test_item_codes_with_regex_characters(self):
		self.assertEqual(next_bom_name("A.B+C", ["BOM-A.B+C-002", "BOM-AxB+C-009"]), "BOM-A.B+C-003")


if __name__ == "__main__":
	unittest.main()
