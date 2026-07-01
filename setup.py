#!/usr/bin/env python3
"""
Setup script for IT Branch 2026 Placement Tracker
This script helps with initial configuration and admin user creation.
"""

import os
import sys
from werkzeug.security import generate_password_hash
from supabase import create_client, Client

def create_env_file():
    """Create .env file from template"""
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        return
    
    if os.path.exists('.env.example'):
        print("Creating .env file from template...")
        with open('.env.example', 'r') as template:
            content = template.read()
        
        with open('.env', 'w') as env_file:
            env_file.write(content)
        
        print("✓ .env file created")
        print("⚠️  Please update .env file with your Supabase credentials")
    else:
        print("❌ .env.example file not found")

def create_admin_user():
    """Create admin user in Supabase"""
    print("\n=== Admin User Setup ===")
    
    # Get Supabase credentials
    supabase_url = input("Enter your Supabase URL: ").strip()
    supabase_key = input("Enter your Supabase Anon Key: ").strip()
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials are required")
        return
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get admin credentials
        admin_email = input("Enter admin email (default: admin@placement.com): ").strip()
        if not admin_email:
            admin_email = "admin@placement.com"
        
        admin_password = input("Enter admin password (default: admin123): ").strip()
        if not admin_password:
            admin_password = "admin123"
        
        # Generate password hash
        password_hash = generate_password_hash(admin_password)
        
        # Insert admin user
        admin_data = {
            'email': admin_email,
            'password_hash': password_hash
        }
        
        response = supabase.table('admins').insert(admin_data).execute()
        
        if response.data:
            print(f"✓ Admin user created successfully!")
            print(f"  Email: {admin_email}")
            print(f"  Password: {admin_password}")
            print("⚠️  Please change the default password after first login")
        else:
            print("❌ Failed to create admin user")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        print("Make sure you have run the database schema SQL in Supabase first")

def check_requirements():
    """Check if all requirements are installed"""
    print("=== Checking Requirements ===")
    
    try:
        import flask
        print("✓ Flask installed")
    except ImportError:
        print("❌ Flask not installed. Run: pip install -r requirements.txt")
        return False
    
    try:
        import supabase
        print("✓ Supabase client installed")
    except ImportError:
        print("❌ Supabase client not installed. Run: pip install -r requirements.txt")
        return False
    
    return True

def create_sample_data():
    """Create sample companies and students"""
    print("\n=== Sample Data Setup ===")
    
    create_sample = input("Do you want to create sample data? (y/n): ").strip().lower()
    if create_sample != 'y':
        return
    
    supabase_url = input("Enter your Supabase URL: ").strip()
    supabase_key = input("Enter your Supabase Anon Key: ").strip()
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Sample companies
        sample_companies = [
            {
                'name': 'TechCorp Solutions',
                'hiring_flow': 'Online Test → Technical Interview → HR Interview → Final Selection',
                'ctc_offer': '₹8.5 LPA',
                'agreement_years': 2
            },
            {
                'name': 'InnovateTech Ltd',
                'hiring_flow': 'Aptitude Test → Coding Round → Technical Interview → Managerial Round',
                'ctc_offer': '₹12.0 LPA',
                'agreement_years': 3
            },
            {
                'name': 'DataDrive Systems',
                'hiring_flow': 'Online Assessment → Group Discussion → Technical Interview → HR Round',
                'ctc_offer': '₹10.5 LPA',
                'agreement_years': 2
            }
        ]
        
        print("Creating sample companies...")
        for company in sample_companies:
            response = supabase.table('companies').insert(company).execute()
            if response.data:
                print(f"✓ Created company: {company['name']}")
        
        print("✓ Sample data created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")

def main():
    """Main setup function"""
    print("🎓 IT Branch 2026 Placement Tracker Setup")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please install requirements first: pip install -r requirements.txt")
        sys.exit(1)
    
    # Create .env file
    print("\n=== Environment Setup ===")
    create_env_file()
    
    # Database setup reminder
    print("\n=== Database Setup ===")
    print("Before proceeding, make sure you have:")
    print("1. Created a Supabase project")
    print("2. Run the SQL from 'database_schema.sql' in Supabase SQL Editor")
    print("3. Updated your .env file with Supabase credentials")
    
    proceed = input("\nHave you completed the above steps? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Please complete the database setup first, then run this script again.")
        sys.exit(0)
    
    # Create admin user
    create_admin_user()
    
    # Create sample data
    create_sample_data()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Update app.py with your Supabase credentials")
    print("2. Run the application: python app.py")
    print("3. Visit http://localhost:5000")
    print("4. Login as admin and start adding companies!")

if __name__ == "__main__":
    main()
