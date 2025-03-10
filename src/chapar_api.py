from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import re
import chapar
import configparser
import tempfile
import shutil
import logging
import magic
from flask import send_from_directory, render_template
import csv

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', tempfile.mkdtemp())
ALLOWED_EXTENSIONS = {'html', 'csv', 'ini'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def validate_email(email):
    """Validates an email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_recipients_file(filepath):
    """Validates email addresses in the recipients file."""
    invalid_emails = []
    with open(filepath, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            email = row.get('email', '').strip()
            if email and not validate_email(email):
                invalid_emails.append(email)
    
    if invalid_emails:
        raise ValueError(f"Invalid email addresses found: {', '.join(invalid_emails[:5])}" +
                        (f" and {len(invalid_emails)-5} more" if len(invalid_emails) > 5 else ""))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_content(filepath, expected_mime_types):
    """Validates the file content type using python-magic."""
    mime = magic.Magic(mime=True).from_file(filepath)
    # Accept any of the expected mime types
    if not any(mime.startswith(expected) for expected in expected_mime_types):
        raise ValueError(f"Invalid file content type. Expected one of {expected_mime_types}, got {mime}")


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

    validate_file_content(file_paths['template'], ['text/html'])
    validate_file_content(file_paths['recipients'], ['text/csv', 'text/plain'])
    validate_file_content(file_paths['config'], ['text/plain', 'text/x-ini'])

    return file_paths


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/templates', methods=['GET'])
def list_templates():
    """API endpoint to list available template folders."""
    try:
        logging.info("Accessing /api/templates endpoint")
        templates = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logging.info(f"Base directory: {base_dir}")
        
        # List all items in the directory for debugging
        all_items = os.listdir(base_dir)
        logging.info(f"All items in directory: {all_items}")
        
        for item in all_items:
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                # Check if directory contains required files
                has_html = os.path.exists(os.path.join(item_path, 'email_template.html'))
                has_csv = os.path.exists(os.path.join(item_path, 'recipients.csv'))
                has_ini = os.path.exists(os.path.join(item_path, 'config.ini'))
                
                logging.info(f"Directory {item}: has_html={has_html}, has_csv={has_csv}, has_ini={has_ini}")
                
                if has_html and has_csv and has_ini:
                    try:
                        desc = get_template_description(item_path)
                        templates.append({
                            'name': item,
                            'description': desc
                        })
                    except Exception as e:
                        logging.exception(f"Error processing template {item}: {e}")
        
        # Sort templates alphabetically
        templates.sort(key=lambda x: x['name'])
        logging.info(f"Returning {len(templates)} templates")
        return jsonify(templates)
    except Exception as e:
        logging.exception(f"Error listing templates: {e}")
        return jsonify({'error': str(e)}), 500
    
    
def get_template_description(folder_path):
    """Extract a description for the template from its files."""
    try:
        # Try to get description from config.ini
        config = configparser.ConfigParser()
        config.read(os.path.join(folder_path, 'config.ini'), encoding='utf-8')
        if config.has_section('Settings') and config.has_option('Settings', 'Description'):
            return config['Settings']['Description']
        
        # Fallback: Use the subject from config
        if config.has_section('SMTP') and config.has_option('SMTP', 'Subject'):
            return config['SMTP']['Subject']
        
        # Last resort: Use folder name
        return os.path.basename(folder_path)
    except Exception as e:
        logging.exception(f"Error getting template description: {e}")
        return os.path.basename(folder_path)

@app.route('/api/run-template', methods=['POST'])
def run_template():
    """API endpoint to run an existing template folder."""
    try:
        data = request.json
        if not data or 'template' not in data:
            return jsonify({'error': 'No template specified'}), 400
        
        template_folder = data['template']
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, template_folder)
        
        # Verify template folder exists and has required files
        if not os.path.isdir(template_path):
            return jsonify({'error': 'Template folder not found'}), 404
        
        required_files = {
            'email_template.html': os.path.join(template_path, 'email_template.html'),
            'recipients.csv': os.path.join(template_path, 'recipients.csv'),
            'config.ini': os.path.join(template_path, 'config.ini')
        }
        
        for name, path in required_files.items():
            if not os.path.exists(path):
                return jsonify({'error': f'Missing required file: {name}'}), 400
        
        # Execute the email sending process
        try:
            chapar.main(template_path)  # Pass the full path to template folder
            result = {'status': 'success', 'message': 'Emails sent successfully'}
        except Exception as e:
            logging.error(f"Error during email dispatch: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logging.exception("Unexpected error")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    
@app.route('/templates/<template_folder>')
def get_template(template_folder):
    """Endpoint to provide template files for front-end use"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, template_folder)
    
    if not os.path.exists(template_path):
        return jsonify({'error': 'Template not found'}), 404
        
    try:
        # Read template files
        html_path = os.path.join(template_path, 'email_template.html')
        config_path = os.path.join(template_path, 'config.ini')
        csv_path = os.path.join(template_path, 'recipients.csv')
        
        if not all(os.path.exists(p) for p in [html_path, config_path, csv_path]):
            return jsonify({'error': 'Template files incomplete'}), 404
            
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
            
        return jsonify({
            'html': html_content,
            'config': config_content,
            'csv': csv_content,
            'name': template_folder
        })
    except Exception as e:
        logging.exception(f"Error reading template: {e}")
        return jsonify({'error': str(e)}), 500
     

@app.route('/api/send', methods=['POST'])
def send_emails():
    """API endpoint to send emails using uploaded files."""
    temp_dir = None
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
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logging.exception("File saving error")
            return jsonify({'error': 'File processing error', 'details': str(e)}), 500

        # Validate email addresses
        try:
            validate_recipients_file(file_paths['recipients'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Run Chapar email sending process
        try:
            chapar.send_emails_from_files(file_paths['config'], file_paths['recipients'], file_paths['template'])
            result = {'status': 'success', 'message': 'Emails sent successfully'}
        except configparser.Error as e:
            return jsonify({'error': 'Configuration error', 'details': str(e)}), 400
        except smtplib.SMTPException as e:
            return jsonify({'error': 'SMTP error', 'details': str(e)}), 500
        except ValueError as e:
            return jsonify({'error': 'Validation error', 'details': str(e)}), 400
        except Exception as e:
            logging.error(f"Error during email dispatch: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

        return jsonify(result)

    except Exception as e:
        logging.exception("Unexpected error")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    
    finally:
        # Ensure cleanup happens even if an exception occurs
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.route('/api/health', methods=['GET'])
def health_check():
    """API endpoint for health check."""
    return jsonify({'status': 'healthy'})

@app.route('/api/debug', methods=['GET'])
def debug_info():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    result = {
        'current_directory': os.getcwd(),
        'base_directory': base_dir,
        'directories': []
    }
    
    try:
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                result['directories'].append({
                    'name': item,
                    'path': item_path,
                    'files': os.listdir(item_path)[:10]  # First 10 files for brevity
                })
    except Exception as e:
        result['error'] = str(e)
        
    return jsonify(result)


if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)