from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import chapar
import configparser
import tempfile
import shutil
import logging
import magic  # Import python-magic

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', tempfile.mkdtemp())
ALLOWED_EXTENSIONS = {'html', 'csv', 'ini'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_content(filepath, expected_mime):
    """Validates the file content type using python-magic."""
    mime = magic.Magic(mime=True).from_file(filepath)
    if mime != expected_mime:
        raise ValueError(f"Invalid file content type. Expected {expected_mime}, got {mime}")

def save_uploaded_files(files, temp_dir):
    """Saves uploaded files to a temporary directory and validates them."""
    file_paths = {}
    for key, filename in files.items():
        if key not in request.files:
            raise ValueError(f'Missing {key} file')

        file = request.files[key]

        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        if file_length > MAX_FILE_SIZE:
             raise ValueError(f"File {filename} exceeds maximum size of {MAX_FILE_SIZE} bytes")
        file.seek(0) # rewind

        if not allowed_file(file.filename):
            raise ValueError(f'Invalid file type for {key}')

        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        file_paths[key] = filepath

    # Validate content
    validate_file_content(file_paths['template'], 'text/html')
    # You might need to adjust the expected mime types
    validate_file_content(file_paths['recipients'], 'text/csv')
    validate_file_content(file_paths['config'], 'text/plain')

    return file_paths

@app.route('/api/send', methods=['POST'])
def send_emails():
    """API endpoint to send emails using uploaded files."""
    try:
        if not request.files:
            return jsonify({'error': 'No files provided'}), 400

        # Create temporary directory for this request
        temp_dir = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])

        # Handle file uploads
        files = {
            'template': 'email_template.html',
            'recipients': 'recipients.csv',
            'config': 'config.ini'
        }

        try:
            file_paths = save_uploaded_files(files, temp_dir)
        except ValueError as e:
            shutil.rmtree(temp_dir)
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            shutil.rmtree(temp_dir)
            logging.exception("File saving error")
            return jsonify({'error': 'File processing error'}), 500

        # Run Chapar email sending process
        try:
            # Call a new function in chapar.py that takes file paths as arguments
            chapar.send_emails_from_files(file_paths['config'], file_paths['recipients'], file_paths['template'])
            result = {'status': 'success', 'message': 'Emails sent successfully'}
        except Exception as e:
            logging.error(f"Error during email dispatch: {e}")
            result = {'status': 'error', 'message': str(e)}

        # Cleanup
        shutil.rmtree(temp_dir)

        return jsonify(result)

    except Exception as e:
        logging.exception("Unexpected error")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """API endpoint for health check."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)