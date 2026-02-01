
import frappe

def debug_transactions():
    # 1. Check Member
    member_id = "MEM-00008"
    m = frappe.get_doc("SACCO Member", member_id)
    print(f"--- Member {member_id} ---")
    print(f"Active Loan Field: {m.active_loan}")
    print(f"Customer Link: {m.customer_link}")
    
    # 2. Check Loan
    loan_id = "LN-00004"
    if frappe.db.exists("SACCO Loan", loan_id):
        l = frappe.get_doc("SACCO Loan", loan_id)
        print(f"\n--- Loan {loan_id} ---")
        print(f"DocStatus: {l.docstatus}")
        print(f"Status: {l.status}")
        print(f"Outstanding: {l.outstanding_balance}")
    else:
        print(f"\nLoan {loan_id} not found.")

    # 3. Check ANY GL entries
    print("\n--- Last 10 GL Entries ---")
    entries = frappe.get_all("GL Entry", limit=10, order_by="creation desc", 
                            fields=["name", "voucher_no", "account", "debit", "credit"])
    for e in entries:
        print(f"{e.name:20} | {e.voucher_no:20} | {e.account:30} | {e.debit:10}")

    # 4. Check ANY SACCO Loan records
    print("\n--- All SACCO Loans ---")
    loans = frappe.get_all("SACCO Loan", fields=["name", "member", "status", "docstatus"])
    for ln in loans:
        print(f"{ln.name:10} | {ln.member:10} | {ln.status:15} | {ln.docstatus}")

if __name__ == "__main__":
    debug_transactions()
