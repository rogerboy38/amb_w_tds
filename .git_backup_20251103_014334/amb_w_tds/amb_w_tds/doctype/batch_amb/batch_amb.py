# Copyright (c) 2024, Roger Mori and contributors
# For license information, please see license.txt


import frappe

from frappe.model.document import Document

from frappe.utils import flt, nowdate, add_days, cint



class BatchAMB(Document):

    def validate(self):

        self.calculate_total_volume()

        self.calculate_concentrations()

        self.calculate_expiry_date()


    def calculate_total_volume(self):

        """Calculate total volume from container details"""

        total = 0

        if self.container_details:

            for row in self.container_details:

                if row.volume_liters:

                    total += flt(row.volume_liters)

        self.total_volume_liters = total


    def calculate_concentrations(self):

        """Calculate concentrations based on total volume"""

        if not self.total_volume_liters or self.total_volume_liters == 0:

            return


        total_volume = flt(self.total_volume_liters)


        # Calculate CBD concentration

        if self.total_cbd_mg:

            self.cbd_concentration_mg_ml = flt(self.total_cbd_mg) / total_volume


        # Calculate THC concentration

        if self.total_thc_mg:

            self.thc_concentration_mg_ml = flt(self.total_thc_mg) / total_volume


        # Calculate CBG concentration

        if self.total_cbg_mg:

            self.cbg_concentration_mg_ml = flt(self.total_cbg_mg) / total_volume


        # Calculate CBN concentration

        if self.total_cbn_mg:

            self.cbn_concentration_mg_ml = flt(self.total_cbn_mg) / total_volume


    def calculate_expiry_date(self):

        """Calculate expiry date based on manufacturing date and expiry period"""

        if self.manufacturing_date and self.expiry_period_in_days:

            self.expiry_date = add_days(self.manufacturing_date, cint(self.expiry_period_in_days))



@frappe.whitelist()

def split_batch(batch_id, num_sub_batches, naming_pattern):

    """

    Split a batch into multiple sub-batches

    Each sub-batch will get equal distribution of containers

    """

    batch = frappe.get_doc("Batch AMB", batch_id)
    

    if not batch.container_details:

        frappe.throw("No containers to split")
    

    num_sub_batches = cint(num_sub_batches)

    containers_per_batch = len(batch.container_details) // num_sub_batches

    remaining_containers = len(batch.container_details) % num_sub_batches
    

    sub_batches = []

    container_index = 0
    

    for i in range(num_sub_batches):

        # Create new sub-batch

        sub_batch = frappe.new_doc("Batch AMB")

        sub_batch.batch_id = f"{naming_pattern}{i+1}"

        sub_batch.item = batch.item

        sub_batch.item_name = batch.item_name

        sub_batch.warehouse = batch.warehouse

        sub_batch.manufacturing_date = batch.manufacturing_date

        sub_batch.expiry_period_in_days = batch.expiry_period_in_days

        sub_batch.parent_batch = batch.name
        

        # Assign containers to this sub-batch

        num_containers = containers_per_batch + (1 if i < remaining_containers else 0)
        

        for j in range(num_containers):

            if container_index < len(batch.container_details):

                container = batch.container_details[container_index]

                sub_batch.append("container_details", {

                    "container_number": j + 1,

                    "container_type": container.container_type,

                    "volume_liters": container.volume_liters,

                    "serial_no": container.serial_no

                })

                container_index += 1
        

        sub_batch.insert()

        sub_batches.append(sub_batch.name)
    

    return sub_batches



@frappe.whitelist()

def create_container_items(batch_id):

    """

    Create Item master for each container in the batch

    Items will be linked to containers

    """

    batch = frappe.get_doc("Batch AMB", batch_id)
    

    if not batch.container_details:

        frappe.throw("No containers available")
    

    created_items = []
    

    for container in batch.container_details:

        # Generate item code

        item_code = f"{batch.batch_id}-C{container.container_number}"
        

        # Check if item already exists

        if frappe.db.exists("Item", item_code):

            container.item_code = item_code

            continue
        

        # Create new item

        item = frappe.new_doc("Item")

        item.item_code = item_code

        item.item_name = f"{batch.item_name} - Container {container.container_number}"

        item.item_group = frappe.db.get_value("Item", batch.item, "item_group") or "Products"

        item.stock_uom = batch.stock_uom or "Litre"

        item.is_stock_item = 1

        item.has_batch_no = 1

        item.create_new_batch = 0

        item.batch_number_series = ""
        

        # Set default warehouse

        if batch.warehouse:

            item.append("item_defaults", {

                "default_warehouse": batch.warehouse,

                "company": frappe.defaults.get_defaults().get("company")

            })
        

        # Copy attributes from parent item

        parent_item = frappe.get_doc("Item", batch.item)

        if parent_item.item_defaults:

            for default in parent_item.item_defaults:

                if not any(d.company == default.company for d in item.item_defaults):

                    item.append("item_defaults", {

                        "company": default.company,

                        "default_warehouse": default.default_warehouse

                    })
        

        item.insert(ignore_permissions=True)
        

        # Update container with item code

        container.item_code = item_code

        created_items.append(item_code)
    

    batch.save()
    

    return created_items



@frappe.whitelist()

def create_container_boms(batch_id):

    """

    Create BOM for each container item

    BOM will include the parent batch item as raw material

    """

    batch = frappe.get_doc("Batch AMB", batch_id)
    

    if not batch.container_details:

        frappe.throw("No containers available")
    

    created_boms = []
    

    for container in batch.container_details:

        if not container.item_code:

            frappe.throw(f"Container {container.container_number} does not have an item code. Please create items first.")
        

        # Check if BOM already exists

        existing_bom = frappe.db.exists("BOM", {

            "item": container.item_code,

            "is_default": 1,

            "is_active": 1

        })
        

        if existing_bom:

            container.bom = existing_bom

            continue
        

        # Create new BOM

        bom = frappe.new_doc("BOM")

        bom.item = container.item_code

        bom.quantity = flt(container.volume_liters) or 1

        bom.uom = batch.stock_uom or "Litre"

        bom.is_default = 1

        bom.is_active = 1
        

        # Add parent batch item as raw material

        bom.append("items", {

            "item_code": batch.item,

            "qty": flt(container.volume_liters) or 1,

            "uom": batch.stock_uom or "Litre",

            "rate": 0

        })
        

        bom.insert(ignore_permissions=True)

        bom.submit()
        

        # Update container with BOM

        container.bom = bom.name

        created_boms.append(bom.name)
    

    batch.save()
    

    return created_boms


# ==================== BATCH ANNOUNCEMENT METHODS ====================

@frappe.whitelist()
def get_running_batch_announcements():
    """
    Get running batch announcements for the dashboard
    This method is called from the client side
    """
    try:
        announcements = frappe.get_all(
            'Batch Announcement',
            filters={
                'status': 'Running',
                'start_date': ['<=', frappe.utils.nowdate()],
                'end_date': ['>=', frappe.utils.nowdate()]
            },
            fields=['title', 'message', 'batch_reference', 'priority'],
            order_by='priority desc, creation desc'
        )
        return announcements
    except Exception as e:
        frappe.log_error(f"Error getting batch announcements: {str(e)}")
        return []

@frappe.whitelist() 
def get_batch_statistics():
    """
    Get batch statistics for dashboard widgets
    """
    try:
        # Count batches by level
        levels_count = frappe.db.sql('''
            SELECT custom_batch_level, COUNT(*) as count
            FROM `tabBatch AMB` 
            WHERE docstatus < 2
            GROUP BY custom_batch_level
        ''', as_dict=1)
        
        # Count batches by status
        status_count = frappe.db.sql('''
            SELECT quality_status, COUNT(*) as count
            FROM `tabBatch AMB`
            WHERE docstatus < 2
            GROUP BY quality_status
        ''', as_dict=1)
        
        return {
            'levels_count': levels_count,
            'status_count': status_count,
            'total_batches': frappe.db.count('Batch AMB', {'docstatus': ['<', 2]})
        }
    except Exception as e:
        frappe.log_error(f"Error getting batch statistics: {str(e)}")
        return {}
