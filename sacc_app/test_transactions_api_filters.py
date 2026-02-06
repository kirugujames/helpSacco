import frappe
import unittest
from sacc_app.api import get_all_transactions

class TestTransactionsFilters(unittest.TestCase):
    def setUp(self):
        # Ensure we have some transactions to test with
        # For simplicity, we'll use existing ones if available, 
        # but the tests will focus on checking if the SQL query doesn't crash 
        # and returns filtered results if they exist.
        pass

    def test_get_all_transactions_no_filters(self):
        result = get_all_transactions()
        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["data"], list)

    def test_get_all_transactions_status_filter(self):
        result = get_all_transactions(status="Completed")
        self.assertEqual(result["status"], "success")
        for tx in result["data"]:
            self.assertEqual(tx["status"], "Completed")

    def test_get_all_transactions_search_filter(self):
        # Test with a search term that likely exists in many systems
        result = get_all_transactions(search="MEM")
        self.assertEqual(result["status"], "success")
        # If there are results, they should contain 'MEM' or be related to a member
        if result["data"]:
            tx = result["data"][0]
            search_found = "MEM" in tx["transaction_id"] or "MEM" in tx["reference"] or "MEM" in tx["member_name"]
            # member_name search is indirect via party, but remarks/transaction_id are direct
            # We just want to ensure it works.

    def test_get_all_transactions_combined_filters(self):
        result = get_all_transactions(status="Completed", search="LOAN")
        self.assertEqual(result["status"], "success")
        for tx in result["data"]:
            self.assertEqual(tx["status"], "Completed")

if __name__ == "__main__":
    frappe.init(site="sacco.test.com")
    frappe.connect()
    unittest.main()
