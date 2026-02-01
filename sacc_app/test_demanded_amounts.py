
import frappe
from frappe.utils import flt, nowdate, add_months
import json

def test_demanded_amounts():
    print("--- Testing Demanded Amounts Calculation ---")
    
    # 1. Setup - Use an existing member or create one
    member_email = "test_demanded@example.com"
    if not frappe.db.exists("SACCO Member", {"email": member_email}):
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Test",
            "last_name": "Demanded",
            "email": member_email,
            "phone": "0700111222",
            "national_id": "TEST_DEM_ID",
            "status": "Active",
            "registration_fee_paid": 1,
            "loan_eligible": 1
        })
        member.insert(ignore_permissions=True)
        member.status = "Active"
        member.registration_fee_paid = 1
        member.loan_eligible = 1
        member.save(ignore_permissions=True)
        frappe.db.commit()
    
    member = frappe.get_doc("SACCO Member", frappe.db.get_value("SACCO Member", {"email": member_email}, "name"))
    if member.status != "Active":
        member.status = "Active"
        member.save(ignore_permissions=True)
        frappe.db.commit()

    # 2. Create a Loan
    loan = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member.name,
        "loan_amount": 12000,
        "loan_product": "Standard Loan",
        "repayment_period": 12,
        "status": "Approved"
    })
    loan.insert(ignore_permissions=True)
    loan.submit() # This will set state to Active and generate schedule
    loan.reload()
    
    print(f"Loan Created: {loan.name}")
    print(f"Total Repayable: {loan.total_repayable}")
    print(f"Monthly Installment: {loan.monthly_installment}")
    
    # 3. Initially demanded amounts should be 0 (if start date is now and first payment is next month)
    loan.update_demanded_amounts()
    print(f"Initial Principal Demanded: {loan.total_principal_demanded}")
    print(f"Initial Interest Demanded: {loan.total_interest_demanded}")
    
    # 4. Manipulate schedule to simulate months passed
    schedule = json.loads(loan.repayment_schedule)
    
    # Set first 3 installments to past dates
    for i in range(3):
        schedule[i]["payment_date"] = add_months(nowdate(), -(3-i))
        
    loan.repayment_schedule = json.dumps(schedule)
    loan.db_set("repayment_schedule", loan.repayment_schedule)
    
    # 5. Run update
    print("Simulated 3 months passing...")
    loan.update_demanded_amounts()
    
    print(f"Updated Principal Demanded: {loan.total_principal_demanded}")
    print(f"Updated Interest Demanded: {loan.total_interest_demanded}")
    
    # Expected: 3 times the installments portions
    total_total = flt(loan.total_repayable)
    p_ratio = flt(loan.loan_amount) / total_total
    i_ratio = flt(loan.total_interest) / total_total
    
    expected_p = round(flt(loan.monthly_installment) * p_ratio, 2) * 3
    expected_i = round(flt(loan.monthly_installment) * i_ratio, 2) * 3
    
    print(f"Expected Principal: {expected_p}")
    print(f"Expected Interest: {expected_i}")
    
    # Allow small rounding diff if any, but they should be close
    assert abs(loan.total_principal_demanded - expected_p) < 0.1
    assert abs(loan.total_interest_demanded - expected_i) < 0.1
    
    print("--- Demanded Amounts Test Passed! ---")

if __name__ == "__main__":
    test_demanded_amounts()
