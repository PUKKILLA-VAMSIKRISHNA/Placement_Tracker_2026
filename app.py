from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from supabase import create_client, Client
import os
from datetime import datetime
# Password hashing removed as per request
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

# Validate required environment variables
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Test the connection
    supabase.table('companies').select('*').limit(1).execute()
except Exception as e:
    print(f"Error initializing Supabase client: {str(e)}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Supabase Key: {SUPABASE_KEY[:10]}...{SUPABASE_KEY[-10:] if SUPABASE_KEY else ''}")
    raise

@app.route('/')
def index():
    """Main page displaying all companies as cards"""
    try:
        # Fetch all companies from Supabase
        response = supabase.table('companies').select('*').execute()
        companies = response.data
        return render_template('index.html', companies=companies)
    except Exception as e:
        flash(f'Error loading companies: {str(e)}', 'error')
        return render_template('index.html', companies=[])

@app.route('/company/<company_id>')
def company_details(company_id):
    """Display detailed view of a specific company"""
    try:
        # Fetch company details
        company_response = supabase.table('companies').select('*').eq('id', company_id).execute()
        if not company_response.data:
            flash('Company not found', 'error')
            return redirect(url_for('index'))
        
        company = company_response.data[0]
        
        # Fetch selected students for this company
        students_response = supabase.table('selected_students').select('*').eq('company_id', company_id).execute()
        students = students_response.data
        
        return render_template('company_details.html', company=company, students=students)
    except Exception as e:
        flash(f'Error loading company details: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/admin')
def admin_login():
    """Admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/authenticate', methods=['POST'])
def admin_authenticate():
    """Handle admin authentication"""
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Hardcoded credentials for testing
    ADMIN_EMAIL = 'bhargavtheadmin@gmail.com'
    ADMIN_PASSWORD = 'Bhargav@123'
    
    print(f"\n=== Authentication Attempt ===")
    print(f"Email: {email}")
    print(f"Expected email: {ADMIN_EMAIL}")
    print(f"Password: {password}")
    print(f"Expected password: {ADMIN_PASSWORD}")
    
    try:
        # Bypass database check temporarily for testing
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_email'] = email
            flash('Login successful! (Using hardcoded credentials)', 'success')
            print("Authentication successful with hardcoded credentials!")
            return redirect(url_for('admin_dashboard'))
        else:
            print("Invalid credentials provided or You are an invalid user")
            
        # Original database check (kept for reference)
        try:
            print("\nAttempting database authentication...")
            response = supabase.table('admins').select('*').eq('email', email).execute()
            print(f"Database response: {response}")
            
            if response.data and response.data[0]['password_hash'] == password:
                session['admin_logged_in'] = True
                session['admin_email'] = email
                flash('Login successful! (Via database)', 'success')
                return redirect(url_for('admin_dashboard'))
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('admin_login'))
        
    except Exception as e:
        print(f"\nAuthentication error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred during authentication', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard with CRUD operations"""
    if not session.get('admin_logged_in'):
        flash('Please login to access admin panel', 'error')
        return redirect(url_for('admin_login'))
    
    try:
        # Fetch all companies for admin view
        companies_response = supabase.table('companies').select('*').execute()
        companies = companies_response.data
        
        return render_template('admin_dashboard.html', companies=companies)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin_dashboard.html', companies=[])

@app.route('/admin/add_company', methods=['GET', 'POST'])
def add_company():
    """Add new company"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            company_data = {
                'name': request.form.get('name'),
                'hiring_flow': request.form.get('hiring_flow'),
                'ctc_offer': request.form.get('ctc_offer'),
                'agreement_years': int(request.form.get('agreement_years')),
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('companies').insert(company_data).execute()
            flash('Company added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Error adding company: {str(e)}', 'error')
    
    return render_template('add_company.html')

@app.route('/admin/edit_company/<company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    """Edit existing company"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            company_data = {
                'name': request.form.get('name'),
                'hiring_flow': request.form.get('hiring_flow'),
                'ctc_offer': request.form.get('ctc_offer'),
                'agreement_years': int(request.form.get('agreement_years')),
                'updated_at': datetime.now().isoformat()
            }
            
            response = supabase.table('companies').update(company_data).eq('id', company_id).execute()
            flash('Company updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f'Error updating company: {str(e)}', 'error')
    
    try:
        # Fetch company details for editing
        response = supabase.table('companies').select('*').eq('id', company_id).execute()
        if not response.data:
            flash('Company not found', 'error')
            return redirect(url_for('admin_dashboard'))
        
        company = response.data[0]
        return render_template('edit_company.html', company=company)
    except Exception as e:
        flash(f'Error loading company: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_company/<company_id>', methods=['POST'])
def delete_company(company_id):
    """Delete company"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Delete associated students first
        supabase.table('selected_students').delete().eq('company_id', company_id).execute()
        # Delete company
        supabase.table('companies').delete().eq('id', company_id).execute()
        flash('Company deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting company: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_student/<company_id>', methods=['GET', 'POST'])
def add_student(company_id):
    """Add student to company"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            student_data = {
                'company_id': company_id,
                'name': request.form.get('name'),
                'student_number': request.form.get('student_number'),
                'linkedin_id': request.form.get('linkedin_id'),
                'max_round_reached': int(request.form.get('max_round_reached')),
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('selected_students').insert(student_data).execute()
            flash('Student added successfully!', 'success')
            return redirect(url_for('company_details', company_id=company_id))
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
    
    try:
        # Get company name for context
        company_response = supabase.table('companies').select('name').eq('id', company_id).execute()
        company_name = company_response.data[0]['name'] if company_response.data else 'Unknown'
        return render_template('add_student.html', company_id=company_id, company_name=company_name)
    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_student/<student_id>', methods=['POST'])
def delete_student(student_id):
    """Delete student"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Get company_id before deleting student
        student_response = supabase.table('selected_students').select('company_id').eq('id', student_id).execute()
        if student_response.data:
            company_id = student_response.data[0]['company_id']
            # Delete student
            supabase.table('selected_students').delete().eq('id', student_id).execute()
            flash('Student removed successfully!', 'success')
            return redirect(url_for('company_details', company_id=company_id))
        else:
            flash('Student not found', 'error')
            return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_email', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/developers')
def developers():
    """Display the developers page."""
    return render_template('developers.html')

# For Vercel deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
