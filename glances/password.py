#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage password."""

import builtins
import getpass
import hashlib
import os
import sys
import uuid

from glances.config import user_config_dir
from glances.globals import b, safe_makedirs, weak_lru_cache
from glances.logger import logger


class GlancesPassword:
    """This class contains all the methods relating to password."""

    def __init__(self, username='glances', config=None):
        self.username = username

        self.config = config
        self.password_dir = self.local_password_path()
        self.password_filename = self.username + '.pwd'
        self.password_file = os.path.join(self.password_dir, self.password_filename)

    def local_password_path(self):
        """Return the local password path.
        Related to issue: Password files in same configuration dir in effect #2143
        """
        if self.config is None:
            return user_config_dir()[0]
        return self.config.get_value('passwords', 'local_password_path', default=user_config_dir()[0])

    @weak_lru_cache(maxsize=32)
    def get_hash(self, plain_password, salt=''):
        """Return the hashed password, salt + pbkdf2_hmac."""
        return hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000, dklen=128).hex()

    @weak_lru_cache(maxsize=32)
    def hash_password(self, plain_password):
        """Hash password with a salt based on UUID (universally unique identifier)."""
        salt = uuid.uuid4().hex
        encrypted_password = self.get_hash(plain_password, salt=salt)
        return salt + '$' + encrypted_password

    @weak_lru_cache(maxsize=32)
    def check_password(self, hashed_password, plain_password):
        """Encode the plain_password with the salt of the hashed_password.

        Return the comparison with the encrypted_password.
        """
        salt, encrypted_password = hashed_password.split('$')
        re_encrypted_password = self.get_hash(plain_password, salt=salt)
        return encrypted_password == re_encrypted_password

    def get_password(self, description='', confirm=False, clear=False):
        """Get the password from a Glances client or server.

        For Glances server, get the password (confirm=True, clear=False):
            1) from the password file (if it exists)
            2) from the CLI
        Optionally: save the password to a file (hashed with salt + SHA-pbkdf2_hmac)

        For Glances client, get the password (confirm=False, clear=True):
            1) from the CLI
            2) the password is hashed with SHA-pbkdf2_hmac (only SHA string transit
               through the network)
        """
        if os.path.exists(self.password_file) and not clear:
            # If the password file exist then use it
            logger.info(f"Read password from file {self.password_file}")
            password = self.load_password()
        else:
            # password_hash is the plain SHA-pbkdf2_hmac password
            # password_hashed is the salt + SHA-pbkdf2_hmac password
            password_hash = self.get_hash(getpass.getpass(description))
            password_hashed = self.hash_password(password_hash)
            if confirm:
                # password_confirm is the clear password (only used to compare)
                password_confirm = self.get_hash(getpass.getpass('Password (confirm): '))

                if not self.check_password(password_hashed, password_confirm):
                    logger.critical("Sorry, passwords do not match. Exit.")
                    sys.exit(1)

            # Return the plain SHA-pbkdf2_hmac or the salted password
            if clear:
                password = password_hash
            else:
                password = password_hashed

            # Save the hashed password to the password file
            if not clear:
                save_input = input('Do you want to save the password? [Yes/No]: ')
                if save_input and save_input[0].upper() == 'Y':
                    self.save_password(password_hashed)

        return password

    def save_password(self, hashed_password):
        """Save the hashed password to the Glances folder."""
        # Create the glances directory
        safe_makedirs(self.password_dir)

        # Create/overwrite the password file
        with builtins.open(self.password_file, 'wb') as file_pwd:
            file_pwd.write(b(hashed_password))

    def load_password(self):
        """Load the hashed password from the Glances folder."""
        # Read the password file, if it exists
        with builtins.open(self.password_file) as file_pwd:
            return file_pwd.read()
