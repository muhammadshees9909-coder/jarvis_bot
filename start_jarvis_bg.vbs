' ===========================================================================
'  JARVIS Forexcast Intelligence - silent background launcher + watchdog
' ---------------------------------------------------------------------------
'  Starts the FastAPI backend and the secure Cloudflare / ngrok tunnel with NO
'  visible window (window style 0) and writes their output into logs\ instead
'  of opening black CMD windows.
'
'  The script stays resident and acts as a watchdog: if the backend stops
'  answering /health, or the tunnel process dies, it is restarted by itself.
'
'  Usage:
'    - Double-click this file, or
'    - run install_startup.bat once so it starts with Windows automatically.
'  Everything is logged to  logs\launcher.log  logs\backend.log  logs\tunnel.log
' ===========================================================================
Option Explicit

Const HEALTH_URL      = "http://127.0.0.1:8000/health"
Const BACKEND_PORT    = 8000
Const TICK_MS         = 15000     ' how often the watchdog checks both services
Const MIN_RESTART_MS  = 30000     ' never restart the same service faster than this
Const MAX_LOG_BYTES   = 2097152   ' rotate a log file once it grows past 2 MB

Dim shell, fso, baseDir, pythonExe, logsDir
Dim backendLog, tunnelLog, launcherLog
Dim lastBackendStart, lastTunnelStart
Dim nowMs

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = baseDir

pythonExe = baseDir & "\venv\Scripts\python.exe"
logsDir = baseDir & "\logs"
backendLog = logsDir & "\backend.log"
tunnelLog = logsDir & "\tunnel.log"
launcherLog = logsDir & "\launcher.log"

' --- only one watchdog at a time -------------------------------------------
If AnotherWatcherRunning() Then
    WScript.Quit 0
End If

If Not fso.FolderExists(logsDir) Then
    fso.CreateFolder(logsDir)
End If

If Not fso.FileExists(pythonExe) Then
    WriteLog "venv python not found: " & pythonExe
    WScript.Quit 1
End If

If Not fso.FileExists(baseDir & "\run_hidden.bat") Then
    WriteLog "run_hidden.bat not found in " & baseDir
    WScript.Quit 1
End If

' This machine's Application Control policy blocks SQLAlchemy's compiled .pyd
' files, so keep them renamed exactly like run.bat does (idempotent no-op once
' they are already disabled).
DisableCompiledSqlAlchemy baseDir & "\venv\Lib\site-packages\sqlalchemy"

WriteLog "Launcher started - backend port " & BACKEND_PORT

' Start from a clean slate. An earlier launcher can leave a wedged cloudflared
' behind: logs\tunnel.log shows it looping on "Unauthorized: Tunnel not found"
' forever while the process itself keeps running, and because tunnel.py was
' still alive the watchdog below never replaced it. Both the quick tunnel and
' its runner are removed here, so the tunnel started on the first tick is a
' single, freshly registered one.
ResetTunnelProcesses

lastBackendStart = 0
lastTunnelStart = 0

' --- watchdog loop ---------------------------------------------------------
Do
    nowMs = Milliseconds()

    If Not BackendAlive() Then
        If nowMs - lastBackendStart > MIN_RESTART_MS Then
            WriteLog "Backend is not answering " & HEALTH_URL & " - starting it"
            StartBackend
            lastBackendStart = nowMs
        End If
    End If

    If Not TunnelAlive() Then
        If nowMs - lastTunnelStart > MIN_RESTART_MS Then
            WriteLog "Tunnel process is not running - starting it"
            StartTunnel
            lastTunnelStart = nowMs
        End If
    End If

    WScript.Sleep TICK_MS
Loop

' ===========================================================================
'  Service control
' ===========================================================================
Sub StartBackend()
    Dim command
    RotateLog backendLog
    ' run_hidden.bat sets exactly the environment run.bat does (host, port,
    ' ALLOWED_HOSTS, FORWARDED_ALLOW_IPS, SQLAlchemy .pyd fixup) and writes its
    ' own output to logs\backend.log. `cmd /c call` is used on purpose: if the
    ' command started with a quote, cmd would strip the first and last quote
    ' and mangle the whole line. Window style 0 = completely hidden.
    command = "cmd /c call """ & baseDir & "\run_hidden.bat"" backend"
    shell.Run command, 0, False
End Sub

Sub StartTunnel()
    Dim command
    RotateLog tunnelLog
    command = "cmd /c call """ & baseDir & "\run_hidden.bat"" tunnel"
    shell.Run command, 0, False
End Sub

' Kills leftover quick-tunnel processes: the python runner (tunnel.py) and the
' cloudflared process it owns. Only quick tunnels are touched - a cloudflared
' command line without "--url" belongs to a named tunnel / service and is left
' alone. Best effort: if WMI is unavailable we simply continue.
Sub ResetTunnelProcesses()
    Dim wmi, procs, item, killed
    killed = 0
    On Error Resume Next
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    If Err.Number = 0 Then
        Set procs = wmi.ExecQuery("SELECT CommandLine FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe' OR Name='cloudflared.exe'")
        If Err.Number = 0 Then
            For Each item In procs
                If Not IsNull(item.CommandLine) Then
                    If InStr(LCase(item.CommandLine), "tunnel.py") > 0 Then
                        item.Terminate()
                        killed = killed + 1
                    ElseIf InStr(LCase(item.CommandLine), "cloudflared") > 0 And InStr(LCase(item.CommandLine), "--url") > 0 Then
                        item.Terminate()
                        killed = killed + 1
                    End If
                End If
            Next
        End If
    End If
    Err.Clear
    On Error GoTo 0
    If killed > 0 Then WriteLog "Cleaned up " & killed & " stale tunnel process(es)"
End Sub

' ===========================================================================
'  Health checks
' ===========================================================================
Function BackendAlive()
    Dim http
    BackendAlive = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    If Err.Number <> 0 Then
        Err.Clear
        Set http = CreateObject("MSXML2.XMLHTTP")
    End If
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    http.setTimeouts 2500, 2500, 2500, 2500
    http.open "GET", HEALTH_URL, False
    http.send
    If Err.Number = 0 Then
        If http.status = 200 Then BackendAlive = True
    End If
    Err.Clear
    On Error GoTo 0
End Function

Function TunnelAlive()
    Dim wmi, procs, item
    TunnelAlive = False
    On Error Resume Next
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set procs = wmi.ExecQuery("SELECT CommandLine FROM Win32_Process WHERE Name='python.exe'")
    If Err.Number <> 0 Then
        ' Cannot inspect processes: assume it is running so we never spawn a
        ' second tunnel by accident.
        Err.Clear
        On Error GoTo 0
        TunnelAlive = True
        Exit Function
    End If
    For Each item In procs
        If Not IsNull(item.CommandLine) Then
            If InStr(LCase(item.CommandLine), "tunnel.py") > 0 Then TunnelAlive = True
        End If
    Next
    On Error GoTo 0
End Function

Function AnotherWatcherRunning()
    Dim wmi, procs, item, count
    AnotherWatcherRunning = False
    count = 0
    On Error Resume Next
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set procs = wmi.ExecQuery("SELECT CommandLine FROM Win32_Process WHERE Name='wscript.exe' OR Name='cscript.exe'")
    If Err.Number <> 0 Then
        Err.Clear
        On Error GoTo 0
        Exit Function
    End If
    For Each item In procs
        If Not IsNull(item.CommandLine) Then
            If InStr(LCase(item.CommandLine), "start_jarvis_bg.vbs") > 0 Then count = count + 1
        End If
    Next
    On Error GoTo 0
    If count > 1 Then AnotherWatcherRunning = True
End Function

' ===========================================================================
'  Logging
' ===========================================================================
Function Milliseconds()
    Milliseconds = DateDiff("s", #1/1/2000#, Now()) * 1000
End Function

Sub WriteLog(message)
    Dim stream
    On Error Resume Next
    RotateLog launcherLog
    Set stream = fso.OpenTextFile(launcherLog, 8, True)
    stream.WriteLine "[" & FormatDateTime(Now(), 0) & "] " & message
    stream.Close
    On Error GoTo 0
End Sub

' Keeps the log folder from growing forever. Called right before a service is
' (re)started, because a running process still holds its own log file open.
Sub RotateLog(path)
    On Error Resume Next
    If fso.FileExists(path) Then
        If fso.GetFile(path).Size > MAX_LOG_BYTES Then
            If fso.FileExists(path & ".old") Then fso.DeleteFile path & ".old", True
            fso.MoveFile path, path & ".old"
        End If
    End If
    On Error GoTo 0
End Sub

' ===========================================================================
'  SQLAlchemy compiled-extension workaround (mirrors run.bat)
' ===========================================================================
Sub DisableCompiledSqlAlchemy(folderPath)
    Dim pending, key, file
    Set pending = CreateObject("Scripting.Dictionary")
    CollectPydFiles folderPath, pending
    For Each key In pending.Keys
        On Error Resume Next
        Set file = fso.GetFile(key)
        file.Name = fso.GetFileName(key) & ".disabled"
        On Error GoTo 0
    Next
End Sub

Sub CollectPydFiles(folderPath, pending)
    Dim folder, file, subFolder
    If Not fso.FolderExists(folderPath) Then Exit Sub
    On Error Resume Next
    Set folder = fso.GetFolder(folderPath)
    For Each file In folder.Files
        If LCase(fso.GetExtensionName(file.Name)) = "pyd" Then pending(file.Path) = 0
    Next
    For Each subFolder In folder.SubFolders
        CollectPydFiles subFolder.Path, pending
    Next
    On Error GoTo 0
End Sub
