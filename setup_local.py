"""First-time setup: creates this laptop's environment; contains no credentials."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run(command):
    subprocess.run(command, cwd=ROOT, check=True)

def main():
    os.chdir(ROOT)
    if sys.version_info < (3, 12):
        raise SystemExit('Install Python 3.12 or newer from https://www.python.org/downloads/ first.')
    if not shutil.which('docker'):
        raise SystemExit('Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and start it first.')
    run(['docker', 'info', '--format', '{{.ServerVersion}}'])
    print('Setup downloads the pinned Python packages from official PyPI (https://pypi.org).')
    print('Starting the app later may download the pgvector/pgvector database image from Docker Hub.')
    print('No Gemini request is made by this setup. Your own key is entered in a private window.')
    if input('Type INSTALL to continue: ').strip().upper() != 'INSTALL':
        raise SystemExit('Setup stopped. No downloads were started.')
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        run([sys.executable, '-m', 'venv', str(environment)])
    run([str(python), '-m', 'pip', '--isolated', 'install', '--index-url', 'https://pypi.org/simple', '-r', 'requirements-lock.txt'])
    (ROOT / 'data').mkdir(exist_ok=True)
    if not (ROOT / '.env').exists():
        shutil.copyfile(ROOT / '.env.example', ROOT / '.env')
    run([str(python), 'setup_demo.py'])
    print('Setup complete. Windows: double-click START-DEMO.cmd. Mac/Linux: python3 run_local.py')

if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f'Setup stopped because a required step failed (exit {exc.returncode}). Read the message above.')
