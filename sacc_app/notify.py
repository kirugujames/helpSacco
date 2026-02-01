import frappe
from frappe import _

def send_member_email(member_id, subject, message):
    """
    Standardizes email delivery to SACCO members.
    """
    member = frappe.get_doc("SACCO Member", member_id)
    if not member.email:
        return
    
    # Standard header/footer for brand consistency
    full_message = f"""
    <div style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f4f7f9;">
        <div style="max-width:600px;margin:20px auto;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); padding: 30px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 1px;">SACCO MANAGEMENT</h1>
            </div>
            
            <!-- Content -->
            <div style="padding: 40px 30px; color: #3c4043; line-height: 1.6;">
                <h2 style="color: #1a73e8; margin-top: 0;">Hello, {member.first_name}!</h2>
                <div style="font-size: 16px;">
                    {message}
                </div>
                
                <!-- Optional CTA -->
                <div style="margin-top: 30px; text-align: center;">
                    <a href="#" style="background-color: #1a73e8; color: #ffffff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: 500; display: inline-block;">Login to Portal</a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e8eaed;">
                <p style="margin: 0; color: #70757a; font-size: 14px;">
                    &copy; 2026 SACCO Team. All rights reserved.
                </p>
                <p style="margin: 5px 0 0; color: #70757a; font-size: 12px;">
                    This is an automated notification regarding your account.
                </p>
                <div style="margin-top: 10px;">
                    <a href="#" style="color: #1a73e8; text-decoration: none; font-size: 12px; margin: 0 10px;">Support</a> | 
                    <a href="#" style="color: #1a73e8; text-decoration: none; font-size: 12px; margin: 0 10px;">Privacy Policy</a>
                </div>
            </div>
        </div>
    </div>
    """
    
    frappe.sendmail(
        recipients=[member.email],
        subject=subject,
        message=full_message,
        delayed=False # Send immediately for financial alerts
    )
