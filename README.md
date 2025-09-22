# IT Branch 2026 Placement Tracker

A comprehensive web application built with Flask and Supabase to track placement activities for IT Branch 2026 batch. This application allows students to view company information and selected students, while providing administrators with full CRUD capabilities.

## Features

### 🎯 Student Features
- **Company Cards View**: Browse all companies with attractive card layouts
- **Company Details**: View detailed information including:
  - Company name and hiring flow
  - CTC offer and agreement years
  - List of selected students with their progress
- **Student Information**: See student names, numbers, LinkedIn profiles, and maximum rounds reached

### 🔐 Admin Features
- **Secure Authentication**: Email and password-based admin login
- **Company Management**: Add, edit, and delete companies
- **Student Management**: Add students to companies and track their progress
- **Dashboard**: Comprehensive overview of all companies and students
- **CRUD Operations**: Full create, read, update, delete functionality

### 🎨 UI/UX Features
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Modern Interface**: Clean, professional design with Bootstrap 5
- **Interactive Elements**: Hover effects, smooth transitions, and user feedback
- **Accessibility**: Screen reader friendly and keyboard navigable

## Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL (Supabase)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Bootstrap 5, Font Awesome icons
- **Authentication**: Session-based with password hashing

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Supabase account
- Git (optional)

### 1. Clone or Download the Project
```bash
git clone <repository-url>
cd placement_tracker
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Supabase Database

1. Create a new project on [Supabase](https://supabase.com)
2. Go to the SQL Editor in your Supabase dashboard
3. Copy and paste the contents of `database_schema.sql`
4. Execute the SQL to create tables and policies

### 5. Configure Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update the `.env` file with your Supabase credentials:
```env
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
FLASK_SECRET_KEY=your-super-secret-key-here
```

### 6. Update App Configuration

Edit `app.py` and replace the placeholder values:
```python
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-anon-key"
app.secret_key = 'your-secret-key-here'
```

### 7. Create Admin User

Run the following SQL in your Supabase SQL Editor to create an admin user:
```sql
INSERT INTO admins (email, password_hash) VALUES 
('admin@placement.com', 'pbkdf2:sha256:260000$salt$hash');
```

Or use Python to generate a proper password hash:
```python
from werkzeug.security import generate_password_hash
print(generate_password_hash('admin123'))
```

### 8. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage Guide

### For Students
1. Visit the homepage to see all companies
2. Click on any company card to view details
3. See selected students and their progress

### For Administrators
1. Click "Admin Login" in the navigation
2. Use credentials: `admin@placement.com` / `admin123`
3. Access the admin dashboard to manage companies and students

### Adding Companies
1. Login as admin
2. Click "Add Company" button
3. Fill in company details:
   - Company name
   - Hiring flow (step-by-step process)
   - CTC offer
   - Agreement years
4. Submit the form

### Adding Students
1. Go to a company's detail page
2. Click "Add Student" (admin only)
3. Fill in student information:
   - Full name
   - Student number/roll number
   - LinkedIn ID (optional)
   - Maximum round reached
4. Submit the form

## Database Schema

### Companies Table
- `id`: UUID (Primary Key)
- `name`: Company name
- `hiring_flow`: Detailed hiring process
- `ctc_offer`: Salary package offered
- `agreement_years`: Bond period
- `created_at`, `updated_at`: Timestamps

### Selected Students Table
- `id`: UUID (Primary Key)
- `company_id`: Foreign key to companies
- `name`: Student full name
- `student_number`: Roll/registration number
- `linkedin_id`: LinkedIn profile username
- `max_round_reached`: Highest round cleared
- `created_at`, `updated_at`: Timestamps

### Admins Table
- `id`: UUID (Primary Key)
- `email`: Admin email
- `password_hash`: Hashed password
- `created_at`: Timestamp

## Security Features

- **Password Hashing**: Uses Werkzeug's secure password hashing
- **Session Management**: Secure session-based authentication
- **Row Level Security**: Supabase RLS policies protect data
- **Input Validation**: Client and server-side validation
- **CSRF Protection**: Built-in Flask CSRF protection

## Customization

### Styling
- Edit `static/css/style.css` for custom styles
- Modify Bootstrap variables for theme changes
- Add custom CSS classes as needed

### Functionality
- Add new routes in `app.py`
- Create new templates in `templates/`
- Extend JavaScript functionality in `static/js/main.js`

### Database
- Modify `database_schema.sql` for schema changes
- Update models in `app.py` accordingly
- Run migrations in Supabase

## Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. Set `FLASK_ENV=production` in environment
2. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Environment Variables for Production
```env
FLASK_ENV=production
FLASK_SECRET_KEY=your-production-secret-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-key
```

## Troubleshooting

### Common Issues

1. **Supabase Connection Error**
   - Verify URL and API key
   - Check network connectivity
   - Ensure RLS policies are correctly set

2. **Admin Login Issues**
   - Verify admin user exists in database
   - Check password hash generation
   - Ensure session configuration is correct

3. **Template Not Found**
   - Verify templates are in `templates/` directory
   - Check file names match route references
   - Ensure proper Flask app structure

4. **Static Files Not Loading**
   - Verify files are in `static/` directory
   - Check file paths in templates
   - Clear browser cache

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Changelog

### Version 1.0.0
- Initial release
- Company and student management
- Admin authentication
- Responsive design
- Full CRUD operations

---

**Note**: This application is designed specifically for IT Branch 2026 placement tracking. Customize as needed for your specific requirements.
