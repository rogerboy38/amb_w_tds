import frappe

def update_workstation_rates():
    """
    Update workstation rates based on KPI factors
    
    KPI Reference (per kg):
    - Utilities: $0.60/kg
    - Labor: $7.70/kg
    - Overhead: $0.37/kg
    """
    
    # KPI-based hourly rates (assuming 25kg/hr average throughput)
    rates = {
        'WS-Secado': {
            'hour_rate': 200.00,  # High energy for spray drying
            'hour_rate_electricity': 15.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 25
        },
        'WS-Decoloracion': {
            'hour_rate': 150.00,
            'hour_rate_electricity': 10.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 50
        },
        'WS-Filtrado': {
            'hour_rate': 175.00,
            'hour_rate_electricity': 12.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 35
        },
        'WS-Concentrado': {
            'hour_rate': 180.00,
            'hour_rate_electricity': 12.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 20
        },
        'WS-Mixing': {
            'hour_rate': 100.00,
            'hour_rate_electricity': 5.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 100
        },
        'WS-Molienda': {
            'hour_rate': 120.00,
            'hour_rate_electricity': 8.00,
            'hour_rate_labour': 192.50,
            'production_capacity': 70
        }
    }
    
    results = []
    for ws_name, rate_data in rates.items():
        try:
            ws = frappe.get_doc("Workstation", ws_name)
            ws.hour_rate = rate_data['hour_rate']
            ws.hour_rate_electricity = rate_data['hour_rate_electricity']
            ws.hour_rate_labour = rate_data['hour_rate_labour']
            ws.production_capacity = rate_data['production_capacity']
            ws.save()
            results.append(f"✓ Updated {ws_name}")
        except Exception as e:
            results.append(f"✗ Failed {ws_name}: {str(e)}")
    
    frappe.db.commit()
    return results

if __name__ == "__main__":
    results = update_workstation_rates()
    for r in results:
        print(r)
