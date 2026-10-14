$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& ./.venv/Scripts/python.exe -c "from dotenv import dotenv_values; import sys; sys.exit(0 if dotenv_values('.env').get('ADMIN_PASSWORD_HASH') else 1)"
if ($LASTEXITCODE -ne 0) { & ./.venv/Scripts/python.exe setup_demo.py; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
Write-Host 'Checking the local database engine...'
$dockerReady = $false
try { docker info --format '{{.ServerVersion}}' 2>$null; $dockerReady = $LASTEXITCODE -eq 0 } catch { $dockerReady = $false }
if (-not $dockerReady) { docker desktop start --timeout 60; if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop and wait for the engine to start.' } }
docker compose up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'The local database did not start.' }
& ./.venv/Scripts/python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database setup failed. Existing data is preserved.' }
Write-Host 'Open http://127.0.0.1:8011. Admin username: admin.'
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
