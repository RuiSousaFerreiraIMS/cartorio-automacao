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

REM --- Auto-atualizacao: puxar a ultima versao do GitHub ----------------------
REM Assim basta o Rui dar 'git push'; cada PC apanha as alteracoes no proximo
REM arranque, sem ir de PC em PC. NAO bloqueia se nao houver internet nem git;
REM --ff-only evita conflitos (se o repo local divergir, nao atualiza e arranca
REM na mesma). So corre o pip install se a atualizacao mexeu em algo.
where git >nul 2>nul
if errorlevel 1 goto :sem_git
echo A verificar atualizacoes no GitHub...
for /f "delims=" %%i in ('git -C "%~dp0" rev-parse HEAD 2^>nul') do set "REV_ANTES=%%i"
git -C "%~dp0" pull --ff-only
for /f "delims=" %%i in ('git -C "%~dp0" rev-parse HEAD 2^>nul') do set "REV_DEPOIS=%%i"
if not "%REV_ANTES%"=="%REV_DEPOIS%" (
    echo Atualizacao aplicada. A confirmar dependencias...
    python -m pip install -r requirements.txt -q
)
:sem_git

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
