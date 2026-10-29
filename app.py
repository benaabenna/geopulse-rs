from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import numpy as np

app = Flask(__name__)
CORS(app)

# ==========================================
# MOCK DATABASE / GEOSPATIAL KNOWLEDGE BASE
# ==========================================
KNOWLEDGE_BASE = {
    "ndvi": {
        "unit": "Digital Image Processing",
        "topic": "NDVI & Spectral Vegetation Indices",
        "formula": "(NIR - Red) / (NIR + Red)",
        "description": "Measures plant greenness and canopy health by comparing NIR reflectance against Red absorption.",
        "python_code": "def calc_ndvi(nir, red):\n    return (nir - red) / (nir + red + 1e-10)\n",
        "gee_code": "var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');"
    },
    "ndwi": {
        "unit": "Remote Sensing Applications",
        "topic": "NDWI & Water Bodies Index",
        "formula": "(Green - NIR) / (Green + NIR)",
        "description": "Highlights open water features and delineates surface water bodies.",
        "python_code": "def calc_ndwi(green, nir):\n    return (green - nir) / (green + nir + 1e-10)\n",
        "gee_code": "var ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI');"
    }
}

# ==========================================
# WEB ROUTE (FRONTEND)
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")

# ==========================================
# REST API ENDPOINTS
# ==========================================
@app.route("/api/v1", methods=["GET"])
def api_info():
    return jsonify({
        "app_name": "GeoPulse RS API",
        "version": "1.0",
        "status": "online",
        "available_endpoints": {
            "GET /api/v1/modules": "List all GIS & Remote Sensing modules",
            "POST /api/v1/calculate/index": "Compute spectral index from raw band values",
            "POST /api/v1/auth/student-login": "Validate student credentials"
        }
    }), 200

@app.route("/api/v1/modules", methods=["GET"])
def get_all_modules():
    return jsonify({"status": "success", "data": KNOWLEDGE_BASE}), 200

@app.route("/api/v1/calculate/index", methods=["POST"])
def calculate_index():
    data = request.get_json() or {}
    index_type = data.get("index_type", "ndvi").lower()
    nir = data.get("nir")
    red = data.get("red")

    if nir is None or red is None:
        return jsonify({"status": "error", "message": "Missing 'nir' or 'red' parameters."}), 400

    try:
        nir_val = np.array(nir, dtype=float)
        red_val = np.array(red, dtype=float)
        denom = nir_val + red_val
        denom[denom == 0] = 1e-10
        result = (nir_val - red_val) / denom

        val = float(result) if result.ndim == 0 or len(np.atleast_1d(result)) == 1 else float(result.mean())
        if val > 0.5:
            classification = "Dense Green Canopy"
        elif val > 0.2:
            classification = "Moderate Vegetation / Crops"
        else:
            classification = "Water / Bare Soil"

        return jsonify({
            "status": "success",
            "index_type": index_type.upper(),
            "computed_value": result.tolist(),
            "classification": classification
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/v1/auth/student-login", methods=["POST"])
def student_login():
    data = request.get_json() or {}
    student_id = data.get("student_id", "").strip()
    passcode = data.get("passcode", "").strip()
    
    is_valid = len(student_id) > 3

    return jsonify({
        "status": "success" if is_valid else "invalid",
        "authenticated": is_valid,
        "student_id": student_id,
        "message": "Login successful" if is_valid else "Invalid ID format"
    }), 200 if is_valid else 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
