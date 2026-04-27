import os
from pathlib import Path

import pytest

from taskcli.config import find_global_root, resolve_root, CONFIG_DIR


def test_find_global_root_env_var(tmp_path, monkeypatch):
    custom = tmp_path / "custom_global_tasks"
    custom.mkdir()
    monkeypatch.setenv("TASKCLI_GLOBAL_ROOT", str(custom))
    monkeypatch.delenv("HOME", raising=False)

    root = find_global_root()
    assert root == custom.resolve()


def test_find_global_root_creates_dir(monkeypatch, tmp_path):
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("TASKCLI_GLOBAL_ROOT", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    expected = fake_home / ".tasks"
    root = find_global_root()
    assert root == expected
    assert expected.is_dir()
    assert (expected / "config").exists()


def test_resolve_root_global(monkeypatch, tmp_path):
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("TASKCLI_GLOBAL_ROOT", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    root = resolve_root("global")
    assert root == fake_home / ".tasks"


def test_resolve_root_project_not_found_raises(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TASKCLI_GLOBAL_ROOT", raising=False)

    with pytest.raises(FileNotFoundError):
        resolve_root("project")


def test_resolve_root_project_found(monkeypatch, tmp_path):
    tasks_dir = tmp_path / CONFIG_DIR
    tasks_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    root = resolve_root("project")
    assert root == tasks_dir.resolve()


def test_resolve_root_auto_fallback_to_global(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("TASKCLI_GLOBAL_ROOT", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    root = resolve_root("auto")
    assert root == fake_home / ".tasks"


def test_resolve_root_auto_project_wins(monkeypatch, tmp_path):
    tasks_dir = tmp_path / CONFIG_DIR
    tasks_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    root = resolve_root("auto")
    assert root == tasks_dir.resolve()
