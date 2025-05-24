import os
from google.cloud import speech
import io

class AudioProcessor:
    def __init__(self, credentials_path=None):
        """Initialize the AudioProcessor with Google Cloud credentials."""
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.client = speech.SpeechClient()
    
    def transcribe_file(self, audio_path):
        """Transcribes audio file using Google Speech-to-Text API with Georgian language."""
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