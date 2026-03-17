import argparse
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_RUNTIME_VENV = BACKEND_DIR / ".runtime-venv"


def run_cmd(cmd: list[str], cwd: Path, desc: str) -> None:
    print(f"[setup] {desc} ...")
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{desc} failed with exit code {result.returncode}")


def try_run_cmd(cmd: list[str], cwd: Path, desc: str) -> subprocess.CompletedProcess:
    print(f"[setup] {desc} ...")
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
    )


def start_process(cmd: list[str], cwd: Path, name: str) -> subprocess.Popen:
    print(f"[start] {name}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(cwd))


def stop_process(proc: subprocess.Popen, name: str) -> None:
    if proc.poll() is not None:
        return
    print(f"[stop] {name}")
    if sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


def ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required tool not found in PATH: {name}")


def resolve_npm_cmd() -> str:
    npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_cmd:
        raise RuntimeError("Required tool not found in PATH: npm")
    return npm_cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start Text-to-SQL platform (backend + frontend) with Python manager."
    )
    parser.add_argument("--backend-host", default="0.0.0.0")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-host", default="0.0.0.0")
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--skip-install", action="store_true", help="Skip pip/npm install step")
    parser.add_argument(
        "--smoke-seconds",
        type=int,
        default=0,
        help="Auto-stop after N seconds (useful for startup smoke tests).",
    )
    return parser.parse_args()


def wait_http_ready(url: str, timeout_s: float = 30.0, interval_s: float = 1.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(interval_s)
    return False


def resolve_backend_python_cmd() -> list[str]:
    """
    Choose a Python interpreter compatible with current dependency pins.
    SQLAlchemy 2.0.25 is not compatible with Python 3.14 in this environment.
    """
    if sys.version_info < (3, 13):
        return [sys.executable]

    py_launcher = shutil.which("py")
    if py_launcher:
        probe = subprocess.run(
            [py_launcher, "-0p"],
            check=False,
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            lines = (probe.stdout or "").splitlines()
            for line in lines:
                if "3.12" in line:
                    parts = line.strip().split()
                    candidate = parts[-1] if parts else ""
                    if candidate and Path(candidate).exists():
                        print("[setup] Using Python 3.12 for backend (compatibility mode).")
                        return [candidate]
            for line in lines:
                if "3.11" in line or "3.10" in line:
                    parts = line.strip().split()
                    candidate = parts[-1] if parts else ""
                    if candidate and Path(candidate).exists():
                        print("[setup] Using Python <=3.12 for backend (compatibility mode).")
                        return [candidate]

    raise RuntimeError(
        "No compatible Python (<=3.12) found. "
        "Install Python 3.12 and rerun start.py."
    )


def install_backend_dependencies(python_cmd: list[str]) -> None:
    primary = try_run_cmd(
        [*python_cmd, "-m", "pip", "install", "-r", "requirements.txt"],
        BACKEND_DIR,
        "Install backend dependencies",
    )
    if primary.returncode == 0:
        return

    combined = (primary.stdout or "") + "\n" + (primary.stderr or "")
    asyncpg_build_failed = "asyncpg" in combined.lower()
    if not asyncpg_build_failed:
        print(primary.stdout)
        print(primary.stderr)
        raise RuntimeError(f"Install backend dependencies failed with exit code {primary.returncode}")

    print("[warn] asyncpg build failed, fallback to runtime-only install (without asyncpg).")
    requirements = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
    filtered = [line for line in requirements if "asyncpg" not in line.lower()]
    fallback_path = BACKEND_DIR / ".requirements.runtime.tmp.txt"
    fallback_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    try:
        run_cmd(
            [*python_cmd, "-m", "pip", "install", "-r", fallback_path.name],
            BACKEND_DIR,
            "Install backend runtime dependencies (fallback)",
        )
    finally:
        if fallback_path.exists():
            fallback_path.unlink()


def ensure_backend_runtime_python(base_python_cmd: list[str]) -> list[str]:
    """
    Create/use project-local backend venv so startup is deterministic and
    not blocked by externally-managed Python environments.
    """
    if sys.platform.startswith("win"):
        venv_python = BACKEND_RUNTIME_VENV / "Scripts" / "python.exe"
    else:
        venv_python = BACKEND_RUNTIME_VENV / "bin" / "python"

    if not venv_python.exists():
        print(f"[setup] Creating backend runtime venv at {BACKEND_RUNTIME_VENV}")
        run_cmd(
            [*base_python_cmd, "-m", "venv", str(BACKEND_RUNTIME_VENV)],
            BACKEND_DIR,
            "Create backend runtime venv",
        )

    # Ensure pip exists and is current enough for resolver compatibility.
    run_cmd([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], BACKEND_DIR, "Upgrade pip in backend venv")
    return [str(venv_python)]


def main() -> int:
    args = parse_args()
    backend_proc: subprocess.Popen | None = None
    frontend_proc: subprocess.Popen | None = None

    try:
        npm_cmd = resolve_npm_cmd()
        base_backend_python_cmd = resolve_backend_python_cmd()
        backend_python_cmd = ensure_backend_runtime_python(base_backend_python_cmd)

        if not args.skip_install:
            install_backend_dependencies(backend_python_cmd)
            run_cmd([npm_cmd, "install"], FRONTEND_DIR, "Install frontend dependencies")

        backend_proc = start_process(
            [
                *backend_python_cmd,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                args.backend_host,
                "--port",
                str(args.backend_port),
            ],
            BACKEND_DIR,
            "Backend",
        )

        # Give backend a short warmup before frontend starts.
        time.sleep(1.5)

        frontend_proc = start_process(
            [
                npm_cmd,
                "run",
                "dev",
                "--",
                "--host",
                args.frontend_host,
                "--port",
                str(args.frontend_port),
            ],
            FRONTEND_DIR,
            "Frontend",
        )

        backend_ok = wait_http_ready(f"http://127.0.0.1:{args.backend_port}/health")
        frontend_ok = wait_http_ready(f"http://127.0.0.1:{args.frontend_port}")
        if not backend_ok or not frontend_ok:
            raise RuntimeError("Service health check failed after startup")

        print("\n========================================")
        print("Text-to-SQL services are running")
        print(f"Backend URL:   http://localhost:{args.backend_port}")
        print(f"API Docs:      http://localhost:{args.backend_port}/docs")
        print(f"Frontend URL:  http://localhost:{args.frontend_port}")
        print("Press Ctrl+C to stop all services")
        if args.smoke_seconds > 0:
            print(f"Smoke mode: auto stop after {args.smoke_seconds}s")
        print("========================================\n")

        started_at = time.time()
        while True:
            if backend_proc.poll() is not None:
                raise RuntimeError("Backend process exited unexpectedly")
            if frontend_proc.poll() is not None:
                raise RuntimeError("Frontend process exited unexpectedly")
            if args.smoke_seconds > 0 and (time.time() - started_at) >= args.smoke_seconds:
                print("[smoke] Startup smoke test passed.")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[signal] Ctrl+C received. Stopping services...")
    except Exception as exc:
        print(f"\n[error] {exc}")
        return_code = 1
    else:
        return_code = 0
    finally:
        if frontend_proc:
            stop_process(frontend_proc, "Frontend")
        if backend_proc:
            stop_process(backend_proc, "Backend")

    return return_code


if __name__ == "__main__":
    # Ensure Ctrl+C works immediately on Windows too.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    raise SystemExit(main())
