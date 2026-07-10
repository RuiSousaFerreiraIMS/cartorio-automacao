' ============================================================
'  Cartorio - Automacao de Escrituras
'  Launcher ELEVADO (como Administrador) e sem consola.
'
'  PORQUE ELEVADO: o SIMN corre como Administrador. O Windows (UIPI) impede um
'  programa normal de enviar teclas/rato a uma janela elevada, por isso o robo
'  nao conseguia preencher o SIMN quando a app era aberta pelo atalho normal.
'  Correr a app elevada (mesmo nivel do SIMN) resolve.
'
'  Ao abrir aparece UMA vez a confirmacao do Windows (UAC): carregar "Sim".
'  Se algo correr mal, abrir iniciar_app.bat (botao direito > Executar como
'  administrador) para ver o erro na consola.
' ============================================================

Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
strBat = strPath & "\iniciar_app.bat"

' ShellExecute(ficheiro, argumentos, pasta, verbo, janela)
'   verbo "runas" = pedir elevacao (UAC)
'   0 = janela escondida (sem consola visivel)
CreateObject("Shell.Application").ShellExecute strBat, "", strPath, "runas", 0
