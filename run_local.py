"""Portable local launcher. Uses this laptop's private setup and database."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    raise SystemExit('First run setup_local.py (Windows: SETUP-FIRST.cmd).')
if not (ROOT / '.env').exists():
    raise SystemExit('First run the private setup. Windows: CONFIGURE-DEMO.cmd.')
(ROOT / 'data').mkdir(exist_ok=True)
def run(command):
    subprocess.run(command, cwd=ROOT, check=True)
try:
    run(['docker', 'info', '--format', '{{.ServerVersion}}'])
    run(['docker', 'compose', 'up', '-d', '--wait'])
    run([str(python), '-m', 'alembic', 'upgrade', 'head'])
    print('Open http://127.0.0.1:8011. Keep this window open. Stop with Ctrl+C.')
    run([str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8011'])
except KeyboardInterrupt:
    print('Application stopped; saved local records are preserved.')
except (OSError, subprocess.CalledProcessError) as exc:
    raise SystemExit(f'Startup stopped. Check that Docker Desktop is running and setup completed. {exc}')
