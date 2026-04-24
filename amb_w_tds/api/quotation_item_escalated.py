# -*- coding: utf-8 -*-
# amb_w_tds.api.quotation_item_escalated
# V13.6.0 P3 / TDS-M3 migration of 2 API Server Scripts:
#   - "QuotationItemEscalated"                   (api_method: QuotationItemEscalated)
#   - "Quotation Item Escalated Server Script"    (api_method: calculate_escalated_prices)
import frappe
from frappe import _


@frappe.whitelist()
def QuotationItemEscalated(*args, **kwargs):
    # Migrated body (verbatim) from Server Script "QuotationItemEscalated"
    class QuotationItemEscalated(Document):
        def validate(self):
            self.set_quantity_limits()
            self.calculate_prices()

        def set_quantity_limits(self):
            """Set min and max quantity based on selected range"""
            if self.quantity_range:
                ranges = {
                    '1-5 kg': (1, 5),
                    '6-10 kg': (6, 10),
                    '11-25 kg': (11, 25),
                    '26-200 kg': (26, 200)
                }

                if self.quantity_range in ranges:
                    self.min_quantity, self.max_quantity = ranges[self.quantity_range]

        def calculate_prices(self):
            """Calculate all prices based on quantity range"""
            if self.ex_works_price and self.freight_cost and self.min_quantity:
                # Calculate delivered price
                self.delivered_price = flt(self.ex_works_price) + flt(self.freight_cost)

                # Calculate price per kg
                self.price_per_kg = self.delivered_price

                # Calculate total price range
                if self.min_quantity == self.max_quantity:
                    self.total_price = self.delivered_price * self.min_quantity
                else:
                    # Store the maximum total for the range
                    self.total_price = self.delivered_price * self.max_quantity

        def calculate_freight_based_on_type(self):
            """Calculate freight cost based on freight type and quantity range"""
            if self.quantity_range and self.freight_type:
                freight_matrix = {
                    '1-5 kg': {
                        'Air Freight': 58.30,
                        'Sea Freight': 45.00,
                        'Ground': 35.00,
                        'Door to Door': 60.00
                    },
                    '6-10 kg': {
                        'Air Freight': 19.87,
                        'Sea Freight': 15.00,
                        'Ground': 12.00,
                        'Door to Door': 22.00
                    },
                    '11-25 kg': {
                        'Air Freight': 16.06,
                        'Sea Freight': 12.00,
                        'Ground': 9.00,
                        'Door to Door': 18.00
                    },
                    '26-200 kg': {
                        'Air Freight': 13.91,
                        'Sea Freight': 10.00,
                        'Ground': 7.00,
                        'Door to Door': 15.00
                    }
                }

                if (self.quantity_range in freight_matrix and 
                    self.freight_type in freight_matrix[self.quantity_range]):
                    self.freight_cost = freight_matrix[self.quantity_range][self.freight_type]


@frappe.whitelist()
def calculate_escalated_prices(*args, **kwargs):
    # Migrated body (verbatim) from Server Script "Quotation Item Escalated Server Script"
    # Server Script for Quotation Item Escalated calculations
    # Enabled: Yes
    # Reference Doctype: Quotation Item Escalated
    # Script Type: API

    def calculate_escalated_prices(doc, method):
        # Calculate freight cost based on quantity
        freight_cost = calculate_freight_cost(doc.qty)
        doc.freight_cost = freight_cost

        # Apply quantity-based escalation
        escalated_rate = apply_quantity_escalation(doc.price_list_rate, doc.qty)
        doc.escalated_rate = escalated_rate

        # Calculate final rate
        doc.rate = flt(escalated_rate) + flt(freight_cost)

        # Calculate amount
        if doc.qty and doc.rate:
            doc.amount = flt(doc.qty) * flt(doc.rate)

            # Calculate net amount if discount exists
            if doc.discount_percentage:
                doc.discount_amount = flt(doc.amount) * flt(doc.discount_percentage) / 100
                doc.net_amount = flt(doc.amount) - flt(doc.discount_amount)

                if doc.qty:
                    doc.net_rate = flt(doc.net_amount) / flt(doc.qty)

    def calculate_freight_cost(quantity):
        quantity = flt(quantity)
        if quantity <= 1:
            return 58.30
        elif quantity <= 5:
            return 19.87
        elif quantity <= 10:
            return 16.06
        elif quantity <= 20:
            return 14.17
        else:
            return 13.91

    def apply_quantity_escalation(base_price, quantity):
        base_price = flt(base_price)
        quantity = flt(quantity)

        if quantity >= 100:
            return base_price * 0.9  # 10% discount
        elif quantity >= 50:
            return base_price * 0.95  # 5% discount
        else:
            return base_price

    # Hook this function to validate event
    calculate_escalated_prices
