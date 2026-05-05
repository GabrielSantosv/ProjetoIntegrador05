@echo off
setlocal

cd /d "%~dp0"

echo Iniciando backend FastAPI na porta 8000...
netstat -ano | findstr ":8000" >nul
if errorlevel 1 (
	start "Backend FastAPI" cmd /k "cd /d "%~dp0" && .venv\Scripts\python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
) else (
	echo Backend ja esta rodando na porta 8000.
)

echo Iniciando frontend Vite na porta 5173...
netstat -ano | findstr ":5173" >nul
if errorlevel 1 (
	start "Frontend Vite" cmd /k "cd /d "%~dp0frontend" && npm run dev"
) else (
	echo Frontend ja esta rodando na porta 5173.
)

timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo Servicos iniciados.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Se o banco PostgreSQL nao estiver rodando, inicie-o antes de usar o sistema.
echo Pressione qualquer tecla para fechar esta janela.
pause >nul
