from typing import List
from .base import BaseScraper, Deal


class GiveawayRadarScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("GiveawayRadar", "https://giveawayradar.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(self.base_url, headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for article in soup.select("article, .post, .giveaway-item")[:20]:
                        title_el = article.select_one("h2 a, h3 a, .entry-title a, .giveaway-title a")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = self.resolve_url(title_el.get("href", ""))
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
                                price="Free",
                                category="games",
                                source="GiveawayRadar",
                            ))
        except Exception as e:
            print(f"[GiveawayRadar] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
