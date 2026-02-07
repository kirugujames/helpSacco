
import frappe
from sacc_app.api import create_account, update_account, delete_account, get_account_statement, get_all_accounts

def run():
    print("--- Starting Account API Verification ---")
    
    # Prerequisite: Find a parent account (Must be a GROUP)
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Try finding "Administrative Expenses" if it is a group
    parent_doc = frappe.db.get_value("Account", {"account_name": "Administrative Expenses", "is_group": 1, "company": company}, ["name", "account_name"], as_dict=True)
    
    if not parent_doc:
        # Try finding ANY expense group
        parent_doc = frappe.db.get_value("Account", {"is_group": 1, "root_type": "Expense", "company": company}, ["name", "account_name"], as_dict=True)
        
    if not parent_doc:
        # One last try: "Expenses" root (which should be a group)
        parent_doc = frappe.db.get_value("Account", {"account_name": "Expenses", "is_group": 1, "company": company}, ["name", "account_name"], as_dict=True)

    if not parent_doc:
        print("!! Could not find a parent GROUP account for testing. Skipping creation tests.")
        # List some potential parents for debugging
        print("Available Expense Groups:")
        groups = frappe.db.get_all("Account", {"is_group": 1, "root_type": "Expense", "company": company}, ["name", "account_name"])
        for g in groups:
             print(f"- {g.account_name}")
        return

    print(f"Using Parent Account: {parent_doc.account_name} ({parent_doc.name})")
    
    # 1. Test Creation
    print("\n1. Testing create_account...")
    acc_name = "Test API Account"
    
    # Cleanup if exists
    if frappe.db.exists("Account", {"account_name": acc_name, "company": company}):
        print("Existing test account found, cleaning up...")
        try:
             delete_account(acc_name)
        except Exception as e:
             print(f"Cleanup failed: {e}")
        
    # Determine appropriate account type
    acc_type = parent_doc.get("account_type")
    if not acc_type:
        # If parent has no type, assume Indirect Expense for testing
        acc_type = "Indirect Expense"
        
    print(f"Creating account with type: {acc_type}")
        
    res = create_account(acc_name, parent_doc.account_name, is_group=0, account_type=acc_type)
    print(f"Creation Result: {res}")
    
    if res['status'] != 'success':
        print("!! Creation failed.")
        return
        
    # 2. Test Update
    print("\n2. Testing update_account (renaming)...")
    new_name = "Test API Account Updated"
    
    # If updated name already exists (from failed prev run), delete it
    if frappe.db.exists("Account", {"account_name": new_name, "company": company}):
         try:
             delete_account(new_name)
         except:
             pass

    res_upd = update_account(acc_name, {"account_name": new_name})
    print(f"Update Result: {res_upd}")
    
    if res_upd['status'] == 'success' and frappe.db.exists("Account", {"account_name": new_name, "company": company}):
        print(">> Update successful.")
        acc_name = new_name # Track new name
    else:
        print(f"!! Update failed: {res_upd.get('message')}")
        
    # 3. Test Get Statement (by Account Name)
    print("\n3. Testing get_account_statement (by Account)...")
    try:
        # Pass account explicitly
        res_stmt = get_account_statement(account=acc_name)
        print(f"Result Status: {res_stmt.get('status')}")
        if res_stmt.get('status') == 'success':
            print(f"Statement generation successful.")
        else:
            print(f"!! Failed: {res_stmt.get('message')}")
    except Exception as e:
        print(f"!! Failed with Exception: {type(e).__name__}: {e}")

    # 4. Test Get Statement (by Member) - Bug Fix Verification
    print("\n4. Testing get_account_statement (by Member)...")
    # Find a member
    member = frappe.db.get_value("SACCO Member", {"status": "Active"}, "name") or "MEM-00146" # Fallback to user example ID
    
    if member:
        print(f"Testing with Member ID: {member}")
        try:
            # Pass ONLY member, account should be None (default)
            # This calls the function using keyword argument 'member', effectively testing the fix
            res_mem = get_account_statement(member=member)
            
            if res_mem and res_mem.get('status') == 'success':
                 print(">> Success! Bug fixed (get_account_statement accepts member argument without account).")
            else:
                 print(f"!! Failed (returned error): {res_mem.get('message')}")
                 
        except TypeError as te:
            print(f"!! FAILED with TypeError (Bug still exists!): {te}")
        except Exception as e:
             print(f"!! Failed with other error: {type(e).__name__}: {e}")
    else:
        print("!! No active member found to test.")

    # 5. Test Deletion
    print("\n5. Testing delete_account...")
    # Add a delay or check if account is locked? Usually fine.
    res_del = delete_account(acc_name)
    print(f"Deletion Result: {res_del}")
    
    if not frappe.db.exists("Account", {"account_name": acc_name, "company": company}):
        print(">> Deletion verification successful.")
    else:
         print("!! Account still exists.")

    print("\n--- Verification Complete ---")
