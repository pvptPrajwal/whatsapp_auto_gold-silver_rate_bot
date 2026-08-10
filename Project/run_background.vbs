Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = base & "\.venv\Scripts\pythonw.exe"
appfile = base & "\app.py"
shell.CurrentDirectory = base
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & appfile & Chr(34) & " --no-browser", 0, False
