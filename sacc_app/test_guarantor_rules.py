
import frappe
from sacc_app.api import apply_for_loan

def test_guarantor_rules():
    print("--- Testing Guarantor Requirements Enforcement ---")
    
    # 1. Setup - Member
    member_email = "guarantor_test@example.com"
    if not frappe.db.exists("SACCO Member", {"email": member_email}):
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Guarantor",
            "last_name": "Tester",
            "email": member_email,
            "phone": "0722333444",
            "national_id": "GUA_TEST_ID",
            "status": "Active",
            "registration_fee_paid": 1,
            "loan_eligible": 1
        })
        member.insert(ignore_permissions=True)
    
    member_name = frappe.db.get_value("SACCO Member", {"email": member_email}, "name")
    frappe.db.set_value("SACCO Member", member_name, {"status": "Active", "active_loan": None})
    frappe.db.commit()

    # 2. Setup - Product with min_guarantors = 2
    product_name = "Secure Loan"
    if not frappe.db.exists("SACCO Loan Product", product_name):
        frappe.get_doc({
            "doctype": "SACCO Loan Product",
            "product_name": product_name,
            "interest_rate": 10,
            "interest_period": "Annually",
            "interest_method": "Flat Rate",
            "max_repayment_period": 12,
            "requires_guarantor": 1,
            "min_guarantors": 2
        }).insert(ignore_permissions=True)
    else:
        frappe.db.set_value("SACCO Loan Product", product_name, {"requires_guarantor": 1, "min_guarantors": 2})
    
    frappe.db.commit()

    # 3. Test - Apply with 0 guarantors (should fail)
    print("\nCase 1: Applying with 0 guarantors...")
    res1 = apply_for_loan(member=member_name, amount=5000, loan_product=product_name, guarantors=[])
    print(f"Result: {res1}")
    assert res1.get("status") == "error"
    assert "requires guarantors" in res1.get("message")

    # 4. Test - Apply with 1 guarantor (should fail)
    print("\nCase 2: Applying with 1 guarantor...")
    res2 = apply_for_loan(member=member_name, amount=5000, loan_product=product_name, guarantors=[{"member": "G1", "amount": 2500}])
    print(f"Result: {res2}")
    assert res2.get("status") == "error"
    assert "requires at least 2 guarantors" in res2.get("message")

    # 5. Test - Apply with 2 guarantors (should succeed)
    print("\nCase 3: Applying with 2 guarantors...")
    res3 = apply_for_loan(member=member_name, amount=5000, loan_product=product_name, guarantors=[
        {"member": member_name, "amount": 2500}, # Self-guarantee for test simplicity
        {"member": member_name, "amount": 2500}
    ])
    print(f"Result: {res3}")
    assert res3.get("status") == "success"

    print("\n--- Guarantor Requirements Test Passed! ---")

if __name__ == "__main__":
    test_guarantor_rules()
