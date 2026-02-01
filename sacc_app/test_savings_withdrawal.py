
import frappe
from frappe.utils import flt
from sacc_app.api import record_savings_deposit, record_savings_withdrawal

def test_savings_withdrawal():
    print("--- Testing Savings Withdrawal ---")
    
    # 1. Setup - Member
    member_email = "withdrawal_test@example.com"
    member_name = frappe.db.get_value("SACCO Member", {"email": member_email}, "name")
    if not member_name:
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Withdrawal",
            "last_name": "Tester",
            "email": member_email,
            "phone": "0733444555",
            "national_id": "WITH_TEST_ID",
            "status": "Active"
        })
        member.insert(ignore_permissions=True)
        member_name = member.name
    else:
        member = frappe.get_doc("SACCO Member", member_name)
    
    frappe.db.set_value("SACCO Member", member_name, {"status": "Active", "total_savings": 0})
    
    # Isolated test: clear any previous test data for this member
    frappe.db.sql("DELETE FROM `tabSACCO Savings` WHERE member = %s", (member_name,))
    
    frappe.db.commit()
    member = frappe.get_doc("SACCO Member", member_name)
    member.reload()

    # 2. Deposit 5000
    print("\nStep 1: Depositing 5000...")
    record_savings_deposit(member=member_name, amount=5000)
    
    # Debug info
    all_savings = frappe.get_all("SACCO Savings", filters={"member": member_name, "docstatus": 1}, fields=["name", "type", "amount"])
    print(f"All Submitted Savings Records for {member_name}: {all_savings}")
    
    # Check the SQL query used in the DocType
    raw_total = frappe.db.sql("""
        SELECT SUM(CASE WHEN type = 'Deposit' THEN amount ELSE -amount END)
        FROM `tabSACCO Savings`
        WHERE member = %s AND docstatus = 1
    """, (member_name,))[0][0] or 0
    print(f"Raw SQL Total for {member_name}: {raw_total}")

    member.reload()
    print(f"Current Savings in Member Doc: {member.total_savings}")
    assert abs(flt(member.total_savings) - 5000) < 0.1

    # 3. Try to withdraw 6000 (should fail)
    print("\nStep 2: Attempting to withdraw 6000 (should fail)...")
    try:
        record_savings_withdrawal(member=member_name, amount=6000)
        print("Error: Withdrawal of 6000 succeeded, but should have failed!")
        assert False
    except frappe.exceptions.ValidationError as e:
        print(f"Caught expected validation error: {e}")
        assert "Insufficient savings balance" in str(e)

    # 4. Withdraw 2000 (should succeed)
    print("\nStep 3: Withdrawing 2000...")
    res = record_savings_withdrawal(member=member_name, amount=2000)
    print(f"Result: {res}")
    assert res.get("status") == "success"
    
    # Force direct DB check
    db_total = frappe.db.get_value("SACCO Member", member_name, "total_savings")
    print(f"Direct DB Total for Member {member_name}: {db_total}")
    
    member.reload()
    print(f"Final Savings in Member Doc: {member.total_savings}")
    assert abs(flt(member.total_savings) - 3000) < 0.1

    print("\n--- Savings Withdrawal Test Passed! ---")

if __name__ == "__main__":
    test_savings_withdrawal()
