from typing import List
from .base import BaseScraper, Deal


class HumbleScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Humble Bundle", "https://www.humblebundle.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(f"{self.base_url}/free", headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for card in soup.select("[data-testid='product-card'], .product-card, .tile")[:20]:
                        title_el = card.select_one("h3, h4, .product-name, .tile-name")
                        link_el = card.select_one("a[href]")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = ""
                            if link_el:
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
                                category="games",
                                source="Humble Bundle",
                                requires_login=True,
                            ))
        except Exception as e:
            print(f"[Humble] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
