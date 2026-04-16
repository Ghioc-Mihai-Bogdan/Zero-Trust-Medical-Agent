import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/translate', methods=['POST'])
def translate():
    text = request.json.get('text', '')
    response = model.generate_content(f"Translate this exactly into Spanish: {text}")
    return jsonify({"spanish": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
