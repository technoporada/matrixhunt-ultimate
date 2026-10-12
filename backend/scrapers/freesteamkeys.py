from typing import List
from .base import BaseScraper, Deal


class FreeSteamKeysScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("FreeSteamKeys", "https://www.freesteamkeys.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(self.base_url, headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for article in soup.select("article, .post, .entry")[:20]:
                        title_el = article.select_one("h2 a, h3 a, .entry-title a")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = self.resolve_url(title_el.get("href", ""))
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
<<<<<<< HEAD
                                **self.listed_as_free(),
=======
                                price="Free",
>>>>>>> main
                                category="games",
                                source="FreeSteamKeys",
                            ))
        except Exception as e:
            print(f"[FreeSteamKeys] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
