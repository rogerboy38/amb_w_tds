"""The one vocabulary of the quality release chain (TASKS-384 B1; decisions 303 and 315).

The same four constants, with the same names and values, live in amb_w_spc
(`amb_w_spc/sfc_manufacturing/lot_quality.py`). Nothing of amb_w_spc is imported here: this app must import
without it. `tests/test_quality_vocabulary.py` fails when these lists drift from the option lists of this app's
own DocTypes, and compares them with the other app's module when that app can be imported.
"""

# Batch AMB `quality_status`, in the order of its options.
LOT_STATUSES = ("Pending", "Passed", "Failed", "Hold")

# `overall_result` of both certificates (COA AMB and COA AMB2), in the order of its options.
CERTIFICATE_RESULTS = ("Pending", "Pass", "Fail", "Partial", "No Tests")

# Decision 303. "Pending" and "No Tests" have no mapping: such a certificate cannot be approved.
RESULT_TO_LOT_STATUS = {"Pass": "Passed", "Fail": "Failed", "Partial": "Hold"}

# Batch AMB `status_source`: who says what the record's status is.
STATUS_SOURCES = ("", "Own certificate", "Inherited", "Hold action")
