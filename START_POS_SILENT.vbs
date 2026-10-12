Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' 1. Run migrations silently
WshShell.Run "cmd /c cd /d """ & strPath & "\backend"" && python manage.py migrate --noinput", 0, True

' 2. Start WhatsApp Gateway in background if present
If fso.FileExists(strPath & "\wa_gateway\server.js") Then
    WshShell.Run "cmd /c cd /d """ & strPath & "\wa_gateway"" && node server.js", 0, False
End If

' 3. Start Django POS server in background
WshShell.Run "cmd /c cd /d """ & strPath & "\backend"" && python manage.py runserver 127.0.0.1:8000", 0, False

' 4. Wait 3 seconds then open default browser to the POS counter
WScript.Sleep 3000
WshShell.Run "http://127.0.0.1:8000/"
