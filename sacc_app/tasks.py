import frappe
from frappe import _
from frappe.utils import add_days, getdate, format_date

def send_loan_reminders():
	"""
	Daily task to send reminders for loans due tomorrow.
	"""
	tomorrow = add_days(frappe.utils.nowdate(), 1)
	
	# Fetch all active loans
	active_loans = frappe.get_all("SACCO Loan", filters={"status": "Active"}, fields=["name", "member", "repayment_schedule", "monthly_installment"])
	
	import json
	for loan in active_loans:
		if not loan.repayment_schedule:
			continue
			
		try:
			schedule = json.loads(loan.repayment_schedule)
		except:
			continue
			
		for entry in schedule:
			# Check if any installment is due tomorrow
			# Entry format assumed from common Frappe patterns: {"payment_date": "YYYY-MM-DD", "principal_amount": ..., "interest_amount": ...}
			if entry.get("payment_date") == tomorrow:
				send_reminder_email(loan, entry)

def send_reminder_email(loan, schedule_entry):
	"""
	Sends an email reminder to the member.
	"""
	from sacc_app.notify import send_member_email
	
	due_amount = schedule_entry.get("total_payment") or loan.monthly_installment
	subject = _("Loan Repayment Reminder - Due Tomorrow")
	message = f"""
	<p>This is a reminder that your loan repayment for <strong>{loan.name}</strong> is due tomorrow, <strong>{format_date(schedule_entry.get('payment_date'))}</strong>.</p>
	<p>Amount Due: <strong>{frappe.format_value(due_amount, "Currency")}</strong></p>
	<p>Please ensure you have sufficient funds in your account or make a payment via the portal.</p>
	"""
	
	send_member_email(loan.member, subject, message)
	
def update_all_demanded_amounts():
	"""
	Scheduled task to update demanded amounts for all active loans.
	"""
	active_loans = frappe.get_all("SACCO Loan", filters={"status": "Active"}, fields=["name"])
	for l in active_loans:
		loan_doc = frappe.get_doc("SACCO Loan", l.name)
		loan_doc.update_demanded_amounts()
