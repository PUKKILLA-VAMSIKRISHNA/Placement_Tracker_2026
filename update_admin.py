from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

# New admin credentials
new_email = 'bhargavtheadmin@gmail.com'
new_password_hash = 'pbkdf2:sha256:600000$ehKMdV1KQEQJqkdA$df7222ac9dce7d4d67a2fcdf43911989e95bd6e3fd38f8c9b10d8b645d3cd2bf'

# Update the admin user
try:
    # First, check if the admin exists
    response = supabase.table('admins').select('*').execute()
    
    if response.data:
        # Update existing admin
        admin_id = response.data[0]['id']
        update_response = supabase.table('admins').update({
            'email': new_email,
            'password_hash': new_password_hash
        }).eq('id', admin_id).execute()
        print("Admin credentials updated successfully!")
    else:
        # Insert new admin if none exists
        insert_response = supabase.table('admins').insert({
            'email': new_email,
            'password_hash': new_password_hash
        }).execute()
        print("New admin user created successfully!")
        
except Exception as e:
    print(f"Error updating admin: {str(e)}")
