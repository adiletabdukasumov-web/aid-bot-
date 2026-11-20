#!/usr/bin/env bash
# Установка на Linux-сервер (Ubuntu/Debian/Oracle Linux). Запуск: sudo bash deploy/install_linux.sh
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DST=/opt/tg-reply-bot
command -v python3 >/dev/null || { (apt-get update && apt-get install -y python3 python3-venv) || dnf install -y python3; }
python3 -m venv --help >/dev/null 2>&1 || apt-get install -y python3-venv || true
id replybot >/dev/null 2>&1 || useradd -r -m -d "$DST" -s /usr/sbin/nologin replybot
mkdir -p "$DST" && cp -r "$SRC"/. "$DST"/
[ -f "$DST/.env" ] || { echo "Нет $DST/.env — скопируй .env.example в .env и заполни, потом запусти скрипт снова"; exit 1; }
python3 -m venv "$DST/.venv"
"$DST/.venv/bin/pip" install -q -r "$DST/requirements.txt"
chown -R replybot "$DST"
cp "$DST/deploy/replybot.service" /etc/systemd/system/replybot.service
systemctl daemon-reload && systemctl enable --now replybot
echo "Готово. Логи: journalctl -u replybot -f   (или $DST/data/bot.log)"
