from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import numpy as np
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            passcode_hash TEXT NOT NULL,
            fullname TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/v1/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    passcode = data.get("passcode", "").strip()
    fullname = data.get("fullname", "Student").strip()

    if not student_id or not passcode:
        return jsonify({"status": "error", "message": "Student ID and Passcode are required."}), 400

    passcode_hash = hashlib.sha256(passcode.encode()).hexdigest()

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (student_id, passcode_hash, fullname) VALUES (?, ?, ?)", 
                       (student_id, passcode_hash, fullname))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Registration successful! You can now log in."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Student ID already exists. Please log in."}), 400

@app.route("/api/v1/auth/student-login", methods=["POST"])
def student_login():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    passcode = data.get("passcode", "").strip()

    passcode_hash = hashlib.sha256(passcode.encode()).hexdigest()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT fullname FROM users WHERE student_id = ? AND passcode_hash = ?", (student_id, passcode_hash))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "authenticated": True,
            "student_id": student_id,
            "fullname": user[0],
            "message": "Login successful"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "authenticated": False,
            "message": "Invalid Student ID or Passcode."
        }), 401

@app.route("/api/v1/calculate/index", methods=["POST"])
def calculate_index():
    data = request.get_json() or {}
    nir = data.get("nir")
    red = data.get("red")

    if nir is None or red is None:
        return jsonify({"status": "error", "message": "Missing parameters."}), 400

    nir_val = float(nir)
    red_val = float(red)
    ndvi = (nir_val - red_val) / (nir_val + red_val + 1e-10)

    if ndvi > 0.5:
        classification = "Dense Green Canopy"
    elif ndvi > 0.2:
        classification = "Moderate Vegetation / Crops"
    else:
        classification = "Water / Bare Soil"

    return jsonify({
        "status": "success",
        "computed_value": ndvi,
        "classification": classification
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
