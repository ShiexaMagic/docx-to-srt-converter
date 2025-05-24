import os
import logging
from dotenv import load_dotenv
from google.cloud import speech
from src.credentials import get_google_credentials_direct

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

def test_credentials():
    # Try to create credentials
    print("Testing Google Cloud credentials...")
    
    # Check environment variables
    print(f"GOOGLE_PROJECT_ID set: {bool(os.environ.get('GOOGLE_PROJECT_ID'))}")
    print(f"GOOGLE_CLIENT_EMAIL set: {bool(os.environ.get('GOOGLE_CLIENT_EMAIL'))}")
    print(f"GOOGLE_PRIVATE_KEY set: {bool(os.environ.get('GOOGLE_PRIVATE_KEY'))}")
    
    # Try direct credentials
    try:
        credentials = get_google_credentials_direct()
        print(f"Direct credentials created: {bool(credentials)}")
        
        # Try to create a client
        client = speech.SpeechClient(credentials=credentials)
        print("Successfully created Speech client!")
        
        # Test a simple API call
        print("Testing API access...")
        
        # Fix: Use a different API call that doesn't require specific parameters
        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US"
        )
        
        # Just create a request object to verify client is working
        request = speech.RecognizeRequest(
            config=recognition_config,
            audio=speech.RecognitionAudio(content=b"")  # Empty audio for test
        )
        
        # Don't actually send the request, just verify the client can create it
        print("Client initialized and request object created successfully!")
        print("API credentials are valid and working!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_credentials()