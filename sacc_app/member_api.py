import frappe
from frappe.utils import nowdate, get_first_day, get_last_day, flt

@frappe.whitelist(allow_guest=True)
def get_member_stats():
    """
    Returns high-level member statistics for the dashboard.
    """
    total_members = frappe.db.count("SACCO Member")
    active_members = frappe.db.count("SACCO Member", filters={"status": "Active"})
    
    # New members this month
    today = nowdate()
    first_day = get_first_day(today)
    new_members = frappe.db.count("SACCO Member", filters={"creation": [">=", first_day]})
    
    # Other members (Probation, Inactive, Suspended, etc.)
    other_members = total_members - active_members
    
    return {
        "status": "success",
        "data": {
            "total_members": total_members,
            "active_members": active_members,
            "new_members_this_month": new_members,
            "other_members": other_members
        }
    }

@frappe.whitelist(allow_guest=True)
def get_member_list(limit_start=0, limit_page_length=20, search=None, status=None):
    """
    Returns a paginated and searchable list of members.
    Supports status filtering.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    filters = {}
    if status:
        filters["status"] = status

    or_filters = {}
    if search:
        or_filters = {
            "member_name": ["like", f"%{search}%"],
            "name": ["like", f"%{search}%"]
        }

    members = frappe.db.get_all("SACCO Member",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "member_name", "email", "phone", "status", "registration_fee_paid", "creation as registration_date"],
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="creation desc"
    )
    
    return {
        "status": "success",
        "data": members
    }

@frappe.whitelist(allow_guest=True)
def edit_member(member_id, first_name=None, last_name=None, email=None, phone=None, 
                national_id=None, county=None, sub_county=None, ward=None, village=None,
                national_id_image=None, passport_photo=None):
    if not member_id:
        frappe.throw("Member ID is required")
        
    doc = frappe.get_doc("SACCO Member", member_id)
    
    if first_name: doc.first_name = first_name
    if last_name: doc.last_name = last_name
    if email: doc.email = email
    if phone: doc.phone = phone
    if national_id: doc.national_id = national_id
    if county: doc.county = county
    if sub_county: doc.sub_county = sub_county
    if ward: doc.ward = ward
    if village: doc.village = village

    # Process Base64 images for updates (using helper from api.py if available, 
    # but member_api.py doesn't import it. Let's use the logic directly or import.)
    from sacc_app.api import save_base64_image

    if national_id_image:
        doc.national_id_image = save_base64_image(national_id_image, f"ID_{doc.name}.png", "SACCO Member", doc.name)
    if passport_photo:
        doc.passport_photo = save_base64_image(passport_photo, f"Photo_{doc.name}.png", "SACCO Member", doc.name)
    
    doc.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "message": f"Member {member_id} updated successfully",
        "data": {
            "name": doc.name,
            "member_name": doc.member_name,
            "email": doc.email,
            "phone": doc.phone
        }
    }

@frappe.whitelist(allow_guest=True)
def disable_member(member_id):
    if not member_id:
        frappe.throw("Member ID is required")
        
    doc = frappe.get_doc("SACCO Member", member_id)
    doc.status = "Inactive"
    doc.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "message": f"Member {member_id} has been disabled (status set to Inactive)"
    }

@frappe.whitelist(allow_guest=True)
def enable_member(member_id):
    if not member_id:
        frappe.throw("Member ID is required")
        
    doc = frappe.get_doc("SACCO Member", member_id)
    doc.status = "Active"
    doc.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "message": f"Member {member_id} has been enabled (status set to Active)"
    }

@frappe.whitelist(allow_guest=True)
def get_member_full_details(member_id):
    if not member_id:
        frappe.throw("Member ID is required")
        
    if not frappe.db.exists("SACCO Member", member_id):
        return {"status": "error", "message": f"Member {member_id} not found"}
        
    doc = frappe.get_doc("SACCO Member", member_id)
    
    # 1. Registration details including images
    member_data = doc.as_dict()
    # Filter out sensitive or irrelevant fields if necessary
    
    # 2. Aggregated Welfare Contributions
    welfare_total = frappe.db.get_value("SACCO Welfare", 
        {"member": member_id, "type": "Contribution", "docstatus": 1}, 
        "sum(contribution_amount)") or 0
        
    # 3. Active Loan Balances
    active_loans = frappe.db.get_all("SACCO Loan", 
        filters={"member": member_id, "status": ["in", ["Active", "Disbursed", "Defaulted"]]},
        fields=["name", "loan_amount", "outstanding_balance", "status"]
    )
    
    return {
        "status": "success",
        "data": {
            "registration_details": member_data,
            "financial_summary": {
                "total_savings": flt(doc.total_savings),
                "total_loan_outstanding": flt(doc.total_loan_outstanding),
                "total_welfare_contribution": flt(welfare_total),
                "active_loans": active_loans
            }
        }
    }
