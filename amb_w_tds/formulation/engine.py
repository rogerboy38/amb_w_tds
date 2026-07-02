"""
AMB Wellness — Formulation Engine (Stage-One Orchestrator core)
================================================================
Framework-agnostic pure-Python engine. Unit-testable standalone; drops into the
ERPNext `BOM Formula` controller (Mix tab) via a thin Frappe whitelisted wrapper.

Grounded in:
  - Legacy FoxPro "Memoria de Cálculo" mass-balance model
        (foxpro-bom-engine-mem-cal-2026-07-01.md)
  - Best-practice research
        (formulation-best-practices-research-2026-07-01.md)
  - Engineering sign-off 2026-07-01 — "THE DOOR": every value the system computes
        is an ESTIMATE; the lab tests the ACTUAL homogenized blend and confirms /
        overrides; the MEASURED value is what gates release (predict -> measure -> confirm).

Two parts:
  A) MassBalance  — the 3-level BOM yield model (Penca -> Concentrate -> Powder -> Mix)
  B) BlendSolver  — per-parameter blend rules + "the door" + TDS compliance
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import log10
from typing import Optional, Dict, List, Union

# =====================================================================================
# A) MASS BALANCE — the FoxPro Memoria de Cálculo model (verified vs real FOLIOs)
# =====================================================================================

def juice_to_concentrate(penca_kg: float, rjbp: float = 0.80, rendjf: float = 0.98,
                         st_decolorized: float = 1.5, st_target: float = 13.0,
                         rc: float = 0.96) -> dict:
    """Penca -> jugo bruto -> jugo filtrado/decolorado -> concentrado (0227).
    JB = P*RJBP ; Filtered = JB*RENDJF ; Concentrate = Filtered*(STdecol/STtarget)*RC.
    Yields default to the FoxPro observed values."""
    jugo_bruto = penca_kg * rjbp
    filtered = jugo_bruto * rendjf
    concentrate = filtered * (st_decolorized / st_target) * rc
    return {"penca_kg": penca_kg, "jugo_bruto_kg": jugo_bruto,
            "filtered_kg": filtered, "concentrate_kg": concentrate,
            "st_target_pct": st_target}


def concentrate_to_powder(concentrate_kg: float, st_conc_pct: float,
                          dry_yield: float = 0.857, st_powder_pct: float = 100.0) -> dict:
    """Concentrate -> spray-dried powder (030X).
    Powder = ConcMass * (STconc/STpowder) * RP.  RP (dry yield) default = FoxPro median 0.857."""
    powder = concentrate_kg * (st_conc_pct / st_powder_pct) * dry_yield
    return {"concentrate_kg": concentrate_kg, "st_conc_pct": st_conc_pct,
            "dry_yield": dry_yield, "powder_kg": powder}


def powder_to_mix(powder_kg: float, pct_powder: float, pct_excipient: float,
                  cunete_kg: float = 25.0) -> dict:
    """Powder + excipient -> mix (0307/QX), packed in cuñetes.
    Excipient = Powder*(pct_exc/pct_powder) ; Mix = Powder+Excipient ; Cuñetes = Mix/cunete."""
    if pct_powder <= 0:
        raise ValueError("pct_powder must be > 0")
    excipient = powder_kg * (pct_excipient / pct_powder)
    mix = powder_kg + excipient
    return {"powder_kg": powder_kg, "excipient_kg": excipient, "mix_kg": mix,
            "pct_powder": pct_powder, "pct_excipient": pct_excipient,
            "cunetes": mix / cunete_kg, "cunete_kg": cunete_kg}


def standardize_with_carrier(native_mass_kg: float, native_marker_pct: float,
                             target_marker_pct: float) -> dict:
    """Standardize potency by DILUTING a concentrated extract down to a target marker %.
    carrier_kg = native_mass*(native/target - 1).  (Best-practice: X:1 is input-side only;
    the marker % is the real guarantee.)  Only valid when native >= target."""
    if target_marker_pct <= 0 or native_marker_pct < target_marker_pct:
        raise ValueError("target must be >0 and <= native marker %")
    carrier_kg = native_mass_kg * (native_marker_pct / target_marker_pct - 1.0)
    final_mass = native_mass_kg + carrier_kg
    return {"native_mass_kg": native_mass_kg, "carrier_kg": carrier_kg,
            "final_mass_kg": final_mass, "final_marker_pct": target_marker_pct}


# =====================================================================================
# B) BLEND SOLVER — per-parameter rules + "the door"
# =====================================================================================

class BlendMethod(str, Enum):
    MASS_AVG   = "mass_avg"    # concentrations: assay, aloin, polysaccharides, ash, moisture, heavy metals
    PH_HPLUS   = "hplus_avg"   # pH: [H+] mass-weight then reconvert (ESTIMATE ONLY -> lab measures)
    WORST_CASE = "worst_case"  # micro counts (APC, Mold&Yeast): max; re-test the blend
    ALL_PASS   = "all_pass"    # qualitative NEGATIVE (Salmonella, E.coli, Coliforms): every lot must pass


@dataclass
class Parameter:
    name: str
    blend_method: BlendMethod
    numeric: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    critical: bool = False          # ICH Q6A: critical attrs are release-tested on the blend
    uom: str = ""


@dataclass
class Lot:
    lot_id: str
    mass_kg: float
    values: Dict[str, Union[float, bool]] = field(default_factory=dict)  # numeric->float; qualitative->PASS(True)/FAIL(False)


@dataclass
class BlendResult:
    parameter: str
    blend_method: str
    computed_value: Union[float, bool, None]   # the ESTIMATE (float, or bool for all_pass)
    is_estimate: bool
    requires_lab_measurement: bool             # THE DOOR: lab must confirm before release
    in_spec_estimate: Optional[bool]           # estimate vs TDS min/max (None if n/a)
    critical: bool
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    measured_value: Union[float, bool, None] = None   # lab fills this on the ACTUAL blend
    confirmed: bool = False
    note: str = ""

    def release_ok(self) -> Optional[bool]:
        """Release gates on the MEASURED value, never the estimate.
        Returns None while awaiting lab confirmation."""
        if not self.confirmed or self.measured_value is None:
            return None
        return _within_spec(self.measured_value, self.min_value, self.max_value, self.blend_method)


def _within_spec(value, mn, mx, method) -> bool:
    if method == BlendMethod.ALL_PASS.value:
        return bool(value)
    if mn is not None and value < mn:
        return False
    if mx is not None and value > mx:
        return False
    return True


def _mass_avg(lots, p):
    tot = sum(l.mass_kg for l in lots if p.name in l.values)
    if tot == 0:
        return None
    return sum(l.mass_kg * l.values[p.name] for l in lots if p.name in l.values) / tot


def _ph_hplus(lots, p):
    """Correct pH blend estimate: average [H+] by mass, then reconvert. NEVER linear."""
    tot = sum(l.mass_kg for l in lots if p.name in l.values)
    if tot == 0:
        return None
    h = sum(l.mass_kg * (10 ** (-l.values[p.name])) for l in lots if p.name in l.values) / tot
    return -log10(h)


def _worst_case(lots, p):
    vals = [l.values[p.name] for l in lots if p.name in l.values]
    return max(vals) if vals else None


def _all_pass(lots, p):
    vals = [bool(l.values[p.name]) for l in lots if p.name in l.values]
    return all(vals) if vals else None


def blend(lots: List[Lot], parameters: List[Parameter]) -> Dict[str, BlendResult]:
    """Compute the predicted blend per parameter, applying the correct rule per class,
    and wire 'the door' (requires_lab_measurement for critical attrs / pH / micro)."""
    out: Dict[str, BlendResult] = {}
    for p in parameters:
        if p.blend_method == BlendMethod.MASS_AVG:
            cv, est, door, note = _mass_avg(lots, p), True, p.critical, "mass-weighted average of per-gram values"
        elif p.blend_method == BlendMethod.PH_HPLUS:
            cv, est, door, note = _ph_hplus(lots, p), True, True, "pH via [H+] mass-average — ESTIMATE; lab must measure the blend (buffered)"
        elif p.blend_method == BlendMethod.WORST_CASE:
            cv, est, door, note = _worst_case(lots, p), True, True, "worst-case (max) screen — RE-TEST the homogenized blend"
        elif p.blend_method == BlendMethod.ALL_PASS:
            cv, est, door, note = _all_pass(lots, p), False, True, "every input lot must pass — composite/blend confirmation"
        else:
            raise ValueError(f"unknown blend_method {p.blend_method}")

        in_spec = None
        if cv is not None:
            in_spec = _within_spec(cv, p.min_value, p.max_value, p.blend_method.value)
        out[p.name] = BlendResult(
            parameter=p.name, blend_method=p.blend_method.value, computed_value=cv,
            is_estimate=est, requires_lab_measurement=door or p.critical,
            in_spec_estimate=in_spec, critical=p.critical,
            min_value=p.min_value, max_value=p.max_value, note=note,
        )
    return out


def blend_uniformity_ok(sample_results: List[float], rsd_max: float = 5.0,
                        band=(90.0, 110.0)) -> bool:
    """Precondition for trusting any mass-avg: individual results within band % of the
    mean AND RSD <= rsd_max (best-practice: 90-110%, RSD<=5%)."""
    if len(sample_results) < 2:
        return False
    mean = sum(sample_results) / len(sample_results)
    if mean == 0:
        return False
    var = sum((x - mean) ** 2 for x in sample_results) / (len(sample_results) - 1)
    rsd = (var ** 0.5) / mean * 100
    lo, hi = band
    within = all(lo <= (x / mean * 100) <= hi for x in sample_results)
    return within and rsd <= rsd_max


# =====================================================================================
# SELF-TEST  (run:  python3 amb_formulation_engine.py)
# =====================================================================================
if __name__ == "__main__":
    ok = 0; total = 0
    def check(name, got, exp, tol=1e-2):
        global ok, total; total += 1
        good = (abs(got - exp) <= tol) if isinstance(exp, (int, float)) and not isinstance(exp, bool) else (got == exp)
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got={got!r} exp={exp!r}")
        ok += 1 if good else 0

    print("== A) Mass balance (vs FoxPro worked FOLIOs) ==")
    jc = juice_to_concentrate(135000)
    check("juice->concentrate 135t penca", jc["concentrate_kg"], 11730, tol=400)  # FoxPro FOLIO 19 ~11,730 kg
    pw = concentrate_to_powder(7042.5, st_conc_pct=15.0, dry_yield=0.861)
    check("concentrate->powder (0307 FOLIO 1288)", pw["powder_kg"], 909.5, tol=1.0)
    mx = powder_to_mix(945, pct_powder=10, pct_excipient=90)
    check("powder->mix 10:90 excipient", mx["excipient_kg"], 8505, tol=1.0)
    check("powder->mix cuñetes (9450/25)", mx["cunetes"], 378, tol=0.1)
    st = standardize_with_carrier(100, native_marker_pct=10.0, target_marker_pct=7.5)
    check("standardize carrier (10%->7.5%)", st["carrier_kg"], 33.333, tol=0.01)

    print("== B) Blend rules + the door ==")
    params = [
        Parameter("Aloin",        BlendMethod.MASS_AVG,   min_value=0, max_value=0.1, critical=True, uom="ppm"),
        Parameter("pH",           BlendMethod.PH_HPLUS,   min_value=3.5, max_value=5.0, critical=True),
        Parameter("AerobicPlate", BlendMethod.WORST_CASE, min_value=0, max_value=500, critical=True, uom="CFU/g"),
        Parameter("Salmonella",   BlendMethod.ALL_PASS,   numeric=False, critical=True),
    ]
    lots = [
        Lot("A", 700, {"Aloin": 0.08, "pH": 3.0, "AerobicPlate": 300, "Salmonella": True}),
        Lot("B", 300, {"Aloin": 0.12, "pH": 5.0, "AerobicPlate": 500, "Salmonella": True}),
    ]
    res = blend(lots, params)
    check("Aloin mass-avg (700*.08+300*.12)/1000", res["Aloin"].computed_value, 0.092)
    check("Aloin in_spec_estimate (<=0.1)", res["Aloin"].in_spec_estimate, True)
    # masses 700:300 -> [H+]=(700e-3+300e-5)/1000=7.03e-4 -> pH 3.15 (mass-weighted; NOT linear 3.6)
    check("pH [H+] mass-weighted (NOT linear)", res["pH"].computed_value, 3.153, tol=0.01)
    check("pH requires lab measurement (door)", res["pH"].requires_lab_measurement, True)
    check("pH in_spec estimate (3.15 in 3.5-5.0?)", res["pH"].in_spec_estimate, False)  # estimate flags it low -> lab confirms
    check("APC worst-case (max 300,500)", res["AerobicPlate"].computed_value, 500)
    check("Salmonella all-pass (both PASS)", res["Salmonella"].computed_value, True)
    check("release_ok before lab = None", res["Aloin"].release_ok(), None)
    # lab measures the actual blend and confirms:
    res["Aloin"].measured_value = 0.089; res["Aloin"].confirmed = True
    check("release_ok after lab confirm", res["Aloin"].release_ok(), True)

    # a failing input lot:
    lots2 = lots + [Lot("C", 50, {"Salmonella": False})]
    check("Salmonella all-pass with 1 fail", blend(lots2, params)["Salmonella"].computed_value, False)

    print("== C) Blend uniformity gate ==")
    check("uniform (99,101,100)", blend_uniformity_ok([99, 101, 100]), True)
    check("non-uniform (80,120,100)", blend_uniformity_ok([80, 120, 100]), False)

    print(f"\n{ok}/{total} checks passed")
