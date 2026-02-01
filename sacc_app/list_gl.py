
import frappe

def list_gl():
    vouch = "LN-00004"
    entries = frappe.get_all("GL Entry", filters={"voucher_no": vouch}, 
                            fields=["name", "account", "debit", "credit", "is_cancelled"])
    
    print(f"--- GL Entries for {vouch} ---")
    if not entries:
        print("None found.")
    for e in entries:
        print(f"{e.name:20} | {e.account:30} | Dr: {e.debit:10} | Cr: {e.credit:10} | Cancelled: {e.is_cancelled}")

if __name__ == "__main__":
    list_gl()
