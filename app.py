import os
import dotenv
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from pypdf import PdfReader
import requests
from flask_cors import CORS  # Import CORS
import json
import re

# Load environment variables
dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['UPLOAD_FOLDER'] = 'uploads'

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Handle file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdfFile' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['pdfFile']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Extract text from PDF
    extracted_text = extract_text_from_pdf(file_path)
    if not extracted_text:
        return jsonify({'error': 'Could not extract text from PDF'}), 500

    # Use GPT model via OpenRouter API to extract fields and values
    extracted_data = extract_data_with_gpt(extracted_text)
    return jsonify({'extracted_data': extracted_data})

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    try:
        text = ''
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ''
        return text.strip()
    except Exception as e:
        print(f'Error extracting text: {e}')
        return None

# Function to extract data using GPT via OpenRouter API
def extract_data_with_gpt(text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {
                "role": "user",
                "content": f"Extract structured key-value pairs from this invoice and return only valid JSON output. Do not include markdown formatting or explanations:\n\n{text}"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        # Debugging: Print API response
        print("GPT API Raw Response:", response_data)

        # Extract the content field
        extracted_text = response_data['choices'][0]['message']['content']

        # Remove Markdown-style code block markers (```json ... ```)
        extracted_text = re.sub(r"```json\n(.*?)\n```", r"\1", extracted_text, flags=re.DOTALL).strip()

        # Try parsing the cleaned response as JSON
        return json.loads(extracted_text)

    except json.JSONDecodeError as json_err:
        print("Invalid JSON received:", extracted_text)
        return {'error': 'Invalid JSON format from GPT API'}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from GPT API: {e}")
        return {'error': 'Failed to fetch data from GPT API'}

# Run the app
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(host='0.0.0.0', port=8000, debug=True)
