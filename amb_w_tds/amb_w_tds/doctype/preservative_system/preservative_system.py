# Copyright (c) 2026, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PreservativeSystem(Document):
    """Preservative System master — formulation catalog seeded from FoxPro CONS_ENC.

    Each system has a single-letter code embedded in TDS version strings (V1.0705F).
    Composition table holds the constituent compounds + percentages (w/w).
    """
    pass
