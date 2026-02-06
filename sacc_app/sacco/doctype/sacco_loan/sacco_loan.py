# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_months

class SACCOLoan(Document):
	def validate(self):
		self.validate_eligibility()
		self.calculate_terms()
		self.calculate_totals()
		self.generate_schedule()

	def validate_eligibility(self):
		# Check member active
		member = frappe.get_doc("SACCO Member", self.member)
		if member.status != "Active":
			frappe.throw("Member is not Active.")
		if not member.loan_eligible:
			frappe.throw("Member is not eligible for loans yet (3 months savings rule).")
		if not member.registration_fee_paid:
			frappe.throw("Registration fee not paid.")
		if member.active_loan:
			# Only Table Banking might allow parallel loans, but usually better to stick to 1 unless specified.
			# Logic check:
			product = frappe.get_doc("SACCO Loan Product", self.loan_product)
			if product.product_name != "Table Banking":
				frappe.throw(f"Member already has an active loan: {member.active_loan}")

		# Validate Amounts
		product = frappe.get_doc("SACCO Loan Product", self.loan_product)

		# Validate Guarantors
		if product.requires_guarantor:
			min_g = getattr(product, "min_guarantors", 0)
			if len(self.guarantors) < min_g:
				frappe.throw(f"Loan product '{self.loan_product}' requires at least {min_g} guarantors. Provided: {len(self.guarantors)}")

		if product.min_loan_amount and self.loan_amount < product.min_loan_amount:
			frappe.throw(f"Loan amount is below the minimum allowed ({product.min_loan_amount}) for '{self.loan_product}'.")
		if product.max_loan_amount and self.loan_amount > product.max_loan_amount:
			frappe.throw(f"Loan amount exceeds the maximum allowed ({product.max_loan_amount}) for '{self.loan_product}'.")

	def calculate_terms(self):
		# Now fetched from Product
		product = frappe.get_doc("SACCO Loan Product", self.loan_product)
		self.interest_rate = product.interest_rate
		self.interest_period = product.interest_period
		self.interest_method = product.interest_method
		if not self.repayment_period:
			self.repayment_period = product.max_repayment_period # Use max as default if not specified

	def calculate_totals(self):
		product = frappe.get_doc("SACCO Loan Product", self.loan_product)
		
		# Portion Ratios & Method Specific Calculation
		if self.interest_method == "Reducing Balance":
			# EMI Formula: [P * r * (1+r)^n] / [(1+r)^n - 1]
			# Convert rate based on period
			if product.interest_period == "Monthly":
				r = (flt(self.interest_rate) / 100.0)
			else:
				r = (flt(self.interest_rate) / 100.0) / 12.0
				
			n = flt(self.repayment_period)
			if r > 0 and n > 0:
				self.monthly_installment = (flt(self.loan_amount) * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1)
			elif n > 0:
				self.monthly_installment = flt(self.loan_amount) / n
			else:
				self.monthly_installment = 0
				
			self.total_repayable = self.monthly_installment * n
			self.total_interest = self.total_repayable - flt(self.loan_amount)
		else:
			# Flat Rate (Current Logic)
			if product.interest_period == "Monthly":
				# Simple Interest: Amount * Rate * Months
				self.total_interest = flt(self.loan_amount) * (flt(self.interest_rate) / 100.0) * flt(self.repayment_period)
			else:
				# Annual Interest: Amount * Rate * (Months/12)
				self.total_interest = flt(self.loan_amount) * (flt(self.interest_rate) / 100.0) * (flt(self.repayment_period) / 12.0)
				
			self.total_repayable = flt(self.loan_amount) + self.total_interest
			if self.repayment_period > 0:
				self.monthly_installment = self.total_repayable / self.repayment_period
			else:
				self.monthly_installment = 0
		
		if self.is_new() or self.outstanding_balance == 0:
			self.outstanding_balance = self.total_repayable

	def generate_schedule(self):
		# Generate a simple JSON schedule
		schedule = []
		start_date = nowdate()
		balance = flt(self.total_repayable)
		total_rep = flt(self.total_repayable)
		
		# Portion Ratios
		interest_ratio = flt(self.total_interest) / total_rep if total_rep > 0 else 0
		principal_ratio = flt(self.loan_amount) / total_rep if total_rep > 0 else 1

		curr_balance = flt(self.loan_amount) # For Reducing Balance tracking
		
		# Rate for reducing balance
		if self.interest_method == "Reducing Balance":
			if self.interest_period == "Monthly":
				r = (flt(self.interest_rate) / 100.0)
			else:
				r = (flt(self.interest_rate) / 100.0) / 12.0
		else:
			r = 0

		for i in range(1, int(self.repayment_period) + 1):
			date = add_months(start_date, i)
			amt = flt(self.monthly_installment)
			
			if self.interest_method == "Reducing Balance":
				i_portion = curr_balance * r
				p_portion = amt - i_portion
				curr_balance -= p_portion
			else:
				# Flat Rate: Proportional Split
				p_portion = amt * principal_ratio
				i_portion = amt * interest_ratio
			
			balance -= amt
			schedule.append({
				"payment_date": date,
				"amount": round(amt, 2),
				"principal": round(p_portion, 2),
				"interest": round(i_portion, 2),
				"principal_to_be_demanded": round(p_portion, 2),
				"interest_to_be_demanded": round(i_portion, 2),
				"balance_after": max(0, round(balance, 2))
			})
		import json
		self.repayment_schedule = json.dumps(schedule, indent=4, default=str)

	def on_submit(self):
		if self.status != "Approved":
			frappe.throw("Loan must be Approved before submitting (Disbursement).")
		self.status = "Disursed" # Or Active
		self.make_disbursement_entry()
		self.update_member_status()
		
		# Refresh balances immediately
		member = frappe.get_doc("SACCO Member", self.member)
		member.get_balances()
		
		self.status = "Active"
		self.db_set("status", "Active")

	def make_disbursement_entry(self):
		member = frappe.get_doc("SACCO Member", self.member)
		if not member.savings_account:
			frappe.throw(f"Member {self.member} does not have a linked Savings Account. Please update the member profile.")
		
		# Debit: Member Loan Account (Receivable UP)
		# Credit: Member Savings Account (Liability UP)
		
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		
		je = frappe.new_doc("Journal Entry")
		je.posting_date = nowdate()
		je.company = company
		je.voucher_type = "Journal Entry"
		je.user_remark = f"Loan Disbursement to Savings: {self.name}"

		# Dr Member Loan Account (Receivable)
		je.append("accounts", {
			"account": member.ledger_account,
			"debit_in_account_currency": self.loan_amount,
			"credit_in_account_currency": 0,
			"party_type": "Customer",
			"party": member.customer_link
		})
		
		# Cr Member Savings Account (Liability/Payable)
		je.append("accounts", {
			"account": member.savings_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": self.loan_amount,
			"is_advance": "Yes"
		})
		
		je.save()
		je.submit()

	def update_member_status(self):
		frappe.db.set_value("SACCO Member", self.member, "active_loan", self.name)

	def mark_as_defaulted(self):
		if self.status == "Defaulted":
			return

		# 1. Update Status
		self.db_set("status", "Defaulted")
		
		# 2. Create Defaulter Record
		defaulter = frappe.get_doc({
			"doctype": "SACCO Defaulter",
			"member": self.member,
			"loan": self.name,
			"overdue_amount": self.outstanding_balance, # Assuming full outstanding is now overdue
			"days_overdue": 0, # Should be calculated based on schedule vs now
			"status": "New Default"
		})
		defaulter.insert(ignore_permissions=True)
		
		# 3. Notify Guarantors
		for g in self.guarantors:
			# Fetch Guarantor email/phone
			guarantor_doc = frappe.get_doc("SACCO Member", g.guarantor_member)
			
			message = f"Dear {guarantor_doc.first_name}, the loan {self.name} you guaranteed for {self.member} has defaulted. Please be advised that you are liable for {g.guarantee_amount}."
			
			# Log Notification (Simulating Email/SMS)
			frappe.log_error(message, f"Guarantor Notification: {guarantor_doc.email}")
			
			# In a real system:
			# frappe.sendmail(recipients=[guarantor_doc.email], subject="Loan Default Notice", message=message)
			
	def update_demanded_amounts(self):
		"""
		Checks the schedule and updates total_principal_demanded and total_interest_demanded
		based on the current date.
		"""
		if not self.repayment_schedule:
			return

		import json
		try:
			schedule = json.loads(self.repayment_schedule)
		except:
			return

		today = nowdate()
		total_p = 0
		total_i = 0
		
		# Sum up what's due by today
		for entry in schedule:
			if entry.get("payment_date") <= today:
				total_p += flt(entry.get("principal_to_be_demanded", 0))
				total_i += flt(entry.get("interest_to_be_demanded", 0))
		
		self.db_set("total_principal_demanded", total_p)
		self.db_set("total_interest_demanded", total_i)
		self.reload() # Refresh local doc values
