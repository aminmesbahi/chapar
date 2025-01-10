# chapar_api.py
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import chapar
import configparser
import tempfile
import shutil

app = Flask(__name__)

# Configure upload folder for temporary files
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'html', 'csv', 'ini'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/send', methods=['POST'])
def send_emails():
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

        for key, filename in files.items():
            if key not in request.files:
                shutil.rmtree(temp_dir)
                return jsonify({'error': f'Missing {key} file'}), 400
            
            file = request.files[key]
            if not allowed_file(file.filename):
                shutil.rmtree(temp_dir)
                return jsonify({'error': f'Invalid file type for {key}'}), 400
            
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)

        # Run Chapar email sending process
        try:
            chapar.main(temp_dir)
            result = {'status': 'success', 'message': 'Emails sent successfully'}
        except Exception as e:
            result = {'status': 'error', 'message': str(e)}

        # Cleanup
        shutil.rmtree(temp_dir)
        
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)