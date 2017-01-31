# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Manage password."""

import getpass
import hashlib
import os
import sys
import uuid
from io import open

from glances.compat import b, input
from glances.config import user_config_dir
from glances.globals import safe_makedirs
from glances.logger import logger


class GlancesPassword(object):

    """This class contains all the methods relating to password."""

    def __init__(self, username='glances'):
        self.username = username
        self.password_dir = user_config_dir()
        self.password_filename = self.username + '.pwd'
        self.password_file = os.path.join(self.password_dir, self.password_filename)

    def sha256_hash(self, plain_password):
        """Return the SHA-256 of the given password."""
        return hashlib.sha256(b(plain_password)).hexdigest()

    def get_hash(self, salt, plain_password):
        """Return the hashed password, salt + SHA-256."""
        return hashlib.sha256(salt.encode() + plain_password.encode()).hexdigest()

    def hash_password(self, plain_password):
        """Hash password with a salt based on UUID (universally unique identifier)."""
        salt = uuid.uuid4().hex
        encrypted_password = self.get_hash(salt, plain_password)
        return salt + '$' + encrypted_password

    def check_password(self, hashed_password, plain_password):
        """Encode the plain_password with the salt of the hashed_password.

        Return the comparison with the encrypted_password.
        """
        salt, encrypted_password = hashed_password.split('$')
        re_encrypted_password = self.get_hash(salt, plain_password)
        return encrypted_password == re_encrypted_password

    def get_password(self, description='', confirm=False, clear=False):
        """Get the password from a Glances client or server.

        For Glances server, get the password (confirm=True, clear=False):
            1) from the password file (if it exists)
            2) from the CLI
        Optionally: save the password to a file (hashed with salt + SHA-256)

        For Glances client, get the password (confirm=False, clear=True):
            1) from the CLI
            2) the password is hashed with SHA-256 (only SHA string transit
               through the network)
        """
        if os.path.exists(self.password_file) and not clear:
            # If the password file exist then use it
            logger.info("Read password from file {}".format(self.password_file))
            password = self.load_password()
        else:
            # password_sha256 is the plain SHA-256 password
            # password_hashed is the salt + SHA-256 password
            password_sha256 = self.sha256_hash(getpass.getpass(description))
            password_hashed = self.hash_password(password_sha256)
            if confirm:
                # password_confirm is the clear password (only used to compare)
                password_confirm = self.sha256_hash(getpass.getpass('Password (confirm): '))

                if not self.check_password(password_hashed, password_confirm):
                    logger.critical("Sorry, passwords do not match. Exit.")
                    sys.exit(1)

            # Return the plain SHA-256 or the salted password
            if clear:
                password = password_sha256
            else:
                password = password_hashed

            # Save the hashed password to the password file
            if not clear:
                save_input = input('Do you want to save the password? [Yes/No]: ')
                if len(save_input) > 0 and save_input[0].upper() == 'Y':
                    self.save_password(password_hashed)

        return password

    def save_password(self, hashed_password):
        """Save the hashed password to the Glances folder."""
        # Create the glances directory
        safe_makedirs(self.password_dir)

        # Create/overwrite the password file
        with open(self.password_file, 'wb') as file_pwd:
            file_pwd.write(b(hashed_password))

    def load_password(self):
        """Load the hashed password from the Glances folder."""
        # Read the password file, if it exists
        with open(self.password_file, 'r') as file_pwd:
            hashed_password = file_pwd.read()

        return hashed_password
