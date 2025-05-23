class Converter:
    def __init__(self, text_processor, timestamp_generator):
        self.text_processor = text_processor
        self.timestamp_generator = timestamp_generator

    def convert_docx_to_srt(self, docx_path, srt_path):
        text = self.text_processor.extract_text(docx_path)
        segments = self.text_processor.split_text(text)
        timestamps = self.timestamp_generator.generate_timestamps(segments)
        srt_content = self.format_srt(segments, timestamps)
        self.write_srt(srt_path, srt_content)
        return srt_path

    def format_srt(self, segments, timestamps):
        srt_lines = []
        for i, (segment, timestamp) in enumerate(zip(segments, timestamps)):
            srt_lines.append(self.format_srt_entry(i + 1, timestamp[0], timestamp[1], segment))
        return "\n".join(srt_lines)

    def format_srt_entry(self, index, start_time, end_time, text):
        """
        Format a subtitle entry according to SRT standards.
        """
        # Ensure timestamps are formatted correctly: HH:MM:SS,mmm --> HH:MM:SS,mmm
        return f"{index}\n{start_time} --> {end_time}\n{text}\n\n"

    def write_srt(self, srt_path, content):
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(content)