# tests/test_auth.py
import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
import dependencies.auth as auth


class TestResolveUserId(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_request = MagicMock()

    def test_anonymous_user_when_no_credentials(self):
        # Simulate no anonymous user in DB
        self.mock_db.query().filter().first.return_value = None
        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        
        # Simulate setting ID in refresh
        self.mock_db.refresh.side_effect = lambda user: setattr(user, 'id', 99)

        user_id = auth.resolve_user_id(self.mock_request, credentials=None, db=self.mock_db)
        self.assertEqual(user_id, 99)

    def test_existing_user_correct_password(self):
        # Simulate existing user with correct password
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password = "password123"
        self.mock_db.query().filter().first.return_value = mock_user

        creds = HTTPBasicCredentials(username="testuser", password="password123")
        user_id = auth.resolve_user_id(self.mock_request, credentials=creds, db=self.mock_db)
        self.assertEqual(user_id, 1)

    def test_existing_user_incorrect_password_raises_401(self):
        # Simulate existing user with wrong password
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password = "correctpass"
        self.mock_db.query().filter().first.return_value = mock_user

        creds = HTTPBasicCredentials(username="testuser", password="wrongpass")
        with self.assertRaises(HTTPException) as context:
            auth.resolve_user_id(self.mock_request, credentials=creds, db=self.mock_db)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Incorrect password.")

    def test_missing_password_raises_401(self):
        creds = HTTPBasicCredentials(username="testuser", password="")
        with self.assertRaises(HTTPException) as context:
            auth.resolve_user_id(self.mock_request, credentials=creds, db=self.mock_db)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Password is required.")

    def test_create_user_if_not_exists(self):
        # Simulate user not found
        self.mock_db.query().filter().first.return_value = None

        # Simulate insert behavior
        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        self.mock_db.refresh.side_effect = lambda user: setattr(user, 'id', 42)

        creds = HTTPBasicCredentials(username="newuser", password="newpass")
        user_id = auth.resolve_user_id(self.mock_request, credentials=creds, db=self.mock_db)
        self.assertEqual(user_id, 42)
