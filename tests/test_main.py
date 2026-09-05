# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Jack Chen <nightcityblade@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only

"""Tests for Glances command-line initialization."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from glances.main import GlancesMain


class TestGlancesMain(TestCase):
    def test_fs_free_space_from_config(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'glances.conf'
            config_path.write_text('[fs]\nfree_space=true\n')

            for mode_args in ([], ['-w']):
                with self.subTest(mode_args=mode_args):
                    with patch('sys.argv', ['glances', *mode_args, '-C', str(config_path)]):
                        args = GlancesMain().get_args()

                    self.assertTrue(args.fs_free_space)
