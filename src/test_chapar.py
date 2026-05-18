import unittest
import os
import sys
import configparser
from unittest.mock import patch, MagicMock
import logging
sys.modules.setdefault('magic', MagicMock())
import chapar_api
from chapar import (
    load_config,
    read_html,
    read_csv,
    _create_smtp_server,
    send_email,
    main
)
from io import BytesIO, StringIO

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

    @patch('chapar._create_smtp_server')
    def test_send_email_success(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        smtp_settings = {
            'host': 'host', 'port': 587, 'email': 'from@example.com',
            'password': 'pass', 'subject': 'Test', 'DisplayName': 'Test'
        }
        result = send_email(smtp_settings, mock_server, 'to@example.com', 'John', 
                           '<html>{{name}}</html>', 'detailed', 'test')
        self.assertTrue(result)
        mock_server.sendmail.assert_called_once()

    @patch('chapar._create_smtp_server')
    def test_send_email_failure(self, mock_smtp):
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = Exception("SMTP error")
        smtp_settings = {'host': 'host', 'port': 587, 'email': 'from@example.com',
                        'password': 'pass', 'subject': 'Test'}
        result = send_email(smtp_settings, mock_server, 'to@example.com', 'John', 
                           '<html></html>', 'none', 'test')
        self.assertFalse(result)

    @patch('chapar.load_config')
    @patch('chapar.read_html')
    @patch('chapar.read_csv')
    @patch('chapar.send_email')
    @patch('chapar._create_smtp_server')
    @patch('time.sleep')
    def test_main_success(self, mock_sleep, mock_smtp_server, mock_send, mock_csv, mock_html, mock_config):
        mock_config.return_value = {
            'SMTP': {'Host': 'host', 'Port': '587', 'Email': 'user', 
                    'Password': 'pass', 'Subject': 'Subj'},
            'Settings': {'Interval': '0', 'LogLevel': 'detailed'}
        }
        mock_html.return_value = "<html></html>"
        mock_csv.return_value = [{'email': 'a@b.com', 'name': 'Alice'}]
        mock_send.return_value = True
        mock_server = MagicMock()
        mock_smtp_server.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_server.return_value.__exit__ = MagicMock(return_value=False)

        main(self.test_folder)
        self.assertEqual(mock_send.call_count, 1)

    @patch('chapar.load_config')
    def test_main_config_error(self, mock_config):
        mock_config.side_effect = ValueError("Config error")
        logging.disable(logging.NOTSET)  # Re-enable logging so assertLogs can capture it
        with self.assertLogs(level='ERROR') as log:
            main(self.test_folder)
        logging.disable(logging.CRITICAL)  # Restore suppression for other tests
        self.assertIn("Config error", log.output[0])


class TestChaparApi(unittest.TestCase):

    def setUp(self):
        chapar_api.app.config['TESTING'] = True
        self.client = chapar_api.app.test_client()

    def _upload_payload(self):
        return {
            'template': (BytesIO(b'<html></html>'), 'email_template.html'),
            'recipients': (BytesIO(b'email,name\nuser@example.com,User\n'), 'recipients.csv'),
            'config': (BytesIO(b'[SMTP]\nHost=smtp.example.com\n'), 'config.ini')
        }

    @patch('chapar_api.shutil.rmtree')
    @patch('chapar_api.tempfile.mkdtemp', return_value='api-test-temp')
    @patch('chapar_api.save_uploaded_files')
    @patch('chapar_api.validate_recipients_file')
    def test_send_masks_recipient_validation_error(self, mock_validate, mock_save, _mock_mkdtemp, _mock_rmtree):
        mock_save.return_value = {
            'template': 'email_template.html',
            'recipients': 'recipients.csv',
            'config': 'config.ini'
        }
        mock_validate.side_effect = ValueError('secret recipient details')

        response = self.client.post('/api/send', data=self._upload_payload(), content_type='multipart/form-data')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': chapar_api.GENERIC_RECIPIENTS_ERROR})

    @patch('chapar_api.shutil.rmtree')
    @patch('chapar_api.tempfile.mkdtemp', return_value='api-test-temp')
    @patch('chapar_api.chapar.send_emails_from_files')
    @patch('chapar_api.validate_recipients_file')
    @patch('chapar_api.save_uploaded_files')
    def test_send_masks_dispatch_exception(self, mock_save, mock_validate, mock_send, _mock_mkdtemp, _mock_rmtree):
        mock_save.return_value = {
            'template': 'email_template.html',
            'recipients': 'recipients.csv',
            'config': 'config.ini'
        }
        mock_validate.return_value = None
        mock_send.side_effect = Exception('smtp credential leak')

        response = self.client.post('/api/send', data=self._upload_payload(), content_type='multipart/form-data')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {
            'status': 'error',
            'message': chapar_api.GENERIC_EMAIL_DISPATCH_ERROR
        })

    @patch('chapar_api.shutil.rmtree')
    @patch('chapar_api.tempfile.mkdtemp', return_value='api-test-temp')
    @patch('chapar_api.save_uploaded_files')
    def test_send_masks_file_processing_error(self, mock_save, _mock_mkdtemp, _mock_rmtree):
        mock_save.side_effect = Exception('filesystem path leak')

        response = self.client.post('/api/send', data=self._upload_payload(), content_type='multipart/form-data')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {'error': chapar_api.GENERIC_FILE_UPLOAD_ERROR})

if __name__ == '__main__':
    unittest.main()