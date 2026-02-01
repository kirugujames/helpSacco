import frappe
from frappe.utils import flt, nowdate, get_datetime

@frappe.whitelist(allow_guest=True)
def get_dashboard_stats():
    """
    Returns high-level statistics:
    - Total Members
    - Total Savings (sum of all member total_savings)
    - Total Active Loans
    - Default Rate
    """
    total_members = frappe.db.count("SACCO Member")
    
    # Summing all member savings directly from the Member doctype for speed, 
    # assuming total_savings field is kept up to date.
    total_savings = frappe.db.sql("SELECT SUM(total_savings) FROM `tabSACCO Member`")[0][0] or 0.0
    
    active_loans = frappe.db.count("SACCO Loan", filters={"status": "Active"})
    total_loans = frappe.db.count("SACCO Loan")
    defaulted_loans = frappe.db.count("SACCO Loan", filters={"status": "Defaulted"})
    
    default_rate = 0.0
    if total_loans > 0:
        default_rate = (flt(defaulted_loans) / flt(total_loans)) * 100.0
        
    return {
        "status": "success",
        "data": {
            "total_members": total_members,
            "total_savings": flt(total_savings),
            "active_loans": active_loans,
            "default_rate": round(default_rate, 2)
        }
    }

@frappe.whitelist(allow_guest=True)
def get_loan_breakdown():
    """
    Returns valid loan accounts count and value grouped by loan type (product).
    """
    # Group by loan_product
    data = frappe.db.sql("""
        SELECT 
            loan_product, 
            COUNT(name) as count, 
            SUM(loan_amount) as total_amount,
            SUM(outstanding_balance) as outstanding_amount
        FROM `tabSACCO Loan`
        WHERE status IN ('Active', 'Disbursed', 'Defaulted') 
        GROUP BY loan_product
    """, as_dict=True)
    
    return {
        "status": "success",
        "data": data
    }

@frappe.whitelist(allow_guest=True)
def get_recent_activities(limit_start=0, limit_page_length=15, search=None):
    """
    Returns combined feed of slightly rich activity data:
    - Savings Deposits
    - Loan Repayments
    Supports pagination and search by member/name.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    fetch_limit = limit_start + limit_page_length

    filters_savings = {"type": "Deposit", "docstatus": 1}
    filters_repayment = {"docstatus": 1}

    if search:
        # Search members by name or ID
        members = frappe.get_all("SACCO Member", 
            or_filters=[["member_name", "like", f"%{search}%"], ["name", "like", f"%{search}%"]],
            pluck="name"
        )
        if members:
            filters_savings["member"] = ["in", members]
            filters_repayment["member"] = ["in", members]
        else:
            # If search is provided but no members found, return empty
            return {"status": "success", "data": []}

    # Fetch Deposits
    deposits = frappe.db.get_all("SACCO Savings", 
        filters=filters_savings, 
        fields=["name", "member", "amount", "posting_date", "creation", "payment_mode"],
        order_by="creation desc",
        limit_page_length=fetch_limit
    )
    
    # Fetch Repayments
    repayments = frappe.db.get_all("SACCO Loan Repayment",
        filters=filters_repayment,
        fields=["name", "member", "payment_amount as amount", "payment_date", "creation", "payment_mode"],
        order_by="creation desc",
        limit_page_length=fetch_limit
    )
    
    activities = []
    
    # Helper to fetch member names efficiently
    member_names = {}
    all_members = list(set([d.member for d in deposits] + [r.member for r in repayments]))
    if all_members:
        # Batch fetch names
        m_list = frappe.db.get_all("SACCO Member", filters={"name": ["in", all_members]}, fields=["name", "member_name"])
        for m in m_list:
            member_names[m.name] = m.member_name
            
    for d in deposits:
        activities.append({
            "type": "Savings Deposit",
            "member": d.member,
            "member_name": member_names.get(d.member, d.member),
            "amount": flt(d.amount),
            "date": d.posting_date, # Date object
            "timestamp": d.creation, # For sorting
            "details": f"Via {d.payment_mode}"
        })
        
    for r in repayments:
        activities.append({
            "type": "Loan Repayment",
            "member": r.member,
            "member_name": member_names.get(r.member, r.member),
            "amount": flt(r.amount),
            "date": r.payment_date,
            "timestamp": r.creation,
            "details": f"Via {r.payment_mode}"
        })
        
    # Sort by timestamp desc and slice
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    activities = activities[limit_start : limit_start + limit_page_length]
    
    return {
        "status": "success",
        "data": activities
    }

@frappe.whitelist(allow_guest=True)
def get_payment_requests(limit_start=0, limit_page_length=20, search=None):
    """
    Returns Pending and Overdue payments.
    Supports pagination and search by member/name.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    filters = {"status": ["in", ["Active", "Defaulted"]]}
    if search:
        members = frappe.get_all("SACCO Member", 
            or_filters=[["member_name", "like", f"%{search}%"], ["name", "like", f"%{search}%"]],
            pluck="name"
        )
        if members:
            filters["member"] = ["in", members]
        else:
            return {"status": "success", "data": []}

    active_loans = frappe.db.get_all("SACCO Loan", 
        filters=filters,
        fields=["name", "member", "loan_product", "total_principal_demanded", "total_interest_demanded", "principal_paid", "interest_paid", "monthly_installment"],
        limit_start=limit_start,
        limit_page_length=limit_page_length
    )
    
    results = []
    
    # Batch fetch member names
    member_names = {}
    if active_loans:
        m_list = frappe.db.get_all("SACCO Member", filters={"name": ["in", [l.member for l in active_loans]]}, fields=["name", "member_name"])
        for m in m_list:
            member_names[m.name] = m.member_name

    for loan in active_loans:
        total_due = flt(loan.total_principal_demanded) + flt(loan.total_interest_demanded)
        total_paid = flt(loan.principal_paid) + flt(loan.interest_paid)
        
        arrears = total_due - total_paid
        
        status = "Good Standing"
        amount_to_show = flt(loan.monthly_installment) # By default show the installment as 'pending'
        
        if arrears > 1.0: # Tolerance
            status = "Overdue"
            amount_to_show = arrears
        
        results.append({
            "loan": loan.name,
            "member": loan.member,
            "member_name": member_names.get(loan.member, loan.member),
            "amount": round(amount_to_show, 2),
            "status": status,
            "product": loan.loan_product
        })
    
    return {
        "status": "success",
        "data": results
    }

@frappe.whitelist(allow_guest=True)
def get_savings_growth():
    """
    Returns monthly savings growth.
    """
    data = frappe.db.sql("""
        SELECT 
            MONTHNAME(posting_date) as month_name, 
            YEAR(posting_date) as year,
            SUM(amount) as total
        FROM `tabSACCO Savings`
        WHERE type = 'Deposit' AND docstatus = 1
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date) ASC, MONTH(posting_date) ASC
    """, as_dict=True)
    
    return {
        "status": "success",
        "data": data
    }
