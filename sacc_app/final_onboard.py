
import frappe

def create_member():
    email = 'loan_tester_final@example.com'
    if not frappe.db.exists('SACCO Member', {'email': email}):
        member = frappe.get_doc({
            'doctype': 'SACCO Member',
            'first_name': 'New',
            'last_name': 'Tester',
            'email': email,
            'phone': '0722112233',
            'national_id': 'ID_NEW_FINAL',
            'gender': 'Female',
            'status': 'Active',
            'registration_fee_paid': 1,
            'loan_eligible': 1
        })
        member.insert(ignore_permissions=True)
        member.db_set('status', 'Active')
        member.db_set('registration_fee_paid', 1)
        member.db_set('loan_eligible', 1)
        # Provision accounts
        member.create_ledger_account(member.customer_link)
        print(f'CREATED: {member.name}')
    else:
        print(f'EXISTS: {email}')
