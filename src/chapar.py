import os
import smtplib
import csv
import time
import configparser
import logging
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(folder):
    config = configparser.ConfigParser()
    config_file = os.path.join(folder, "config.ini") if os.path.exists(os.path.join(folder, "config.ini")) else "config.ini"
    config.read(config_file, encoding='utf-8')
    return config

def read_html(folder):
    html_file = os.path.join(folder, "email_template.html")
    if not os.path.exists(html_file):
        raise FileNotFoundError(f"HTML template not found in {folder}")
    with open(html_file, 'r', encoding='utf-8') as file:
        return file.read()

def read_csv(folder):
    csv_file = os.path.join(folder, "recipients.csv")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Recipients CSV file not found in {folder}")
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

def send_email(smtp_settings, recipient_email, recipient_name, html_content):
    try:
        message = MIMEMultipart("alternative")
        display_name = smtp_settings.get('DisplayName', 'TechAfternoon')
        message["From"] = formataddr((str(Header(display_name, "utf-8")), smtp_settings['email']))
        message["To"] = recipient_email
        message["Subject"] = Header(smtp_settings['subject'], "utf-8")

        personalized_html = html_content.replace("{{name}}", recipient_name)
        part = MIMEText(personalized_html, "html", "utf-8")
        message.attach(part)

        if int(smtp_settings['port']) == 465:
            with smtplib.SMTP_SSL(smtp_settings['host'], 465) as server:
                logging.info("SSL connection established")
                server.ehlo()
                server.login(smtp_settings['email'], smtp_settings['password'])
                server.sendmail(smtp_settings['email'], recipient_email, message.as_string())
        elif int(smtp_settings['port']) == 587:
            with smtplib.SMTP(smtp_settings['host'], 587) as server:
                server.ehlo()
                server.starttls()
                logging.info("TLS connection established")
                server.login(smtp_settings['email'], smtp_settings['password'])
                server.sendmail(smtp_settings['email'], recipient_email, message.as_string())
        else:
            raise ValueError("Unsupported port for SMTP connection")

        logging.info(f"Sent email to {recipient_email}")
        return True

    except Exception as e:
        logging.error(f"Failed to send email to {recipient_email}: {e}")
        return False

def main(folder):
    start_time = time.time()
    logging.info(f"Starting email dispatch for folder: {folder}")

    try:
        config = load_config(folder)
        smtp_settings = {
            'host': config['SMTP']['Host'],
            'port': config['SMTP']['Port'],
            'email': config['SMTP']['Email'],
            'password': config['SMTP']['Password'],
            'subject': config['SMTP']['Subject']
        }
        interval = int(config['Settings']['Interval'])

        html_content = read_html(folder)
        recipients = read_csv(folder)

        total_recipients = len(recipients)
        success_count = 0
        failure_count = 0

        logging.info(f"Found {total_recipients} recipients in the list.")

        for recipient in recipients:
            email = recipient['email']
            name = recipient['name']
            if send_email(smtp_settings, email, name, html_content):
                success_count += 1
            else:
                failure_count += 1
            time.sleep(interval)

        elapsed_time = time.time() - start_time
        logging.info(f"Email dispatch completed: {success_count} sent, {failure_count} failed. Total time: {elapsed_time:.2f} seconds.")

    except Exception as e:
        logging.error(f"Error during email dispatch: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chapar Email Dispatcher")
    parser.add_argument("folder", help="Folder containing the email template and recipients CSV file")
    args = parser.parse_args()
    main(args.folder)