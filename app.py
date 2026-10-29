from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# ==========================================
# INITIALIZE DATABASE & TABLES
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            passcode_hash TEXT NOT NULL,
            fullname TEXT
        )
    """)
    
    # Dynamic Lessons table for custom user input
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_name TEXT NOT NULL,
            topic_name TEXT UNIQUE NOT NULL,
            description TEXT,
            formula TEXT,
            python_code TEXT,
            gee_code TEXT
        )
    """)
    
    # Insert default baseline lessons if table is empty
    cursor.execute("SELECT COUNT(*) FROM lessons")
    if cursor.fetchone()[0] == 0:
        default_lessons = [
            (
                "Digital Image Processing",
                "NDVI & Spectral Vegetation Indices",
                "Measures plant greenness and canopy health by comparing NIR reflectance against Red absorption.",
                "(NIR - Red) / (NIR + Red)",
                "import rasterio\n# NDVI calculation\nndvi = (nir - red) / (nir + red + 1e-10)",
                "var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');"
            ),
            (
                "Remote Sensing Applications",
                "NDWI & Water Bodies Index",
                "Highlights open water features and delineates surface water bodies using green and NIR bands.",
                "(Green - NIR) / (Green + NIR)",
                "import rasterio\n# NDWI calculation\nndwi = (green - nir) / (green + nir + 1e-10)",
                "var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');"
            )
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO lessons (unit_name, topic_name, description, formula, python_code, gee_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """, default_lessons)

    conn.commit()
    conn.close()

init_db()

# ==========================================
# WEB ROUTE
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")

# ==========================================
# AUTHENTICATION API ENDPOINTS
# ==========================================
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

# ==========================================
# DYNAMIC LESSONS & SEARCH API ENDPOINTS
# ==========================================
@app.route("/api/v1/lessons/search", methods=["POST"])
def search_or_create_lesson():
    data = request.get_json() or {}
    unit_name = data.get("unit_name", "").strip()
    topic_name = data.get("topic_name", "").strip()

    if not topic_name:
        return jsonify({"status": "error", "message": "Topic name is required."}), 400

    if not unit_name:
        unit_name = "General GIS & Remote Sensing"

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if lesson already exists
    cursor.execute("SELECT unit_name, topic_name, description, formula, python_code, gee_code FROM lessons WHERE topic_name = ?", (topic_name,))
    row = cursor.fetchone()

    if row:
        lesson_data = {
            "unit": row[0],
            "topic": row[1],
            "description": row[2],
            "formula": row[3],
            "python_code": row[4],
            "gee_code": row[5]
        }
    else:
        # Dynamically create new lesson profile on the fly
        description = f"Custom study module for '{topic_name}' under the unit '{unit_name}'. Explores advanced spatial data processing and analytical workflows."
        formula = "Custom Expression / Analytical Model"
        python_code = f"# Python workflow for {topic_name}\nimport geopandas as gpd\nimport numpy as np\n\nprint('Executing module: {topic_name}')"
        gee_code = f"// Google Earth Engine script for {topic_name}\nvar region = ee.Geometry.Point([36.8219, -1.2921]);\nMap.centerObject(region, 10);"
        
        cursor.execute("""
            INSERT INTO lessons (unit_name, topic_name, description, formula, python_code, gee_code)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (unit_name, topic_name, description, formula, python_code, gee_code))
        conn.commit()
        
        lesson_data = {
            "unit": unit_name,
            "topic": topic_name,
            "description": description,
            "formula": formula,
            "python_code": python_code,
            "gee_code": gee_code
        }

    conn.close()
    return jsonify({"status": "success", "data": lesson_data}), 200

@app.route("/api/v1/calculate/index", methods=["POST"])
def calculate_index():
    data = request.get_json() or {}
    nir = data.get("nir")
    red = data.get("red")

    if nir is None or red is None:
        return jsonify({"status": "error", "message": "Missing parameters."}), 400

    try:
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
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
