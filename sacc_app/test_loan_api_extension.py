import frappe
import unittest
from sacc_app.api import get_loan_application_by_id

class TestLoanApiExtension(unittest.TestCase):
    def setUp(self):
        # Create a test member
        self.member_id = self.create_test_member()
        
        # Create a loan product
        self.product_name = self.create_test_loan_product()
        
        # Create a loan
        self.loan_id = self.create_test_loan(self.member_id, self.product_name)

    def tearDown(self):
        frappe.db.delete("SACCO Loan", {"name": self.loan_id})
        frappe.db.delete("SACCO Loan Product", {"name": self.product_name})
        frappe.db.delete("SACCO Member", {"name": self.member_id})
        frappe.db.commit()

    def create_test_member(self):
        import random
        suffix = str(random.randint(10000, 99999))
        email = f"test_loan_api_{suffix}@example.com"
        # Generate random 10 digit phone number starting with 07
        phone = "07" + "".join([str(random.randint(0, 9)) for _ in range(8)])
        
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Test",
            "last_name": f"User {suffix}",
            "email": email,
            "status": "Active",
            "phone": phone,
            "national_id": f"ID{suffix}",
            "loan_eligible": 1,
            "registration_fee_paid": 1
        })
        member.insert(ignore_permissions=True)
        # Force status update just in case defaults override it
        frappe.db.set_value("SACCO Member", member.name, "status", "Active")
        frappe.db.set_value("SACCO Member", member.name, "loan_eligible", 1)
        frappe.db.set_value("SACCO Member", member.name, "registration_fee_paid", 1)
        return member.name

    def create_test_loan_product(self):
        product_name = "Test Product"
        if not frappe.db.exists("SACCO Loan Product", product_name):
            product = frappe.get_doc({
                "doctype": "SACCO Loan Product",
                "product_name": product_name,
                "interest_rate": 10,
                "max_repayment_period": 12,
                "interest_method": "Reducing Balance"
            })
            product.insert(ignore_permissions=True)
        return product_name

    def create_test_loan(self, member_id, product_name):
        loan = frappe.get_doc({
            "doctype": "SACCO Loan",
            "member": member_id,
            "loan_product": product_name,
            "loan_amount": 10000,
            "interest_rate": 10,
            "repayment_period": 12,
            "status": "Draft",
            "repayment_schedule": '[{"payment_date": "2024-01-01", "principal": 1000, "interest": 100, "total": 1100}]'
        })
        loan.insert(ignore_permissions=True)
        return loan.name

    def test_get_loan_application_by_id_success(self):
        result = get_loan_application_by_id(self.loan_id)
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["name"], self.loan_id)
        self.assertEqual(data["status"], "Draft")
        self.assertEqual(data["member_id"], self.member_id)
        expected_name = frappe.db.get_value("SACCO Member", self.member_id, "member_name")
        self.assertEqual(data["member_name"], expected_name)
        self.assertEqual(data["first_name"], "Test")
        # last_name is dynamic in the setup (f"User {suffix}")
        expected_last_name = frappe.db.get_value("SACCO Member", self.member_id, "last_name")
        self.assertEqual(data["last_name"], expected_last_name)
        # Verify schedule parsing - it might have more than 1 entry due to auto-generation
        self.assertIsInstance(data["repayment_schedule"], list)
        self.assertTrue(len(data["repayment_schedule"]) > 0)

    def test_get_loan_application_by_id_not_found(self):
        result = get_loan_application_by_id("NON_EXISTENT_LOAN_ID")
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    def test_repayment_schedule_parsing_empty(self):
        # Create a loan and MANUALLY empty the schedule to test the parsing logic
        loan2 = frappe.get_doc({
            "doctype": "SACCO Loan",
            "member": self.member_id,
            "loan_product": self.product_name,
            "loan_amount": 5000,
            "status": "Draft",
            "loan_eligible": 1,
            "registration_fee_paid": 1
        })
        loan2.insert(ignore_permissions=True)
        frappe.db.set_value("SACCO Loan", loan2.name, "repayment_schedule", "")
        
        result = get_loan_application_by_id(loan2.name)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["repayment_schedule"], [])
        
        # Clean up
        frappe.delete_doc("SACCO Loan", loan2.name)

if __name__ == "__main__":
    unittest.main()
