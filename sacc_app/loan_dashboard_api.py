import frappe
from frappe.utils import flt

@frappe.whitelist(allow_guest=True)
def get_loan_dashboard():
    """
    Returns loan dashboard statistics:
    - total_pending_applications: Count of loans with status 'Draft' or 'Pending Approval'
    - active_loans_count: Count of active loans
    - active_loans_amount: Total outstanding balance of active loans
    - total_disbursed_amount: Sum of all disbursed loan amounts
    - default_rate: Percentage of defaulted loans vs total loans
    """
    
    # Pending applications (Draft or Pending Approval)
    total_pending_applications = frappe.db.count("SACCO Loan", 
        filters={"status": ["in", ["Draft", "Pending Approval"]]}
    )
    
    # Active loans count and amount
    active_loans_stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            SUM(outstanding_balance) as total_outstanding
        FROM `tabSACCO Loan`
        WHERE status = 'Active'
    """, as_dict=True)
    
    active_loans_count = active_loans_stats[0].count if active_loans_stats else 0
    active_loans_amount = flt(active_loans_stats[0].total_outstanding) if active_loans_stats else 0.0
    
    # Total disbursed amount (all loans that have been disbursed)
    total_disbursed = frappe.db.sql("""
        SELECT SUM(loan_amount) as total
        FROM `tabSACCO Loan`
        WHERE status IN ('Active', 'Completed', 'Defaulted', 'Disbursed')
    """, as_dict=True)
    
    total_disbursed_amount = flt(total_disbursed[0].total) if total_disbursed and total_disbursed[0].total else 0.0
    
    # Default rate calculation
    loan_stats = frappe.db.sql("""
        SELECT 
            COUNT(CASE WHEN status = 'Defaulted' THEN 1 END) as defaulted_count,
            COUNT(*) as total_count
        FROM `tabSACCO Loan`
        WHERE status IN ('Active', 'Completed', 'Defaulted', 'Disbursed')
    """, as_dict=True)
    
    defaulted_count = loan_stats[0].defaulted_count if loan_stats else 0
    total_count = loan_stats[0].total_count if loan_stats else 0
    
    default_rate = 0.0
    if total_count > 0:
        default_rate = (flt(defaulted_count) / flt(total_count)) * 100.0
    
    return {
        "status": "success",
        "data": {
            "total_pending_applications": total_pending_applications,
            "active_loans_count": active_loans_count,
            "active_loans_amount": round(active_loans_amount, 2),
            "total_disbursed_amount": round(total_disbursed_amount, 2),
            "default_rate": round(default_rate, 2)
        }
    }


@frappe.whitelist(allow_guest=True)
def get_loan_applications(status=None, member_name=None, member_id=None, loan_id=None, 
                          limit_start=0, limit_page_length=20):
    """
    Returns detailed loan applications list with filters and pagination.
    
    Parameters:
    - status: Filter by loan status
    - member_name: Search by member name (partial match)
    - member_id: Filter by exact member ID
    - loan_id: Filter by exact loan ID
    - limit_start: Pagination offset (default: 0)
    - limit_page_length: Page size (default: 20)
    
    Returns:
    - member_name: Full name of member
    - member_id: Member ID
    - loan_id: Loan ID
    - amount_applied: Original loan amount
    - amount_disbursed: Same as amount_applied
    - interest_rate: Interest rate percentage
    - status: Current loan status
    - purpose: Loan purpose
    - payment_progress: Percentage of loan paid (0-100)
    - creation_date: When loan was created
    """
    
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    # Build WHERE clause based on filters
    conditions = []
    params = []
    
    if status:
        conditions.append("l.status = %s")
        params.append(status)
    
    if member_id:
        conditions.append("l.member = %s")
        params.append(member_id)
    
    if loan_id:
        conditions.append("l.name = %s")
        params.append(loan_id)
    
    if member_name:
        conditions.append("m.member_name LIKE %s")
        params.append(f"%{member_name}%")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    # Main query
    query = f"""
        SELECT 
            l.name as loan_id,
            l.member as member_id,
            COALESCE(m.member_name, l.member) as member_name,
            l.loan_amount as amount_applied,
            l.loan_amount as amount_disbursed,
            l.interest_rate,
            l.status,
            l.purpose,
            l.total_interest,
            l.principal_paid,
            l.interest_paid,
            l.creation as creation_date
        FROM `tabSACCO Loan` l
        LEFT JOIN `tabSACCO Member` m ON l.member = m.name
        {where_clause}
        ORDER BY l.creation DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([limit_page_length, limit_start])
    
    loans = frappe.db.sql(query, tuple(params), as_dict=True)
    
    # Calculate payment progress for each loan
    results = []
    for loan in loans:
        # Calculate total repayable
        total_repayable = flt(loan.amount_applied) + flt(loan.total_interest)
        
        # Calculate total paid
        total_paid = flt(loan.principal_paid) + flt(loan.interest_paid)
        
        # Calculate payment progress percentage
        payment_progress = 0.0
        if total_repayable > 0:
            payment_progress = (total_paid / total_repayable) * 100.0
        
        results.append({
            "member_name": loan.member_name or "",
            "member_id": loan.member_id,
            "loan_id": loan.loan_id,
            "amount_applied": round(flt(loan.amount_applied), 2),
            "amount_disbursed": round(flt(loan.amount_disbursed), 2),
            "interest_rate": flt(loan.interest_rate),
            "status": loan.status,
            "purpose": loan.purpose or "",
            "payment_progress": round(payment_progress, 2),
            "creation_date": str(loan.creation_date) if loan.creation_date else ""
        })
    
    # Get total count for pagination info
    count_query = f"""
        SELECT COUNT(*) as total
        FROM `tabSACCO Loan` l
        LEFT JOIN `tabSACCO Member` m ON l.member = m.name
        {where_clause}
    """
    
    # Remove the limit/offset params for count query
    count_params = params[:-2] if params else []
    total_count = frappe.db.sql(count_query, tuple(count_params), as_dict=True)
    total = total_count[0].total if total_count else 0
    
    return {
        "status": "success",
        "data": results,
        "pagination": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "total": total
        }
    }
