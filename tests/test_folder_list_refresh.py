"""Tests for the per-folder refresh timer of the folder list."""

from time import time

import pytest

import glances.folder_list as folder_list_mod
from glances.folder_list import FolderList


def expire(timer):
    """Push a timer past its deadline without touching its duration."""
    timer.target = time() - 1


class FakeConfig:
    """Minimal stand-in for the Glances config, with a single monitored folder."""

    def __init__(self, refresh):
        self.refresh = refresh

    def has_section(self, section):
        return section == 'folders'

    def get_value(self, section, key, default=None):
        return {'folder_1_path': '/a/folder', 'folder_1_refresh': self.refresh}.get(key, default)


@pytest.fixture
def walks(monkeypatch):
    """Count the folder_size() walks and keep the real filesystem out of it."""
    calls = []

    def fake_folder_size(path, refresh=False):
        calls.append(path)
        return 1234, 0

    monkeypatch.setattr(folder_list_mod, 'folder_size', fake_folder_size)
    return calls


@pytest.fixture(autouse=True)
def _empty_list():
    # The folder list is held on the class, so it survives between instances.
    FolderList._FolderList__folder_list = []
    yield
    FolderList._FolderList__folder_list = []


def test_folder_is_not_walked_again_before_its_refresh_delay(walks):
    folders = FolderList(FakeConfig('600'))
    for _ in range(4):
        folders.update()
    assert len(walks) == 1


def test_folder_is_walked_again_once_the_timer_is_over(walks):
    folders = FolderList(FakeConfig('600'))
    folders.update()
    expire(folders.timer_folders[0])
    folders.update()
    assert len(walks) == 2


def test_the_timer_is_restarted_after_a_walk(walks):
    folders = FolderList(FakeConfig('600'))
    folders.update()
    expire(folders.timer_folders[0])
    folders.update()
    # Restarted for another 600s, so the next cycles must not walk the folder again.
    assert not folders.timer_folders[0].finished()
    folders.update()
    assert len(walks) == 2


def test_a_folder_without_a_timer_is_still_updated(walks):
    folders = FolderList(FakeConfig('600'))
    folders.update()
    folders.timer_folders = []
    folders.update()
    assert len(walks) == 2
