# Always run the dashboard with the project virtual environment.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Project venv not found at $Python"
    exit 1
}

Set-Location $ProjectRoot
& $Python -m streamlit run dashboard/app.py @args
