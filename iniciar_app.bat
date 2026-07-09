@echo off
REM ============================================================
REM  Cartorio - Automacao de Escrituras
REM  Duplo-clique para arrancar a app da funcionaria.
REM  Fechar esta janela para parar tudo.
REM ============================================================

cd /d "%~dp0"

REM Verificar venv
if not exist ".venv\Scripts\activate.bat" goto :sem_venv

REM Verificar chave da API - pelo menos uma tem de existir (Groq, Google ou Anthropic).
REM 'if defined' NAO expande o valor, logo e imune a newlines/caracteres estranhos
REM na chave (que com o "%VAR%"=="" partiam a linha e davam "syntax incorrect").
if defined GROQ_API_KEY goto :tem_chave
if defined GOOGLE_API_KEY goto :tem_chave
if defined ANTHROPIC_API_KEY goto :tem_chave
goto :sem_chave
:tem_chave

REM Ambiente pronto, arrancar
call .venv\Scripts\activate.bat
cd peca_a_extracao

echo.
echo ============================================================
echo  A abrir a app no browser em http://localhost:8501
echo  Para parar: fecha esta janela ou Ctrl+C.
echo ============================================================
echo.

python -m streamlit run app.py
goto :fim


:sem_venv
echo.
echo ERRO: Ambiente Python nao encontrado.
echo Corre o setup de deploy primeiro. Ver DEPLOY.md
echo.
pause
exit /b 1


:sem_chave
echo.
echo ERRO: Chave da API nao configurada.
echo Setar no PowerShell como User env var:
echo   [System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'gsk_...', 'User'^)
echo Depois fecha esta janela e a que setaste, abre uma nova, e volta a correr.
echo.
pause
exit /b 1


:fim
pause
