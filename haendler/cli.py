"""Einstieg: python -m haendler.cli <befehl>

  gruppen [N]        Produktgruppen aus dem Warenbestand anzeigen (größte zuerst), ohne eBay
  probe              eine echte eBay-Antwort zeigen (prüft Zugang und Impressum-Felder)
  suche [N] [--mail] die N größten Gruppen (Standard 25) durchsuchen, je 20 Händler →
                     data/haendler_JJJJ-MM-TT.xlsx; mit --mail als Anhang an Marc
"""

import json
import os
import smtplib
import ssl
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

from . import excel
from .ebay import Ebay, impressum
from .gruppen import gruppieren, lade_bestand
from .suche import bestehende_kontakte, suche_gruppe

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


AUSGESCHLOSSEN = Path("config/ausgeschlossen.txt")


def _gruppen():
    pfad = Path(os.getenv("WARENBESTAND_CSV", "/opt/ghostwriter/data/warenbestand.csv"))
    raus = set()
    if AUSGESCHLOSSEN.exists():
        raus = {z.strip().lower() for z in AUSGESCHLOSSEN.read_text().splitlines() if z.strip() and not z.startswith("#")}
    return [g for g in gruppieren(lade_bestand(pfad)) if g.name.lower() not in raus]


def _mail(pfad: Path, text: str) -> None:
    load_dotenv(os.getenv("GHOSTWRITER_ENV", "/opt/ghostwriter/.env"))  # IONOS-Zugang des Ghostwriters
    msg = EmailMessage()
    msg["Subject"] = f"eBay-Händlersuche: neue Händlerliste vom {date.today():%d.%m.%Y}"
    msg["From"] = msg["To"] = os.environ["MAIL_FROM"]
    msg.set_content(text)
    msg.add_attachment(pfad.read_bytes(), maintype="application", subtype=XLSX.split("/")[1], filename=pfad.name)
    with smtplib.SMTP("smtp.ionos.de", 587, timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ["IONOS_SMTP_USER"], os.environ["IONOS_SMTP_PASSWORD"])
        smtp.send_message(msg)


def main() -> None:
    load_dotenv()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    zahlen = [int(a) for a in sys.argv[2:] if a.isdigit()]

    if cmd == "gruppen":
        for i, g in enumerate(_gruppen()[: zahlen[0] if zahlen else 50], 1):
            print(f"{i:3}. {g.name:<40} {len(g.artikel):3} Artikel  EANs: {', '.join(g.suchbegriffe(3))}")
        return

    if cmd == "probe":
        ebay = Ebay()
        g = _gruppen()[0]
        treffer = ebay.suche(gtin=g.suchbegriffe(1)[0]) or ebay.suche(q=g.name)
        print(f"Suche „{g.name}“: {len(treffer)} Angebote gewerblicher Händler")
        if treffer:
            print("Verkäufer im Suchergebnis:", json.dumps(treffer[0].get("seller"), ensure_ascii=False))
            item = ebay.artikel(treffer[0]["itemId"])
            print("Verkäufer im Angebot:", json.dumps(item.get("seller"), ensure_ascii=False, indent=1))
            print("→ ausgelesen:", impressum(item))
        return

    if cmd == "suche":
        anzahl = zahlen[0] if zahlen else 25
        ebay, cache, ergebnis = Ebay(), {}, []
        adressen, domains = bestehende_kontakte(Path(os.getenv("MAILINGLISTEN", "/opt/ghostwriter/data/mailinglisten")))
        for g in _gruppen()[:anzahl]:
            liste = suche_gruppe(ebay, g, cache, adressen, domains)
            ergebnis.append((g.name, liste))
            print(f"{g.name:<40} {len(liste):2} Händler")
        pfad = excel.schreibe(ergebnis, Path(f"data/haendler_{date.today().isoformat()}.xlsx"))
        gesamt = sum(len(l) for _, l in ergebnis)
        mit_mail = sum(1 for _, l in ergebnis for h in l if h.kontakt.get("email"))
        zusammenfassung = (f"{gesamt} Händler in {len(ergebnis)} Produktgruppen, davon {mit_mail} mit E-Mail-Adresse.\n"
                           f"{len(cache)} verschiedene Händler, {ebay.aufrufe} eBay-Abfragen.")
        print(zusammenfassung, "→", pfad)
        if "--mail" in sys.argv:
            _mail(pfad, "Moin Marc,\n\nanbei die neue Händlerliste von ebay.de.\n\n" + zusammenfassung +
                  "\n\nBestehende Kontakte aus deinen Mailinglisten sind schon herausgefiltert.\n")
            print("Liste an Marc geschickt.")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
