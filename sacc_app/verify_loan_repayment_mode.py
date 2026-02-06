import frappe
from sacc_app.api import record_loan_repayment

def verify_mode():
    print("Testing record_loan_repayment with custom mode...")
    
    # 1. Create a unique member
    import random
    suffix = str(random.randint(1000, 9999))
    member_email = f"verify_repayment_{suffix}@example.com"
    phone = "070" + str(random.randint(1000000, 9999999))

    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Verify",
        "last_name": f"Repayment {suffix}",
        "email": member_email,
        "phone": phone,
        "national_id": f"VR{suffix}",
        "status": "Active",
        "registration_fee_paid": 1,
        "loan_eligible": 1
    }).insert(ignore_permissions=True)
    member.status = "Active"
    member.save(ignore_permissions=True)
    frappe.db.commit()
    
    member_id = frappe.db.get_value("SACCO Member", {"email": member_email}, "name")
    
    # 2. Ensure loan product exists
    product_name = "Standard Loan"
    if not frappe.db.exists("SACCO Loan Product", product_name):
        frappe.get_doc({
            "doctype": "SACCO Loan Product",
            "product_name": product_name,
            "interest_rate": 12,
            "max_repayment_period": 12,
            "interest_method": "Reducing Balance"
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    # 3. Create a loan
    loan = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member_id,
        "loan_amount": 5000,
        "loan_product": product_name,
        "repayment_period": 6,
        "status": "Approved"
    })
    loan.insert(ignore_permissions=True)
    loan.submit()
    
    loan_id = loan.name
    print(f"Created loan: {loan_id}")
    
    # 4. Record repayment with custom mode
    custom_mode = "M-Pesa"
    res = record_loan_repayment(loan=loan_id, amount=1000, member=member_id, mode=custom_mode, reference="REF123")
    
    if res["status"] == "success":
        repayment_id = res["id"]
        saved_mode = frappe.db.get_value("SACCO Loan Repayment", repayment_id, "payment_mode")
        print(f"Repayment recorded: {repayment_id}")
        print(f"Saved mode: {saved_mode}")
        
        if saved_mode == custom_mode:
            print("✅ Success: Custom mode correctly saved.")
        else:
            print(f"❌ Failure: Expected mode '{custom_mode}', but found '{saved_mode}'.")
    else:
        print(f"❌ Failure: API returned error: {res.get('message')}")

if __name__ == "__main__":
    verify_mode()
