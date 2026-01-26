#!/usr/bin/env python3
"""
NotebookLM Study Hub - Summary Regenerator

This script regenerates summaries from transcripts in article-style format,
enriched with images from Wikimedia Commons and proper study guide structure.

Usage:
    python regenerate_summaries.py [--asset-id <id>] [--all]

Environment variables:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_KEY - Your Supabase service role key (not anon key!)
    OPENAI_API_KEY - Your OpenAI API key (for GPT-4o)
"""

import os
import sys
import json
import re
import argparse
import time
from typing import Optional
from dataclasses import dataclass

# Try imports
try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Please install openai: pip install openai")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("Please install supabase: pip install supabase")
    sys.exit(1)


@dataclass
class WikiImage:
    """Represents an image from Wikimedia Commons"""
    title: str
    url: str
    thumb_url: str
    description: str
    attribution: str
    width: int
    height: int


# =============================================================================
# PROMPTS - The key to getting article-style content, not meta summaries
# =============================================================================

ARTICLE_GENERATION_PROMPT = """You are creating an educational study guide article from a podcast transcript.

CRITICAL INSTRUCTIONS:
1. Write the content AS IF IT WERE A STANDALONE ARTICLE about the topic - NOT a summary of a podcast
2. NEVER use phrases like:
   - "The hosts discuss..."
   - "The podcast covers..."
   - "They talk about..."
   - "The speakers mention..."
   - "This episode explores..."
3. Instead, write DIRECTLY about the subject matter as factual content
4. Write as if you are a knowledgeable author teaching the reader about the topic

FORMAT REQUIREMENTS:
- Use markdown formatting with ## headers for sections
- Include **bold** for key terms when first introduced
- Organize logically by topic/theme, not chronologically by conversation
- Aim for 800-1500 words of substantive content

STUDY GUIDE STRUCTURE:
1. Opening paragraph introducing the topic (no meta-commentary)
2. Main content sections with ## headers
3. Each section should teach concrete information
4. Include specific facts, dates, names, places as mentioned
5. End with key takeaways

EXAMPLE OF WHAT NOT TO DO:
❌ "In this podcast, the hosts explore the Palace of Versailles and discuss its history..."

EXAMPLE OF WHAT TO DO:
✅ "The Palace of Versailles stands as one of the most magnificent royal residences ever constructed. Built during the reign of Louis XIV in the 17th century, it transformed from a hunting lodge into a symbol of absolute monarchy..."

Now generate an article-style study guide from this transcript:

---
{transcript}
---

Remember: Write ABOUT the topic, not ABOUT the podcast."""


KEY_TERMS_PROMPT = """Extract key terms, people, places, events, and concepts from this educational content that would benefit from visual illustrations.

For each item, provide:
1. The term/name
2. A brief description (1 sentence)
3. A suggested Wikipedia article title for finding images
4. A suggested image search query

Return as JSON array:
[
  {
    "term": "Palace of Versailles",
    "description": "French royal château and gardens built by Louis XIV",
    "wikipedia_article": "Palace of Versailles",
    "image_query": "Palace of Versailles exterior"
  },
  ...
]

Focus on terms that are:
- Visual (places, people, artworks, objects, events)
- Central to the topic (not peripheral mentions)
- Educational (would help the reader understand better)

Limit to 5-8 most important visual terms.

Content to analyze:
{content}"""


TLDR_PROMPT = """Write a single sentence (max 25 words) that captures the main topic and key insight from this content. Do not reference "the podcast" or "the hosts" - just state the key information directly.

Example:
✅ "The Palace of Versailles revolutionized European court architecture and became the model for royal residences across the continent."
❌ "This podcast discusses how Versailles influenced European architecture."

Content:
{content}"""


KEY_POINTS_PROMPT = """Extract 5-7 key takeaways from this educational content. Each should be a concrete fact or insight the reader should remember. Write them as direct statements, not as summaries of what was discussed.

Format as a JSON array of strings:
["Key point 1", "Key point 2", ...]

Example:
✅ ["Versailles took 50 years to complete and employed over 36,000 workers", "The Hall of Mirrors contains 357 mirrors and symbolized French technological achievement"]
❌ ["The podcast mentions that Versailles took a long time to build", "They discuss the Hall of Mirrors"]

Content:
{content}"""


# =============================================================================
# Wikimedia Commons Image Fetcher
# =============================================================================

class WikimediaImageFetcher:
    """Fetches high-quality images from Wikimedia Commons"""

    COMMONS_API = "https://commons.wikimedia.org/w/api.php"
    WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.cache = {}

    def search_images(self, query: str, limit: int = 3) -> list[WikiImage]:
        """Search Wikimedia Commons for images matching query"""
        if query in self.cache:
            return self.cache[query]

        images = []

        # First try to get images from the Wikipedia article
        wiki_images = self._get_wikipedia_article_images(query, limit)
        images.extend(wiki_images)

        # If not enough, search Commons directly
        if len(images) < limit:
            commons_images = self._search_commons(query, limit - len(images))
            images.extend(commons_images)

        self.cache[query] = images[:limit]
        return images[:limit]

    def _get_wikipedia_article_images(self, article_title: str, limit: int) -> list[WikiImage]:
        """Get images from a Wikipedia article"""
        images = []

        try:
            # Get images used in the article
            params = {
                "action": "query",
                "titles": article_title,
                "prop": "images",
                "imlimit": limit * 2,  # Get more since we'll filter
                "format": "json"
            }
            resp = self.client.get(self.WIKIPEDIA_API, params=params)
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                for img in page.get("images", []):
                    title = img.get("title", "")
                    # Skip icons, logos, and non-content images
                    if any(skip in title.lower() for skip in [
                        "icon", "logo", "flag", "commons-logo", "wiki",
                        ".svg", "symbol", "button", "arrow"
                    ]):
                        continue

                    # Get image details from Commons
                    img_details = self._get_image_details(title)
                    if img_details:
                        images.append(img_details)
                        if len(images) >= limit:
                            break
        except Exception as e:
            print(f"Warning: Could not fetch Wikipedia images for '{article_title}': {e}")

        return images

    def _search_commons(self, query: str, limit: int) -> list[WikiImage]:
        """Search Wikimedia Commons directly"""
        images = []

        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": f"{query} filetype:bitmap",
                "srnamespace": "6",  # File namespace
                "srlimit": limit * 2,
                "format": "json"
            }
            resp = self.client.get(self.COMMONS_API, params=params)
            data = resp.json()

            for result in data.get("query", {}).get("search", []):
                title = result.get("title", "")
                img_details = self._get_image_details(title)
                if img_details:
                    images.append(img_details)
                    if len(images) >= limit:
                        break
        except Exception as e:
            print(f"Warning: Could not search Commons for '{query}': {e}")

        return images

    def _get_image_details(self, file_title: str) -> Optional[WikiImage]:
        """Get details for a specific image file"""
        try:
            params = {
                "action": "query",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata",
                "iiurlwidth": 800,  # Get thumbnail at 800px width
                "format": "json"
            }
            resp = self.client.get(self.COMMONS_API, params=params)
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                info = page.get("imageinfo", [{}])[0]
                meta = info.get("extmetadata", {})

                url = info.get("url", "")
                thumb_url = info.get("thumburl", url)

                # Skip if too small
                width = info.get("width", 0)
                height = info.get("height", 0)
                if width < 200 or height < 150:
                    return None

                description = meta.get("ImageDescription", {}).get("value", "")
                # Clean HTML from description
                description = re.sub(r'<[^>]+>', '', description)[:200]

                artist = meta.get("Artist", {}).get("value", "")
                artist = re.sub(r'<[^>]+>', '', artist)[:100]
                license_info = meta.get("LicenseShortName", {}).get("value", "")

                attribution = f"{artist}" if artist else "Wikimedia Commons"
                if license_info:
                    attribution += f" ({license_info})"

                return WikiImage(
                    title=file_title.replace("File:", ""),
                    url=url,
                    thumb_url=thumb_url,
                    description=description,
                    attribution=attribution,
                    width=width,
                    height=height
                )
        except Exception as e:
            print(f"Warning: Could not get image details for '{file_title}': {e}")

        return None

    def close(self):
        self.client.close()


# =============================================================================
# Summary Generator
# =============================================================================

class SummaryGenerator:
    """Generates article-style summaries with images"""

    def __init__(self, openai_api_key: str):
        self.openai = OpenAI(api_key=openai_api_key)
        self.image_fetcher = WikimediaImageFetcher()

    def generate_rich_summary(self, transcript: str, title: str) -> dict:
        """Generate a complete rich summary with images and resources"""

        print(f"  Generating article content...")
        article_content = self._generate_article(transcript)

        print(f"  Extracting key terms for images...")
        key_terms = self._extract_key_terms(article_content)

        print(f"  Fetching images from Wikimedia Commons...")
        images = self._fetch_images_for_terms(key_terms)

        print(f"  Generating TL;DR...")
        tldr = self._generate_tldr(article_content)

        print(f"  Extracting key points...")
        key_points = self._extract_key_points(article_content)

        # Build the final summary with embedded images
        enhanced_content = self._embed_images_in_content(article_content, images, key_terms)

        # Build metadata
        metadata = {
            "tldr": tldr,
            "images": [
                {
                    "term": img["term"],
                    "url": img["image"].url,
                    "thumb_url": img["image"].thumb_url,
                    "caption": img["image"].description or img["term"],
                    "attribution": img["image"].attribution
                }
                for img in images
            ],
            "resources": {
                "wikipedia_articles": [t["wikipedia_article"] for t in key_terms if t.get("wikipedia_article")],
                "search_queries": [t["term"] for t in key_terms],
                "image_searches": [t.get("image_query", t["term"]) for t in key_terms]
            },
            "claude_reference": {
                "topics_covered": [t["term"] for t in key_terms]
            }
        }

        return {
            "summary_text": enhanced_content,
            "key_points": key_points,
            "metadata": metadata,
            "summary_type": "rich"
        }

    def _generate_article(self, transcript: str) -> str:
        """Generate article-style content from transcript"""
        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": ARTICLE_GENERATION_PROMPT.format(transcript=transcript)}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        return response.choices[0].message.content

    def _extract_key_terms(self, content: str) -> list[dict]:
        """Extract key visual terms from content"""
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": KEY_TERMS_PROMPT.format(content=content)}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        try:
            # Extract JSON from response
            text = response.choices[0].message.content
            # Find JSON array in response
            match = re.search(r'\[[\s\S]*\]', text)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Could not parse key terms: {e}")

        return []

    def _generate_tldr(self, content: str) -> str:
        """Generate a TL;DR sentence"""
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": TLDR_PROMPT.format(content=content[:2000])}
            ],
            temperature=0.5,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()

    def _extract_key_points(self, content: str) -> list[str]:
        """Extract key takeaway points"""
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": KEY_POINTS_PROMPT.format(content=content)}
            ],
            temperature=0.3,
            max_tokens=500
        )

        try:
            text = response.choices[0].message.content
            match = re.search(r'\[[\s\S]*\]', text)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Warning: Could not parse key points: {e}")

        return []

    def _fetch_images_for_terms(self, key_terms: list[dict]) -> list[dict]:
        """Fetch images from Wikimedia Commons for each key term"""
        images = []

        for term in key_terms:
            wiki_article = term.get("wikipedia_article", term["term"])
            found_images = self.image_fetcher.search_images(wiki_article, limit=1)

            if found_images:
                images.append({
                    "term": term["term"],
                    "image": found_images[0]
                })

            # Rate limit to be nice to Wikimedia
            time.sleep(0.2)

        return images

    def _embed_images_in_content(self, content: str, images: list[dict], key_terms: list[dict]) -> str:
        """Embed image references in the content at appropriate locations"""

        if not images:
            return content

        # Create image markdown blocks
        image_blocks = []
        for img_data in images:
            img = img_data["image"]
            block = f'\n\n![{img_data["term"]}]({img.thumb_url})\n*{img.description or img_data["term"]}. Credit: {img.attribution}*\n\n'
            image_blocks.append({
                "term": img_data["term"],
                "block": block
            })

        # Try to insert images after the first paragraph that mentions each term
        enhanced = content
        for img_block in image_blocks:
            term = img_block["term"]
            # Find first occurrence of the term
            pattern = re.compile(rf'(\n\n[^#\n]*{re.escape(term)}[^#\n]*\n)', re.IGNORECASE)
            match = pattern.search(enhanced)
            if match:
                # Insert image after the paragraph
                insert_pos = match.end()
                enhanced = enhanced[:insert_pos] + img_block["block"] + enhanced[insert_pos:]

        # If we couldn't insert any images inline, add them at the end
        inline_count = sum(1 for img in image_blocks if img["term"].lower() in enhanced.lower())
        if inline_count == 0 and images:
            enhanced += "\n\n## Visual References\n\n"
            for img_data in images:
                img = img_data["image"]
                enhanced += f'![{img_data["term"]}]({img.thumb_url})\n*{img.description or img_data["term"]}. Credit: {img.attribution}*\n\n'

        return enhanced

    def close(self):
        self.image_fetcher.close()


# =============================================================================
# Database Operations
# =============================================================================

class DatabaseManager:
    """Manages Supabase database operations"""

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def get_all_assets_with_transcripts(self) -> list[dict]:
        """Get all assets that have transcripts"""
        result = self.client.table("notebooklm_assets").select(
            "id, asset_title, notebooklm_transcripts(transcript_text)"
        ).execute()

        return [
            {
                "id": r["id"],
                "title": r["asset_title"],
                "transcript": r["notebooklm_transcripts"][0]["transcript_text"]
                    if r.get("notebooklm_transcripts") else None
            }
            for r in result.data
            if r.get("notebooklm_transcripts")
        ]

    def get_asset_with_transcript(self, asset_id: str) -> Optional[dict]:
        """Get a specific asset with its transcript"""
        result = self.client.table("notebooklm_assets").select(
            "id, asset_title, notebooklm_transcripts(transcript_text)"
        ).eq("id", asset_id).execute()

        if result.data:
            r = result.data[0]
            if r.get("notebooklm_transcripts"):
                return {
                    "id": r["id"],
                    "title": r["asset_title"],
                    "transcript": r["notebooklm_transcripts"][0]["transcript_text"]
                }
        return None

    def upsert_summary(self, asset_id: str, summary_data: dict) -> None:
        """Insert or update a summary"""

        # Check if rich summary exists
        existing = self.client.table("notebooklm_summaries").select("id").eq(
            "asset_id", asset_id
        ).eq("summary_type", "rich").execute()

        record = {
            "asset_id": asset_id,
            "summary_type": "rich",
            "summary_text": summary_data["summary_text"],
            "key_points": summary_data["key_points"],
            "metadata": summary_data["metadata"]
        }

        if existing.data:
            # Update existing
            self.client.table("notebooklm_summaries").update(record).eq(
                "id", existing.data[0]["id"]
            ).execute()
            print(f"  Updated existing rich summary")
        else:
            # Insert new
            self.client.table("notebooklm_summaries").insert(record).execute()
            print(f"  Created new rich summary")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Regenerate NotebookLM summaries in article-style format"
    )
    parser.add_argument(
        "--asset-id",
        help="Process a specific asset by ID"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all assets with transcripts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate but don't save to database"
    )

    args = parser.parse_args()

    if not args.asset_id and not args.all:
        parser.error("Must specify either --asset-id or --all")

    # Check environment variables
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not all([supabase_url, supabase_key, openai_key]):
        print("Error: Missing required environment variables.")
        print("Set SUPABASE_URL, SUPABASE_KEY, and OPENAI_API_KEY")
        sys.exit(1)

    # Initialize
    db = DatabaseManager(supabase_url, supabase_key)
    generator = SummaryGenerator(openai_key)

    try:
        # Get assets to process
        if args.asset_id:
            asset = db.get_asset_with_transcript(args.asset_id)
            if not asset:
                print(f"Error: Asset {args.asset_id} not found or has no transcript")
                sys.exit(1)
            assets = [asset]
        else:
            assets = db.get_all_assets_with_transcripts()
            print(f"Found {len(assets)} assets with transcripts")

        # Process each asset
        for i, asset in enumerate(assets, 1):
            print(f"\n[{i}/{len(assets)}] Processing: {asset['title']}")

            summary_data = generator.generate_rich_summary(
                asset["transcript"],
                asset["title"]
            )

            if args.dry_run:
                print(f"  [DRY RUN] Would save summary:")
                print(f"    TL;DR: {summary_data['metadata']['tldr']}")
                print(f"    Key points: {len(summary_data['key_points'])}")
                print(f"    Images: {len(summary_data['metadata']['images'])}")
            else:
                db.upsert_summary(asset["id"], summary_data)
                print(f"  Saved to database!")

        print(f"\n✓ Completed processing {len(assets)} assets")

    finally:
        generator.close()


if __name__ == "__main__":
    main()
