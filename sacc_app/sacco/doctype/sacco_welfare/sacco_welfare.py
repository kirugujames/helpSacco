# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SACCOWelfare(Document):
	def on_submit(self):
		self.make_gl_entries()
		if self.purpose == "Emergency" and self.type == "Contribution":
			self.notify_whatsapp()

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
