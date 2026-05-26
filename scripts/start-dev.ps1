param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$FrontendRun = "C:\Users\Public\ProjetoIntegrador05-run\frontend"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$RunDir = Join-Path $Root ".run"
$BackendLog = Join-Path $RunDir "backend.log"
$BackendErr = Join-Path $RunDir "backend.err.log"
$FrontendLog = Join-Path $RunDir "frontend.log"
$FrontendErr = Join-Path $RunDir "frontend.err.log"
$env:NODE_NO_WARNINGS = "1"

function Invoke-Checked {
    param(
        [scriptblock]$Command,
        [string]$ErrorMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

function Stop-Port {
    param([int]$Port)

    $connections = netstat -ano | Select-String ":$Port"
    foreach ($connection in $connections) {
        $parts = ($connection.Line -split "\s+") | Where-Object { $_ }
        if ($parts.Count -ge 5 -and $parts[3] -eq "LISTENING") {
            $pidToStop = [int]$parts[4]
            if ($pidToStop -gt 0) {
                cmd.exe /c "taskkill /PID $pidToStop /T /F >nul 2>nul"
            }
        }
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

Write-Host ""
Write-Host "=== Projeto Integrador 05 - start ==="
Write-Host ""

if (-not (Test-Path $VenvPython)) {
    Write-Host "Criando ambiente Python em .venv..."
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python nao encontrado no PATH. Instale Python 3.11+ ou adicione-o ao PATH."
    }
    & $python.Source -m venv (Join-Path $Root ".venv")
}

if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Path $RunDir | Out-Null
}

Write-Host "Instalando/validando dependencias Python..."
Invoke-Checked -Command {
    & $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements.txt")
} -ErrorMessage "Falha ao instalar dependencias Python."

$tesseract = Get-Command tesseract.exe -ErrorAction SilentlyContinue
if (-not $tesseract) {
    $commonTesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
    if (-not (Test-Path $commonTesseract)) {
        $windowsOcr = & $VenvPython -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('winsdk') else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Tesseract OCR nao encontrado; usando fallback OCR nativo do Windows."
        } else {
            Write-Host ""
            Write-Host "Aviso: nenhum OCR local encontrado."
            Write-Host "PDFs escaneados/imagem abrem no preview, mas nao terao extracao completa sem OCR."
            Write-Host "Instale Tesseract OCR ou mantenha a dependencia winsdk instalada na venv."
            Write-Host ""
        }
    }
}

Write-Host "Sincronizando frontend para caminho sem acento..."
if (-not (Test-Path $FrontendRun)) {
    New-Item -ItemType Directory -Path $FrontendRun -Force | Out-Null
}
& robocopy $Frontend $FrontendRun /MIR /XD node_modules dist /XF vite.log vite.err.log | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Falha ao sincronizar frontend para $FrontendRun."
}

Write-Host "Instalando/validando dependencias do frontend..."
Push-Location $FrontendRun
try {
    Invoke-Checked -Command {
        & npm.cmd install --no-audit --fund=false
    } -ErrorMessage "Falha ao instalar dependencias do frontend."
} finally {
    Pop-Location
}

Write-Host "Liberando portas 8000 e 5173..."
Stop-Port 8000
Stop-Port 5173
Start-Sleep -Seconds 2

$backendPortBusy = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
$frontendPortBusy = netstat -ano | Select-String ":5173" | Select-String "LISTENING"

if ($backendPortBusy) {
    throw "A porta 8000 ainda esta ocupada. Execute .\scripts\stop-dev.ps1 como administrador ou reinicie o Windows se a porta ficou presa por um processo antigo."
}

if ($frontendPortBusy) {
    throw "A porta 5173 ainda esta ocupada. Execute .\scripts\stop-dev.ps1 como administrador ou feche o processo que esta usando essa porta."
}

Write-Host "Iniciando backend em http://127.0.0.1:8000 ..."
Start-Process `
    -FilePath $VenvPython `
    -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErr `
    -WindowStyle Hidden

Write-Host "Iniciando frontend em http://127.0.0.1:5173 ..."
Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c cd /d `"$FrontendRun`" && npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort" `
    -WorkingDirectory $FrontendRun `
    -RedirectStandardOutput $FrontendLog `
    -RedirectStandardError $FrontendErr `
    -WindowStyle Hidden

Start-Sleep -Seconds 4

$backendReady = Wait-HttpOk "http://127.0.0.1:8000/health"
$frontendReady = netstat -ano | Select-String ":5173" | Select-String "LISTENING"

if (-not $backendReady) {
    Write-Host ""
    Write-Host "Backend nao iniciou. Veja:"
    Write-Host $BackendErr
    if (Test-Path $BackendErr) {
        Get-Content $BackendErr -Tail 40
    }
    throw "Falha ao iniciar backend."
}

if (-not $frontendReady) {
    Write-Host ""
    Write-Host "Frontend nao iniciou. Veja:"
    Write-Host $FrontendErr
    if (Test-Path $FrontendErr) {
        Get-Content $FrontendErr -Tail 40
    }
    throw "Falha ao iniciar frontend."
}

if (-not $NoOpen) {
    Start-Process "http://127.0.0.1:5173"
}

Write-Host ""
Write-Host "[OK] Projeto iniciado."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host ""
Write-Host "Logs:"
Write-Host "Backend:  $BackendLog"
Write-Host "Frontend: $FrontendLog"
