# Shiny Articles

A personal news reader with a dark UI. Pulls articles from NewsAPI based on your interests, shows a daily top story, lets you read articles in-app, and includes a NASA astronomy photo gallery.

## Features

- **Feed** — personalized article grid filtered by your chosen topics; ads and off-topic articles are stripped automatically
- **Article of the Day** — one top story from major outlets (BBC, Reuters, NYT, WSJ, Bloomberg, AP), refreshes at 5 AM daily
- **In-app reader** — click any article to read it without leaving the app; strips clutter via Mozilla Readability; "Open in browser" button always available
- **Saved Articles** — star any article to keep it; persists across restarts
- **NASA Images 📷** — last 30 days of NASA Astronomy Picture of the Day in a masonry grid; click to open a lightbox with HD image, description, and download button; results cached to survive restarts
- **Multiple API keys** — add extras so the app rotates keys when one hits its daily limit
- **27 interest topics** with smart keyword expansion (e.g. "Planes" matches aviation, aircraft, airline, airport, flight…)
- **Background service** — runs as a systemd user service; auto-starts on login

## Requirements

- Python 3.8+
- A free [NewsAPI](https://newsapi.org/register) key
- (Optional) A free [NASA API](https://api.nasa.gov) key

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Open port 3000 in your firewall (first time only)

```bash
sudo ufw allow 3000/tcp
```

### 3. Get a NewsAPI key

Sign up for free at [newsapi.org/register](https://newsapi.org/register). Free keys allow 100 requests/day.

### 4. (Optional) Get a NASA API key

Generate one at [api.nasa.gov](https://api.nasa.gov). Without it, a shared demo key is used (30 req/hour). A personal key allows 1,000 req/hour and enables the 24-hour cache to work reliably.

### 5. Run the app

```bash
./start.sh
```

Then open [http://localhost:3000](http://localhost:3000) in your browser. On first launch, paste your NewsAPI key into the setup banner and pick your interests in the Settings tab.

### Running as a background service (auto-start on login)

The app can be installed as a systemd user service so it starts automatically and runs in the background:

```bash
systemctl --user enable shiny-articles
systemctl --user start shiny-articles
```

To manage it:

```bash
systemctl --user stop shiny-articles
systemctl --user restart shiny-articles
systemctl --user status shiny-articles
```

## Configuration

All settings are stored in `config.json` (gitignored — your keys stay local). Manage everything from the **Settings** tab in the UI:

- Add/remove NewsAPI keys
- Add/remove NASA API key
- Choose from 27 interest topics

### Available interests

Technology, Science, Space, Artificial Intelligence, Climate, Health, Medicine, Politics, Business, Finance, Cryptocurrency, Sports, Gaming, Movies, Music, Art, Travel, Food, History, Philosophy, Psychology, Education, Environment, Cybersecurity, Robotics, Startups, World News, Planes

### Multiple NewsAPI keys

The free NewsAPI tier allows 100 requests/day per key. Add more than one key in Settings → Add API Key and the app automatically rotates to the next when one is exhausted.

### Rate limits at a glance

| Service | Free tier limit |
|---------|----------------|
| NewsAPI | 100 requests/day per key |
| NASA APOD | 30 req/hour (demo key) · 1,000 req/hour (personal key) |

The NASA response is cached for 24 hours and the Article of the Day is cached until 5 AM, so normal use stays well within limits.

## Tabs

| Tab | Description |
|-----|-------------|
| Feed | Personalized article grid based on your interests |
| ★ Article of the Day | Single top story, refreshes at 5 AM |
| Saved Articles | Articles you've starred |
| NASA Images 📷 | NASA Astronomy Picture of the Day gallery |
| Settings | API keys and interest selection |

## How article filtering works

When you refresh the feed, the app:

1. Builds a search query from your selected interests (e.g. `"artificial intelligence" OR "machine learning" OR "space" OR …`)
2. Fetches up to 100 recent articles from NewsAPI
3. Filters out non-English articles (heuristic: >25% non-ASCII characters)
4. Filters out ads and listicles (matches patterns like "best X of", "% off", "buy now", sponsored, etc.)
5. Filters out articles that don't mention at least one of your interest keywords in the title or description

## Project structure

```
app.py              Flask backend — API routes and filtering logic
start.sh            Convenience launcher (prints URL, runs app.py)
requirements.txt    Python dependencies
templates/
  index.html        Single-page frontend (vanilla JS, no build step)
config.json         Local config and API keys (gitignored)
nasa_cache.json     NASA response cache, refreshed every 24 h (gitignored)
```

## API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/articles` | Filtered feed based on saved interests |
| GET | `/api/article-of-day` | Today's top story (cached until 5 AM) |
| GET | `/api/read?url=…` | Fetch and extract readable article content |
| GET | `/api/nasa-pictures` | Last 30 days of NASA APOD (24 h cache) |
| GET/POST | `/api/config` | Read or update selected interests |
| POST | `/api/keys/add` | Append new NewsAPI keys |
| DELETE | `/api/keys/:idx` | Remove a NewsAPI key by index |
| POST/DELETE | `/api/nasa-key` | Set or remove the NASA API key |
| GET/POST/DELETE | `/api/saved` | List, save, or unsave articles |

## Troubleshooting

**No articles showing up**
- Check that you have at least one NewsAPI key saved in Settings
- Make sure at least one interest is selected and saved
- Your key may have hit its 100 req/day limit — add a second key in Settings

**"Could not fetch article" in the reader**
- Many sites block automated requests. Use the **Open in browser** button in the reader toolbar as a fallback.

**NASA Images tab shows an error or is empty**
- The demo key has a low rate limit (30 req/hour). Generate a free personal key at [api.nasa.gov](https://api.nasa.gov) and add it in Settings.
- NASA images are cached for 24 hours — hitting Refresh won't re-fetch until the cache expires.

**Browser shows "Access Denied" or connection refused on localhost:3000**
- Make sure the firewall allows port 3000: `sudo ufw allow 3000/tcp`
- Confirm the service is running: `systemctl --user status shiny-articles`
- If port 3000 is taken, check `lsof -i :3000` and change the port in `app.py`
