# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Morgonpodd is an automated podcast generation service that creates daily news summaries using AI. It scrapes news from configured sources, generates summaries with OpenAI, converts text to speech with ElevenLabs, and publishes episodes via RSS feed hosted on Cloudflare R2.

## Common Development Commands

### Setup and Installation
```bash
# Initial setup
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
pip install boto3  # For Cloudflare R2
```

### Running the Service
```bash
# Generate a single episode now
python src/main.py

# Run with scheduled generation (keeps running)
python src/main.py schedule

# For automatic daily generation via cron
0 6 * * * cd /path/to/morgonpodd && venv/bin/python src/main.py
```

## Architecture

### Core Pipeline
1. **scraper.py**: Fetches content from news sources defined in sources.json
2. **summarizer.py**: Uses OpenAI GPT-4 to create podcast script from scraped content
3. **tts_generator.py**: Converts script to audio using ElevenLabs API
4. **rss_generator.py**: Creates/updates RSS feed with episode metadata
5. **cloudflare_uploader.py**: Uploads audio and feed to Cloudflare R2
6. **main.py**: Orchestrates the entire pipeline

### Data Flow
```
sources.json → scraper → scraped_content.json → summarizer → script.txt
                                                     ↓
                                              tts_generator → episode.mp3
                                                     ↓
                                              rss_generator → feed.xml
                                                     ↓
                                            cloudflare_uploader → R2 bucket
```

## Configuration

### Required Environment Variables (.env)
- `OPENAI_API_KEY`: For content summarization
- `ELEVENLABS_API_KEY`: For text-to-speech
- `ELEVENLABS_VOICE_ID`: Voice selection (default: Rachel)
- `CLOUDFLARE_ACCOUNT_ID`: R2 account
- `CLOUDFLARE_ACCESS_KEY_ID`: R2 access key
- `CLOUDFLARE_SECRET_ACCESS_KEY`: R2 secret
- `CLOUDFLARE_R2_BUCKET`: Bucket name
- `CLOUDFLARE_R2_PUBLIC_URL`: Public URL for podcast

### News Sources (sources.json)
- Configure sources with URL, CSS selector, type, and priority
- Adjust `maxItems` to control content volume per source
- Weather sources handled specially in scraper

## Key Implementation Details

### OpenAI Integration
- Model: GPT-4o for Swedish language support
- Prompt engineering in summarizer.py creates conversational podcast scripts
- Fallback script generation if API fails

### ElevenLabs Configuration
- Model: `eleven_multilingual_v2` for Swedish support
- Voice settings tuned for natural speech
- Estimates ~10,000 characters per 10-minute episode

### Cloudflare R2 Setup
- Uses boto3 S3 client with R2 endpoint
- Handles audio files, metadata, RSS feed, and static assets
- Public bucket required for podcast distribution

### RSS Feed Generation
- Uses feedgen library with podcast extension
- iTunes-compatible metadata
- Maintains last 50 episodes in feed

## Directory Structure
```
episodes/     # Generated audio files and metadata
scripts/      # Text scripts for each episode  
public/       # Static files (index.html, images)
src/          # Main application code
```

## Error Handling
- Each module has fallback mechanisms
- Comprehensive logging throughout pipeline
- Scraped content saved for debugging
- Metadata preserved at each stage