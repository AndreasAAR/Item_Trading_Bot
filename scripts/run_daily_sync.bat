@echo off
cd /d "%~dp0\.."

echo ============================================================ >> data\sync_cron.log
echo [DAILY SYNC STARTED] %DATE% %TIME% >> data\sync_cron.log
echo ============================================================ >> data\sync_cron.log

python -u -m src.cli sync --target all --headless >> data\sync_cron.log 2>&1

echo [DAILY SYNC COMPLETED] %DATE% %TIME% >> data\sync_cron.log
echo. >> data\sync_cron.log
