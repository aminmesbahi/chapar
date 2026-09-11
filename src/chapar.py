import configparser
import csv
import html
import logging
import os
import smtplib
import time
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(folder: str) -> configparser.ConfigParser:
    """Loads and validates the configuration file.

    Args:
        folder: The folder containing the config.ini file.

    Returns:
        A ConfigParser object.

    Raises:
        FileNotFoundError: If the config.ini file is not found.
        ValueError: If the config file is invalid.
    """
    config = configparser.ConfigParser()
    config_file = os.path.join(folder, "config.ini")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")
    try:
        config.read(config_file, encoding='utf-8')
    except configparser.Error as e:
        raise ValueError(f"Error parsing config file: {e}")

    required_sections = ['SMTP', 'Settings']
    for section in required_sections:
        if not config.has_section(section):
            raise ValueError(f"Missing section in config: {section}")

    try:
        interval = int(config['Settings'].get('Interval', '0'))
        config['Settings']['Interval'] = str(interval)
        log_level = config['Settings'].get('LogLevel', 'none').lower()
        if log_level not in ['none', 'job', 'detailed']:
            raise ValueError("Invalid LogLevel. Must be 'none', 'job', or 'detailed'.")
        config['Settings']['LogLevel'] = log_level
    except ValueError as e:
        raise ValueError(f"Invalid setting in config: {e}")

    env_overrides = {
        'Host': 'SMTP_HOST',
        'Port': 'SMTP_PORT',
        'Email': 'SMTP_EMAIL',
        'Password': 'SMTP_PASSWORD',
        'Subject': 'SMTP_SUBJECT',
        'DisplayName': 'SMTP_DISPLAY_NAME',
    }
    for key, env_var in env_overrides.items():
        value = os.environ.get(env_var)
        if value is not None:
            config['SMTP'][key] = value

    return config

def read_html(folder: str) -> str:
    """Reads the HTML template file.

    Args:
        folder: The folder containing the email_template.html file.

    Returns:
        The HTML content as a string.

    Raises:
        FileNotFoundError: If the email_template.html file is not found.
    """
    html_file = os.path.join(folder, "email_template.html")
    if not os.path.exists(html_file):
        raise FileNotFoundError(f"HTML template not found in {folder}")
    with open(html_file, 'r', encoding='utf-8') as file:
        return file.read()

def read_csv(folder: str) -> List[Dict[str, str]]:
    """Reads the recipients CSV file.

    Args:
        folder: The folder containing the recipients.csv file.

    Returns:
        A list of dictionaries, where each dictionary represents a recipient.

    Raises:
        FileNotFoundError: If the recipients.csv file is not found.
        ValueError: If the CSV file is missing required columns.
    """
    csv_file = os.path.join(folder, "recipients.csv")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Recipients CSV file not found in {folder}")
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        required_columns = {'email', 'name'}
        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError("CSV missing required columns: email/name")
        return [row for row in reader]

def _create_smtp_server(host: str, port: int, email: str, password: str) -> smtplib.SMTP:
    """Creates and logs in to an SMTP server.

    Args:
        host: The SMTP host.
        port: The SMTP port.
        email: The email address to log in with.
        password: The password to log in with.

    Returns:
        An SMTP server object.

    Raises:
        ValueError: If the port is not supported.
        smtplib.SMTPException: If there is an error connecting to the SMTP server.
    """
    try:
        server: smtplib.SMTP
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
            logging.info("SSL connection established")
        elif port == 587:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
            logging.info("TLS connection established")
        else:
            raise ValueError("Unsupported port")
        server.login(email, password)
        return server
    except smtplib.SMTPException as e:
        raise smtplib.SMTPException(f"SMTP authentication error: {e}")

def _smtp_settings_from_config(config: configparser.ConfigParser) -> Dict[str, str]:
    """Builds the SMTP settings dict used by send_email/_create_smtp_server from a loaded config."""
    return {
        'host': config['SMTP']['Host'],
        'port': config['SMTP']['Port'],
        'email': config['SMTP']['Email'],
        'password': config['SMTP']['Password'],
        'subject': config['SMTP']['Subject'],
        'DisplayName': config['SMTP'].get('DisplayName', ''),
    }


def _dispatch(
    smtp_settings: Dict[str, str],
    interval: int,
    log_level: str,
    template_name: str,
    html_content: str,
    recipients: List[Dict[str, str]],
) -> tuple[int, int]:
    """Sends html_content to every recipient over one SMTP connection, logging progress.

    Returns:
        A (success_count, failure_count) tuple.
    """
    start_time = time.time()
    logging.info(f"Found {len(recipients)} recipients in the list.")
    success_count = 0
    failure_count = 0

    with _create_smtp_server(
        smtp_settings['host'],
        int(smtp_settings['port']),
        smtp_settings['email'],
        smtp_settings['password'],
    ) as server:
        for recipient in recipients:
            email = recipient['email']
            name = recipient['name']
            if send_email(smtp_settings, server, email, name, html_content, log_level, template_name):
                success_count += 1
            else:
                failure_count += 1
            time.sleep(interval)

    elapsed_time = time.time() - start_time
    logging.info(
        f"Email dispatch completed: {success_count} sent, {failure_count} failed. "
        f"Total time: {elapsed_time:.2f} seconds."
    )
    return success_count, failure_count


def send_emails_from_files(config_path: str, recipients_path: str, template_path: str) -> None:
    """
    Sends emails using the specified configuration, recipients, and template files.

    Args:
        config_path: Path to the config.ini file.
        recipients_path: Path to the recipients.csv file.
        template_path: Path to the email_template.html file.
    """
    folder = os.path.dirname(config_path)
    logging.info(f"Starting email dispatch using config: {config_path}")

    try:
        config = load_config(folder)
        smtp_settings = _smtp_settings_from_config(config)
        interval = int(config['Settings']['Interval'])
        log_level = config['Settings']['LogLevel']
        template_name = os.path.basename(folder)

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"HTML template not found: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if not os.path.exists(recipients_path):
            raise FileNotFoundError(f"Recipients CSV not found: {recipients_path}")
        with open(recipients_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            required_columns = {'email', 'name'}
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise ValueError("CSV missing required columns: email/name")
            recipients = [row for row in reader]

        _dispatch(smtp_settings, interval, log_level, template_name, html_content, recipients)

    except Exception as e:
        logging.exception(f"Error during email dispatch: {e}")
        raise

def send_email(
    smtp_settings: Dict[str, str],
    server: smtplib.SMTP,
    recipient_email: str,
    recipient_name: str,
    html_content: str,
    log_level: str,
    template_name: str,
) -> bool:
    """Sends a personalized email to a recipient.

    Args:
        smtp_settings: A dictionary containing the SMTP settings.
        server: An already-open and authenticated SMTP server object.
        recipient_email: The recipient's email address.
        recipient_name: The recipient's name.
        html_content: The HTML content of the email.
        log_level: The logging level.
        template_name: The name of the email template.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    try:
        message = MIMEMultipart("alternative")
        display_name = smtp_settings.get('DisplayName', 'TechAfternoon')
        message["From"] = formataddr((str(Header(display_name, "utf-8")), smtp_settings['email']))
        message["To"] = recipient_email
        message["Subject"] = str(Header(smtp_settings['subject'], "utf-8"))

        personalized_html = html_content.replace("{{name}}", html.escape(recipient_name))
        part = MIMEText(personalized_html, "html", "utf-8")
        message.attach(part)

        server.sendmail(smtp_settings['email'], recipient_email, message.as_string())

        if log_level == 'detailed':
            logging.info(f"Sent template {template_name} to {recipient_email} succeeded")
        return True

    except Exception as e:
        logging.error(f"Failed to send email to {recipient_email} from template {template_name}: {e}")
        return False

def main(folder: str) -> None:
    """Dispatches emails to recipients based on the configuration and data in the specified folder.

    Args:
        folder: The folder containing the configuration file, HTML template, and recipient list.

    Raises:
        Exception: Re-raises whatever error interrupted the dispatch, after logging it.
    """
    logging.info(f"Starting email dispatch for folder: {folder}")

    try:
        config = load_config(folder)
        smtp_settings = _smtp_settings_from_config(config)
        interval = int(config['Settings']['Interval'])
        log_level = config['Settings']['LogLevel']
        template_name = os.path.basename(folder)

        html_content = read_html(folder)
        recipients = read_csv(folder)

        success_count, _ = _dispatch(smtp_settings, interval, log_level, template_name, html_content, recipients)

        if log_level == 'job':
            logging.info(
                f"Sent {success_count} successful emails from {len(recipients)} total "
                f"recipients with template {template_name}"
            )

    except Exception as e:
        logging.exception(f"Error during email dispatch in folder {folder}: {e}")
        raise

if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Chapar Email Dispatcher")
    parser.add_argument("folder", help="Folder containing the email template and recipients CSV file")
    args = parser.parse_args()
    try:
        main(args.folder)
    except Exception:
        sys.exit(1)
