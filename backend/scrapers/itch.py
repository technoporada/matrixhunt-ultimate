from typing import List
from .base import BaseScraper, Deal


class ItchScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Itch.io", "https://itch.io", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            url = f"{self.base_url}/games/free"
            async with self.session.get(url, headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for cell in soup.select(".game_cell")[:30]:
                        title_el = cell.select_one("a.title")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = title_el.get("href", "")
                            if href and not href.startswith("http"):
                                href = f"https:{href}" if href.startswith("//") else f"{self.base_url}{href}"
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
                                **self.listed_as_free("/games/free"),
                                **self.listed_as_free(),
                                category="games",
                                source="Itch.io",
                                requires_login=False,
                            ))
        except Exception as e:
            print(f"[Itch] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
