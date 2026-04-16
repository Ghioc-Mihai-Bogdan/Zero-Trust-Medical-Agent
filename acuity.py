import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.json.get('text', '')
    response = model.generate_content(f"Based on the Emergency Severity Index (ESI), assign a triage level (1 to 5) to these symptoms and explain why in one sentence: {text}")
    return jsonify({"acuity_level": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
