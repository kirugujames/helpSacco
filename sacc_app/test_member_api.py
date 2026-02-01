import frappe
import unittest
from sacc_app.member_api import get_member_stats, get_member_list, edit_member, disable_member, enable_member

class TestMemberAPI(unittest.TestCase):
    def setUp(self):
        # Clear old test data
        frappe.db.delete("SACCO Member", {"email": ["like", "member_test%"]})
        frappe.db.commit() # Ensure it's committed before starting
        
        # Create some test members
        import random
        suffix = str(random.randint(1000, 9999))
        self.mem1_email = f"member_test1_{suffix}@test.com"
        self.mem2_email = f"member_test2_{suffix}@test.com"
        
        self.create_member(self.mem1_email, "Test", "Member1", "Active")
        self.create_member(self.mem2_email, "Test", "Member2", "Probation")

    def create_member(self, email, fname, lname, status):
        if frappe.db.exists("SACCO Member", {"email": email}):
            return frappe.db.get_value("SACCO Member", {"email": email}, "name")
            
        import random
        doc = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": fname,
            "last_name": lname,
            "status": status,
            "phone": "".join([str(random.randint(0, 9)) for _ in range(10)]),
            "national_id": "ID_" + frappe.generate_hash(length=8)
        })
        doc.insert(ignore_permissions=True)
        doc.db_set("email", email)
        doc.db_set("status", status)
        return doc.name

    def test_get_member_stats(self):
        res = get_member_stats()
        data = res["data"]
        self.assertTrue(data["total_members"] >= 2)
        self.assertTrue(data["active_members"] >= 1)
        self.assertTrue(data["new_members_this_month"] >= 2)
        self.assertTrue(data["other_members"] >= 1)

    def test_get_member_list(self):
        # 1. Basic list
        res = get_member_list(limit_page_length=2)
        self.assertEqual(len(res["data"]), 2)
        
        # 2. Search by name
        res_s = get_member_list(search="Member1")
        self.assertTrue(len(res_s["data"]) > 0)
        self.assertEqual(res_s["data"][0]["member_name"], "Test Member1")
        
        # 3. Search by ID
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        res_sid = get_member_list(search=mem_id)
        self.assertEqual(res_sid["data"][0]["name"], mem_id)
        
        # 4. Pagination
        res_p = get_member_list(limit_start=1, limit_page_length=1)
        self.assertEqual(len(res_p["data"]), 1)
        
        # 5. Status filter
        res_st = get_member_list(status="Probation")
        for m in res_st["data"]:
            self.assertEqual(m["status"], "Probation")
            
        # 6. Combined filter
        res_comb = get_member_list(search="Member2", status="Probation")
        self.assertEqual(len(res_comb["data"]), 1)
        self.assertEqual(res_comb["data"][0]["member_name"], "Test Member2")

    def test_edit_member(self):
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        new_fname = "EditedName"
        new_phone = "0711111111"
        
        res = edit_member(member_id=mem_id, first_name=new_fname, phone=new_phone)
        self.assertEqual(res["status"], "success")
        
        doc = frappe.get_doc("SACCO Member", mem_id)
        self.assertEqual(doc.first_name, new_fname)
        self.assertEqual(doc.phone, new_phone)
        self.assertEqual(doc.member_name, f"{new_fname} Member1")

    def test_disable_member(self):
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        
        res = disable_member(member_id=mem_id)
        self.assertEqual(res["status"], "success")
        
        status = frappe.db.get_value("SACCO Member", mem_id, "status")
        self.assertEqual(status, "Inactive")

    def test_enable_member(self):
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem2_email}, "name")
        # Ensure it's inactive first (m2 is probation, so let's set it to Active)
        res = enable_member(member_id=mem_id)
        self.assertEqual(res["status"], "success")
        
        status = frappe.db.get_value("SACCO Member", mem_id, "status")
        self.assertEqual(status, "Active")

    def test_delete_member(self):
        from sacc_app.api import delete_member
        mem_id = frappe.db.get_value("SACCO Member", {"email": self.mem1_email}, "name")
        
        # Ensure it exists
        self.assertTrue(frappe.db.exists("SACCO Member", mem_id))
        
        res = delete_member(mem_id)
        self.assertEqual(res["status"], "success")
        
        # Ensure it's gone
        self.assertFalse(frappe.db.exists("SACCO Member", mem_id))
