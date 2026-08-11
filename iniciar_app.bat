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

REM --- Auto-atualizar do GitHub (silencioso e a prova de falhas) ---------------
REM Abrir a app passa a trazer sempre a ultima versao: a funcionaria NAO tem de
REM correr o atualizar.bat a mao. GIT_TERMINAL_PROMPT=0 garante que, se o token
REM expirou ou nao ha internet, o git FALHA JA (nao fica preso a pedir password
REM numa consola escondida). Se falhar, abrimos a versao local que ja esta no PC
REM e mostramos um popup (wscript, porque o 'msg' nao existe no Windows Home) para
REM o problema nao passar despercebido.
echo.
echo  A verificar atualizacoes no GitHub...
set GIT_TERMINAL_PROMPT=0
git fetch origin --quiet
if errorlevel 1 goto :sem_update
git reset --hard origin/main --quiet
if errorlevel 1 goto :sem_update
REM Update OK: limpar cache do Python e confirmar dependencias.
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
python -m pip install -q -r requirements.txt
echo  Atualizado.
goto :fim_update
:sem_update
echo  (Sem atualizacao: a abrir a versao atual.)
>"%TEMP%\_cartorio_upd.vbs" echo MsgBox "Nao consegui atualizar a app (pode ser falta de internet ou o acesso ao GitHub ter expirado). Vou abrir a versao que ja esta no PC. Se isto se repetir, avisa o Rui.",48,"Cartorio - atualizacao"
start "" wscript "%TEMP%\_cartorio_upd.vbs"
:fim_update

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
