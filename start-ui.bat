@echo off
cd /d "C:\Users\ASUS\Desktop\rag"
"C:\Users\ASUS\Desktop\rag\.venv\Scripts\python.exe" "C:\Users\ASUS\Desktop\rag\tools\launch_ui.py" %*
echo.
echo Launcher exit code: %ERRORLEVEL%
echo Log file: C:\Users\ASUS\Desktop\rag\start-ui.log
pause
