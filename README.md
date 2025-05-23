# DOCX to SRT Subtitle Converter

A web application that converts DOCX documents to SRT subtitle format.

## Features

- Upload DOCX files through a simple web interface
- Convert text documents to properly formatted SRT subtitles
- Support for speaker identification and subtitle timing
- Works with multiple languages, including Georgian

## Deployment

This application is deployed on Vercel.

## Local Development

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   python src/main.py
   ```

3. Follow the prompts to upload your Word document and generate the SRT file.

## Project Structure

```
docx-to-srt-converter
├── src
│   ├── __init__.py
│   ├── main.py
│   ├── converter.py
│   ├── text_processor.py
│   ├── timestamp_generator.py
│   └── utils
│       ├── __init__.py
│       └── file_handler.py
├── tests
│   ├── __init__.py
│   ├── test_converter.py
│   ├── test_text_processor.py
│   └── test_timestamp_generator.py
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore
```

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.