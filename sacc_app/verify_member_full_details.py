import frappe
from sacc_app.member_api import get_member_full_details
import json

def run_test():
    print("Verifying Member Full Details API...")
    
    # Get an existing member
    member_id = frappe.db.get_value("SACCO Member", {}, "name")
    if not member_id:
        print("❌ Failure: No members found in database")
        return

    print(f"Testing for member: {member_id}")
    response = get_member_full_details(member_id=member_id)
    
    if response.get("status") == "success":
        data = response.get("data", {})
        print("✅ Success: API returned success status")
        
        # Check registration details
        if "registration_details" in data:
            print("✅ Registration Details found")
            # print(json.dumps(data["registration_details"], indent=4))
        else:
            print("❌ Failure: 'registration_details' missing")
            
        # Check financial summary
        financials = data.get("financial_summary", {})
        expected_keys = ["total_savings", "total_loan_outstanding", "total_welfare_contribution", "active_loans"]
        all_keys_found = True
        for key in expected_keys:
            if key in financials:
                print(f"✅ Financial field found: {key} = {financials[key]}")
            else:
                print(f"❌ Failure: Financial field missing: {key}")
                all_keys_found = False
        
        if all_keys_found:
            print("\nFinal Result: API is working correctly!")
    else:
        print(f"❌ Failure: API returned error: {response.get('message')}")

if __name__ == "__main__":
    run_test()
