@echo off
rem Restart-on-crash supervisor for the ASP reconciler.
rem Runs `node reconcile.mjs` in a loop: if it exits for any reason (crash, killed, etc.),
rem wait 5s and start it again. The reconciler's own single-instance lock (reconciler.pid)
rem prevents two copies running at once even across restarts.
setlocal
cd /d "%~dp0"

:loop
echo [%date% %time%] supervisor: starting reconciler >> logs\supervisor.log
node reconcile.mjs >> logs\supervisor.log 2>&1
echo [%date% %time%] supervisor: reconciler exited with code %errorlevel%, restarting in 5s >> logs\supervisor.log
timeout /t 5 /nobreak >nul
goto loop
