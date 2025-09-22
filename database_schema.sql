-- Supabase Database Schema for Placement Tracker
-- Run these SQL commands in your Supabase SQL editor

-- Create companies table
CREATE TABLE companies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hiring_flow TEXT NOT NULL,
    ctc_offer VARCHAR(100) NOT NULL,
    agreement_years INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create selected_students table
CREATE TABLE selected_students (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    student_number VARCHAR(50) NOT NULL,
    linkedin_id VARCHAR(255),
    max_round_reached INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create admins table
CREATE TABLE admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default admin (password: admin123)
-- Note: Change this password in production!
INSERT INTO admins (email, password_hash) VALUES 
('admin@placement.com', 'pbkdf2:sha256:260000$salt$hash');

-- Create indexes for better performance
CREATE INDEX idx_selected_students_company_id ON selected_students(company_id);
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_admins_email ON admins(email);

-- Enable Row Level Security (RLS)
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE selected_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access to companies and students
CREATE POLICY "Allow public read access to companies" ON companies
    FOR SELECT USING (true);

CREATE POLICY "Allow public read access to selected_students" ON selected_students
    FOR SELECT USING (true);

-- Create policies for admin access
CREATE POLICY "Allow admin full access to companies" ON companies
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow admin full access to selected_students" ON selected_students
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow admin read access to admins" ON admins
    FOR SELECT USING (auth.role() = 'authenticated');
