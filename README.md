# Shiny Articles

A personal news reader with a dark UI. Pulls articles from NewsAPI based on your interests, shows a daily top story, and includes a NASA astronomy photo gallery.

## Features

- **Feed** — personalized article grid filtered by topic interests
- **Article of the Day** — one top story from major outlets, refreshes at 5 AM daily
- **Built-in reader** — strips paywalls/clutter and renders articles in-app
- **Saved Articles** — star any article to keep it
- **NASA Images** — last 30 days of NASA Astronomy Picture of the Day, with lightbox viewer
- **Multiple API keys** — add extras so the app rotates keys when one hits its daily limit

## Setup

### 1. Install dependencies

```bash
pip install flask requests readability-lxml
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
- Choose interests from 27 topics (Technology, Space, AI, Gaming, Planes, and more)

## Project structure

```
app.py          Flask backend — API routes and filtering logic
start.sh        Convenience launcher
templates/
  index.html    Single-page frontend (vanilla JS, no build step)
config.json     Local config and API keys (gitignored)
nasa_cache.json NASA response cache, refreshed every 24 h (gitignored)
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
