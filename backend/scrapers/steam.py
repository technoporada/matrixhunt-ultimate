from typing import List
from .base import BaseScraper, Deal


class SteamScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Steam", "https://store.steampowered.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            url = f"{self.base_url}/search/?specials=1&maxprice=free&ignore_preferences=1&ndl=1"
            async with self.session.get(url, headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for row in soup.select("a.search_result_row")[:20]:
                        title_el = row.select_one(".title")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = row.get("href", "").split("?")[0]
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
                                price="Free",
                                category="games",
                                source="Steam",
                                requires_login=True,
                            ))
        except Exception as e:
            print(f"[Steam] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
