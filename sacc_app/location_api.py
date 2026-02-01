import frappe
import json

@frappe.whitelist(allow_guest=True)
def seed_kenya_data(data=None):
    """
    Seeds Kenya Location data (County, Constituency, Ward).
    If data is not provided, reads from apps/sacc_app/sacc_app/data/kenya_locations.json
    """
    if data is None:
        # Load from file
        import os
        file_path = frappe.get_app_path("sacc_app", "data", "kenya_locations.json")
        if not os.path.exists(file_path):
            frappe.throw(f"Location data file not found at {file_path}")
            
        with open(file_path, "r") as f:
            data = json.load(f)

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            frappe.throw(f"Invalid JSON data: {str(e)}")
            
    if not data:
        frappe.throw("No data provided.")

    counties_created = 0
    constituencies_created = 0
    wards_created = 0

    for c_data in data:
        county_name = c_data.get("county_name")
        county_code = c_data.get("county_code")
        
        if not county_name:
            continue
            
        # 1. Create County
        if not frappe.db.exists("Kenya County", county_name) and not frappe.db.exists("Kenya County", {"county_code": county_code}):
            county = frappe.get_doc({
                "doctype": "Kenya County",
                "county_name": county_name,
                "county_code": county_code
            })
            county.insert(ignore_permissions=True)
            counties_created += 1
            
        # 2. Process Constituencies
        constituencies = c_data.get("constituencies", [])
        for con_data in constituencies:
            con_name = con_data.get("constituency_name")
            if not con_name:
                continue
                
            con_id = f"{con_name} ({county_name})"
            if not frappe.db.exists("Kenya Constituency", con_id):
                constituency = frappe.get_doc({
                    "doctype": "Kenya Constituency",
                    "constituency_name": con_name,
                    "county": county_name
                })
                constituency.insert(ignore_permissions=True)
                constituencies_created += 1
            
            # 3. Process Wards
            wards = con_data.get("wards", [])
            for w_name in wards:
                w_name = w_name.strip()
                if not w_name:
                    continue
                    
                ward_id = f"{w_name} ({con_id})"
                if not frappe.db.exists("Kenya Ward", ward_id):
                    ward = frappe.get_doc({
                        "doctype": "Kenya Ward",
                        "ward_name": w_name,
                        "constituency": con_id
                    })
                    ward.insert(ignore_permissions=True)
                    wards_created += 1

    frappe.db.commit()
    
    return {
        "status": "success",
        "message": f"Seeding complete: {counties_created} counties, {constituencies_created} constituencies, {wards_created} wards created."
    }

@frappe.whitelist(allow_guest=True)
def get_counties():
    """Returns all counties."""
    counties = frappe.db.get_all("Kenya County", 
        fields=["county_name", "county_code"], 
        order_by="county_name asc"
    )
    return {"status": "success", "data": counties}

@frappe.whitelist(allow_guest=True)
def get_constituencies(county):
    """Returns constituencies for a given county."""
    if not county:
        frappe.throw("County name is required.")
        
    constituencies = frappe.db.get_all("Kenya Constituency",
        filters={"county": county},
        fields=["name", "constituency_name"],
        order_by="constituency_name asc"
    )
    return {"status": "success", "data": constituencies}

@frappe.whitelist(allow_guest=True)
def get_wards(constituency):
    """Returns wards for a given constituency."""
    if not constituency:
        frappe.throw("Constituency name or ID is required.")
        
    wards = frappe.db.get_all("Kenya Ward",
        filters={"constituency": constituency},
        fields=["name", "ward_name"],
        order_by="ward_name asc"
    )
    return {"status": "success", "data": wards}
