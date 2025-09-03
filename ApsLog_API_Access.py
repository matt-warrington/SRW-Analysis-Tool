from flask import Flask, request, jsonify
from flask_cors import CORS
import zipfile
import os

# Import existing functions
from ApsLogs import get_basic_info, log_info, check_licenses

app = Flask(__name__)
CORS(app)  # Allow JavaScript to communicate with Flask API

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle ZIP file upload and process it."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Extract ZIP contents
    extract_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(file.filename)[0])
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # Process extracted files using existing functions
    system_info = get_basic_info(extract_path)
    logs = log_info(extract_path)
    licenses = check_licenses(extract_path)

    return jsonify({
        "system_info": system_info,
        "logs": logs,
        "licenses": licenses
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)