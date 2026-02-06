import frappe
import unittest
from sacc_app.api import (
    get_savings_dashboard, 
    get_savings_vs_expense, 
    get_top_savers, 
    get_savings_transactions
)
from frappe.utils import now_datetime, get_first_day, get_last_day

class TestSavingsDashboardApi(unittest.TestCase):
    def setUp(self):
        # Create a test member with a unique suffix
        suffix = frappe.utils.now_datetime().strftime("%f")
        member_name = f"TEST-SAVER-{suffix}"
        
        if not frappe.db.exists("SACCO Member", member_name):
            member = frappe.get_doc({
                "doctype": "SACCO Member",
                "name": member_name,
                "first_name": "Test",
                "last_name": f"Saver {suffix}",
                "email": f"testsaver_{suffix}@example.com",
                "phone": f"07{suffix[:8]}",
                "national_id": f"ID{suffix}",
                "status": "Active",
                "registration_fee_paid": 1,
                "loan_eligible": 1
            })
            member.insert(ignore_permissions=True)
            self.member_id = member.name
        else:
            self.member_id = member_name
        
        # Create a test deposit
        savings = frappe.get_doc({
            "doctype": "SACCO Savings",
            "member": self.member_id,
            "type": "Deposit",
            "amount": 1000,
            "posting_date": frappe.utils.today(),
            "payment_mode": "M-Pesa"
        })
        savings.insert(ignore_permissions=True)
        savings.submit()

    def tearDown(self):
        frappe.db.rollback()

    def test_get_savings_dashboard(self):
        result = get_savings_dashboard()
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertIn("total_savings", data)
        self.assertIn("monthly_deposits", data)
        self.assertIn("active_savers_count", data)
        self.assertGreaterEqual(data["total_savings"], 1000)

    def test_get_savings_vs_expense(self):
        result = get_savings_vs_expense()
        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["data"], list)
        self.assertEqual(len(result["data"]), 6)
        # Check current month structure
        current_month = result["data"][-1]
        self.assertIn("month", current_month)
        self.assertIn("savings", current_month)
        self.assertIn("expense", current_month)

    def test_get_top_savers(self):
        result = get_top_savers()
        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["data"], list)
        self.assertLessEqual(len(result["data"]), 5)
        if result["data"]:
            first = result["data"][0]
            self.assertIn("member_name", first)
            self.assertIn("total_savings", first)

    def test_get_savings_transactions(self):
        result = get_savings_transactions(limit_page_length=5)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("pagination", result)
        if result["data"]:
            t = result["data"][0]
            self.assertIn("member_name", t)
            self.assertIn("amount", t)

    def test_get_savings_transactions_with_search(self):
        # Search by member name
        result = get_savings_transactions(searchTerm="Saver")
        self.assertEqual(result["status"], "success")
        if result["data"]:
            for t in result["data"]:
                self.assertIn("Saver", t.member_name)
        
        # Search by non-existent reference
        result = get_savings_transactions(searchTerm="NON_EXISTENT_REF_12345")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 0)

