@echo off
REM ============================================================
REM  Cartorio - PARAR a app (fecha o servidor Streamlit).
REM
REM  Fechar o browser NAO para o servidor (o Streamlit fica em
REM  memoria a' espera). Isto nao e' perigoso, mas para fechar
REM  de forma limpa, da' duplo-clique aqui.
REM ============================================================
cd /d "%~dp0"

echo  A parar a app...

REM 1) Matar quem esta' a ouvir na porta 8501 (o servidor) E os filhos (/T).
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8501" ^| findstr LISTENING') do (
    taskkill /F /T /PID %%p >nul 2>nul
)

REM 2) Rede de seguranca: matar qualquer python que esteja mesmo a correr o
REM    Streamlit desta app (filtra pela linha de comando, para NAO tocar noutro
REM    python que a funcionaria tenha aberto).
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'streamlit' -and $_.CommandLine -match 'app.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

echo  Feito. Ja podes fechar esta janela.
timeout /t 2 >nul
