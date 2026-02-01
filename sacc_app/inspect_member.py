import frappe
import json

def inspect():
    meta = frappe.get_meta("SACCO Member")
    fields = [{"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype} for f in meta.fields]
    
    # Check status options if it's a Select field
    status_options = ""
    for f in meta.fields:
        if f.fieldname == "status":
            status_options = f.options
            break
            
    print(json.dumps({
        "fields": fields,
        "status_options": status_options
    }, indent=2))

if __name__ == "__main__":
    inspect()
