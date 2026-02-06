import frappe

def run_test():
    """Test that members with registration_fee_paid=1 cannot pay again"""
    print("Testing enhanced registration fee payment validation...")
    
    # Clean up previous test member if exists
    member_email = "test_reg_paid@example.com"
    cleanup_member(member_email)

    try:
        # Test 1: Member with registration_fee_paid = 1
        print("\n=== Test 1: Member with registration_fee_paid=1 ===")
        member = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Paid",
            "last_name": "Member",
            "email": member_email,
            "phone": "0788888888",
            "national_id": "77777777"
        })
        member.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"   Created member: {member.name}")
        print(f"   Initial Status: {member.status}")
        print(f"   Initial registration_fee_paid: {member.registration_fee_paid}")
        
        # Manually set registration_fee_paid to 1 (simulating already paid)
        frappe.db.set_value("SACCO Member", member.name, "registration_fee_paid", 1)
        frappe.db.commit()
        
        # Reload to get updated value
        member.reload()
        print(f"   Updated registration_fee_paid: {member.registration_fee_paid}")
        
        # Try to pay registration fee - should fail
        print("\n   Attempting to pay registration fee...")
        try:
            from sacc_app.api import pay_registration_fee
            result = pay_registration_fee(member.name, amount=500, mode="Cash")
            print(f"   ❌ FAILURE: Payment was allowed!")
            print(f"   Result: {result}")
        except Exception as e:
            error_msg = str(e)
            if "already paid" in error_msg.lower() or "registration fee" in error_msg.lower():
                print(f"   ✅ SUCCESS: Payment correctly blocked")
                print(f"   Error message: {error_msg}")
            else:
                print(f"   ⚠️  Payment blocked with different error: {error_msg}")
        
        # Test 2: Member with Active status
        print("\n=== Test 2: Member with Active status ===")
        cleanup_member(member_email)
        
        member2 = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Active",
            "last_name": "Member",
            "email": member_email,
            "phone": "0788888888",
            "national_id": "77777777"
        })
        member2.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"   Created member: {member2.name}")
        
        # Manually set status to Active
        frappe.db.set_value("SACCO Member", member2.name, "status", "Active")
        frappe.db.commit()
        
        member2.reload()
        print(f"   Updated Status: {member2.status}")
        print(f"   registration_fee_paid: {member2.registration_fee_paid}")
        
        # Try to pay registration fee - should fail
        print("\n   Attempting to pay registration fee...")
        try:
            from sacc_app.api import pay_registration_fee
            result = pay_registration_fee(member2.name, amount=500, mode="Cash")
            print(f"   ❌ FAILURE: Payment was allowed!")
            print(f"   Result: {result}")
        except Exception as e:
            error_msg = str(e)
            if "already paid" in error_msg.lower() or "active" in error_msg.lower():
                print(f"   ✅ SUCCESS: Payment correctly blocked")
                print(f"   Error message: {error_msg}")
            else:
                print(f"   ⚠️  Payment blocked with different error: {error_msg}")
        
        # Test 3: Normal member (Pending Payment, registration_fee_paid=0)
        print("\n=== Test 3: Normal Pending Payment member ===")
        cleanup_member(member_email)
        
        member3 = frappe.get_doc({
            "doctype": "SACCO Member",
            "first_name": "Pending",
            "last_name": "Member",
            "email": member_email,
            "phone": "0788888888",
            "national_id": "77777777"
        })
        member3.insert(ignore_permissions=True)
        frappe.db.commit()
        
        member3.reload()
        print(f"   Created member: {member3.name}")
        print(f"   Status: {member3.status}")
        print(f"   registration_fee_paid: {member3.registration_fee_paid}")
        
        # Check if invoice exists
        if member3.customer_link:
            invoice = frappe.db.get_value("Sales Invoice", 
                {"customer": member3.customer_link, "docstatus": 1, "status": ["!=", "Paid"]},
                ["name", "outstanding_amount"], as_dict=True)
            if invoice:
                print(f"   Found invoice: {invoice.name} with outstanding: {invoice.outstanding_amount}")
                print("   ✅ This member should be able to pay registration fee")
            else:
                print("   ⚠️  No pending invoice found - payment may fail")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n=== Cleanup ===")
        cleanup_member(member_email)
        print("✅ Cleanup completed")

def cleanup_member(email):
    """Helper function to clean up test member and related records"""
    if frappe.db.exists("SACCO Member", {"email": email}):
        member_name = frappe.db.get_value("SACCO Member", {"email": email}, "name")
        member_doc = frappe.get_doc("SACCO Member", member_name)
        
        if member_doc.customer_link and frappe.db.exists("Customer", member_doc.customer_link):
            # Delete payment entries
            payments = frappe.db.get_all("Payment Entry", {"party": member_doc.customer_link}, pluck="name")
            for pay in payments:
                try:
                    pe = frappe.get_doc("Payment Entry", pay)
                    if pe.docstatus == 1:
                        pe.cancel()
                    frappe.delete_doc("Payment Entry", pay, force=1)
                except:
                    pass
            
            # Delete invoices
            invoices = frappe.db.get_all("Sales Invoice", {"customer": member_doc.customer_link}, pluck="name")
            for inv in invoices:
                try:
                    si = frappe.get_doc("Sales Invoice", inv)
                    if si.docstatus == 1:
                        si.cancel()
                    frappe.delete_doc("Sales Invoice", inv, force=1)
                except:
                    pass
            
            frappe.delete_doc("Customer", member_doc.customer_link, force=1)
        
        frappe.delete_doc("SACCO Member", member_name, force=1)
        frappe.db.commit()

if __name__ == "__main__":
    run_test()
