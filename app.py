from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g
import sqlite3, re
from datetime import date, datetime

DATABASE = "medislot.db"
SLOTS = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

from flask import current_app

def init_db(app):
    with app.app_context():
        db = get_db()
        schema_path = os.path.join(app.root_path, "schema.sql")
        with open(schema_path, encoding="utf-8") as f:
            db.executescript(f.read())
        count = db.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO doctors(name, specialization, fee, available_days) VALUES(?,?,?,?)",
                [
                    ("Dr. Arjun Rao", "Cardiologist", 900, "Mon,Wed,Fri"),
                    ("Dr. Karthik Iyer", "Orthopedic Surgeon", 800, "Mon,Tue,Thu"),
                    ("Dr. Meera Nair", "General Physician", 400, "Mon,Tue,Wed,Thu,Fri"),
                    ("Dr. Priya Menon", "Pediatrician", 500, "Tue,Wed,Thu,Fri,Sat"),
                    ("Dr. Sana Fatima", "Dermatologist", 700, "Tue,Thu,Sat"),
                ],
            )
        db.commit()

import os

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY="change-this-secret-key", DATABASE=DATABASE)
    if test_config:
        app.config.update(test_config)
    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()
    with app.app_context():
        init_db(app)
    register_routes(app)
    return app

def taken_slots(doctor_id, appt_date):
    rows = get_db().execute(
        "SELECT time_slot FROM appointments WHERE doctor_id=? AND appt_date=? AND status='Booked'",
        (doctor_id, appt_date),
    ).fetchall()
    return {row["time_slot"] for row in rows}

def validate_booking(form):
    errors = []
    name = form.get("patient_name", "").strip()
    phone = form.get("phone", "").strip()
    reason = form.get("reason", "").strip()
    slot = form.get("time_slot", "")
    try:
        doctor_id = int(form.get("doctor_id", 0))
    except (TypeError, ValueError):
        doctor_id = 0
    doctor = get_db().execute("SELECT * FROM doctors WHERE id=?", (doctor_id,)).fetchone()
    if len(name) < 3:
        errors.append("Patient name must be at least 3 characters.")
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        errors.append("Enter a valid 10-digit Indian mobile number.")
    if doctor is None:
        errors.append("Please select a doctor.")
    if slot not in SLOTS:
        errors.append("Please select a valid time slot.")
    appt = None
    try:
        appt = datetime.strptime(form.get("appt_date", ""), "%Y-%m-%d").date()
        if appt < date.today():
            errors.append("Appointment date cannot be in the past.")
        elif doctor and DAY_NAMES[appt.weekday()] not in doctor["available_days"].split(","):
            errors.append(f'{doctor["name"]} is not available on {DAY_NAMES[appt.weekday()]}. Available: {doctor["available_days"]}.')
    except (TypeError, ValueError):
        errors.append("Please choose a valid date.")
    if not errors and slot in taken_slots(doctor_id, appt.isoformat()):
        errors.append("That slot is already booked. Please pick another one.")
    data = dict(doctor_id=doctor_id, patient_name=name, phone=phone,
                appt_date=appt.isoformat() if appt else "", time_slot=slot, reason=reason)
    return data, errors

def register_routes(app):
    @app.get("/")
    def home():
        db = get_db()
        doctors = db.execute("SELECT * FROM doctors ORDER BY name").fetchall()
        active = db.execute("SELECT COUNT(*) FROM appointments WHERE status='Booked'").fetchone()[0]
        cancelled = db.execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'").fetchone()[0]
        return render_template("index.html", doctors=doctors, active=active, cancelled=cancelled)

    @app.route("/book", methods=["GET", "POST"])
    def book():
        db = get_db()
        doctors = db.execute("SELECT * FROM doctors ORDER BY name").fetchall()
        if request.method == "POST":
            data, errors = validate_booking(request.form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("book.html", doctors=doctors, slots=SLOTS,
                    form=request.form, min_date=date.today().isoformat()), 400
            try:
                db.execute("""INSERT INTO appointments
                    (doctor_id, patient_name, phone, appt_date, time_slot, reason)
                    VALUES (:doctor_id,:patient_name,:phone,:appt_date,:time_slot,:reason)""", data)
                db.commit()
            except sqlite3.IntegrityError:
                flash("That slot was just taken. Please choose another.", "error")
                return render_template("book.html", doctors=doctors, slots=SLOTS,
                    form=request.form, min_date=date.today().isoformat()), 409
            flash("Appointment booked successfully!", "success")
            return redirect(url_for("appointments", phone=data["phone"]))
        form = {"doctor_id": request.args.get("doctor_id", ""), "appt_date": request.args.get("appt_date", "")}
        return render_template("book.html", doctors=doctors, slots=SLOTS, form=form, min_date=date.today().isoformat())

    @app.get("/appointments")
    def appointments():
        term = request.args.get("q", "").strip()
        phone = request.args.get("phone", "").strip()
        search = term or phone
        sql = """SELECT a.*, d.name AS doctor_name, d.specialization, d.fee
                 FROM appointments a JOIN doctors d ON d.id=a.doctor_id"""
        params = []
        if search:
            sql += " WHERE a.phone LIKE ? OR a.patient_name LIKE ?"
            params.extend([f"%{search}%", f"%{search}%"])
        sql += " ORDER BY a.appt_date DESC, a.time_slot"
        rows = get_db().execute(sql, params).fetchall()
        return render_template("appointments.html", appointments=rows, q=search)

    @app.post("/cancel/<int:appointment_id>")
    def cancel(appointment_id):
        db = get_db()
        db.execute("UPDATE appointments SET status='Cancelled' WHERE id=? AND status='Booked'", (appointment_id,))
        db.commit()
        flash("Appointment cancelled if it was active.", "success")
        return redirect(url_for("appointments"))

    @app.get("/dashboard")
    def dashboard():
        rows = get_db().execute("""
            SELECT d.id, d.name, d.specialization, d.fee,
                   SUM(CASE WHEN a.status='Booked' THEN 1 ELSE 0 END) AS bookings,
                   SUM(CASE WHEN a.status='Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                   SUM(CASE WHEN a.status='Booked' THEN d.fee ELSE 0 END) AS revenue
            FROM doctors d LEFT JOIN appointments a ON a.doctor_id=d.id
            GROUP BY d.id ORDER BY d.name
        """).fetchall()
        total_active = get_db().execute("SELECT COUNT(*) FROM appointments WHERE status='Booked'").fetchone()[0]
        total_cancelled = get_db().execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'").fetchone()[0]
        revenue = sum(row["revenue"] or 0 for row in rows)
        return render_template("dashboard.html", rows=rows, total_active=total_active, total_cancelled=total_cancelled, revenue=revenue)

    @app.get("/api/doctors")
    def api_doctors():
        rows = get_db().execute("SELECT * FROM doctors ORDER BY name").fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/api/slots")
    def api_slots():
        try:
            doctor_id = int(request.args["doctor_id"])
            appt_date = request.args["appt_date"]
            datetime.strptime(appt_date, "%Y-%m-%d")
        except (KeyError, ValueError):
            return jsonify(error="doctor_id and appt_date (YYYY-MM-DD) are required"), 400
        doctor = get_db().execute("SELECT id FROM doctors WHERE id=?", (doctor_id,)).fetchone()
        if doctor is None:
            return jsonify(error="Unknown doctor_id"), 400
        taken = taken_slots(doctor_id, appt_date)
        return jsonify(doctor_id=doctor_id, date=appt_date,
                       available=[slot for slot in SLOTS if slot not in taken],
                       booked=sorted(taken))

    @app.get("/api/appointments")
    def api_appointments():
        rows = get_db().execute("""SELECT a.*, d.name AS doctor_name FROM appointments a
            JOIN doctors d ON d.id=a.doctor_id ORDER BY a.appt_date, a.time_slot""").fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/appointments")
    def api_create_appointment():
        payload = request.get_json(silent=True) or {}
        data, errors = validate_booking(payload)
        if errors:
            return jsonify(errors=errors), 400
        db = get_db()
        try:
            db.execute("""INSERT INTO appointments
                (doctor_id, patient_name, phone, appt_date, time_slot, reason)
                VALUES (:doctor_id,:patient_name,:phone,:appt_date,:time_slot,:reason)""", data)
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify(errors=["That slot is already booked. Please pick another one."]), 409
        return jsonify(message="Appointment booked successfully", appointment=data), 201

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
