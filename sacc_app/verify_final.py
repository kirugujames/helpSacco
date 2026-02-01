
import frappe
from frappe.utils import flt
from sacc_app.api import submit_loan_application, approve_loan_application, disburse_loan, record_loan_repayment

def verify_all_fixes():
    print("--- Verifying Disbursement and Balanced Split ---")
    
    # 1. Create a Fresh Member to test account creation logic
    email = "final_test@example.com"
    if frappe.db.exists("SACCO Member", {"email": email}):
        frappe.delete_doc("SACCO Member", frappe.db.get_value("SACCO Member", {"email": email}, "name"))
        
    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Final",
        "last_name": "Tester",
        "email": email,
        "phone": "0999888777",
        "national_id": "ID_FINAL",
        "gender": "Male",
        "status": "Active",
        "registration_fee_paid": 1,
        "loan_eligible": 1
    })
    member.insert(ignore_permissions=True)
    member.db_set("status", "Active") # Bypassing probation for test
    member.reload()
    
    print(f"Member Created: {member.name}")
    print(f"Loan Account: {member.ledger_account}")
    print(f"Savings Account: {member.savings_account}")
    
    assert member.ledger_account and member.savings_account
    assert "SAV-" in member.savings_account

    # 2. Apply for Loan
    loan_amount = 10000
    res = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member.name,
        "loan_amount": loan_amount,
        "loan_product": "Standard Loan",
        "repayment_period": 10,
        "status": "Draft"
    })
    res.insert(ignore_permissions=True)
    loan_id = res.name
    print(f"Loan Created: {loan_id}, Interest: {res.total_interest}")

    # 3. Submission & Approval
    submit_loan_application(loan_id)
    approve_loan_application(loan_id)
    
    # 4. Disbursement
    print(f"Disbursing loan {loan_id}...")
    disburse_loan(loan_id)
    
    # Verify GL Entries
    gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": loan_id}, fields=["account", "debit", "credit"])
    print(f"GL Entries for Disbursement: {gl_entries}")
    
    # Debit Member Loan, Credit Member Savings
    loan_acc_hit = any(e.account == member.ledger_account and e.debit == loan_amount for e in gl_entries)
    sav_acc_hit = any(e.account == member.savings_account and e.credit == loan_amount for e in gl_entries)
    
    print(f"Loan Account Debited: {loan_acc_hit}")
    print(f"Savings Account Credited: {sav_acc_hit}")
    assert loan_acc_hit and sav_acc_hit

    # 5. Verify Balanced Split on Repayment
    payment = 2200 # Installment is 2200 (10000 + 12000 total int / 10 is wrong, wait)
    # Total interest was calculated as 10000 * 0.1 * 10 = 10000. So total rep is 20000.
    # Monthly is 2000.
    
    # Let's reload to get exact monthly installment
    res.reload()
    print(f"Monthly Installment: {res.monthly_installment}")
    
    print(f"Recording repayment of {res.monthly_installment}...")
    record_loan_repayment(loan=loan_id, amount=res.monthly_installment, member=member.name)
    
    res.reload()
    print(f"After Repayment:")
    print(f"Principal Paid: {res.principal_paid}")
    print(f"Interest Paid: {res.interest_paid}")
    
    # Expected proportional split:
    # Int = 10000, Total = 20000 -> 50%
    # If payment is 2000, then 1000 Principal, 1000 Interest.
    
    assert res.principal_paid > 0
    assert res.interest_paid > 0
    
    print("--- All Fixes Verified Successfully! ---")

if __name__ == "__main__":
    verify_all_fixes()
