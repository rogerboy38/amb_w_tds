# Copyright (c) 2025, AMB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BatchProcessingHistory(Document):
	"""
	Child table to track Batch AMB processing history.
	
	Records changes in plant location, item transformations, quality status changes,
	and general processing events for audit trail purposes.
	"""
	pass
