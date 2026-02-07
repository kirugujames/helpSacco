# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class SACCOWelfare(Document):
	def validate(self):
		if self.welfare_claim:
			claim = frappe.get_doc("SACCO Welfare Claim", self.welfare_claim)
			
			if claim.status != "Approved":
				frappe.throw(f"Cannot contribute to a claim with status '{claim.status}'. Only 'Approved' claims accept contributions.")

			if claim.amount_per_member > 0:
				# Calculate cumulative contribution for this member on this claim
				existing_contribution = frappe.db.get_value("SACCO Welfare", 
					{"member": self.member, "welfare_claim": self.welfare_claim, "docstatus": 1, "name": ["!=", self.name or ""]}, 
					"sum(contribution_amount)") or 0
				
				total_planned = flt(existing_contribution) + flt(self.contribution_amount)
				
				if total_planned > flt(claim.amount_per_member):
					frappe.throw(f"Total contribution for this member exceeds the limit of {claim.amount_per_member}. Current total: {existing_contribution}, Adding: {self.contribution_amount}")

		elif self.type == "Contribution":
			min_contribution = frappe.db.get_single_value("SACCO Settings", "welfare_contribution_amount")
			if min_contribution and self.contribution_amount < min_contribution:
				frappe.throw(f"Contribution amount must be at least {min_contribution}")

	def on_submit(self):
		self.make_gl_entries()
		if self.welfare_claim:
			self.update_claim_total()
		if self.purpose == "Emergency" and self.type == "Contribution":
			self.notify_whatsapp()

	def update_claim_total(self):
		total = frappe.db.get_value("SACCO Welfare", {"welfare_claim": self.welfare_claim, "docstatus": 1}, "sum(contribution_amount)") or 0
		frappe.db.set_value("SACCO Welfare Claim", self.welfare_claim, "total_collected", total)

	def make_gl_entries(self):
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		cash_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company})
		if not cash_account:
			cash_account = frappe.db.get_value("Account", {"is_group": 0, "root_type": "Asset", "company": company})
		
		welfare_fund = frappe.db.get_value("Account", {"account_name": "Welfare Fund Account", "company": company})
		if not welfare_fund:
			welfare_fund = frappe.db.get_value("Account", {"root_type": "Liability", "is_group": 0, "company": company})

		je = frappe.new_doc("Journal Entry")
		je.posting_date = self.posting_date
		je.company = company
		je.voucher_type = "Journal Entry"
		je.user_remark = f"Welfare {self.type}: {self.name}"

		if self.type == "Contribution":
			# Dr Cash, Cr Welfare Fund
			je.append("accounts", {
				"account": cash_account,
				"debit_in_account_currency": self.contribution_amount,
				"credit_in_account_currency": 0
			})
			je.append("accounts", {
				"account": welfare_fund,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": self.contribution_amount
			})
		else:
			# Withdrawal: Dr Welfare Fund, Cr Cash
			je.append("accounts", {
				"account": welfare_fund,
				"debit_in_account_currency": self.contribution_amount,
				"credit_in_account_currency": 0
			})
			je.append("accounts", {
				"account": cash_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": self.contribution_amount
			})
		
		je.save()
		je.submit()

	def notify_whatsapp(self):
		# Placeholder for WhatsApp integration
		pass
