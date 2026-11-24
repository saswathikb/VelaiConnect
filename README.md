# VelaiConnect — AI Daily-Wage Employment Connector

A Flask + MySQL starter application for connecting daily-wage workers with local job listings.

## Features implemented
- Worker and employer account registration
- Password hashing and session-based login
- Worker profile details: language, city, skills and experience
- Employer job posting
- Job search by keyword and city
- Job detail pages and worker applications
- Worker/employer dashboards
- Basic transparent keyword matching endpoint
- Optional Gemini-powered skill extraction endpoint
- Browser speech input (where supported by the browser)
- Responsive UI

## Important prototype limitations
- Employer accounts are **not automatically verified**. The verified badge is controlled by the database `verified` field and should only be enabled after a real verification process.
- Job listings are user-submitted, not independently verified.
- Browser speech recognition depends on browser/device support and may send audio to the browser provider.
- Location is entered by the user; this version does not use live GPS.
- Matching is keyword-based. Gemini is used only for optional skill extraction, not guaranteed job suitability.
- Add HTTPS, CSRF protection, rate limiting, email/OTP verification, moderation, privacy policy and production logging before public deployment.

## Requirements
- Python 3.10+
- MySQL 8+
- A terminal / command prompt

## Setup on Windows
1. Install Python and MySQL Server. Make sure the MySQL service is running.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Create the database. Open MySQL Workbench or MySQL command line and run:

   ```sql
   CREATE DATABASE velaiconnect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

6. Copy `.env.example` to `.env`, then fill in your MySQL username and password. Change `SECRET_KEY` to a long random value.
7. Start the app:

   ```powershell
   python app.py
   ```

8. Visit `http://127.0.0.1:5000`.

The app creates its tables automatically on first startup. The database itself must exist first.

## Optional Gemini setup
Add a valid Gemini API key to `GEMINI_API_KEY` in `.env`. If it is blank, skill extraction uses the built-in keyword list. Never commit `.env` or publish API keys.

## First-time testing
- Register a worker account with skills such as `painting, plumbing`.
- Register a second account as an employer.
- Log in as the employer and post a job.
- Log out, log in as the worker and apply.
- Use the dashboard to view applications.

## GitHub upload
Upload the project folder to a new GitHub repository. Do **not** upload `.env`, passwords, API keys, or real worker personal data.
