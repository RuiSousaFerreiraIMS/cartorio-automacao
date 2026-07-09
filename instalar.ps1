# ============================================================================
#  Cartorio - Automacao de Escrituras :: INSTALADOR
#
#  Instala tudo num PC novo das funcionarias, com LOGS de cada passo e um
#  VERIFICADOR automatico no fim que tem de passar. Correr UMA vez por PC.
#
#  Como correr (botao direito no ficheiro > "Executar com o PowerShell", OU):
#     powershell -ExecutionPolicy Bypass -File instalar.ps1
#
#  O que faz:
#    1. Confirma o Python
#    2. Cria o ambiente Python isolado (.venv) e instala as dependencias
#    3. Confirma o LibreOffice (para ler os .doc antigos)
#    4. Pede/guarda a chave da API (Claude) se ainda nao estiver posta
#    5. Corre o verificador (verificar_instalacao.py)
#    6. Cria o atalho no ambiente de trabalho
#  Tudo o que aparece no ecra fica tambem gravado num ficheiro de log.
# ============================================================================

$ErrorActionPreference = "Continue"
$raiz = $PSScriptRoot
Set-Location $raiz

# --- Log: escreve no ecra E num ficheiro com data/hora -----------------------
$pastaLogs = Join-Path $raiz "logs"
if (-not (Test-Path $pastaLogs)) { New-Item -ItemType Directory -Path $pastaLogs | Out-Null }
$logFile = Join-Path $pastaLogs ("instalacao_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

function Log {
    param([string]$Msg, [string]$Nivel = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    $linha = "[$ts] [$Nivel] $Msg"
    $cor = switch ($Nivel) {
        "OK"    { "Green" }
        "ERRO"  { "Red" }
        "AVISO" { "Yellow" }
        "PASSO" { "Cyan" }
        default { "Gray" }
    }
    Write-Host $linha -ForegroundColor $cor
    Add-Content -Path $logFile -Value $linha -Encoding utf8
}

$problemas = 0

Log "============================================================" "PASSO"
Log " INSTALADOR - Cartorio Automacao de Escrituras" "PASSO"
Log " Log deste run: $logFile" "PASSO"
Log "============================================================" "PASSO"

# --- 1. Python ---------------------------------------------------------------
Log "1/6  A confirmar o Python..." "PASSO"
$pyVersao = $null
try { $pyVersao = (& python --version) 2>&1 } catch { $pyVersao = $null }
if ($LASTEXITCODE -ne 0 -or -not $pyVersao) {
    Log "Python nao encontrado no PATH. Instala de https://www.python.org/downloads/ e marca 'Add Python to PATH'." "ERRO"
    Log "Sem Python nao da para continuar. A parar." "ERRO"
    Read-Host "Enter para fechar"
    exit 1
}
Log "Python OK: $pyVersao" "OK"

# --- 2. Ambiente Python (.venv) + dependencias -------------------------------
Log "2/6  A preparar o ambiente Python (.venv)..." "PASSO"
$venvPy = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Log "A criar .venv (pode demorar 1 min)..." "INFO"
    & python -m venv .venv 2>&1 | ForEach-Object { Log $_ "INFO" }
    if (-not (Test-Path $venvPy)) {
        Log "Falhou a criacao do .venv. A parar." "ERRO"
        Read-Host "Enter para fechar"
        exit 1
    }
    Log ".venv criado." "OK"
} else {
    Log ".venv ja existia, a reutilizar." "OK"
}

Log "A instalar dependencias (pip install -r requirements.txt)... isto pode demorar alguns minutos." "INFO"
& $venvPy -m pip install --upgrade pip 2>&1 | ForEach-Object { Log $_ "INFO" }
& $venvPy -m pip install -r requirements.txt 2>&1 | ForEach-Object { Log $_ "INFO" }
if ($LASTEXITCODE -eq 0) {
    Log "Dependencias instaladas." "OK"
} else {
    Log "pip terminou com erro (codigo $LASTEXITCODE). Ver o log acima. O verificador no fim vai dizer o que falta." "AVISO"
    $problemas++
}

# --- 3. LibreOffice (leitor de .doc antigo) ----------------------------------
Log "3/6  A confirmar o leitor de .doc antigo (LibreOffice)..." "PASSO"
$soffice = @(
    "C:\Program Files\LibreOffice\program\soffice.exe",
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($soffice) {
    Log "LibreOffice OK: $soffice" "OK"
} else {
    Log "LibreOffice NAO encontrado. As escrituras .doc antigas nao vao abrir." "AVISO"
    Log "  Instala aqui (gratis): https://pt.libreoffice.org/descarregar/" "AVISO"
    Log "  Depois de instalar, corre este instalador outra vez (ou so o verificar_instalacao.py)." "AVISO"
    $problemas++
}

# --- 4. Chave da API (Claude) ------------------------------------------------
Log "4/6  A confirmar a chave da API (Claude)..." "PASSO"
if (-not $env:LLM_PROVIDER) {
    [System.Environment]::SetEnvironmentVariable("LLM_PROVIDER", "claude", "User")
    $env:LLM_PROVIDER = "claude"
    Log "LLM_PROVIDER posto a 'claude'." "OK"
} else {
    Log "LLM_PROVIDER ja definido: $env:LLM_PROVIDER" "OK"
}
if (-not $env:ANTHROPIC_API_KEY) {
    Log "Nao ha chave ANTHROPIC_API_KEY neste PC." "AVISO"
    $chave = Read-Host "   Cola aqui a chave da API do Claude (comeca por sk-ant-...) e Enter (vazio p/ saltar)"
    $chave = $chave.Trim()
    if ($chave) {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $chave, "User")
        $env:ANTHROPIC_API_KEY = $chave
        Log "Chave guardada (variavel de utilizador ANTHROPIC_API_KEY)." "OK"
    } else {
        Log "Chave nao definida. Poe-la depois e corre o verificador outra vez." "AVISO"
        $problemas++
    }
} else {
    Log "ANTHROPIC_API_KEY ja definida neste PC." "OK"
}

# --- 5. Verificador automatico ----------------------------------------------
Log "5/6  A correr o verificador automatico (testes que tem de passar)..." "PASSO"
& $venvPy verificar_instalacao.py 2>&1 | ForEach-Object { Log $_ "INFO" }
$codVerif = $LASTEXITCODE
if ($codVerif -eq 0) {
    Log "Verificador: TUDO OK." "OK"
} else {
    Log "Verificador encontrou problemas (ver [FALHA] em cima). Corrige e volta a correr." "AVISO"
    $problemas++
}

# --- 6. Atalho no ambiente de trabalho ---------------------------------------
Log "6/6  A criar o atalho no ambiente de trabalho..." "PASSO"
try {
    $vbs = Join-Path $raiz "cartorio.vbs"
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = Join-Path $desktop "Cartorio Escrituras.lnk"
    $sh = New-Object -ComObject WScript.Shell
    $atalho = $sh.CreateShortcut($lnk)
    $atalho.TargetPath = "wscript.exe"
    $atalho.Arguments = """$vbs"""
    $atalho.WorkingDirectory = $raiz
    $atalho.Description = "Cartorio - Automatizacao de Escrituras"
    $atalho.Save()
    Log "Atalho criado: $lnk" "OK"
} catch {
    Log "Nao consegui criar o atalho: $_" "AVISO"
    $problemas++
}

# --- Resumo final ------------------------------------------------------------
Log "============================================================" "PASSO"
if ($problemas -eq 0 -and $codVerif -eq 0) {
    Log " INSTALACAO CONCLUIDA. Esta tudo OK neste PC." "OK"
    Log " Duplo-clique no atalho 'Cartorio Escrituras' no ambiente de trabalho." "OK"
} else {
    Log " INSTALACAO TERMINOU COM $problemas ponto(s) a resolver (ver [AVISO]/[FALHA] em cima)." "AVISO"
    Log " Resolve-os e corre outra vez:  powershell -ExecutionPolicy Bypass -File instalar.ps1" "AVISO"
}
Log " Log completo guardado em: $logFile" "PASSO"
Log "============================================================" "PASSO"

Read-Host "Enter para fechar"
