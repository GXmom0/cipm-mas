from __future__ import annotations

import argparse
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdk.settings import CipmSettings  # noqa: E402


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本地一键启动中台与仪表盘")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--api-only", action="store_true", help="仅启动业务中台")
    group.add_argument("--ui-only", action="store_true", help="仅启动仪表盘")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    return parser.parse_args(argv)


def build_commands(settings: CipmSettings, args: argparse.Namespace) -> list[list[str]]:
    commands: list[list[str]] = []
    python = sys.executable
    if not args.ui_only:
        commands.append(
            [python, "-m", "uvicorn", "apps.platform_api.main:app", "--host", "127.0.0.1", "--port", str(settings.api_port)]
        )
    if not args.api_only:
        commands.append(
            [python, "-m", "streamlit", "run", "apps/console/app.py", "--server.port", str(settings.ui_port)]
        )
    return commands


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = CipmSettings.from_env(ROOT / ".env")
    host = "127.0.0.1"

    target_ports = []
    if not args.ui_only:
        target_ports.append(("中台", settings.api_port))
    if not args.api_only:
        target_ports.append(("仪表盘", settings.ui_port))
    for name, port in target_ports:
        if port_in_use(host, port):
            print(f"[启动失败] {name}端口 {port} 已被占用，请先释放该端口。", file=sys.stderr)
            return 3

    for label, module in (("中台", "apps.platform_api.main"), ("仪表盘", "apps.console.app")):
        if label == "中台" and args.ui_only:
            continue
        if label == "仪表盘" and args.api_only:
            continue
        if importlib.util.find_spec(module) is None:
            print(f"[未就绪] {module} 尚未实现，请先完成对应任务组。", file=sys.stderr)
            return 4
    if not args.api_only and importlib.util.find_spec("streamlit") is None:
        print("[未就绪] 未安装 streamlit，请执行：pip install -e .[ui]", file=sys.stderr)
        return 4

    mode = "演示模式：零外部依赖" if settings.mock else f"云端模式：{settings.runtime}"
    print(f"CIPM_RUNTIME={settings.runtime} CIPM_MOCK={int(settings.mock)}")
    print(f"{mode}")
    print(f"中台地址：http://{host}:{settings.api_port}")
    print(f"仪表盘地址：http://{host}:{settings.ui_port}")

    processes: list[subprocess.Popen] = []
    try:
        for command in build_commands(settings, args):
            processes.append(subprocess.Popen(command, cwd=ROOT))
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n正在停止本地服务...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())