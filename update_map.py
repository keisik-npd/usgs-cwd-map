
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

SOURCE = (
    "https://www.usgs.gov/centers/nwhc/science/"
    "expanding-distribution-chronic-wasting-disease"
)

OUTPUT = Path("docs/cwd-map.jpg")

session = requests.Session()
session.headers.update({
    "User-Agent": "CWD-Map-Updater/1.0"
})

def fetch_page(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")

# Find the current USGS map media page.
soup = fetch_page(SOURCE)

media_url = None

for link in soup.find_all("a", href=True):
    href = link["href"]

    if "/media/images/distribution-chronic-wasting-disease" in href:
        media_url = urljoin(SOURCE, href)
        break

if not media_url:
    raise RuntimeError("CWD map media page not found")

print("Media page:", media_url)

# Find the original image.
media_soup = fetch_page(media_url)

image_url = None

for link in media_soup.find_all("a", href=True):
    if link.get_text(" ", strip=True).lower() == "original":
        image_url = urljoin(media_url, link["href"])
        break

if not image_url:
    raise RuntimeError("Original image URL not found")

print("Image URL:", image_url)

# Download the image.
response = session.get(image_url, timeout=60)
response.raise_for_status()

content_type = response.headers.get("Content-Type", "")

if "jpeg" not in content_type.lower():
    raise RuntimeError(
        f"Expected JPEG image, got {content_type}"
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

if OUTPUT.exists() and OUTPUT.read_bytes() == response.content:
    print("Map has not changed")
else:
    OUTPUT.write_bytes(response.content)
    print("Map downloaded successfully")
