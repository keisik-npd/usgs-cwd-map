
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime, timezone
import hashlib

SOURCE = (
    "https://www.usgs.gov/centers/nwhc/science/"
    "expanding-distribution-chronic-wasting-disease"
)

OUTPUT = Path("docs/cwd-map.jpg")
ARCHIVE = Path("archive")

session = requests.Session()
session.headers.update({
    "User-Agent": "CWD-Map-Updater/1.0"
})


def fetch_page(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# Find the latest USGS map media page.
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


# Find the original-resolution image.
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

new_image = response.content
new_hash = hashlib.sha256(new_image).hexdigest()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
ARCHIVE.mkdir(parents=True, exist_ok=True)


# Check whether the image changed.
if OUTPUT.exists():
    old_image = OUTPUT.read_bytes()
else:
    old_image = None


# Archive unique images.
def archive_image(image):
    image_hash = hashlib.sha256(image).hexdigest()

    # Avoid archiving duplicate image contents.
    for existing in ARCHIVE.glob("*.jpg"):
        if hashlib.sha256(existing.read_bytes()).hexdigest() == image_hash:
            print("Image already archived:", existing.name)
            return

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = ARCHIVE / f"cwd-map-{date}-{image_hash[:8]}.jpg"

    filename.write_bytes(image)
    print("Archived:", filename)


if old_image == new_image:
    print("No map changes detected")

    # Ensure the current map is archived.
    archive_image(new_image)

else:
    # Preserve the previous version before replacing it.
    if old_image is not None:
        archive_image(old_image)

    # Archive the newly retrieved version.
    archive_image(new_image)

    OUTPUT.write_bytes(new_image)
    print("Current map updated successfully")
