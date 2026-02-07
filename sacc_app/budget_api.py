import frappe
from frappe.utils import flt, nowdate
import json

@frappe.whitelist(allow_guest=True)
def get_cost_centers():
    """
    Returns a list of Cost Centers (Group and Leaf).
    """
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    data = frappe.db.get_all("Cost Center", 
        filters={"company": company}, 
        fields=["name", "cost_center_name", "is_group", "parent_cost_center"]
    )
    return {"status": "success", "data": data}

@frappe.whitelist(allow_guest=True)
def get_fiscal_years():
    """
    Returns a list of Fiscal Years.
    """
    data = frappe.db.get_all("Fiscal Year", fields=["name", "year", "year_start_date", "year_end_date"], order_by="year_start_date desc")
    return {"status": "success", "data": data}

@frappe.whitelist(allow_guest=True)
def create_budget_request(cost_center, fiscal_year, items, budget_against="Cost Center"):
    """
    Creates a new Budget in Draft status.
    items: List of dicts {account: "Expense Account", budget_amount: 1000}
    """
    if isinstance(items, str):
        items = json.loads(items)
        
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

    # Basic Validation
    if not frappe.db.exists("Cost Center", cost_center):
        return {"status": "error", "message": f"Cost Center {cost_center} not found."}
    if not frappe.db.exists("Fiscal Year", fiscal_year):
        return {"status": "error", "message": f"Fiscal Year {fiscal_year} not found."}

    # Create Budget Doc
    doc = frappe.new_doc("Budget")
    doc.budget_against = "Cost Center" # Enforce Cost Center based on requirements
    doc.cost_center = cost_center
    doc.fiscal_year = fiscal_year
    doc.company = company
    
    # Strict Control Settings (Block Transactions)
    doc.action_if_annual_budget_exceeded = "Stop"
    doc.action_if_accumulated_monthly_budget_exceeded = "Stop"
    # doc.applicable_on_booking_actual_expenses = 1 # This field might be needed depending on ERPNext version

    # Add Accounts
    for item in items:
        account = item.get("account")
        amount = flt(item.get("budget_amount"))
        
        if not account or amount <= 0:
            continue
            
        doc.append("accounts", {
            "account": account,
            "budget_amount": amount
        })
        
    if not doc.accounts:
        return {"status": "error", "message": "At least one valid account with a budget amount is required."}

    doc.insert(ignore_permissions=True)
    
    return {"status": "success", "message": "Budget created successfully (Draft).", "budget_id": doc.name}

@frappe.whitelist(allow_guest=True)
def approve_budget(budget_id):
    """
    Submits the Budget, making it active/enabled and enforcing rules.
    """
    if not frappe.db.exists("Budget", budget_id):
        return {"status": "error", "message": f"Budget {budget_id} not found."}
        
    doc = frappe.get_doc("Budget", budget_id)
    if doc.docstatus == 1:
        return {"status": "error", "message": "Budget is already approved/enabled."}
        
    doc.submit()
    return {"status": "success", "message": f"Budget {budget_id} approved and enabled."}

@frappe.whitelist(allow_guest=True)
def disable_budget(budget_id):
    """
    Cancels the Budget, effectively disabling it.
    """
    if not frappe.db.exists("Budget", budget_id):
        return {"status": "error", "message": f"Budget {budget_id} not found."}
        
    doc = frappe.get_doc("Budget", budget_id)
    if doc.docstatus != 1:
         return {"status": "error", "message": "Only enabled (submitted) budgets can be disabled."}
         
    doc.cancel()
    return {"status": "success", "message": f"Budget {budget_id} disabled (cancelled)."}

@frappe.whitelist(allow_guest=True)
def enable_budget(budget_id):
    """
    Re-enables a disabled (cancelled) budget by creating a new amended version and submitting it.
    """
    if not frappe.db.exists("Budget", budget_id):
        return {"status": "error", "message": f"Budget {budget_id} not found."}
        
    doc = frappe.get_doc("Budget", budget_id)
    
    # If it's Draft (0), just submit it
    if doc.docstatus == 0:
        doc.submit()
        return {"status": "success", "message": f"Budget {budget_id} enabled."}
        
    # If it's Cancelled (2), we need to amend it
    if doc.docstatus == 2:
        new_doc = frappe.copy_doc(doc)
        new_doc.amended_from = doc.name
        new_doc.docstatus = 0
        new_doc.insert(ignore_permissions=True)
        new_doc.submit()
        return {"status": "success", "message": f"Budget re-enabled as new version {new_doc.name}.", "new_budget_id": new_doc.name}

    return {"status": "success", "message": f"Budget {budget_id} is already enabled."}

@frappe.whitelist(allow_guest=True)
def get_budgets(cost_center=None, fiscal_year=None):
    """
    Returns a list of budgets with their status.
    """
    filters = {}
    if cost_center:
        filters["cost_center"] = cost_center
    if fiscal_year:
        filters["fiscal_year"] = fiscal_year
        
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters["company"] = company
        
    budgets = frappe.db.get_all("Budget", 
        filters=filters, 
        fields=["name", "fiscal_year", "cost_center", "docstatus", "creation", "modified"],
        order_by="creation desc"
    )
    
    # Map docstatus to human readable status
    for b in budgets:
        if b.docstatus == 0:
            b["status"] = "Draft"
            b["enabled"] = False
        elif b.docstatus == 1:
            b["status"] = "Enabled"
            b["enabled"] = True
        elif b.docstatus == 2:
            b["status"] = "Disabled"
            b["enabled"] = False
            
    return {"status": "success", "data": budgets}

@frappe.whitelist(allow_guest=True)
def delete_budget(budget_id):
    """
    Deletes a budget. Only allowed if in Draft status.
    """
    if not frappe.db.exists("Budget", budget_id):
        return {"status": "error", "message": f"Budget {budget_id} not found."}
        
    doc = frappe.get_doc("Budget", budget_id)
    if doc.docstatus == 1:
        return {"status": "error", "message": "Cannot delete an active budget. Please disable it first."}
    
    # If Cancelled, we can delete
    frappe.delete_doc("Budget", budget_id)
    return {"status": "success", "message": f"Budget {budget_id} deleted."}
