from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, make_response, Response
from flask_mail import Mail, Message
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
# Password hashing removed as per request
from dotenv import load_dotenv
import uuid
import pandas as pd
from io import BytesIO
import base64
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import random
import re

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'placementtrackergmrit@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'placementtrackergmrit@gmail.com')

mail = Mail(app)

# File upload configuration for Supabase Storage
ALLOWED_EXTENSIONS = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Initialize Supabase client
supabase = None
supabase_admin = None  # For storage operations that require elevated permissions

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        # Regular client for database operations
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        # Admin client for storage operations (if service key is available)
        if SUPABASE_SERVICE_KEY:
            supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        else:
            print("Warning: SUPABASE_SERVICE_KEY not found. Storage operations may fail due to RLS policies.")
            supabase_admin = supabase  # Fallback to regular client
            
    except Exception as e:
        print(f"Error initializing Supabase client: {str(e)}")
        supabase = None
        supabase_admin = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def test_supabase_storage():
    """Test Supabase storage connection and bucket access"""
    try:
        if not supabase:
            return False, "Supabase client not initialized"
        
        # Try to list buckets to test connection
        buckets = supabase.storage.list_buckets()
        return True, f"Storage connection successful. Found {len(buckets)} buckets."
    except Exception as e:
        return False, f"Storage connection failed: {str(e)}"

@app.route('/')
def index():
    """Home page"""
    return render_template('home.html')

@app.route('/companies')
def companies():
    """Companies page - requires login (student or admin)"""
    # Check if user is logged in (either as student or admin)
    if 'user_id' not in session and 'student_id' not in session:
        flash('Please login to view placement companies.', 'warning')
        return redirect(url_for('index'))
    
    if not supabase:
        return render_template('index.html', companies=[])
    
    try:
        # Fetch all companies from Supabase
        response = supabase.table('companies').select('*').execute()
        companies_list = response.data
        return render_template('index.html', companies=companies_list)
    except Exception as e:
        flash(f'Error loading companies: {str(e)}', 'error')
        return render_template('index.html', companies=[])

def sort_students_by_priority(students):
    """Sort students by priority: Got Offer first, then by rounds descending, then Others last"""
    def get_sort_key(student):
        max_round = student['max_round_reached']
        
        # Priority 1: Students with "Got Offer" (highest priority = 0)
        if max_round == 'Got Offer':
            return (0, 0, student['name'])  # Sort by name as tiebreaker
        
        # Priority 3: Students with "Others" (lowest priority = 2)
        elif max_round == 'Others':
            return (2, 0, student['name'])  # Sort by name as tiebreaker
        
        # Priority 2: Students with rounds (middle priority = 1)
        elif max_round.startswith('Round '):
            try:
                # Extract round number for descending sort
                round_num = int(max_round.split(' ')[1])
                return (1, -round_num, student['name'])  # Negative for descending order
            except (ValueError, IndexError):
                # If round parsing fails, treat as Others
                return (2, 0, student['name'])
        
        # Default case: treat as Others
        else:
            return (2, 0, student['name'])
    
    return sorted(students, key=get_sort_key)

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
        
        # Sort students by priority: Got Offer first, then by rounds descending, then Others last
        students = sort_students_by_priority(students)
        
        # Fetch model papers for this company
        model_papers_response = supabase.table('model_papers').select('*').eq('company_id', company_id).execute()
        model_papers = model_papers_response.data
        
        return render_template('company_details.html', company=company, students=students, model_papers=model_papers)
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
            # Get hiring rounds as a comma-separated string from the form (step-wise input will be handled in the form later)
            # Collect all hiring_rounds fields and join into a comma-separated string
            rounds_list = request.form.getlist('hiring_rounds')
            hiring_rounds = ','.join([r.strip() for r in rounds_list if r.strip()])
            company_data = {
                'name': request.form.get('name'),
                'hiring_rounds': hiring_rounds,
                'ctc_offer': request.form.get('ctc_offer'),
                'agreement_years': float(request.form.get('agreement_years')),
                'logo_url': request.form.get('logo_url'),
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
            # Get hiring rounds as a comma-separated string from the form (step-wise input will be handled in the form later)
            rounds_list = request.form.getlist('hiring_rounds')
            hiring_rounds = ','.join([r.strip() for r in rounds_list if r.strip()])
            company_data = {
                'name': request.form.get('name'),
                'hiring_rounds': hiring_rounds,
                'ctc_offer': request.form.get('ctc_offer'),
                'agreement_years': float(request.form.get('agreement_years')),
                'logo_url': request.form.get('logo_url'),
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
            student_number = request.form.get('student_number')
            
            # Check for duplicate student by roll number within the same company
            existing_student = supabase.table('selected_students').select('*').eq('student_number', student_number).eq('company_id', company_id).execute()
            if existing_student.data:
                flash(f'Student with roll number {student_number} already exists in this company!', 'error')
                # Get company info for form reload
                company_response = supabase.table('companies').select('name, hiring_rounds').eq('id', company_id).execute()
                if company_response.data:
                    company_name = company_response.data[0]['name']
                    hiring_rounds_str = company_response.data[0].get('hiring_rounds', '')
                    company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
                else:
                    company_name = 'Unknown'
                    company_rounds = []
                return render_template('add_student.html', company_id=company_id, company_name=company_name, company_rounds=company_rounds)
            
            student_data = {
                'company_id': company_id,
                'name': request.form.get('name'),
                'student_number': student_number,
                'email': request.form.get('email'),
                'linkedin_id': request.form.get('linkedin_id'),
                'max_round_reached': request.form.get('max_round_reached'),
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('selected_students').insert(student_data).execute()
            flash('Student added successfully!', 'success')
            return redirect(url_for('company_details', company_id=company_id))
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
    
    try:
        # Get company name and rounds for context
        company_response = supabase.table('companies').select('name, hiring_rounds').eq('id', company_id).execute()
        if company_response.data:
            company_name = company_response.data[0]['name']
            hiring_rounds_str = company_response.data[0].get('hiring_rounds', '')
            company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
        else:
            company_name = 'Unknown'
            company_rounds = []
        return render_template('add_student.html', company_id=company_id, company_name=company_name, company_rounds=company_rounds)
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

@app.route('/admin/reports')
def admin_reports():
    """Admin reports dashboard"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Fetch all companies with student counts
        companies_response = supabase.table('companies').select('*').execute()
        companies = companies_response.data
        
        # Fetch all students
        students_response = supabase.table('selected_students').select('*').execute()
        students = students_response.data
        
        # Calculate statistics - count unique students only
        total_companies = len(companies)
        unique_students = set()
        for student in students:
            unique_students.add(student['student_number'])
        total_unique_students = len(unique_students)
        
        # Count total offers (unique students who got offers)
        unique_offer_students = set()
        for student in students:
            if student['max_round_reached'] == 'Got Offer':
                unique_offer_students.add(student['student_number'])
        total_got_offers = len(unique_offer_students)
        
        # Group students by company and calculate round-wise statistics
        company_stats = {}
        for student in students:
            company_id = student['company_id']
            if company_id not in company_stats:
                company_stats[company_id] = {
                    'students': [],
                    'got_offer': 0,
                    'round_stats': {}
                }
            company_stats[company_id]['students'].append(student)
            
            # Count by status
            if student['max_round_reached'] == 'Got Offer':
                company_stats[company_id]['got_offer'] += 1
            
            # Count round-wise statistics
            round_reached = student['max_round_reached']
            if round_reached not in ['Got Offer']:
                if round_reached not in company_stats[company_id]['round_stats']:
                    company_stats[company_id]['round_stats'][round_reached] = 0
                company_stats[company_id]['round_stats'][round_reached] += 1
        
        # Add company details to stats and calculate hiring round statistics
        for company in companies:
            company_id = company['id']
            if company_id not in company_stats:
                company_stats[company_id] = {
                    'company': company,
                    'students': [],
                    'got_offer': 0,
                    'round_stats': {}
                }
            else:
                company_stats[company_id]['company'] = company
            
            # Sort students within each company by priority
            if company_stats[company_id]['students']:
                company_stats[company_id]['students'] = sort_students_by_priority(company_stats[company_id]['students'])
            
            # Parse hiring rounds for this company
            hiring_rounds_str = company.get('hiring_rounds', '')
            company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
            company_stats[company_id]['hiring_rounds'] = company_rounds
        
        # Get list of students with offers for modal display
        students_with_offers = []
        unique_students_with_offers = []
        seen_student_numbers = set()
        
        for student in students:
            if student['max_round_reached'] == 'Got Offer':
                students_with_offers.append(student)
                # Add to unique list only if not seen before
                if student['student_number'] not in seen_student_numbers:
                    unique_students_with_offers.append(student)
                    seen_student_numbers.add(student['student_number'])
        
        # Sort both lists by student name for consistent display
        students_with_offers = sorted(students_with_offers, key=lambda x: x['name'])
        unique_students_with_offers = sorted(unique_students_with_offers, key=lambda x: x['name'])
        
        return render_template('admin_reports.html', 
                             companies=companies, 
                             students=students,
                             company_stats=company_stats,
                             total_companies=total_companies,
                             total_students=total_unique_students,
                             total_got_offers=total_got_offers,
                             students_with_offers=students_with_offers,
                             unique_students_with_offers=unique_students_with_offers)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return render_template('admin_reports.html', 
                             companies=[], 
                             students=[],
                             company_stats={},
                             total_companies=0,
                             total_students=0,
                             total_got_offers=0)

@app.route('/admin/reports/download/<format>')
def download_report(format):
    """Download reports in Excel or PDF format"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Fetch data
        companies_response = supabase.table('companies').select('*').execute()
        companies = companies_response.data
        
        students_response = supabase.table('selected_students').select('*').execute()
        students = students_response.data
        
        if format.lower() == 'excel':
            return generate_excel_report(companies, students)
        elif format.lower() == 'pdf':
            return generate_pdf_report(companies, students)
        else:
            flash('Invalid format requested', 'error')
            return redirect(url_for('admin_reports'))
            
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('admin_reports'))

def generate_excel_report(companies, students):
    """Generate Excel report with attractive formatting"""
    output = BytesIO()
    
    # Create workbook and worksheets
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'font_size': 12
        })
        
        metric_format = workbook.add_format({
            'bold': True,
            'fg_color': '#D9E1F2',
            'border': 1,
            'font_size': 11
        })
        
        value_format = workbook.add_format({
            'border': 1,
            'font_size': 11,
            'text_wrap': True
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'font_size': 11,
            'num_format': '#,##0'
        })
        
        success_format = workbook.add_format({
            'border': 1,
            'font_size': 11,
            'fg_color': '#C6EFCE',
            'num_format': '#,##0'
        })
        
        # Calculate overall statistics
        unique_students = set(s['student_number'] for s in students)
        unique_offer_students = set(s['student_number'] for s in students if s['max_round_reached'] == 'Got Offer')
        total_got_offers = len([s for s in students if s['max_round_reached'] == 'Got Offer'])
        
        # 1. Overall Statistics Sheet
        overall_stats_data = [
            ['Total No of Companies', len(companies)],
            ['All Company Names', ', '.join([c['name'] for c in companies])],
            ['Total No of Students', len(unique_students)],  # Fixed: Use unique student count
            ['Total Got Offers', total_got_offers],
            ['Total Unique Students with Offers', len(unique_offer_students)]
        ]
        overall_df = pd.DataFrame(overall_stats_data, columns=['Metric', 'Value'])
        overall_df.to_excel(writer, sheet_name='Overall_Statistics', index=False, startrow=1)
        
        # Format Overall Statistics sheet
        worksheet = writer.sheets['Overall_Statistics']
        worksheet.write('A1', 'Overall Placement Statistics', header_format)
        worksheet.merge_range('A1:B1', 'Overall Placement Statistics', header_format)
        
        # Apply formatting to data
        for row in range(len(overall_stats_data)):
            worksheet.write(row + 2, 0, overall_stats_data[row][0], metric_format)
            if row == 3 or row == 4:  # Offers data
                worksheet.write(row + 2, 1, overall_stats_data[row][1], success_format)
            else:
                worksheet.write(row + 2, 1, overall_stats_data[row][1], value_format)
        
        # Set column widths
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 50)
        
        # 2. Company-wise Statistics Sheet
        company_stats_data = []
        for company in companies:
            company_students = [s for s in students if s['company_id'] == company['id']]
            got_offer_count = len([s for s in company_students if s['max_round_reached'] == 'Got Offer'])
            
            # Parse hiring rounds for this company
            hiring_rounds_str = company.get('hiring_rounds', '')
            company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
            
            # Count students in each round
            round_stats = []
            for i, round_name in enumerate(company_rounds, 1):
                round_key = f'Round {i}'
                count = len([s for s in company_students if s['max_round_reached'] == round_key])
                if count > 0:
                    round_stats.append(f'{round_name}: {count}')
            
            company_stats_data.append({
                'Company Name': company['name'],
                'CTC': company['ctc_offer'],
                'Bond/Agreement (Years)': company['agreement_years'],
                'Round-wise Student Count': '; '.join(round_stats) if round_stats else 'No round data',
                'No of Students Got Offers': got_offer_count
            })
        
        company_stats_df = pd.DataFrame(company_stats_data)
        company_stats_df.to_excel(writer, sheet_name='Company_Statistics', index=False, startrow=1)
        
        # Format Company Statistics sheet
        company_worksheet = writer.sheets['Company_Statistics']
        company_worksheet.merge_range('A1:E1', 'Company-wise Placement Statistics', header_format)
        
        # Write headers with formatting
        headers = ['Company Name', 'CTC', 'Bond/Agreement (Years)', 'Round-wise Student Count', 'No of Students Got Offers']
        for col, header in enumerate(headers):
            company_worksheet.write(1, col, header, header_format)
        
        # Apply formatting to data rows
        for row in range(len(company_stats_data)):
            company_worksheet.write(row + 2, 0, company_stats_data[row]['Company Name'], value_format)
            company_worksheet.write(row + 2, 1, company_stats_data[row]['CTC'], value_format)
            company_worksheet.write(row + 2, 2, company_stats_data[row]['Bond/Agreement (Years)'], number_format)
            company_worksheet.write(row + 2, 3, company_stats_data[row]['Round-wise Student Count'], value_format)
            company_worksheet.write(row + 2, 4, company_stats_data[row]['No of Students Got Offers'], success_format)
        
        # Set column widths
        company_worksheet.set_column('A:A', 25)  # Company Name
        company_worksheet.set_column('B:B', 15)  # CTC
        company_worksheet.set_column('C:C', 20)  # Bond/Agreement
        company_worksheet.set_column('D:D', 40)  # Round-wise
        company_worksheet.set_column('E:E', 20)  # Got Offers
        
        # 3. Detailed Student Information (Company-wise)
        student_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#70AD47',
            'font_color': 'white',
            'border': 1,
            'font_size': 11
        })
        
        student_data_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'text_wrap': True
        })
        
        offer_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'fg_color': '#C6EFCE',
            'text_wrap': True
        })
        
        for company in companies:
            company_students = [s for s in students if s['company_id'] == company['id']]
            if company_students:
                # Sort students by priority: Got Offer first, then by rounds descending, then Others last
                company_students = sort_students_by_priority(company_students)
                student_details = []
                for student in company_students:
                    student_details.append({
                        'Student Name': student['name'],
                        'Roll No': student['student_number'],
                        'Email ID': student.get('email', 'N/A'),
                        'Max Round Reached/Got Offer': student['max_round_reached']
                    })
                
                student_df = pd.DataFrame(student_details)
                # Clean company name for sheet name (Excel sheet names have character limits)
                safe_company_name = company['name'].replace('/', '_').replace('\\', '_')[:25]
                student_df.to_excel(writer, sheet_name=f'{safe_company_name}_Students', index=False, startrow=1)
                
                # Format student sheets
                student_worksheet = writer.sheets[f'{safe_company_name}_Students']
                student_worksheet.merge_range('A1:D1', f'{company["name"]} - Student Details', header_format)
                
                # Write headers with formatting
                student_headers = ['Student Name', 'Roll No', 'Email ID', 'Max Round Reached/Got Offer']
                for col, header in enumerate(student_headers):
                    student_worksheet.write(1, col, header, student_header_format)
                
                # Apply formatting to data rows
                for row in range(len(student_details)):
                    student_worksheet.write(row + 2, 0, student_details[row]['Student Name'], student_data_format)
                    student_worksheet.write(row + 2, 1, student_details[row]['Roll No'], student_data_format)
                    student_worksheet.write(row + 2, 2, student_details[row]['Email ID'], student_data_format)
                    
                    # Highlight "Got Offer" status
                    if student_details[row]['Max Round Reached/Got Offer'] == 'Got Offer':
                        student_worksheet.write(row + 2, 3, student_details[row]['Max Round Reached/Got Offer'], offer_format)
                    else:
                        student_worksheet.write(row + 2, 3, student_details[row]['Max Round Reached/Got Offer'], student_data_format)
                
                # Set column widths
                student_worksheet.set_column('A:A', 25)  # Student Name
                student_worksheet.set_column('B:B', 15)  # Roll No
                student_worksheet.set_column('C:C', 30)  # Email ID
                student_worksheet.set_column('D:D', 25)  # Max Round
        
        # 4. All Students with Offers Sheet
        students_with_offers = [s for s in students if s['max_round_reached'] == 'Got Offer']
        if students_with_offers:
            offers_data = []
            for student in students_with_offers:
                # Find company name
                company_name = 'Unknown'
                for company in companies:
                    if company['id'] == student['company_id']:
                        company_name = company['name']
                        break
                
                offers_data.append({
                    'Student Name': student['name'],
                    'Roll No': student['student_number'],
                    'Email ID': student.get('email', 'N/A'),
                    'Company': company_name
                })
            
            offers_df = pd.DataFrame(offers_data)
            offers_df.to_excel(writer, sheet_name='All_Students_With_Offers', index=False, startrow=1)
            
            # Format All Students with Offers sheet
            offers_worksheet = writer.sheets['All_Students_With_Offers']
            offers_worksheet.merge_range('A1:D1', f'All Students with Offers ({len(students_with_offers)})', header_format)
            
            # Write headers
            offers_headers = ['Student Name', 'Roll No', 'Email ID', 'Company']
            for col, header in enumerate(offers_headers):
                offers_worksheet.write(1, col, header, student_header_format)
            
            # Apply formatting to data rows
            for row in range(len(offers_data)):
                offers_worksheet.write(row + 2, 0, offers_data[row]['Student Name'], offer_format)
                offers_worksheet.write(row + 2, 1, offers_data[row]['Roll No'], offer_format)
                offers_worksheet.write(row + 2, 2, offers_data[row]['Email ID'], offer_format)
                offers_worksheet.write(row + 2, 3, offers_data[row]['Company'], offer_format)
            
            # Set column widths
            offers_worksheet.set_column('A:A', 25)  # Student Name
            offers_worksheet.set_column('B:B', 15)  # Roll No
            offers_worksheet.set_column('C:C', 30)  # Email ID
            offers_worksheet.set_column('D:D', 25)  # Company
        
        # 5. Unique Students with Offers Sheet
        unique_students_with_offers = []
        seen_student_numbers = set()
        for student in students:
            if student['max_round_reached'] == 'Got Offer' and student['student_number'] not in seen_student_numbers:
                # Find company name
                company_name = 'Unknown'
                for company in companies:
                    if company['id'] == student['company_id']:
                        company_name = company['name']
                        break
                
                unique_students_with_offers.append({
                    'Student Name': student['name'],
                    'Roll No': student['student_number'],
                    'Email ID': student.get('email', 'N/A'),
                    'Company': company_name
                })
                seen_student_numbers.add(student['student_number'])
        
        if unique_students_with_offers:
            unique_df = pd.DataFrame(unique_students_with_offers)
            unique_df.to_excel(writer, sheet_name='Unique_Students_With_Offers', index=False, startrow=1)
            
            # Format Unique Students with Offers sheet
            unique_worksheet = writer.sheets['Unique_Students_With_Offers']
            unique_worksheet.merge_range('A1:D1', f'Unique Students with Offers ({len(unique_students_with_offers)})', header_format)
            
            # Write headers
            unique_headers = ['Student Name', 'Roll No', 'Email ID', 'Company']
            for col, header in enumerate(unique_headers):
                unique_worksheet.write(1, col, header, student_header_format)
            
            # Apply formatting to data rows
            for row in range(len(unique_students_with_offers)):
                unique_worksheet.write(row + 2, 0, unique_students_with_offers[row]['Student Name'], offer_format)
                unique_worksheet.write(row + 2, 1, unique_students_with_offers[row]['Roll No'], offer_format)
                unique_worksheet.write(row + 2, 2, unique_students_with_offers[row]['Email ID'], offer_format)
                unique_worksheet.write(row + 2, 3, unique_students_with_offers[row]['Company'], offer_format)
            
            # Set column widths
            unique_worksheet.set_column('A:A', 25)  # Student Name
            unique_worksheet.set_column('B:B', 15)  # Roll No
            unique_worksheet.set_column('C:C', 30)  # Email ID
            unique_worksheet.set_column('D:D', 25)  # Company
    
    output.seek(0)
    
    response = make_response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=placement_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

def generate_pdf_report(companies, students):
    """Generate PDF report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    story.append(Paragraph("IT Branch 2026 Placements Report", title_style))
    story.append(Spacer(1, 15))
    
    # Calculate overall statistics
    unique_students = set(s['student_number'] for s in students)
    unique_offer_students = set(s['student_number'] for s in students if s['max_round_reached'] == 'Got Offer')
    total_got_offers = len([s for s in students if s['max_round_reached'] == 'Got Offer'])
    
    # 1. Overall Statistics
    story.append(Paragraph("Overall Statistics", styles['Heading2']))
    
    # Create proper paragraph for company names without truncation
    company_names_text = ', '.join([c['name'] for c in companies])
    
    # Create style for summary data
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='LTR'
    )
    
    summary_data = [
        ['Total No of Companies', str(len(companies))],
        ['All Company Names', Paragraph(company_names_text, summary_style)],
        ['Total No of Students', str(len(unique_students))],  # Fixed: Use unique student count
        ['Total Got Offers', str(total_got_offers)],
        ['Total Unique Students with Offers', str(len(unique_offer_students))]
    ]
    
    summary_table = Table(summary_data, colWidths=[2.2*inch, 3.3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # 2. Company-wise Statistics and Student Details
    for company in companies:
        company_students = [s for s in students if s['company_id'] == company['id']]
        # Sort students by priority: Got Offer first, then by rounds descending, then Others last
        company_students = sort_students_by_priority(company_students)
        got_offer_count = len([s for s in company_students if s['max_round_reached'] == 'Got Offer'])
        
        # Company header
        story.append(Paragraph(f"Company: {company['name']}", styles['Heading2']))
        
        # Company statistics
        hiring_rounds_str = company.get('hiring_rounds', '')
        company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
        
        # Count students in each round
        round_stats = []
        for i, round_name in enumerate(company_rounds, 1):
            round_key = f'Round {i}'
            count = len([s for s in company_students if s['max_round_reached'] == round_key])
            if count > 0:
                round_stats.append(f'{round_name}: {count}')
        
        # Create proper paragraph for round statistics without truncation
        round_stats_text = '; '.join(round_stats) if round_stats else 'No round data'
        
        # Create a custom style for better text wrapping
        wrap_style = ParagraphStyle(
            'WrapStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='LTR'
        )
        
        company_info = [
            ['CTC', company['ctc_offer']],
            ['Bond/Agreement', f"{company['agreement_years']} years"],
            ['Round-wise Students', Paragraph(round_stats_text, wrap_style)],
            ['Students Got Offers', str(got_offer_count)]
        ]
        
        company_table = Table(company_info, colWidths=[1.8*inch, 3.7*inch])
        company_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(company_table)
        story.append(Spacer(1, 15))
        
        # Student details for this company
        if company_students:
            story.append(Paragraph("Student Details:", styles['Heading3']))
            
            student_data = [['Student Name', 'Roll No', 'Email ID', 'Max Round/Offer']]
            
            # Create style for student data with proper wrapping
            student_style = ParagraphStyle(
                'StudentStyle',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
                wordWrap='LTR'
            )
            
            for student in company_students:
                # Use full data without truncation, let Paragraph handle wrapping
                student_name = student['name']
                student_email = student.get('email', 'N/A')
                max_round = student['max_round_reached']
                
                student_data.append([
                    Paragraph(student_name, student_style),
                    student['student_number'],
                    Paragraph(student_email, student_style),
                    Paragraph(max_round, student_style)
                ])
            
            # Adjust column widths for better data display
            student_table = Table(student_data, colWidths=[1.6*inch, 0.9*inch, 1.8*inch, 1.2*inch])
            student_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightblue])
            ]))
            story.append(student_table)
        
        story.append(Spacer(1, 30))
    
    # Add new sections for student lists
    story.append(PageBreak())
    
    # All Students with Offers Section
    students_with_offers = [s for s in students if s['max_round_reached'] == 'Got Offer']
    if students_with_offers:
        story.append(Paragraph("All Students with Offers", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        offers_data = [['Student Name', 'Roll No', 'Email ID', 'Company']]
        
        for student in students_with_offers:
            # Find company name
            company_name = 'Unknown'
            for company in companies:
                if company['id'] == student['company_id']:
                    company_name = company['name']
                    break
            
            offers_data.append([
                Paragraph(student['name'], student_style),
                student['student_number'],
                Paragraph(student.get('email', 'N/A'), student_style),
                Paragraph(company_name, student_style)
            ])
        
        offers_table = Table(offers_data, colWidths=[1.8*inch, 1.0*inch, 1.8*inch, 1.9*inch])
        offers_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightyellow])
        ]))
        story.append(offers_table)
        story.append(Spacer(1, 20))
    
    # Unique Students with Offers Section
    unique_students_with_offers = []
    seen_student_numbers = set()
    for student in students:
        if student['max_round_reached'] == 'Got Offer' and student['student_number'] not in seen_student_numbers:
            unique_students_with_offers.append(student)
            seen_student_numbers.add(student['student_number'])
    
    if unique_students_with_offers:
        story.append(Paragraph("Unique Students with Offers", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        unique_data = [['Student Name', 'Roll No', 'Email ID', 'Company']]
        
        for student in unique_students_with_offers:
            # Find company name
            company_name = 'Unknown'
            for company in companies:
                if company['id'] == student['company_id']:
                    company_name = company['name']
                    break
            
            unique_data.append([
                Paragraph(student['name'], student_style),
                student['student_number'],
                Paragraph(student.get('email', 'N/A'), student_style),
                Paragraph(company_name, student_style)
            ])
        
        unique_table = Table(unique_data, colWidths=[1.8*inch, 1.0*inch, 1.8*inch, 1.9*inch])
        unique_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightblue])
        ]))
        story.append(unique_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=placement_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

@app.route('/admin/test_storage')
def test_storage():
    """Test route to check Supabase storage connection"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    success, message = test_supabase_storage()
    if success:
        flash(f'Storage Test: {message}', 'success')
    else:
        flash(f'Storage Test Failed: {message}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload_model_paper/<company_id>', methods=['POST'])
def upload_model_paper(company_id):
    """Upload model paper for a company using Supabase Storage"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        if 'model_paper' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('company_details', company_id=company_id))
        
        file = request.files['model_paper']
        paper_name = request.form.get('paper_name', '').strip()
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('company_details', company_id=company_id))
        
        if not paper_name:
            flash('Please provide a name for the model paper', 'error')
            return redirect(url_for('company_details', company_id=company_id))
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create unique filename to avoid conflicts
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Read file content into memory
            file_content = file.read()
            file_size = len(file_content)
            
            # Reset file pointer and create BytesIO object for alternative upload methods
            file_bytes = BytesIO(file_content)
            
            # Upload to Supabase Storage
            try:
                # Upload file to Supabase Storage bucket 'model-papers'
                # Try multiple method signatures for different Supabase client versions
                try:
                    # Method 1: Latest Supabase client (using admin client for storage)
                    storage_client = supabase_admin if supabase_admin else supabase
                    storage_response = storage_client.storage.from_('model-papers').upload(
                        file=file_content,
                        path=unique_filename,
                        file_options={
                            'content-type': 'application/pdf',
                            'cache-control': '3600'
                        }
                    )
                except Exception as method1_error:
                    print(f"Method 1 failed: {str(method1_error)}")
                    try:
                        # Method 2: Alternative signature
                        storage_response = storage_client.storage.from_('model-papers').upload(
                            path=unique_filename,
                            file=file_content,
                            file_options={
                                'content-type': 'application/pdf'
                            }
                        )
                    except Exception as method2_error:
                        print(f"Method 2 failed: {str(method2_error)}")
                        try:
                            # Method 3: Simple signature
                            storage_response = storage_client.storage.from_('model-papers').upload(
                                unique_filename,
                                file_content
                            )
                        except Exception as method3_error:
                            print(f"Method 3 failed: {str(method3_error)}")
                            try:
                                # Method 4: Using BytesIO object
                                storage_response = storage_client.storage.from_('model-papers').upload(
                                    unique_filename,
                                    file_bytes
                                )
                            except Exception as method4_error:
                                print(f"Method 4 failed: {str(method4_error)}")
                                # Method 5: Base64 encoded string (last resort)
                                file_base64 = base64.b64encode(file_content).decode('utf-8')
                                storage_response = storage_client.storage.from_('model-papers').upload(
                                    unique_filename,
                                    file_base64,
                                    {'content-type': 'application/pdf'}
                                )
                
                # Get public URL for the uploaded file
                public_url = storage_client.storage.from_('model-papers').get_public_url(unique_filename)
                
                # Save to database
                model_paper_data = {
                    'company_id': company_id,
                    'paper_name': paper_name,
                    'file_url': public_url,
                    'file_size': file_size,
                    'uploaded_by': session.get('admin_email'),
                    'created_at': datetime.now().isoformat()
                }
                
                supabase.table('model_papers').insert(model_paper_data).execute()
                flash('Model paper uploaded successfully!', 'success')
                
            except Exception as storage_error:
                print(f"Initial storage upload failed: {str(storage_error)}")
                # Fallback: try creating bucket if it doesn't exist
                try:
                    storage_client.storage.create_bucket('model-papers', {
                        'public': True,
                        'file_size_limit': 16777216,  # 16MB
                        'allowed_mime_types': ['application/pdf']
                    })
                    
                    # Retry upload after creating bucket
                    # Try multiple method signatures for different Supabase client versions
                    try:
                        # Method 1: Latest Supabase client
                        storage_response = storage_client.storage.from_('model-papers').upload(
                            file=file_content,
                            path=unique_filename,
                            file_options={
                                'content-type': 'application/pdf',
                                'cache-control': '3600'
                            }
                        )
                    except Exception as retry_method1_error:
                        print(f"Retry Method 1 failed: {str(retry_method1_error)}")
                        try:
                            # Method 2: Alternative signature
                            storage_response = storage_client.storage.from_('model-papers').upload(
                                path=unique_filename,
                                file=file_content,
                                file_options={
                                    'content-type': 'application/pdf'
                                }
                            )
                        except Exception as retry_method2_error:
                            print(f"Retry Method 2 failed: {str(retry_method2_error)}")
                            try:
                                # Method 3: Simple signature
                                storage_response = storage_client.storage.from_('model-papers').upload(
                                    unique_filename,
                                    file_content
                                )
                            except Exception as retry_method3_error:
                                print(f"Retry Method 3 failed: {str(retry_method3_error)}")
                                try:
                                    # Method 4: Using BytesIO object
                                    storage_response = storage_client.storage.from_('model-papers').upload(
                                        unique_filename,
                                        file_bytes
                                    )
                                except Exception as retry_method4_error:
                                    print(f"Retry Method 4 failed: {str(retry_method4_error)}")
                                    try:
                                        # Method 5: Base64 encoded string (last resort)
                                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                                        storage_response = storage_client.storage.from_('model-papers').upload(
                                            unique_filename,
                                            file_base64,
                                            {'content-type': 'application/pdf'}
                                        )
                                    except Exception as retry_method5_error:
                                        print(f"Retry Method 5 failed: {str(retry_method5_error)}")
                                        
                    
                    public_url = storage_client.storage.from_('model-papers').get_public_url(unique_filename)
                    
                    model_paper_data = {
                        'company_id': company_id,
                        'paper_name': paper_name,
                        'file_url': public_url,
                        'file_size': file_size,
                        'uploaded_by': session.get('admin_email'),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    supabase.table('model_papers').insert(model_paper_data).execute()
                    flash('Model paper uploaded successfully!', 'success')
                    
                except Exception as retry_error:
                    flash(f'Error uploading to cloud storage: {str(retry_error)}', 'error')
                    
        else:
            flash('Invalid file type. Only PDF files are allowed.', 'error')
            
    except Exception as e:
        flash(f'Error uploading model paper: {str(e)}', 'error')
    
    return redirect(url_for('company_details', company_id=company_id))

@app.route('/admin/delete_model_paper/<paper_id>', methods=['POST'])
def delete_model_paper(paper_id):
    """Delete model paper from Supabase Storage"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Get paper details first
        paper_response = supabase.table('model_papers').select('*').eq('id', paper_id).execute()
        if paper_response.data:
            paper = paper_response.data[0]
            company_id = paper['company_id']
            
            # Extract filename from URL for Supabase Storage deletion
            file_url = paper['file_url']
            if 'model-papers' in file_url:
                # Extract filename from Supabase Storage URL
                filename = file_url.split('/')[-1]
                try:
                    # Delete file from Supabase Storage
                    supabase.storage.from_('model-papers').remove([filename])
                except Exception as storage_error:
                    print(f"Warning: Could not delete file from storage: {str(storage_error)}")
                    # Continue with database deletion even if file deletion fails
            
            # Delete from database
            supabase.table('model_papers').delete().eq('id', paper_id).execute()
            flash('Model paper deleted successfully!', 'success')
            return redirect(url_for('company_details', company_id=company_id))
        else:
            flash('Model paper not found', 'error')
            return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error deleting model paper: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/uploads/model_papers/<filename>')
def download_model_paper(filename):
    """Download model paper - redirect to Supabase Storage URL"""
    try:
        # For Supabase Storage, we'll redirect to the public URL
        # The file_url in database already contains the full public URL
        paper_response = supabase.table('model_papers').select('file_url, paper_name').like('file_url', f'%{filename}%').execute()
        if paper_response.data:
            file_url = paper_response.data[0]['file_url']
            return redirect(file_url)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/admin/edit_student/<student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student details"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Fetch student info
    student_response = supabase.table('selected_students').select('*').eq('id', student_id).execute()
    if not student_response.data:
        flash('Student not found', 'error')
        return redirect(url_for('admin_dashboard'))
    student = student_response.data[0]

    # Fetch company info for rounds
    company_id = student['company_id']
    company_response = supabase.table('companies').select('name, hiring_rounds').eq('id', company_id).execute()
    if company_response.data:
        company_name = company_response.data[0]['name']
        hiring_rounds_str = company_response.data[0].get('hiring_rounds', '')
        company_rounds = [r.strip() for r in hiring_rounds_str.split(',') if r.strip()]
    else:
        company_name = 'Unknown'
        company_rounds = []

    if request.method == 'POST':
        try:
            new_student_number = request.form.get('student_number')
            
            # Check for duplicate student number within the same company (only if student number is being changed)
            if new_student_number != student['student_number']:
                existing_student = supabase.table('selected_students').select('*').eq('student_number', new_student_number).eq('company_id', company_id).execute()
                if existing_student.data:
                    flash(f'Student with roll number {new_student_number} already exists in this company!', 'error')
                    return render_template('edit_student.html', student=student, company_id=company_id, company_name=company_name, company_rounds=company_rounds)
            
            update_data = {
                'name': request.form.get('name'),
                'student_number': new_student_number,
                'email': request.form.get('email'),
                'linkedin_id': request.form.get('linkedin_id'),
                'max_round_reached': request.form.get('max_round_reached'),
                'updated_at': datetime.now().isoformat()
            }
            supabase.table('selected_students').update(update_data).eq('id', student_id).execute()
            flash('Student updated successfully!', 'success')
            return redirect(url_for('company_details', company_id=company_id))
        except Exception as e:
            flash(f'Error updating student: {str(e)}', 'error')

    return render_template('edit_student.html', student=student, company_id=company_id, company_name=company_name, company_rounds=company_rounds)

# SEO Routes
@app.route('/sitemap.xml')
def sitemap():
    """Generate dynamic sitemap for SEO"""
    try:
        # Get all companies for dynamic URLs
        companies_response = supabase.table('companies').select('id, name, updated_at').execute()
        companies = companies_response.data
        
        # Base URL (you should replace this with your actual domain)
        base_url = request.url_root.rstrip('/')
        
        # Generate sitemap XML
        sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{base_url}/developers</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>'''.format(base_url=base_url, lastmod=datetime.now().strftime('%Y-%m-%d'))
        
        # Add company pages
        for company in companies:
            company_lastmod = company.get('updated_at', company.get('created_at', datetime.now().isoformat()))
            try:
                # Parse the datetime string and format it for sitemap
                if isinstance(company_lastmod, str):
                    company_date = datetime.fromisoformat(company_lastmod.replace('Z', '+00:00'))
                    formatted_date = company_date.strftime('%Y-%m-%d')
                else:
                    formatted_date = datetime.now().strftime('%Y-%m-%d')
            except:
                formatted_date = datetime.now().strftime('%Y-%m-%d')
            
            sitemap_xml += '''
    <url>
        <loc>{base_url}/company/{company_id}</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>'''.format(base_url=base_url, company_id=company['id'], lastmod=formatted_date)
        
        sitemap_xml += '''
</urlset>'''
        
        response = Response(sitemap_xml, mimetype='application/xml')
        return response
        
    except Exception as e:
        # Return basic sitemap if database error
        basic_sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>'''.format(base_url=request.url_root.rstrip('/'), lastmod=datetime.now().strftime('%Y-%m-%d'))
        
        return Response(basic_sitemap, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    """Generate robots.txt for search engine crawlers"""
    base_url = request.url_root.rstrip('/')
    
    robots_txt = '''User-agent: *
Allow: /
Allow: /company/*
Allow: /developers
Disallow: /admin*
Disallow: /uploads/*

# Sitemap location
Sitemap: {base_url}/sitemap.xml

# Crawl delay (optional)
Crawl-delay: 1'''.format(base_url=base_url)
    
    return Response(robots_txt, mimetype='text/plain')

# ============================================
# STUDENT AUTHENTICATION ROUTES
# ============================================

def validate_gmrit_email(email):
    """Validate GMRIT email format: XX34XA12XX@gmrit.edu.in (where X = digit 0-9)"""
    pattern = r'^\d{2}34\d[aA]12\d{2}@gmrit\.edu\.in$'
    return re.match(pattern, email) is not None

def validate_student_number(student_number):
    """Validate student number format: XX34XA12XX (where X = digit 0-9)"""
    pattern = r'^\d{2}34\d[aA]12\d{2}$'
    return re.match(pattern, student_number) is not None

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    """Send OTP email to student"""
    try:
        print(f"Attempting to send email to: {email}")
        print(f"Using MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
        print(f"Using MAIL_SERVER: {app.config['MAIL_SERVER']}")
        
        msg = Message(
            'Password Reset OTP - Placement Tracker',
            recipients=[email]
        )
        msg.body = f'''Hello,

You have requested to reset your password for the Placement Tracker system.

Your OTP is: {otp}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Best regards,
Placement Tracker Team
GMRIT'''
        
        mail.send(msg)
        print(f"Email sent successfully to {email}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    """Student registration page"""
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name', '').strip()
            student_number = request.form.get('student_number', '').strip().upper()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([full_name, student_number, email, password, confirm_password]):
                flash('All fields are required!', 'error')
                return render_template('student_register.html')
            
            if not validate_gmrit_email(email):
                flash('Invalid email format! Must be XX34XA12XX@gmrit.edu.in (where X is a digit)', 'error')
                return render_template('student_register.html')
            
            if not validate_student_number(student_number):
                flash('Invalid student number format! Must be XX34XA12XX (where X is a digit)', 'error')
                return render_template('student_register.html')
            
            if password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('student_register.html')
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long!', 'error')
                return render_template('student_register.html')
            
            # Check if email already exists
            response = supabase.table('studentdetails').select('*').eq('email', email).execute()
            if response.data:
                flash('Email already registered! Please login.', 'error')
                return render_template('student_register.html')
            
            # Check if student number already exists
            response = supabase.table('studentdetails').select('*').eq('student_number', student_number).execute()
            if response.data:
                flash('Student number already registered!', 'error')
                return render_template('student_register.html')
            
            # Hash password
            password_hash = generate_password_hash(password)
            
            # Insert into database
            data = {
                'email': email,
                'password_hash': password_hash,
                'full_name': full_name,
                'student_number': student_number,
                'is_verified': False
            }
            
            response = supabase.table('studentdetails').insert(data).execute()
            
            if response.data:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('student_login'))
            else:
                flash('Registration failed! Please try again.', 'error')
                return render_template('student_register.html')
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('student_register.html')
    
    return render_template('student_register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    """Student login page"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Email and password are required!', 'error')
                return render_template('student_login.html')
            
            if not validate_gmrit_email(email):
                flash('Invalid email format!', 'error')
                return render_template('student_login.html')
            
            # Get student from database
            response = supabase.table('studentdetails').select('*').eq('email', email).execute()
            
            if not response.data:
                flash('Invalid email or password!', 'error')
                return render_template('student_login.html')
            
            student = response.data[0]
            
            # Verify password
            if not check_password_hash(student['password_hash'], password):
                flash('Invalid email or password!', 'error')
                return render_template('student_login.html')
            
            # Set session
            session['student_id'] = str(student['id'])
            session['student_email'] = student['email']
            session['student_name'] = student['full_name']
            
            flash(f'Welcome back, {student["full_name"]}!', 'success')
            return redirect(url_for('student_dashboard'))
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('student_login.html')
    
    return render_template('student_login.html')

@app.route('/student/dashboard')
def student_dashboard():
    """Student dashboard page"""
    if 'student_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('student_login'))
    
    try:
        # Get student details
        response = supabase.table('studentdetails').select('*').eq('id', session['student_id']).execute()
        
        if not response.data:
            session.clear()
            flash('Student not found. Please login again.', 'error')
            return redirect(url_for('student_login'))
        
        student = response.data[0]
        return render_template('student_dashboard.html', student=student)
        
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('student_login'))

@app.route('/student/logout')
def student_logout():
    """Student logout"""
    session.pop('student_id', None)
    session.pop('student_email', None)
    session.pop('student_name', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('student_login'))

@app.route('/student/forgot-password', methods=['GET', 'POST'])
def student_forgot_password():
    """Forgot password - send OTP"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            
            if not email:
                flash('Email is required!', 'error')
                return render_template('student_forgot_password.html')
            
            if not validate_gmrit_email(email):
                flash('Invalid email format!', 'error')
                return render_template('student_forgot_password.html')
            
            # Check if email exists
            response = supabase.table('studentdetails').select('*').eq('email', email).execute()
            
            if not response.data:
                flash('Email not found! Please register first.', 'error')
                return render_template('student_forgot_password.html')
            
            # Generate OTP
            otp = generate_otp()
            otp_expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
            
            # Update OTP in database
            update_data = {
                'otp_code': otp,
                'otp_expiry': otp_expiry
            }
            
            supabase.table('studentdetails').update(update_data).eq('email', email).execute()
            
            # Send OTP email
            if send_otp_email(email, otp):
                flash('OTP has been sent to your email. Please check your inbox.', 'success')
                return redirect(url_for('student_reset_password', email=email))
            else:
                flash('Failed to send OTP. Please try again later.', 'error')
                return render_template('student_forgot_password.html')
            
        except Exception as e:
            print(f"Forgot password error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('student_forgot_password.html')
    
    return render_template('student_forgot_password.html')

@app.route('/student/reset-password', methods=['GET', 'POST'])
def student_reset_password():
    """Reset password with OTP"""
    email = request.args.get('email', '').strip().lower()
    
    if not email or not validate_gmrit_email(email):
        flash('Invalid email!', 'error')
        return redirect(url_for('student_forgot_password'))
    
    if request.method == 'POST':
        try:
            otp = request.form.get('otp', '').strip()
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([otp, new_password, confirm_password]):
                flash('All fields are required!', 'error')
                return render_template('student_reset_password.html', email=email)
            
            if new_password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('student_reset_password.html', email=email)
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long!', 'error')
                return render_template('student_reset_password.html', email=email)
            
            # Get student details
            response = supabase.table('studentdetails').select('*').eq('email', email).execute()
            
            if not response.data:
                flash('Student not found!', 'error')
                return redirect(url_for('student_forgot_password'))
            
            student = response.data[0]
            
            # Verify OTP
            if not student.get('otp_code') or student['otp_code'] != otp:
                flash('Invalid OTP!', 'error')
                return render_template('student_reset_password.html', email=email)
            
            # Check OTP expiry
            if student.get('otp_expiry'):
                otp_expiry_str = student['otp_expiry']
                # Remove timezone info for simple comparison (stored as naive datetime)
                # Extract just the datetime part before any timezone offset
                if '+' in otp_expiry_str:
                    otp_expiry_str = otp_expiry_str.split('+')[0]
                if 'Z' in otp_expiry_str:
                    otp_expiry_str = otp_expiry_str.replace('Z', '')
                
                otp_expiry = datetime.fromisoformat(otp_expiry_str)
                current_time = datetime.now()
                
                if current_time > otp_expiry:
                    flash('OTP has expired! Please request a new one.', 'error')
                    return redirect(url_for('student_forgot_password'))
            
            # Hash new password
            password_hash = generate_password_hash(new_password)
            
            # Update password and clear OTP
            update_data = {
                'password_hash': password_hash,
                'otp_code': None,
                'otp_expiry': None
            }
            
            supabase.table('studentdetails').update(update_data).eq('email', email).execute()
            
            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('student_login'))
            
        except Exception as e:
            print(f"Reset password error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('student_reset_password.html', email=email)
    
    return render_template('student_reset_password.html', email=email)

# ============================================
# END OF STUDENT AUTHENTICATION ROUTES
# ============================================

# For Vercel deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
