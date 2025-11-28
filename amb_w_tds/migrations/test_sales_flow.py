#!/usr/bin/env python3
"""
Test Complete Sales Flow: SO → SE → QI → DN → INV
"""

import frappe
from frappe.utils import nowdate, nowtime, add_days

@frappe.whitelist()

def test_complete_sales_flow(cleanup=False):
    """
    Test the complete sales flow from order to invoice
    
    Usage:
        import amb_w_tds.migrations.test_sales_flow as tsf
        result = tsf.test_complete_sales_flow()
    """
    
    if cleanup:
        cleanup_test_data()
    
    results = {
        'sales_order': None,
        'stock_entry': None,
        'quality_inspection': None,
        'delivery_note': None,
        'sales_invoice': None,
        'errors': []
    }
    
    # ... rest of the function stays the same
    
    try:
        print("" + "="*70)
        print("TESTING COMPLETE SALES FLOW")
        print("="*70 + "")
        
        # Step 1: Create or get test customer
        print("[1/6] Creating/Getting Customer...")
        customer = get_or_create_customer()
        print("    Customer: {}".format(customer.name))
        
        # Step 2: Create or get test item
        print("[2/6] Creating/Getting Item...")
        item = get_or_create_item()
        print("    Item: {}".format(item.name))
        
        # Step 3: Create Sales Order
        print("[3/6] Creating Sales Order...")
        so = create_sales_order(customer.name, item.name)
        results['sales_order'] = so.name
        print("    Sales Order: {}".format(so.name))
        
        # Step 4: Create Stock Entry
        print("[4/6] Creating Stock Entry...")
        se = create_stock_entry(so, item)
        results['stock_entry'] = se.name
        print("    Stock Entry: {}".format(se.name))
        
        # Step 5: Create Quality Inspection
        print("[5/6] Creating Quality Inspection...")
        qi = create_quality_inspection(se, item)
        results['quality_inspection'] = qi.name
        print("    Quality Inspection: {}".format(qi.name))
        
        # Step 6: Create Delivery Note
        print("[6/6] Creating Delivery Note...")
        dn = create_delivery_note(so, qi)
        results['delivery_note'] = dn.name
        print("    Delivery Note: {}".format(dn.name))
        
        # Step 7: Create Sales Invoice
        print("[7/7] Creating Sales Invoice...")
        sinv = create_sales_invoice(dn)
        results['sales_invoice'] = sinv.name
        print("    Sales Invoice: {}".format(sinv.name))
        
        frappe.db.commit()
        
        print("" + "="*70)
        print("SUCCESS! Complete flow created:")
        print("  Sales Order: {}".format(results['sales_order']))
        print("  Stock Entry: {}".format(results['stock_entry']))
        print("  Quality Inspection: {}".format(results['quality_inspection']))
        print("  Delivery Note: {}".format(results['delivery_note']))
        print("  Sales Invoice: {}".format(results['sales_invoice']))
        print("="*70 + "")
        
        return results
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = str(e)
        results['errors'].append(error_msg)
        print("ERROR: {}".format(error_msg))
        frappe.log_error("Sales Flow Test Error", error_msg)
        return results


def get_or_create_customer():
    """Get or create test customer"""
    customer_name = "Test Customer - BRENNTAG"
    
    if frappe.db.exists('Customer', customer_name):
        return frappe.get_doc('Customer', customer_name)
    
    customer = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': customer_name,
        'customer_type': 'Company',
        'customer_group': 'Commercial',
        'territory': 'All Territories',
        # Mexico localization fields
        'tax_id': 'XAXX010101000',  # Generic RFC for testing
        'tax_system': '601'  # General de Ley Personas Morales
    })
    customer.insert(ignore_permissions=True)
    return customer

def get_or_create_item():
    """Get or create test item with batch"""
    item_code = "TEST-ALOE-001"
    
    if frappe.db.exists('Item', item_code):
        # Item exists, just return it
        item = frappe.get_doc('Item', item_code)
        print("    Using existing item: {}".format(item_code))
        return item
    
    # Delete any orphaned item prices before creating
    frappe.db.sql("DELETE FROM `tabItem Price` WHERE item_code = %s", (item_code,))
    
    item = frappe.get_doc({
        'doctype': 'Item',
        'item_code': item_code,
        'item_name': 'Test Aloe Vera Powder 200:1',
        'item_group': 'Products',
        'stock_uom': 'Kg',
        'is_stock_item': 1,
        'has_batch_no': 1,
        'create_new_batch': 1,
        'is_sales_item': 1,
        'valuation_rate': 100,
        # DO NOT set standard_rate - it creates auto Item Prices
        # 'standard_rate': 150,  # REMOVED
        'description': 'Test item for sales flow',
        'product_key': '12164502'
    })
    item.insert(ignore_permissions=True)
    print("    Created new item: {}".format(item_code))
    return item

def create_sales_order(customer, item_code):
    """Create Sales Order with all required fields"""
    # Get default company
    company = frappe.defaults.get_defaults().company
    
    # Use specific warehouse for finished goods sales
    warehouse = 'FG to Sell Warehouse - AMB-W'
    
    # Get default currency and price list
    currency = frappe.db.get_value('Company', company, 'default_currency')
    price_list = frappe.db.get_value('Selling Settings', None, 'selling_price_list')
    
    so = frappe.get_doc({
        'doctype': 'Sales Order',
        'naming_series': 'SO-',
        'customer': customer,
        'order_type': 'Sales',
        'transaction_date': nowdate(),
        'delivery_date': add_days(nowdate(), 7),
        'company': company,
        'currency': currency,
        'conversion_rate': 1.0,
        'selling_price_list': price_list or 'Standard Selling',
        'price_list_currency': currency,
        'plc_conversion_rate': 1.0,
        
        # Custom field - set subcliente same as customer
        'custom_subcliente': customer,
        
        'items': [{
            'item_code': item_code,
            'qty': 100,
            'rate': 150,
            'delivery_date': add_days(nowdate(), 7),
            'warehouse': warehouse,
            'custom_package_type': 'Bags'
        }]
    })
    
    so.insert(ignore_permissions=True)
    so.submit()
    return so

def create_stock_entry(sales_order, item):
    """Create Stock Entry (Manufacture/Transfer)"""
    # Use the same FG to Sell warehouse
    warehouse = 'FG to Sell Warehouse - AMB-W'
    
    se = frappe.get_doc({
        'doctype': 'Stock Entry',
        'stock_entry_type': 'Manufacture',
        'company': sales_order.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'items': [{
            'item_code': item.name,
            'qty': 100,
            't_warehouse': warehouse,
            'basic_rate': 100,
            'cost_center': frappe.db.get_value('Company', sales_order.company, 'cost_center')
        }]
    })
    se.insert(ignore_permissions=True)
    se.submit()
    return se

def create_delivery_note(sales_order, quality_inspection):
    """Create Delivery Note from Sales Order"""
    dn = frappe.get_doc({
        'doctype': 'Delivery Note',
        'customer': sales_order.customer,
        'company': sales_order.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'items': []
    })
    
    # Add items from Sales Order
    for so_item in sales_order.items:
        dn.append('items', {
            'item_code': so_item.item_code,
            'item_name': so_item.item_name,
            'description': so_item.description,
            'qty': so_item.qty,
            'rate': so_item.rate,
            'warehouse': 'FG to Sell Warehouse - AMB-W',  # Same warehouse
            'uom': so_item.uom,
            'against_sales_order': sales_order.name,
            'so_detail': so_item.name,
            'quality_inspection': quality_inspection.name,
            'cost_center': frappe.db.get_value('Company', sales_order.company, 'cost_center')
        })
    
    dn.insert(ignore_permissions=True)
    dn.submit()
    return dn

def create_sales_invoice(delivery_note):
    """Create Sales Invoice from Delivery Note"""
    sinv = frappe.get_doc({
        'doctype': 'Sales Invoice',
        'customer': delivery_note.customer,
        'company': delivery_note.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'due_date': add_days(nowdate(), 30),
        'items': []
    })
    
    # Add items from Delivery Note
    for dn_item in delivery_note.items:
        sinv.append('items', {
            'item_code': dn_item.item_code,
            'item_name': dn_item.item_name,
            'description': dn_item.description,
            'qty': dn_item.qty,
            'rate': dn_item.rate,
            'warehouse': 'FG to Sell Warehouse - AMB-W',  # Same warehouse
            'uom': dn_item.uom,
            'delivery_note': delivery_note.name,
            'dn_detail': dn_item.name,
            'cost_center': frappe.db.get_value('Company', delivery_note.company, 'cost_center')
        })
    
    sinv.insert(ignore_permissions=True)
    sinv.submit()
    return sinv



def create_stock_entry(sales_order, item):
    """Create Stock Entry (Manufacture/Transfer)"""
    se = frappe.get_doc({
        'doctype': 'Stock Entry',
        'stock_entry_type': 'Manufacture',
        'company': sales_order.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'items': [{
            'item_code': item.name,
            'qty': 100,
            't_warehouse': 'Finished Goods - AMB',
            'basic_rate': 100,
            'cost_center': 'Main - AMB'
        }]
    })
    se.insert(ignore_permissions=True)
    se.submit()
    return se

def create_quality_inspection(stock_entry, item):
    """Create Quality Inspection linked to Stock Entry"""
    qi = frappe.get_doc({
        'doctype': 'Quality Inspection',
        'naming_series': 'MAT-QA-.YYYY.-',
        'inspection_type': 'Outgoing',
        'reference_type': 'Stock Entry',
        'reference_name': stock_entry.name,
        'item_code': item.name,
        'sample_size': 100,
        'report_date': nowdate(),
        'inspected_by': frappe.session.user,
        'status': 'Accepted',
        'description': 'Test Quality Inspection for complete flow'
    })
    qi.insert(ignore_permissions=True)
    qi.submit()
    return qi

def create_delivery_note(sales_order, quality_inspection):
    """Create Delivery Note from Sales Order"""
    dn = frappe.get_doc({
        'doctype': 'Delivery Note',
        'customer': sales_order.customer,
        'company': sales_order.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'items': []
    })
    
    # Add items from Sales Order
    for so_item in sales_order.items:
        dn.append('items', {
            'item_code': so_item.item_code,
            'item_name': so_item.item_name,
            'description': so_item.description,
            'qty': so_item.qty,
            'rate': so_item.rate,
            'warehouse': so_item.warehouse,
            'uom': so_item.uom,
            'against_sales_order': sales_order.name,
            'so_detail': so_item.name,
            'quality_inspection': quality_inspection.name,
            'cost_center': 'Main - AMB'
        })
    
    dn.insert(ignore_permissions=True)
    dn.submit()
    return dn

def create_sales_invoice(delivery_note):
    """Create Sales Invoice from Delivery Note"""
    sinv = frappe.get_doc({
        'doctype': 'Sales Invoice',
        'customer': delivery_note.customer,
        'company': delivery_note.company,
        'posting_date': nowdate(),
        'posting_time': nowtime(),
        'due_date': add_days(nowdate(), 30),
        'items': []
    })
    
    # Add items from Delivery Note
    for dn_item in delivery_note.items:
        sinv.append('items', {
            'item_code': dn_item.item_code,
            'item_name': dn_item.item_name,
            'description': dn_item.description,
            'qty': dn_item.qty,
            'rate': dn_item.rate,
            'warehouse': dn_item.warehouse,
            'uom': dn_item.uom,
            'delivery_note': delivery_note.name,
            'dn_detail': dn_item.name,
            'cost_center': 'Main - AMB'
        })
    
    sinv.insert(ignore_permissions=True)
    sinv.submit()
    return sinv

@frappe.whitelist()
def cleanup_test_data2():
    """Clean up test data before running test"""
    print("\n[CLEANUP] Removing previous test data...")
    
    # Cancel and delete in reverse order
    doctypes_to_clean = [
        ('Sales Invoice', {}),
        ('Delivery Note', {}),
        ('Stock Entry', {}),
        ('Sales Order', {}),
        ('Quality Inspection', {'item_code': 'TEST-ALOE-001'}),
        ('Batch', {'item': 'TEST-ALOE-001'}),
        ('Item Price', {'item_code': 'TEST-ALOE-001'}),
        ('Item', {'item_code': 'TEST-ALOE-001'}),
        ('Customer', {'customer_name': 'Test Customer - BRENNTAG'})
    ]
    
    for doctype, filters in doctypes_to_clean:
        try:
            docs = frappe.get_all(doctype, filters=filters, pluck='name')
            for doc_name in docs:
                try:
                    doc = frappe.get_doc(doctype, doc_name)
                    if hasattr(doc, 'docstatus') and doc.docstatus == 1:
                        doc.cancel()
                    doc.delete(force=1)
                except Exception as e:
                    pass  # Ignore errors during cleanup
            if docs:
                print("    Cleaned {} {} records".format(len(docs), doctype))
        except Exception as e:
            pass
    
    frappe.db.commit()
    print("[CLEANUP] Complete\n")

@frappe.whitelist()
def cleanup_test_data():
    """Clean up test data before running test - SIMPLIFIED"""
    print("\n[CLEANUP] Removing previous test data...")
    
    try:
        # Just delete item prices directly - no cancellation needed
        frappe.db.sql("DELETE FROM `tabItem Price` WHERE item_code = 'TEST-ALOE-001'")
        print("    Cleaned Item Prices")
        frappe.db.commit()
        print("[CLEANUP] Complete\n")
    except Exception as e:
        print("    Cleanup warning: {}".format(str(e)))
        frappe.db.rollback()

