import frappe
from sacc_app.api import record_expense
from sacc_app.expense_api import (
    get_expense_dashboard_stats,
    get_expenses_by_category,
    get_monthly_expense_trends,
    get_all_expense_transactions,
    get_expense_details
)
import random

def run_verification():
    print("--- Verifying Expense APIs ---")
    
    # 1. Create some test expenses if none exist or just to be sure
    # Need valid expense accounts. Default Frappe often has 'Office Rent', 'Electricity', etc.
    expense_accounts = ["Office Rent", "Electricity", "Internet", "Travel", "Marketing"]
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Ensure accounts exist in the DB (mapping from account_name to name)
    valid_accounts = []
    for acc in expense_accounts:
        if frappe.db.exists("Account", {"account_name": acc, "company": company}):
            valid_accounts.append(acc)
            
    if not valid_accounts:
        # Try to find any expense account
        any_expense = frappe.db.get_value("Account", {"root_type": "Expense", "is_group": 0, "company": company}, "account_name")
        if any_expense:
            valid_accounts = [any_expense]
        else:
            print("❌ Error: No expense accounts found to test with.")
            # Return early or raise? Let's return.
            return
            
    print(f"Using expense accounts: {valid_accounts}")
    
    # Record a few expenses
    for i in range(3):
        acc = random.choice(valid_accounts)
        amount = random.randint(100, 5000)
        desc = f"Test Expense {i+1} - {acc}"
        res = record_expense(amount=amount, expense_account=acc, description=desc)
        if res.get("status") == "success":
            print(f"Recorded expense: {res.get('reference')}")
        else:
            print(f"Failed to record expense: {res.get('message')}")

    # 2. Test Dashboard Stats
    stats = get_expense_dashboard_stats()
    print(f"Dashboard Stats: {stats['data']}")
    assert stats['status'] == 'success'
    assert stats['data']['total_expense_mtd'] > 0
    
    # 3. Test Expenses by Category
    categories = get_expenses_by_category()
    print(f"Categories Breakdown: {len(categories['data'])} categories found")
    assert categories['status'] == 'success'
    
    # 4. Test Monthly Trends
    trends = get_monthly_expense_trends()
    print(f"Monthly Trends: {len(trends['data'])} months returned")
    assert trends['status'] == 'success'
    assert len(trends['data']) == 6
    
    # 5. Test Transaction List
    list_res = get_all_expense_transactions(limit_page_length=10)
    print(f"Transactions List: {len(list_res['data'])} items")
    assert list_res['status'] == 'success'
    if list_res['data']:
        first_id = list_res['data'][0]['id']
        
        # 6. Test Get Details
        detail_res = get_expense_details(first_id)
        print(f"Expense Detail for {first_id}: {detail_res['data']['category']} - {detail_res['data']['amount']}")
        assert detail_res['status'] == 'success'
        assert detail_res['data']['id'] == first_id

    print("✅ All Expense API verification tests passed!")

if __name__ == "__main__":
    run_verification()
