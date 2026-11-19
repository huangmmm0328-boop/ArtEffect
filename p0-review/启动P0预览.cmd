@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Please follow README.md first.
  pause
  exit /b 1
)
echo P0 preview: http://127.0.0.1:4190/
echo Keep this window open. Close it to stop the preview.
".venv\Scripts\python.exe" manage.py serve --port 4190
pause
