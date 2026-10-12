from typing import List
from .base import BaseScraper, Deal


class GOGScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("GOG", "https://www.gog.com", session)

    async def scrape(self) -> List[Deal]:
        """GOG's public /games/ajax/filtered has NO free filter: `is_free=true`
        is ignored, `price=1-0` returns a non-JSON error page, `price=free`
        returns zero products, and `limit` is not a supported param (400). The
        default listing is 3 paid games - verified live, the first one is
        "Offworld Trading Company" with price.isFree === false. So the old code
        stored paid games as "Free". We now filter on GOG's own isFree and
        therefore usually return 0: that is the honest answer, and adding the
        offers back means finding a real giveaway feed first.
        """
        deals = []
        try:
            # is_free=true is NOT a documented filter of /games/ajax/filtered
            # (the documented ones are category/devpub/feature/language/
            # mediaType/page/price/release/search/sort/system/limit), so it
            # was ignored and EVERY returned product was stored as price
            # "Free" - paid games included. The response does carry
            # products[].price.isFree, so that is what we check now.
            url = f"{self.base_url}/games/ajax/filtered?mediaType=game"
            async with self.session.get(url, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for product in data.get("products", [])[:40]:
                        if not self._is_free(product):
                            continue
                        title = product.get("title") or ""
                        if not title or self.is_garbage(title):
                            continue
                        href = product.get("url") or ""
                        if not href:
                            continue
                        deals.append(Deal(
                            title=self.clean_title(title),
                            url=self.resolve_url(href),
                            price="Free",
<<<<<<< HEAD
                                    price_claim="Free",
                                    price_source="api:gog",
=======
>>>>>>> main
                            category="games",
                            source="GOG",
                            image_url=product.get("image", "") or "",
                            requires_login=True,
                        ))
        except Exception as e:
            print(f"[GOG] Error: {e}")
        return [d for d in deals if self.is_valid(d)]

    @staticmethod
    def _is_free(product) -> bool:
        """True only when GOG itself says the product is free.

        Fail closed: if the price block is missing entirely we do NOT assume
        free, because that is exactly how paid games ended up in the DB.
        """
        price = product.get("price")
        if not isinstance(price, dict):
            return False
        if price.get("isFree") is True:
            return True
        # Some entries carry a finalPrice of 0 with a discount; treat an
        # explicit zero final price as free too, but nothing else.
        fp = price.get("finalPrice")
        if isinstance(fp, (int, float)) and fp == 0 and price.get("isFree") is not False:
            return True
        return False
