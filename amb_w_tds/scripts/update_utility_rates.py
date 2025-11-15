"""
Update utility item rates (WATER, ELECTRIC, GAS, LABOR) to correct industrial rates
Run: bench execute amb_w_tds.scripts.update_utility_rates.update_all_utility_rates
"""

import frappe

# Correct utility rates (in USD)
UTILITY_RATES = {
    'WATER': {
        'rate': 3.00,
        'uom': 'Cubic Meter',
        'description': 'Industrial water cost (~$3/m³)'
    },
    'ELECTRIC': {
        'rate': 0.15,
        'uom': 'kWh',
        'description': 'Industrial electricity rate (~$0.15/kWh)'
    },
    'GAS': {
        'rate': 8.00,
        'uom': 'Gigajoule',
        'description': 'Industrial gas rate (~$8/GJ)'
    },
    'LABOR': {
        'rate': 25.00,
        'uom': 'Hour',
        'description': 'Production labor hourly rate (~$25/hour)'
    }
}


def update_all_utility_rates(dry_run=False):
    """
    Update all utility item rates to correct values
    
    Args:
        dry_run: If True, only show what would be changed without applying
    """
    
    print("=" * 80)
    print("🔧 Updating Utility Item Rates")
    print("=" * 80)
    
    if dry_run:
        print("\n🛑 DRY RUN MODE - No changes will be made\n")
    
    updates = []
    
    for item_code, settings in UTILITY_RATES.items():
        if not frappe.db.exists("Item", item_code):
            print(f"⚠️  {item_code}: Item not found")
            continue
        
        # Get current rate
        current_rate = frappe.db.get_value("Item", item_code, "valuation_rate")
        new_rate = settings['rate']
        
        print(f"\n📦 {item_code}:")
        print(f"   Current: ${current_rate:,.2f}")
        print(f"   New: ${new_rate:,.2f}")
        print(f"   Change: {((new_rate / current_rate - 1) * 100) if current_rate > 0 else 0:+.1f}%")
        print(f"   {settings['description']}")
        
        updates.append({
            'item_code': item_code,
            'old_rate': current_rate,
            'new_rate': new_rate
        })
    
    if not dry_run:
        print("\n" + "=" * 80)
        print("🚨 APPLYING UPDATES...")
        print("=" * 80)
        
        for update in updates:
            try:
                frappe.db.set_value("Item", update['item_code'], "valuation_rate", update['new_rate'])
                print(f"✅ {update['item_code']}: ${update['old_rate']:,.2f} → ${update['new_rate']:,.2f}")
            except Exception as e:
                print(f"❌ {update['item_code']}: {str(e)}")
        
        frappe.db.commit()
        print("\n✅ ALL UTILITY RATES UPDATED")
    else:
        print("\n" + "=" * 80)
        print("🛑 DRY RUN - No changes made")
        print("\nTo apply changes, run:")
        print("   update_all_utility_rates(dry_run=False)")
    
    print("=" * 80)
    
    return updates


def update_single_utility(item_code, rate):
    """Update rate for a single utility item"""
    
    if not frappe.db.exists("Item", item_code):
        print(f"❌ Item {item_code} not found")
        return False
    
    old_rate = frappe.db.get_value("Item", item_code, "valuation_rate")
    
    frappe.db.set_value("Item", item_code, "valuation_rate", rate)
    frappe.db.commit()
    
    print(f"✅ {item_code}: ${old_rate:,.2f} → ${rate:,.2f}")
    return True


def show_current_utility_rates():
    """Display current utility rates"""
    
    print("=" * 80)
    print("📊 Current Utility Rates")
    print("=" * 80)
    
    for item_code in UTILITY_RATES.keys():
        if frappe.db.exists("Item", item_code):
            rate = frappe.db.get_value("Item", item_code, "valuation_rate")
            uom = frappe.db.get_value("Item", item_code, "stock_uom")
            
            print(f"\n{item_code}:")
            print(f"   Rate: ${rate:,.2f} per {uom}")
        else:
            print(f"\n{item_code}: ❌ Not found")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    update_all_utility_rates(dry_run=True)
