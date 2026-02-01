# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SACCOShares(Document):
	def validate(self):
		self.total_amount = self.number_of_shares * self.share_price

	def on_submit(self):
		self.make_gl_entries()
		# Optionally update member share count

	def make_gl_entries(self):
		# Dr Cash
		# Cr Share Capital
		
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		cash_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company})
		if not cash_account:
			cash_account = frappe.db.get_value("Account", {"is_group": 0, "root_type": "Asset", "company": company})
			
		share_capital = frappe.db.get_value("Account", {"account_name": "Share Capital Account", "company": company})
		if not share_capital:
			# Find any Equity account
			share_capital = frappe.db.get_value("Account", {"root_type": "Equity", "is_group": 0, "company": company})

		je = frappe.new_doc("Journal Entry")
		je.posting_date = self.posting_date
		je.company = company
		je.voucher_type = "Journal Entry"
		je.user_remark = f"Shares Purchase: {self.name}"

		je.append("accounts", {
			"account": cash_account,
			"debit_in_account_currency": self.total_amount,
			"credit_in_account_currency": 0
		})
		
		je.append("accounts", {
			"account": share_capital,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": self.total_amount
		})
		
		je.save()
		je.submit()
