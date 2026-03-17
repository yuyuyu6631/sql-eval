@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0run_ai_design_flow_tests.ps1"
exit /b %errorlevel%
