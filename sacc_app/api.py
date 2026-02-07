import frappe
import random
import string
from frappe import _
from frappe.utils import flt
from sacc_app.swagger_spec import get_swagger_spec
import sacc_app.budget_api # Expose budget APIs


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
	member = frappe.db.get_value("SACCO Member", {"email": user}, 
        ["name", "member_name", "total_savings", "total_loan_outstanding", "active_loan", "status", "registration_fee_paid", "loan_eligible"], 
        as_dict=1)
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
    repayment_period = data.get("repayment_period")
    
    # 1. Fetch Loan Product Settings
    product = frappe.get_doc("SACCO Loan Product", product_name)
    
    # Validate Repayment Period
    if repayment_period:
        repayment_period = int(repayment_period)
        if product.max_repayment_period > 0 and repayment_period > product.max_repayment_period:
            return {"status": "error", "message": f"Repayment period exceeds maximum allowed ({product.max_repayment_period} months) for this product."}
    else:
        repayment_period = product.max_repayment_period

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
        "repayment_period": repayment_period,
        "purpose": data.get("purpose"),
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
    products = frappe.db.get_all("SACCO Loan Product", 
        fields=["name", "product_name", "interest_rate", "interest_period", "interest_method", "max_repayment_period", "min_loan_amount", "max_loan_amount", "requires_guarantor", "min_guarantors", "description"])
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

@frappe.whitelist(allow_guest=True)
def get_all_roles():
    """
    Returns all roles, excluding standard Frappe system roles.
    Includes System Manager and all SACCO-related roles.
    """
    # Get all roles
    all_roles = frappe.db.get_all("Role", fields=["name", "role_name", "desk_access"])
    
    # Standard Frappe roles to exclude
    frappe_system_roles = [
        "Guest", "Administrator", "All", "Blogger", "Customer", "Employee", 
        "Employee Self Service", "HR Manager", "HR User", "Knowledge Base Contributor",
        "Knowledge Base Editor", "Newsletter Manager", "Projects Manager", "Projects User",
        "Purchase Manager", "Purchase Master Manager", "Purchase User", "Quality Manager",
        "Sales Manager", "Sales Master Manager", "Sales User", "Stock Manager", "Stock User",
        "Supplier", "Website Manager", "Accounts Manager", "Accounts User", "Analytics",
        "Auditor", "Expense Approver", "Fleet Manager", "Fulfillment User", "Item Manager",
        "Maintenance Manager", "Maintenance User", "Manufacturing Manager", "Manufacturing User",
        "Material Manager", "Material Master Manager", "Material User", "Report Manager",
        "Script Manager", "Support Team", "Translator", "Workspace Manager"
    ]
    
    # Filter roles: keep System Manager and exclude standard Frappe roles
    filtered_roles = [
        role for role in all_roles 
        if role.get("name") == "System Manager" or role.get("name") not in frappe_system_roles
    ]
    
    return {"status": "success", "data": filtered_roles}

@frappe.whitelist(allow_guest=True)
def get_all_users():
    """
    Returns all system users with their details.
    Excludes users who only have the 'SACCO Member' role.
    """
    users = frappe.db.get_all("User", 
        filters={"name": ["not in", ["Administrator", "Guest"]]},
        fields=["name", "email", "first_name", "last_name", "full_name", "enabled", "user_type", "creation"],
        order_by="creation desc"
    )
    
    filtered_users = []
    
    # Get roles for each user and filter out SACCO Member-only users
    for user in users:
        user_roles = frappe.db.get_all("Has Role",
            filters={"parent": user.get("name")},
            fields=["role"],
            pluck="role"
        )
        user["roles"] = user_roles
        
        # Exclude users who only have "SACCO Member" role
        # Keep users who have other roles (even if they also have SACCO Member)
        if user_roles and not (len(user_roles) == 1 and user_roles[0] == "SACCO Member"):
            filtered_users.append(user)
    
    return {"status": "success", "data": filtered_users}

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

@frappe.whitelist(allow_guest=True)
def update_account(account_name, data=None, **kwargs):
    if not data:
        data = kwargs
    if isinstance(data, str):
        import json
        data = json.loads(data)
        
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # account_name passed might be the ID or the name. 
    # Usually in Frappe, Account ID is "Name - Company".
    # We should support finding it.
    
    account_id = None
    if frappe.db.exists("Account", account_name):
        account_id = account_name
    elif frappe.db.exists("Account", {"account_name": account_name, "company": company}):
        account_id = frappe.db.get_value("Account", {"account_name": account_name, "company": company}, "name")
        
    if not account_id:
         return {"status": "error", "message": f"Account '{account_name}' not found."}
         
    doc = frappe.get_doc("Account", account_id)
    
    # Update fields
    if "parent_account" in data:
        new_parent = data.get("parent_account")
        # Validate parent
        parent_exists = frappe.db.exists("Account", {"account_name": new_parent, "company": company}) or frappe.db.exists("Account", new_parent)
        if not parent_exists:
             return {"status": "error", "message": f"Parent account '{new_parent}' not found."}
        
        # Resolve parent ID if name given
        if not frappe.db.exists("Account", new_parent):
            new_parent = frappe.db.get_value("Account", {"account_name": new_parent, "company": company}, "name")
            
        doc.parent_account = new_parent
        
    if "account_type" in data:
        doc.account_type = data.get("account_type")
        
    if "account_name" in data:
        doc.account_name = data.get("account_name")
        
    if "is_group" in data:
        doc.is_group = int(data.get("is_group"))

    doc.save(ignore_permissions=True)
    return {"status": "success", "message": f"Account '{account_name}' updated.", "data": doc.as_dict()}

@frappe.whitelist(allow_guest=True)
def delete_account(account_name):
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    account_id = None
    if frappe.db.exists("Account", account_name):
        account_id = account_name
    elif frappe.db.exists("Account", {"account_name": account_name, "company": company}):
        account_id = frappe.db.get_value("Account", {"account_name": account_name, "company": company}, "name")
        
    if not account_id:
         return {"status": "error", "message": f"Account '{account_name}' not found."}
         
    # Check for balance? Frappe delete logic usually handles validation but we can be safe.
    from erpnext.accounts.utils import get_balance_on
    balance = get_balance_on(account_id)
    if balance != 0:
        return {"status": "error", "message": f"Cannot delete account with non-zero balance: {balance}"}
        
    try:
        frappe.delete_doc("Account", account_id)
        return {"status": "success", "message": f"Account '{account_name}' deleted."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest= True  )
def record_expense(amount, expense_account, description, mode_of_payment="Cash", vendor_name=None):
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
    
    remark = f"{vendor_name}: {description}" if vendor_name else description
    je.user_remark = remark
    
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
def record_savings_deposit(member, amount, mode="Cash", reference=None, posting_date=None):
    doc = frappe.get_doc({
        "doctype": "SACCO Savings",
        "member": member,
        "type": "Deposit",
        "amount": amount,
        "payment_mode": mode,
        "reference_number": reference or "",
        "posting_date": posting_date or frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()

    if posting_date:
        # Update creation date via SQL
        frappe.db.sql("UPDATE `tabSACCO Savings` SET creation = %s WHERE name = %s", (posting_date, doc.name))

    return {"status": "success", "message": "Savings deposit recorded.", "id": doc.name}

@frappe.whitelist(allow_guest= True  )
def record_savings_withdrawal(member, amount, mode="Cash", reference=None, posting_date=None):
    doc = frappe.get_doc({
        "doctype": "SACCO Savings",
        "member": member,
        "type": "Withdrawal",
        "amount": amount,
        "payment_mode": mode,
        "reference_number": reference or "",
        "posting_date": posting_date or frappe.utils.nowdate()
    })
    doc.insert(ignore_permissions=True)
    doc.submit()

    if posting_date:
        # Update creation date via SQL
        frappe.db.sql("UPDATE `tabSACCO Savings` SET creation = %s WHERE name = %s", (posting_date, doc.name))

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
def pay_registration_fee(member, amount=None, mode="Cash", reference=None, posting_date=None):
    member_doc = frappe.get_doc("SACCO Member", member)
    
    # Prevent active members from paying registration fee
    if member_doc.status == "Active" or member_doc.registration_fee_paid == 1:
        frappe.throw(
            "Cannot pay registration fee. This member has already paid the registration fee and is active.",
            title="Registration Fee Already Paid"
        )
    
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
        "reference_date": posting_date or frappe.utils.nowdate(),
        "mode_of_payment": mode,
        "posting_date": posting_date or frappe.utils.nowdate(),
        "paid_to": frappe.db.get_value("Account", {"account_type": "Cash", "company": frappe.defaults.get_user_default("Company")}, "name") 
    })
    pe.append("references", {
        "reference_doctype": "Sales Invoice",
        "reference_name": inv_name,
        "allocated_amount": amount
    })
    pe.insert(ignore_permissions=True)
    pe.submit()
    
    if posting_date:
        # Backdate the invoice and payment via SQL
        frappe.db.sql("UPDATE `tabSales Invoice` SET creation = %s, posting_date = %s WHERE name = %s", (posting_date, posting_date, inv_name))
        frappe.db.sql("UPDATE `tabPayment Entry` SET creation = %s WHERE name = %s", (posting_date, pe.name))

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
    # Fetch actual products from DB
    products = frappe.db.get_all("SACCO Loan Product", 
        fields=["name as type", "interest_rate", "max_repayment_period as max_period", "description"])
    
    for p in products:
        p["interest"] = f"{p.interest_rate}%"
        # Optional: format max_period for UI
        if p.max_period:
            p["max_period"] = f"{p.max_period} Months"
        else:
            p["max_period"] = "Dependent on Amount"

    return {
        "status": "success",
        "products": products
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
def get_all_accounts():
    return get_all_accounts_with_balances()

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
    
    enabled = 1 if str(status).lower() in ["1", "active", "true", "enabled"] else 0
    frappe.db.set_value("User", user_id, "enabled", enabled)
    
    status_text = "Enabled" if enabled else "Disabled"
    return {"status": "success", "message": f"User {user_id} has been {status_text}."}

# --- Core Financial Reports ---

def get_report_dates(from_date=None, to_date=None):
    from erpnext.accounts.utils import get_fiscal_year
    from frappe.utils import nowdate, getdate
    
    if not to_date:
        to_date = nowdate()
    
    to_date = getdate(to_date)
    
    if not from_date:
        try:
            fiscal_year = get_fiscal_year(to_date)
            from_date = fiscal_year[1]
        except:
            from_date = f"{to_date.year}-01-01"
            
    return getdate(from_date), to_date

@frappe.whitelist(allow_guest=True)
def get_profit_and_loss(from_date=None, to_date=None):
    from_date, to_date = get_report_dates(from_date, to_date)
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "period_start_date": from_date,
        "period_end_date": to_date,
        "filter_based_on": "Date Range",
        "periodicity": "Monthly",
        "accumulated_values": 1
    }
    from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute
    columns, data, message, chart, report_summary, primitive_summary = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data, "report_summary": report_summary}

@frappe.whitelist(allow_guest=True)
def get_balance_sheet(to_date=None):
    if not to_date:
        to_date = frappe.utils.nowdate()
        
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    from_date, to_date_obj = get_report_dates(to_date=to_date)
    
    filters = {
        "company": company,
        "period_start_date": from_date,
        "period_end_date": to_date_obj,
        "to_date": to_date_obj,
        "filter_based_on": "Date Range",
        "periodicity": "Monthly",
        "accumulated_values": 1
    }
    from erpnext.accounts.report.balance_sheet.balance_sheet import execute
    columns, data, message, chart, report_summary, primitive_summary = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data, "report_summary": report_summary}

@frappe.whitelist(allow_guest=True)
def get_trial_balance(from_date=None, to_date=None):
    from_date, to_date = get_report_dates(from_date, to_date)
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    from erpnext.accounts.utils import get_fiscal_year
    fiscal_year = get_fiscal_year(to_date)[0]
    
    filters = {
        "company": company,
        "fiscal_year": fiscal_year,
        "from_date": from_date,
        "to_date": to_date,
        "show_zero_values": 1
    }
    from erpnext.accounts.report.trial_balance.trial_balance import execute
    columns, data = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data}

@frappe.whitelist(allow_guest=True)
@frappe.whitelist(allow_guest=True)
def get_account_statement(account=None, member=None, from_date=None, to_date=None):
    from_date, to_date = get_report_dates(from_date, to_date)
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    target = account or member
    if not target:
         return {"status": "error", "message": "Please provide either 'account' or 'member'."}

    # Resolve account name if it's a SACCO Savings record, Member ID, or Loan ID
    real_account = target
    
    # Check if target is a valid Account ID first
    if not frappe.db.exists("Account", target):
        # 0. Check if it's an Account Name
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
        acc_by_name = frappe.db.get_value("Account", {"account_name": target, "company": company}, "name")
        if acc_by_name:
            real_account = acc_by_name
        else:
            # 1. Check if it's a member ID
            member_data = frappe.db.get_value("SACCO Member", target, ["savings_account", "ledger_account"], as_dict=1)
            if member_data:
                # Default to savings account if it's just a member ID
                real_account = member_data.savings_account
            else:
                # 2. Check if it's a SACCO Savings document name
                saved_member = frappe.db.get_value("SACCO Savings", target, "member")
                if saved_member:
                    real_account = frappe.db.get_value("SACCO Member", saved_member, "savings_account")
                else:
                    # 3. Check if it's a SACCO Loan document name
                    loan_member = frappe.db.get_value("SACCO Loan", target, "member")
                    if loan_member:
                        real_account = frappe.db.get_value("SACCO Member", loan_member, "ledger_account")

    if not real_account or not frappe.db.exists("Account", real_account):
        return {"status": "error", "message": f"Account {target} could not be resolved to a valid General Ledger account."}

    filters = {
        "company": company,
        "account": [real_account],
        "from_date": from_date,
        "to_date": to_date,
        "group_by": "Group by Voucher (Consolidated)"
    }
    from erpnext.accounts.report.general_ledger.general_ledger import execute
    columns, data = execute(frappe._dict(filters))
    return {"status": "success", "columns": columns, "data": data}

# --- Operational Reports ---

@frappe.whitelist(allow_guest=True)
def get_loan_repayment_summary(from_date=None, to_date=None):
    from_date, to_date = get_report_dates(from_date, to_date)
    filters = {}
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
    from_date, to_date = get_report_dates(from_date, to_date)
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
        AND posting_date BETWEEN %s AND %s
    """
    params = [income_account, company, from_date, to_date]
        
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
def record_welfare_contribution(member, amount, purpose="Monthly Contribution", type="Contribution", claim_id=None):
    doc = frappe.get_doc({
        "doctype": "SACCO Welfare",
        "member": member,
        "contribution_amount": amount,
        "purpose": purpose,
        "type": type,
        "posting_date": frappe.utils.nowdate()
    })
    
    if claim_id:
        if frappe.db.exists("SACCO Welfare Claim", claim_id):
             doc.welfare_claim = claim_id
        else:
             frappe.throw(f"Welfare Claim {claim_id} not found")

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
def get_loan_application_by_id(loan_id):
    """
    Returns a single loan application by its ID, with repayment schedule parsed.
    """
    if not frappe.db.exists("SACCO Loan", loan_id):
        return {"status": "error", "message": f"Loan {loan_id} not found."}

    loan = frappe.db.get_value("SACCO Loan", loan_id, 
        ["name", "member", "loan_product", "loan_amount", "interest_rate", "repayment_period", "status", "total_repayable", "outstanding_balance", "repayment_schedule", "creation"],
        as_dict=True
    )
    
    if loan:
        loan["member_id"] = loan.member
        member_data = frappe.db.get_value("SACCO Member", loan.member, ["member_name", "first_name", "last_name"], as_dict=1)
        if member_data:
            loan["member_name"] = member_data.member_name
            loan["first_name"] = member_data.first_name
            loan["last_name"] = member_data.last_name
    
    import json
    if loan.repayment_schedule:
        try:
            loan.repayment_schedule = json.loads(loan.repayment_schedule)
        except:
            loan.repayment_schedule = []
    else:
        loan.repayment_schedule = []
                
    return {"status": "success", "data": loan}

@frappe.whitelist(allow_guest=True)
def generate_loan_ready_member(savings_amount=100000, registration_date=None):
    """
    Generates a test member who is ready to apply for a loan.
    1. Creates Member
    2. Pays Registration Fee
    3. Deposits Savings
    """
    # 0. Ensure Registration Fee logic is active
    settings = frappe.get_doc("SACCO Settings")
    
    dirty = False
    if not settings.charge_registration_fee_on_onboarding:
        settings.charge_registration_fee_on_onboarding = 1
        dirty = True
        
    if not settings.registration_fee or flt(settings.registration_fee) <= 0:
        settings.registration_fee = 500
        dirty = True
        
    if dirty:
        settings.save(ignore_permissions=True)
        
    # 1. Generate Random Details
    suffix = "".join(random.choices(string.digits, k=4))
    first_name = f"TestMember"
    last_name = f"User{suffix}"
    email = f"test.user.{suffix}@example.com"
    phone = f"07{suffix}{suffix}0"
    national_id = f"ID{suffix}{suffix}"
    
    # 2. Create Member
    member_res = create_member_application({
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "national_id": national_id,
        "county": "Nairobi",
        "sub_county": "Westlands", 
        "ward": "Kitisuru",
        "village": "Test Village"
    })
    
    if member_res.get("status") != "success":
        return member_res
        
    member_id = member_res.get("member_id")

    if registration_date:
        # Backdate member creation via SQL
        frappe.db.sql("UPDATE `tabSACCO Member` SET creation = %s WHERE name = %s", (registration_date, member_id))
    
    # 3. Pay Registration Fee
    fee_amount = settings.registration_fee or 500
    
    # Check if invoice exists (it should if setting was on)
    # If not, maybe create_member_application didn't trigger it immediately? 
    # It runs on hooks or after_insert? assuming it worked since setting is now on.
    
    pay_res = pay_registration_fee(member_id, amount=fee_amount, mode="Cash", reference=f"REG-{suffix}", posting_date=registration_date)
    if pay_res.get("status") != "success":
        return {"status": "error", "message": f"Failed to pay reg fee: {pay_res.get('message')}"}
        
    # 4. Deposit Savings (Divided into 3 monthly installments if backdated)
    monthly_installment = flt(savings_amount) / 3.0
    
    for i in range(3):
        # Calculate date for each installment
        if registration_date:
            curr_date = frappe.utils.add_months(registration_date, i)
        else:
            curr_date = frappe.utils.nowdate()
            
        savings_res = record_savings_deposit(
            member_id, 
            amount=monthly_installment, 
            mode="Cash", 
            reference=f"DEP-{suffix}-{i+1}", 
            posting_date=curr_date
        )
        if savings_res.get("status") != "success":
             return {"status": "error", "message": f"Failed to deposit savings installment {i+1}: {savings_res.get('message')}"}
    
    # Check if we should set loan_eligible
    if registration_date:
        today = frappe.utils.now_datetime().date()
        date_obj = frappe.utils.getdate(registration_date)
        # If backdated 3 months or more
        if frappe.utils.date_diff(today, date_obj) >= 90:
            frappe.db.set_value("SACCO Member", member_id, "loan_eligible", 1)
            # Update local list if needed, but it's already in DB.
            
    # Fetch final details to ensure balances are included
    final_member = frappe.db.get_value("SACCO Member", member_id, ["total_savings", "total_loan_outstanding"], as_dict=1)
            
    return {
        "status": "success",
        "message": "Loan-ready member generated successfully.",
        "data": {
            "member_id": member_id,
            "name": f"{first_name} {last_name}",
            "email": email,
            "national_id": national_id,
            "total_savings": flt(final_member.total_savings),
            "total_loan_outstanding": flt(final_member.total_loan_outstanding),
            "status": "Active"
        }
    }

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
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    company_name = frappe.db.get_value("Company", company, "company_name") or company or "SACCO"

    subject = _("Your {0} Verification Code").format(company_name)
    message = f"""
    <p>Your verification code is: <strong style="font-size: 1.2em; color: #1a73e8;">{otp}</strong></p>
    <p>This code will expire in 10 minutes.</p>
    <p>If you did not request this code, please ignore this email.</p>
    """
    
    # Use standardized notification helper
    from sacc_app.notify import send_member_email
    send_member_email(email, subject, message)
        
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
def get_company_details():
    """
    Returns details of the default company.
    """
    company_name = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    if not company_name:
        return {"status": "error", "message": "No default company set."}
        
    company = frappe.get_doc("Company", company_name)
    
    return {
        "status": "success",
        "data": {
            "name": company.name,
            "company_name": company.company_name,
            "abbr": company.abbr,
            "default_currency": company.default_currency,
            "country": company.country,
            "tax_id": company.tax_id,
            "domain": company.domain,
            "phone_no": company.phone_no,
            "email": company.email,
            "logo": company.company_logo
        }
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


@frappe.whitelist(allow_guest=True)
def get_loan_ledger_report(date_from=None, date_to=None, member=None, loan_id=None, limit_start=0, limit_page_length=100):
    """
    Returns loan ledger report with GL Entry transactions.
    Filters: date_from, date_to, member, loan_id
    Shows running balance for loan accounts.
    """
    from frappe.utils import flt
    
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    # Build filters
    filters = {
        "is_cancelled": 0
    }
    
    # Filter by member's loan ledger account
    if member:
        ledger_account = frappe.db.get_value("SACCO Member", member, "ledger_account")
        if ledger_account:
            filters["account"] = ledger_account
        else:
            return {"status": "error", "message": f"Member {member} has no loan ledger account"}
    else:
        # Get all loan ledger accounts (accounts under "SACCO Members Accounts")
        parent_account = frappe.db.get_value("Account", {"account_name": "SACCO Members Accounts"})
        if parent_account:
            loan_accounts = frappe.db.get_all("Account", 
                filters={"parent_account": parent_account},
                pluck="name"
            )
            if loan_accounts:
                filters["account"] = ["in", loan_accounts]
    
    # Filter by date range
    if date_from:
        filters["posting_date"] = [">=", date_from]
    if date_to:
        if "posting_date" in filters:
            filters["posting_date"] = ["between", [date_from, date_to]]
        else:
            filters["posting_date"] = ["<=", date_to]
    
    # Filter by loan_id (voucher_no for Journal Entry or against for Payment Entry)
    if loan_id:
        filters["voucher_no"] = ["like", f"%{loan_id}%"]
    
    # Get GL entries
    gl_entries = frappe.db.get_all("GL Entry",
        filters=filters,
        fields=["posting_date", "account", "debit", "credit", "voucher_type", "voucher_no", "against", "remarks", "party"],
        order_by="posting_date asc, creation asc",
        limit_start=limit_start,
        limit_page_length=limit_page_length
    )
    
    # Calculate running balance and enrich data
    running_balance = 0
    opening_balance = 0
    
    # Get opening balance if date_from is specified
    if date_from and filters.get("account"):
        account_filter = filters["account"]
        if isinstance(account_filter, list) and account_filter[0] == "in":
            # Multiple accounts - sum all
            for acc in account_filter[1]:
                opening_balance += flt(frappe.db.sql("""
                    SELECT sum(debit) - sum(credit)
                    FROM `tabGL Entry`
                    WHERE account = %s AND posting_date < %s AND is_cancelled = 0
                """, (acc, date_from))[0][0])
        else:
            # Single account
            opening_balance = flt(frappe.db.sql("""
                SELECT sum(debit) - sum(credit)
                FROM `tabGL Entry`
                WHERE account = %s AND posting_date < %s AND is_cancelled = 0
            """, (account_filter, date_from))[0][0])
    
    running_balance = opening_balance
    
    transactions = []
    total_debit = 0
    total_credit = 0
    
    for entry in gl_entries:
        # Get member info from account name
        member_id = entry.account.split(" - ")[0] if " - " in entry.account else None
        member_name = frappe.db.get_value("SACCO Member", member_id, "member_name") if member_id else None
        
        # Extract loan_id from voucher_no or against field
        loan_ref = entry.voucher_no if "LOAN" in (entry.voucher_no or "") else entry.against
        
        debit = flt(entry.debit)
        credit = flt(entry.credit)
        running_balance += debit - credit
        
        total_debit += debit
        total_credit += credit
        
        transactions.append({
            "date": str(entry.posting_date),
            "voucher_type": entry.voucher_type,
            "voucher_no": entry.voucher_no,
            "loan_id": loan_ref,
            "member": member_id,
            "member_name": member_name,
            "account": entry.account,
            "debit": debit,
            "credit": credit,
            "balance": running_balance,
            "remarks": entry.remarks
        })
    
    return {
        "status": "success",
        "data": {
            "transactions": transactions,
            "summary": {
                "opening_balance": opening_balance,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "closing_balance": running_balance
            },
            "count": len(transactions)
        }
    }


# --- Loan Dashboard APIs ---

@frappe.whitelist(allow_guest=True)
def get_loan_dashboard():
    """
    Returns loan dashboard statistics:
    - total_pending_applications: Count of loans with status 'Draft' or 'Pending Approval'
    - active_loans_count: Count of active loans
    - active_loans_amount: Total outstanding balance of active loans
    - total_disbursed_amount: Sum of all disbursed loan amounts
    - default_rate: Percentage of defaulted loans vs total loans
    """
    
    # Pending applications (Draft or Pending Approval)
    total_pending_applications = frappe.db.count("SACCO Loan", 
        filters={"status": ["in", ["Draft", "Pending Approval"]]}
    )
    
    # Active loans count and amount
    active_loans_stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as count,
            SUM(outstanding_balance) as total_outstanding
        FROM `tabSACCO Loan`
        WHERE status = 'Active'
    """, as_dict=True)
    
    active_loans_count = active_loans_stats[0].count if active_loans_stats else 0
    active_loans_amount = flt(active_loans_stats[0].total_outstanding) if active_loans_stats else 0.0
    
    # Total disbursed amount (all loans that have been disbursed)
    total_disbursed = frappe.db.sql("""
        SELECT SUM(loan_amount) as total
        FROM `tabSACCO Loan`
        WHERE status IN ('Active', 'Completed', 'Defaulted', 'Disbursed')
    """, as_dict=True)
    
    total_disbursed_amount = flt(total_disbursed[0].total) if total_disbursed and total_disbursed[0].total else 0.0
    
    # Default rate calculation
    loan_stats = frappe.db.sql("""
        SELECT 
            COUNT(CASE WHEN status = 'Defaulted' THEN 1 END) as defaulted_count,
            COUNT(*) as total_count
        FROM `tabSACCO Loan`
        WHERE status IN ('Active', 'Completed', 'Defaulted', 'Disbursed')
    """, as_dict=True)
    
    defaulted_count = loan_stats[0].defaulted_count if loan_stats else 0
    total_count = loan_stats[0].total_count if loan_stats else 0
    
    default_rate = 0.0
    if total_count > 0:
        default_rate = (flt(defaulted_count) / flt(total_count)) * 100.0
    
    return {
        "status": "success",
        "data": {
            "total_pending_applications": total_pending_applications,
            "active_loans_count": active_loans_count,
            "active_loans_amount": round(active_loans_amount, 2),
            "total_disbursed_amount": round(total_disbursed_amount, 2),
            "default_rate": round(default_rate, 2)
        }
    }


@frappe.whitelist(allow_guest=True)
def get_loan_applications(status=None, member_name=None, member_id=None, loan_id=None, 
                          limit_start=0, limit_page_length=20):
    """
    Returns detailed loan applications list with filters and pagination.
    
    Parameters:
    - status: Filter by loan status
    - member_name: Search by member name (partial match)
    - member_id: Filter by exact member ID
    - loan_id: Filter by exact loan ID
    - limit_start: Pagination offset (default: 0)
    - limit_page_length: Page size (default: 20)
    
    Returns:
    - member_name: Full name of member
    - member_id: Member ID
    - loan_id: Loan ID
    - amount_applied: Original loan amount
    - amount_disbursed: Same as amount_applied
    - interest_rate: Interest rate percentage
    - status: Current loan status
    - purpose: Loan purpose
    - payment_progress: Percentage of loan paid (0-100)
    - creation_date: When loan was created
    """
    
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    # Build WHERE clause based on filters
    conditions = []
    params = []
    
    if status:
        conditions.append("l.status = %s")
        params.append(status)
    
    if member_id:
        conditions.append("l.member = %s")
        params.append(member_id)
    
    if loan_id:
        conditions.append("l.name = %s")
        params.append(loan_id)
    
    if member_name:
        conditions.append("m.member_name LIKE %s")
        params.append(f"%{member_name}%")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    # Main query
    query = f"""
        SELECT 
            l.name as loan_id,
            l.member as member_id,
            COALESCE(m.member_name, l.member) as member_name,
            l.loan_amount as amount_applied,
            l.loan_amount as amount_disbursed,
            l.interest_rate,
            l.status,
            l.purpose,
            l.total_interest,
            l.principal_paid,
            l.interest_paid,
            l.creation as creation_date
        FROM `tabSACCO Loan` l
        LEFT JOIN `tabSACCO Member` m ON l.member = m.name
        {where_clause}
        ORDER BY l.creation DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([limit_page_length, limit_start])
    
    loans = frappe.db.sql(query, tuple(params), as_dict=True)
    
    # Calculate payment progress for each loan
    results = []
    for loan in loans:
        # Calculate total repayable
        total_repayable = flt(loan.amount_applied) + flt(loan.total_interest)
        
        # Calculate total paid
        total_paid = flt(loan.principal_paid) + flt(loan.interest_paid)
        
        # Calculate payment progress percentage
        payment_progress = 0.0
        if total_repayable > 0:
            payment_progress = (total_paid / total_repayable) * 100.0
        
        results.append({
            "member_name": loan.member_name or "",
            "member_id": loan.member_id,
            "loan_id": loan.loan_id,
            "amount_applied": round(flt(loan.amount_applied), 2),
            "amount_disbursed": round(flt(loan.amount_disbursed), 2),
            "interest_rate": flt(loan.interest_rate),
            "status": loan.status,
            "purpose": loan.purpose or "",
            "payment_progress": round(payment_progress, 2),
            "creation_date": str(loan.creation_date) if loan.creation_date else ""
        })
    
    # Get total count for pagination info
    count_query = f"""
        SELECT COUNT(*) as total
        FROM `tabSACCO Loan` l
        LEFT JOIN `tabSACCO Member` m ON l.member = m.name
        {where_clause}
    """
    
    # Remove the limit/offset params for count query
    count_params = params[:-2] if params else []
    total_count = frappe.db.sql(count_query, tuple(count_params), as_dict=True)
    total = total_count[0].total if total_count else 0
    
    return {
        "status": "success",
        "data": results,
        "pagination": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "total": total
        }
    }


@frappe.whitelist(allow_guest=True)
def get_savings_dashboard():
    """
    Returns savings dashboard statistics:
    - total_savings: Sum of all member savings
    - monthly_deposits: Sum of deposits in the current month
    - monthly_withdrawals: Sum of withdrawals in the current month
    - active_savers_count: Number of members with total_savings > 0
    """
    # Total Savings across all members
    total_savings = frappe.db.get_value("SACCO Member", filters={}, fieldname="SUM(total_savings)") or 0.0
    
    # Active Savers (members with total_savings > 0)
    active_savers = frappe.db.count("SACCO Member", filters={"total_savings": [">", 0]})
    
    # Current month data
    from frappe.utils import now_datetime, get_first_day, get_last_day
    today = now_datetime().date()
    month_start = get_first_day(today)
    month_end = get_last_day(today)
    
    # Monthly Deposits
    monthly_deposits = frappe.db.get_value("SACCO Savings", 
        filters={"type": "Deposit", "posting_date": ["between", [month_start, month_end]], "docstatus": 1}, 
        fieldname="SUM(amount)") or 0.0
        
    # Monthly Withdrawals
    monthly_withdrawals = frappe.db.get_value("SACCO Savings", 
        filters={"type": "Withdrawal", "posting_date": ["between", [month_start, month_end]], "docstatus": 1}, 
        fieldname="SUM(amount)") or 0.0
        
    return {
        "status": "success",
        "data": {
            "total_savings": round(flt(total_savings), 2),
            "monthly_deposits": round(flt(monthly_deposits), 2),
            "monthly_withdrawals": round(flt(monthly_withdrawals), 2),
            "active_savers_count": active_savers
        }
    }


@frappe.whitelist(allow_guest=True)
def get_savings_vs_expense():
    """
    Returns monthly savings vs expense comparison for the last 6 months.
    """
    from frappe.utils import add_months, getdate, formatdate, get_first_day, get_last_day
    
    data = []
    today = getdate()
    
    for i in range(5, -1, -1):
        month_pivot = add_months(today, -i)
        month_start = get_first_day(month_pivot)
        month_end = get_last_day(month_pivot)
        
        month_label = formatdate(month_pivot, "MMM YYYY")
        
        # Total Savings (Deposits) for the month
        savings = frappe.db.get_value("SACCO Savings", 
            filters={
                "type": "Deposit", 
                "posting_date": ["between", [month_start, month_end]], 
                "docstatus": 1
            }, 
            fieldname="SUM(amount)") or 0.0
            
        # Total Expense for the month (Journal Entries to Expense accounts)
        expense = frappe.db.sql("""
            SELECT SUM(jea.debit) as total
            FROM `tabJournal Entry Account` jea
            JOIN `tabJournal Entry` je ON jea.parent = je.name
            JOIN `tabAccount` acc ON jea.account = acc.name
            WHERE acc.root_type = 'Expense' 
              AND je.posting_date BETWEEN %s AND %s
              AND je.docstatus = 1
        """, (month_start, month_end), as_dict=True)[0].total or 0.0
        
        data.append({
            "month": month_label,
            "savings": round(flt(savings), 2),
            "expense": round(flt(expense), 2)
        })
        
    return {"status": "success", "data": data}


@frappe.whitelist(allow_guest=True)
def get_top_savers():
    """
    Returns top 5 members by total savings.
    Includes:
    - member_name: Full name
    - current_month_savings: Sum of deposits in current month
    - total_savings: Lifetime savings
    """
    members = frappe.db.get_all("SACCO Member", 
        fields=["name", "member_name", "total_savings"], 
        order_by="total_savings desc", 
        limit=5)
    
    from frappe.utils import now_datetime, get_first_day, get_last_day
    today = now_datetime().date()
    month_start = get_first_day(today)
    month_end = get_last_day(today)
    
    for m in members:
        # Savings this month for this member
        current_month = frappe.db.get_value("SACCO Savings", 
            filters={
                "member": m.name, 
                "type": "Deposit", 
                "posting_date": ["between", [month_start, month_end]], 
                "docstatus": 1
            }, 
            fieldname="SUM(amount)") or 0.0
        m.current_month_savings = round(flt(current_month), 2)
        m.total_savings = round(flt(m.total_savings), 2)
        
    return {"status": "success", "data": members}


@frappe.whitelist(allow_guest=True)
def get_savings_transactions(limit_start=0, limit_page_length=20, member=None, type=None, date_from=None, date_to=None, searchTerm=None):
    """
    Returns a list of savings/withdrawal transactions with filtering and pagination.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    conditions = ["docstatus = 1"]
    params = []
    
    if member:
        conditions.append("member = %s")
        params.append(member)
    if type:
        conditions.append("type = %s")
        params.append(type)
    if date_from and date_to:
        conditions.append("posting_date BETWEEN %s AND %s")
        params.extend([date_from, date_to])
    elif date_from:
        conditions.append("posting_date >= %s")
        params.append(date_from)
    elif date_to:
        conditions.append("posting_date <= %s")
        params.append(date_to)
        
    if searchTerm:
        # Search in name and reference_number
        conditions.append("(name LIKE %s OR reference_number LIKE %s OR member IN (SELECT name FROM `tabSACCO Member` WHERE member_name LIKE %s))")
        search_val = f"%{searchTerm}%"
        params.extend([search_val, search_val, search_val])
        
    where_clause = "WHERE " + " AND ".join(conditions)
    
    query = f"""
        SELECT 
            name, member, type, amount, posting_date, payment_mode, reference_number
        FROM `tabSACCO Savings`
        {where_clause}
        ORDER BY posting_date DESC, creation DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([limit_page_length, limit_start])
    
    transactions = frappe.db.sql(query, tuple(params), as_dict=True)
    
    results = []
    for t in transactions:
        t.member_name = frappe.db.get_value("SACCO Member", t.member, "member_name")
        results.append(t)
        
    count_query = f"SELECT COUNT(*) as total FROM `tabSACCO Savings` {where_clause}"
    count_params = params[:-2]
    total_count = frappe.db.sql(count_query, tuple(count_params), as_dict=True)
    total = total_count[0].total if total_count else 0
    
    return {
        "status": "success",
        "data": results,
        "pagination": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "total": total
        }
    }
    
@frappe.whitelist(allow_guest=True)
def get_transactions_dashboard():
    """
    Returns high-level transaction statistics based on Cash/Bank movements.
    """
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Identify Cash/Bank accounts
    bank_accounts = frappe.db.get_all("Account", 
        filters={"account_type": ["in", ["Cash", "Bank"]], "company": company, "is_group": 0},
        pluck="name"
    )
    
    if not bank_accounts:
        # Fallback to any asset account if none marked as Cash/Bank
        bank_accounts = frappe.db.get_all("Account", 
            filters={"root_type": "Asset", "company": company, "is_group": 0},
            pluck="name"
        )

    today = frappe.utils.nowdate()
    
    # 1. Today's Transaction Amount (Net movement today)
    today_stats = frappe.db.sql("""
        SELECT SUM(debit - credit) as net
        FROM `tabGL Entry`
        WHERE account IN %s AND posting_date = %s AND docstatus = 1
    """, (tuple(bank_accounts), today), as_dict=True)
    today_amount = today_stats[0].net if today_stats and today_stats[0].net else 0.0
    
    # 2. Total In (Debits to Cash/Bank)
    total_in = frappe.db.get_value("GL Entry", 
        {"account": ["in", bank_accounts], "docstatus": 1}, "SUM(debit)") or 0.0
        
    # 3. Total Out (Credits to Cash/Bank)
    total_out = frappe.db.get_value("GL Entry", 
        {"account": ["in", bank_accounts], "docstatus": 1}, "SUM(credit)") or 0.0
        
    return {
        "status": "success",
        "data": {
            "today_transactions_amount": round(flt(today_amount), 2),
            "total_in": round(flt(total_in), 2),
            "total_out": round(flt(total_out), 2),
            "net_flow": round(flt(total_in - total_out), 2)
        }
    }


@frappe.whitelist(allow_guest=True)
def get_all_transactions(limit_start=0, limit_page_length=20, category=None, start_date=None, end_date=None, status=None, search=None):
    """
    Returns a consolidated list of transactions from GL Entry.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # We want one row per "Transaction" (Voucher)
    # Most transactions have multiple GL entries. We focus on the "Cash/Bank" side or the "Party" side.
    # To keep it simple and accurate, we group by voucher_no.
    
    conditions = ["gl.docstatus = 1", "gl.company = %s"]
    params = [company]
    
    if category:
        if category == "Savings":
            conditions.append("gl.voucher_type = 'Journal Entry' AND gl.voucher_no LIKE 'SAV-%%'")
        elif category == "Loan":
            conditions.append("gl.voucher_type IN ('Journal Entry', 'Payment Entry') AND (gl.voucher_no LIKE 'LREP-%%' OR gl.voucher_no LIKE 'LOAN-%%')")
        elif category == "Expense":
            conditions.append("gl.voucher_type = 'Journal Entry' AND EXISTS (SELECT 1 FROM `tabJournal Entry Account` jea JOIN `tabAccount` acc ON jea.account = acc.name WHERE jea.parent = gl.voucher_no AND acc.root_type = 'Expense')")
            
    if start_date and end_date:
        conditions.append("gl.posting_date BETWEEN %s AND %s")
        params.extend([start_date, end_date])

    if status:
        if status.lower() == "completed":
            conditions.append("gl.docstatus = 1")
        elif status.lower() == "cancelled":
            conditions.append("gl.docstatus = 2")
        elif status.lower() == "draft":
            conditions.append("gl.docstatus = 0")

    if search:
        search_val = f"%{search}%"
        conditions.append("(gl.voucher_no LIKE %s OR gl.remarks LIKE %s OR gl.party LIKE %s)")
        params.extend([search_val, search_val, search_val])

    where_clause = "WHERE " + " AND ".join(conditions)
    
    # Query for distinct vouchers
    query = f"""
        SELECT 
            gl.voucher_no as transaction_id,
            gl.posting_date as date,
            gl.voucher_type,
            SUM(gl.debit) as total_volume,
            gl.party,
            gl.party_type,
            gl.remarks,
            gl.docstatus
        FROM `tabGL Entry` gl
        {where_clause}
        GROUP BY gl.voucher_no
        ORDER BY gl.posting_date DESC, gl.creation DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([limit_page_length, limit_start])
    vouchers = frappe.db.sql(query, tuple(params), as_dict=True)
    
    # Identify Cash/Bank accounts to determine In/Out
    bank_accounts = frappe.db.get_all("Account", 
        filters={"account_type": ["in", ["Cash", "Bank"]], "company": company, "is_group": 0},
        pluck="name"
    )
    
    results = []
    for v in vouchers:
        # Determine Category
        category = "General"
        remarks_lower = (v.remarks or "").lower()
        
        if "savings" in remarks_lower:
            category = "Savings"
        elif "repayment" in remarks_lower:
            category = "Loan Repayment"
        elif "disbursement" in remarks_lower:
            category = "Loan Disbursement"
        elif "registration" in remarks_lower:
            category = "Registration Fee"
        elif v.voucher_type == "Journal Entry":
            # Check for Expense accounts in this voucher
            has_expense = frappe.db.sql("""
                SELECT 1 FROM `tabGL Entry` gl
                JOIN `tabAccount` acc ON gl.account = acc.name
                WHERE gl.voucher_no = %s AND acc.root_type = 'Expense'
                LIMIT 1
            """, v.transaction_id)
            if has_expense:
                category = "Expense"

        # Determine In/Out based on Cash/Bank impact
        # If Cash/Bank is Debited -> In
        # If Cash/Bank is Credited -> Out
        cash_impact = frappe.db.sql("""
            SELECT SUM(debit - credit) as net
            FROM `tabGL Entry`
            WHERE voucher_no = %s AND account IN %s
        """, (v.transaction_id, tuple(bank_accounts)), as_dict=True)
        
        net_cash = cash_impact[0].net if cash_impact and cash_impact[0].net else 0.0
        tx_type = "In" if net_cash > 0 else "Out" if net_cash < 0 else "Neutral"
        
        # Absolute amount for display
        display_amount = abs(net_cash) if net_cash != 0 else (flt(v.total_volume) / 1.0) # Fallback to total volume if no cash impact (unlikely)
        
        # Member Name
        member_name = ""
        if v.party_type == "Customer":
            member_name = frappe.db.get_value("SACCO Member", {"customer_link": v.party}, "member_name")
        
        if not member_name and v.remarks:
            import re
            match = re.search(r'MEM-\d+', v.remarks)
            if match:
                member_id = match.group()
                member_name = frappe.db.get_value("SACCO Member", member_id, "member_name")
        
        results.append({
            "transaction_id": v.transaction_id,
            "date": str(v.date),
            "member_name": member_name or "System",
            "type": tx_type,
            "category": category,
            "amount": round(display_amount, 2),
            "reference": v.remarks,
            "status": "Completed" if v.docstatus == 1 else "Cancelled" if v.docstatus == 2 else "Draft"
        })
        
    return {
        "status": "success",
        "data": results,
        "pagination": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "total": frappe.db.sql(f"SELECT COUNT(DISTINCT voucher_no) as total FROM `tabGL Entry` gl {where_clause}", tuple(params[:-2]), as_dict=True)[0].total
        }
    }


@frappe.whitelist(allow_guest=True)
def get_transaction_details(transaction_id):
    """
    Returns detailed view of a transaction including ledger movements and parties.
    """
    entries = frappe.db.get_all("GL Entry", 
        filters={"voucher_no": transaction_id},
        fields=["account", "debit", "credit", "party", "party_type", "remarks", "posting_date"]
    )
    
    if not entries:
        frappe.throw(f"Transaction {transaction_id} not found.", frappe.DoesNotExistError)
        
    accounts_affected = []
    parties = set()
    
    for e in entries:
        accounts_affected.append({
            "account": e.account,
            "debit": round(flt(e.debit), 2),
            "credit": round(flt(e.credit), 2)
        })
        if e.party:
            parties.add(e.party)
            
    # Resolve party names
    involved_parties = []
    for p in parties:
        # Check if it's a member
        member = frappe.db.get_value("SACCO Member", {"customer_link": p}, ["name", "member_name"], as_dict=True)
        if member:
            involved_parties.append({
                "id": member.name,
                "name": member.member_name,
                "type": "Member"
            })
        else:
            involved_parties.append({"id": p, "name": p, "type": "Other"})
            
    return {
        "status": "success",
        "data": {
            "transaction_id": transaction_id,
            "date": str(entries[0].posting_date),
            "accounts_affected": accounts_affected,
            "parties_involved": involved_parties,
            "remarks": entries[0].remarks
        }
    }



