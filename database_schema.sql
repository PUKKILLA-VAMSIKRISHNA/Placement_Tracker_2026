-- Supabase Database Schema for Placement Tracker
-- Run these SQL commands in your Supabase SQL editor

-- MIGRATION SCRIPT (Run this first if you have existing data)
-- If you already have tables, run these ALTER commands instead of CREATE commands:
/*
-- Update companies table structure
ALTER TABLE companies RENAME COLUMN hiring_flow TO hiring_rounds;
ALTER TABLE companies ALTER COLUMN agreement_years TYPE DECIMAL(3,1);

-- Add email column to selected_students table if it doesn't exist
ALTER TABLE selected_students ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Update max_round_reached column type
ALTER TABLE selected_students ALTER COLUMN max_round_reached TYPE VARCHAR(50);

-- Add logo_url column to companies table if it doesn't exist
ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
*/

-- Create companies table
CREATE TABLE companies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hiring_rounds TEXT NOT NULL,
    ctc_offer VARCHAR(100) NOT NULL,
    agreement_years DECIMAL(3,1) NOT NULL,
    logo_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create selected_students table
CREATE TABLE selected_students (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    student_number VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    linkedin_id VARCHAR(255),
    max_round_reached VARCHAR(50) NOT NULL,
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

-- Create policies for admin read access to admins
CREATE POLICY "Allow admin read access to admins" ON admins
    FOR SELECT USING (auth.role() = 'authenticated');

-- Create model_papers table
CREATE TABLE model_papers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    paper_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size INTEGER,
    uploaded_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_model_papers_company_id ON model_papers(company_id);

-- Enable Row Level Security (RLS)
ALTER TABLE model_papers ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access to model papers
CREATE POLICY "Allow public read access to model_papers" ON model_papers
    FOR SELECT USING (true);

-- Create policies for admin access to model papers
CREATE POLICY "Allow admin full access to model_papers" ON model_papers
    FOR ALL USING (auth.role() = 'authenticated');
