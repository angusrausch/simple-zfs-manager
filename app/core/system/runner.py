import asyncio
import os
import logging
import shlex
import subprocess

audit_logger = logging.getLogger("app.audit")
DEFAULT_TIMEOUT = 20


def run_command(uid: int, command: list[str], timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
    command_str = " ".join(shlex.quote(str(item)) for item in command)
    audit_logger.info(f"[CMD] User {uid} requested command: {command_str}")

    env = os.environ.copy()
    standard_paths = ["/sbin", "/usr/sbin", "/usr/local/sbin"]
    current_path = env.get("PATH", "")

    missing_paths = [p for p in standard_paths if p not in current_path]
    if missing_paths:
        env["PATH"] = f"{':'.join(missing_paths)}:{current_path}"

    try:
        run_return = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
            env=env
        )

    except subprocess.CalledProcessError as e:
        return_code = e.returncode

        output = e.stderr.strip() if e.stderr.strip() else e.stdout.strip()
        audit_logger.warning(f"[CMD] Command failed for User {uid} | Code: {return_code} | Error: {output}")
        
    except subprocess.TimeoutExpired:
        return_code = -1
        output = "Command timed out"
        audit_logger.error(f"[CMD] Command timed out for User {uid} after {timeout}s.")
        
    except OSError as e:
        return_code = -2
        output = f"System execution error: {e.strerror}"
        audit_logger.error(f"[CMD] Failed to execute binary for User {uid} | Error: {output} (Errno: {e.errno})")
        
    else:
        return_code = 0
        output = run_return.stdout.strip()
        audit_logger.info(f"[CMD] Command succeeded for User {uid}")

    return return_code, output


async def async_run_command(uid: int, command: list[str], timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
    return await asyncio.to_thread(run_command, uid, command, timeout)


async def create_piped_asyncio_subprocess(uid: int, command: list[str], stdin_pipe=asyncio.subprocess.PIPE) -> asyncio.subprocess.Process:
    command_str = " ".join(shlex.quote(str(item)) for item in command)
    audit_logger.info(f"[CMD] User {uid} requested command: {command_str}")

    return await asyncio.create_subprocess_exec(
        *command,
        stdin=stdin_pipe,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )