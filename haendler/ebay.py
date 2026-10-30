"""Offizielle eBay Browse API (ebay.de) – kein Auslesen der Webseite.

Anmeldung per Client-Credentials (App ID + Cert ID aus developer.ebay.com, in .env).
Die Feldnamen für das Impressum (sellerLegalInfo) prüft `python -m haendler.cli probe`
beim ersten Lauf gegen eine echte Antwort.
"""

import base64
import os
import time

import requests

API = "https://api.ebay.com"
MARKTPLATZ = "EBAY_DE"
SCOPE = "https://api.ebay.com/oauth/api_scope"


class Ebay:
    def __init__(self) -> None:
        self._token = ""
        self._ablauf = 0.0
        self.aufrufe = 0

    def _auth(self) -> str:
        if time.time() < self._ablauf - 60:
            return self._token
        kennung = f"{os.environ['EBAY_CLIENT_ID']}:{os.environ['EBAY_CLIENT_SECRET']}"
        resp = requests.post(
            f"{API}/identity/v1/oauth2/token",
            headers={"Authorization": "Basic " + base64.b64encode(kennung.encode()).decode(),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": SCOPE},
            timeout=30,
        )
        resp.raise_for_status()
        daten = resp.json()
        self._token, self._ablauf = daten["access_token"], time.time() + daten.get("expires_in", 7200)
        return self._token

    def _get(self, pfad: str, params: dict | None = None) -> dict:
        for versuch in range(4):
            self.aufrufe += 1
            resp = requests.get(
                f"{API}{pfad}", params=params, timeout=30,
                headers={"Authorization": f"Bearer {self._auth()}", "X-EBAY-C-MARKETPLACE-ID": MARKTPLATZ},
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(5 * (versuch + 1))  # Limit/Störung bei eBay: kurz warten
                continue
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return {}

    def suche(self, q: str | None = None, gtin: str | None = None, seiten: int = 1) -> list[dict]:
        """Angebote gewerblicher Händler (bis 200 je Seite)."""
        params = {"limit": 200, "filter": "sellerAccountTypes:{BUSINESS}"}
        if q:
            params["q"] = q
        if gtin:
            params["gtin"] = gtin
        out = []
        for seite in range(seiten):
            params["offset"] = seite * 200
            daten = self._get("/buy/browse/v1/item_summary/search", params)
            out += daten.get("itemSummaries", [])
            if len(out) >= daten.get("total", 0):
                break
        return out

    def artikel(self, item_id: str) -> dict:
        return self._get(f"/buy/browse/v1/item/{item_id}")


def impressum(item: dict) -> dict:
    """Kontaktdaten aus dem Impressum eines Angebots (leer, wenn eBay keine liefert)."""
    verkaeufer = item.get("seller") or {}
    info = verkaeufer.get("sellerLegalInfo") or {}
    adr = info.get("sellerProvidedLegalAddress") or {}
    strasse = " ".join(x for x in (adr.get("addressLine1"), adr.get("addressLine2")) if x)
    ort = " ".join(x for x in (adr.get("postalCode"), adr.get("city")) if x)
    land = adr.get("countryName") or adr.get("country") or ""
    return {
        "firma": info.get("name") or "",
        "vorname": info.get("legalContactFirstName") or "",
        "name": info.get("legalContactLastName") or "",
        "adresse": ", ".join(x for x in (strasse, ort, land) if x),
        "email": info.get("email") or "",
        "telefon": info.get("phone") or "",
    }
