# Copyright (c) 2026, AMB Wellness and Contributors
# See license.txt
"""Regression lock for the blend engine, built from a REAL Alicia case.

LORAND F-2886-26 (1200 kg, 2026-09-09) is the first production formulation we
have with her own arithmetic visible in the cells, so the expected values below
are hers (INVENTARIO-LORAND-F-2886-26-1200-KG, Hoja1 K34/L34/M34) — not values
this codebase produced and then blessed. That is the whole point of the lock:
if `mass_avg` ever drifts, it drifts away from what the analyst actually does.

Engine-level by design. `BOM Formula.simulate_blend()` reads COA AMB2 rows from
the database and ends in `self.save()`; the arithmetic under test is the
`engine.blend()` call it delegates to, so the lots are built in memory and
nothing is persisted.

`kg_per_batch` (her F2) is deliberately NOT asserted here — it is G-1b work and
does not exist on this commit; asserting it would manufacture a red that is not
a regression.
"""
import unittest

from amb_w_tds.formulation import engine

# kg · acemannan % · aloína ppm · arsénico ppm — her six selected lots, Σ 1228 kg
LORAND_LINES = [
    ("0803018261",    34, 17.2, 1.2630, 2.02),
    ("0302125251-2",  40, 24.5, 1.3439, 2.57),
    ("0302125251-1", 320, 23.5, 2.2717, 2.42),
    ("0302055261",   500, 22.9, 0.9878, 2.22),
    ("0302220251",    34, 20.7, 1.0593, 1.81),
    ("0301234251",   300,  1.0, 0.3281, 2.06),
]

ACEMANNAN, ALOINA, ARSENICO = "Acemannan", "Aloina", "Arsenico"

# Her spec block: As NMT 3 ppm · Aloína NMT 2 ppm (dry) · Acemannan 15-20 %
SPEC = [
    engine.Parameter(ACEMANNAN, engine.BlendMethod.MASS_AVG,
                     min_value=15.0, max_value=20.0, uom="%"),
    engine.Parameter(ALOINA, engine.BlendMethod.MASS_AVG,
                     max_value=2.0, uom="PPM"),
    engine.Parameter(ARSENICO, engine.BlendMethod.MASS_AVG,
                     max_value=3.0, uom="PPM"),
]

# Hoja1 K34/L34/M34 — Σ(kg×v)/Σkg, "estimación aproximada" in her own label
EXPECTED = {ACEMANNAN: 17.5395, ALOINA: 1.18240, ARSENICO: 2.22754}
TOL = 1e-3


def _lots(lines):
    return [
        engine.Lot(lot_id=lot, mass_kg=kg,
                   values={ACEMANNAN: ace, ALOINA: alo, ARSENICO: ars})
        for lot, kg, ace, alo, ars in lines
    ]


class TestBOMFormulaBlend(unittest.TestCase):
    def test_simulate_blend_lorand_f2886(self):
        """Her three predicted values, reproduced to 1e-3."""
        lots = _lots(LORAND_LINES)
        self.assertEqual(sum(l.mass_kg for l in lots), 1228)

        results = engine.blend(lots, SPEC)

        for name, expected in EXPECTED.items():
            br = results[name]
            self.assertAlmostEqual(
                br.computed_value, expected, delta=TOL,
                msg=f"{name}: mass_avg {br.computed_value} != Alicia's {expected}")
            self.assertTrue(br.in_spec_estimate, f"{name} should be in spec")
            self.assertTrue(br.is_estimate, f"{name} must be flagged an estimate")
            # THE DOOR: release gates on a measured value, so before the lab
            # confirms, release_ok() is None ("Pending") — never a pass.
            self.assertIsNone(br.release_ok(),
                              f"{name} released on an estimate")

    def test_simulate_blend_rejects_out_of_spec_acemannan(self):
        """Negative control, on BOTH bounds.

        Every assertion above is a pass, and a suite that cannot fail cannot
        tell a working spec check from `return True` — the same fail-quiet shape
        that made VM3's first COA differential read clean while every call was
        raising. Acemannan is the one parameter here with a floor AND a ceiling,
        so a one-sided control would leave half the check unproven.
        """
        # Floor: the 500 kg lot carries the blend, so dropping it to 5 % pulls
        # the mean under 15 %.
        low = [l if l[0] != "0302055261" else ("0302055261", 500, 5.0, 0.9878, 2.22)
               for l in LORAND_LINES]
        acemannan = engine.blend(_lots(low), SPEC)[ACEMANNAN]
        self.assertLess(acemannan.computed_value, 15.0)
        self.assertFalse(acemannan.in_spec_estimate,
                         "a blend below the 15 % floor was reported in spec")

        # Ceiling: her lowest lot (1 %) is what holds this blend down; lifting it
        # to 12 % carries the mean past 20 %.
        high = LORAND_LINES[:-1] + [("0301234251-HIGH", 300, 12.0, 0.3281, 2.06)]
        acemannan = engine.blend(_lots(high), SPEC)[ACEMANNAN]
        self.assertGreater(acemannan.computed_value, 20.0)
        self.assertFalse(acemannan.in_spec_estimate,
                         "a blend above the 20 % ceiling was reported in spec")

        # The other two parameters are untouched by both edits and must stay
        # passing: a control that reddens everything proves nothing either.
        self.assertTrue(engine.blend(_lots(high), SPEC)[ALOINA].in_spec_estimate)
        self.assertTrue(engine.blend(_lots(high), SPEC)[ARSENICO].in_spec_estimate)


if __name__ == "__main__":
    unittest.main()
