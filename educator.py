import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/educate', methods=['POST'])
def educate():
    text = request.json.get('text', '')
    response = model.generate_content(f"Explain these medical symptoms and next steps to the patient at a 6th-grade reading level, in a calm and reassuring tone: {text}")
    return jsonify({"patient_explanation": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
