class TimestampGenerator:
    def generate_timestamps(self, segments):
        timestamps = []
        start_time = 0  # Start at 0 seconds

        for segment in segments:
            end_time = start_time + len(segment.split()) * 0.5  # Assuming 2 words per second
            timestamps.append((start_time, end_time))
            start_time = end_time  # Update start time for the next segment

        return timestamps

# Modification for timestamp_generator.py
def format_timestamp(seconds):
    """
    Format seconds into SRT timestamp format: HH:MM:SS,mmm
    Note the comma instead of period for milliseconds
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    # Use comma instead of period for milliseconds
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")