from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import os
import sys
import tempfile

# Add the src directory to the path so we can import our modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, 'src'))

# Import our converter modules
from text_processor import TextProcessor
from timestamp_generator import TimestampGenerator
from converter import Converter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize our converter components
text_processor = TextProcessor()
timestamp_generator = TimestampGenerator()
converter = Converter(text_processor, timestamp_generator)

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

# For local development
if __name__ == '__main__':
    app.run(debug=True)