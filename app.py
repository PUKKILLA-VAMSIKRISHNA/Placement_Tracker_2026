from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, make_response
from supabase import create_client, Client
import os
from datetime import datetime
# Password hashing removed as per request
from dotenv import load_dotenv
import uuid
import pandas as pd
from io import BytesIO
import xlsxwriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from werkzeug.utils import secure_filename

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# File upload configuration
UPLOAD_FOLDER = 'uploads/model_papers'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

# Initialize Supabase client
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client: {str(e)}")
        supabase = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page displaying all companies as cards"""
    if not supabase:
        return render_template('index.html', companies=[])
    
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
            ['Total No of Students', len(students)],
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
        ['Total No of Students', str(len(students))],
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

@app.route('/admin/upload_model_paper/<company_id>', methods=['POST'])
def upload_model_paper(company_id):
    """Upload model paper for a company"""
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
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Save to database
            model_paper_data = {
                'company_id': company_id,
                'paper_name': paper_name,
                'file_url': f'/uploads/model_papers/{unique_filename}',
                'file_size': file_size,
                'uploaded_by': session.get('admin_email'),
                'created_at': datetime.now().isoformat()
            }
            
            supabase.table('model_papers').insert(model_paper_data).execute()
            flash('Model paper uploaded successfully!', 'success')
        else:
            flash('Invalid file type. Only PDF files are allowed.', 'error')
            
    except Exception as e:
        flash(f'Error uploading model paper: {str(e)}', 'error')
    
    return redirect(url_for('company_details', company_id=company_id))

@app.route('/admin/delete_model_paper/<paper_id>', methods=['POST'])
def delete_model_paper(paper_id):
    """Delete model paper"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Get paper details first
        paper_response = supabase.table('model_papers').select('*').eq('id', paper_id).execute()
        if paper_response.data:
            paper = paper_response.data[0]
            company_id = paper['company_id']
            
            # Delete file from filesystem
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(paper['file_url']))
            if os.path.exists(file_path):
                os.remove(file_path)
            
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
    """Download model paper"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
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

# For Vercel deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
