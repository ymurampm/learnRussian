@echo off
chcp 65001 >nul
title Tanya Russian Trainer - 毎日の定期バッチ処理 (01:00 AM)

cd /d "%~dp0"

echo ========================================================
echo   Tanya Russian Trainer - 毎日の定期バッチ処理 [01:00 AM]
echo ========================================================
echo 実行開始時刻: %date% %time%
echo.

if not exist logs mkdir logs

echo [1/3] Pythonバッチ処理を実行中...
python scripts\daily_batch.py >> logs\daily_batch.log 2>&1
set BATCH_EXIT=%errorlevel%

if %BATCH_EXIT% equ 0 (
    echo [2/3] バッチ処理が正常に完了しました。[Exit Code: 0]
) else (
    echo [2/3] [警告] バッチ処理でエラーが発生しました。[Exit Code: %BATCH_EXIT%]
)

echo [3/3] 実行ログ (最新抜粋):
echo --------------------------------------------------------
powershell -Command "if (Test-Path logs\daily_batch.log) { Get-Content -Tail 10 logs\daily_batch.log }" 2>nul
echo --------------------------------------------------------
echo.
echo 実行完了時刻: %date% %time%
exit /b %BATCH_EXIT%
