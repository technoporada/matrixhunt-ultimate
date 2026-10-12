from typing import List
from .base import BaseScraper, Deal


class NebulaScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Nebula", "https://games.nebula.app", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            api_url = "https://games.nebula.app/api/games/free"
            async with self.session.get(api_url, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data if isinstance(data, list) else data.get("games", data.get("data", []))
                    for game in items[:30]:
                        if not isinstance(game, dict):
                            continue
                        title = game.get("title", game.get("name", ""))
                        if not title or self.is_garbage(title):
                            continue
                        url = game.get("url", game.get("link", ""))
                        deals.append(Deal(
                            title=self.clean_title(title),
                            url=url,
<<<<<<< HEAD
                            **self.listed_as_free("/api/games/free"),
=======
                            price="Free",
>>>>>>> main
                            category="games",
                            source="Nebula",
                            description=game.get("description", "")[:200],
                            image_url=game.get("image", game.get("thumbnail", "")),
                        ))
        except Exception as e:
            print(f"[Nebula] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
