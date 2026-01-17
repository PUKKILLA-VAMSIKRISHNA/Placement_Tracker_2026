# Student Authentication Setup Guide

## Overview
This guide will help you set up the student registration, login, and password reset functionality for the Placement Tracker project.

## Features Added
1. **Student Registration** - Email validation (XX34XA12XX@gmrit.edu.in format)
2. **Student Login** - Secure authentication with password hashing
3. **Student Dashboard** - Personalized dashboard for students
4. **Forgot Password** - OTP-based password reset via email

## Step 1: Create Database Table in Supabase

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project: **Placement-Tracker**
3. Click on **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy and paste the contents of `studentdetails_schema.sql`
6. Click **Run** to create the table

The table will include:
- `id` (UUID, Primary Key)
- `email` (VARCHAR, Unique)
- `password_hash` (VARCHAR)
- `full_name` (VARCHAR)
- `student_number` (VARCHAR)
- `is_verified` (BOOLEAN)
- `otp_code` (VARCHAR)
- `otp_expiry` (TIMESTAMP)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## Step 2: Configure Email Settings

### Option A: Using Gmail (Recommended)

1. Go to your Gmail account
2. Enable 2-Factor Authentication
3. Generate an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" as the app
   - Select "Other (Custom name)" as the device
   - Name it "Placement Tracker"
   - Copy the generated 16-character password

4. Update your `.env` file:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=placementtrackergmrit@gmail.com
MAIL_PASSWORD=your_16_character_app_password_here
MAIL_DEFAULT_SENDER=placementtrackergmrit@gmail.com
```

### Option B: Using Other Email Providers

For other providers, update the SMTP settings accordingly in `.env`.

## Step 3: Install Required Packages

Run the following command in your terminal:

```bash
cd C:\Users\msant\OneDrive\Desktop\myproject\Placement_Tracker_2026
pip install -r requirements.txt
```

This will install:
- Flask
- Flask-Mail (for sending emails)
- werkzeug (for password hashing)
- All other existing dependencies

## Step 4: Test the Application

1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to:
   - Registration: http://localhost:5000/student/register
   - Login: http://localhost:5000/student/login
   - Dashboard: http://localhost:5000/student/dashboard

## Email Format Validation

The system enforces the following email format: **XX34XA12XX@gmrit.edu.in**

Where:
- First 2 characters (XX) = Numbers (e.g., 22)
- Characters 3-4 = "34"
- Character 5 = Any letter (e.g., A)
- Characters 6-7 = "A12"
- Last 2 characters (XX) = Numbers (e.g., 01)

**Valid Examples:**
- 2234AA1201@gmrit.edu.in
- 2234BA1234@gmrit.edu.in
- 2234CA1299@gmrit.edu.in

**Invalid Examples:**
- 22341234@gmrit.edu.in (missing letter)
- 2234AA12A1@gmrit.edu.in (wrong format)
- 2234AA1201@gmail.com (wrong domain)

## Student Number Format

The system enforces the following student number format: **XX34XA12XX**

**Valid Examples:**
- 2234AA1201
- 2234BA1234
- 2234CA1299

## Routes Added

| Route | Method | Description |
|-------|--------|-------------|
| `/student/register` | GET, POST | Student registration page |
| `/student/login` | GET, POST | Student login page |
| `/student/dashboard` | GET | Student dashboard (requires login) |
| `/student/logout` | GET | Student logout |
| `/student/forgot-password` | GET, POST | Request password reset OTP |
| `/student/reset-password` | GET, POST | Reset password with OTP |

## Password Reset Flow

1. Student clicks "Forgot Password" on login page
2. Student enters their GMRIT email
3. System generates a 6-digit OTP
4. OTP is sent to the student's email (valid for 10 minutes)
5. Student enters OTP and new password
6. Password is updated and student can login

## Security Features

✅ Email format validation (GMRIT domain only)
✅ Student number format validation
✅ Password hashing using Werkzeug
✅ OTP expiration (10 minutes)
✅ Session-based authentication
✅ Password strength requirement (minimum 8 characters)
✅ Duplicate email/student number prevention

## Troubleshooting

### Email Not Sending
1. Check that `MAIL_PASSWORD` in `.env` is the App Password (not your regular Gmail password)
2. Ensure 2-Factor Authentication is enabled on Gmail
3. Check firewall settings allow SMTP connections
4. Check spam folder for OTP emails

### Registration Errors
1. Ensure the `studentdetails` table exists in Supabase
2. Check that email format matches: XX34XA12XX@gmrit.edu.in
3. Verify student number format: XX34XA12XX
4. Make sure passwords match and are at least 8 characters

### Database Connection Issues
1. Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
2. Check that Row Level Security policies are set correctly in Supabase
3. Run the SQL schema file again if table is missing

## Files Created/Modified

### New Files:
- `studentdetails_schema.sql` - Database schema
- `templates/student_register.html` - Registration page
- `templates/student_login.html` - Login page
- `templates/student_dashboard.html` - Student dashboard
- `templates/student_forgot_password.html` - Forgot password page
- `templates/student_reset_password.html` - Reset password page
- `STUDENT_AUTH_SETUP.md` - This setup guide

### Modified Files:
- `app.py` - Added student authentication routes and email configuration
- `requirements.txt` - Added Flask-Mail and werkzeug
- `.env.example` - Added email configuration variables

## Next Steps

1. ✅ Create the database table in Supabase
2. ✅ Configure email settings in `.env`
3. ✅ Install dependencies
4. ✅ Test registration and login
5. ✅ Test password reset flow
6. Update navigation menus to include student login link
7. Add student-specific features to the dashboard
8. Consider email verification on registration (optional)

## Support

For issues or questions, contact the development team.

---
**Last Updated:** January 15, 2026
