import frappe

def test_filters():
    # Let's see what SQL it generates (if we can find out) or just check results
    res = frappe.get_all("SACCO Member", 
        filters={"status": "Active"}, 
        or_filters={"member_name": ["like", "%NonExistent%"], "name": ["like", "%NonExistent%"]}
    )
    print(f"Results with filters AND non-existent or_filters: {len(res)}")
    
    res2 = frappe.get_all("SACCO Member", 
        filters={"status": "Active"}
    )
    print(f"Results with only active filters: {len(res2)}")

if __name__ == "__main__":
    test_filters()
