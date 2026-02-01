import frappe
from frappe import _
from sacc_app.swagger_spec import get_swagger_spec


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		frappe.clear_messages()
		frappe.local.response["message"] = {
			"success_key": 0,
			"message": "Authentication Failed. Please check your credentials."
		}
		return

	api_generate = generate_keys(frappe.session.user)
	user = frappe.get_doc("User", frappe.session.user)
	
	# Send OTP upon successful login
	send_otp(user.email)

	company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
	
	frappe.local.response["message"] = {
		"success_key": 1,
		"message": "Authentication Success. OTP sent to your email.",
		"sid": frappe.session.sid,
		"api_key": user.api_key,
		"api_secret": api_generate,
		"username": user.username,
		"email": user.email,
		"company": company
	}

def generate_keys(user):
	user_doc = frappe.get_doc("User", user)
	api_secret = frappe.generate_hash(length=15)
	if not user_doc.api_key:
		api_key = frappe.generate_hash(length=15)
		user_doc.api_key = api_key
	user_doc.api_secret = api_secret
	user_doc.save(ignore_permissions=True)
	return api_secret

@frappe.whitelist(allow_guest=True)
def get_member_profile():
	user = frappe.session.user
	# Find linked member
	# Assuming User email = Member email for correlation
	member = frappe.db.get_value("SACCO Member", {"email": user}, ["name", "member_name", "total_savings", "active_loan", "status"], as_dict=1)
	if not member:
		return {"status": "error", "message": "Member profile not found for current user"}
	
	return {"status": "success", "data": member}

def save_base64_image(base64_str, filename, doctype, docname):
    """
    Decodes a base64 string and saves it as a file linked to the doc.
    Returns the file URL.
    """
    if not base64_str or not base64_str.startswith("data:image"):
        return base64_str

    from frappe.utils.file_manager import save_file
    import base64

    header, encoded = base64_str.split(",", 1)
    content = base64.b64decode(encoded)
    
    file_doc = save_file(filename, content, doctype, docname, is_private=0)
    return file_doc.file_url

@frappe.whitelist(allow_guest=True)
def create_member_application(data=None, **kwargs):
    # data can be a JSON string, a dict, or we use kwargs for flat POST
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    doc = frappe.get_doc({
        "doctype": "SACCO Member",
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "national_id": data.get("national_id"),
        "county": data.get("county"),
        "sub_county": data.get("sub_county"),
        "ward": data.get("ward"),
        "village": data.get("village"),
        "status": "Probation" # Default
    })
    doc.insert(ignore_permissions=True)
    
    # Process Base64 images if present
    if data.get("national_id_image"):
        doc.national_id_image = save_base64_image(data.get("national_id_image"), f"ID_{doc.name}.png", "SACCO Member", doc.name)
    if data.get("passport_photo"):
        doc.passport_photo = save_base64_image(data.get("passport_photo"), f"Photo_{doc.name}.png", "SACCO Member", doc.name)
        
    if data.get("national_id_image") or data.get("passport_photo"):
        doc.save(ignore_permissions=True)
        
    return {"status": "success", "message": "Member application created", "member_id": doc.name}


@frappe.whitelist(allow_guest=True)
def get_openapi_spec():
    import json
    spec = get_swagger_spec()
    frappe.response['type'] = 'binary'
    frappe.response['filename'] = 'openapi.json'
    frappe.response['content_type'] = 'application/json'
    frappe.response['filecontent'] = json.dumps(spec)
    
@frappe.whitelist(allow_guest=True)
def apply_for_loan(data=None, **kwargs):
    # data is a JSON string, dict, or flat kwargs
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    member = data.get("member")
    amount = data.get("amount")
    product_name = data.get("loan_product")
    guarantors = data.get("guarantors", []) # List of {member: "ID", amount: 1000}
    
    # 1. Fetch Loan Product Settings
    product = frappe.get_doc("SACCO Loan Product", product_name)
    
    # Validate Amount
    if product.max_loan_amount > 0 and amount > product.max_loan_amount:
        return {"status": "error", "message": f"Loan amount exceeds maximum allowed ({product.max_loan_amount}) for this product."}
        
    # Validate Guarantors if required
    if product.requires_guarantor:
        if not guarantors:
             return {"status": "error", "message": "This loan product requires guarantors."}
        
        # Enforce minimum number of guarantors
        min_g = getattr(product, "min_guarantors", 0)
        if len(guarantors) < min_g:
            return {"status": "error", "message": f"This loan product requires at least {min_g} guarantors. Provided: {len(guarantors)}"}
        
        total_guaranteed = sum([float(g.get("amount", 0)) for g in guarantors])
        if total_guaranteed < amount:
             # Strict check: guarantee must cover loan? Or partial?
             # For now, let's warn or enforce at least some coverage. 
             # Let's assume 100% coverage for simplicity or just ensure they exist.
             if total_guaranteed < amount:
                 pass # Warning: "Guarantees cover only X amount"
    
    doc = frappe.get_doc({
        "doctype": "SACCO Loan",
        "member": member,
        "loan_amount": amount,
        "loan_product": product_name,
        "interest_rate": product.interest_rate,
        "interest_period": product.interest_period,
        "interest_method": product.interest_method,
        "repayment_period": product.max_repayment_period, # Default to max, can be overridden if passed
        "status": "Draft"
    })
    
    # Add Guarantors
    for g in guarantors:
        doc.append("guarantors", {
            "guarantor_member": g.get("member"),
            "guarantee_amount": g.get("amount")
        })
        
    doc.insert(ignore_permissions=True) 
    return {"status": "success", "message": "Loan application created", "loan_id": doc.name}

# --- Loan Product CRUD ---

@frappe.whitelist(allow_guest=True)
def create_loan_product(data=None, **kwargs):
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
    
    doc = frappe.get_doc({"doctype": "SACCO Loan Product", **data})
    doc.insert(ignore_permissions=True)
    return {"status": "success", "message": f"Product '{doc.name}' created."}

@frappe.whitelist(allow_guest=True)
def get_all_loan_products():
    products = frappe.db.get_all("SACCO Loan Product", fields=["name", "interest_rate", "max_loan_amount", "requires_guarantor"])
    return {"status": "success", "data": products}

@frappe.whitelist(allow_guest=True)
def update_loan_product(product_name, data=None, **kwargs):
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    doc = frappe.get_doc("SACCO Loan Product", product_name)
    for k, v in data.items():
        setattr(doc, k, v)
    doc.save()
    return {"status": "success", "message": f"Product '{product_name}' updated."}

@frappe.whitelist(allow_guest= True  )
def delete_loan_product(product_name):
    frappe.delete_doc("SACCO Loan Product", product_name)
    return {"status": "success", "message": f"Product '{product_name}' deleted."}

@frappe.whitelist(allow_guest= True  )
def mark_loan_default(loan_id):
    loan = frappe.get_doc("SACCO Loan", loan_id)
    loan.mark_as_defaulted()
    return {"status": "success", "message": f"Loan {loan_id} marked as defaulted."}

@frappe.whitelist(allow_guest= True  )
def get_all_loan_applications():
    loans = frappe.db.get_all("SACCO Loan", fields=["name", "member", "loan_product", "loan_amount", "status", "creation"])
    return {"status": "success", "data": loans}

@frappe.whitelist(allow_guest= True  )
def submit_loan_application(loan_id):
    loan = frappe.get_doc("SACCO Loan", loan_id)
    if loan.status != "Draft":
        return {"status": "error", "message": f"Loan {loan_id} is already in {loan.status} status. Only Draft loans can be submitted."}
    
    loan.status = "Pending Approval"
    loan.save(ignore_permissions=True)
    return {"status": "success", "message": f"Loan {loan_id} submitted for approval.", "new_status": loan.status}

@frappe.whitelist(allow_guest= True  )
def approve_loan_application(loan_id):
    loan = frappe.get_doc("SACCO Loan", loan_id)
    if loan.status != "Pending Approval":
        return {"status": "error", "message": f"Loan {loan_id} must be in 'Pending Approval' status to be approved. Current: {loan.status}"}
    
    loan.status = "Approved"
    loan.save(ignore_permissions=True)
    return {"status": "success", "message": f"Loan {loan_id} approved.", "new_status": loan.status}

@frappe.whitelist(allow_guest= True  )
def disburse_loan(loan_id):
    loan = frappe.get_doc("SACCO Loan", loan_id)
    if loan.status != "Approved":
        return {"status": "error", "message": f"Loan {loan_id} must be 'Approved' before it can be disbursed. Current: {loan.status}"}
    
    # Submitting will trigger on_submit in sacco_loan.py
    # which handles accounting and activation.
    loan.submit()
    return {"status": "success", "message": f"Loan {loan_id} disbursed and activated.", "outstanding_balance": loan.outstanding_balance}

# --- User & Role Management ---

@frappe.whitelist(allow_guest= True  )
def get_all_roles():
    roles = frappe.db.get_all("Role", fields=["name", "role_name", "desk_access"])
    return {"status": "success", "data": roles}

@frappe.whitelist(allow_guest= True  )
def update_role(role_name, desk_access=0):
    if not frappe.db.exists("Role", role_name):
        return {"status": "error", "message": f"Role {role_name} not found."}
        
    role = frappe.get_doc("Role", role_name)
    role.desk_access = int(desk_access)
    role.save(ignore_permissions=True)
    return {"status": "success", "message": f"Role {role_name} updated."}

@frappe.whitelist(allow_guest=True)
def update_member(member_id, data=None, **kwargs):
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)

    if not frappe.db.exists("SACCO Member", member_id):
        return {"status": "error", "message": "Member not found"}
        
    member_doc = frappe.get_doc("SACCO Member", member_id)
    
    # Handle Base64 images in updates
    if data.get("national_id_image") and data.get("national_id_image").startswith("data:"):
        data["national_id_image"] = save_base64_image(data.get("national_id_image"), f"ID_{member_id}.png", "SACCO Member", member_id)
    if data.get("passport_photo") and data.get("passport_photo").startswith("data:"):
        data["passport_photo"] = save_base64_image(data.get("passport_photo"), f"Photo_{member_id}.png", "SACCO Member", member_id)
        
    member_doc.update(data)
    member_doc.save(ignore_permissions=True)
    return {"status": "success", "message": "Member updated"}

@frappe.whitelist(allow_guest= True  )
def delete_role(role_name):
    if not frappe.db.exists("Role", role_name):
        return {"status": "error", "message": f"Role {role_name} not found."}
    
    # Check if standard role
    if frappe.get_doc("Role", role_name).is_custom == 0:
         return {"status": "error", "message": "Cannot delete standard System roles."}
         
    frappe.delete_doc("Role", role_name)
    return {"status": "success", "message": f"Role {role_name} deleted."}

@frappe.whitelist(allow_guest= True  )
def get_role_permissions(role):
    # Get all custom docperms for this role
    perms = frappe.db.get_all("Custom DocPerm", filters={"role": role}, fields=["parent", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "share", "print", "email"])
    
    # Also fetch standard permissions from DocTypes directly if no custom perm exists?
    # Frappe's permission system is complex. Usually 'Custom DocPerm' overrides.
    # But if we want *effective* permissions it's hard to list "all" doctypes.
    # We will list what is explicitly defined in Custom DocPerms (which is what assign_permission sets).
    
    return {"status": "success", "data": perms}

@frappe.whitelist(allow_guest= True  )
def create_role(role_name):
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        return {"status": "success", "message": f"Role '{role_name}' created."}
    return {"status": "skipped", "message": f"Role '{role_name}' already exists."}

@frappe.whitelist(allow_guest= True  )
def create_user(email, first_name, last_name, roles=None):
    # roles can be a JSON string list or list
    if not frappe.db.exists("User", email):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "send_welcome_email": 0
        })
        user.insert(ignore_permissions=True)
        
        if roles:
            import json
            if isinstance(roles, str):
                roles = json.loads(roles)
            
            for role in roles:
                user.add_roles(role)
                
        return {"status": "success", "message": f"User '{email}' created.", "user": email}
    return {"status": "error", "message": f"User '{email}' already exists."}

@frappe.whitelist(allow_guest= True  )
@frappe.whitelist(allow_guest= True  )
def assign_permission(doctype, role, read=0, write=0, create=0, delete=0, submit=0, cancel=0, amend=0, print=0, email=0, report=0, share=0, export=0):
    """
    Assigns permissions to a Role for a specific DocType.
    Equivalent to adding a row in the Role Permissions Manager.
    """
    dt = frappe.get_doc("DocType", doctype)
    
    # Check if this role already has an entry in permissions
    found = False
    for p in dt.permissions:
        if p.role == role:
            # Update existing
            p.read = int(read)
            p.write = int(write)
            p.create = int(create)
            p.delete = int(delete)
            p.submit = int(submit)
            p.cancel = int(cancel)
            p.amend = int(amend)
            p.print = int(print)
            p.email = int(email)
            p.report = int(report)
            p.share = int(share)
            p.export = int(export)
            found = True
            break
            
    if not found:
        dt.append("permissions", {
            "role": role,
            "read": int(read),
            "write": int(write),
            "create": int(create),
            "delete": int(delete),
            "submit": int(submit),
            "cancel": int(cancel),
            "amend": int(amend),
            "print": int(print),
            "email": int(email),
            "report": int(report),
            "share": int(share),
            "export": int(export)
        })
    
    dt.save(ignore_permissions=True)
    return {"status": "success", "message": f"Permissions updated for {role} on {doctype}"}

@frappe.whitelist(allow_guest=True)
def update_doctype_permissions(doctype, role, permissions):
    """
    Updates permissions for a Role on a DocType using a permissions object.
    Example permissions structure: {"read": 1, "write": 0, "create": 1, ...}
    """
    if isinstance(permissions, str):
        import json
        permissions = json.loads(permissions)

    return assign_permission(doctype, role, **permissions)

# --- Account & Expenses ---

@frappe.whitelist(allow_guest= True  )
def create_account(account_name, parent_account, is_group=0, account_type=None):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Check if exists
    if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
         return {"status": "error", "message": "Account already exists"}
         
    # Verify parent
    parent = frappe.db.get_value("Account", {"account_name": parent_account, "company": company})
    if not parent:
        return {"status": "error", "message": f"Parent account '{parent_account}' not found."}

    acc = frappe.get_doc({
        "doctype": "Account",
        "account_name": account_name,
        "parent_account": parent, # The ID (name) of parent
        "company": company,
        "is_group": int(is_group),
        "account_type": account_type or ""
    })
    acc.insert(ignore_permissions=True)
    return {"status": "success", "message": f"Account '{account_name}' created.", "name": acc.name}

@frappe.whitelist(allow_guest= True  )
def record_expense(amount, expense_account, description, mode_of_payment="Cash"):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Get Cash/Bank Account
    credit_account = None
    if mode_of_payment == "Cash":
        credit_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company})
    else:
        credit_account = frappe.db.get_value("Account", {"account_type": "Bank", "company": company})
        
    expense_acc_name = frappe.db.get_value("Account", {"account_name": expense_account, "company": company})
    
    if not credit_account or not expense_acc_name:
        return {"status": "error", "message": "Invalid Accounts"}

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = frappe.utils.nowdate()
    je.company = company
    je.user_remark = description
    
    # Dr Expense
    je.append("accounts", {
        "account": expense_acc_name,
        "debit_in_account_currency": amount,
        "credit_in_account_currency": 0
    })
    
    # Cr Cash/Bank
    je.append("accounts", {
        "account": credit_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": amount
    })
    
    je.save(ignore_permissions=True)
    je.submit()
    return {"status": "success", "message": "Expense recorded.", "reference": je.name}

# --- Transactions ---

@frappe.whitelist(allow_guest= True  )
def record_savings_deposit(member, amount, mode="Cash", reference=None):
    doc = frappe.get_doc({
        "doctype": "SACCO Savings",
        "member": member,
        "type": "Deposit",
        "amount": amount,
        "payment_mode": mode,
        "reference_number": reference or "",
        "posting_date": frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"status": "success", "message": "Savings deposit recorded.", "id": doc.name}

@frappe.whitelist(allow_guest= True  )
def record_savings_withdrawal(member, amount, mode="Cash", reference=None):
    doc = frappe.get_doc({
        "doctype": "SACCO Savings",
        "member": member,
        "type": "Withdrawal",
        "amount": amount,
        "payment_mode": mode,
        "reference_number": reference or "",
        "posting_date": frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"status": "success", "message": "Savings withdrawal recorded.", "id": doc.name}

@frappe.whitelist(allow_guest= True  )
def record_loan_repayment(loan, amount, member=None, mode="Cash", reference=None, deduct_from_savings=False):
    # Validate loan belongs to member if member is provided
    if member:
        loan_member = frappe.db.get_value("SACCO Loan", loan, "member")
        if loan_member != member:
             return {"status": "error", "message": f"Loan {loan} does not belong to member {member}"}

    # API Payload logic: If deduct_from_savings is true, override mode
    if deduct_from_savings and str(deduct_from_savings).lower() in ["true", "1", "yes"]:
        mode = "Savings"

    doc = frappe.get_doc({
        "doctype": "SACCO Loan Repayment",
        "loan": loan,
        "member": member, # Optional, will be auto-fetched if None but good to set if passed
        "payment_amount": amount,
        "payment_mode": mode,
        "reference_number": reference,
        "payment_date": frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"status": "success", "message": "Repayment recorded.", "id": doc.name, "member": doc.member}

@frappe.whitelist(allow_guest= True  )
def get_member_invoices(member):
    member_doc = frappe.get_doc("SACCO Member", member)
    invoices = frappe.db.get_all("Sales Invoice", 
        filters={"customer": member_doc.customer_link, "docstatus": 1, "status": ["!=", "Paid"]},
        fields=["name", "grand_total", "outstanding_amount", "due_date"]
    )
    return {"status": "success", "invoices": invoices}

@frappe.whitelist(allow_guest=True)
def pay_registration_fee(member, amount=None, mode="Cash", reference=None):
    member_doc = frappe.get_doc("SACCO Member", member)
    
    # Find active registration invoice
    invoice = frappe.db.sql("""
        SELECT name, outstanding_amount 
        FROM `tabSales Invoice` 
        WHERE customer = %s AND docstatus = 1 AND status != 'Paid'
        AND name IN (SELECT parent FROM `tabSales Invoice Item` WHERE item_code = 'Registration Fee')
    """, (member_doc.customer_link,), as_dict=True)
    
    if not invoice:
        return {"status": "error", "message": "No pending registration fee invoice found."}
    
    inv_name = invoice[0].name
    outstanding = float(invoice[0].outstanding_amount)
    
    # Strict validation of paid amount
    if amount is not None:
        paid_amt = float(amount)
        if paid_amt < outstanding:
            frappe.throw(f"Partial payment not allowed for registration. Required: {outstanding}, Provided: {paid_amt}")
        if paid_amt > outstanding:
            frappe.throw(f"Excess payment not allowed. Required: {outstanding}, Provided: {paid_amt}")
    else:
        amount = outstanding

    # Create Payment Entry
    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": member_doc.customer_link,
        "paid_amount": amount,
        "received_amount": amount,
        "reference_no": reference,
        "reference_date": frappe.utils.nowdate(),
        "mode_of_payment": mode,
        "paid_to": frappe.db.get_value("Account", {"account_type": "Cash", "company": frappe.defaults.get_user_default("Company")}, "name") 
    })
    pe.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": inv_name,
        "allocated_amount": amount
    })
    pe.insert(ignore_permissions=True)
    pe.submit()
    
    # Activate Member
    frappe.db.set_value("SACCO Member", member, "status", "Active")
    frappe.db.set_value("SACCO Member", member, "registration_fee_paid", 1)
    
    return {"status": "success", "message": "Registration fee paid. Member activated.", "payment_entry": pe.name}

# --- Reporting ---

@frappe.whitelist(allow_guest=True)
def get_member_financial_history(member, savings_start=0, savings_limit=20, repayments_start=0, repayments_limit=20):
    savings_start = int(savings_start)
    savings_limit = int(savings_limit)
    repayments_start = int(repayments_start)
    repayments_limit = int(repayments_limit)

    # Savings
    savings = frappe.db.get_all("SACCO Savings", 
        filters={"member": member, "docstatus": 1}, 
        fields=["name", "posting_date", "amount", "payment_mode", "type", "reference_number"],
        order_by="posting_date desc",
        limit_start=savings_start,
        limit_page_length=savings_limit
    )
    
    # Loans (Active and Historical)
    loans = frappe.db.get_all("SACCO Loan", 
        filters={"member": member}, 
        fields=["name", "loan_amount", "status", "outstanding_balance", "loan_type", "loan_product", "repayment_period", "creation"],
        order_by="creation desc"
    )
    
    # All Loan Repayments
    repayments = frappe.db.get_all("SACCO Loan Repayment", 
        filters={"member": member, "docstatus": 1}, 
        fields=["name", "payment_date", "payment_amount", "loan", "payment_mode", "reference_number"],
        order_by="payment_date desc",
        limit_start=repayments_start,
        limit_page_length=repayments_limit
    )
        
    return {
        "status": "success",
        "savings": savings,
        "loans": loans,
        "repayments": repayments,
        "savings_pagination": {
            "start": savings_start,
            "limit": savings_limit
        },
        "repayments_pagination": {
            "start": repayments_start,
            "limit": repayments_limit
        }
    }

@frappe.whitelist(allow_guest= True  )
def get_loan_products():
    # Since we hardcoded types in logic, returning static list or config
    return {
        "status": "success",
        "products": [
            {"type": "Short-term", "interest": "10%", "max_period": "Dependent on Amount"},
            {"type": "Long-term", "interest": "10%", "max_period": "Dependent on Amount"},
            {"type": "Table Banking", "interest": "10%", "max_period": "Dependent on Amount"}
        ]
    }

# --- Member CRUD ---

@frappe.whitelist(allow_guest=True)
def get_all_members():
    members = frappe.db.get_all("SACCO Member", fields=["name", "member_name", "phone", "email", "status", "national_id", "total_savings"])
    return {"status": "success", "data": members}

@frappe.whitelist(allow_guest= True  )
def delete_member(member_id):
    frappe.delete_doc("SACCO Member", member_id)
    return {"status": "success", "message": f"Member {member_id} deleted."}

# --- Account Queries ---

@frappe.whitelist(allow_guest= True  )
def get_parent_accounts():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    accounts = frappe.db.get_all("Account", filters={"is_group": 1, "company": company}, fields=["name", "account_name", "root_type"])
    return {"status": "success", "data": accounts}

@frappe.whitelist(allow_guest= True  )
def get_expense_accounts():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    # Fetch accounts where root_type is Expense and is not a group
    accounts = frappe.db.get_all("Account", filters={"is_group": 0, "root_type": "Expense", "company": company}, fields=["name", "account_name"])
    return {"status": "success", "data": accounts}

# --- Metadata & Permissions ---

@frappe.whitelist(allow_guest=True)
def get_doctypes_and_permissions(module="Sacco"):
    # Fetch DocTypes for the module
    doctypes = frappe.db.get_all("DocType", filters={"module": module, "istable": 0}, fields=["name"])
    
    results = []
    user_roles = frappe.get_roles()
    
    for dt in doctypes:
        # Get permissions for this doctype for current user
        # frappe.permissions.get_role_permissions returns a specific structure
        # We can also check explicit rights
        
        perms = {
            "read": frappe.has_permission(dt.name, "read"),
            "write": frappe.has_permission(dt.name, "write"),
            "create": frappe.has_permission(dt.name, "create"),
            "delete": frappe.has_permission(dt.name, "delete"),
            "submit": frappe.has_permission(dt.name, "submit"),
            "cancel": frappe.has_permission(dt.name, "cancel"),
            "amend": frappe.has_permission(dt.name, "amend"),
            "report": frappe.has_permission(dt.name, "report"),
        }
        
        results.append({
            "doctype": dt.name,
            "title": dt.name,  # Use name as title since column doesn't exist
            "permissions": perms
        })
        
    return {"status": "success", "data": results}

# --- Reporting Expansion ---

@frappe.whitelist(allow_guest=True)
def get_all_savings_deposits():
    deposits = frappe.db.get_all("SACCO Savings", 
        fields=["name", "member", "member.member_name as member_name", "amount", "posting_date", "payment_mode"])
    return {"status": "success", "data": deposits}

@frappe.whitelist(allow_guest= True  )
def get_all_loan_repayments():
    repayments = frappe.db.get_all("SACCO Loan Repayment", 
        fields=["name", "loan", "member", "member.member_name as member_name", "payment_amount", "payment_date", "payment_mode"])
    return {"status": "success", "data": repayments}

@frappe.whitelist(allow_guest= True  )
def get_all_expenses():
    # Fetch Journal Entries where an account with root_type 'Expense' is debited
    expenses = frappe.db.sql("""
        SELECT 
            je.name, je.posting_date, jea.account, jea.debit as amount, je.user_remark
        FROM 
            `tabJournal Entry` je
        JOIN 
            `tabJournal Entry Account` jea ON jea.parent = je.name
        JOIN 
            `tabAccount` acc ON acc.name = jea.account
        WHERE 
            acc.root_type = 'Expense' AND jea.debit > 0 AND je.docstatus = 1
    """, as_dict=True)
    return {"status": "success", "data": expenses}

@frappe.whitelist(allow_guest= True  )
def get_all_accounts_with_balances():
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    accounts = frappe.db.get_all("Account", filters={"company": company}, fields=["name", "account_name", "account_type", "root_type"])
    
    from frappe.utils import flt
    from erpnext.accounts.utils import get_balance_on
    
    results = []
    for acc in accounts:
        balance = get_balance_on(acc.name)
        results.append({
            "name": acc.name,
            "account_name": acc.account_name,
            "account_type": acc.account_type,
            "root_type": acc.root_type,
            "balance": flt(balance)
        })
        
    return {"status": "success", "data": results}

# --- Status Management ---

@frappe.whitelist(allow_guest= True  )
def set_member_status(member_id, status):
    """
    Sets the status of a SACCO Member (e.g., Active, Inactive, Suspended).
    """
    if not frappe.db.exists("SACCO Member", member_id):
        return {"status": "error", "message": f"Member {member_id} not found."}
    
    frappe.db.set_value("SACCO Member", member_id, "status", status)
    return {"status": "success", "message": f"Member {member_id} status set to {status}."}

@frappe.whitelist(allow_guest= True  )
def set_user_status(user_id, status):
    """
    Enables or disables a system user. status should be 1 (Active) or 0 (Disabled).
    """
    if not frappe.db.exists("User", user_id):
        return {"status": "error", "message": f"User {user_id} not found."}
    
    enabled = 1 if str(status).lower() in ["1", "active", "true"] else 0
    frappe.db.set_value("User", user_id, "enabled", enabled)
    
    status_text = "Enabled" if enabled else "Disabled"
    return {"status": "success", "message": f"User {user_id} has been {status_text}."}

# --- Core Financial Reports ---

@frappe.whitelist(allow_guest=True)
def get_profit_and_loss(from_date, to_date):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "periodicity": "Monthly"
    }
    from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute
    columns, data = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data}

@frappe.whitelist(allow_guest=True)
def get_balance_sheet(to_date):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters = {
        "company": company,
        "to_date": to_date,
        "periodicity": "Monthly"
    }
    from erpnext.accounts.report.balance_sheet.balance_sheet import execute
    columns, data = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data}

@frappe.whitelist(allow_guest=True)
def get_trial_balance(from_date, to_date):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date
    }
    from erpnext.accounts.report.trial_balance.trial_balance import execute
    columns, data = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data}

@frappe.whitelist(allow_guest=True)
def get_account_statement(account, from_date, to_date):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters = {
        "company": company,
        "account": [account],
        "from_date": from_date,
        "to_date": to_date,
        "group_by": "Group by Voucher (Consolidated)"
    }
    from erpnext.accounts.report.general_ledger.general_ledger import execute
    columns, data = execute(filters)
    return {"status": "success", "columns": columns, "data": data}

# --- Operational Reports ---

@frappe.whitelist(allow_guest=True)
def get_loan_repayment_summary(from_date=None, to_date=None):
    filters = {}
    if from_date and to_date:
        filters["payment_date"] = ["between", [from_date, to_date]]
        
    data = frappe.db.get_all("SACCO Loan Repayment",
        filters=filters,
        fields=["loan", "member", "payment_amount", "payment_date", "payment_mode"],
        order_by="payment_date desc"
    )
    return {"status": "success", "data": data}

@frappe.whitelist(allow_guest=True)
def get_loan_aging_report(bucket=None):
    """
    Returns loans categorized by overdue days: 30, 60, 90, 120+.
    """
    query = """
        SELECT 
            l.name as loan_id,
            l.member,
            l.loan_amount,
            l.outstanding_balance,
            l.status,
            COALESCE(d.days_overdue, 0) as days_overdue,
            CASE 
                WHEN COALESCE(d.days_overdue, 0) > 120 THEN '120+'
                WHEN COALESCE(d.days_overdue, 0) > 90 THEN '91-120'
                WHEN COALESCE(d.days_overdue, 0) > 60 THEN '61-90'
                WHEN COALESCE(d.days_overdue, 0) > 30 THEN '31-60'
                ELSE '0-30'
            END as aging_bucket
        FROM `tabSACCO Loan` l
        LEFT JOIN `tabSACCO Defaulter` d ON d.loan = l.name
        WHERE l.status IN ('Active', 'Defaulted')
    """
    
    if bucket:
        query += f" HAVING aging_bucket = '{bucket}'"
        
    records = frappe.db.sql(query, as_dict=True)
    return {"status": "success", "data": records}

@frappe.whitelist(allow_guest=True)
def get_loan_performance_report():
    # Summary of loan counts by status
    stats = frappe.db.sql("""
        SELECT status, COUNT(*) as count, SUM(loan_amount) as total_amount
        FROM `tabSACCO Loan`
        GROUP BY status
    """, as_dict=True)
    return {"status": "success", "data": stats}

@frappe.whitelist(allow_guest=True)
def get_interest_collection_report(loan_product=None, from_date=None, to_date=None):
    # This queries the SACCO Interest Income account entries
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    income_account = frappe.db.get_value("Account", {"account_name": "SACCO Interest Income", "company": company})
    
    if not income_account:
        return {"status": "error", "message": "Interest Income account not found."}
        
    query = """
        SELECT 
            SUM(credit) as total_interest
        FROM `tabGL Entry`
        WHERE account = %s AND company = %s AND is_cancelled = 0
    """
    params = [income_account, company]
    
    if from_date and to_date:
        query += " AND posting_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])
        
    # Optional logic: if we want to filter by loan product, we'd need to join with Journal Entry Remarks or similar
    # or have a link in GL Entry. Since we put loan ID in remark, we can use that.
    
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return {"status": "success", "total_collected": data[0].get("total_interest", 0) if data else 0}

@frappe.whitelist(allow_guest=True)
def get_auth_logs(user=None, from_date=None, to_date=None):
    filters = {}
    if user:
        filters["user"] = user
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]
        
    logs = frappe.db.get_all("Authentication Log", 
        fields=["name", "user", "operation", "status", "ip_address", "creation"],
        filters=filters,
        order_by="creation desc",
        limit=100
    )
    return {"status": "success", "data": logs}

@frappe.whitelist(allow_guest=True)
def get_document_history(doctype, docname):
    """
    Returns the audit trail (version history) for a specific document.
    """
    versions = frappe.db.get_all("Version",
        fields=["name", "owner", "creation", "data"],
        filters={
            "ref_doctype": doctype,
            "docname": docname
        },
        order_by="creation desc"
    )
    
    # Process data field (Frappe stores diffs in 'data')
    import json
    for v in versions:
        if v.data:
            try:
                v.data = json.loads(v.data)
            except:
                pass
                
    return {"status": "success", "data": versions}

@frappe.whitelist(allow_guest=True)
def get_all_audit_trails(doctypes=None, from_date=None, to_date=None, limit=50):
    """
    Returns global audit logs (versions) across critical DocTypes.
    """
    if not doctypes:
        doctypes = ["SACCO Member", "SACCO Loan", "SACCO Savings", "SACCO Loan Product"]
    
    import json
    if isinstance(doctypes, str):
        try:
            doctypes = json.loads(doctypes)
        except:
            doctypes = [doctypes]

    filters = {"ref_doctype": ["in", doctypes]}
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]
        
    versions = frappe.db.get_all("Version",
        fields=["name", "ref_doctype", "docname", "owner", "creation", "data"],
        filters=filters,
        order_by="creation desc",
        limit=limit
    )
    
    # Process diff data
    for v in versions:
        if v.data:
            try:
                v.data = json.loads(v.data)
            except:
                pass
                
    return {"status": "success", "data": versions}

# --- Welfare Management ---

@frappe.whitelist(allow_guest=True)
def record_welfare_contribution(member, amount, purpose="Monthly Contribution", type="Contribution"):
    doc = frappe.get_doc({
        "doctype": "SACCO Welfare",
        "member": member,
        "contribution_amount": amount,
        "purpose": purpose,
        "type": type,
        "posting_date": frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"status": "success", "message": "Welfare transaction recorded.", "id": doc.name}

@frappe.whitelist(allow_guest=True)
def get_member_welfare_history(member):
    history = frappe.db.get_all("SACCO Welfare",
        filters={"member": member, "docstatus": 1},
        fields=["name", "posting_date", "contribution_amount", "purpose", "type"],
        order_by="posting_date desc"
    )
    return {"status": "success", "data": history}

@frappe.whitelist(allow_guest=True)
def get_all_welfare_contributions(from_date=None, to_date=None):
    filters = {"docstatus": 1}
    if from_date and to_date:
        filters["posting_date"] = ["between", [from_date, to_date]]
        
    data = frappe.db.get_all("SACCO Welfare",
        filters=filters,
        fields=["name", "member", "contribution_amount", "posting_date", "purpose", "type"],
        order_by="posting_date desc"
    )
    return {"status": "success", "data": data}

@frappe.whitelist(allow_guest=True)
def get_member_loans(member):
    """
    Returns all loans for a specific member, including parsed repayment schedules.
    """
    loans = frappe.db.get_all("SACCO Loan",
        filters={"member": member},
        fields=["name", "loan_product", "loan_amount", "interest_rate", "repayment_period", "status", "total_repayable", "outstanding_balance", "repayment_schedule", "creation"],
        order_by="creation desc"
    )
    
    import json
    for loan in loans:
        if loan.repayment_schedule:
            try:
                loan.repayment_schedule = json.loads(loan.repayment_schedule)
            except:
                loan.repayment_schedule = []
                
    return {"status": "success", "data": loans}

@frappe.whitelist(allow_guest=True)
def get_current_user():
    """
    Returns information about the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        return {"status": "success", "user": "Guest", "authenticated": False}

    user_doc = frappe.get_doc("User", user)
    
    # Check if a SACCO Member is linked to this user
    member_id = frappe.db.get_value("SACCO Member", {"user": user}, "name")
    
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    return {
        "status": "success",
        "authenticated": True,
        "user_id": user,
        "full_name": user_doc.full_name,
        "roles": [r.role for r in user_doc.roles],
        "member_id": member_id,
        "company": company,
        "permissions": get_user_doctype_permissions(user)
    }

def get_user_doctype_permissions(user):
    """
    Helper to get simplified permission mapping for SACCO DocTypes.
    """
    sacco_doctypes = [
        "SACCO Member", "SACCO Loan", "SACCO Loan Repayment", 
        "SACCO Savings", "SACCO Welfare", "SACCO Loan Product",
        "SACCO Defaulter", "SACCO Guarantor"
    ]
    
    perms_map = {}
    for dt in sacco_doctypes:
        perms_map[dt] = {
            "read": frappe.has_permission(dt, "read", user=user),
            "write": frappe.has_permission(dt, "write", user=user),
            "create": frappe.has_permission(dt, "create", user=user),
            "delete": frappe.has_permission(dt, "delete", user=user),
            "submit": frappe.has_permission(dt, "submit", user=user),
            "cancel": frappe.has_permission(dt, "cancel", user=user),
            "amend": frappe.has_permission(dt, "amend", user=user),
            "report": frappe.has_permission(dt, "report", user=user),
            "export": frappe.has_permission(dt, "export", user=user),
            "import": frappe.has_permission(dt, "import", user=user),
            "share": frappe.has_permission(dt, "share", user=user),
            "print": frappe.has_permission(dt, "print", user=user),
            "email": frappe.has_permission(dt, "email", user=user)
        }
    return perms_map

@frappe.whitelist(allow_guest=True)
def check_user_exists(email):
    """
    Checks if a user with the given email exists in the system.
    """
    exists = frappe.db.exists("User", email)
    if exists:
        send_otp(email)
        return {"status": "success", "exists": True, "message": "User exists. OTP sent to your email."}
    
    return {"status": "success", "exists": False, "message": "User not found."}

@frappe.whitelist(allow_guest=True)
def send_otp(email):
    """
    Generates a 6-digit OTP, stores it in cache, and sends it to the user.
    """
    if not frappe.db.exists("User", email):
        return {"status": "error", "message": "User not found"}

    import random
    otp = str(random.randint(100000, 999999))
    
    # Store OTP in cache for 10 minutes
    frappe.cache().set_value(f"otp_{email}", otp, expires_in_sec=600)
    
    # Send via email
    subject = _("Your SACCO Verification Code")
    message = f"""
    <p>Your verification code is: <strong style="font-size: 1.2em;">{otp}</strong></p>
    <p>This code will expire in 10 minutes.</p>
    """
    
    # Use existing notification helper if possible or send_mail directly
    from sacc_app.notify import send_member_email
    member_id = frappe.db.get_value("SACCO Member", {"email": email}, "name")
    
    if member_id:
        send_member_email(member_id, subject, message)
    else:
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            delayed=False
        )
        
    return {"status": "success", "message": "OTP sent to your email"}

@frappe.whitelist(allow_guest=True)
def verify_otp(email, otp):
    """
    Verifies if the provided OTP is valid.
    """
    cached_otp = frappe.cache().get_value(f"otp_{email}")
    if not cached_otp:
        return {"status": "error", "message": "OTP expired or not found"}
    
    if str(cached_otp) == str(otp):
        return {"status": "success", "message": "OTP verified successfully"}
    else:
        return {"status": "error", "message": "Invalid OTP"}

@frappe.whitelist(allow_guest=True)
def reset_password(email, otp, new_password):
    """
    Resets the user's password if the OTP is valid.
    """
    # Verify OTP first
    verification = verify_otp(email, otp)
    if verification.get("status") != "success":
        return verification

    if not frappe.db.exists("User", email):
        return {"status": "error", "message": "User not found"}

    user = frappe.get_doc("User", email)
    user.new_password = new_password
    user.save(ignore_permissions=True)
    
    # Clear OTP from cache after successful reset
    frappe.cache().delete_value(f"otp_{email}")
    
    return {"status": "success", "message": "Password updated successfully"}

@frappe.whitelist(allow_guest=True)
def get_sacco_settings():
    """
    Returns the current SACCO Settings.
    """
    settings = frappe.get_single("SACCO Settings")
    return {
        "status": "success",
        "data": settings.as_dict()
    }

@frappe.whitelist(allow_guest=True)
def update_sacco_settings(data=None, **kwargs):
    """
    Updates the SACCO Settings. Performs a 'Create' effectively if it's the first time,
    though 'Single' DocTypes always exist in Frappe.
    """
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    settings = frappe.get_doc("SACCO Settings")
    settings.update(data)
    settings.save(ignore_permissions=True)
    
    return {"status": "success", "message": "SACCO Settings updated successfully", "data": settings.as_dict()}

@frappe.whitelist(allow_guest=True)
def delete_sacco_settings():
    """
    Resets SACCO Settings to default/null values.
    Since Single DocTypes cannot be 'deleted' in the traditional sense, we clear the fields.
    """
    settings = frappe.get_doc("SACCO Settings")
    
    # Get all fields from the DocType and reset them
    meta = frappe.get_meta("SACCO Settings")
    for field in meta.fields:
        if field.fieldname:
            settings.set(field.fieldname, None)
            
    settings.save(ignore_permissions=True)
    return {"status": "success", "message": "SACCO Settings have been reset to defaults."}



