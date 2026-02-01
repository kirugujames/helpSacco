import frappe
from sacc_app.member_api import get_member_list, edit_member

def run_test():
    print("Verifying Member API Updates...")
    
    # 1. Test get_member_list response fields
    print("\nTesting get_member_list...")
    response = get_member_list(limit_page_length=1)
    if response["status"] == "success" and response["data"]:
        member = response["data"][0]
        if "registration_fee_paid" in member:
            print(f"✅ Success: 'registration_fee_paid' found: {member['registration_fee_paid']}")
        else:
            print("❌ Failure: 'registration_fee_paid' NOT found in member data")
    else:
        print("❌ Failure: Could not fetch member list or list is empty")

    # 2. Test edit_member expanded payload
    print("\nTesting edit_member expanded payload...")
    # Get an existing member
    member_id = frappe.db.get_value("SACCO Member", {}, "name")
    if member_id:
        test_village = "Test Village 123"
        edit_response = edit_member(member_id=member_id, village=test_village)
        
        # Verify in DB
        updated_village = frappe.db.get_value("SACCO Member", member_id, "village")
        if updated_village == test_village:
            print(f"✅ Success: 'village' updated successfully for member {member_id}")
        else:
            print(f"❌ Failure: 'village' update failed. Expected: {test_village}, Got: {updated_village}")
    else:
        print("❌ Failure: No members found to test edit_member")

if __name__ == "__main__":
    run_test()
