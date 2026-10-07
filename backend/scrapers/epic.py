from typing import List
from .base import BaseScraper, Deal


class EpicScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Epic Games", "https://store.epicgames.com", session)
        self.api_url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(self.api_url, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    games = self.nested(data, "data", "Catalog", "searchStore", "elements", default=[])
                    for game in games:
                        price_info = self.nested(game, "price", "totalPrice", default={})
                        discount = price_info.get("discountPrice", -1)
                        if discount is None:
                            discount = -1
                        if discount == 0:
                            slug = ""
                            mappings = self.nested(game, "catalogNs", "mappings", default=[])
                            if mappings:
                                slug = mappings[0].get("pageSlug", "") or ""
                            original = price_info.get("originalPrice") or 0
                            deals.append(Deal(
                                title=self.clean_title(game.get("title", "")),
                                url=f"{self.base_url}/en-US/p/{slug}" if slug else "",
                                price="Free",
                                original_price=f"${original/100:.2f}",
                                category="games",
                                source="Epic Games",
                                description=(game.get("description") or "")[:200],
                                requires_login=True,
                            ))
        except Exception as e:
            print(f"[Epic] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
