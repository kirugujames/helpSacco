import frappe
from frappe.utils import flt

@frappe.whitelist(allow_guest=True)
def get_welfare_stats():
    """
    Returns statistics for the welfare dashboard.
    """
    # 1. Total Claims
    total_claims = frappe.db.count("SACCO Welfare Claim")
    
    # 2. Pending Claims
    pending_claims = frappe.db.count("SACCO Welfare Claim", filters={"status": "Pending"})
    
    # 3. Approved Claims
    approved_claims = frappe.db.count("SACCO Welfare Claim", filters={"status": "Approved"})
    
    # 4. Total Member Contributions
    # Sum of all SACCO Welfare records of type 'Contribution' and docstatus=1 (Submitted)
    total_contributions = frappe.db.get_value("SACCO Welfare", 
        {"type": "Contribution", "docstatus": 1}, 
        "sum(contribution_amount)") or 0
        
    return {
        "status": "success",
        "data": {
            "total_claims": total_claims,
            "pending_claims": pending_claims,
            "approved_claims": approved_claims,
            "total_contributions": flt(total_contributions)
        }
    }
