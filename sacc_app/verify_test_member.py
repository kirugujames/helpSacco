import frappe
from sacc_app.api import generate_loan_ready_member

def verify():
    print("Testing generate_loan_ready_member API...")
    
    # Generate Member
    res = generate_loan_ready_member(savings_amount=50000)
    
    if res.get("status") != "success":
        print(f"❌ Generation Failed: {res.get('message')}")
        return
        
    data = res.get("data")
    member_id = data.get("member_id")
    print(f"Generated Member ID: {member_id}")
    
    # Verify Member Status
    member = frappe.get_doc("SACCO Member", member_id)
    if member.status == "Active":
        print("✅ Member Status is Active")
    else:
        print(f"❌ Member Status is {member.status} (Expected Active)")
        
    if member.registration_fee_paid:
        print("✅ Registration Fee is marked as Paid")
    else:
        print("❌ Registration Fee is NOT Paid")
        
    # Verify Savings
    savings_balance = frappe.db.get_value("SACCO Member", member_id, "total_savings")
    print(f"Total Savings: {savings_balance}")
    
    if float(savings_balance) == 50000.0:
        print("✅ Initial Savings Deposit Verified")
    else:
        print(f"❌ Savings Mismatch. Expected 50000.0, got {savings_balance}")

if __name__ == "__main__":
    pass
