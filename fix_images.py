#\!/usr/bin/env python3
"""Validate and fix Wikimedia image URLs in generated JSON files.

Checks each image URL, and if broken (404), searches Wikimedia Commons API
for a replacement based on the caption text.
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
RATE_LIMIT = 1.0  # seconds between API calls

def check_url(url, timeout=10):
    """Check if a URL returns 200."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "StudyHubImageFixer/1.0")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

def search_commons(query, limit=3):
    """Search Wikimedia Commons for images matching query."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",  # File namespace
        "gsrsearch": query,
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "400",
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "StudyHubImageFixer/1.0")
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            ii = page.get("imageinfo", [{}])[0]
            if ii.get("url"):
                thumb = ii.get("thumburl", ii["url"])
                meta = ii.get("extmetadata", {})
                artist = meta.get("Artist", {}).get("value", "")
                license_name = meta.get("LicenseShortName", {}).get("value", "")
                # Strip HTML from artist
                artist = re.sub(r"<[^>]+>", "", artist).strip()
                attribution = f"{artist}, {license_name}, via Wikimedia Commons" if artist else ""
                results.append({
                    "url": ii["url"],
                    "thumbnail_url": thumb,
                    "attribution": attribution,
                })
        return results
    except Exception as e:
        print(f"  Search error: {e}")
        return []

def extract_search_terms(image):
    """Extract search terms from image caption and entity info."""
    caption = image.get("caption", "")
    # Take first 60 chars of caption, remove parenthetical details
    terms = re.sub(r"\([^)]*\)", "", caption)
    terms = re.sub(r"--.*", "", terms)
    terms = terms.strip()[:60]
    return terms

def process_file(filepath):
    """Process a single JSON file, fixing broken image URLs."""
    with open(filepath) as f:
        data = json.load(f)

    images = data.get("images", [])
    if not images:
        return 0

    fixed = 0
    for img in images:
        url = img.get("url") or img.get("thumbnail_url")
        if not url:
            continue

        print(f"  Checking: {url[:80]}...")
        if check_url(url):
            print(f"    OK")
            continue

        # Also check thumbnail
        thumb = img.get("thumbnail_url")
        if thumb and thumb \!= url and check_url(thumb):
            print(f"    Main broken, thumbnail OK")
            continue

        print(f"    BROKEN - searching for replacement...")
        terms = extract_search_terms(img)
        if not terms:
            print(f"    No search terms available, skipping")
            continue

        time.sleep(RATE_LIMIT)
        results = search_commons(terms)
        if results:
            replacement = results[0]
            old_url = img["url"]
            img["url"] = replacement["url"]
            img["thumbnail_url"] = replacement["thumbnail_url"]
            if replacement["attribution"]:
                img["attribution"] = replacement["attribution"]
            print(f"    FIXED: {replacement[url][:80]}")
            fixed += 1
        else:
            print(f"    No replacement found for: {terms[:50]}")

        time.sleep(RATE_LIMIT)

    if fixed > 0:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {fixed} fixes to {os.path.basename(filepath)}")

    return fixed

def main():
    total_fixed = 0
    total_checked = 0
    files = sorted(f for f in os.listdir(GENERATED_DIR) if f.endswith(".json") and f \!= "timeline_anchors.json")

    print(f"Processing {len(files)} JSON files...")
    for filename in files:
        filepath = os.path.join(GENERATED_DIR, filename)
        print(f"\n{filename}:")
        total_checked += 1
        total_fixed += process_file(filepath)

    print(f"\n{=*50}")
    print(f"Done\! Checked {total_checked} files, fixed {total_fixed} images.")

if __name__ == "__main__":
    main()
