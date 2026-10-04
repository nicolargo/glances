#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Glances contributors
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Configured folder lists must not share state between instances."""

from glances.config import Config
from glances.folder_list import FolderList


def test_configured_folder_lists_are_independent(tmp_path):
    first_config = tmp_path / 'first.conf'
    first_config.write_text('[folders]\nfolder_1_path=/first\nfolder_1_refresh=600\n')
    second_config = tmp_path / 'second.conf'
    second_config.write_text('[folders]\nfolder_1_path=/second\nfolder_1_refresh=60\n')

    first = FolderList(Config(config_dir=str(first_config)))
    second = FolderList(Config(config_dir=str(second_config)))

    assert [folder['path'] for folder in first.get()] == ['/first']  # nosec B101 - pytest regression assertion.
    assert [folder['path'] for folder in second.get()] == ['/second']  # nosec B101 - pytest regression assertion.
    assert len(first) == len(first.timer_folders) == 1  # nosec B101 - pytest regression assertion.
    assert len(second) == len(second.timer_folders) == 1  # nosec B101 - pytest regression assertion.
