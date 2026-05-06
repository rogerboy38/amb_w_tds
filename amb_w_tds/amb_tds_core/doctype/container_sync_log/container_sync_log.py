"""
Container Sync Log DocType Controller
Tracks synchronization events between Container Selection and Batch AMB
"""

import frappe
from frappe.model.document import Document

class ContainerSyncLog(Document):
    """Container Sync Log controller"""
    
    def validate(self):
        """Validate sync log entry"""
        if not self.sync_timestamp:
            self.sync_timestamp = frappe.utils.now()
    
    def before_save(self):
        """Execute before saving"""
        # Ensure timestamp is set
        if not self.sync_timestamp:
            self.sync_timestamp = frappe.utils.now()
            
        # Clean up old logs (keep last 1000 per container)
        self.cleanup_old_logs()
    
    def cleanup_old_logs(self):
        """Remove old sync logs to prevent database bloat"""
        if self.container_selection:
            # Count existing logs for this container
            count = frappe.db.count('Container Sync Log', {
                'container_selection': self.container_selection
            })
            
            if count > 1000:
                # Get oldest logs to delete
                old_logs = frappe.get_all(
                    'Container Sync Log',
                    filters={'container_selection': self.container_selection},
                    fields=['name'],
                    order_by='sync_timestamp asc',
                    limit=count - 1000
                )
                
                # Delete old logs
                for log in old_logs:
                    frappe.delete_doc('Container Sync Log', log.name)

# API Methods
@frappe.whitelist()
def get_sync_history(container_name, limit=50):
    """Get sync history for a container"""
    sync_logs = frappe.get_all(
        'Container Sync Log',
        filters={'container_selection': container_name},
        fields=['name', 'sync_direction', 'sync_status', 'sync_timestamp', 'error_message'],
        order_by='sync_timestamp desc',
        limit=limit
    )
    
    return {'success': True, 'logs': sync_logs}

@frappe.whitelist()
def get_failed_syncs(days=7):
    """Get failed sync operations from last N days"""
    from frappe.utils import add_days, nowdate
    
    date_filter = add_days(nowdate(), -days)
    
    failed_syncs = frappe.get_all(
        'Container Sync Log',
        filters={
            'sync_status': 'Error',
            'sync_timestamp': ['>=', date_filter]
        },
        fields=['name', 'container_selection', 'batch_amb', 'sync_direction', 'error_message', 'sync_timestamp'],
        order_by='sync_timestamp desc'
    )
    
    return {'success': True, 'failed_syncs': failed_syncs}