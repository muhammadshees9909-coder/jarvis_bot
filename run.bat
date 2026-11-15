@echo off
setlocal
cd /d "%~dp0"

:: Modes:
::   run.bat            -> local machine only (http://127.0.0.1:8000)
::   run.bat lan        -> reachable from phones on the same Wi-Fi network
::   run.bat remote     -> secure public HTTPS tunnel (works from ANY network)
set "MODE=%~1"
set "JARVIS_HOST=127.0.0.1"
set "JARVIS_PORT=8000"
set "JARVIS_PROXY_ARGS="

if /i "%MODE%"=="lan" (
    set "JARVIS_HOST=0.0.0.0"
    set "ALLOWED_HOSTS=*"
)
:: NOTE: `--forwarded-allow-ips *` must NOT be passed on the command line.
:: uvicorn's CLI is built on Click, and Click expands every argument that
:: contains a wildcard on Windows (click/utils.py -> _expand_args -> glob), so
:: `*` turns into a listing of this folder and uvicorn dies with
:: "Got unexpected extra arguments (...)". The trust list therefore goes
:: through the environment variable uvicorn reads (uvicorn/config.py reads
:: FORWARDED_ALLOW_IPS, where "*" means trust everything).
if /i "%MODE%"=="remote" (
    set "JARVIS_HOST=0.0.0.0"
    set "ALLOWED_HOSTS=*"
    set "FORWARDED_ALLOW_IPS=*"
    set "JARVIS_PROXY_ARGS=--proxy-headers"
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [ERROR] venv Python nahi mila:
    echo         %VENV_PY%
    echo.
    echo Pehle ye chalayein:
    echo     python -m venv venv
    echo     venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

title JARVIS Backend - FastAPI (%JARVIS_HOST%:%JARVIS_PORT%)

echo ============================================================
echo   JARVIS Backend  :  http://127.0.0.1:%JARVIS_PORT%
echo   Docs            :  http://127.0.0.1:%JARVIS_PORT%/docs
if /i "%MODE%"=="lan" (
    echo.
    echo   [LAN MODE]  Phone se access karne ke liye:
    echo     1^) Is PC ka IPv4 address dekhein:  ipconfig
    echo        ^(look for "Wireless LAN adapter" -^> IPv4 Address^)
    echo     2^) Phone browser me kholein:  http://^<YOUR-IP^>:%JARVIS_PORT%/
    echo     3^) Windows Firewall me python.exe ko allow karein.
    echo     Note: PC aur phone same Wi-Fi par hone chahiye.
)
if /i "%MODE%"=="remote" (
    echo.
    echo   [REMOTE MODE]  Duniya me kahin se bhi phone par JARVIS:
    echo     - Backend alag window me start hoga ^(minimized^).
    echo     - Cloudflare Tunnel yahin start hoga aur ek secure
    echo       HTTPS URL print karega ^(jaise https://xxxx.trycloudflare.com^).
    echo     - Us URL ko phone browser me kholein - mic aur voice
    echo       HTTPS par hi chalta hai, isliye ye zaroori hai.
)
echo.
echo   Band karne ke liye: is window me Ctrl+C dabayein
echo ============================================================
echo.

:: Is machine ki Application Control policy SQLAlchemy ki compiled .pyd files
:: ko block karti hai (import par "DLL load failed"). Unhe disable kar ke
:: SQLAlchemy pure-Python mode me chalata hai.
for /r "%~dp0venv\Lib\site-packages\sqlalchemy" %%F in (*.pyd) do ren "%%F" "%%~nxF.disabled" 2>nul

:: REMOTE MODE: backend chhup kar (minimized) chalta hai, aur tunnel isi window
:: me chalta hai taaki public HTTPS URL seedha isi console me print ho.
if /i "%MODE%"=="remote" (
    echo [%date% %time%] Backend start ho raha hai ^(minimized window^)...
    start "JARVIS Backend" /min "%VENV_PY%" -m uvicorn main:app --host %JARVIS_HOST% --port %JARVIS_PORT% %JARVIS_PROXY_ARGS%
    echo [%date% %time%] Secure tunnel start ho raha hai...
    echo.
    "%VENV_PY%" tunnel.py
    echo.
    echo Tunnel band ho gaya. Backend window ko band karne ke liye
    echo taskbar par "JARVIS Backend" window close karein.
    pause
    exit /b 0
)

:run
echo [%date% %time%] Server start ho raha hai...
"%VENV_PY%" -m uvicorn main:app --host %JARVIS_HOST% --port %JARVIS_PORT% %JARVIS_PROXY_ARGS%
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" goto :done

echo.
echo [WARN] Server band ho gaya (exit code %EXITCODE%). 5 second me retry...
:: `timeout` stdin redirect hone par fail hota hai, isliye ping se delay lete hain.
ping -n 6 127.0.0.1 >nul
goto :run

:done
echo.
echo Server normally band hua.
pause
