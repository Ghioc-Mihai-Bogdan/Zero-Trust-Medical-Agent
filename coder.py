import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/code', methods=['POST'])
def code():
    text = request.json.get('text', '')
    response = model.generate_content(f"Extract the primary symptoms and assign the most accurate ICD-10 codes for this patient note: {text}")
    return jsonify({"icd10_codes": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
