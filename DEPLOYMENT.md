# Deployment Guide for Vercel

This guide explains how to deploy the Placement Tracker application to Vercel.

## Prerequisites

1. A Vercel account (sign up at [vercel.com](https://vercel.com))
2. A Supabase project with the database schema set up
3. Git installed on your local machine

## Environment Variables

You'll need to set the following environment variables in your Vercel project:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon/public key
- `FLASK_SECRET_KEY`: A secret key for Flask sessions
- `FLASK_DEBUG`: Set to 'true' for development, 'false' for production

## Deployment Steps

### Option 1: Deploy with Vercel CLI (Recommended)

1. Install Vercel CLI if you haven't already:
   ```bash
   npm install -g vercel
   ```

2. Login to your Vercel account:
   ```bash
   vercel login
   ```

3. Deploy the application:
   ```bash
   vercel
   ```

4. Follow the prompts to complete the deployment.

### Option 2: Deploy via GitHub

1. Push your code to a GitHub repository.

2. Go to [Vercel Dashboard](https://vercel.com/dashboard)

3. Click "New Project"

4. Import your GitHub repository

5. Configure the project:
   - Framework Preset: Other
   - Root Directory: (leave as default)
   - Build Command: `bash vercel_build.sh`
   - Output Directory: (leave empty)
   - Install Command: `pip install -r requirements.txt`

6. Add the environment variables mentioned above in the project settings.

7. Click "Deploy"

## Post-Deployment

1. After deployment, Vercel will provide you with a URL where your application is hosted.

2. Test the application to ensure everything is working correctly.

## Troubleshooting

- If you see a 404 error, make sure all your routes are properly defined in `app.py`
- Check the Vercel deployment logs for any errors during build or runtime
- Ensure all environment variables are correctly set in the Vercel project settings

## Updating the Application

1. Make your changes locally
2. Commit and push to your GitHub repository
3. Vercel will automatically detect the changes and trigger a new deployment

## Custom Domain (Optional)

You can set up a custom domain in the Vercel project settings if you want to use your own domain name.
