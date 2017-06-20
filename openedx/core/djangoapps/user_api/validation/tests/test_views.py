# -*- coding: utf-8 -*-
"""
Tests for an API endpoint for client-side user data validation.
"""

import ddt
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from openedx.core.djangoapps.user_api.accounts import (
    EMAIL_CONFLICT_MSG, EMAIL_MAX_LENGTH, EMAIL_MIN_LENGTH,
    PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH,
    USERNAME_CONFLICT_MSG, USERNAME_MAX_LENGTH, USERNAME_MIN_LENGTH
)
from openedx.core.djangoapps.user_api.accounts.tests.testutils import (
    VALID_EMAILS, VALID_PASSWORDS, VALID_USERNAMES,
    INVALID_EMAILS, INVALID_PASSWORDS, INVALID_USERNAMES
)
from openedx.core.lib.api import test_utils


@ddt.ddt
class RegistrationValidationViewTests(test_utils.ApiTestCase):
    """
    Tests for validity of user data in registration forms.
    """

    def setUp(self):
        super(RegistrationValidationViewTests, self).setUp()
        self.endpoint_name = 'registration_validation'
        self.path = reverse(self.endpoint_name)

    def get_validation_decision(self, data):
        response = self.client.get(self.path, data)
        return response.data.get('validation_decisions', {})

    def test_no_decision_for_empty_request(self):
        validation_decisions = self.get_validation_decision({})
        self.assertEqual(validation_decisions, {})

    def test_no_decision_for_invalid_request(self):
        validation_decisions = self.get_validation_decision({
            'invalid_field': 'random_user_data'
        })
        self.assertEqual(validation_decisions, {})

    @ddt.data(
        ['email', VALID_EMAILS],
        ['password', VALID_PASSWORDS],
        ['username', VALID_USERNAMES]
    )
    @ddt.unpack
    def test_positive_validation_decision(self, form_field_name, user_data):
        """
        Test if {0} as any item in {1} gives a positive validation decision.
        """
        for data in user_data:
            self.assertEqual(
                self.get_validation_decision({form_field_name: data}),
                {form_field_name: ''}
            )

    @ddt.data(
        # Skip None type for invalidity checks.
        ['email', INVALID_EMAILS[1:]],
        ['password', INVALID_PASSWORDS[1:]],
        ['username', INVALID_USERNAMES[1:]]
    )
    @ddt.unpack
    def test_negative_validation_decision(self, form_field_name, user_data):
        """
        Test if {0} as any item in {1} gives a negative validation decision.
        """
        for data in user_data:
            self.assertNotEqual(
                self.get_validation_decision({form_field_name: data}),
                {form_field_name: ''}
            )

    @ddt.data(
        ['username', 'username@email.com'],  # No conflict
        ['user', 'username@email.com'],  # Username conflict
        ['username', 'user@email.com'],  # Email conflict
        ['user', 'user@email.com']  # Both conflict
    )
    @ddt.unpack
    def test_existence_conflict(self, username, email):
        """
        Test if username '{0}' and email '{1}' have conflicts with
        username 'user' and email 'user@email.com'.
        """
        user = User.objects.create_user(username='user', email='user@email.com')
        validation_decisions = self.get_validation_decision({
            'username': username,
            'email': email
        })
        self.assertEqual(validation_decisions, {
            "username": _(USERNAME_CONFLICT_MSG).format(username=user.username) if username == user.username else '',
            "email": _(EMAIL_CONFLICT_MSG).format(email_address=user.email) if email == user.email else ''
        })

    def test_email_less_than_min_length_validation_decision(self):
        email = ''
        validation_decisions = self.get_validation_decision({
            'email': email
        })
        self.assertEqual(validation_decisions, {
            'email': "Email '{email}' must be at least {min} characters long".format(email=email, min=EMAIL_MIN_LENGTH)
        })

    def test_email_more_than_max_length_validation_decision(self):
        email = ('e'*EMAIL_MAX_LENGTH) + '@email.com'
        validation_decisions = self.get_validation_decision({
            'email': email
        })
        self.assertEqual(validation_decisions, {
            'email': "Email '{email}' must be at most {max} characters long".format(email=email, max=EMAIL_MAX_LENGTH)
        })

    def test_email_generically_invalid_validation_decision(self):
        email = 'email'
        validation_decisions = self.get_validation_decision({
            'email': email
        })
        self.assertEqual(validation_decisions, {
            'email': "Email '{email}' format is not valid".format(email=email)
        })

    def test_username_less_than_min_length_validation_decision(self):
        username = 'u'*(USERNAME_MIN_LENGTH - 1)
        validation_decisions = self.get_validation_decision({
            'username': username
        })
        self.assertEqual(validation_decisions, {
            'username': "Username '{username}' must be at least {min} characters long".format(
                username=username,
                min=USERNAME_MIN_LENGTH
            )
        })

    def test_username_more_than_max_length_validation_decision(self):
        username = 'u'*(USERNAME_MAX_LENGTH + 1)
        validation_decisions = self.get_validation_decision({
            'username': username
        })
        self.assertEqual(validation_decisions, {
            'username': "Username '{username}' must be at most {max} characters long".format(
                username=username,
                max=USERNAME_MAX_LENGTH
            )
        })

    def test_username_generically_invalid_validation_decision(self):
        username = '$user$'
        validation_decisions = self.get_validation_decision({
            "username": username
        })
        self.assertEqual(validation_decisions, {
            "username": "Username '{username}' must contain only A-Z, a-z, 0-9, -, or _ characters".format(
                username=username
            )
        })

    def test_password_less_than_min_length_validation_decision(self):
        password = 'p'*(PASSWORD_MIN_LENGTH - 1)
        validation_decisions = self.get_validation_decision({
            "password": password
        })
        self.assertEqual(validation_decisions, {
            "password": "Password must be at least {min} characters long".format(min=PASSWORD_MIN_LENGTH)
        })

    def test_password_more_than_max_length_validation_decision(self):
        password = 'p'*(PASSWORD_MAX_LENGTH + 1)
        validation_decisions = self.get_validation_decision({
            "password": password
        })
        self.assertEqual(validation_decisions, {
            "password": "Password must be at most {max} characters long".format(max=PASSWORD_MAX_LENGTH)
        })

    def test_password_equals_username_validation_decision(self):
        validation_decisions = self.get_validation_decision({
            "username": "somephrase",
            "password": "somephrase"
        })
        self.assertEqual(validation_decisions, {
            "username": "",
            "password": "Password cannot be the same as the username"
        })
