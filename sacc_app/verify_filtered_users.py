import frappe
from sacc_app.api import get_all_users

def verify():
    print("Testing get_all_users API (excluding SACCO Member-only users)...")
    
    # Test get_all_users
    users_res = get_all_users()
    
    if users_res.get("status") != "success":
        print(f"❌ get_all_users Failed: {users_res.get('message')}")
        return
        
    users = users_res.get("data", [])
    print(f"✅ Retrieved {len(users)} users")
    
    # Check if any user has only SACCO Member role
    sacco_member_only = [
        u for u in users 
        if u.get("roles") == ["SACCO Member"]
    ]
    
    if sacco_member_only:
        print(f"❌ Found {len(sacco_member_only)} users with only SACCO Member role:")
        for u in sacco_member_only[:5]:  # Show first 5
            print(f"   - {u.get('email')}: {u.get('roles')}")
    else:
        print("✅ No users with only SACCO Member role found")
    
    # Check if users with multiple roles (including SACCO Member) are still included
    multi_role_with_sacco = [
        u for u in users 
        if "SACCO Member" in u.get("roles", []) and len(u.get("roles", [])) > 1
    ]
    
    if multi_role_with_sacco:
        print(f"✅ Found {len(multi_role_with_sacco)} users with SACCO Member + other roles (correctly included)")
        print(f"   Sample: {multi_role_with_sacco[0].get('email')}: {multi_role_with_sacco[0].get('roles')}")
    else:
        print("ℹ️  No users with SACCO Member + other roles found")
    
    # Show sample of returned users
    if users:
        print(f"\nSample users returned:")
        for u in users[:3]:
            print(f"   - {u.get('email')}: {u.get('roles')}")
    
    print("\n✅ Verification complete!")

if __name__ == "__main__":
    pass
