"""Lane 6 discriminator — the cases that must never regress.

The truncation case is the reason this file exists: before the guard,
'0722002251' resolved to LIQUIDO because its first four digits look like
family 07. Three live Items were classified wrongly and confidently.
"""

import unittest

from amb_w_tds.classification import substrate as S


class TestSubstrateDiscriminator(unittest.TestCase):
	def test_powder_families_resolve(self):
		for code in ("0301", "0401", "0501", "0601", "0801", "0901", "1001", "1101", "1201", "1301"):
			self.assertEqual(S.classify_code(code), S.POWDER, code)

	def test_family_07_is_the_only_liquid(self):
		for code in ("0701", "0705", "0716"):
			self.assertEqual(S.classify_code(code), S.LIQUID, code)

	def test_variant_suffix_still_resolves(self):
		self.assertEqual(S.classify_code("0307-ABSARA"), S.POWDER)
		self.assertEqual(S.classify_code("0705 TDS BASE"), S.LIQUID)

	def test_lot_code_must_raise_not_truncate(self):
		# THE REGRESSION GUARD. '0722002251'[:4] == '0722' -> family 07 -> LIQUIDO,
		# on rows whose substrate is PWDF. A fifth leading digit means lot, not product.
		for lot in ("0722002251", "0729246241", "0201071211", "0638251241"):
			with self.assertRaises(S.SubstrateUnresolved, msg=lot):
				S.classify_code(lot)

	def test_deprecated_family_02_raises(self):
		with self.assertRaises(S.SubstrateUnresolved):
			S.classify_code("0227")

	def test_families_14_plus_raise_never_guess(self):
		# 1607 is Products Liquid inside powder family 16 — one counterexample is enough.
		with self.assertRaises(S.SubstrateUnresolved):
			S.classify_code("1607")

	def test_garbage_raises(self):
		for bad in ("", None, "abcd", "12", "0"):
			with self.assertRaises(S.SubstrateUnresolved):
				S.classify_code(bad)

	def test_catalogue_rule_reproduces_from_its_own_data(self):
		codes = S._catalogue()
		self.assertEqual(len(codes), 524)
		liquid_families = {v["familia"] for v in codes.values() if v["fase"] == S.LIQUID}
		self.assertEqual(liquid_families, {"07"})
		self.assertTrue(all(v["fase"] == S.POWDER for v in codes.values() if v["familia"] != "07"))
