# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

# Import system libs
import getpass
import hashlib
import os
import sys
import uuid

# Import Glances lib
from glances.core.glances_globals import appname, is_bsd, is_linux, is_mac, is_windows
from glances.core.glances_logging import logger

# Trick: bind raw_input to input in Python 2
try:
    input = raw_input
except NameError:
    pass


class GlancesPassword(object):

    """This class contains all the methods relating to password."""

    def __init__(self):
        self.password_path = self.get_password_path()
        self.password_filename = 'glances.pwd'
        self.password_filepath = os.path.join(self.password_path, self.password_filename)

    def get_password_path(self):
        r"""Get the path where the password file will be stored.

        * Linux and BSD: ~/.config/glances
        * OS X: ~/Library/glances
        * Windows: %APPDATA%\glances
        """
        if is_linux or is_bsd:
            app_path = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
        elif is_mac:
            app_path = os.path.join(os.environ.get('HOME'), 'Library')
        elif is_windows:
            app_path = os.environ.get('APPDATA')
        else:
            app_path = '.'

        # Append the Glances folder
        app_path = os.path.join(app_path, appname)

        return app_path

    def sha256_hash(self, plain_password):
        """Return the SHA-256 of the given password."""
        return hashlib.sha256(plain_password.encode('utf-8')).hexdigest()

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
        if os.path.exists(self.password_filepath) and not clear:
            # If the password file exist then use it
            logger.info("Read password from file {0}".format(self.password_filepath))
            password = self.load_password()
        else:
            # Else enter the password from the command line
            if description != '':
                print(description)

            # password_sha256 is the plain SHA-256 password
            # password_hashed is the salt + SHA-256 password
            password_sha256 = self.sha256_hash(getpass.getpass('Password: '))
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
        # Check if the Glances folder already exists
        if not os.path.exists(self.password_path):
            # Create the Glances folder
            try:
                os.makedirs(self.password_path)
            except OSError as e:
                logger.error("Cannot create Glances directory: {0}".format(e))
                return

        # Create/overwrite the password file
        with open(self.password_filepath, 'w') as file_pwd:
            file_pwd.write(hashed_password)

    def load_password(self):
        """Load the hashed password from the Glances folder."""
        # Read the password file, if it exists
        with open(self.password_filepath, 'r') as file_pwd:
            hashed_password = file_pwd.read()

        return hashed_password
