# eBay-Händlersuche

Findet auf **ebay.de** je Produktgruppe aus dem Neobution-Warenbestand die **20 größten
gewerblichen Händler** und schreibt sie in eine Excel-Liste – als Grundlage für die
Neukunden-Akquise.

- Quelle der Produktgruppen: Warenbestand des Ghostwriters (`/opt/ghostwriter/data/warenbestand.csv`),
  eingeteilt nach Marke + Kategorie, größte Gruppe (Bestandswert) zuerst.
- eBay-Zugriff nur über die **offizielle Browse API** (kein Auslesen der Webseite).
- „Größter Händler“ = meiste passende Angebote in der Gruppe, dann meiste Bewertungen.
- Kontaktdaten aus dem Pflicht-Impressum gewerblicher Händler.
- Bestehende Kontakte aus den Ghostwriter-Mailinglisten und Neobution selbst fallen raus.

## Excel

Blatt **Händler**: Produktgruppe · Name · Vorname · Firma · Adresse · E-Mail-Adresse · Telefonnummer
Blatt **Details**: Rang, eBay-Verkäufer, Bewertungen, Positiv-%, passende Angebote, Beispiel-Link

## Befehle (auf dem Server, in `/opt/ebay-haendlersuche`)

    .venv/bin/python -m haendler.cli gruppen        # Produktgruppen ansehen
    .venv/bin/python -m haendler.cli probe          # eBay-Zugang und Impressum-Felder prüfen
    .venv/bin/python -m haendler.cli suche 25 --mail  # 25 Gruppen, Liste per Mail an Marc

## Rechtlicher Hinweis

Werbe-E-Mails ohne vorherige Einwilligung sind auch an Firmen unzulässig (§ 7 UWG).
Die Liste ist für die Erstansprache per Telefon gedacht; per Mail erst nach Zustimmung.
