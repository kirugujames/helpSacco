import frappe
from sacc_app.api import record_savings_deposit, record_savings_withdrawal

def test_withdrawal_fix():
    print("--- Testing Savings Withdrawal Fix ---")
    
    # 1. Create a test member
    suffix = frappe.utils.now_datetime().strftime("%f")
    member_name = f"TEST-WITHDRAW-{suffix}"
    
    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Test",
        "last_name": f"User {suffix}",
        "email": f"testw_{suffix}@example.com",
        "phone": f"0712{suffix[:6]}",
        "national_id": f"ID{suffix}",
        "status": "Active",
        "registration_fee_paid": 1
    })
    member.insert(ignore_permissions=True)
    member_id = member.name
    print(f"Created test member: {member_id}")

    # Ensure accounts are provisioned (usually happens after_insert, but let's be sure)
    member.reload()
    if not member.savings_account:
        print("Waiting for accounts...")
        import time
        time.sleep(1)
        member.reload()

    # 2. Record a deposit first (to have balance)
    print(f"Recording deposit for {member_id}...")
    record_savings_deposit(member=member_id, amount=5000, mode="Cash")
    
    # 3. Record a withdrawal
    print(f"Recording withdrawal for {member_id}...")
    try:
        res = record_savings_withdrawal(member=member_id, amount=2000, mode="Cash")
        print(f"Success: {res}")
    except Exception as e:
        print(f"Failed! Error: {e}")
        import traceback
        traceback.print_exc()
        raise e

    print("--- Savings Withdrawal Fix Verified ---")

if __name__ == "__main__":
    test_withdrawal_fix()
