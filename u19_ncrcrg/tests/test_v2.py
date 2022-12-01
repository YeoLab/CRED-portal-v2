import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "u19_ncrcrg.settings")
django.setup()

from u19_ncrcrg.accounts.admin import SettingsBackend

be = SettingsBackend()


class TestV2(unittest.TestCase):

    def test_login(self):
        username = 'byee'

        user = be.authenticate(username, password)

    def test_get_user(self):
        user_id = 5
        user = be.get_user(user_id)

        assert user.username == 'byee'


if __name__ == '__main__':
    unittest.main()
