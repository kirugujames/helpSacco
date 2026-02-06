import frappe
from sacc_app.api import record_expense

def run_verification():
    print("--- Verifying record_expense with vendor_name ---")
    
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    any_expense = frappe.db.get_value("Account", {"root_type": "Expense", "is_group": 0, "company": company}, "account_name")
    
    if not any_expense:
        print("❌ Error: No expense accounts found.")
        return

    # Test with vendor_name
    res = record_expense(amount=100, expense_account=any_expense, description="Test vendor", vendor_name="Google")
    print(f"Result with vendor: {res}")
    assert res.get("status") == "success"
    
    # Check remark
    remark = frappe.db.get_value("Journal Entry", res.get("reference"), "user_remark")
    print(f"Saved remark: {remark}")
    assert "Google: Test vendor" in remark
    
    # Test without vendor_name
    res2 = record_expense(amount=50, expense_account=any_expense, description="No vendor test")
    print(f"Result without vendor: {res2}")
    assert res2.get("status") == "success"
    
    remark2 = frappe.db.get_value("Journal Entry", res2.get("reference"), "user_remark")
    print(f"Saved remark (no vendor): {remark2}")
    assert remark2 == "No vendor test"

    print("✅ Vendor name verification passed!")

if __name__ == "__main__":
    run_verification()
