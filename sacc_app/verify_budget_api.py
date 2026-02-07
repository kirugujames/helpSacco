import frappe
from sacc_app.budget_api import create_budget_request, approve_budget, disable_budget, enable_budget, get_budgets, delete_budget
from frappe.utils import nowdate, getdate

def run():
    print("--- Starting Budget API Verification ---")
    
    # 1. Setup Data
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Ensure Fiscal Year
    # Try to find a fiscal year that contains today
    today = nowdate()
    existing_fy = frappe.db.sql("""
        select name from `tabFiscal Year`
        where %s between year_start_date and year_end_date
        limit 1
    """, (today,))
    
    if existing_fy and existing_fy[0][0]:
        year_name = existing_fy[0][0]
        print(f"Using existing Fiscal Year: {year_name}")
    else:
        # Fallback: Find *any* fiscal year
        any_fy = frappe.db.get_all("Fiscal Year", limit=1)
        if any_fy:
             year_name = any_fy[0].name
             print(f"Using fallback Fiscal Year: {year_name}")
        else:
             print("!! No Fiscal Year found and creation logic might fail. Aborting.")
             return
        
    # Ensure Cost Center
    cc_name = "Test Cost Center"
    if not frappe.db.exists("Cost Center", {"cost_center_name": cc_name, "company": company}):
        # Find a parent cost center
        parent_cc = frappe.db.get_value("Cost Center", {"is_group": 1, "company": company})
        if not parent_cc:
             # Create a root if needed? Usually exists.
             pass
             
        cc = frappe.new_doc("Cost Center")
        cc.cost_center_name = cc_name
        cc.parent_cost_center = parent_cc
        cc.company = company
        cc.insert(ignore_permissions=True)
        cc_name = cc.name # Update to actual ID
        print(f"Created Cost Center: {cc_name}")
    else:
        cc_name = frappe.db.get_value("Cost Center", {"cost_center_name": cc_name, "company": company}, "name")
        print(f"Using Cost Center: {cc_name}")
        
    # Get an Expense Account (Must be Ledger)
    expense_acc = frappe.db.get_value("Account", {"account_name": "Indirect Expenses", "company": company, "is_group": 0}, "name")
    if not expense_acc:
        # Try generic search for any expense ledger
        expense_acc = frappe.db.get_value("Account", {"root_type": "Expense", "is_group": 0, "company": company}, "name")
        
    if not expense_acc:
        print("!! No Expense Ledger Account found. Skipping.")
        return

    print(f"Using Expense Account: {expense_acc}")

    # 2. Test Create Budget
    print("\n2. Testing create_budget_request...")
    items = [{"account": expense_acc, "budget_amount": 50000}]
    
    res = create_budget_request(cc_name, year_name, items)
    print(f"Creation Result: {res}")
    
    if res['status'] != 'success':
        print("!! Creation failed.")
        return
        
    budget_id = res['budget_id']
    
    # 3. Test Approve (Enable)
    print("\n3. Testing approve_budget...")
    res_app = approve_budget(budget_id)
    print(f"Approval Result: {res_app}")
    
    doc = frappe.get_doc("Budget", budget_id)
    if doc.docstatus == 1:
        print(">> Budget is Active (Submitted).")
    else:
        print("!! Budget format incorrect.")
        
    # 4. Test Disable
    print("\n4. Testing disable_budget...")
    res_dis = disable_budget(budget_id)
    print(f"Disable Result: {res_dis}")
    
    doc.reload()
    if doc.docstatus == 2:
        print(">> Budget is Disabled (Cancelled).")
    else:
        print("!! Budget not cancelled.")
        
    # 5. Test Enable (Re-enable)
    print("\n5. Testing enable_budget...")
    res_en = enable_budget(budget_id)
    print(f"Enable Result: {res_en}")
    
    new_budget_id = res_en.get("new_budget_id") or budget_id
    if new_budget_id != budget_id:
        print(f">> Created new amended budget: {new_budget_id}")
        
    doc_new = frappe.get_doc("Budget", new_budget_id)
    if doc_new.docstatus == 1:
        print(">> New Budget is Active.")
    else:
        print("!! New Budget not active.")
        
    # 6. Test Get Budgets
    print("\n6. Testing get_budgets...")
    res_list = get_budgets(cost_center=cc_name, fiscal_year=year_name)
    print(f"Found {len(res_list['data'])} budgets.")
    if len(res_list['data']) > 0:
        print(f"Top entry status: {res_list['data'][0].get('status')}")
        
    # 7. Test Delete (Clean up)
    # First must be disabled/draft. The new one is Active.
    print("\n7. Testing delete_budget...")
    # Try deleting active (Should fail)
    res_del_fail = delete_budget(new_budget_id)
    print(f"Delete Active Result (Expected Fail): {res_del_fail}")
    
    # Disable first
    disable_budget(new_budget_id)
    # Delete cancelled
    res_del = delete_budget(new_budget_id)
    print(f"Delete Cancelled Result: {res_del}")
    
    if not frappe.db.exists("Budget", new_budget_id):
        print(">> Deletion successful.")

    print("\n--- Verification Complete ---")
