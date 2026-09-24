"""Install a package into the running environment: conda (or mamba), else pip. Qt-free.

Both GUIs offer to install an optional backend (umap-learn, napari)
when a method needs it; this is the part that does it -- finding the solver,
running it (elevated on Windows when the environment is not writable), and
testing the import afterwards. The Qt prompts live in
:mod:`ndxplorer.deps_installer`; the emtk app runs :func:`install_task` as an
:mod:`emtk.tasks` task and shows its log.

Nothing here can work in a browser: there is no process to start.
"""
from __future__ import annotations

import importlib
import os
import shutil  # noqa: F401 - kept for callers that patch it
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..logging_config import logging

# ------------------------------
# Low-level command execution
# ------------------------------

def _run_command(cmd: List[str]) -> Tuple[bool, Optional[str], str, str]:
    """
    Run a command, capture stdout/stderr.

    Returns: (ok, error_message, stdout, stderr)
    """
    try:
        logging.debug(f"deps_installer: executing: {' '.join(cmd)}")
        popen_cmd = cmd
        use_shell = False
        if os.name == 'nt':
            exe = (cmd[0] if cmd else '').lower()
            if exe.endswith('.bat') or exe.endswith('.cmd'):
                popen_cmd = ['cmd.exe', '/C', *cmd]
                logging.debug("deps_installer: wrapping batch with cmd.exe /C on Windows")
        proc = subprocess.Popen(
            popen_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell,
        )
        out, err = proc.communicate()
        if out:
            logging.debug(f"deps_installer stdout:\n{out}")
        if err:
            logging.debug(f"deps_installer stderr:\n{err}")
        if proc.returncode != 0:
            return False, f"Exit code {proc.returncode}", out, err
        return True, None, out, err
    except Exception as e:
        return False, str(e), '', ''


def _needs_elevation(env_prefix: str) -> bool:
    """
    Heuristic to decide if we may need elevation to modify the environment.
    On Windows, if env is under Program Files or not writable.
    On POSIX, if env is under /usr (not /usr/local) or not writable.
    """
    try:
        env_path = Path(env_prefix)
        if os.name == 'nt':
            program_files = os.environ.get('ProgramFiles', r'C:\\Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\\Program Files (x86)')
            if str(env_path).startswith(program_files) or str(env_path).startswith(program_files_x86):
                return True
        else:
            if str(env_path).startswith('/usr') and not str(env_path).startswith('/usr/local'):
                return True
        # Try a write test inside env
        test_dir = env_path / 'conda-meta'
        if not test_dir.exists():
            test_dir = env_path
        test_file = test_dir / ('.write_test_' + next(tempfile._get_candidate_names()))
        try:
            with open(test_file, 'w') as f:
                f.write('ok')
            test_file.unlink(missing_ok=True)  # type: ignore[arg-type]
            return False
        except Exception:
            return True
    except Exception:
        # Be conservative
        return False


def _run_with_elevation(cmd: List[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Windows-only: run command elevated, logging output to a persistent file.
    Returns: (ok, error_message, log_file_path)
    On non-Windows, falls back to normal run.
    """
    if os.name != 'nt':
        ok, err, _, _ = _run_command(cmd)
        return ok, err, None
    try:
        temp_dir = tempfile.mkdtemp(prefix='ndxplorer_elev_')
        log_file = os.path.join(temp_dir, 'elevated_command.log')
        # Properly quote args with spaces
        quoted = [f'"{a}"' if (' ' in str(a) and not str(a).startswith('"')) else str(a) for a in cmd]
        win_cmd = ' '.join(quoted)
        batch_file = os.path.join(temp_dir, 'run_elevated.bat')
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write(f'echo Running elevated command at %DATE% %TIME% > "{log_file}"\n')
            f.write(f'echo Command: {win_cmd} >> "{log_file}"\n')
            f.write(f'{win_cmd} >> "{log_file}" 2>&1\n')
            f.write('set EXITCODE=%ERRORLEVEL%\n')
            f.write(f'echo. >> "{log_file}"\n')
            f.write(f'echo Exit code: %EXITCODE% >> "{log_file}"\n')
            f.write('if %EXITCODE% NEQ 0 (\n')
            f.write(f'  echo Elevated command failed with error code %EXITCODE% >> "{log_file}"\n')
            f.write('  exit /b %EXITCODE%\n')
            f.write(')\n')
            f.write('echo Elevated command completed successfully >> "{log_file}"\n')
            f.write('exit /b 0\n')
        ps = [
            'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            f"$p = Start-Process -FilePath '{batch_file}' -Verb RunAs -Wait -PassThru; exit $p.ExitCode",
        ]
        logging.debug(f"deps_installer: running elevated batch: {batch_file}")
        logging.debug(f"deps_installer: elevated log: {log_file}")
        proc = subprocess.Popen(ps, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        if out:
            logging.debug(f"elevation launcher stdout:\n{out}")
        if err:
            logging.debug(f"elevation launcher stderr:\n{err}")
        if proc.returncode != 0:
            # Provide tail hint
            tail_hint = ''
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', errors='ignore') as lf:
                        lines = lf.readlines()
                        tail_hint = ''.join(lines[-25:]).strip()
            except Exception:
                pass
            msg = f"Elevation failed with exit code {proc.returncode}. See log: {log_file}"
            if tail_hint:
                msg += f"\n--- Log tail ---\n{tail_hint}"
            return False, msg, log_file
        return True, None, log_file
    except Exception as e:
        return False, str(e), None


# ------------------------------
# Conda and pip helpers
# ------------------------------

def find_conda_executable() -> str:
    """Try to locate a conda executable suitable for running commands."""
    conda_exe = os.environ.get('CONDA_EXE', '')
    if conda_exe and os.path.exists(conda_exe):
        return conda_exe
    candidates: list[str] = []
    if os.name == 'nt':
        candidates.extend([
            str(Path(sys.prefix) / 'Scripts' / 'conda.exe'),
            str(Path(sys.prefix) / 'condabin' / 'conda.bat'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'Scripts' / 'conda.exe'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'condabin' / 'conda.bat'),
        ])
    else:
        candidates.extend([
            str(Path(sys.prefix) / 'bin' / 'conda'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'bin' / 'conda'),
        ])
    for c in candidates:
        if c and os.path.exists(c):
            os.environ['CONDA_EXE'] = c
            return c
    return 'conda'  # hope it's on PATH


def find_mamba_executable() -> Optional[str]:
    """Locate mamba or micromamba if available, preferring mamba.

    Returns an absolute path when possible. If not found, returns None.
    """
    # Check env hints first
    for var in ('MAMBA_EXE', 'MAMBA', 'MICROMAMBA_EXE'):
        p = os.environ.get(var, '')
        if p and os.path.exists(p):
            return p
    candidates: list[str] = []
    if os.name == 'nt':
        # Common Windows paths inside the current env or CONDA_PREFIX
        candidates.extend([
            str(Path(sys.prefix) / 'Scripts' / 'mamba.exe'),
            str(Path(sys.prefix) / 'condabin' / 'mamba.bat'),
            str(Path(sys.prefix) / 'Scripts' / 'micromamba.exe'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'Scripts' / 'mamba.exe'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'condabin' / 'mamba.bat'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'Scripts' / 'micromamba.exe'),
        ])
    else:
        candidates.extend([
            str(Path(sys.prefix) / 'bin' / 'mamba'),
            str(Path(sys.prefix) / 'bin' / 'micromamba'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'bin' / 'mamba'),
            str(Path(os.environ.get('CONDA_PREFIX', '')) / 'bin' / 'micromamba'),
        ])
    for c in candidates:
        if c and os.path.exists(c):
            return c
    # Fallback to PATH resolution using shutil.which
    try:
        from shutil import which
    except Exception:
        which = None  # type: ignore
    if which is not None:
        path = which('mamba')
        if path:
            # Prefer native exe over BAT wrappers when possible
            p_lower = path.lower()
            if p_lower.endswith('mamba.bat') or p_lower.endswith('mamba.cmd'):
                try:
                    # Try to reconstruct base prefix and use Scripts\mamba.exe
                    base = Path(path).parents[2]  # .../Library/Bin -> base
                    exe_candidate = base / 'Scripts' / 'mamba.exe'
                    if exe_candidate.exists():
                        return str(exe_candidate)
                except Exception:
                    pass
            return path
        path = which('micromamba')
        if path:
            return path
    return None


def choose_solver() -> Tuple[str, str]:
    """
    Choose the best available conda-family solver executable and its name.
    Returns (exe_path_or_name, solver_name) where solver_name in { 'mamba', 'micromamba', 'conda' }.
    """
    m = find_mamba_executable()
    if m:
        # Try to infer the solver name from path/basename
        base = os.path.basename(m).lower()
        solver_name = 'micromamba' if 'micro' in base else 'mamba'
        logging.debug(f"deps_installer: choosing solver {solver_name} at: {m}")
        return m, solver_name
    c = find_conda_executable()
    logging.debug(f"deps_installer: choosing solver conda at: {c}")
    return c, 'conda'


def conda_install(packages: List[str], channels: Optional[List[str]] = None, update_deps: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Install given packages into current env (sys.prefix) via conda-family solver.
    Prefers mamba/micromamba when available, falls back to conda.
    """
    channels = channels or ['conda-forge', 'defaults']
    solver_exe, solver_name = choose_solver()
    env_path = sys.prefix
    cmd: List[str] = [
        solver_exe, 'install', '-y', '--prefix', env_path,
    ]
    if update_deps and solver_name == 'conda':
        # Only conda needs --update-deps explicitly; mamba/micromamba update deps by default
        cmd.append('--update-deps')
    cmd.extend(packages)
    for ch in channels:
        cmd.extend(['-c', ch])
    logging.info(f"{solver_name} install -> env: {env_path}")
    logging.debug("solver command: " + ' '.join(cmd))
    if _needs_elevation(env_path):
        ok, err, _ = _run_with_elevation(cmd)
        if not ok:
            return False, err
    else:
        ok, err, _, _ = _run_command(cmd)
        if not ok:
            return False, err
    # Diagnostics: list packages via conda (or solver)
    try:
        list_cmd = [solver_exe, 'list', '--prefix', env_path, *packages]
        logging.debug("list command: " + ' '.join(list_cmd))
        _ok, _err, out, _ = _run_command(list_cmd)
        if not _ok:
            logging.warning(f"list command reported an issue: {_err}")
        else:
            logging.debug(f"list output:\n{out}")
    except Exception as e:
        logging.debug(f"list diagnostic failed: {e}")
    return True, None


def pip_install(packages: List[str]) -> Tuple[bool, Optional[str]]:
    """Install packages via pip into the current environment."""
    cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', *packages]
    logging.info("pip install -> packages: " + ', '.join(packages))
    logging.debug("pip command: " + ' '.join(cmd))
    ok, err, _, _ = _run_command(cmd)
    return ok, err


def try_import(import_name: str) -> Tuple[bool, Optional[str]]:
    try:
        mod = __import__(import_name)
        ver = getattr(mod, '__version__', 'unknown')
        logging.info(f"Import test succeeded for {import_name}, version: {ver}")
        return True, None
    except Exception as e:
        logging.warning(f"Import test failed for {import_name}: {e}")
        return False, str(e)


def install_task(task, packages: List[str], channels: Optional[List[str]] = None,
                 import_name: Optional[str] = None):
    """Install *packages* with conda (``channels``), then test *import_name*.

    A generator for :func:`emtk.tasks.start`: yields status lines, writes the
    solver's command and output to ``task.write`` (the progress window's log),
    and returns ``True`` when the package imports afterwards.
    """
    channels = channels or ["conda-forge", "defaults"]
    solver, name = choose_solver()
    yield None, f"Installing {', '.join(packages)} with {name}…"
    if hasattr(task, "write"):
        task.write(f"{name} install {' '.join(packages)} -c {' -c '.join(channels)}\n"
                   f"into {sys.prefix}\n")
    ok, err = conda_install(list(packages), channels=channels)
    if hasattr(task, "write"):
        task.write(("installed\n" if ok else f"failed: {err}\n"))
    if not ok:
        return False
    if import_name:
        importlib.invalidate_caches()
        imported, err = try_import(import_name)
        if hasattr(task, "write"):
            task.write(f"import {import_name}: {'ok' if imported else err}\n")
        return imported
    return True


RISK_NOTE = (
    "Warning: Installing additional packages can change the ChiSurf environment. "
    "This may break your ChiSurf installation and could require reinstalling ChiSurf."
)
