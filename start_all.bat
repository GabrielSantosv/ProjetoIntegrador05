@echo off
setlocal

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1"

echo.
echo Pressione ENTER para fechar esta janela.
pause >nul
