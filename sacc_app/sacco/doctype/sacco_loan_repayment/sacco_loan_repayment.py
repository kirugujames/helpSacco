# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from sacc_app.notify import send_member_email

class SACCOLoanRepayment(Document):
	def validate(self):
		if not self.member:
			self.member = frappe.db.get_value("SACCO Loan", self.loan, "member")
			
		# Check if loan is already completed
		loan_status = frappe.db.get_value("SACCO Loan", self.loan, "status")
		if loan_status == "Completed":
			frappe.throw(f"Loan {self.loan} is already fully paid (Completed). No further payments can be recorded.")

		# Check sufficient savings if paying from savings
		if self.payment_mode == "Savings":
			total_savings = frappe.db.get_value("SACCO Member", self.member, "total_savings") or 0
			if flt(self.payment_amount) > flt(total_savings):
				frappe.throw(f"Insufficient savings balance. Available: {total_savings}, Required: {self.payment_amount}")

	def on_submit(self):
		self.process_payment()
		
		# Send Repayment Notification
		send_member_email(self.member, "Loan Repayment Received", 
			f"Your loan <b>{self.loan}</b> has been <b>debited</b> with <b>{self.payment_amount}</b>. "
			f"Current Outstanding Balance: <b>{frappe.db.get_value('SACCO Loan', self.loan, 'outstanding_balance')}</b>.")


	def process_payment(self):
		loan = frappe.get_doc("SACCO Loan", self.loan)
		
		# 1. Calculate Balanced Split (Proportional to Total)
		# This ensures both principal and interest are reduced with every payment.
		total_rep = flt(loan.total_repayable)
		if total_rep > 0:
			interest_ratio = flt(loan.total_interest) / total_rep
			principal_ratio = flt(loan.loan_amount) / total_rep
			
			interest_portion = flt(self.payment_amount) * interest_ratio
			principal_portion = flt(self.payment_amount) * principal_ratio
			
			# Cap interest portion if it exceeds remaining due
			rem_int = max(0, flt(loan.total_interest) - flt(loan.interest_paid))
			if interest_portion > rem_int:
				interest_portion = rem_int
				principal_portion = flt(self.payment_amount) - interest_portion
		else:
			interest_portion = 0
			principal_portion = self.payment_amount
		
		# 2. Update Loan record
		loan.interest_paid = flt(loan.interest_paid) + interest_portion
		loan.principal_paid = flt(loan.principal_paid) + principal_portion
		loan.outstanding_balance = flt(loan.outstanding_balance) - flt(self.payment_amount)
		
		if loan.outstanding_balance <= 0:
			loan.status = "Completed"
			loan.outstanding_balance = 0
			# Clear member active loan
			frappe.db.set_value("SACCO Member", loan.member, "active_loan", None)
		
		loan.save(ignore_permissions=True)

		# 3. Create Journal Entry
		self.create_journal_entry(loan, principal_portion, interest_portion)

	def create_journal_entry(self, loan, principal_portion, interest_portion):
		member = frappe.get_doc("SACCO Member", self.member)
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		
		cash_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company})
		if not cash_account:
			cash_account = frappe.db.get_value("Account", {"root_type": "Asset", "is_group": 0, "company": company})
			
		income_account = frappe.db.get_value("Account", {"account_name": "SACCO Interest Income", "company": company})
		if not income_account:
			# Fallback
			income_account = frappe.db.get_value("Account", {"root_type": "Income", "is_group": 0, "company": company})

		je = frappe.new_doc("Journal Entry")
		je.posting_date = self.payment_date
		je.company = company
		je.voucher_type = "Journal Entry"
		je.user_remark = f"Loan Repayment: {self.loan} (Ref: {self.name}) (Principal: {principal_portion}, Interest: {interest_portion})"

		# Dr Cash or Savings Account (Total Payment)
		debit_account = cash_account
		if self.payment_mode == "Savings":
			debit_account = member.savings_account

		je.append("accounts", {
			"account": debit_account,
			"debit_in_account_currency": self.payment_amount,
			"credit_in_account_currency": 0
		})
		
		# Cr Member Ledger (Principal Reduction Portion)
		if principal_portion > 0:
			je.append("accounts", {
				"account": member.ledger_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": principal_portion,
				"party_type": "Customer",
				"party": member.customer_link
			})
			
		# Cr SACCO Interest Income (Interest Portion)
		if interest_portion > 0:
			je.append("accounts", {
				"account": income_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": interest_portion
			})
		
		je.save(ignore_permissions=True)
		je.submit()

