import frappe
from sacc_app.welfare_dashboard_api import get_welfare_stats

def test_dashboard():
    stats = get_welfare_stats()
    print("Welfare Dashboard Stats:")
    print(stats)
    
    # Basic validation
    data = stats.get("data", {})
    if "total_claims" in data and "total_contributions" in data:
        print("PASS: API returned expected keys.")
    else:
        print("FAIL: API missing expected keys.")

if __name__ == "__main__":
    test_dashboard()
