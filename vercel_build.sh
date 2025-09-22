#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Install any additional build dependencies if needed
# For example, if you need to compile any Python extensions

# Set environment variables
echo "SUPABASE_URL=$SUPABASE_URL" > .env
echo "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" >> .env
echo "FLASK_SECRET_KEY=$FLASK_SECRET_KEY" >> .env
