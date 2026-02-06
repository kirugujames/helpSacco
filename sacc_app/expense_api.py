import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate, add_months, formatdate
import json

@frappe.whitelist(allow_guest=True)
def get_expense_dashboard_stats():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    today = nowdate()
    first_day_of_month = today[:8] + "01"
    
    # 1. Total Expense (MTD)
    total_expense = frappe.db.sql("""
        SELECT SUM(gl.debit - gl.credit) as total
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE gl.company = %s AND acc.root_type = 'Expense' 
        AND gl.posting_date >= %s AND gl.docstatus = 1
    """, (company, first_day_of_month), as_dict=True)[0].total or 0.0
    
    # 2. Pending Payments (Unpaid Purchase Invoices)
    pending_payments = 0.0
    if frappe.db.exists("DocType", "Purchase Invoice"):
        pending_payments = frappe.db.sql("""
            SELECT SUM(outstanding_amount)
            FROM `tabPurchase Invoice`
            WHERE company = %s AND docstatus = 1 AND status != 'Paid'
        """, (company))[0][0] or 0.0
    
    # 3. Largest Expense (This Month)
    largest_expense = frappe.db.sql("""
        SELECT MAX(gl.debit) as max_val
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE gl.company = %s AND acc.root_type = 'Expense'
        AND gl.posting_date >= %s AND gl.docstatus = 1
    """, (company, first_day_of_month), as_dict=True)[0].max_val or 0.0
    
    # 4. Budget Remaining (Placeholder or simple check)
    budget_remaining = 0.0
    # If Budgets are fully implemented, we'd query tabBudget. 
    # For now, returning 0 or a dummy value if no budgets found.
    
    return {
        "status": "success",
        "data": {
            "total_expense_mtd": round(total_expense, 2),
            "pending_payments": round(pending_payments, 2),
            "largest_expense": round(largest_expense, 2),
            "budget_remaining": round(budget_remaining, 2)
        }
    }

@frappe.whitelist(allow_guest=True)
def get_expenses_by_category():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    data = frappe.db.sql("""
        SELECT acc.account_name as category, SUM(gl.debit - gl.credit) as amount
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE gl.company = %s AND acc.root_type = 'Expense' AND gl.docstatus = 1
        GROUP BY acc.account_name
        ORDER BY amount DESC
    """, company, as_dict=True)
    
    return {"status": "success", "data": data}

@frappe.whitelist(allow_guest=True)
def get_monthly_expense_trends():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Last 6 months
    trends = []
    for i in range(5, -1, -1):
        target_date = add_months(nowdate(), -i)
        year = getdate(target_date).year
        month = getdate(target_date).month
        month_name = formatdate(target_date, "MMMM")
        
        start_date = f"{year}-{month:02d}-01"
        # End date logic simplified
        end_date = add_months(start_date, 1)
        
        total = frappe.db.sql("""
            SELECT SUM(gl.debit - gl.credit)
            FROM `tabGL Entry` gl
            JOIN `tabAccount` acc ON gl.account = acc.name
            WHERE gl.company = %s AND acc.root_type = 'Expense' 
            AND gl.posting_date >= %s AND gl.posting_date < %s AND gl.docstatus = 1
        """, (company, start_date, end_date))[0][0] or 0.0
        
        trends.append({
            "month": month_name,
            "total": round(total, 2)
        })
        
    return {"status": "success", "data": trends}

@frappe.whitelist(allow_guest=True)
def get_all_expense_transactions(limit_start=0, limit_page_length=20, search=None, category=None, status=None):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    conditions = ["gl.company = %s", "acc.root_type = 'Expense'", "gl.docstatus != 0"]
    params = [company]
    
    if search:
        conditions.append("(gl.voucher_no LIKE %s OR gl.remarks LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
        
    if category:
        conditions.append("acc.account_name = %s")
        params.append(category)
        
    if status:
        if status.lower() == "completed":
            conditions.append("gl.docstatus = 1")
        elif status.lower() == "cancelled":
            conditions.append("gl.docstatus = 2")
            
    where_clause = "WHERE " + " AND ".join(conditions)
    
    query = f"""
        SELECT 
            gl.voucher_no as id,
            gl.posting_date as date,
            acc.account_name as category,
            gl.remarks as description,
            gl.party as vendor,
            gl.debit as amount,
            gl.docstatus
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        {where_clause}
        ORDER BY gl.posting_date DESC, gl.creation DESC
        LIMIT %s OFFSET %s
    """
    params.extend([int(limit_page_length), int(limit_start)])
    
    expenses = frappe.db.sql(query, tuple(params), as_dict=True)
    
    for e in expenses:
        e["status"] = "Completed" if e.docstatus == 1 else "Cancelled"
        e["date"] = str(e.date)
        
    return {"status": "success", "data": expenses}

@frappe.whitelist(allow_guest=True)
def get_expense_details(expense_id):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Find the expense leg of the voucher
    expense = frappe.db.sql("""
        SELECT 
            gl.voucher_no as id,
            gl.posting_date as date,
            acc.account_name as category,
            gl.remarks as description,
            gl.party as vendor,
            gl.debit as amount,
            gl.docstatus,
            gl.voucher_type
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE gl.voucher_no = %s AND acc.root_type = 'Expense' AND gl.company = %s
        LIMIT 1
    """, (expense_id, company), as_dict=True)
    
    if not expense:
        return {"status": "error", "message": "Expense not found"}
        
    expense = expense[0]
    expense["status"] = "Completed" if expense.docstatus == 1 else "Cancelled"
    expense["date"] = str(expense.date)
    
    return {"status": "success", "data": expense}
