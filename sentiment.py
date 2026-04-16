import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.json.get('text', '')
    response = model.generate_content(f"Analyze the sentiment of this text in one word (e.g., Positive, Negative, Neutral, Curious): {text}")
    return jsonify({"sentiment": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
