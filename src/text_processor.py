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
        
        return processed_segments
    
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
        
        # Continue with original processing logic
        # [Keep existing post-processing code...]
        
        return segments
    
    def _post_process_segments(self, segments, max_chars=42):
        """
        Enhanced post-processing to combine segments more intelligently.
        - Combines very short segments (1-3 words)
        - Avoids splitting sentences across subtitles when possible
        - Ensures no subtitle is too short or too long
        - Ensures periods stay with preceding text
        - Limits to maximum 2 lines per subtitle
        - Never leaves speaker tags or 1-2 word segments alone
        """
        # First pass - aggressively combine speaker-only or very short segments
        i = 0
        while i < len(segments) - 1:
            current = segments[i]
            next_segment = segments[i + 1]
            
            # If current segment is just a speaker tag, always combine with next
            if current.endswith(':') and len(current.split()) <= 2:
                segments[i] = current + " " + next_segment
                segments.pop(i + 1)
                continue
                
            # If next segment is very short (1-2 words or ending with period)
            next_word_count = len(next_segment.split())
            if next_word_count <= 2 or (next_segment.strip().endswith('.') and next_word_count <= 4):
                # Always try to combine very short segments
                if "\n" in current:
                    # Current already has a line break
                    lines = current.split('\n')
                    if len(lines[1]) + len(next_segment) + 1 <= max_chars:
                        # Can fit next segment in second line
                        segments[i] = lines[0] + "\n" + lines[1] + " " + next_segment
                    else:
                        # Create a balanced 2-line segment
                        combined = current.replace('\n', ' ') + " " + next_segment
                        words = combined.split()
                        
                        # Find balanced break point
                        total_chars = len(combined)
                        best_break = len(words) // 2
                        
                        for j in range(1, len(words)):
                            first_part = " ".join(words[:j])
                            second_part = " ".join(words[j:])
                            
                            if len(first_part) <= max_chars and len(second_part) <= max_chars:
                                if abs(len(first_part) - len(second_part)) < abs(len(" ".join(words[:best_break])) - len(" ".join(words[best_break:]))):
                                    best_break = j
                    
                        segments[i] = " ".join(words[:best_break]) + "\n" + " ".join(words[best_break:])
                elif len(current) + len(next_segment) + 1 <= max_chars:
                    # Can fit on one line
                    segments[i] = current + " " + next_segment
                else:
                    # Create a 2-line segment
                    segments[i] = current + "\n" + next_segment
                    
                # Remove the next segment since we combined it
                segments.pop(i + 1)
                continue
                
            i += 1
        
        # Continue with standard processing
        processed_segments = []
        i = 0
        
        while i < len(segments):
            current_segment = segments[i]
            
            # First, ensure no segment has more than 2 lines
            if current_segment.count('\n') > 1:
                lines = current_segment.split('\n')
                current_segment = lines[0] + '\n' + lines[1]
                # Add remaining lines as separate segments
                for j in range(2, len(lines)):
                    if lines[j].strip():
                        segments.insert(i+1, lines[j])
        
            # Check if we can combine with next segment
            if i + 1 < len(segments):
                next_segment = segments[i + 1]
                next_word_count = len(next_segment.split())
                next_char_count = len(next_segment)
                
                # Check for period at end of current segment
                ends_with_period = re.search(r'\.\s*$', current_segment)
                
                # More aggressive combination for short segments (up to 5 words or 25 characters)
                if next_word_count <= 5 or next_char_count <= 25:
                    # If current ends with period, next segment should start a new subtitle
                    if not ends_with_period:
                        # Check if we can combine them
                        combined = self._try_combine_segments(current_segment, next_segment, max_chars)
                        
                        if combined:
                            processed_segments.append(combined)
                            i += 2  # Skip next segment since we combined it
                            continue
            
                # Check for incomplete sentences (no ending punctuation)
                if not re.search(r'[.!?;:]$', current_segment.replace('\n', '').strip()):
                    # Current segment doesn't end with punctuation
                    combined = self._try_combine_segments(current_segment, next_segment, max_chars, allow_longer=True)
                    
                    if combined:
                        processed_segments.append(combined)
                        i += 2  # Skip next segment
                        continue
        
            processed_segments.append(current_segment)
            i += 1
        
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
        Respects sentence structure and contextual meaning.
        """
        if len(text) <= max_chars:
            return [text]  # Text fits in one line
        
        if keep_speaker:
            # Extract speaker name and make sure it stays with content
            speaker_match = re.match(r'^([\w\s-]+:)\s*(.+)', text, re.UNICODE)
            if speaker_match:
                speaker = speaker_match.group(1)
                content = speaker_match.group(2).strip()
                
                # Always keep speaker with at least some content
                first_space_idx = content.find(' ', max_chars - len(speaker) - 1)
                
                if first_space_idx > 0:
                    # Can split after some content
                    first_part_content = content[:first_space_idx]
                    remaining_content = content[first_space_idx+1:].strip()
                    
                    first_part = speaker + " " + first_part_content
                    
                    if len(first_part) <= max_chars and remaining_content:
                        # Format remaining text separately
                        remaining_segments = self._format_subtitle_text(remaining_content)
                        return [first_part] + remaining_segments
        
        # Standard processing
        # First try to split at periods for logical breaks
        if '.' in text and not text.endswith('.'):
            period_idx = text.rfind('.')
            if period_idx > 0 and period_idx < len(text) - 1:
                first_part = text[:period_idx + 1].strip()
                second_part = text[period_idx + 1:].strip()
                
                if len(first_part) <= max_chars and second_part:
                    # Format remaining text ცალკე
                    remaining_segments = self._format_subtitle_text(second_part)
                    return [first_part] + remaining_segments
        
        # Try to split into sentences for logical breaks
        sentences = re.split(r'([.!?;:](?:\s|$))', text)
        
        # Recombine sentences with their punctuation
        full_sentences = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and re.match(r'[.!?;:](?:\s|$)', sentences[i+1]):
                full_sentences.append(sentences[i] + sentences[i+1])
                i += 2
            else:
                if sentences[i].strip():
                    full_sentences.append(sentences[i])
                i += 1
        
        # Now format each sentence appropriately
        result = []
        current_segment = ""
        
        for sentence in full_sentences:
            if len(current_segment) + len(sentence) <= max_chars:
                # Can fit this sentence in current segment
                current_segment += sentence
            else:
                if current_segment:
                    # Current segment is already non-empty
                    if len(sentence) <= max_chars:
                        # If the next sentence can be a segment by itself
                        # First add the current segment
                        result.append(current_segment.strip())
                        current_segment = sentence
                    else:
                        # Need to break the sentence intelligently
                        if current_segment.strip():
                            result.append(current_segment.strip())
                        
                        # Format this longer sentence into two-line segments
                        line_segments = self._break_into_two_lines(sentence, max_chars)
                        result.extend(line_segments)
                        current_segment = ""
                else:
                    # Current segment is empty, format this sentence
                    line_segments = self._break_into_two_lines(sentence, max_chars)
                    result.extend(line_segments)
        
        # Add any remaining text
        if current_segment.strip():
            result.append(current_segment.strip())
        
        return result
    
    def _break_into_two_lines(self, text, max_chars=42):
        """
        Break text into segments of two lines maximum, respecting word boundaries
        and ensuring each segment has at most max_chars per line.
        
        Makes intelligent breaks at natural points in the sentence rather than
        simply filling the first line to maximum capacity.
        """
        if len(text) <= max_chars:
            return [text]
        
        # Fix period handling - ensure periods stay with preceding text
        text = re.sub(r'([.!?;:])(\s)', r'\1\2', text)
        
        words = text.split()
        total_length = len(text)
        
        # If the total text is suitable for a two-line subtitle (up to 2*max_chars)
        if total_length <= max_chars * 2:
            # Try to find a natural break point first (after a period, comma, etc.)
            for i in range(len(words) - 1):
                if words[i].endswith('.') or words[i].endswith(',') or words[i].endswith(';') or words[i].endswith(':'):
                    first_part = " ".join(words[:i+1])
                    second_part = " ".join(words[i+1:])
                    if len(first_part) <= max_chars and len(second_part) <= max_chars:
                        return [f"{first_part}\n{second_part}"]
            
            # If no natural break, find the most balanced point
            best_idx = self._find_optimal_break_point(words, max_chars)
            
            # Create the two lines based on the best break point
            if best_idx > 0:
                first_line = " ".join(words[:best_idx+1])
                second_line = " ".join(words[best_idx+1:])
                return [f"{first_line}\n{second_line}"]
        
        # For longer text, break into multiple segments
        result = []
        current_line1 = ""
        current_line2 = ""
        
        for word in words:
            # Try to add to first line
            if len(current_line1) + len(word) + (1 if current_line1 else 0) <= max_chars:
                current_line1 += " " + word if current_line1 else word
            # Try to add to second line
            elif len(current_line2) + len(word) + (1 if current_line2 else 0) <= max_chars:
                current_line2 += " " + word if current_line2 else word
            # Both lines are full, create a new segment
            else:
                if current_line1 and current_line2:
                    # We have two lines filled
                    segment = current_line1
                    if current_line2:
                        segment += "\n" + current_line2
                    result.append(segment)
                    
                    # Reset lines and start with current word
                    current_line1 = word
                    current_line2 = ""
                else:
                    # First line is too long already
                    result.append(current_line1)
                    current_line1 = word
                    current_line2 = ""
        
        # Add remaining content
        if current_line1 or current_line2:
            segment = current_line1
            if current_line2:
                segment += "\n" + current_line2
            result.append(segment)
        
        return result