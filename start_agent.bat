@echo off
set "ROOT=%~dp0"
"%ROOT%.venv\Scripts\python.exe" "%ROOT%agent_cli.py" %*
pause
