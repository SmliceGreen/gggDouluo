@echo off
chcp 65001 >nul
pushd "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  python -X utf8 "%~dp0publish.py" %*
) else (
  py -3 -X utf8 "%~dp0publish.py" %*
)
set "publish_result=%errorlevel%"
echo.
pause
popd
exit /b %publish_result%
