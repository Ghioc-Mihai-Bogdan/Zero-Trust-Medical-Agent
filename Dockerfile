FROM python:3.10-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests google-generativeai werkzeug redis
COPY . .
CMD ["python", "app.py"]
