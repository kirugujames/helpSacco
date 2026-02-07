# Copyright (c) 2026, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SACCOWelfareClaim(Document):
	def validate(self):
		"""Validate the claim before saving."""
		if self.amount_paid and self.amount_paid > self.claim_amount:
			frappe.throw("Amount paid cannot exceed claim amount")
		
		# Auto-update status based on payment
		if self.amount_paid:
			if self.amount_paid >= self.claim_amount:
				self.status = "Paid"
			elif self.amount_paid > 0:
				self.status = "Partially Paid"
	
	def on_update(self):
		"""Send notification when claim status changes."""
		if self.has_value_changed("status"):
			self.notify_member()
	
	def notify_member(self):
		"""Notify member about claim status update."""
		from sacc_app.notify import send_member_email
		
		status_messages = {
			"Approved": f"Your welfare claim {self.name} for {self.reason} has been approved.",
			"Rejected": f"Your welfare claim {self.name} for {self.reason} has been rejected.",
			"Paid": f"Your welfare claim {self.name} has been paid. Amount: {self.amount_paid}",
			"Partially Paid": f"Your welfare claim {self.name} has been partially paid. Amount: {self.amount_paid}"
		}
		
		if self.status in status_messages:
			subject = f"Welfare Claim Update - {self.status}"
			message = f"<p>{status_messages[self.status]}</p>"
			
			try:
				send_member_email(self.member, subject, message)
			except Exception as e:
				frappe.log_error(f"Failed to send notification: {str(e)}", "Welfare Claim Notification")
