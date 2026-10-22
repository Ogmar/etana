<#
.SYNOPSIS
    Launch-day startup: one command from cold machine to archiving telemetry.

.DESCRIPTION
    1. Ensures the Docker engine is running (starts Docker Desktop if not).
    2. Starts the Postgres container.
    3. Waits until Postgres accepts TCP connections. The compose healthcheck is
       not enough: on first init Postgres runs a temporary server that answers
       pg_isready on its Unix socket but not on TCP, and connecting then gives
       "server closed the connection unexpectedly". Probing over TCP inside the
       container only passes once the real server is up.
    4. Applies migrations (in case the schema changed since the last flight).
    5. Runs ingestion against the packet source, archiving to Postgres.

    The packet source is TCP (the transport seam): the simulator for a rehearsal,
    or whatever bridges the ground receiver onto a TCP port on launch day.
    With -Simulate, the script also starts the simulator on 127.0.0.1:<Port>
    and stops it when ingestion exits.

.EXAMPLE
    .\launch.ps1 -Name "Eagle-1 flight 1"
.EXAMPLE
    .\launch.ps1 -Name "rehearsal" -SourceHost 192.168.1.50 -Port 9000
.EXAMPLE
    .\launch.ps1 -Name "dress rehearsal" -Simulate -Speed 60
#>
param(
    # Name of the flight record created in the archive.
    [Parameter(Mandatory = $true)][string]$Name,
    # Packet source address. ($Host is reserved in PowerShell, hence SourceHost.)
    [string]$SourceHost = "127.0.0.1",
    [int]$Port = 9000,
    # Seconds to wait for Docker and for Postgres before giving up.
    [int]$TimeoutSec = 120,
    # Rehearsal mode: also start the simulator as the packet source.
    [switch]$Simulate,
    # Simulator speed (sim-seconds per real second); only used with -Simulate.
    [double]$Speed = 60
)

if ($Simulate -and $SourceHost -ne "127.0.0.1") {
    Write-Host "FAILED: -Simulate runs the simulator locally; don't combine it with -SourceHost" -ForegroundColor Red
    exit 1
}

$root = $PSScriptRoot

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "FAILED: $msg" -ForegroundColor Red; exit 1 }

# Read POSTGRES_USER / POSTGRES_DB from .env (same defaults as docker-compose.yml).
$envVals = @{ POSTGRES_USER = "etana"; POSTGRES_DB = "etana" }
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) { Fail ".env not found at $envFile (copy .env.example)" }
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*(POSTGRES_USER|POSTGRES_DB)\s*=\s*(.+?)\s*$') { $envVals[$Matches[1]] = $Matches[2] }
}

# Migrations and the app must target the same database; a stray ETANA_DB=sqlite
# would migrate SQLite while ingestion writes to Postgres.
if ($env:ETANA_DB) {
    Write-Host "warning: ETANA_DB=$($env:ETANA_DB) is set; clearing it for this run so everything targets Postgres" -ForegroundColor Yellow
    Remove-Item Env:ETANA_DB
}

Step "Checking Python packages"
python -c "import ccsds, ingestion, django, psycopg" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Python packages missing; pip install -e each package (see CLAUDE.md)" }

Step "Checking Docker engine"
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerDesktop)) { Fail "Docker engine not running and Docker Desktop not found" }
    Write-Host "starting Docker Desktop ..."
    Start-Process $dockerDesktop
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        if ((Get-Date) -gt $deadline) { Fail "Docker engine did not start within $TimeoutSec s" }
        Start-Sleep -Seconds 3
        docker info 2>$null | Out-Null
    } while ($LASTEXITCODE -ne 0)
}
Write-Host "docker engine ready"

Step "Starting Postgres"
Push-Location $root
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { Fail "docker compose up failed" }

    Write-Host "waiting for Postgres to accept TCP connections ..."
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        if ((Get-Date) -gt $deadline) { Fail "Postgres not ready within $TimeoutSec s (check: docker compose logs postgres)" }
        Start-Sleep -Seconds 2
        docker compose exec -T postgres pg_isready -h 127.0.0.1 -p 5432 -U $envVals.POSTGRES_USER -d $envVals.POSTGRES_DB 2>$null | Out-Null
    } while ($LASTEXITCODE -ne 0)
    Write-Host "postgres ready"
} finally {
    Pop-Location
}

Step "Applying migrations"
Push-Location (Join-Path $root "services\api")
try {
    python manage.py migrate
    if ($LASTEXITCODE -ne 0) { Fail "migrate failed" }
} finally {
    Pop-Location
}

$simulator = $null
if ($Simulate) {
    Step "Starting simulator on 127.0.0.1:$Port (speed x$Speed)"
    $simulator = Start-Process python -ArgumentList "-m", "simulator.main", "--port", $Port, "--speed", $Speed `
        -WorkingDirectory (Join-Path $root "services\simulator") -NoNewWindow -PassThru
    # Don't probe the port: the simulator serves one client and starts the flight
    # on connect, so a probe would consume it. Give it a moment to bind instead.
    Start-Sleep -Seconds 1
    if ($simulator.HasExited) { Fail "simulator exited before ingestion could connect (port $Port in use?)" }
}

try {
    Step "Starting ingestion: '$Name' from ${SourceHost}:$Port"
    python -m ingestion.main --name $Name --host $SourceHost --port $Port
    $code = $LASTEXITCODE
} finally {
    if ($simulator -and -not $simulator.HasExited) { Stop-Process -Id $simulator.Id -Force }
}
exit $code
