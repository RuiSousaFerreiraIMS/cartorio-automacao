' ============================================================
'  Cartorio - Automacao de Escrituras
'  Launcher silencioso (sem consola). Duplo-clique para arrancar.
'  Se algo correr mal (nao abre browser), abrir iniciar_app.bat
'  em vez deste para ver o erro na consola.
' ============================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Pasta onde este VBS esta
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' Correr o .bat com janela escondida (0) e nao esperar (False)
WshShell.Run """" & strPath & "\iniciar_app.bat""", 0, False
