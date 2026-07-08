@echo off
REM ============================================================
REM  Cartorio - Automacao de Escrituras
REM  Duplo-clique para arrancar a app da funcionaria.
REM  Fechar esta janela para parar tudo.
REM ============================================================

cd /d "%~dp0"

REM Verificar venv
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo ERRO: Ambiente Python nao encontrado.
    echo Corre o setup de deploy primeiro (ver DEPLOY.md).
    echo.
    pause
    exit /b 1
)

REM Verificar chave da API
if "%GROQ_API_KEY%"=="" (
    if "%GOOGLE_API_KEY%"=="" (
        echo.
        echo ERRO: Chave da API nao configurada.
        echo Corre no PowerShell UMA VEZ ^(como Utilizador^):
        echo.
        echo   [System.Environment]::SetEnvironmentVariable("GROQ_API_KEY", "gsk_...", "User"^)
        echo.
        echo Depois fecha e reabre esta janela.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
cd peca_a_extracao

echo.
echo ============================================================
echo  A abrir a app no browser em http://localhost:8501
echo  Para parar, fecha esta janela ou carrega Ctrl+C.
echo ============================================================
echo.

python -m streamlit run app.py

pause
