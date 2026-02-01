import frappe

def run_test():
    print("Testing SACCO Member with 'Pending Payment' status...")
    
    # Clean up previous test member if exists
    member_email = "test_status@example.com"
    if frappe.db.exists("SACCO Member", {"email": member_email}):
        frappe.delete_doc("SACCO Member", frappe.db.get_value("SACCO Member", {"email": member_email}, "name"))
        frappe.db.commit()

    try:
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Test",
            "last_name": "Status",
            "email": member_email,
            "phone": "0700000001",
            "national_id": "9999999",
            "status": "Pending Payment"
        })
        member.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"✅ Success: Member {member.name} created with status '{member.status}'")
    except frappe.exceptions.ValidationError as e:
        print(f"❌ Failure: ValidationError: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    run_test()
