#!/usr/bin/env bash
# Einrichtung auf dem Ghostwriter-Server (als root):
#   bash /opt/ebay-haendlersuche/deploy/install.sh
# Fragt die eBay-Zugangsschlüssel ab (Cert ID unsichtbar) – nichts davon landet im Chat oder Repo.
set -euo pipefail
APP=/opt/ebay-haendlersuche
cd "$APP"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
if [ ! -f .env ]; then
  read -rp "eBay App ID (Client ID): " ID
  read -rsp "eBay Cert ID (Client Secret, Eingabe unsichtbar): " SECRET; echo
  { echo "EBAY_CLIENT_ID=$ID"; echo "EBAY_CLIENT_SECRET=$SECRET"; grep -v '^EBAY_\|^#' .env.example; } > .env
  chmod 600 .env
fi
mkdir -p data
echo "Fertig. Test: cd $APP && .venv/bin/python -m haendler.cli probe"
