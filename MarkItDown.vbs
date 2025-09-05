' This script activates a Conda environment and runs a Python script without a visible command window.
' Optimized for faster startup

Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this VBScript is located.
appDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' --- User Configuration ---
' NOTE: Please ensure these paths are correct for your system.
condaPath = "C:\Users\chenw\miniconda3"
condaEnvName = "markitdown"
entryScript = "MarkURLdown.pyw"
' --------------------------

' Use chr(34) to represent the double-quote character (") for clarity.
q = chr(34)

' Optimized command: Use direct python path instead of activation
pythonPath = q & condaPath & "\envs\" & condaEnvName & "\pythonw.exe" & q
cdCmd = "cd /D " & q & appDir & q
pythonCmd = pythonPath & " " & q & entryScript & q

' Simplified command without conda activation overhead
fullCommand = cdCmd & " & " & pythonCmd

' Create the final command to be executed by cmd.exe, wrapped in quotes.
cmdToRun = "cmd.exe /C " & q & fullCommand & q

' Run the command: 
' 0 = The window is hidden.
' True = The script waits for the command to finish.
WshShell.Run cmdToRun, 0, True

'