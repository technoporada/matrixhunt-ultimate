from typing import List
from .base import BaseScraper, Deal


class FreeToGameScraper(BaseScraper):
    """freetogame.com indexes free-to-play games. That is the entire site.

    A F2P title is not free-to-keep: you get a client, and the game lives
    behind a purchase, battle pass, gacha or energy timer. So this source
    cannot produce a valid offer for this project, and the 30 entries it
    returns every run were all rejected. Kept wired up, returns nothing.
    """

    def __init__(self, session=None):
        super().__init__("FreeToGame", "https://www.freetogame.com", session)

    async def scrape(self) -> List[Deal]:
        return []
        deals = []  # noqa: unreachable - kept for reference
        try:
            api_url = f"{self.base_url}/api/games?platform=pc&sort-by=popularity"
            async with self.session.get(api_url, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for game in data[:30]:
                        title = game.get("title", "")
                        if self.is_garbage(title):
                            continue
                        deals.append(Deal(
                            title=self.clean_title(title),
                            url=game.get("game_url", ""),
                            **self.listed_as_free("/api/games"),
                            **self.listed_as_free(),
                            category="games",
                            source="FreeToGame",
                            description=game.get("short_description", "")[:200],
                            image_url=game.get("thumbnail", ""),
                        ))
        except Exception as e:
            print(f"[FreeToGame] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
