import docx
import re

class TextProcessor:
    def extract_text(self, docx_path):
        """
        Extract text from a Word document.
        """
        doc = docx.Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

    def split_text(self, text):
        """
        Split text into logical segments based on speaker changes and paragraph breaks.
        Works with any language including Georgian.
        Ensures contextual integrity between paragraphs.
        """
        segments = []
        # First split by paragraphs
        paragraphs = text.strip().split('\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Improved pattern for Georgian text
            # Matches names like "მზია:", "გამომძიებელი:", "ადვოკატი:", etc.
            speaker_match = re.match(r'^([\w\s-]+):(.+)', paragraph.strip(), re.UNICODE)
            
            if speaker_match:
                # There's a speaker, extract the name and content
                speaker = speaker_match.group(1).strip() + ":"
                content = speaker_match.group(2).strip()
                
                if content:
                    # Always keep speaker with content - never separate them
                    speaker_with_content = speaker + " " + content
                    
                    # Format into proper subtitle segments
                    content_parts = self._format_subtitle_text(speaker_with_content, keep_speaker=True)
                    segments.extend(content_parts)
                else:
                    # Speaker without content - find next paragraph with content to combine with
                    next_content_found = False
                    for next_idx in range(paragraphs.index(paragraph) + 1, len(paragraphs)):
                        next_para = paragraphs[next_idx].strip()
                        if next_para:
                            # Found next non-empty paragraph, combine with speaker
                            next_speaker_match = re.match(r'^([\w\s-]+):(.+)', next_para, re.UNICODE)
                            if next_speaker_match:
                                # Next paragraph also has a speaker, don't combine
                                break
                            else:
                                # Combine speaker with next paragraph
                                combined = speaker + " " + next_para
                                content_parts = self._format_subtitle_text(combined, keep_speaker=True)
                                segments.extend(content_parts)
                                next_content_found = True
                                # Skip this paragraph when we get to it
                                paragraphs[next_idx] = ""
                                break
                    
                    # If we couldn't find content to combine with, add speaker alone
                    if not next_content_found:
                        segments.append(speaker)
            else:
                # No speaker pattern - format as standard subtitle
                formatted_parts = self._format_subtitle_text(paragraph.strip())
                segments.extend(formatted_parts)
        
        # Filter out empty segments
        segments = [seg for seg in segments if seg.strip()]
        
        # Enhanced post-processing to combine segments more intelligently
        processed_segments = self._post_process_segments(segments)
        
        # Final pass to strictly enforce character limits
        enforced_segments = self._enforce_character_limit(processed_segments, max_chars=42)
        
        return enforced_segments
    
    def _post_process_segments(self, segments, max_chars=42):
        """
        Enhanced post-processing to combine segments more intelligently.
        - Combines very short segments (1-3 words)
        - Avoids splitting sentences across subtitles when possible
        - Ensures no subtitle is too short or too long
        - Ensures periods stay with preceding text
        - Limits to maximum 2 lines per subtitle
        - Never leaves speaker tags or 1-2 word segments alone
        - Properly handles speaker names that appear at segment boundaries
        """
        # First pass - fix BOTH speaker at end and at beginning of segments
        i = 0
        while i < len(segments) - 1:
            current = segments[i]
            next_segment = segments[i + 1]
            
            # Check if current segment ends with a speaker name
            speaker_at_end_match = re.search(r'([\w\s-]+):\s*$', current, re.UNICODE)
            if speaker_at_end_match:
                # Found speaker at the end, move it to the beginning of next segment
                speaker = speaker_at_end_match.group(0).strip()
                # Remove speaker from current segment
                segments[i] = current[:current.rfind(speaker)].strip()
                # Add to beginning of next segment
                segments[i + 1] = speaker + " " + next_segment
                # Don't increment i - check this segment again
                continue
            
            # Check if next segment begins with a speaker
            speaker_at_start_match = re.match(r'^([\w\s-]+):\s*', next_segment, re.UNICODE)
            if speaker_at_start_match:
                # Next segment begins with a speaker - make sure current segment ends properly
                # Only do this if current segment doesn't end with punctuation
                if not re.search(r'[.!?;:]$', current.strip()):
                    # Add period to current segment to complete it
                    segments[i] = current.strip() + "."
        
            i += 1
        
        # More aggressive second pass - properly format common Georgian speaker names
        known_speakers = ["მზია", "მოსამართლე", "გამომძიებელი", "ადვოკატი", "დარბაზიდან", "ბრალმდებელი", "მოწმე"]
        i = 0
        while i < len(segments):
            segment = segments[i]
            
            # Look for speaker patterns that might be split incorrectly
            for speaker in known_speakers:
                # Check for speaker at the end of segment
                speaker_pattern = speaker + ":"
                if segment.endswith(speaker_pattern):
                    # Speaker is at the end of segment - move to next segment if possible
                    if i + 1 < len(segments):
                        # Remove speaker from current segment
                        segments[i] = segment[:-len(speaker_pattern)].strip()
                        # Add to beginning of next segment
                        segments[i + 1] = speaker_pattern + " " + segments[i + 1]
                        # Don't increment i - check this segment again
                        continue
            
            # Check for incomplete dialogue (ending with ellipsis)
            if segment.strip().endswith("...") and i + 1 < len(segments):
                next_segment = segments[i + 1]
                # If next segment starts with speaker, keep as is
                if not any(next_segment.lstrip().startswith(sp + ":") for sp in known_speakers):
                    # Try to combine segments
                    if len(segment) + len(next_segment) <= max_chars * 2:
                        segments[i] = segment.strip() + " " + next_segment
                        segments.pop(i + 1)
                        continue
            
            i += 1

        # Third pass - check for single speaker names and merge them
        i = 0
        while i < len(segments) - 1:
            current = segments[i]
            next_segment = segments[i + 1]
            
            # If current segment is just a speaker name
            if any(current.strip() == sp + ":" for sp in known_speakers):
                # Always combine with next segment
                segments[i] = current.strip() + " " + next_segment
                segments.pop(i + 1)
                continue
                
            i += 1
        
        # Fourth pass - ensure no lines are too long
        processed_segments = []
        
        for segment in segments:
            # Check if segment contains a newline
            if '\n' in segment:
                lines = segment.split('\n')
                
                # Process each line to ensure it doesn't exceed max_chars
                for i in range(len(lines)):
                    if len(lines[i]) > max_chars:
                        # Split this line into words and rebuild it to fit max_chars
                        words = lines[i].split()
                        new_line = ""
                        for word in words:
                            if len(new_line) + len(word) + (1 if new_line else 0) <= max_chars:
                                new_line += " " + word if new_line else word
                            else:
                                break
                        lines[i] = new_line
                
                # Reconstruct the segment with fixed lines
                if len(lines) > 1:
                    processed_segments.append(lines[0] + "\n" + lines[1])
                else:
                    processed_segments.append(lines[0])
            else:
                # No newline, check if length exceeds max_chars
                if len(segment) > max_chars:
                    # Split into two lines
                    words = segment.split()
                    line1 = ""
                    line2 = ""
                    
                    for word in words:
                        if len(line1) + len(word) + (1 if line1 else 0) <= max_chars:
                            line1 += " " + word if line1 else word
                        elif len(line2) + len(word) + (1 if line2 else 0) <= max_chars:
                            line2 += " " + word if line2 else word
                        else:
                            break  # Can't fit more words
                    
                    if line2:
                        processed_segments.append(line1 + "\n" + line2)
                    else:
                        processed_segments.append(line1)
                else:
                    processed_segments.append(segment)
        
        # Fix period handling and other issues in a final pass
        result = []
        for segment in processed_segments:
            # Fix period dropping to next line
            if '\n' in segment and '.' in segment:
                lines = segment.split('\n')
                if lines[1].startswith('. '):
                    lines[0] += '.'
                    lines[1] = lines[1][2:].strip()
                    segment = lines[0] + '\n' + lines[1]
            
            # Fix other specific issues as needed
            result.append(segment)
        
        return result
    
    def _try_combine_segments(self, segment1, segment2, max_chars=42, allow_longer=False):
        """
        Try to combine two segments intelligently.
        Returns the combined segment if possible, None otherwise.
        """
        # Special case: If segment1 is a speaker tag alone, always combine
        if segment1.endswith(':') and len(segment1.split()) == 1:
            return segment1 + " " + segment2
        
        # Check if segment1 ends with a period - if so, don't combine
        if segment1.strip().endswith('.'):
            return None
        
        # Get total length without line breaks
        total_length = len(segment1.replace('\n', ' ')) + len(segment2.replace('\n', ' ')) + 1
        
        # If allow_longer is True, we can exceed max_chars*2 somewhat for better contextual integrity
        max_combined_length = max_chars * 2.2 if allow_longer else max_chars * 2
        
        if total_length <= max_combined_length:
            # Can be combined, decide how
            if "\n" in segment1:
                # Current already has a line break, handle carefully
                lines = segment1.split('\n')
                
                if len(lines) >= 2:
                    # If both lines are relatively short, we can add segment2 as a third line
                    # Otherwise just keep segment2 separate
                    if len(lines[0]) + len(lines[1]) <= max_chars * 1.5:
                        # Try to fit segment2 into second line if possible
                        if len(lines[1]) + len(segment2) + 1 <= max_chars:
                            return lines[0] + "\n" + lines[1] + " " + segment2
                    return None
                else:
                    # Only one line in segment1, can add segment2 as second line if it fits
                    if len(segment2) <= max_chars:
                        return segment1 + "\n" + segment2
                    return None
            elif len(segment1) + len(segment2) <= max_chars:
                # Both fit on one line
                return segment1 + " " + segment2
            else:
                # Need to split into two balanced lines
                combined_text = segment1 + " " + segment2
                words = combined_text.split()
                
                # Find optimal break point
                best_idx = self._find_optimal_break_point(words, max_chars)
                
                first_line = " ".join(words[:best_idx+1])
                second_line = " ".join(words[best_idx+1:])
                
                if len(first_line) <= max_chars and len(second_line) <= max_chars:
                    return first_line + "\n" + second_line
                    
        # Cannot be reasonably combined
        return None
    
    def _find_optimal_break_point(self, words, max_chars=42):
        """
        Find the optimal point to break a list of words into two balanced lines.
        Prefers breaking at punctuation or natural phrase boundaries.
        """
        total_text = " ".join(words)
        best_idx = 0
        best_balance = float('inf')
        
        # First try to find a punctuation break point
        for i, word in enumerate(words):
            if i > 0 and i < len(words) - 1:
                if word.endswith('.') or word.endswith('?') or word.endswith('!') or word.endswith(';') or word.endswith(':'):
                    first_line = " ".join(words[:i+1])
                    second_line = " ".join(words[i+1:])
                    if len(first_line) <= max_chars and len(second_line) <= max_chars:
                        return i  # Found a good punctuation break point
        
        # If no good punctuation break, try to balance the lines
        current_length = 0
        for i, word in enumerate(words):
            if i > 0:
                current_length += 1  # Space
            current_length += len(word)
            
            first_line_length = current_length
            second_line_length = len(total_text) - current_length
            
            # We prefer the break point that gives the most balanced lines
            # but still keeps each line under max_chars
            if (first_line_length <= max_chars and second_line_length <= max_chars):
                balance = abs(first_line_length - second_line_length)
                if balance < best_balance:
                    best_idx = i
                    best_balance = balance
        
        return best_idx
    
    def _format_subtitle_text(self, text, max_chars=42, keep_speaker=False):
        """
        Format text into proper subtitle format with maximum 2 lines
        and maximum characters per line for better readability.
        Strictly enforces the max_chars limit per line.
        """
        if len(text) <= max_chars:
            return [text]  # Text fits in one line
        
        if keep_speaker:
            # Extract speaker name
            speaker_match = re.match(r'^([\w\s-]+:)\s*(.+)', text, re.UNICODE)
            if speaker_match:
                speaker = speaker_match.group(1)
                content = speaker_match.group(2).strip()
                
                # Always keep speaker with at least some content
                first_space_idx = content.find(' ', max(0, max_chars - len(speaker) - 1))
                
                if first_space_idx > 0:
                    # Can split after some content
                    first_part_content = content[:first_space_idx]
                    remaining_content = content[first_space_idx+1:].strip()
                    
                    first_part = speaker + " " + first_part_content
                    
                    if len(first_part) <= max_chars and remaining_content:
                        # Format remaining text separately
                        remaining_segments = self._format_subtitle_text(remaining_content)
                        return [first_part] + remaining_segments
    
        # Stricter handling of line breaks to enforce the max_chars limit
        words = text.split()
        result = []
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed the max_chars limit
            if len(current_line) + len(word) + (1 if current_line else 0) <= max_chars:
                # Can add to current line
                current_line += " " + word if current_line else word
            else:
                # Current line is full, start a new one
                if current_line:
                    result.append(current_line)
                current_line = word
                
                # If this single word is longer than max_chars, we need to break it
                if len(word) > max_chars:
                    # Break the word into chunks of max_chars
                    while len(current_line) > max_chars:
                        result.append(current_line[:max_chars])
                        current_line = current_line[max_chars:]
    
        # Add the last line if there's anything left
        if current_line:
            result.append(current_line)
    
        # Now ensure we have at most two lines per segment
        segments = []
        for i in range(0, len(result), 2):
            if i+1 < len(result):
                segments.append(f"{result[i]}\n{result[i+1]}")
            else:
                segments.append(result[i])
    
        return segments
    
    def _break_into_two_lines(self, text, max_chars=42):
        """
        Break text into exactly two lines, respecting the max_chars limit strictly.
        Makes an intelligent break at a natural point in the sentence.
        """
        if len(text) <= max_chars:
            return [text]
        
        words = text.split()
        
        # Find the best break point
        best_break = 0
        current_length = 0
        
        for i, word in enumerate(words):
            # Calculate length if we add this word
            word_length = len(word) + (1 if current_length > 0 else 0)
            
            # If adding this word would exceed max_chars, the previous position was our break point
            if current_length + word_length > max_chars:
                best_break = i - 1
                break
            
            current_length += word_length
            
            # If we're at the last word, this is our break point
            if i == len(words) - 1:
                best_break = i
        
        # If we couldn't find a good break point (e.g., first word is too long)
        if best_break <= 0:
            best_break = 0  # Force break after first word
        
        first_line = " ".join(words[:best_break+1])
        second_line = " ".join(words[best_break+1:])
        
        # Handle case where second line might still be too long
        if len(second_line) > max_chars:
            second_words = second_line.split()
            second_line = ""
            for word in second_words:
                if len(second_line) + len(word) + (1 if second_line else 0) <= max_chars:
                    second_line += " " + word if second_line else word
                else:
                    # If cannot fit all words in second line, truncate and add ellipsis
                    if not second_line.endswith('...'):
                        second_line = second_line.strip() + "..."
                    break
        
        return [f"{first_line}\n{second_line}"]

    def _enforce_character_limit(self, segments, max_chars=42):
        """
        Final pass to strictly enforce the character limit per line, even if it means 
        breaking sentences in less ideal places.
        """
        enforced_segments = []
        
        for segment in segments:
            if '\n' in segment:
                lines = segment.split('\n')
                
                # Process each line independently
                processed_lines = []
                for line in lines:
                    if len(line) <= max_chars:
                        processed_lines.append(line)
                    else:
                        # Line is too long, need to split it
                        words = line.split()
                        current = ""
                        
                        for word in words:
                            if len(current) + len(word) + (1 if current else 0) <= max_chars:
                                current += " " + word if current else word
                            else:
                                # Current word would exceed max_chars
                                processed_lines.append(current)
                                current = word
                        
                        if current:
                            processed_lines.append(current)
                
                # Create new segments with max 2 lines per segment
                for i in range(0, len(processed_lines), 2):
                    if i + 1 < len(processed_lines):
                        enforced_segments.append(processed_lines[i] + '\n' + processed_lines[i+1])
                    else:
                        enforced_segments.append(processed_lines[i])
            
            else:
                # No line break yet
                if len(segment) <= max_chars:
                    enforced_segments.append(segment)
                else:
                    # Need to split this long line
                    words = segment.split()
                    lines = []
                    current = ""
                    
                    for word in words:
                        if len(current) + len(word) + (1 if current else 0) <= max_chars:
                            current += " " + word if current else word
                        else:
                            lines.append(current)
                            current = word
                    
                    if current:
                        lines.append(current)
                    
                    # Create segments with max 2 lines each
                    for i in range(0, len(lines), 2):
                        if i + 1 < len(lines):
                            enforced_segments.append(lines[i] + '\n' + lines[i+1])
                        else:
                            enforced_segments.append(lines[i])
        
        return enforced_segments