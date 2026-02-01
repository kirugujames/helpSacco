# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from sacc_app.notify import send_member_email

class SACCOSavings(Document):
	def validate(self):
		if self.type == "Withdrawal":
			current_balance = frappe.db.get_value("SACCO Member", self.member, "total_savings") or 0
			if flt(self.amount) > flt(current_balance):
				frappe.throw(f"Insufficient savings balance. Available: {current_balance}, Attempted withdrawal: {self.amount}")

	def on_submit(self):
		self.make_gl_entries()
		self.update_member_savings()
		
		# Send Notification
		subject = "Savings Deposit Received" if self.type == "Deposit" else "Savings Withdrawal Recorded"
		verb = "credited" if self.type == "Deposit" else "debited"
		
		send_member_email(self.member, subject, 
			f"Your account has been <b>{verb}</b> with <b>{self.amount}</b>. "
			f"New Total Savings: <b>{frappe.db.get_value('SACCO Member', self.member, 'total_savings')}</b>.")


	def on_cancel(self):
		self.make_gl_entries(cancel=True)
		self.update_member_savings()

	def make_gl_entries(self, cancel=False):
		# Dr Cash/Bank
		# Cr Member Ledger
		
		# Get Member Account
		member = frappe.get_doc("SACCO Member", self.member)
		if not member.ledger_account:
			frappe.throw(f"Member {self.member} does not have a linked Ledger Account.")
			
		member_account = member.savings_account
		
		# Get Cash/Bank Account - simplified for now, usually based on Mode of Payment
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		cash_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company})
		
		if not cash_account:
			# Fallback
			cash_account = frappe.db.get_value("Account", {"is_group": 0, "root_type": "Asset", "company": company})

		if not cash_account:
			frappe.throw("No Cash/Bank Account found. Please set up Chart of Accounts.")

		# Create Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.posting_date = self.posting_date
		je.company = company
		je.voucher_type = "Journal Entry"
		if self.reference_number:
			je.cheque_no = self.reference_number
			je.cheque_date = self.posting_date
		je.user_remark = f"Savings {self.type} for {self.member}"
		
		amount = flt(self.amount)
		
		if self.type == "Deposit":
			# Dr Cash/Bank, Cr Member Savings (Liability UP)
			je.append("accounts", {
				"account": cash_account,
				"debit_in_account_currency": amount,
				"credit_in_account_currency": 0
			})
			je.append("accounts", {
				"account": member_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": amount,
				"is_advance": "Yes"
			})
		else:
			# Withdrawal: Dr Member Savings (Liability DOWN), Cr Cash/Bank
			je.append("accounts", {
				"account": member_account,
				"debit_in_account_currency": amount,
				"credit_in_account_currency": 0,
				"is_advance": "Yes"
			})
			je.append("accounts", {
				"account": cash_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": amount
			})
		
		je.save()
		je.submit()
		
		if cancel:
			je.cancel()

	def update_member_savings(self):
		# Calculate total savings for member
		results = frappe.db.get_all("SACCO Savings", 
			filters={"member": self.member, "docstatus": 1}, 
			fields=["type", "amount"])
		
		total = 0
		for r in results:
			if r.type == "Deposit":
				total += flt(r.amount)
			else:
				total -= flt(r.amount)
		
		print(f"DEBUG: Calculated total savings for {self.member}: {total}")
		frappe.db.set_value("SACCO Member", self.member, "total_savings", total)
		frappe.db.commit() # Ensure persisted for tests
