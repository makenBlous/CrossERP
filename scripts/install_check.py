"""从本地 wheel 计时安装、初始化、演示和真实登录。"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


def _run(command: list[str], *, env: dict[str, str], input_text: str | None = None) -> None:
    completed = subprocess.run(
        command,
        env=env,
        input=input_text,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"命令失败({completed.returncode}): {' '.join(command)}")


def _find_wheel(pattern: str) -> Path:
    candidates = [Path(item) for item in glob.glob(pattern)]
    if len(candidates) != 1:
        raise RuntimeError(f"wheel 匹配数量应为 1, 实际为 {len(candidates)}: {pattern}")
    return candidates[0].resolve()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(
    url: str, *, timeout: float = 90.0, process: subprocess.Popen[bytes] | None = None
) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"服务进程提前退出，退出码 {process.returncode}")  # noqa: RUF001
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"服务未在 {timeout:.0f}s 内就绪: {last_error}")


def _login(base_url: str, username: str, password: str) -> bool:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with opener.open(f"{base_url}/login", timeout=5) as response:
        if response.status != 200:
            return False
    csrf = next((cookie.value for cookie in jar if cookie.name == "crosserp_login_csrf"), "")
    payload = urlencode(
        {
            "username": username,
            "password": password,
            "csrf_token": csrf,
            "next": "/",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/login",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with opener.open(request, timeout=5) as response:
            return response.status in {200, 303}
    except urllib.error.HTTPError as exc:
        return exc.code == 303


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, help="本地 wheel 路径或 glob")
    parser.add_argument("--output", type=Path, default=Path(".ci/install-timing.json"))
    args = parser.parse_args()

    started = time.perf_counter()
    wheel = _find_wheel(args.wheel)
    root = Path.cwd().resolve()
    result: dict[str, Any] = {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "wheel": str(wheel),
        "steps": [],
        "login_success": False,
    }
    env = os.environ.copy()
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("找不到 uv。CI 或本机请先安装 uv 0.13.x。")

    tool_root = root / ".ci" / "uv-tools"
    tool_bin = root / ".ci" / "uv-bin"
    tool_root.mkdir(parents=True, exist_ok=True)
    tool_bin.mkdir(parents=True, exist_ok=True)
    env.update({"UV_TOOL_DIR": str(tool_root), "UV_TOOL_BIN_DIR": str(tool_bin)})

    def step(name: str, action: Any) -> None:
        begin = time.perf_counter()
        action()
        result["steps"].append({"name": name, "seconds": round(time.perf_counter() - begin, 3)})

    step("uv", lambda: _run([uv, "--version"], env=env))
    step("wheel_install", lambda: _run([uv, "tool", "install", str(wheel), "--force"], env=env))
    executable = tool_bin / ("crosserp.exe" if os.name == "nt" else "crosserp")
    if not executable.exists():
        raise RuntimeError(f"uv tool 未生成命令: {executable}")

    with tempfile.TemporaryDirectory(prefix="crosserp-install-check-") as raw_dir:
        work = Path(raw_dir)
        database = work / "data.db"
        demo_database = work / "demo.db"
        database_url = f"sqlite:///{database.as_posix()}"
        username = "install-check"
        password = "Install-check-password-123"
        env.update(
            {
                "CROSSERP_DATABASE_URL": database_url,
                "CROSSERP_COOKIE_SECURE": "0",
                "PYTHONUTF8": "1",
            }
        )

        step(
            "init",
            lambda: _run(
                [str(executable), "init", "--admin-username", username, "--admin-password-stdin"],
                env=env,
                input_text=f"{password}\n{password}\n",
            ),
        )
        step(
            "demo",
            lambda: _run(
                [
                    str(executable),
                    "demo",
                    "--db",
                    f"sqlite:///{demo_database.as_posix()}",
                    "--check",
                    "--no-browser",
                ],
                env=env,
            ),
        )
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [str(executable), "serve", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            step("serve", lambda: _wait_for_health(f"{base_url}/health", process=process))
            begin = time.perf_counter()
            result["login_success"] = _login(base_url, username, password)
            result["steps"].append(
                {"name": "login", "seconds": round(time.perf_counter() - begin, 3)}
            )
            if not result["login_success"]:
                raise RuntimeError("登录失败")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    result["total_seconds"] = round(time.perf_counter() - started, 3)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
