import frappe
from sacc_app.api import apply_for_loan, get_loan_products, get_all_loan_products
import random

def run_verification():
    print("--- Verifying Loan Repayment Period Configuration ---")
    
    # 1. Test get_loan_products
    products_res = get_loan_products()
    print(f"get_loan_products status: {products_res['status']}")
    if products_res['status'] == 'success':
        print(f"Found {len(products_res['products'])} products")
        for p in products_res['products']:
            print(f"Product: {p['type']}, Max Period: {p['max_period']}")
            assert "max_period" in p
    
    # 2. Test get_all_loan_products
    all_products_res = get_all_loan_products()
    print(f"get_all_loan_products status: {all_products_res['status']}")
    if all_products_res['status'] == 'success' and all_products_res['data']:
        p = all_products_res['data'][0]
        print(f"Detailed field check for {p['name']}: {p.keys()}")
        assert "max_repayment_period" in p
        assert "interest_period" in p
        
    # 3. Test apply_for_loan validation
    # Create/Get a member
    member_email = f"test_period_{random.randint(1000, 9999)}@example.com"
    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Period",
        "last_name": "Test",
        "email": member_email,
        "phone": "07" + str(random.randint(10000000, 99999999)),
        "national_id": "TEST_" + str(random.randint(1000, 9999)),
        "status": "Active",
        "registration_fee_paid": 1,
        "loan_eligible": 1
    }).insert(ignore_permissions=True)
    member.status = "Active"
    member.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Create a product with specific max period
    product_name = f"Test Period Product {random.randint(1000, 9999)}"
    product = frappe.get_doc({
        "doctype": "SACCO Loan Product",
        "product_name": product_name,
        "interest_rate": 10,
        "max_repayment_period": 12, # 12 months max
        "interest_period": "Monthly",
        "interest_method": "Flat Rate"
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    
    # A. Test valid period
    res_valid = apply_for_loan(member=member.name, amount=1000, loan_product=product_name, repayment_period=6)
    print(f"Apply (valid 6 months): {res_valid['status']}")
    assert res_valid['status'] == 'success'
    
    # B. Test invalid period (exceeding max)
    res_invalid = apply_for_loan(member=member.name, amount=1000, loan_product=product_name, repayment_period=24)
    print(f"Apply (invalid 24 months): {res_invalid['status']} - {res_invalid.get('message')}")
    assert res_invalid['status'] == 'error'
    assert "exceeds maximum allowed" in res_invalid.get('message')
    
    # C. Test default period (not provided)
    res_default = apply_for_loan(member=member.name, amount=1000, loan_product=product_name)
    print(f"Apply (default): {res_default['status']}")
    assert res_default['status'] == 'success'
    loan_id = res_default['loan_id']
    saved_period = frappe.db.get_value("SACCO Loan", loan_id, "repayment_period")
    print(f"Saved default period: {saved_period}")
    assert saved_period == 12

    print("✅ All repayment period configuration tests passed!")

if __name__ == "__main__":
    run_verification()
