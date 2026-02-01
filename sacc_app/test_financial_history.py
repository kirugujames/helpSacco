import frappe
import unittest
from sacc_app.api import get_member_financial_history

class TestFinancialHistory(unittest.TestCase):
    def setUp(self):
        # Cleanup
        frappe.db.delete("SACCO Member", {"email": "finance_test@test.com"})
        frappe.db.delete("SACCO Member", {"phone": ["like", "0799%"]}) # Clean up phones
        frappe.db.delete("SACCO Savings", {"reference_number": ["like", "TEST_SAVE_%"]})
        
        # Ensure Loan Product
        if not frappe.db.exists("SACCO Loan Product", "Test Product"):
             frappe.get_doc({
                 "doctype": "SACCO Loan Product",
                 "product_name": "Test Product",
                 "interest_rate": 10,
                 "interest_period": "Monthly",
                 "interest_method": "Flat Rate",
                 "max_repayment_period": 12
             }).insert(ignore_permissions=True)

        import random
        phone_suffix = random.randint(100000, 999999)
        self.phone = f"0799{phone_suffix}"

        # Create Member
        self.member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Finance",
            "last_name": "Test",
            "email": "finance_test@test.com",
            "status": "Active",
            "phone": self.phone,
            "national_id": f"ID_FIN_TEST_{phone_suffix}"
        }).insert(ignore_permissions=True)
        self.member.db_set("status", "Active")
        self.member.db_set("registration_fee_paid", 1)
        self.member.db_set("loan_eligible", 1)
        self.member.db_set("creation", frappe.utils.add_months(frappe.utils.nowdate(), -4))
        
        # Add an old saving to satisfy duration rule
        frappe.get_doc({
            "doctype": "SACCO Savings",
            "member": self.member.name,
            "amount": 5000,
            "type": "Deposit",
            "payment_mode": "Cash",
            "posting_date": frappe.utils.add_months(frappe.utils.nowdate(), -4),
            "reference_number": "TEST_SAVE_OLD"
        }).insert(ignore_permissions=True).submit()

        # Create Savings (25 entries) - these are recent
        for i in range(25):
            s = frappe.get_doc({
                "doctype": "SACCO Savings",
                "member": self.member.name,
                "amount": 1000,
                "type": "Deposit",
                "payment_mode": "Cash",
                "posting_date": frappe.utils.add_days(frappe.utils.nowdate(), -i),
                "reference_number": f"TEST_SAVE_{i}"
            }).insert(ignore_permissions=True)
            s.submit()
            
        # Create Loan
        self.loan = frappe.get_doc({
            "doctype": "SACCO Loan",
            "member": self.member.name,
            "loan_product": "Test Product",
            "loan_amount": 50000,
            "interest_rate": 10,
            "repayment_period": 12,
            "status": "Active"
        }).insert(ignore_permissions=True)
        
        # Create Repayments (25 entries)
        for i in range(25):
            r = frappe.get_doc({
                "doctype": "SACCO Loan Repayment",
                "loan": self.loan.name,
                "member": self.member.name,
                "payment_amount": 100,
                "payment_mode": "Cash",
                "payment_date": frappe.utils.add_days(frappe.utils.nowdate(), -i),
                "reference_number": f"TEST_REP_{i}"
            }).insert(ignore_permissions=True)
            r.submit()

    def test_pagination(self):
        # 1. Default limits (20)
        res = get_member_financial_history(self.member.name)
        self.assertEqual(len(res["savings"]), 20)
        self.assertEqual(len(res["repayments"]), 20)
        
        # 2. Savings Page 2 (offset 20, limit 20 -> should get 6 because 25+1=26 total)
        res_s2 = get_member_financial_history(self.member.name, savings_start=20)
        self.assertEqual(len(res_s2["savings"]), 6)
        
        # 3. Repayments specific limit
        res_r = get_member_financial_history(self.member.name, repayments_limit=10)
        self.assertEqual(len(res_r["repayments"]), 10)
        
        # 4. Repayments Page 2 with limit 10 (offset 10)
        res_r2 = get_member_financial_history(self.member.name, repayments_start=10, repayments_limit=10)
        self.assertEqual(len(res_r2["repayments"]), 10)
