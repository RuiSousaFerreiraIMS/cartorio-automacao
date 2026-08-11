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

REM --- Parar QUALQUER servidor da app que tenha ficado a correr escondido -------
REM Fechar o browser NAO para o Streamlit (o cartorio.vbs abre-o sem consola), e
REM esse servidor fica com o codigo ANTIGO em memoria. Depois de um 'git pull' a
REM app continuava a servir o velho ate se matar o processo. Aqui, antes de abrir,
REM libertamos a porta 8501 (mata o servidor antigo) para arrancar sempre limpo.
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8501" ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>nul
)

REM --- Streamlit: saltar o prompt de email do 1o arranque ----------------------
REM Sem este ficheiro, o Streamlit pergunta um email na consola no primeiro
REM arranque e FICA PRESO a espera (a consola esta escondida pelo cartorio.vbs,
REM logo a app nunca abria). Criar um credentials.toml vazio salta o prompt.
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

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
