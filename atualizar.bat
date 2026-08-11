@echo off
REM ============================================================
REM  Cartorio - ATUALIZAR a app para a ultima versao.
REM  Duplo-clique num PC das funcionarias para apanhar as
REM  ultimas correcoes do GitHub.
REM
REM  Usa fetch + reset --hard (nao git pull): poe o codigo
REM  EXATAMENTE igual ao GitHub, mesmo que o repositorio local
REM  esteja num estado estranho. NAO mexe no trabalho delas: o
REM  campos.json, os logs e o .venv estao fora do git.
REM ============================================================
cd /d "%~dp0"

REM Parar a app se estiver a correr (senao continua com o codigo antigo em
REM memoria e o erro volta ate se matar o processo). Liberta a porta 8501.
echo  A parar a app (se estiver aberta)...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8501" ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>nul
)

echo.
echo ============================================================
echo  A atualizar a app...
echo ============================================================
git fetch origin
if errorlevel 1 goto :erro
git reset --hard origin/main
if errorlevel 1 goto :erro

echo.
echo  A limpar cache do Python...
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo.
echo  A confirmar dependencias (pode demorar uns segundos)...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python -m pip install -q -r requirements.txt
)

echo.
echo ============================================================
echo  ATUALIZACAO CONCLUIDA. Ja podes abrir a app normalmente.
echo ============================================================
pause
exit /b 0

:erro
echo.
echo ============================================================
echo  FALHOU a ligacao ao GitHub. Causas comuns:
echo   - Sem internet.
echo   - Pediu utilizador/password (o token pode ter expirado):
echo     nesse caso avisa o Rui.
echo ============================================================
pause
exit /b 1
