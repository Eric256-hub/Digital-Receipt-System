# Digital Receipt and Transaction Record Management System

A Django-based transaction recording and receipt management prototype for small-scale businesses. It supports day-to-day sales recording, receipt generation and transaction-history retrieval.

## Features
- Public landing page, account registration and sign-in
- Business profile setup for each registered owner
- Business-scoped transaction records
- Multiple line items per transaction with server-side total calculation
- Unique receipt numbers and optional customer details
- Cash, mobile money, bank and other payment methods
- Transaction history with receipt/customer search, date and status filters
- Receipt details with browser print / Save as PDF
- Cancellation with a required reason while retaining the original transaction record
- Dashboard metrics and recent activity
- Django administration

## Technology
Python, Django, SQLite (local development), PostgreSQL (production), HTML, CSS, JavaScript, Gunicorn and WhiteNoise.

## Local setup
1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set a long random `DJANGO_SECRET_KEY`. Keep `.env` private.
4. Run `python manage.py migrate`.
5. Create an administrator with `python manage.py createsuperuser`.
6. Run `python manage.py runserver` and open `http://127.0.0.1:8000/`.

## Render deployment
Create a PostgreSQL database and a Python Web Service connected to this repository.

- Build command: `./build.sh`
- Start command: `gunicorn receipt_system.wsgi:application`
- Environment variables: `DJANGO_SECRET_KEY` (new secure value), `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` (your hostname), and `DATABASE_URL` (PostgreSQL connection string).
- Set `CSRF_TRUSTED_ORIGINS` to your HTTPS origin if needed.

Never commit `.env`, production credentials or a live database.

## Scope and limitations
This is a transaction-recording and receipt-generation prototype. It is not an accounting package, payment processor, inventory system or URA EFRIS integration. Its receipts are business records and must not be represented as official EFRIS fiscal receipts or proof of tax compliance. Browser printing can print or save a receipt as PDF; it does not create a digitally signed PDF.

Before commercial use, add automated tests, database backups, staff access-management workflows, rate limiting, monitoring and a reviewed privacy/data-retention policy.
