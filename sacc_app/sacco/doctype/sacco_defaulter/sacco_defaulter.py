# Copyright (c) 2024, SACCO Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SACCODefaulter(Document):
	def after_insert(self):
		self.notify_guarantors()

	def notify_guarantors(self):
		pass
