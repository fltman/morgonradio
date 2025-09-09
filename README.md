# Morgonpodd 🎙️

En automatiserad podcast-tjänst som skapar dagliga nyhetssammanfattningar med AI och text-till-tal.

## Funktioner

- 🔍 **Automatisk innehållsinhämtning** från flera nyhetskällor
- 🤖 **AI-driven sammanfattning** med OpenAI GPT-4
- 🗣️ **Naturlig röstsyntes** med ElevenLabs
- 📡 **RSS-feed** för podcastappar
- ☁️ **Cloudflare R2** för hosting
- ⏰ **Schemalagd generering** varje morgon

## Installation

### 1. Klona projektet och installera

```bash
# Kör setup-scriptet
chmod +x setup.sh
./setup.sh
```

### 2. Konfigurera API-nycklar

Redigera `.env` med dina nycklar:

```env
# OpenAI för sammanfattning
OPENAI_API_KEY=sk-...

# ElevenLabs för röstsyntes
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Cloudflare R2
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_ACCESS_KEY_ID=...
CLOUDFLARE_SECRET_ACCESS_KEY=...
CLOUDFLARE_R2_BUCKET=morgonpodd
CLOUDFLARE_R2_PUBLIC_URL=https://morgonpodd.din-doman.com
```

### 3. Anpassa källor

Redigera `sources.json` för att välja nyhetskällor:

```json
{
  "sources": [
    {
      "name": "SVT Nyheter",
      "url": "https://www.svt.se/nyheter/",
      "type": "news",
      "selector": "article h2",
      "maxItems": 5
    }
  ]
}
```

## Användning

### Generera ett avsnitt

```bash
# Aktivera virtual environment
source venv/bin/activate

# Generera ett avsnitt
python src/main.py
```

### Kör på schema

```bash
# Kör tjänsten med schemaläggning
python src/main.py schedule
```

### Automatisk körning med cron

Lägg till i crontab för daglig generering kl 06:00:

```bash
crontab -e

# Lägg till:
0 6 * * * cd /path/to/morgonpodd && venv/bin/python src/main.py
```

## Cloudflare R2 Setup

1. Skapa ett R2-bucket i Cloudflare Dashboard
2. Aktivera public access för bucket
3. Konfigurera en custom domain
4. Skapa API-tokens med R2 read/write permissions
5. Uppdatera `.env` med dina credentials

## Struktur

```
morgonpodd/
├── src/
│   ├── scraper.py         # Innehållsinhämtning
│   ├── summarizer.py      # AI-sammanfattning
│   ├── tts_generator.py   # Röstgenerering
│   ├── rss_generator.py   # RSS-feed
│   ├── cloudflare_uploader.py  # Upload till R2
│   └── main.py           # Huvudprogram
├── episodes/             # Genererade avsnitt
├── scripts/             # Podcast-manus
├── public/              # Statiska filer
├── sources.json         # Konfiguration
└── .env                # API-nycklar
```

## API-kostnader

- **OpenAI**: ~$0.01-0.02 per avsnitt
- **ElevenLabs**: ~10,000 tecken per avsnitt
- **Cloudflare R2**: Gratis för små volymer

## RSS-feed

Podden blir tillgänglig på:
- RSS: `https://din-doman.com/feed.xml`
- Webbsida: `https://din-doman.com`

Prenumerera i valfri poddapp genom att lägga till RSS-länken.

## Felsökning

### Problem med scraping
- Kontrollera att CSS-selektorerna i `sources.json` stämmer
- Vissa sajter kan kräva Selenium istället för requests

### Audio-generering misslyckas
- Verifiera ElevenLabs API-nyckel och voice ID
- Kontrollera att du har krediter kvar

### Upload misslyckas
- Verifiera Cloudflare R2 credentials
- Kontrollera bucket-namnet och permissions

## Licens

MIT