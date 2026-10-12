from typing import List
from .base import BaseScraper, Deal


class GameJoltScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("GameJolt", "https://gamejolt.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            api_url = f"{self.base_url}/api/v1/games/?sort=-hot&limit=20&filters=free"
            async with self.session.get(api_url, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    games = self.nested(data, "payload", "games", default=[])[:20]
                    for game in games:
                        if not isinstance(game, dict):
                            continue
                        title = game.get("title", "")
                        if not title or self.is_garbage(title):
                            continue
                        slug = game.get("slug") or ""
                        deals.append(Deal(
                            title=self.clean_title(title),
                            url=f"{self.base_url}/games/{slug}",
<<<<<<< HEAD
                            **self.listed_as_free("/api/v1/games/"),
=======
                            price="Free",
>>>>>>> main
                            category="games",
                            source="GameJolt",
                            description=(game.get("description") or "")[:200],
                            image_url=game.get("img_thumbnail", "") or "",
                        ))
        except Exception as e:
            print(f"[GameJolt] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
