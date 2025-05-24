from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
import sys
import tempfile
import json
from google.cloud import speech
import io
import traceback
import logging

# Add the src directory to the path so we can import our modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, 'src'))

# Import our converter modules
from text_processor import TextProcessor
from timestamp_generator import TimestampGenerator
from converter import Converter

# Set up logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip for production

# Handle Google Cloud credentials
def get_google_credentials():
    """Get Google credentials from environment variables or file"""
    try:
        # Check if running on Vercel with environment variables
        if os.environ.get('GOOGLE_PRIVATE_KEY') and os.environ.get('GOOGLE_CLIENT_EMAIL'):
            logging.info("Found Google credentials in environment variables")
            
            # Get private key and fix formatting issues
            private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
            
            # Ensure proper newlines in the private key
            if r'\n' in private_key and '\n' not in private_key:
                private_key = private_key.replace(r'\n', '\n')
            
            # Make sure private key has proper format
            if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                logging.error("Private key does not have correct format")
                return None
                
            # Create credentials from environment variables
            credentials_dict = {
                "type": "service_account",
                "project_id": os.environ.get('GOOGLE_PROJECT_ID', ''),
                "private_key": private_key,
                "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('GOOGLE_CLIENT_EMAIL', '').replace('@', '%40')}",
                "universe_domain": "googleapis.com"
            }
            
            # Create temp credentials file for library to use
            try:
                credentials_path = '/tmp/google_credentials_temp.json'
                
                # Debug the content being written (masked for security)
                logging.info(f"Writing credentials file to {credentials_path}")
                logging.info(f"Project ID: {credentials_dict['project_id']}")
                logging.info(f"Client email: {credentials_dict['client_email']}")
                logging.info(f"Private key format looks correct: {private_key.startswith('-----BEGIN PRIVATE KEY-----')}")
                
                with open(credentials_path, 'w') as f:
                    json.dump(credentials_dict, f)
                
                # Verify the file was created successfully
                if os.path.exists(credentials_path):
                    logging.info(f"Credentials file created successfully: {os.path.getsize(credentials_path)} bytes")
                    return credentials_path
                else:
                    logging.error("Credentials file was not created")
                    return None
                    
            except Exception as e:
                logging.error(f"Error creating credentials file: {str(e)}")
                logging.error(traceback.format_exc())
                return None
        
        # Check for credentials file
        elif os.path.exists('google_credentials.json'):
            logging.info("Found google_credentials.json file")
            return 'google_credentials.json'
        
        logging.warning("No Google credentials found")
        return None
    except Exception as e:
        logging.error(f"Error in get_google_credentials: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Set up Google credentials if available
credentials_path = get_google_credentials()
if credentials_path:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# Audio processing class
class AudioProcessor:
    def __init__(self):
        """Initialize the AudioProcessor with Google Cloud credentials."""
        self.client = None
        try:
            if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                logging.info(f"Using credentials from: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
            else:
                logging.warning("GOOGLE_APPLICATION_CREDENTIALS not set")
                
            self.client = speech.SpeechClient()
            logging.info("Successfully initialized Google Speech client")
        except Exception as e:
            logging.error(f"Error initializing Google Speech client: {str(e)}")
            logging.error(traceback.format_exc())

    def transcribe_file(self, audio_path):
        """Transcribes audio file using Google Speech-to-Text API with Georgian language."""
        if not self.client:
            raise ValueError("Google Speech client not initialized. Check credentials.")
            
        # Read the audio file
        with io.open(audio_path, "rb") as audio_file:
            content = audio_file.read()
            
        # Configure the request
        audio = speech.RecognitionAudio(content=content)
        
        # Configure recognition with Georgian language
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,  # Adjust based on your audio
            language_code="ka-GE",    # Georgian language code
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,  # Enable word-level timestamps
            model="default"
        )
        
        # Make the API call
        operation = self.client.long_running_recognize(config=config, audio=audio)
        print("Waiting for operation to complete...")
        response = operation.result(timeout=90)
        
        return response.results
        
    def convert_to_srt(self, results, text_processor, output_path):
        """Converts Google Speech-to-Text results to SRT format."""
        # Extract sentences with start/end times
        segments = []
        
        for result in results:
            if not result.alternatives:
                continue
                
            transcript = result.alternatives[0].transcript.strip()
            if not transcript:
                continue
                
            # Get the first and last word's timestamps
            words = result.alternatives[0].words
            if not words:
                continue
                
            start_time = words[0].start_time
            end_time = words[-1].end_time
            
            # Add segment with start/end times
            segments.append({
                "text": transcript,
                "start_time": start_time.total_seconds(),
                "end_time": end_time.total_seconds()
            })
        
        # Process segments with TextProcessor to enforce character limits
        processed_segments = []
        for segment in segments:
            text_segments = text_processor._enforce_character_limit([segment["text"]], max_chars=42)
            for text_seg in text_segments:
                processed_segments.append({
                    "text": text_seg,
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"]
                })
        
        # Generate SRT file
        with open(output_path, "w", encoding="utf-8") as srt_file:
            for i, segment in enumerate(processed_segments):
                start = self._format_timestamp(segment["start_time"])
                end = self._format_timestamp(segment["end_time"])
                
                srt_file.write(f"{i+1}\n")
                srt_file.write(f"{start} --> {end}\n")
                srt_file.write(f"{segment['text']}\n\n")
                
        return output_path
    
    def _format_timestamp(self, seconds):
        """Convert seconds to SRT timestamp format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        msecs = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"

# Initialize our components
text_processor = TextProcessor()
timestamp_generator = TimestampGenerator()
converter = Converter(text_processor, timestamp_generator)
audio_processor = AudioProcessor()

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
        # Check if Google client is initialized
        if not audio_processor.client:
            # Try to initialize again
            logging.info("Attempting to reinitialize Google Speech client")
            credentials_path = get_google_credentials()
            
            if credentials_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                audio_processor.client = speech.SpeechClient()
                
            # If still not initialized, show error
            if not audio_processor.client:
                flash('Google Speech API not available. Please check server configuration.')
                return redirect(url_for('index'))
        
        # Create temp directory that works on Vercel
        if os.environ.get('VERCEL'):
            temp_dir = '/tmp'
            os.makedirs(temp_dir, exist_ok=True)
        else:
            temp_dir = tempfile.mkdtemp()
        
        logging.info(f"Using temp directory: {temp_dir}")
        
        # Save uploaded file
        audio_path = os.path.join(temp_dir, file.filename)
        file.save(audio_path)
        
        # Create output path
        srt_filename = os.path.splitext(file.filename)[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        # Log file details
        logging.info(f"Processing audio file: {audio_path} ({os.path.getsize(audio_path)} bytes)")
        
        # Process the audio file
        results = audio_processor.transcribe_file(audio_path)
        
        # Convert to SRT
        audio_processor.convert_to_srt(results, text_processor, srt_path)
        
        # Return the converted file
        return send_file(
            srt_path,
            as_attachment=True,
            download_name=srt_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logging.error(f"Error in transcribe route: {str(e)}")
        logging.error(traceback.format_exc())
        flash(f'Error during transcription: {str(e)}')
        return redirect(url_for('index'))

# For local development
if __name__ == '__main__':
    app.run(debug=True)