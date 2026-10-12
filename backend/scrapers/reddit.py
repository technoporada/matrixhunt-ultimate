from typing import List
from .base import BaseScraper, Deal

# r/FreeGameFindings via the Arctic Shift archive API. Reddit's own .json
# endpoints return 403 without OAuth since 2023 (the old stealth-UA trick in
# debug_reddit.py is dead), while Arctic Shift serves the same posts keyless.
# Trade-off: the archive lags live Reddit by hours, noted in the README.
API_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

# Flairs that are not claimable offers. Matched on word boundaries, so every
# entry is a bare word or a full phrase: "until " with its trailing space was
# unmatched by \b and so was skipped by a substring test that also threw away
# "available until further notice" - an ACTIVE giveaway.
SKIP_FLAIRS = ("expired", "previously given", "psa", "read comments",
               "delisted", "next week", "until", "tasks",
               "prior work required", "paid base game", "claimed",
               "giveaway over", "no longer available", "not available")

# Posts below this score are unvetted drive-bys. The archive lags live
# Minimum score, 0 means no score filter.
#
# The archive is inconsistent: a post from weeks ago carries its real score
# (+557, +69 in the DB), while a post from the last few hours is served as
# score=1 regardless of its actual votes, because Arctic Shift snapshots the
# listing rather than the item. So a hard minimum of 5 rejected 39 of the 40
# newest posts and let the scraper look broken on a quiet day, and there is no
# signal to tell a genuine low-score drive-by from a fresh post that simply
# has not been voted on yet.
#
# Spam defence rests on the flair set, the badware list and is_safe_url, which
# are all independent of voting. Verified on live data: the newest 40 posts are
# almost entirely "PSA", "Random", "F2P to Paid" and "Prior Work Required" -
# all caught by the flair filter - plus one score=148 "Read Comments", also
# caught. Set to a number to re-enable the threshold.
MIN_SCORE = 0


def _reputation():
    """Badware engine from the local cache, or None.

    Returning None used to skip the whole badware check with no log line, so
    on a fresh install - before the first filter download - the only
    protection against a malware URL was absent and nothing said so."""
    try:
        from filterlists import cached_engine
        eng = cached_engine()
        if eng is None:
            print("[Reddit] filter lists unavailable - badware check DISABLED")
        return eng
    except Exception as e:
        print(f"[Reddit] filter lists unavailable ({type(e).__name__}) - "
              f"badware check DISABLED")
        return None


class RedditScraper(BaseScraper):
    def __init__(self, session=None):
        super().__init__("Reddit", "https://www.reddit.com", session)

    def _flair_skip(self, flair):
        """Match the phrase set on word boundaries.

        Plain substring matching meant a flair of "available until further
        notice" was dropped by the "until " entry - i.e. an ACTIVE giveaway
        was skipped - and "read comments first" matched "read comments"."""
        low = (flair or "").lower().strip()
        if not low:
            return False
        import re as _re
        for phrase in SKIP_FLAIRS:
            if _re.search(r"\b" + _re.escape(phrase.strip()) + r"\b", low):
                return True
        return False

    async def scrape(self) -> List[Deal]:
        deals = []
        try:
            # Pin a time window. "limit=40, sort=desc" returns the newest 40
            # posts whatever window that covers, so on a busy subreddit the
            # scrape could span minutes and still look healthy.
            import time as _time
            params = {
                "subreddit": "FreeGameFindings", "limit": 40, "sort": "desc",
                "after": _time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        _time.gmtime(_time.time() - 48 * 3600)),
            }
            async with self.session.get(API_URL, params=params, headers=self.headers) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                posts = data.get("data") or []
                rep = _reputation()
                for post in posts:
                    if not isinstance(post, dict):
                        continue
                    flair = post.get("link_flair_text") or ""
                    if self._flair_skip(flair):
                        continue
                    try:
                        score = int(post.get("score") or 0)
                    except (TypeError, ValueError):
                        score = 0
                    if score < MIN_SCORE:
                        continue
                    title = post.get("title", "") or ""
                    if not title or self.is_garbage(title):
                        continue
                    url = (post.get("url") or "").strip()
                    # Self-posts link back to reddit and carry no external
                    # destination - the deal (if any) lives in the text.
                    # Match on the HOST, not the whole string: the old
                    # `"reddit.com" in url` also dropped external links that
                    # merely contained the substring in a path or query, and
                    # let redd.it short links through to whatever they point at.
                    host = ""
                    try:
                        from urllib.parse import urlparse
                        host = (urlparse(url).hostname or "").lower()
                    except Exception:
                        host = ""
                    if not url or not host:
                        continue
                    if (host == "reddit.com" or host.endswith(".reddit.com")
                            or host == "redd.it" or host.endswith(".redd.it")):
                        continue
                    if not self.is_safe_url(url):
                        continue
                    # Reputation: drop links to badware-listed hosts.
                    if rep is not None:
                        blocked, rule = rep.check(url, url, "document")
                        if blocked:
                            print(f"[Reddit] badware skip: {url[:80]} ({rule.list_id})")
                            continue
                    deals.append(Deal(
                        title=self.clean_title(title),
                        url=url,
<<<<<<< HEAD
                        **self.listed_as_free(),
=======
                        price="Free",
>>>>>>> main
                        category="games",
                        source="Reddit",
                        description=f"[r/FreeGameFindings | {flair or 'no flair'} | "
                                    f"archive score {score}]",
                        is_adult=bool(post.get("over_18")),
                    ))
        except Exception as e:
            print(f"[Reddit] Error: {e}")
        return [d for d in deals if self.is_valid(d)]
