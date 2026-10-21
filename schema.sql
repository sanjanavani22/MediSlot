CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    fee INTEGER NOT NULL CHECK(fee >= 0),
    available_days TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
    patient_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    appt_date TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'Booked' CHECK(status IN ('Booked','Cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_slot
    ON appointments(doctor_id, appt_date, time_slot)
    WHERE status = 'Booked';
