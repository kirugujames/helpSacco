
import frappe
from sacc_app.api import disburse_loan

def test_fresh_loan():
    member_id = "MEM-00008"
    print(f"--- Testing Fresh Loan for {member_id} ---")
    
    # 1. Create a Draft Loan
    loan = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member_id,
        "loan_amount": 15000,
        "loan_product": "Standard Loan",
        "repayment_period": 10,
        "status": "Approved" # Bypass approval for test
    })
    loan.insert(ignore_permissions=True)
    loan_id = loan.name
    print(f"Created loan {loan_id}. Status: {loan.status}")
    
    # 2. Disburse
    print(f"Attempting disbursement via API...")
    try:
        res = disburse_loan(loan_id)
        print(f"Response: {res}")
        frappe.db.commit() # Ensure committed for debug visibility
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Check Loan Status in DB
    frappe.db.begin() # Start new transaction to read
    db_loan = frappe.get_doc("SACCO Loan", loan_id)
    print(f"\nDB State - Status: {db_loan.status} | DocStatus: {db_loan.docstatus}")
    
    # 4. Check GL
    gles = frappe.db.get_all("GL Entry", filters={"user_remark": ["like", f"%{loan_id}%"]}, fields=["name", "account", "debit", "credit"])
    print(f"GL Entries found: {len(gles)}")
    for g in gles:
        print(f"  {g.account:30} | Dr: {g.debit:10} | Cr: {g.credit:10}")

if __name__ == "__main__":
    test_fresh_loan()
