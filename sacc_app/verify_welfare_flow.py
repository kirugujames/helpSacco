import frappe
from frappe.utils import flt
# Need to import from the app module where it is installed
from sacc_app.welfare_claims_api import create_welfare_claim, approve_welfare_claim

def test_welfare_flow():
    # frappe.db.begin() # bench execute already does this? or not?
    # bench execute wraps in transaction but commits if no error?
    # Actually bench execute commits at the end if successful.
    
    try:
        # 1. Setup Settings
        settings = frappe.get_single("SACCO Settings")
        settings.welfare_contribution_amount = 500
        settings.save()
        # No need to commit here if bench execute handles transaction, 
        # but to be safe we can commit if we want intermediate saves to persist 
        # even if later steps fail? No, better rollback on failure.
        frappe.db.commit() 
        print("PASS: Settings configured with welfare_contribution_amount = 500")

        # Get a member
        member = frappe.db.get_value("SACCO Member", {"status": "Active"}, "name")
        if not member:
            print("SKIP: No active member found to test with.")
            # Create one?
            member = frappe.get_doc({
                "doctype": "SACCO Member",
                "first_name": "Test",
                "last_name": "Member",
                "status": "Active",
                "registration_fee_paid": 1
            }).insert().name
            print(f"Created temp member {member}")

        # 2. Test Contribution Validation
        # Case A: Below limit
        try:
            doc = frappe.get_doc({
                "doctype": "SACCO Welfare",
                "member": member,
                "type": "Contribution",
                "contribution_amount": 400,
                "posting_date": "2024-02-07",
                "purpose": "Monthly Contribution"
            })
            doc.insert()
            print("FAIL: Contribution of 400 should have been rejected (Limit 500)")
        except Exception as e:
            if "Contribution amount must be at least 500" in str(e):
                print("PASS: Contribution of 400 rejected as expected.")
            else:
                print(f"FAIL: Unexpected error for 400: {e}")
        
        # Case B: Above limit
        try:
            doc = frappe.get_doc({
                "doctype": "SACCO Welfare",
                "member": member,
                "type": "Contribution",
                "contribution_amount": 500,
                "posting_date": "2024-02-07",
                "purpose": "Monthly Contribution"
            })
            doc.insert()
            print("PASS: Contribution of 500 accepted.")
        except Exception as e:
            print(f"FAIL: Contribution of 500 rejected: {e}")

        # 3. Test Claim Approval
        # Create Claim
        claim_res = create_welfare_claim(member, "Medical Emergency", 10000, "Test Claim")
        claim_id = claim_res["data"]["claim_id"]
        print(f"PASS: Created Claim {claim_id}")

        # Approve Claim
        try:
            approve_res = approve_welfare_claim(claim_id, 100)
            
            if approve_res["status"] == "success" and \
               approve_res["data"]["status"] == "Approved" and \
               approve_res["data"]["amount_per_member"] == 100:
                print("PASS: Claim approved successfully with amount_per_member=100")
            else:
                print(f"FAIL: Claim approval failed or data mismatch. Res: {approve_res}")

            # Verify in DB
            claim_doc = frappe.get_doc("SACCO Welfare Claim", claim_id)
            if claim_doc.status == "Approved" and claim_doc.amount_per_member == 100:
                 print("PASS: DB Verification successful.")
            else:
                 print(f"FAIL: DB State mismatch. Status={claim_doc.status}, Amount={claim_doc.amount_per_member}")
        except Exception as e:
            print(f"FAIL: Claim approval error: {e}")

    except Exception as e:
        frappe.db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
