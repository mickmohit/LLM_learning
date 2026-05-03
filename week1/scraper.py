import requests
from bs4 import BeautifulSoup


def fetch_website_contents(url):
    """Fetch and return the text content of a website."""
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    return soup.get_text(separator="\n", strip=True)
