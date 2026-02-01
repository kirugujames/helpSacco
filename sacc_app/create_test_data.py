
import frappe
from frappe.utils import nowdate

def create_eligible_member():
    print("--- Creating Eligible Test Member ---")
    
    # 1. Create SACCO Member
    email = "eligible_test@example.com"
    if frappe.db.exists("SACCO Member", {"email": email}):
        print(f"Member with email {email} already exists. Cleaning up...")
        member_name = frappe.db.get_value("SACCO Member", {"email": email}, "name")
        frappe.delete_doc("SACCO Member", member_name)

    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Eligible",
        "last_name": "Member",
        "email": email,
        "phone": "0711223344",
        "national_id": "ID998877",
        "gender": "Male",
        "date_of_birth": "1995-05-05",
        "status": "Active",
        "registration_fee_paid": 1,
        "loan_eligible": 1
    })
    member.insert(ignore_permissions=True)
    print(f"Created Member: {member.name}")

    # 2. Ensure a Loan Product exists
    if not frappe.db.exists("SACCO Loan Product"):
        print("No Loan Product found, creating default 'Standard Loan'...")
        product = frappe.get_doc({
            "doctype": "SACCO Loan Product",
            "product_name": "Standard Loan",
            "interest_rate": 10,
            "interest_period": "Monthly",
            "max_repayment_period": 12,
            "min_loan_amount": 1000,
            "max_loan_amount": 1000000,
            "requires_guarantor": 0
        })
        product.insert(ignore_permissions=True)
    
    product_name = frappe.db.get_value("SACCO Loan Product", {}, "name")
    print(f"Eligible for Loan Product: {product_name}")

    # 3. Add some savings to make the profile look good
    print("Adding initial savings deposit...")
    from sacc_app.api import record_savings_deposit
    try:
        record_savings_deposit(member=member.name, amount=50000, mode="Cash", reference="INI-SAV-001")
        print("Savings deposit successful.")
    except Exception as e:
        print(f"Savings deposit failed: {e}")

    print(f"--- Member {member.name} is now ready and eligible for a loan! ---")

if __name__ == "__main__":
    create_eligible_member()
