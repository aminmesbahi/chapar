import unittest
import os
import configparser
from unittest.mock import patch, MagicMock
import logging
from chapar import (
    load_config,
    read_html,
    read_csv,
    _create_smtp_server,
    send_email,
    main
)
from io import StringIO

class TestEmailDispatcher(unittest.TestCase):

    def setUp(self):
        self.test_folder = "test_data"
        os.makedirs(self.test_folder, exist_ok=True)
        logging.disable(logging.CRITICAL)  # Disable logs during tests

    def tearDown(self):
        for f in os.listdir(self.test_folder):
            os.remove(os.path.join(self.test_folder, f))
        os.rmdir(self.test_folder)
        logging.disable(logging.NOTSET)

    def create_config(self, sections=None):
        config = configparser.ConfigParser()
        if sections:
            for section, options in sections.items():
                config.add_section(section)
                for key, value in options.items():
                    config.set(section, key, value)
        with open(os.path.join(self.test_folder, "config.ini"), 'w') as f:
            config.write(f)

    def test_load_config_valid(self):
        self.create_config({
            'SMTP': {'Host': 'smtp.example.com', 'Port': '587', 'Email': 'user@example.com', 
                     'Password': 'pass', 'Subject': 'Hello'},
            'Settings': {'Interval': '1'}
        })
        config = load_config(self.test_folder)
        self.assertEqual(config['SMTP']['Host'], 'smtp.example.com')

    def test_load_config_missing_section(self):
        self.create_config({'SMTP': {'Host': '...'}})
        with self.assertRaises(ValueError):
            load_config(self.test_folder)

    def test_read_html_valid(self):
        with open(os.path.join(self.test_folder, "email_template.html"), 'w') as f:
            f.write("<html></html>")
        content = read_html(self.test_folder)
        self.assertEqual(content, "<html></html>")

    def test_read_html_missing(self):
        with self.assertRaises(FileNotFoundError):
            read_html(self.test_folder)

    def test_read_csv_valid(self):
        with open(os.path.join(self.test_folder, "recipients.csv"), 'w') as f:
            f.write("email,name\njohn@doe.com,John")
        recipients = read_csv(self.test_folder)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]['email'], 'john@doe.com')

    def test_read_csv_missing_columns(self):
        with open(os.path.join(self.test_folder, "recipients.csv"), 'w') as f:
            f.write("email\njohn@doe.com")
        with self.assertRaises(ValueError):
            read_csv(self.test_folder)

    @patch('smtplib.SMTP_SSL')
    @patch('smtplib.SMTP')
    def test_create_smtp_server(self, mock_smtp, mock_smtp_ssl):
        # Test SSL
        _create_smtp_server('host', 465, 'user', 'pass')
        mock_smtp_ssl.assert_called_once_with('host', 465, timeout=10)

        # Test TLS
        _create_smtp_server('host', 587, 'user', 'pass')
        mock_smtp.assert_called_once_with('host', 587, timeout=10)
        mock_smtp.return_value.starttls.assert_called_once()

    @patch('email_dispatcher._create_smtp_server')
    def test_send_email_success(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        smtp_settings = {
            'host': 'host', 'port': 587, 'email': 'from@example.com',
            'password': 'pass', 'subject': 'Test', 'DisplayName': 'Test'
        }
        result = send_email(smtp_settings, 'to@example.com', 'John', 
                           '<html>{{name}}</html>', 'detailed', 'test')
        self.assertTrue(result)
        mock_server.sendmail.assert_called_once()

    @patch('email_dispatcher._create_smtp_server')
    def test_send_email_failure(self, mock_smtp):
        mock_smtp.side_effect = Exception("SMTP error")
        smtp_settings = {'host': 'host', 'port': 587, 'email': 'from@example.com',
                        'password': 'pass', 'subject': 'Test'}
        result = send_email(smtp_settings, 'to@example.com', 'John', 
                           '<html></html>', 'none', 'test')
        self.assertFalse(result)

    @patch('email_dispatcher.load_config')
    @patch('email_dispatcher.read_html')
    @patch('email_dispatcher.read_csv')
    @patch('email_dispatcher.send_email')
    @patch('time.sleep')
    def test_main_success(self, mock_sleep, mock_send, mock_csv, mock_html, mock_config):
        mock_config.return_value = {
            'SMTP': {'Host': 'host', 'Port': '587', 'Email': 'user', 
                    'Password': 'pass', 'Subject': 'Subj'},
            'Settings': {'Interval': '0', 'LogLevel': 'detailed'}
        }
        mock_html.return_value = "<html></html>"
        mock_csv.return_value = [{'email': 'a@b.com', 'name': 'Alice'}]
        mock_send.return_value = True

        main(self.test_folder)
        self.assertEqual(mock_send.call_count, 1)

    @patch('email_dispatcher.load_config')
    def test_main_config_error(self, mock_config):
        mock_config.side_effect = ValueError("Config error")
        with self.assertLogs(level='ERROR') as log:
            main(self.test_folder)
            self.assertIn("Config error", log.output[0])

if __name__ == '__main__':
    unittest.main()