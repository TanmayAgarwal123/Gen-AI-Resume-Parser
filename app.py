# FLASK APP - Run the app using flask --app app.py run
import os, sys
from flask import Flask, request, render_template, abort
from PyPDF2 import PdfReader 
import json
from resumeparser import ats_extractor
import secrets
from werkzeug.utils import secure_filename
import shutil
from pathlib import Path
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sys.path.insert(0, os.path.abspath(os.getcwd()))


UPLOAD_PATH = r"__DATA__"
app = Flask(__name__)
# Security configurations
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size 16MB
app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['SECRET_KEY'] = os.urandom(24)  # For session security

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.route('/')
def index():
    return render_template('index.html')

def secure_file_handler(uploaded_file):
    """Securely handle uploaded files with random names"""
    filename = secure_filename(uploaded_file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
        abort(400, description="Invalid file format")
    
    # Generate secure random filename
    random_filename = secrets.token_hex(16) + file_ext
    file_path = os.path.join(UPLOAD_PATH, random_filename)
    
    return file_path

@app.route("/process", methods=["POST"])
@limiter.limit("10 per minute")  # Rate limit for uploads
def ats():
    if 'pdf_doc' not in request.files:
        abort(400, description="No file provided")
    
    doc = request.files['pdf_doc']
    if doc.filename == '':
        abort(400, description="No file selected")

    try:
        file_path = secure_file_handler(doc)
        doc.save(file_path)
        data = _read_file_from_path(file_path)
        # Clean up after processing
        os.remove(file_path)
        
        data = ats_extractor(data)
        return render_template('index.html', data=json.loads(data))
    except Exception as e:
        # Clean up on error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        abort(500, description=f"Error processing file: {str(e)}")

def _read_file_from_path(path):
    try:
        reader = PdfReader(path)
        data = ""
        for page in reader.pages:
            data += page.extract_text()
        return data
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")

def init_app():
    """Initialize application requirements"""
    # Ensure upload directory exists
    Path(UPLOAD_PATH).mkdir(parents=True, exist_ok=True)
    
    # Clean any leftover files from previous runs
    shutil.rmtree(UPLOAD_PATH)
    Path(UPLOAD_PATH).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    init_app()
    app.run(port=8000, debug=False)  # Set debug=False in production

