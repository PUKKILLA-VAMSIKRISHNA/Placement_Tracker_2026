from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

def check_admin():
    try:
        # Check for specific admin email
        email_to_check = 'bhargavtheadmin@gmail.com'
        print(f"\n=== Checking for admin with email: {email_to_check} ===")
        
        # Get admin by email
        response = supabase.table('admins').select('*').eq('email', email_to_check).execute()
        
        if response.data:
            admin = response.data[0]
            print("\n=== Admin Found ===")
            print(f"ID: {admin['id']}")
            print(f"Email: {admin['email']}")
            print(f"Password Hash: {admin['password_hash']}")
            print(f"Created At: {admin.get('created_at')}")
            
            # Check the length of the password hash
            print(f"\nPassword hash length: {len(str(admin['password_hash']))} characters")
            
            # Check if it's a hash or plain text
            if len(str(admin['password_hash'])) > 50:
                print("This looks like a hashed password")
            else:
                print("This looks like a plain text password")
        else:
            print(f"\nNo admin found with email: {email_to_check}")
            
        # Also list all admins for reference
        print("\n=== All Admin Users ===")
        all_admins = supabase.table('admins').select('*').execute()
        if all_admins.data:
            for admin in all_admins.data:
                print(f"\nEmail: {admin['email']}")
                print(f"Password: {admin['password_hash']}")
        else:
            print("No admin users found in the database!")
            
    except Exception as e:
        print(f"\nError checking admin users: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_admin()
