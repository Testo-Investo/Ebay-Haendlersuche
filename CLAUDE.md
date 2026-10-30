# eBay-Händlersuche – Projekt für Marc Knieb (Neobution)

Ziel: Neukunden finden. Je Produktgruppe aus dem Warenbestand die 20 größten gewerblichen
Händler auf ebay.de, als Excel mit **Produktgruppe, Name, Vorname, Firma, Adresse,
E-Mail-Adresse, Telefonnummer** (Marcs Vorgabe, 30.10.2026).

## Entscheidungen

- Läuft auf dem Ghostwriter-Server (Hetzner, 2.31.88.120) unter `/opt/ebay-haendlersuche`,
  nutzt dessen Warenbestand-CSV und Mailinglisten (bestehende Kontakte rausfiltern) und
  das IONOS-Postfach für den Versand der Liste an Marc (`--mail`).
- **Nur offizielle eBay Browse API**, kein Scraping (eBay-AGB). Zugang: Marcs eBay-
  Entwicklerkonto, App ID/Cert ID nur in `/opt/ebay-haendlersuche/.env` (chmod 600).
- Produktgruppen bildet Claude selbst: Marke + Kategorie (`haendler/gruppen.py`),
  sortiert nach Bestandswert. Microsoft Surface nie (wie im Ghostwriter).
  Gruppen, die Marc nicht will, stehen in `config/ausgeschlossen.txt` (seit 30.10.: MAMIBOT).
- Impressum-Felder (`seller.sellerLegalInfo`) stammen aus Claudes Wissen über die API,
  die Doku war aus der Cloud nicht erreichbar → beim ersten Lauf mit `probe` prüfen.
- Marc entscheidet selbst, wie er die Händler anspricht. Claude hat auf § 7 UWG
  hingewiesen (keine Werbe-Mails ohne Einwilligung; Telefon zuerst).
- Kundendaten (Excel-Listen in `data/`) nie committen.

## Struktur

- `haendler/gruppen.py` – Warenbestand lesen, Produktgruppen bilden
- `haendler/ebay.py` – Browse-API-Client (OAuth Client Credentials, EBAY_DE), Impressum auslesen
- `haendler/suche.py` – Händler je Gruppe sammeln, sortieren, bestehende Kontakte filtern
- `haendler/excel.py` – Excel mit Blatt „Händler“ und „Details“
- `haendler/cli.py` – `gruppen`, `probe`, `suche [N] [--mail]`
- `deploy/install.sh` – Einrichtung auf dem Server
