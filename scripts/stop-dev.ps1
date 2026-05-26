$ErrorActionPreference = "Continue"

function Stop-Port {
    param([int]$Port)

    $connections = netstat -ano | Select-String ":$Port"
    foreach ($connection in $connections) {
        $parts = ($connection.Line -split "\s+") | Where-Object { $_ }
        if ($parts.Count -ge 5 -and $parts[3] -eq "LISTENING") {
            $pidToStop = [int]$parts[4]
            if ($pidToStop -gt 0) {
                Write-Host "Encerrando porta $Port (PID $pidToStop)..."
                cmd.exe /c "taskkill /PID $pidToStop /T /F >nul 2>nul"
            }
        }
    }
}

Write-Host ""
Write-Host "=== Projeto Integrador 05 - stop ==="
Write-Host ""

Stop-Port 5173
Stop-Port 8000

Start-Sleep -Seconds 2

$stillRunning = @()
if (netstat -ano | Select-String ":5173" | Select-String "LISTENING") {
    $stillRunning += "5173"
}
if (netstat -ano | Select-String ":8000" | Select-String "LISTENING") {
    $stillRunning += "8000"
}

if ($stillRunning.Count -gt 0) {
    Write-Host ""
    Write-Host "Aviso: ainda ha processo escutando na(s) porta(s): $($stillRunning -join ', ')"
    Write-Host "Feche o terminal/processo correspondente ou reinicie o computador se o Windows mantiver a porta presa."
    exit 1
}

Write-Host "[OK] Servicos encerrados."
