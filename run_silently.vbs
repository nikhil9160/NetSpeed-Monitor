' NetSpeed Monitor Silent Launcher
' Runs the application in the background without showing any command prompt window.
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe main.py", 0, False
Set WshShell = Nothing
