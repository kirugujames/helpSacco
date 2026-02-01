
import frappe
from frappe.utils import flt, nowdate, add_months
import json

def test_interest_methods():
    print("--- Testing Interest Calculation Methods ---")
    
    # Setup Member
    member_email = "interest_test@example.com"
    member_name = frappe.db.get_value("SACCO Member", {"email": member_email}, "name")
    if not member_name:
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Interest",
            "last_name": "Tester",
            "email": member_email,
            "phone": "0711222333",
            "national_id": "INT_TEST_ID",
            "status": "Active",
            "registration_fee_paid": 1,
            "loan_eligible": 1
        })
        member.insert(ignore_permissions=True)
        member_name = member.name
    
    frappe.db.set_value("SACCO Member", member_name, {
        "status": "Active",
        "registration_fee_paid": 1,
        "loan_eligible": 1,
        "active_loan": None
    })
    frappe.db.commit()
    member = frappe.get_doc("SACCO Member", member_name)

    # 1. Test Flat Rate
    print("\n[Testing Flat Rate]")
    product_flat = "Flat Product"
    if not frappe.db.exists("SACCO Loan Product", product_flat):
        frappe.get_doc({
            "doctype": "SACCO Loan Product",
            "product_name": product_flat,
            "interest_rate": 10,
            "interest_period": "Annually",
            "interest_method": "Flat Rate",
            "max_repayment_period": 12
        }).insert(ignore_permissions=True)
        
    loan_flat = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member.name,
        "loan_amount": 12000,
        "loan_product": product_flat,
        "repayment_period": 12,
        "status": "Approved"
    })
    loan_flat.insert(ignore_permissions=True)
    loan_flat.submit()
    loan_flat.reload()
    
    # Expected: 12000 * 0.10 * (12/12) = 1200 Interest. Total = 13200. Installment = 1100.
    print(f"Flat Rate - Total Interest: {loan_flat.total_interest}")
    print(f"Flat Rate - Monthly Installment: {loan_flat.monthly_installment}")
    assert abs(loan_flat.total_interest - 1200) < 0.1
    assert abs(loan_flat.monthly_installment - 1100) < 0.1

    # 2. Test Reducing Balance
    print("\n[Testing Reducing Balance]")
    product_red = "Reducing Product"
    if not frappe.db.exists("SACCO Loan Product", product_red):
        frappe.get_doc({
            "doctype": "SACCO Loan Product",
            "product_name": product_red,
            "interest_rate": 12, # 12% annual = 1% monthly
            "interest_period": "Annually",
            "interest_method": "Reducing Balance",
            "max_repayment_period": 12
        }).insert(ignore_permissions=True)
        
    # Clear active loan for second test
    frappe.db.set_value("SACCO Member", member.name, "active_loan", None)
    frappe.db.commit()

    loan_red = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member.name,
        "loan_amount": 10000,
        "loan_product": product_red,
        "repayment_period": 12,
        "status": "Approved"
    })
    loan_red.insert(ignore_permissions=True)
    loan_red.submit()
    loan_red.reload()
    
    # For P=10000, r=0.01, n=12 -> EMI should be 888.49
    print(f"Reducing Balance - Total Interest: {loan_red.total_interest}")
    print(f"Reducing Balance - Monthly Installment: {loan_red.monthly_installment}")
    assert abs(loan_red.monthly_installment - 888.49) < 0.1
    
    # Verify schedule portions
    schedule = json.loads(loan_red.repayment_schedule)
    # First month: Interest = 10000 * 0.01 = 100. Principal = 888.49 - 100 = 788.49.
    print(f"First Month - Principal: {schedule[0]['principal']}, Interest: {schedule[0]['interest']}")
    assert abs(schedule[0]['interest'] - 100) < 0.1
    
    # Last month: Interest should be much lower
    print(f"Last Month - Principal: {schedule[-1]['principal']}, Interest: {schedule[-1]['interest']}")
    assert schedule[-1]['interest'] < 10

    print("\n--- Interest Methods Test Passed! ---")

if __name__ == "__main__":
    test_interest_methods()
