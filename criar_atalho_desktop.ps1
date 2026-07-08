# Cria um atalho no Desktop do utilizador actual que aponta para cartorio.vbs.
# Correr UMA VEZ apos o setup inicial. Ideal para criar atalho para as funcionarias.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File criar_atalho_desktop.ps1

$repoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbsPath = Join-Path $repoPath "cartorio.vbs"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$atalhoPath = Join-Path $desktopPath "Cartorio Escrituras.lnk"

$shell = New-Object -ComObject WScript.Shell
$atalho = $shell.CreateShortcut($atalhoPath)
$atalho.TargetPath = "wscript.exe"
$atalho.Arguments = """$vbsPath"""
$atalho.WorkingDirectory = $repoPath
$atalho.Description = "Cartorio - Automatizacao de Escrituras"
$atalho.WindowStyle = 1
# Icone: usar o icone do Streamlit (opcional). Comentar se der problemas.
# $atalho.IconLocation = Join-Path $repoPath ".venv\Scripts\python.exe, 0"
$atalho.Save()

Write-Host ""
Write-Host "Atalho criado em:" -ForegroundColor Green
Write-Host "  $atalhoPath"
Write-Host ""
Write-Host "Duplo-clique para arrancar a app sem consola." -ForegroundColor Cyan
Write-Host ""
