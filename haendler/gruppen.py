"""Warenbestand lesen und in Produktgruppen (Marke + Kategorie) einteilen.

Quelle ist die CSV, die der Ghostwriter stündlich aus dem Google Sheet „Warenbestand“
holt. Gelesen werden nur Hersteller, Artikel, EAN, Verfügbar und ⌀ EK; der EK dient nur
intern zum Sortieren der Gruppen (Bestandswert) und landet nie in der Ausgabe.
"""

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Kategorie → Muster im Artikelnamen (klein geschrieben). Reihenfolge zählt: erster Treffer gewinnt.
KATEGORIEN = [
    ("Smartphones", r"galaxy (s|a|z)\d|\bpixel \d|\biphone"),
    ("Tablets", r"\bipad|galaxy tab|\btab s\d"),
    ("Dockingstations", r"\bdock|\b(sd|wd)\d{2}tb\d"),
    ("Monitore", r"monitor|thinkvision|\b(p|u|s|se|e|g)\d{4}[a-z]*\b"),
    ("Webcams", r"webcam"),
    ("Taschen", r"topload|rucksack|backpack|tasche|sleeve"),
    ("Notebooks", r"laptop|thinkpad|notebook|ideapad|macbook"),
    ("Action-Kameras", r"osmo action|osmo pocket|insta360|gopro"),
    ("Sicherheitskameras", r"eufycam|überwachungskamera|security cam|doorbell|türklingel"),
    ("Kameras", r"\beos\b|kamera|camera|\balpha \d|lumix|\bkit\b.*\brf\b"),
    ("Drucker", r"pixma|drucker|printer|laserjet|ecotank|officejet"),
    ("Smartwatches & Fitness", r"forerunner|fenix|vivoactive|venu|versa|inspire|smartwatch|\bwatch\b|amazfit|fitbit"),
    ("Smart Speaker", r"\becho\b|\bnest\b|homepod"),
    ("E-Reader", r"kindle|tolino"),
    ("Konsolen & VR", r"playstation|xbox|nintendo|\bswitch 2\b|\bquest\b"),
    ("Headsets", r"headset|arctis|\bzone\b|encorepro|\bepos\b|\bpoly\b|jabra|kopfhörer|buds|airpods|barracuda|blackshark|kraken"),
    ("Mikrofone", r"seiren|\byeti\b|mikrofon|microphone"),
    ("Lautsprecher", r"\b(clip|flip|charge|go|xtreme|boombox) \d|lautsprecher|speaker"),
    ("Saugroboter & Haushalt", r"saug|robot|wisch|deebot|winbot|airfryer|fritteuse|\bmova\b|floor cleaner|vacuum|bürste|brush|staubbeutel|ersatzteil"),
    ("Drohnen", r"drohne|\bdji (mini|neo|flip|air|mavic|avata)"),
    ("Netzwerk", r"fritz|repeater|router|\bdeco\b|archer|zyxel|access point"),
    ("Speicher", r"\bssd\b|\bt7\b|sn\d{3}|microsd|usb-stick|festplatte"),
    ("Mäuse & Tastaturen", r"maus|mouse|keyboard|tastatur|huntsman|viper|deathadder|basilisk|mx master|\bmx board|\bkc \d|\bg\d{2,3}\b"),
    ("Eingabestifte", r"pencil|stylus"),
    ("Telefonie", r"yealink|mitel|\bdect\b|telefon"),
    ("Laufbänder", r"walkingpad|laufband|kingsmith"),
    ("Baby", r"momcozy|breast pump|milchpumpe"),
]
# Marken, deren ganzes Sortiment in eine Kategorie gehört (wenn der Name nichts verrät)
MARKEN_KATEGORIE = {"dreame": "Saugroboter & Haushalt", "ecovacs": "Saugroboter & Haushalt",
                    "mamibot": "Saugroboter & Haushalt", "roborock": "Saugroboter & Haushalt"}
_MUSTER = [(k, re.compile(m, re.I)) for k, m in KATEGORIEN]
# wie im Ghostwriter (agent/stock.py): Surface-Modelle heißen oft nur „Pro 7“, „Laptop 4“ …
_SURFACE = re.compile(r"\bsurface\b|\b(pro|laptop|book|studio|go)\s*\d", re.I)
MARKEN_ALIAS = {"fitbit": "Fitbit", "fritz!": "AVM", "avm": "AVM", "western": "Western Digital"}


@dataclass
class Artikel:
    hersteller: str
    name: str
    ean: str
    verfuegbar: int
    ek: float


@dataclass
class Gruppe:
    name: str
    artikel: list[Artikel] = field(default_factory=list)

    @property
    def bestandswert(self) -> float:
        return sum(a.verfuegbar * a.ek for a in self.artikel)

    def suchbegriffe(self, max_eans: int = 5) -> list[str]:
        """EANs der Artikel mit dem meisten Bestand (für die Suche per GTIN)."""
        top = sorted(self.artikel, key=lambda a: a.verfuegbar * a.ek, reverse=True)
        return [a.ean for a in top if a.ean][:max_eans]


def _zahl(text: str) -> float:
    text = (text or "").replace("€", "").replace("\xa0", "").strip()
    if not text:
        return 0.0
    if "," in text:  # deutsches Format 1.234,56
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def lade_bestand(pfad: Path) -> list[Artikel]:
    rows = csv.DictReader(io.StringIO(pfad.read_text(encoding="utf-8-sig")))
    out = []
    for r in rows:
        menge = int(_zahl(r.get("Verfügbar", "")))
        if menge <= 0 or not (r.get("Artikel") or "").strip():
            continue
        hersteller = (r.get("Hersteller") or "").strip()
        hersteller = MARKEN_ALIAS.get(hersteller.lower(), hersteller)
        out.append(Artikel(hersteller, " ".join(r["Artikel"].split()), (r.get("EAN") or "").strip(),
                           menge, _zahl(r.get("⌀ EK", ""))))
    return out


def kategorie(name: str) -> str | None:
    return next((k for k, m in _MUSTER if m.search(name)), None)


def gruppieren(artikel: list[Artikel]) -> list[Gruppe]:
    """Marke + Kategorie, sortiert nach Bestandswert (größte Gruppe zuerst).

    Microsoft Surface bleibt draußen (Marcs Regel: wird nie angeboten)."""
    gruppen: dict[str, Gruppe] = defaultdict(lambda: Gruppe(""))
    schreibweise: dict[str, str] = {}
    for a in artikel:
        if a.hersteller.lower() == "microsoft" and _SURFACE.search(a.name):
            continue
        marke = schreibweise.setdefault(a.hersteller.lower(), a.hersteller)  # MARSHALL = Marshall
        k = kategorie(a.name) or MARKEN_KATEGORIE.get(marke.lower())
        name = f"{marke} {k}" if k else marke
        g = gruppen[name.lower()]
        g.name = name
        g.artikel.append(a)
    return sorted(gruppen.values(), key=lambda g: g.bestandswert, reverse=True)
