@echo off
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q KV_HMI_V2.spec 2>nul

pyinstaller kv_hmi.spec

echo.
echo Build complete.
echo Check dist\KV_HMI_V2\
pause