import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/haiku', methods=['POST'])
def haiku():
    text = request.json.get('text', '')
    response = model.generate_content(f"Write a 3-line haiku based on this text: {text}")
    return jsonify({"haiku": response.text.strip()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
