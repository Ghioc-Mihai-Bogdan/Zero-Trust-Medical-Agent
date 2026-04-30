import requests
import base64

API_URL = "http://127.0.0.1:8088/diagnose"
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png"

print("1. Downloading Chest X-ray from Wikipedia...")

# Wikimedia blocks default Python requests. We must provide a User-Agent!
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Fetch the image with the fake browser header
img_response = requests.get(IMAGE_URL, headers=headers)

if img_response.status_code != 200:
    print(f"Failed to download image. Status: {img_response.status_code}")
    exit()

print("2. Encoding image to Base64...")
# Convert the raw bytes into a base64 string
base64_string = base64.b64encode(img_response.content).decode('utf-8')

# Build the multimodal payload
payload = {
    "text": "Patient presents with a persistent cough and mild shortness of breath. Please analyze the provided chest X-ray and provide your top 3 differential diagnoses.",
    "images": [base64_string]
}

print("3. Sending text and X-ray to the 31B Multimodal Diagnostician...")
# Send it to your local Kubernetes mesh
try:
    # Upped the timeout slightly just in case the 31B model takes a moment to process the image tokens
    response = requests.post(API_URL, json=payload, timeout=180)
    
    print("\n" + "="*50)
    print(" 🩺 DIAGNOSTICIAN REPORT (Multimodal)")
    print("="*50)
    print(response.json().get('diagnoses', 'No response received.'))
    
except Exception as e:
    print(f"Connection failed: {e}")