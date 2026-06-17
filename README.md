# Shiny Articles

A personal news reader with a dark UI. Pulls articles from NewsAPI based on your interests, shows a daily top story, and includes a NASA astronomy photo gallery.

## Features

- **Feed** — personalized article grid filtered by topic interests
- **Article of the Day** — one top story from major outlets, refreshes at 5 AM daily
- **Built-in reader** — strips paywalls/clutter and renders articles in-app
- **Saved Articles** — star any article to keep it
- **NASA Images** — last 30 days of NASA Astronomy Picture of the Day, with lightbox viewer
- **Multiple API keys** — add extras so the app rotates keys when one hits its daily limit

## Requirements

- Python 3.8+
- A free [NewsAPI](https://newsapi.org/register) key
- (Optional) A free [NASA API](https://api.nasa.gov) key

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a NewsAPI key

Sign up for free at [newsapi.org/register](https://newsapi.org/register). Free keys allow 100 requests/day.

### 3. (Optional) Get a NASA API key

Generate one at [api.nasa.gov](https://api.nasa.gov). Without it, a shared demo key is used (limited to 30 req/hour).

### 4. Run the app

```bash
./start.sh
```

Then open [http://localhost:3000](http://localhost:3000) in your browser. On first launch, paste your NewsAPI key into the setup banner and pick your interests.

## Configuration

All settings are stored in `config.json` (gitignored — your keys stay local). You can manage everything from the **Settings** tab in the UI:

- Add/remove NewsAPI keys
- Add/remove NASA API key
- Choose from 27 interest topics

### Available interests

Technology, Science, Space, Artificial Intelligence, Climate, Health, Medicine, Politics, Business, Finance, Cryptocurrency, Sports, Gaming, Movies, Music, Art, Travel, Food, History, Philosophy, Psychology, Education, Environment, Cybersecurity, Robotics, Startups, World News, Planes

### Multiple NewsAPI keys

The free NewsAPI tier allows 100 requests/day per key. If you add more than one key (Settings → Add API Key), the app automatically rotates to the next key when one is exhausted. Useful if you check the feed frequently throughout the day.

### Rate limits at a glance

| Service | Free tier limit |
|---------|----------------|
| NewsAPI | 100 requests/day per key |
| NASA APOD | 30 req/hour (demo key) · 1000 req/hour (personal key) |

The NASA response is cached for 24 hours and the Article of the Day is cached until 5 AM, so normal use stays well within limits.

## How article filtering works

When you refresh the feed, the app:

1. Builds a search query from your selected interests (e.g. `"artificial intelligence" OR "machine learning" OR "space" OR …`)
2. Fetches up to 100 recent articles from NewsAPI
3. Filters out non-English articles (heuristic: >25% non-ASCII characters)
4. Filters out ads and listicles (matches patterns like "best X of", "% off", "buy now", sponsored, etc.)
5. Filters out articles that don't mention at least one of your interest keywords in the title or description

## Project structure

```
app.py            Flask backend — API routes and filtering logic
start.sh          Convenience launcher
requirements.txt  Python dependencies
templates/
  index.html      Single-page frontend (vanilla JS, no build step)
config.json       Local config and API keys (gitignored)
nasa_cache.json   NASA response cache, refreshed every 24 h (gitignored)
```

## API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/articles` | Filtered feed based on saved interests |
| GET | `/api/article-of-day` | Today's top story (cached until 5 AM) |
| GET | `/api/read?url=…` | Fetch and extract readable content from a URL |
| GET | `/api/nasa-pictures` | Last 30 days of NASA APOD (24 h cache) |
| GET/POST | `/api/config` | Read or update selected interests |
| POST | `/api/keys/add` | Add new NewsAPI keys |
| DELETE | `/api/keys/:idx` | Remove a NewsAPI key by index |
| POST/DELETE | `/api/nasa-key` | Set or remove the NASA API key |
| GET/POST/DELETE | `/api/saved` | List, save, or unsave articles |

## Troubleshooting

**No articles showing up**
- Check that you have at least one NewsAPI key saved in Settings
- Make sure at least one interest is selected
- Your key may have hit its 100 req/day limit — add a second key in Settings

**"Could not fetch article" in the reader**
- Many sites block automated requests. Use the "Open in browser" button in the reader toolbar as a fallback.

**NASA Images tab is empty or shows an error**
- The demo key has a low rate limit (30 req/hour). If you're hitting it, generate a free personal key at [api.nasa.gov](https://api.nasa.gov) and add it in Settings.
- NASA responses are cached for 24 hours, so hitting Refresh repeatedly won't help if the cache is still fresh.

**App won't start**
- Make sure dependencies are installed: `pip install -r requirements.txt`
- Check that port 3000 isn't already in use: `lsof -i :3000`
