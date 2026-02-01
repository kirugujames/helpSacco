# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from sacc_app.notify import send_member_email

class SACCOMember(Document):
	def validate(self):
		self.member_name = f"{self.first_name} {self.last_name}"
		self.get_balances()

	def onload(self):
		self.get_balances()

	def get_balances(self):
		if not self.savings_account and not self.ledger_account:
			return

		# 1. Savings Balance = Sum(Credit) - Sum(Debit)
		if self.savings_account:
			self.total_savings = flt(frappe.db.sql("""
				SELECT sum(credit) - sum(debit)
				FROM `tabGL Entry`
				WHERE account = %s AND is_cancelled = 0
			""", (self.savings_account,))[0][0])
		
		# 2. Loan Outstanding = Sum(Debit) - Sum(Credit)
		if self.ledger_account:
			self.total_loan_outstanding = flt(frappe.db.sql("""
				SELECT sum(debit) - sum(credit)
				FROM `tabGL Entry`
				WHERE account = %s AND is_cancelled = 0
			""", (self.ledger_account,))[0][0])
		
		# Update values in DB without triggering hooks
		if self.name:
			frappe.db.set_value("SACCO Member", self.name, {
				"total_savings": self.total_savings,
				"total_loan_outstanding": self.total_loan_outstanding
			}, update_modified=False)
	def after_insert(self):
		self.create_customer()
		self.create_registration_invoice()
		self.create_system_user()
		
		# Send Welcome Email
		send_member_email(self.name, "Welcome to SACCO!", 
			f"You have been successfully registered as a member. Your Member ID is <b>{self.name}</b>. "
			"We are excited to have you onboard!")

	def create_system_user(self):
		if not self.email:
			return

		if frappe.db.exists("User", self.email):
			user = frappe.get_doc("User", self.email)
		else:
			user = frappe.get_doc({
				"doctype": "User",
				"email": self.email,
				"first_name": self.first_name,
				"last_name": self.last_name,
				"enabled": 1,
				"send_welcome_email": 0 # User can reset password later
			})
			user.insert(ignore_permissions=True)
		
		# Assign 'SACCO Member' role if not already assigned
		if not any(r.role == "SACCO Member" for r in user.roles):
			user.append("roles", {"role": "SACCO Member"})
			user.save(ignore_permissions=True)
			
		self.db_set("user", user.name)

	def create_customer(self):
		if not self.customer_link:
			# Check if customer exists
			if frappe.db.exists("Customer", self.name):
				self.db_set("customer_link", self.name)
				return

			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": self.member_name,
				"customer_group": "All Customer Groups", # Will create 'SACCO Members' group if needed later
				"customer_type": "Individual",
				"territory": "All Territories"
			})
			customer.insert(ignore_permissions=True)
			self.db_set("customer_link", customer.name)
			self.create_ledger_account(customer.name)

	def create_savings_account(self, parent_account, company):
		# Create individual savings account under the liability parent
		account_name = f"SAV-{self.name} - {self.member_name}"
		if not frappe.db.exists("Account", account_name):
			account = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent_account,
				"company": company,
				"account_type": "", # Leave blank to avoid strict Payable/Supplier validation
			})
			account.insert(ignore_permissions=True)
			self.db_set("savings_account", account.name)

	def create_ledger_account(self, customer_name):
		# For simplicity getting default company
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		
		# 1. Handle Loan Account (Receivable)
		parent_loan_name = "SACCO Members Accounts"
		parent_loan = frappe.db.get_value("Account", {"account_name": parent_loan_name, "company": company})
		
		if not parent_loan:
			ar_root = frappe.db.get_value("Account", {"account_type": "Receivable", "is_group": 1, "company": company})
			if ar_root:
				parent_doc = frappe.get_doc({
					"doctype": "Account",
					"account_name": parent_loan_name,
					"parent_account": ar_root,
					"company": company,
					"is_group": 1,
					"account_type": "Receivable"
				})
				parent_doc.insert(ignore_permissions=True)
				parent_loan = parent_doc.name
		
		# 2. Handle Savings Account (Liability)
		parent_savings_name = "SACCO Member Savings"
		parent_savings = frappe.db.get_value("Account", {"account_name": parent_savings_name, "company": company})
		
		if not parent_savings:
			liab_root = frappe.db.get_value("Account", {"root_type": "Liability", "is_group": 1, "company": company})
			if liab_root:
				parent_doc = frappe.get_doc({
					"doctype": "Account",
					"account_name": parent_savings_name,
					"parent_account": liab_root,
					"company": company,
					"is_group": 1,
					"account_type": "Payable"
				})
				parent_doc.insert(ignore_permissions=True)
				parent_savings = parent_doc.name

		if parent_savings:
			self.create_savings_account(parent_savings, company)

		if parent_loan:
			# Create individual account
			account_name = f"{self.name} - {self.member_name}"
			if not frappe.db.exists("Account", account_name):
				account = frappe.get_doc({
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": parent_loan,
					"company": company,
					"account_type": "Receivable"
				})
				account.insert(ignore_permissions=True)
				self.db_set("ledger_account", account.name)
				
				# Send Finance Account Notification
				send_member_email(self.name, "Financial Account Provisioned", 
					f"Your dedicated SACCO accounts <b>{account.name}</b> (Loans) and <b>{self.savings_account}</b> (Savings) have been created. "
					"You can now begin making deposits.")

	def create_registration_invoice(self):
		settings = frappe.get_single("SACCO Settings")
		if not settings.charge_registration_fee_on_onboarding:
			return

		fee_amount = settings.registration_fee or 0
		if fee_amount <= 0:
			return

		if not frappe.db.exists("Item", "Registration Fee"):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": "Registration Fee",
				"item_name": "SACCO Registration Fee",
				"item_group": "Services",
				"is_stock_item": 0,
				"standard_rate": fee_amount
			})
			item.insert(ignore_permissions=True)
		else:
			# Update item rate if different? 
			# For now just use it.
			pass
			
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		
		si = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": self.customer_link,
			"company": company,
			"due_date": frappe.utils.nowdate(),
			"items": [{
				"item_code": "Registration Fee",
				"qty": 1,
				"rate": fee_amount
			}]
		})
		si.insert(ignore_permissions=True)
		si.submit()
		
		self.db_set("status", "Pending Payment")
		
		# Send Invoice Notification
		send_member_email(self.name, "Registration Fee Invoice", 
			f"Your registration invoice <b>{si.name}</b> for amount <b>{si.grand_total}</b> has been generated. "
			"Please pay to activate your membership.")
            
		frappe.msgprint(f"Registration Invoice {si.name} created. Please pay to activate membership.")

