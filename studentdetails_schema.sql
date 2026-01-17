-- Student Details Table Schema for Placement Tracker
-- Run this SQL command in your Supabase SQL editor

-- Create studentdetails table for student authentication
CREATE TABLE studentdetails (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    student_number VARCHAR(50) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    otp_code VARCHAR(6),
    otp_expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_studentdetails_email ON studentdetails(email);
CREATE INDEX idx_studentdetails_student_number ON studentdetails(student_number);

-- Enable Row Level Security (RLS)
ALTER TABLE studentdetails ENABLE ROW LEVEL SECURITY;

-- Create policy for students to read their own data
CREATE POLICY "Students can read own data" ON studentdetails
    FOR SELECT USING (auth.uid()::text = id::text);

-- Create policy for students to update their own data
CREATE POLICY "Students can update own data" ON studentdetails
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Create policy for public insert (registration)
CREATE POLICY "Allow public insert for registration" ON studentdetails
    FOR INSERT WITH CHECK (true);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_studentdetails_updated_at BEFORE UPDATE
    ON studentdetails FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
