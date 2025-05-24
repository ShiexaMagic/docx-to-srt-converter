import os
from google.cloud import speech
import io
import logging
import traceback
import json
import subprocess
import tempfile

# Fix the import to include both functions
from src.credentials import get_google_credentials_direct

# Add the missing function directly in audio_processor.py
def get_google_credentials():
    """Get Google credentials from environment variables or file"""
    try:
        # Check if running with environment variables
        if os.environ.get('GOOGLE_PRIVATE_KEY') and os.environ.get('GOOGLE_CLIENT_EMAIL'):
            logging.info("Found Google credentials in environment variables")
            
            # Get private key and fix formatting issues
            private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
            
            # Ensure proper newlines in the private key
            if r'\n' in private_key and '\n' not in private_key:
                private_key = private_key.replace(r'\n', '\n')
            
            # Create temp credentials file for library to use
            try:
                if os.environ.get('VERCEL'):
                    credentials_path = '/tmp/google_credentials_temp.json'
                else:
                    credentials_path = 'google_credentials_temp.json'
                
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
                
                with open(credentials_path, 'w') as f:
                    json.dump(credentials_dict, f)
                
                logging.info(f"Created credentials file at {credentials_path}")
                return credentials_path
            except Exception as e:
                logging.error(f"Error creating credentials file: {str(e)}")
                return None
        
        # Check for credentials file
        elif os.path.exists('google_credentials.json'):
            logging.info("Found google_credentials.json file")
            return 'google_credentials.json'
        
        logging.warning("No Google credentials found")
        return None
    except Exception as e:
        logging.error(f"Error in get_google_credentials: {str(e)}")
        return None

class AudioProcessor:
    def __init__(self):
        """Initialize the AudioProcessor with Google Cloud credentials."""
        self.client = None
        try:
            # First try to get direct credentials
            credentials = get_google_credentials_direct()
            if credentials:
                logging.info("Using direct credentials")
                self.client = speech.SpeechClient(credentials=credentials)
                logging.info("Successfully initialized Google Speech client with direct credentials")
                return
                
            # Fall back to file-based credentials
            credentials_path = get_google_credentials()
            if credentials_path:
                logging.info(f"Using credentials file: {credentials_path}")
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                self.client = speech.SpeechClient()
                logging.info("Successfully initialized Google Speech client with file credentials")
                return
                
            logging.error("Failed to obtain Google credentials")
            
        except Exception as e:
            logging.error(f"Error initializing Google Speech client: {str(e)}")
            logging.error(traceback.format_exc())
    
    def transcribe_file(self, audio_path):
        """Transcribes audio file using Google Speech-to-Text API."""
        if not self.client:
            raise ValueError("Google Speech client not initialized. Check credentials.")
        
        # Get file extension
        file_ext = os.path.splitext(audio_path)[1].lower()
        
        # Special handling for MP3 files
        if file_ext == '.mp3':
            logging.info("Using special handling for MP3 file")
            import base64
            
            # Read MP3 file as base64
            with open(audio_path, "rb") as mp3_file:
                mp3_content = mp3_file.read()
                
            # Create audio content using base64 encoding
            audio = speech.RecognitionAudio(content=mp3_content)
            
            # Configure with MP3 encoding explicitly
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                sample_rate_hertz=16000,  
                language_code="ka-GE",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="default"
            )
        else:
            # Normal handling for other file types
            with io.open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            
            # Set encoding based on file type
            if file_ext == '.flac':
                encoding = speech.RecognitionConfig.AudioEncoding.FLAC
            elif file_ext == '.ogg':
                encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
            else:  # Default for WAV and other formats
                encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
            
            # Configure the request
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code="ka-GE",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="default"
            )
        
        # Make the API call
        operation = self.client.long_running_recognize(config=config, audio=audio)
        logging.info("Waiting for operation to complete...")
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
    
    def convert_audio_if_needed(self, audio_path):
        """
        Convert audio to a format supported by Google Speech API if necessary.
        Returns path to the (possibly converted) audio file.
        """
        file_ext = os.path.splitext(audio_path)[1].lower()
        
        # If it's already a supported format, return the original path
        if file_ext in ['.flac', '.wav']:
            return audio_path
            
        try:
            # For MP3 and other formats, convert to FLAC
            output_path = os.path.splitext(audio_path)[0] + '.flac'
            
            # Use ffmpeg for conversion if available
            try:
                logging.info(f"Converting {file_ext} to FLAC format")
                subprocess.run(
                    ['ffmpeg', '-i', audio_path, '-ar', '16000', output_path],
                    check=True,
                    capture_output=True
                )
                return output_path
            except (subprocess.SubprocessError, FileNotFoundError):
                logging.warning("ffmpeg not available or conversion failed")
                return audio_path  # Fall back to original file
                
        except Exception as e:
            logging.error(f"Audio conversion failed: {e}")
            return audio_path  # Fall back to original file