@echo off
rem Restart-on-crash supervisor for the AI-session watchdog.
rem Runs `node session-watchdog.mjs` in a loop: if it exits for any reason (crash, killed,
rem etc.), wait 5s and start it again. The watchdog's own single-instance lock
rem (logs\watchdog.lock.json) prevents two copies running at once even across restarts.
setlocal
cd /d "%~dp0"

:loop
echo [%date% %time%] supervisor: starting session-watchdog >> logs\watchdog-supervisor.log
node session-watchdog.mjs >> logs\watchdog-supervisor.log 2>&1
echo [%date% %time%] supervisor: session-watchdog exited with code %errorlevel%, restarting in 5s >> logs\watchdog-supervisor.log
timeout /t 5 /nobreak >nul
goto loop
