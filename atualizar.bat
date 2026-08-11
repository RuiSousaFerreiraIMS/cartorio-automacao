@echo off
REM ============================================================
REM  Cartorio - ATUALIZAR a app para a ultima versao.
REM  Duplo-clique num PC das funcionarias para apanhar as
REM  ultimas correcoes do GitHub. Nao mexe em nada do trabalho
REM  delas (o campos.json e os logs ficam de fora do git).
REM ============================================================
cd /d "%~dp0"

echo.
echo ============================================================
echo  A atualizar a app (git pull)...
echo ============================================================
git pull
if errorlevel 1 goto :erro

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
echo  O git pull FALHOU. Causas comuns:
echo   - Sem internet.
echo   - Pediu utilizador/password do GitHub (o token pode ter
REM     expirado): nesse caso avisa o Rui.
echo ============================================================
pause
exit /b 1
