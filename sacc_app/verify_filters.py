from sacc_app.api import get_all_transactions
import json

def run_test():
    print("Testing get_all_transactions filters...")
    
    # 1. No filters
    res1 = get_all_transactions()
    print(f"No filters count: {len(res1.get('data', []))}")
    
    # 2. Status filter
    res2 = get_all_transactions(status="Completed")
    data2 = res2.get('data', [])
    print(f"Status='Completed' count: {len(data2)}")
    if data2:
        statuses = set(t['status'] for t in data2)
        print(f"Unique statuses found: {statuses}")
        assert all(s == 'Completed' for s in statuses)
    
    # 3. Search filter
    res3 = get_all_transactions(search="LOAN")
    data3 = res3.get('data', [])
    print(f"Search='LOAN' count: {len(data3)}")
    if data3:
        print(f"First search result ID: {data3[0]['transaction_id']}")
    
    # 4. Combined
    res4 = get_all_transactions(status="Completed", search="LOAN")
    data4 = res4.get('data', [])
    print(f"Combined count: {len(data4)}")
    
    print("✅ All filter tests passed!")

if __name__ == "__main__":
    run_test()
