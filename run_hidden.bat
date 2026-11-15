@echo off
setlocal
cd /d "%~dp0"

:: ===========================================================================
::  JARVIS - hidden background runner (used by start_jarvis_bg.vbs)
:: ---------------------------------------------------------------------------
::  Ye file run.bat wala bilkul same environment set karti hai, lekin apni
::  output khud logs\ me likhti hai - is liye jab ise window style 0 se
::  chalaya jaye to koi CMD window nazar nahi aati.
::
::  Usage (normally called BY start_jarvis_bg.vbs with a hidden window):
::      run_hidden.bat            -> backend  (logs\backend.log)
::      run_hidden.bat tunnel     -> tunnel   (logs\tunnel.log)
:: ===========================================================================

set "MODE=%~1"
set "JARVIS_HOST=0.0.0.0"
set "JARVIS_PORT=8000"
set "ALLOWED_HOSTS=*"

:: ---------------------------------------------------------------------------
::  WARNING: NEVER pass `--forwarded-allow-ips *` as a command-line argument.
::  uvicorn's CLI is built on Click, and Click expands every argument that
::  contains a wildcard on Windows (click/utils.py -> _expand_args -> glob).
::  A bare - or even a quoted - `*` therefore arrives at uvicorn as a listing
::  of this folder, and it dies with:
::      Error: Got unexpected extra arguments (config data extension ...)
::  Quoting does not help: cmd strips the quotes before Click ever sees them.
::  The trust list is set through the environment variable uvicorn reads
::  instead (uvicorn/config.py: FORWARDED_ALLOW_IPS, where "*" = trust all).
:: ---------------------------------------------------------------------------
set "FORWARDED_ALLOW_IPS=*"

set "VENV_PY=%~dp0venv\Scripts\python.exe"
if not exist "%VENV_PY%" exit /b 1
if not exist "%~dp0logs" mkdir "%~dp0logs"

:: Is machine ki Application Control policy SQLAlchemy ki compiled .pyd files
:: ko block karti hai (import par "DLL load failed"). Same fixup as run.bat.
for /r "%~dp0venv\Lib\site-packages\sqlalchemy" %%F in (*.pyd) do ren "%%F" "%%~nxF.disabled" 2>nul

if /i "%MODE%"=="tunnel" goto :run_tunnel

echo [%date% %time%] run_hidden.bat starting uvicorn on %JARVIS_HOST%:%JARVIS_PORT% >> "%~dp0logs\backend.log"
"%VENV_PY%" -m uvicorn main:app --host %JARVIS_HOST% --port %JARVIS_PORT% --proxy-headers >> "%~dp0logs\backend.log" 2>&1
exit /b %ERRORLEVEL%

:run_tunnel
echo [%date% %time%] run_hidden.bat starting tunnel >> "%~dp0logs\tunnel.log"
"%VENV_PY%" "%~dp0tunnel.py" >> "%~dp0logs\tunnel.log" 2>&1
exit /b %ERRORLEVEL%
