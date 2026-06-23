import frappe
import unittest


class TestSampleRequestAMB(unittest.TestCase):
    def _doc(self, net, gross):
        d = frappe.new_doc("Sample Request AMB")
        d.shipment_net_weight = net
        d.gross_weight_kg = gross
        return d

    def test_net_exceeding_gross_is_blocked(self):
        # net 0.283 > gross 0.280 -> negative tara -> must raise
        self.assertRaises(
            frappe.ValidationError,
            self._doc(0.283, 0.280).validate_shipment_weights,
        )

    def test_net_below_gross_passes(self):
        # net 0.283 < gross 0.500 -> ok
        self._doc(0.283, 0.500).validate_shipment_weights()

    def test_zero_gross_is_skipped(self):
        # guard only enforces when both > 0 (won't fire on incomplete drafts)
        self._doc(0.283, 0).validate_shipment_weights()
