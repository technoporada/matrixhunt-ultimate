from typing import List
from .base import BaseScraper, Deal


class SharewareScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("SharewareOnSale", "https://sharewareonsale.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(f"{self.base_url}/free", headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for card in soup.select(".deal-card, .product-card, article")[:20]:
                        title_el = card.select_one("h2, h3, .title, .deal-title")
                        link_el = card.select_one("a[href]")
                        if title_el and link_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = link_el.get("href", "")
                            if not href.startswith("http"):
                                href = f"{self.base_url}{href}"
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
<<<<<<< HEAD
                                **self.listed_as_free("/free"),
=======
                                price="Free",
>>>>>>> main
                                category="software",
                                source="SharewareOnSale",
                            ))
        except Exception as e:
            print(f"[SharewareOnSale] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
