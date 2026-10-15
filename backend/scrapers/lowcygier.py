from typing import List
from .base import BaseScraper, Deal
import re as _re

# Łowcy Gier (lowcygier.pl/darmowe/) — polska redakcja, codziennie: darmowe
# gry Steam/Epic/GOG/PS/Xbox/Switch. Strona główna stoi za Cloudflare
# ("Just a moment", 403 z datacenter), ale firmowy RSS WordPressa przechodzi
# (200) i niesie tytuł + link + zajawkę każdego wpisu.
#
# Bierzemy poziom ARTYKUŁU, nie pojedynczej gry: pełna treść z listą
# "- [Gra (Platforma)] za darmo" jest dopiero w HTML artykułu (zablokowany),
# a zajawka RSS to proza. Deal wskazuje więc artykuł po polsku, który tłumaczy
# jak odebrać (ważne przy Prime/Luna z kluczami). price_source mówi wprost:
# listing, nie pomiar.
RSS_URL = "https://lowcygier.pl/darmowe/feed/"

# Artykuły nie do trzymania: demka, DLC, triale czasowe i tygodniówki
# (te ostatnie linkują inne artykuły — duplikaty bez treści do odebrania).
_SKIP = _re.compile(
    r"\b(demo|dlc|dodatek|free play|trial|prolog|prologue)\b"
    r"|za darmo to uczciwa cena", _re.I)
# Bariera przy odbiorze: subskrypcja albo posiadanie podstawki.
# "posiada" bez końcowego \b, bo polskie końcówki (posiadacie/posiadaczy)
# nie mają tam granicy słowa — a \b z przodu chroni przed śmieciem.
_BARRIER = _re.compile(
    r"\b(prime|amazon luna|\bluna\b|game pass|playstation plus|ps plus)\b"
    r"|\bposiada", _re.I)


class LowcyGierScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("LowcyGier", "https://lowcygier.pl", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(RSS_URL, headers=self.headers) as resp:
                if resp.status != 200:
                    return []
                raw = await resp.text()
            import xml.etree.ElementTree as ET
            channel = ET.fromstring(raw).find("channel")
            if channel is None:
                return []
            for item in channel.findall("item")[:25]:
                link = (item.findtext("link") or "").strip()
                # Feed miesza kategorie — bierzemy tylko dział /darmowe/.
                if "/darmowe/" not in link:
                    continue
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                if not title or not link:
                    continue
                if _SKIP.search(title) or _SKIP.search(desc):
                    continue
                if not self.is_safe_url(link):
                    continue
                deals.append(Deal(
                    title=self.clean_title(title),
                    url=link,
                    **self.listed_as_free("/darmowe/"),
                    category="games",
                    source="LowcyGier",
                    description=" ".join(desc.split())[:300],
                    requires_login=bool(_BARRIER.search(title)
                                        or _BARRIER.search(desc)),
                ))
        except Exception as e:
            print(f"[LowcyGier] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
