import frappe

@frappe.whitelist()
def get_cost_dashboard(year=None):
    filters = {}
    if year:
        filters["year"] = year
    recs = frappe.get_all("Amb KPI Factors", filters=filters,
        fields=["name","goal","kpi_name","kpi_type","year","values_currency",
                "base_value","target_value","current_calculated_value",
                "threshold_warning","threshold_critical","visualization"],
        order_by="year desc, kpi_name")
    for r in recs:
        r["factor_count"] = frappe.db.count("AMB Cost Factors",
            {"parent": r["name"], "parenttype": "Amb KPI Factors"})
    years = [y[0] for y in frappe.db.sql(
        "select distinct year from `tabAmb KPI Factors` where ifnull(year,'')!='' order by year desc")]
    return {"records": recs, "years": years}
