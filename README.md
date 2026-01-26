# NotebookLM Study Hub

A web app for studying with AI-generated study guides and quizzes from NotebookLM audio overviews.

## Features

- **Study Guides**: Article-style content that teaches you the topic directly (not meta summaries about what "the hosts discussed")
- **Embedded Images**: Visual references from Wikimedia Commons for people, places, artworks, and concepts
- **Key Takeaways**: Quick bullet points to refresh your memory
- **Resource Links**: Wikipedia articles and search links for further learning
- **Quizzes**: Test your knowledge with interactive quizzes
- **Progress Tracking**: Your quiz scores are saved locally
- **Dark Theme**: Easy on the eyes for late-night study sessions

## Architecture

```
NotebookLM Audio Overviews
         ↓ (Whisper transcription)
     Transcripts
         ↓ (regenerate_summaries.py - GPT-4o)
Study Guides + Images + Quizzes
         ↓
     Supabase DB
         ↓
    This Web App
```

## Study Guide Format

Study guides are generated in **article format**, not as meta-summaries:

❌ **Old format**: "The hosts discuss the Palace of Versailles and talk about its history..."

✅ **New format**: "The Palace of Versailles stands as one of the most magnificent royal residences ever constructed. Built during the reign of Louis XIV..."

Each study guide includes:
- **TL;DR**: One-sentence summary of the key insight
- **Article Content**: Full educational content with headers and formatting
- **Visual References**: Embedded images from Wikimedia Commons
- **Key Takeaways**: Bullet points for quick review
- **Learn More**: Links to Wikipedia and Google for further research
- **Quiz Button**: Direct link to test your knowledge

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS (single file)
- **Backend**: Supabase (PostgreSQL + REST API)
- **AI**: GPT-4o for article generation, GPT-4o-mini for extraction
- **Images**: Wikimedia Commons API
- **Hosting**: Netlify

## Local Development

Simply open `index.html` in a browser. The app connects to Supabase directly.

## Regenerating Summaries

To regenerate summaries in the new article format:

```bash
cd scraper

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-service-role-key"  # Not anon key!
export OPENAI_API_KEY="your-openai-key"

# Regenerate all summaries
python regenerate_summaries.py --all

# Or regenerate a specific asset
python regenerate_summaries.py --asset-id "uuid-here"

# Dry run (no database changes)
python regenerate_summaries.py --all --dry-run
```

## Deployment

Deployed to Netlify. Push to main to auto-deploy.

## Database Tables

| Table | Purpose |
|-------|---------|
| `notebooklm_notebooks` | Notebook metadata |
| `notebooklm_assets` | Audio overviews, quizzes, flashcards |
| `notebooklm_transcripts` | Full text transcripts |
| `notebooklm_summaries` | AI summaries (standard, TLDR, rich) |
| `notebooklm_quizzes` | Quiz questions with explanations |

### Rich Summary Metadata Schema

```json
{
  "tldr": "One sentence summary",
  "images": [
    {
      "term": "Palace of Versailles",
      "url": "https://upload.wikimedia.org/...",
      "thumb_url": "https://upload.wikimedia.org/.../800px-...",
      "caption": "The palace from the gardens",
      "attribution": "Author Name (CC BY-SA 4.0)"
    }
  ],
  "resources": {
    "wikipedia_articles": ["Palace of Versailles", "Louis XIV"],
    "search_queries": ["Versailles gardens", "Hall of Mirrors"]
  },
  "claude_reference": {
    "topics_covered": ["Versailles", "Louis XIV", "French Architecture"]
  }
}
```

## Related

- **Supabase Project**: `ydwjzlikslebokuxzwco`
