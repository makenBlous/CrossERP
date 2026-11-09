"""安装检查在 Windows 上必须释放仍被占用的 SQLite 文件。"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "install_check.py"
_SPEC = importlib.util.spec_from_file_location("install_check", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
install_check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(install_check)


def test_cleanup_directory_retries_until_lock_clears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "data.db"
    target.write_bytes(b"locked")
    attempts = {"count": 0}
    real_rmtree = install_check.shutil.rmtree

    def flaky_rmtree(path: str | Path) -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError(32, "另一个程序正在使用此文件", str(target))
        real_rmtree(path)

    monkeypatch.setattr(install_check.shutil, "rmtree", flaky_rmtree)
    install_check._cleanup_directory(tmp_path, timeout=5)
    assert attempts["count"] == 3
    assert not tmp_path.exists()


def test_cleanup_directory_reports_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data.db").write_bytes(b"locked")

    def always_locked(path: str | Path) -> None:
        raise PermissionError(32, "另一个程序正在使用此文件", str(path))

    monkeypatch.setattr(install_check.shutil, "rmtree", always_locked)
    with pytest.raises(RuntimeError, match="无法删除临时目录"):
        install_check._cleanup_directory(tmp_path, timeout=0.4)


@pytest.mark.skipif(os.name != "nt", reason="只在 Windows 上验证进程树和文件锁")
def test_stop_process_releases_file_held_by_child(tmp_path: Path) -> None:
    locked = tmp_path / "data.db"
    child_code = textwrap.dedent(
        """
        import sys
        import time
        handle = open(sys.argv[1], "a+b")
        handle.write(b"x")
        handle.flush()
        time.sleep(120)
        """
    )
    parent_code = textwrap.dedent(
        """
        import subprocess
        import sys
        child = subprocess.Popen([sys.executable, "-c", sys.argv[1], sys.argv[2]])
        raise SystemExit(child.wait())
        """
    )
    parent = subprocess.Popen([sys.executable, "-c", parent_code, child_code, str(locked)])
    deadline = time.monotonic() + 10
    while not locked.exists():
        if parent.poll() is not None:
            raise AssertionError(f"父进程提前退出 exit={parent.returncode}")
        if time.monotonic() >= deadline:
            parent.kill()
            raise AssertionError("子进程没有打开数据库文件")
        time.sleep(0.05)

    install_check._stop_process(parent)
    install_check._cleanup_directory(tmp_path, timeout=10)
    assert parent.wait(timeout=5) is not None
    assert not tmp_path.exists()


def test_install_login_reads_csrf_from_html() -> None:
    html = (
        '<input type="hidden" name="next" value="/">'
        '<input type="hidden" name="csrf_token" value="issued-token">'
    )
    assert install_check._form_csrf(html) == "issued-token"
    assert install_check._form_csrf('<input name="csrf_token" value="">') == ""
