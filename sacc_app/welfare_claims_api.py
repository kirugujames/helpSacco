import frappe
from frappe import _
from frappe.utils import flt, nowdate

@frappe.whitelist(allow_guest=True, methods=['POST'])
def create_welfare_claim(member_id, reason, claim_amount, description=None):
    """
    Creates a new welfare claim for a member.
    """
    if not member_id:
        frappe.throw("Member ID is required")
    
    if not frappe.db.exists("SACCO Member", member_id):
        frappe.throw(f"Member {member_id} not found")
    
    if not reason:
        frappe.throw("Reason is required")
        
    if not claim_amount or flt(claim_amount) <= 0:
        frappe.throw("Valid claim amount is required")
    
    # Create the claim document
    claim = frappe.get_doc({
        "doctype": "SACCO Welfare Claim",
        "member": member_id,
        "reason": reason,
        "claim_amount": flt(claim_amount),
        "description": description or "",
        "claim_date": nowdate(),
        "status": "Pending"
    })
    
    claim.insert(ignore_permissions=True)
    
    return {
        "status": "success",
        "message": f"Welfare claim {claim.name} created successfully",
        "data": {
            "claim_id": claim.name,
            "member_id": member_id,
            "reason": reason,
            "claim_amount": flt(claim_amount),
            "status": "Pending",
            "claim_date": str(claim.claim_date)
        }
    }


@frappe.whitelist(allow_guest=True, methods=['POST'])
def approve_welfare_claim(claim_id, amount_per_member):
    """
    Approves a welfare claim and sets the amount per member.
    """
    if not claim_id:
        frappe.throw("Claim ID is required")
        
    if not frappe.db.exists("SACCO Welfare Claim", claim_id):
        frappe.throw(f"Welfare claim {claim_id} not found")

    if amount_per_member is None:
         frappe.throw("Amount per member is required")
         
    claim = frappe.get_doc("SACCO Welfare Claim", claim_id)
    
    if claim.status != "Pending":
        frappe.throw(f"Claim {claim_id} is not in Pending status")
        
    claim.status = "Approved"
    claim.amount_per_member = flt(amount_per_member)
    claim.save(ignore_permissions=True)
    
    return {
        "status": "success",
        "message": f"Welfare claim {claim.name} approved successfully",
        "data": {
            "claim_id": claim.name,
            "status": "Approved",
            "amount_per_member": claim.amount_per_member
        }
    }


@frappe.whitelist(allow_guest=True)
def get_all_welfare_claims(status=None, member_id=None, limit_start=0, limit_page_length=20):
    """
    Returns all welfare claims with optional filters.
    """
    limit_start = int(limit_start)
    limit_page_length = int(limit_page_length)
    
    filters = {}
    if status:
        filters["status"] = status
    if member_id:
        filters["member"] = member_id
    
    claims = frappe.db.get_all("SACCO Welfare Claim",
        filters=filters,
        fields=[
            "name", "member", "reason", "claim_amount", "amount_paid",
            "status", "claim_date", "payment_date", "description", "creation",
            "amount_per_member", "total_collected"
        ],
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="creation desc"
    )
    
    # Enrich with member names
    for claim in claims:
        member_name = frappe.db.get_value("SACCO Member", claim.member, "member_name")
        claim["member_name"] = member_name or claim.member
        claim["claim_amount"] = flt(claim.claim_amount)
        claim["amount_per_member"] = flt(claim.amount_per_member)
        claim["total_collected"] = flt(claim.total_collected)
        claim["amount_paid"] = flt(claim.amount_paid)
        claim["claim_date"] = str(claim.claim_date) if claim.claim_date else ""
        claim["payment_date"] = str(claim.payment_date) if claim.payment_date else ""
    
    # Get total count
    total = frappe.db.count("SACCO Welfare Claim", filters=filters)
    
    return {
        "status": "success",
        "data": claims,
        "pagination": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "total": total
        }
    }


@frappe.whitelist(allow_guest=True, methods=['POST'])
def pay_welfare_claim(claim_id, payment_amount, payment_mode="Cash"):
    """
    Processes payment for a welfare claim and links it to the claim.
    """
    if not claim_id:
        frappe.throw("Claim ID is required")
    
    if not frappe.db.exists("SACCO Welfare Claim", claim_id):
        frappe.throw(f"Welfare claim {claim_id} not found")
    
    if not payment_amount or flt(payment_amount) <= 0:
        frappe.throw("Valid payment amount is required")
    
    claim = frappe.get_doc("SACCO Welfare Claim", claim_id)
    
    if claim.status == "Paid":
        frappe.throw(f"Claim {claim_id} has already been paid")
    
    if claim.status == "Rejected":
        frappe.throw(f"Claim {claim_id} has been rejected and cannot be paid")
    
    # Update claim with payment details
    claim.amount_paid = flt(payment_amount)
    claim.payment_date = nowdate()
    claim.payment_mode = payment_mode
    claim.status = "Paid" if flt(payment_amount) >= flt(claim.claim_amount) else "Partially Paid"
    claim.save(ignore_permissions=True)
    
    # Create GL Entry for the payment
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # Get accounts
    cash_account = frappe.db.get_value("Account", {"account_type": "Cash", "company": company, "is_group": 0})
    if not cash_account:
        cash_account = frappe.db.get_value("Account", {"is_group": 0, "root_type": "Asset", "company": company})
    
    welfare_fund = frappe.db.get_value("Account", {"account_name": "Welfare Fund Account", "company": company})
    if not welfare_fund:
        welfare_fund = frappe.db.get_value("Account", {"root_type": "Liability", "is_group": 0, "company": company})
    
    # Create Journal Entry for payment
    je = frappe.new_doc("Journal Entry")
    je.posting_date = nowdate()
    je.company = company
    je.voucher_type = "Journal Entry"
    je.user_remark = f"Welfare Claim Payment: {claim_id}"
    
    # Dr Welfare Fund, Cr Cash (paying out from welfare fund)
    je.append("accounts", {
        "account": welfare_fund,
        "debit_in_account_currency": flt(payment_amount),
        "credit_in_account_currency": 0
    })
    je.append("accounts", {
        "account": cash_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": flt(payment_amount)
    })
    
    je.save(ignore_permissions=True)
    je.submit()
    
    # Link the journal entry to the claim
    claim.db_set("journal_entry", je.name)
    
    return {
        "status": "success",
        "message": f"Payment of {payment_amount} processed for claim {claim_id}",
        "data": {
            "claim_id": claim_id,
            "amount_paid": flt(payment_amount),
            "payment_date": str(claim.payment_date),
            "claim_status": claim.status,
            "journal_entry": je.name
        }
    }


@frappe.whitelist(allow_guest=True)
def get_welfare_claim_by_id(claim_id):
    """
    Returns detailed information about a specific welfare claim.
    """
    if not claim_id:
        frappe.throw("Claim ID is required")
    
    if not frappe.db.exists("SACCO Welfare Claim", claim_id):
        return {
            "status": "error",
            "message": f"Welfare claim {claim_id} not found"
        }
    
    claim = frappe.get_doc("SACCO Welfare Claim", claim_id)
    
    # Get member details
    member = frappe.get_doc("SACCO Member", claim.member)
    
    claim_data = {
        "claim_id": claim.name,
        "member_id": claim.member,
        "member_name": member.member_name,
        "member_email": member.email,
        "member_phone": member.phone,
        "reason": claim.reason,
        "description": claim.description or "",
        "claim_amount": flt(claim.claim_amount),
        "amount_per_member": flt(claim.amount_per_member),
        "total_collected": flt(claim.total_collected),
        "amount_paid": flt(claim.amount_paid),
        "status": claim.status,
        "claim_date": str(claim.claim_date) if claim.claim_date else "",
        "payment_date": str(claim.payment_date) if claim.payment_date else "",
        "payment_mode": claim.payment_mode or "",
        "journal_entry": claim.journal_entry or "",
        "creation": str(claim.creation),
        "modified": str(claim.modified)
    }
    
    return {
        "status": "success",
        "data": claim_data
    }
