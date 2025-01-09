# Chapar (چاپار)

Chapar (چاپار) is a Python-based tool for sending personalized HTML emails effortlessly. Inspired by the Persian word "Chapar," which refers to the ancient postal couriers who swiftly delivered messages across distances, this project modernizes the art of communication, enabling efficient and customizable email delivery for your needs.

## Usage

Run the script with the folder containing your `email_template.html`, `recipients.csv`, and optionally a `config.ini`:

```bash
python chapar.py newsletter0-ltr
```

## ⚠️ This document, samples, and features will be improved! soon!

### Current features
- Supports only secure connections (SSL and TLS)
- minimal template and responsive modern templates (Just replace your texts)
- templates in RTL and LTR format
- interval between sends


# Docker Usage Guide for Chapar

This guide explains how to use Chapar with Docker for sending personalized HTML emails.

## Building the Docker Image

Build the Docker image from the project root directory:

```bash
docker build -t chapar .
```
Collecting workspace information

I'll help create a Dockerfile and docker-usage.md file for the Chapar email sending application. Here's what we'll create:

First, let's create a `Dockerfile`:

```dockerfile
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
```

Now, let's create a `requirements.txt` file (place it in the root directory):

```text
configparser>=5.0.0
```

Here's the content for `docker-usage.md`:

```markdown
# Docker Usage Guide for Chapar

This guide explains how to use Chapar with Docker for sending personalized HTML emails.

## Building the Docker Image

Build the Docker image from the project root directory:

```bash
docker build -t chapar .
```

## Running Chapar with Docker

### Basic Usage

Run Chapar by mounting your newsletter folder and specifying the folder name:

```bash
docker run -v $(pwd)/src/newsletter0-ltr:/app/newsletter0-ltr chapar newsletter0-ltr
```

### Directory Structure

Your mounted directory should contain:
- email_template.html: Your HTML email template
- recipients.csv: CSV file with email recipients
- config.ini: SMTP and other configuration settings

### Example Commands

1. For LTR (Left-to-Right) template:
```bash
docker run -v $(pwd)/src/newsletter0-ltr:/app/newsletter0-ltr chapar newsletter0-ltr
```

2. For RTL (Right-to-Left) template:
```bash
docker run -v $(pwd)/src/newsletter0-rtl:/app/newsletter0-rtl chapar newsletter0-rtl
```

### Configuration

Make sure your `config.ini` file in the mounted directory contains proper SMTP settings:

```ini
[SMTP]
Host = smtp.example.com
Port = 587
Email = your_email@example.com
Password = your_password
Subject = Your Subject Here
DisplayName = Your Name

[Settings]
Interval = 5
```

### Security Notes

- Always use secure SMTP connections (Port 587 for TLS or 465 for SSL)
- Keep your SMTP credentials secure and never commit them to version control
- Consider using environment variables for sensitive information

## Troubleshooting

1. If you encounter encoding issues:
   - Ensure all files are saved with UTF-8 encoding
   - The Docker container is configured with UTF-8 support by default

2. For permission issues:
   - Check the file permissions in your mounted directory
   - Ensure the container has read access to all required files

3. For network issues:
   - Verify your SMTP server settings
   - Check if your host allows outgoing SMTP connections

---
This Docker setup allows you to:
1. Package the Chapar application in a container
2. Run it with different newsletter templates
3. Mount local directories containing your email templates and configurations
4. Handle both RTL and LTR templates properly with UTF-8 support

### Roadmap
- docker support
- expose REST API
- more

