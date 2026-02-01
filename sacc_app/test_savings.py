
import frappe
from sacc_app.api import record_savings_deposit

def test_savings_fix():
    print("--- Testing Savings Deposit Fix ---")
    
    # 1. Get a test member
    member = frappe.db.get_value("SACCO Member", {}, "name")
    if not member:
        print("No member found, creating one...")
        member_doc = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Test",
            "last_name": "User",
            "email": "test_savings@example.com",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "phone_number": "0000000000"
        })
        member_doc.insert(ignore_permissions=True)
        member = member_doc.name
    
    # 2. Record deposit WITHOUT reference
    print(f"Recording deposit for {member} without reference...")
    try:
        res = record_savings_deposit(member=member, amount=1000, mode="Cash")
        print(f"Success: {res}")
    except Exception as e:
        print(f"Failed as expected? Error: {e}")
        raise e

    # 3. Record deposit WITH reference
    print(f"Recording deposit for {member} with reference 'REF123'...")
    try:
        res = record_savings_deposit(member=member, amount=2000, mode="M-Pesa", reference="REF123")
        print(f"Success: {res}")
    except Exception as e:
        print(f"Failed: {e}")
        raise e

    print("--- Savings Deposit Fix Verified ---")

if __name__ == "__main__":
    test_savings_fix()
