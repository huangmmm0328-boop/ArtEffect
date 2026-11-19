@echo off
setlocal
cd /d "%~dp0"
echo Merged review: http://127.0.0.1:4191/site/#future
echo Keep this window open. No production deployment.
".venv\Scripts\python.exe" manage.py serve --merged --port 4191
pause
