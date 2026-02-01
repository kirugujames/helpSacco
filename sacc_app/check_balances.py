
import frappe
from frappe.utils import flt

def check_balances():
    member_id = "MEM-00008"
    m = frappe.get_doc("SACCO Member", member_id)
    
    print(f"--- Balances for {member_id} ---")
    print(f"Member Field total_savings: {m.total_savings}")
    print(f"Member Field active_loan: {m.active_loan}")
    
    # 1. Check GL for Loan Account
    loan_bal = frappe.db.get_value("GL Entry", {"account": m.ledger_account}, "sum(debit) - sum(credit)") or 0
    print(f"GL Balance (Loan Account {m.ledger_account}): {loan_bal}")
    
    # 2. Check GL for Savings Account
    sav_bal = frappe.db.get_value("GL Entry", {"account": m.savings_account}, "sum(credit) - sum(debit)") or 0
    print(f"GL Balance (Savings Account {m.savings_account}): {sav_bal}")

    # 3. Check Loans
    loans = frappe.get_all("SACCO Loan", filters={"member": member_id}, fields=["name", "status", "loan_amount", "outstanding_balance", "docstatus"])
    print("\n--- Loans for Member ---")
    for l in loans:
        print(f"{l.name:10} | {l.status:15} | Amt: {l.loan_amount:10} | Out: {l.outstanding_balance:10} | DocStatus: {l.docstatus}")

if __name__ == "__main__":
    check_balances()
