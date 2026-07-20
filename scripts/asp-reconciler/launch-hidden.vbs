' Launches run-supervised.bat with no visible console window.
' Mirrors the pattern okx-a2a's own autostart uses (launch-okx-a2a-daemon.vbs).
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = scriptDir
objShell.Run """" & scriptDir & "\run-supervised.bat""", 0, False
