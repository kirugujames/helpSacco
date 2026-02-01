import frappe
import json
from frappe.utils import nowdate, random_string, add_months

frappe.init(site="sacco.test.com")
frappe.connect()

def test_schedule_breakdown():
    # 1. Setup Member
    suffix = random_string(5)
    member = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": "Sched",
        "last_name": f"Test {suffix}",
        "email": f"sched_{suffix}@example.com",
        "phone": f"0740000{suffix[:3]}", # Just dummy
        "national_id": f"ID_S_{suffix}",
        "status": "Active",
        "loan_eligible": 1,
        "registration_fee_paid": 1
    })
    member.insert(ignore_permissions=True)
    
    # Active setup
    frappe.db.set_value("SACCO Member", member.name, "status", "Active")
    frappe.db.set_value("SACCO Member", member.name, "registration_fee_paid", 1)
    member.reload()
    
    # 2. Create Loan
    loan = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member.name,
        "loan_product": frappe.get_all("SACCO Loan Product", limit=1)[0].name,
        "loan_amount": 12000,
        "repayment_period": 12,
        "posting_date": nowdate()
    })
    
    # Trigger validate to generate schedule
    loan.validate()
    
    print(f"Loan Product: {loan.loan_product}")
    print(f"Loan Amount: {loan.loan_amount}")
    print(f"Total Repayable: {loan.total_repayable}")
    print(f"Monthly Installment: {loan.monthly_installment}")
    
    if not loan.repayment_schedule:
        print("FAILURE: Repayment Schedule is empty.")
        return

    schedule = json.loads(loan.repayment_schedule)
    if schedule:
        row = schedule[0]
        print("\nSample Schedule Item:")
        print(json.dumps(row, indent=2))
        
        expected_keys = ["payment_date", "amount", "principal", "interest", "balance_after"]
        missing = [k for k in expected_keys if k not in row]
        
        if not missing:
            print("\nSUCCESS: All expected fields found in schedule.")
            # Verify sum
            if abs(row['principal'] + row['interest'] - row['amount']) < 0.05:
                 print("SUCCESS: Principal + Interest = Total Amount.")
            else:
                 print(f"FAILURE: Sum mismatch. P:{row['principal']} + I:{row['interest']} != A:{row['amount']}")
        else:
            print(f"FAILURE: Missing keys in schedule: {missing}")
    else:
        print("FAILURE: Schedule list is empty.")

if __name__ == "__main__":
    test_schedule_breakdown()
