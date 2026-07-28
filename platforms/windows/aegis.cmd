@echo off
REM aegis.cmd — Windows cmd launcher.
REM
REM Usage:
REM   aegis                       (reads ~/.aegis/prompt.txt)
REM   aegis "your prompt here"    (inline)
REM   aegis --strategy parallel

setlocal

set DIR=%~dp0
set ROOT=%DIR%..\..

REM Prefer aegis on PATH; fall back to python aegis.py.
where aegis >nul 2>&1
if %ERRORLEVEL% == 0 goto :on_path

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo [!] python not on PATH. Install Python 3.10+ from python.org.
  exit /b 2
)

set PY_SCRIPT=%ROOT%\aegis.py
if not exist "%PY_SCRIPT%" (
  echo [!] aegis.py not found at %PY_SCRIPT%
  echo     Run install.bat first.
  exit /b 2
)

cd /d "%ROOT%"
python "%PY_SCRIPT%" %*
goto :end

:on_path
aegis %*
goto :end

:end
endlocal
