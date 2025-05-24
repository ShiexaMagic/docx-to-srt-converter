from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
import sys
import tempfile
import json

# Add the src directory to the path so we can import our modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, 'src'))

# Import our converter modules
from text_processor import TextProcessor
from timestamp_generator import TimestampGenerator
from converter import Converter
from src.audio_processor import AudioProcessor

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize our converter components
text_processor = TextProcessor()
timestamp_generator = TimestampGenerator()
converter = Converter(text_processor, timestamp_generator)

# Add this code to handle credentials securely
if os.environ.get('GOOGLE_CREDENTIALS'):
    # Create credentials file from environment variable on Vercel
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    credentials_path = 'google_credentials_temp.json'
    with open(credentials_path, 'w') as f:
        f.write(creds_json)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
else:
    # Look for credentials file locally
    if os.path.exists('google_credentials.json'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google_credentials.json'

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
        # Create temp directory for file processing
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded file
        docx_path = os.path.join(temp_dir, file.filename)
        file.save(docx_path)
        
        # Generate output path
        srt_filename = os.path.splitext(file.filename)[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        # Convert file
        converter.convert_docx_to_srt(docx_path, srt_path)
        
        # Send the converted file
        return send_file(
            srt_path,
            as_attachment=True,
            download_name=srt_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        flash(f'Error during conversion: {str(e)}')
        return redirect(url_for('index'))

@app.route('/audio')
def audio_page():
    return render_template('audio.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    # Check if file was uploaded
    if 'audio_file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('audio_page'))
    
    file = request.files['audio_file']
    
    # Check if file is valid
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('audio_page'))
    
    # Check file extension
    allowed_extensions = ['.mp3', '.wav', '.flac', '.ogg']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        flash(f'Only {", ".join(allowed_extensions)} files are supported')
        return redirect(url_for('audio_page'))
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded file
        audio_path = os.path.join(temp_dir, file.filename)
        file.save(audio_path)
        
        # Create output path
        srt_filename = os.path.splitext(file.filename)[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        # Initialize processors
        audio_processor = AudioProcessor()
        
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
        flash(f'Error during transcription: {str(e)}')
        return redirect(url_for('audio_page'))

# For local development
if __name__ == '__main__':
    app.run(debug=True)