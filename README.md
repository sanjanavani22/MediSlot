# MediSlot: Clinic Appointment Booking System

A Flask + SQLite + HTML/CSS appointment booking app.

## Features
- Doctor directory with specialization, fee and weekly availability
- Appointment booking with server-side validation
- Prevents double booking with a partial unique SQLite index
- Search appointments by name or mobile and cancel bookings
- Clinic dashboard with bookings, cancellations and expected revenue
- JSON REST endpoints and automated tests

## Requirements
- Python 3.10+
- Flask

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Run tests
```bash
python -m unittest discover -s tests -v
```

## API
- `GET /api/doctors`
- `GET /api/slots?doctor_id=1&appt_date=YYYY-MM-DD`
- `GET /api/appointments`
- `POST /api/appointments` with JSON patient_name, phone, doctor_id, appt_date, time_slot and optional reason

This is a classroom/demo project. Before production use, add authentication/authorization, CSRF protection, deployment configuration and privacy/security review.
