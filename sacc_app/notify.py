import frappe
from frappe import _

def send_member_email(member_id_or_email, subject, message, template=None, args=None, recipient_name=None):
    """
    Standardizes email delivery to SACCO members or users.
    Supports standard Frappe Email Templates.
    """
    if not member_id_or_email:
        return

    email = None
    member = None
    
    if "@" in member_id_or_email:
        email = member_id_or_email
        # Try to find corresponding member
        member_id = frappe.db.get_value("SACCO Member", {"email": email}, "name")
        if member_id:
            member = frappe.get_doc("SACCO Member", member_id)
    else:
        if frappe.db.exists("SACCO Member", member_id_or_email):
            member = frappe.get_doc("SACCO Member", member_id_or_email)
            email = member.email

    if not email:
        return
    
    # Get Company Name for branding
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    company_name = frappe.db.get_value("Company", company, "company_name") or company or "SACCO MANAGEMENT"
    
    # Standard fallback for name
    salutation_name = recipient_name or "Member"
    if member:
        salutation_name = member.first_name or member.member_name or salutation_name
    elif not recipient_name:
        # Try to find user name
        salutation_name = frappe.db.get_value("User", email, "first_name") or "User"
        
    if template:
        # If a template is provided, use Frappe's rendering logic
        from frappe.email.doctype.email_template.email_template import get_email_template
        
        email_args = {
            "first_name": salutation_name,
            "company_name": company_name
        }
        if member:
            email_args["doc"] = member
        if args:
            email_args.update(args)
            
        template_data = get_email_template(template, email_args)
        subject = template_data.get("subject", subject)
        message = template_data.get("message", message)

    # Portal URL (Strip port if present for production-like URL)
    from frappe.utils import get_url
    site_url = get_url()
    if ":8000" in site_url:
        site_url = site_url.replace(":8000", "")
    
    # Standard header/footer for brand consistency
    full_message = f"""
    <div style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f4f7f9;">
        <div style="max-width:600px;margin:20px auto;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); padding: 30px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 1px;">{company_name.upper()}</h1>
            </div>
            
            <!-- Content -->
            <div style="padding: 40px 30px; color: #3c4043; line-height: 1.6;">
                <h2 style="color: #1a73e8; margin-top: 0;">Hello, {salutation_name}!</h2>
                <div style="font-size: 16px;">
                    {message}
                </div>
                
                <!-- Optional CTA -->
                <div style="margin-top: 30px; text-align: center;">
                    <a href="{site_url}" style="background-color: #1a73e8; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: 500; display: inline-block;">Login to Portal</a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e8eaed;">
                <p style="margin: 0; color: #70757a; font-size: 14px;">
                    &copy; 2026 {company_name}. All rights reserved.
                </p>
                <p style="margin: 5px 0 0; color: #70757a; font-size: 12px;">
                    This is an automated notification regarding your account.
                </p>
            </div>
        </div>
    </div>
    """
    
    frappe.sendmail(
        recipients=[email],
        subject=subject,
        message=full_message,
        delayed=False # Send immediately for financial/auth alerts
    )
