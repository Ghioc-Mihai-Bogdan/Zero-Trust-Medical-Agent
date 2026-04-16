import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/diagnose', methods=['POST'])
def diagnose():
    text = request.json.get('text', '')
    response = model.generate_content(f"Act as a CDSS. Give the top 3 most probable differential diagnoses for these symptoms: {text}")
    return jsonify({"diagnoses": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
