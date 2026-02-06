import frappe
import unittest
from sacc_app.api import (
    get_transactions_dashboard,
    get_all_transactions,
    get_transaction_details,
    record_savings_deposit,
    record_expense
)

class TestTransactionsApi(unittest.TestCase):
    def setUp(self):
        # Create a test member
        suffix = frappe.utils.now_datetime().strftime("%f")
        member_name = f"TEST-TX-MEMBER-{suffix}"
        
        if not frappe.db.exists("SACCO Member", member_name):
            member = frappe.get_doc({
                "doctype": "SACCO Member",
                "name": member_name,
                "first_name": "Test",
                "last_name": f"TX {suffix}",
                "email": f"testtx_{suffix}@example.com",
                "phone": f"07{suffix[:8]}",
                "national_id": f"TXID{suffix}",
                "status": "Active",
                "registration_fee_paid": 1,
                "loan_eligible": 1
            })
            member.insert(ignore_permissions=True)
            self.member_id = member.name
        else:
            self.member_id = member_name

        # Create some transactions
        # 1. Savings Deposit
        res = record_savings_deposit(self.member_id, 1000, mode="Cash", reference=f"REF-{suffix}")
        savings_name = res["id"]
        
        # Commit to ensure GL entries are visible
        frappe.db.commit()
        
        # Find the voucher_no from GL Entry. Try multiple ways.
        self.voucher_no = frappe.db.get_value("GL Entry", {"remarks": ["like", f"%{savings_name}%"]}, "voucher_no")
        
        if not self.voucher_no:
            # Fallback: Find any Journal Entry with this comment
            self.voucher_no = frappe.db.get_value("Journal Entry", {"user_remark": ["like", f"%{savings_name}%"]}, "name")
            
        print(f"DEBUG: Savings Name: {savings_name}, Voucher No: {self.voucher_no}")
        
        # 2. Expense
        # Need an expense account
        expense_acc = frappe.db.get_value("Account", {"root_type": "Expense", "is_group": 0}, "name")
        if expense_acc:
            record_expense(200, expense_acc, f"Test Expense {suffix}")

    def tearDown(self):
        frappe.db.rollback()

    def test_get_transactions_dashboard(self):
        result = get_transactions_dashboard()
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertIn("today_transactions_amount", data)
        self.assertIn("total_in", data)
        self.assertGreaterEqual(data["total_in"], 1000)

    def test_get_all_transactions(self):
        result = get_all_transactions(limit_page_length=5)
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertTrue(len(result["data"]) > 0)
        
        # Check first transaction
        tx = result["data"][0]
        self.assertIn("transaction_id", tx)
        self.assertIn("category", tx)
        self.assertIn("amount", tx)

    def test_get_transaction_details(self):
        # Use the voucher_no found in setUp
        result = get_transaction_details(self.voucher_no)
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["transaction_id"], self.voucher_no)
        self.assertTrue(len(data["accounts_affected"]) >= 2)
        
        # Check involved party
        parties = [p["name"] for p in data["parties_involved"]]
        expected_name = frappe.db.get_value("SACCO Member", self.member_id, "member_name")
        self.assertIn(expected_name, parties)
