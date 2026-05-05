@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ===================================
echo  Iniciando Projeto Integrador 05
echo ===================================
echo.

REM Verificar backend na porta 8000
echo Verificando backend (porta 8000)...
netstat -ano | findstr ":8000" >nul
if errorlevel 1 (
	echo Backend nao esta rodando. Iniciando...
	start "Backend FastAPI" cmd /k "cd /d "%~dp0" && .venv\Scripts\python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
) else (
	echo [OK] Backend ja esta rodando na porta 8000.
)

REM Verificar frontend na porta 5173
echo.
echo Verificando frontend (porta 5173)...
netstat -ano | findstr ":5173" >nul
if errorlevel 1 (
	echo Frontend nao esta rodando. Iniciando...
	REM Instalar dependencias se necessario
	if not exist "%~dp0frontend\node_modules" (
		echo Instalando dependencias do frontend (npm install)...
		start "Frontend Setup" cmd /k "cd /d "%~dp0frontend" && npm install && npm run dev"
	) else (
		echo Iniciando servidor de desenvolvimento...
		start "Frontend Vite" cmd /k "cd /d "%~dp0frontend" && npm run dev"
	)
) else (
	echo [OK] Frontend ja esta rodando na porta 5173.
)

timeout /t 4 /nobreak >nul
echo.
echo ===================================
echo  Abrindo interface...
echo ===================================
start http://localhost:5173

echo.
echo [OK] Servicos iniciados!
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Nota: PostgreSQL deve estar rodando antes de usar o sistema.
echo Pressione ENTER para fechar esta janela.
pause >nul
