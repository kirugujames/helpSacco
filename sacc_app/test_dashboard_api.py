import frappe
import unittest
from sacc_app.dashboard_api import get_dashboard_stats, get_loan_breakdown, get_recent_activities, get_payment_requests, get_savings_growth
from frappe.utils import nowdate, add_days

class TestDashboardAPI(unittest.TestCase):
    def setUp(self):
        # Create Dummy Data with unique emails to avoid state collision
        import random
        suffix = str(random.randint(1000, 9999))
        self.mem1_email = f"dash_mem1_{suffix}@test.com"
        self.mem2_email = f"dash_mem2_{suffix}@test.com"
        
        self.create_member(self.mem1_email, "Dash", "Mem1")
        self.create_member(self.mem2_email, "Dash", "Mem2")
        
        # Savings
        self.create_savings(self.mem1_email, 5000)
        self.create_savings(self.mem2_email, 3000)
        
        # Loan
        self.create_loan(self.mem1_email, 10000, "Standard Loan")

    def create_member(self, email, fname, lname):
        if frappe.db.exists("SACCO Member", {"email": email}):
            name = frappe.db.get_value("SACCO Member", {"email": email}, "name")
            frappe.db.set_value("SACCO Member", name, "status", "Active")
            return name
            
        doc = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "phone": "0799999999",
            "national_id": "ID_" + fname + "_" + frappe.generate_hash(length=5),
            "status": "Active",
            "registration_fee_paid": 1,
            "loan_eligible": 1
        })
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("SACCO Member", doc.name, "status", "Active")
        return doc.name

    def create_savings(self, email, amount):
        mem_id = frappe.db.get_value("SACCO Member", {"email": email}, "name")
        doc = frappe.get_doc({
            "doctype": "SACCO Savings",
            "member": mem_id,
            "type": "Deposit",
            "amount": amount,
            "posting_date": nowdate(),
            "payment_mode": "Cash"
        })
        doc.insert(ignore_permissions=True)
        doc.submit()

    def create_loan(self, email, amount, product):
        mem_id = frappe.db.get_value("SACCO Member", {"email": email}, "name")
        # Ensure product exists
        if not frappe.db.exists("SACCO Loan Product", product):
            p = frappe.get_doc({
                "doctype": "SACCO Loan Product",
                "product_name": product,
                "interest_rate": 10,
                "max_repayment_period": 12,
                "interest_method": "Flat Rate",
                "interest_period": "Monthly"
            })
            p.insert(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "SACCO Loan",
            "member": mem_id,
            "loan_amount": amount,
            "loan_product": product,
            "repayment_period": 12,
            "status": "Approved"
        })
        doc.insert(ignore_permissions=True)
        doc.submit() # Becomes Active
        return doc.name

    def test_get_dashboard_stats(self):
        res = get_dashboard_stats()
        data = res["data"]
        # We can't assert exact numbers because other tests might have created data
        # But we can assert they are > 0
        self.assertTrue(data["total_members"] >= 2)
        self.assertTrue(data["total_savings"] >= 8000)
        self.assertTrue(data["active_loans"] >= 1)

    def test_get_loan_breakdown(self):
        res = get_loan_breakdown()
        data = res["data"]
        found = False
        for item in data:
            if item["loan_product"] == "Standard Loan":
                self.assertTrue(item["total_amount"] >= 10000)
                found = True
        self.assertTrue(found)

    def test_get_recent_activities(self):
        res = get_recent_activities()
        data = res["data"]
        self.assertTrue(len(data) > 0)
        self.assertTrue(data[0].get("type") in ["Savings Deposit", "Loan Repayment"])

    def test_get_payment_requests(self):
        res = get_payment_requests()
        data = res["data"]
        # Find our loan
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        found = False
        for item in data:
            if item["member"] == mem_id:
                self.assertEqual(item["status"], "Good Standing")
                found = True
        self.assertTrue(found)

    def test_get_savings_growth(self):
        res = get_savings_growth()
        data = res["data"]
        self.assertTrue(len(data) > 0)
        # Verify valid structure
        self.assertTrue("month_name" in data[0])
        self.assertTrue("year" in data[0])
        self.assertTrue("total" in data[0])

    def test_pagination(self):
        # Create many savings entries
        for i in range(10):
            self.create_savings(self.mem1_email, 10 + i)
            
        # 1. Test get_recent_activities pagination
        res_p1 = get_recent_activities(limit_start=0, limit_page_length=5)
        self.assertEqual(len(res_p1["data"]), 5)
        
        res_p2 = get_recent_activities(limit_start=5, limit_page_length=5)
        self.assertEqual(len(res_p2["data"]), 5)
        
        # Check that we got different items
        self.assertNotEqual(res_p1["data"][0]["timestamp"], res_p2["data"][0]["timestamp"])
        
        # 2. Test get_payment_requests pagination
        # We only have 1 active loan from setUp, so we can only test limit 1
        res_pay = get_payment_requests(limit_start=0, limit_page_length=1)
        self.assertEqual(len(res_pay["data"]), 1)

    def test_search(self):
        # 1. Test get_recent_activities search
        # Search by member ID (mem1)
        mem1_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        res_s1 = get_recent_activities(search=mem1_id)
        for item in res_s1["data"]:
            self.assertEqual(item["member"], mem1_id)
            
        # Search by name (Mem2)
        res_s2 = get_recent_activities(search="Mem2")
        self.assertTrue(len(res_s2["data"]) > 0)
        for item in res_s2["data"]:
            self.assertEqual(item["member_name"], "Dash Mem2")
            
        # 2. Test get_payment_requests search
        res_s3 = get_payment_requests(search="Mem1")
        self.assertTrue(len(res_s3["data"]) > 0)
        for item in res_s3["data"]:
            self.assertEqual(item["member_name"], "Dash Mem1")
            
        # Search for non-existent member
        res_s4 = get_payment_requests(search="NonExistent")
        self.assertEqual(len(res_s4["data"]), 0)
