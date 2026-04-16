import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# Updated to use the 2.5 Flash model!
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/summarize', methods=['POST'])
def summarize():
    text = request.json.get('text', '')
    try:
        response = model.generate_content(f"Summarize this text concisely: {text}")
        return jsonify({"summary": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
