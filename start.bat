@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Telegram-бот ответов

if not exist .env (
  echo Нет файла .env. Скопируй .env.example в .env и впиши BOT_TOKEN, OWNER_ID, OPENAI_API_KEY.
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Первый запуск: ставлю окружение Python...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo Не нашёл Python. Установи Python 3.12 с python.org, при установке отметь "Add python.exe to PATH".
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt

:loop
echo [%date% %time%] Запускаю бота...
.venv\Scripts\python.exe bot.py
echo [%date% %time%] Бот остановился. Перезапуск через 15 секунд (закрой окно, чтобы остановить)...
timeout /t 15 /nobreak >nul
goto loop
