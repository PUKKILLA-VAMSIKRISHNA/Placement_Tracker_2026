#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static
mkdir -p templates

# Copy static files if they don't exist
if [ ! -f "static/style.css" ]; then
    cp -r static_src/* static/ 2>/dev/null || true
fi

# Set environment variables
echo "SUPABASE_URL=$SUPABASE_URL" > .env
echo "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" >> .env
echo "FLASK_SECRET_KEY=$FLASK_SECRET_KEY" >> .env
echo "FLASK_ENV=production" >> .env
echo "ADMIN_EMAIL=$ADMIN_EMAIL" >> .env
echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> .env
