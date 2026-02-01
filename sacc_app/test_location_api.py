import frappe
import unittest
import json
from sacc_app.location_api import seed_kenya_data, get_counties, get_constituencies, get_wards

class TestLocationAPI(unittest.TestCase):
    def setUp(self):
        # Clear existing data to avoid collision
        frappe.db.delete("Kenya Ward")
        frappe.db.delete("Kenya Constituency")
        frappe.db.delete("Kenya County")
        frappe.db.commit()

        self.test_json = [
            {
                "county_code": 1,
                "county_name": "Test County 1",
                "constituencies": [
                    {
                        "constituency_name": "Test Constituency 1A",
                        "wards": ["Ward 1A1", "Ward 1A2"]
                    },
                    {
                        "constituency_name": "Test Constituency 1B",
                        "wards": ["Ward 1B1"]
                    }
                ]
            }
        ]

    def test_seeding_and_retrieval(self):
        # 1. Seed data
        res = seed_kenya_data(self.test_json)
        self.assertEqual(res["status"], "success")
        
        # 2. Get Counties
        res_c = get_counties()
        self.assertEqual(len(res_c["data"]), 1)
        self.assertEqual(res_c["data"][0]["county_name"], "Test County 1")
        
        # 3. Get Constituencies
        res_con = get_constituencies("Test County 1")
        self.assertEqual(len(res_con["data"]), 2)
        con_name = res_con["data"][0]["constituency_name"]
        
        # 4. Get Wards
        con_id = res_con["data"][0]["name"]
        res_w = get_wards(con_id)
        # Check if it was Constituency 1A or 1B (order depends on asc)
        if "1A" in con_name:
            self.assertEqual(len(res_w["data"]), 2)
        else:
            self.assertEqual(len(res_w["data"]), 1)

    def test_duplicate_seeding(self):
        # Seed twice, counts should stay same
        seed_kenya_data(self.test_json)
        res = seed_kenya_data(self.test_json)
        self.assertIn("0 counties, 0 constituencies, 0 wards created", res["message"])
