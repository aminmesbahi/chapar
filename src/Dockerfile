# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements (if you have any external dependencies)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and templates
COPY src/ .

# Set environment variables for encoding
ENV PYTHONIOENCODING=utf8
ENV LANG=C.UTF-8

# Command to run the application
ENTRYPOINT ["python", "chapar.py"]