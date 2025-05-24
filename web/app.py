from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
import sys
import tempfile
import json
import logging
import traceback

# Add the src directory to the path so we can import our modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("Loaded environment variables from .env file")
except ImportError:
    logging.warning("python-dotenv not installed, skipping .env file loading")

# Import our converter modules (after environment variables are loaded)
from src.text_processor import TextProcessor
from src.timestamp_generator import TimestampGenerator
from src.converter import Converter
from src.audio_processor import AudioProcessor, get_google_credentials

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize our components
text_processor = TextProcessor()
timestamp_generator = TimestampGenerator()
converter = Converter(text_processor, timestamp_generator)

# Initialize audio processor
audio_processor = AudioProcessor()

# Print diagnostic info for debugging
logging.info(f"AudioProcessor client initialized: {audio_processor.client is not None}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    # Check if file was uploaded
    if 'docx_file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['docx_file']
    
    # Check if file is valid
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not file.filename.lower().endswith('.docx'):
        flash('Only DOCX files are supported')
        return redirect(url_for('index'))
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded file
        docx_path = os.path.join(temp_dir, file.filename)
        file.save(docx_path)
        
        # Create output path
        srt_filename = os.path.splitext(file.filename)[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        # Convert file
        converter.convert_docx_to_srt(docx_path, srt_path)
        
        # Return the converted file
        return send_file(
            srt_path,
            as_attachment=True,
            download_name=srt_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        flash(f'Error during conversion: {str(e)}')
        return redirect(url_for('index'))

@app.route('/transcribe', methods=['POST'])
def transcribe():
    # Check if file was uploaded
    if 'audio_file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['audio_file']
    
    # Check if file is valid
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    # Check file extension
    allowed_extensions = ['.mp3', '.wav', '.flac', '.ogg']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        flash(f'Only {", ".join(allowed_extensions)} files are supported')
        return redirect(url_for('index'))
    
    try:
        # Verify the audio processor client is initialized
        if not audio_processor.client:
            logging.error("Speech client not initialized, attempting reinitialize")
            try:
                # Try to reinitialize using direct credentials
                from src.credentials import get_google_credentials_direct
                credentials = get_google_credentials_direct()
                if credentials:
                    audio_processor.client = speech.SpeechClient(credentials=credentials)
                    logging.info("Successfully reinitialized Google Speech client")
            except Exception as reinit_error:
                logging.error(f"Failed to reinitialize client: {reinit_error}")
                
            # Final check if client is available
            if not audio_processor.client:
                flash('Google Speech API not available. Check server configuration.')
                return redirect(url_for('index'))
        
        # Create temp directory that's compatible with the environment
        if os.environ.get('VERCEL'):
            temp_dir = '/tmp'
            os.makedirs(temp_dir, exist_ok=True)
        else:
            temp_dir = tempfile.mkdtemp()
        
        # Save uploaded file
        audio_path = os.path.join(temp_dir, file.filename)
        file.save(audio_path)
        
        # Create output path
        srt_filename = os.path.splitext(file.filename)[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        # Process the audio file
        results = audio_processor.transcribe_file(audio_path)
        
        # Convert to SRT
        audio_processor.convert_to_srt(results, text_processor, srt_path)
        
        # Return the SRT file
        return send_file(
            srt_path,
            as_attachment=True,
            download_name=srt_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logging.error(f"Error during transcription: {str(e)}")
        logging.error(traceback.format_exc())
        flash(f'Error during transcription: {str(e)}')
        return redirect(url_for('index'))

# Modify your debug_credentials route to avoid circular imports
@app.route('/debug-credentials')
def debug_credentials():
    """Debug route to check credentials status"""
    result = {
        'env_vars_present': {
            'GOOGLE_PROJECT_ID': bool(os.environ.get('GOOGLE_PROJECT_ID')),
            'GOOGLE_CLIENT_EMAIL': bool(os.environ.get('GOOGLE_CLIENT_EMAIL')),
            'GOOGLE_PRIVATE_KEY': bool(os.environ.get('GOOGLE_PRIVATE_KEY'))
        },
        'app_credentials_path': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set'),
        'current_audio_processor_client': bool(audio_processor.client)
    }
    
    # Test local credentials function
    try:
        local_credentials_path = get_google_credentials()
        result['local_credentials_path'] = local_credentials_path
        result['local_credentials_file_exists'] = os.path.exists(local_credentials_path) if local_credentials_path else False
    except Exception as e:
        result['local_credentials_error'] = str(e)
    
    return result

# For local development
if __name__ == '__main__':
    app.run(debug=True)