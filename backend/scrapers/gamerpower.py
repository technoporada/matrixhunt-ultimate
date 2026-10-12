from typing import List
from .base import BaseScraper, Deal


class GamerpowerScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("GamerPower", "https://www.gamerpower.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(f"{self.base_url}/api/giveaways", headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data[:50]:
                        title = item.get("title", "")
                        if self.is_garbage(title):
                            continue
                        deals.append(Deal(
                            title=self.clean_title(title),
                            url=item.get("open_giveaway_url", ""),
<<<<<<< HEAD
                            **self.listed_as_free("/api/giveaways"),
=======
                            price="Free",
>>>>>>> main
                            original_price=item.get("worth", ""),
                            category="games",
                            source="GamerPower",
                            description=item.get("description", "")[:200],
                            image_url=item.get("image", ""),
                            requires_login=bool(item.get("keys", [])),
                        ))
        except Exception as e:
            print(f"[GamerPower] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
