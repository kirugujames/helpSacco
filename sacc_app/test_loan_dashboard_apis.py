import frappe
from frappe.utils import flt

def test_dashboard_api():
    """Test the loan dashboard API"""
    print("\n=== Testing Loan Dashboard API ===")
    
    from sacc_app.api import get_loan_dashboard
    
    try:
        result = get_loan_dashboard()
        
        print(f"✅ API call successful")
        print(f"   Status: {result.get('status')}")
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            print(f"\n   Dashboard Statistics:")
            print(f"   - Total Pending Applications: {data.get('total_pending_applications')}")
            print(f"   - Active Loans Count: {data.get('active_loans_count')}")
            print(f"   - Active Loans Amount: {data.get('active_loans_amount')}")
            print(f"   - Total Disbursed Amount: {data.get('total_disbursed_amount')}")
            print(f"   - Default Rate: {data.get('default_rate')}%")
            
            # Verify all required fields are present
            required_fields = ['total_pending_applications', 'active_loans_count', 
                             'active_loans_amount', 'total_disbursed_amount', 'default_rate']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
        else:
            print(f"   ❌ API returned error status")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_applications_basic():
    """Test the loan applications API - basic functionality"""
    print("\n=== Testing Loan Applications API - Basic ===")
    
    from sacc_app.api import get_loan_applications
    
    try:
        result = get_loan_applications(limit_page_length=5)
        
        print(f"✅ API call successful")
        print(f"   Status: {result.get('status')}")
        
        if result.get('status') == 'success':
            data = result.get('data', [])
            pagination = result.get('pagination', {})
            
            print(f"\n   Pagination Info:")
            print(f"   - Total Records: {pagination.get('total')}")
            print(f"   - Limit Start: {pagination.get('limit_start')}")
            print(f"   - Limit Page Length: {pagination.get('limit_page_length')}")
            print(f"   - Records Returned: {len(data)}")
            
            if data:
                print(f"\n   Sample Loan (first record):")
                loan = data[0]
                print(f"   - Member Name: {loan.get('member_name')}")
                print(f"   - Member ID: {loan.get('member_id')}")
                print(f"   - Loan ID: {loan.get('loan_id')}")
                print(f"   - Amount Applied: {loan.get('amount_applied')}")
                print(f"   - Interest Rate: {loan.get('interest_rate')}%")
                print(f"   - Status: {loan.get('status')}")
                print(f"   - Purpose: {loan.get('purpose')}")
                print(f"   - Payment Progress: {loan.get('payment_progress')}%")
                
                # Verify all required fields
                required_fields = ['member_name', 'member_id', 'loan_id', 'amount_applied',
                                 'amount_disbursed', 'interest_rate', 'status', 'purpose',
                                 'payment_progress', 'creation_date']
                missing_fields = [f for f in required_fields if f not in loan]
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")
            else:
                print(f"   ℹ️  No loan records found in database")
                
        else:
            print(f"   ❌ API returned error status")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_applications_filters():
    """Test the loan applications API - filters"""
    print("\n=== Testing Loan Applications API - Filters ===")
    
    from sacc_app.api import get_loan_applications
    
    try:
        # Test 1: Filter by status
        print("\n   Test 1: Filter by status='Active'")
        result = get_loan_applications(status="Active", limit_page_length=3)
        
        if result.get('status') == 'success':
            data = result.get('data', [])
            print(f"   ✅ Found {len(data)} active loans")
            
            # Verify all returned loans have Active status
            if data:
                all_active = all(loan.get('status') == 'Active' for loan in data)
                if all_active:
                    print(f"   ✅ All returned loans have Active status")
                else:
                    print(f"   ❌ Some loans don't have Active status")
        
        # Test 2: Filter by member name (partial match)
        print("\n   Test 2: Search by member_name (partial match)")
        # Get first member name from database
        first_member = frappe.db.get_value("SACCO Member", {}, ["name", "member_name"], as_dict=True)
        
        if first_member and first_member.member_name:
            # Search with first word of member name
            search_term = first_member.member_name.split()[0]
            result = get_loan_applications(member_name=search_term, limit_page_length=3)
            
            if result.get('status') == 'success':
                data = result.get('data', [])
                print(f"   ✅ Search for '{search_term}' returned {len(data)} loans")
                
                if data:
                    # Verify member names contain search term
                    matches = [loan for loan in data if search_term.lower() in loan.get('member_name', '').lower()]
                    print(f"   ✅ {len(matches)} loans match the search term")
        else:
            print(f"   ℹ️  No members found for testing")
        
        # Test 3: Filter by member_id
        print("\n   Test 3: Filter by member_id")
        first_loan = frappe.db.get_value("SACCO Loan", {}, ["member"], as_dict=True)
        
        if first_loan:
            result = get_loan_applications(member_id=first_loan.member, limit_page_length=10)
            
            if result.get('status') == 'success':
                data = result.get('data', [])
                print(f"   ✅ Found {len(data)} loans for member {first_loan.member}")
                
                # Verify all loans belong to the member
                if data:
                    all_match = all(loan.get('member_id') == first_loan.member for loan in data)
                    if all_match:
                        print(f"   ✅ All returned loans belong to the specified member")
                    else:
                        print(f"   ❌ Some loans don't belong to the specified member")
        else:
            print(f"   ℹ️  No loans found for testing")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_applications_pagination():
    """Test the loan applications API - pagination"""
    print("\n=== Testing Loan Applications API - Pagination ===")
    
    from sacc_app.api import get_loan_applications
    
    try:
        # Get total count
        result_all = get_loan_applications(limit_page_length=1000)
        total_loans = result_all.get('pagination', {}).get('total', 0)
        
        print(f"   Total loans in database: {total_loans}")
        
        if total_loans > 0:
            # Test pagination
            page_size = 2
            result_page1 = get_loan_applications(limit_start=0, limit_page_length=page_size)
            result_page2 = get_loan_applications(limit_start=page_size, limit_page_length=page_size)
            
            data_page1 = result_page1.get('data', [])
            data_page2 = result_page2.get('data', [])
            
            print(f"\n   Page 1 (limit_start=0, limit_page_length={page_size}):")
            print(f"   - Records returned: {len(data_page1)}")
            if data_page1:
                print(f"   - First loan ID: {data_page1[0].get('loan_id')}")
            
            print(f"\n   Page 2 (limit_start={page_size}, limit_page_length={page_size}):")
            print(f"   - Records returned: {len(data_page2)}")
            if data_page2:
                print(f"   - First loan ID: {data_page2[0].get('loan_id')}")
            
            # Verify pages don't overlap
            if data_page1 and data_page2:
                page1_ids = {loan.get('loan_id') for loan in data_page1}
                page2_ids = {loan.get('loan_id') for loan in data_page2}
                overlap = page1_ids.intersection(page2_ids)
                
                if not overlap:
                    print(f"   ✅ No overlap between pages - pagination working correctly")
                else:
                    print(f"   ❌ Pages overlap: {overlap}")
            
            print(f"   ✅ Pagination test completed")
        else:
            print(f"   ℹ️  No loans in database to test pagination")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests():
    """Run all loan dashboard API tests"""
    print("=" * 60)
    print("LOAN DASHBOARD AND APPLICATIONS API TESTS")
    print("=" * 60)
    
    test_dashboard_api()
    test_applications_basic()
    test_applications_filters()
    test_applications_pagination()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
