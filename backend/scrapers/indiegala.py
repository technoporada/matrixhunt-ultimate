from typing import List
from .base import BaseScraper, Deal


class IndieGalaScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("IndieGala", "https://freebies.indiegala.com", session)

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            async with self.session.get(self.base_url, headers=self.headers) as resp:
                if resp.status == 200:
                    from bs4 import BeautifulSoup
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for col in soup.select("div.products-col")[:20]:
                        title_div = col.find("div", class_="product-title")
                        link = col.find("a")
                        if title_div and link:
                            title = title_div.get_text(strip=True)
                            if self.is_garbage(title):
                                continue
                            href = link.get("href", "")
                            if not href.startswith("http"):
                                href = f"https://freebies.indiegala.com{href}"
                            deals.append(Deal(
                                title=self.clean_title(title),
                                url=href,
                                price="Free",
                                category="games",
                                source="IndieGala",
                                requires_login=True,
                            ))
        except Exception as e:
            print(f"[IndieGala] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
