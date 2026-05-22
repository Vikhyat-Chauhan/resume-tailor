import httpx
from bs4 import BeautifulSoup

_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
_MIN_TEXT_LENGTH = 300  # below this, assume JS-rendered and fall back to Playwright


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    # prefer semantic content containers when available
    main = soup.find("main") or soup.find("article") or soup.body
    return " ".join((main or soup).get_text(separator=" ").split())


def _fetch_with_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30_000)
        html = page.content()
        browser.close()

    return _extract_text(html)


def fetch_jd(url: str) -> str:
    """Fetch job description text from a URL. Falls back to Playwright for JS-rendered pages."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=15, headers=_HEADERS)
        response.raise_for_status()
        text = _extract_text(response.text)
    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e

    if len(text) < _MIN_TEXT_LENGTH:
        try:
            text = _fetch_with_playwright(url)
        except ImportError:
            raise RuntimeError(
                "Page appears JS-rendered but playwright is not installed. "
                "Run: pip install playwright && playwright install chromium"
            )

    if not text.strip():
        raise RuntimeError(f"Could not extract any text from {url}")

    return text
