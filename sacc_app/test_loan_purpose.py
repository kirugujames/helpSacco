import frappe
from sacc_app.api import apply_for_loan, get_loan_applications

def run_test():
    print("\n=== Testing Loan Purpose Field ===")
    
    # 1. Create a loan with a purpose
    member = "MEM-00182"
    product = frappe.db.get_value("SACCO Loan Product", {}, "name")
    
    if not member or not product:
        print("❌ Missing test data (member or product)")
        return

    test_purpose = "Business Expansion Test"
    print(f"   Creating loan for member {member} with product {product} and purpose '{test_purpose}'")
    
    result = apply_for_loan(
        member=member,
        amount=10000,
        loan_product=product,
        purpose=test_purpose
    )
    
    if result.get("status") == "success":
        loan_id = result.get("loan_id")
        print(f"   ✅ Loan created: {loan_id}")
        
        # 2. Verify in database
        db_purpose = frappe.db.get_value("SACCO Loan", loan_id, "purpose")
        if db_purpose == test_purpose:
            print(f"   ✅ Purpose correctly saved in database: {db_purpose}")
        else:
            print(f"   ❌ Purpose NOT correctly saved. Found: {db_purpose}")
            
        # 3. Verify in get_loan_applications API
        apps_result = get_loan_applications(loan_id=loan_id)
        if apps_result.get("status") == "success" and apps_result.get("data"):
            api_purpose = apps_result["data"][0].get("purpose")
            if api_purpose == test_purpose:
                print(f"   ✅ Purpose correctly returned by API: {api_purpose}")
            else:
                print(f"   ❌ Purpose NOT correctly returned by API. Found: {api_purpose}")
        else:
            print(f"   ❌ API call failed or returned no data")
    else:
        print(f"   ❌ Failed to create loan: {result.get('message')}")

if __name__ == "__main__":
    run_test()
