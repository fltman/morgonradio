# 🎙️ Morgonpodd - Automatiserad Svensk Podcast Generator

[![Support me on Patreon](https://img.shields.io/badge/Patreon-Support%20my%20work-FF424D?style=flat&logo=patreon&logoColor=white)](https://www.patreon.com/AndersBjarby)

En AI-driven tjänst som automatiskt genererar dagliga svenska podcast-avsnitt med två värdar, musikintegration och RSS-distribution via Cloudflare R2.

## ✨ Funktioner

- **🤖 Två AI-värdar**: Anna & Erik med naturlig konversation
- **📰 Multi-källa nyheter**: Samlar innehåll från svenska och internationella nyhetskällor
- **🎵 Musikintegration**: Automatisk intro, outro och övergångsmusik
- **🗣️ Naturligt tal**: ElevenLabs text-to-dialogue API för realistiska samtal
- **📡 RSS-distribution**: Automatisk RSS-feed generering och hosting på Cloudflare R2
- **🌤️ Väderuppdateringar**: Inkluderar lokal väderinformation
- **🎛️ Webbgränssnitt**: Streamlit-baserad kontrollpanel för konfiguration

## 📋 Förutsättningar

- Python 3.8 eller högre
- macOS, Linux eller Windows
- FFmpeg installerat (`brew install ffmpeg` på macOS)
- API-nycklar för OpenAI eller OpenRouter, och ElevenLabs
- Cloudflare-konto med R2 storage

## 🤖 AI Providers

Morgonpodd stödjer två AI-leverantörer för innehållsgenerering:

### OpenAI (Direkt API)
- **Fördelar**: Direktintegration, stabil prestanda, senaste GPT-5 modeller
- **Modeller**: 
  - **GPT-5 serien** ✨: gpt-5 (400K kontext), gpt-5-mini, gpt-5-nano
  - **GPT-4.1 serien** ✨: gpt-4.1, gpt-4.1-mini, gpt-4.1-nano (1M+ kontext!)
  - **GPT-4o serien**: gpt-4o, gpt-4o-mini, gpt-4o-audio-preview
  - **o1 reasoning**: o1-pro, o1, o1-mini (avancerad resonering)
  - **GPT-4 turbo**: gpt-4-turbo, gpt-4-turbo-preview
  - **GPT-3.5**: gpt-3.5-turbo, gpt-3.5-turbo-16k
- **Kostnad**: Betala per token direkt till OpenAI
- **Skaffa nyckel**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **OBS**: GPT-5 modeller är nu tillgängliga via OpenAI API!

### OpenRouter (Rekommenderat)
- **Fördelar**: Tillgång till 90+ AI-modeller från olika leverantörer
- **Modeller**: Claude, Gemini, Llama, GPT-4, Mistral, Command R, och många fler
- **Kostnad**: Ofta billigare än direkta API:er, betala endast för användning
- **Skaffa nyckel**: [openrouter.ai](https://openrouter.ai)

#### Populära OpenRouter-modeller för svenska poddar:
- `anthropic/claude-3.5-sonnet` - Excellant för svenska samtal
- `openai/gpt-4o-mini` - Kostnadeffektiv och snabb  
- `openai/o1-mini` - Bra för komplex resonering
- `google/gemini-pro-1.5` - Lång kontext för innehållsanalys
- `meta-llama/llama-3.1-70b-instruct` - Kraftfull open source
- `mistralai/mistral-large` - Europeisk AI med bra svenska

**Tips**: Om du har både nycklar kommer systemet automatiskt att använda OpenRouter för fler modellalternativ.

## 🚀 Installation

### 1. Klona repository

```bash
git clone https://github.com/fltman/morgonradio.git
cd morgonpodd
```

### 2. Sätt upp Python-miljö

```bash
# Skapa virtuell miljö
python3 -m venv venv

# Aktivera virtuell miljö
source venv/bin/activate  # På macOS/Linux
# eller
venv\Scripts\activate  # På Windows

# Installera beroenden
pip install -r requirements.txt
```

### 3. Konfigurera miljövariabler

Kopiera exempelfilen och redigera den:

```bash
cp .env.example .env
```

Redigera `.env` med dina API-nycklar och inställningar:

```env
# OpenAI API (Krävs) - eller använd OpenRouter nedan
OPENAI_API_KEY=din_openai_api_nyckel_här

# OpenRouter API (Alternativ till OpenAI) - ger tillgång till fler modeller
OPENROUTER_API_KEY=din_openrouter_api_nyckel_här

# ElevenLabs API (Krävs)
ELEVENLABS_API_KEY=din_elevenlabs_api_nyckel_här
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel röst, eller välj annan

# Cloudflare R2 (Krävs för publicering)
CLOUDFLARE_ACCOUNT_ID=ditt_konto_id_här
CLOUDFLARE_ACCESS_KEY_ID=din_access_key_id_här
CLOUDFLARE_SECRET_ACCESS_KEY=din_secret_access_key_här
CLOUDFLARE_R2_BUCKET=morgonpodd
CLOUDFLARE_R2_PUBLIC_URL=https://morgonpodd.din-doman.com
```

## ☁️ Cloudflare R2 Setup - Steg för steg

### Steg 1: Skapa ett Cloudflare-konto

1. Gå till [cloudflare.com](https://cloudflare.com)
2. Klicka på **"Sign Up"** och skapa ett gratis konto
3. Verifiera din e-postadress

### Steg 2: Aktivera R2 Storage

1. Logga in på din Cloudflare dashboard
2. I vänstermenyn, klicka på **"R2"**
3. Om R2 inte är aktiverat, klicka **"Enable R2"**
4. Acceptera villkoren (R2 har en generös gratis-nivå)

### Steg 3: Skapa en Bucket

1. I R2 dashboard, klicka **"Create bucket"**
2. Välj ett bucket-namn (t.ex. `morgonpodd`)
   - Måste vara globalt unikt
   - Använd endast små bokstäver, siffror och bindestreck
3. Välj en region nära din målgrupp (t.ex. "EEUR" för Europa)
4. Klicka **"Create bucket"**

### Steg 4: Gör Bucket Publik

1. Klicka på ditt bucket-namn
2. Gå till fliken **"Settings"**
3. Under **"Public Access"**, klicka **"Allow public access"**
4. Välj ett av följande alternativ:

#### Alternativ A: Använd R2 Standard URL (Utan egen domän)
Om du inte har en egen domän eller vill komma igång snabbt:
1. Efter att du aktiverat public access får du automatiskt en R2 dev URL
2. URL-formatet blir: `https://[bucket-namn].[konto-hash].r2.dev`
3. Exempel: `https://morgonpodd.abc123xyz.r2.dev`
4. Denna URL fungerar direkt utan ytterligare konfiguration
5. **Fördelar**: Ingen DNS-konfiguration krävs, fungerar omedelbart
6. **Nackdelar**: Längre och mindre minnesvärd URL

#### Alternativ B: Anslut egen domän (Rekommenderas för produktion)
Om du har en egen domän:
1. Klicka **"Connect Domain"**
2. Ange en subdomän som `podcast.dindoman.se`
3. Följ DNS-konfigurationsinstruktionerna
4. Vänta 5-10 minuter på DNS-propagering
5. **Fördelar**: Kort, professionell URL som är lätt att dela
6. **Nackdelar**: Kräver domän och DNS-konfiguration

### Steg 5: Skaffa API-uppgifter

1. Gå till **"R2"** → **"Manage R2 API tokens"**
2. Klicka **"Create API token"**
3. Konfigurera token:
   - **Token name**: `morgonpodd-token`
   - **Permissions**: Välj **"Admin Read & Write"** för Object Read & Write
   - **Specify bucket**: Välj din bucket (`morgonpodd`)
   - **TTL**: Lämna som standard eller sätt utgångsdatum
4. Klicka **"Create API Token"**
5. **VIKTIGT**: Spara dessa uppgifter omedelbart (de visas bara en gång):
   - **Access Key ID** → Kopiera till `CLOUDFLARE_ACCESS_KEY_ID`
   - **Secret Access Key** → Kopiera till `CLOUDFLARE_SECRET_ACCESS_KEY`
   - **Account ID** (visas i URL eller R2 dashboard) → Kopiera till `CLOUDFLARE_ACCOUNT_ID`

### Steg 6: Notera din publika URL

**För Alternativ A (R2 Standard URL):**
1. Gå till din bucket i Cloudflare dashboard
2. Under fliken "Settings" hittar du din dev URL
3. Kopiera URL:en som ser ut som: `https://morgonpodd.abc123xyz.r2.dev`
4. Lägg till denna i `.env` som `CLOUDFLARE_R2_PUBLIC_URL=https://morgonpodd.abc123xyz.r2.dev`

**För Alternativ B (Egen domän):**
1. Använd din anpassade URL: `https://podcast.dindoman.se`
2. Lägg till denna i `.env` som `CLOUDFLARE_R2_PUBLIC_URL=https://podcast.dindoman.se`

**Viktigt att komma ihåg:**
- R2 dev URL:er ändras aldrig och fungerar direkt
- De är säkra att använda för produktion
- Din podcast kommer vara tillgänglig på `[din-url]/feed.xml`

## 🎯 Användning

### Generera ett enskilt avsnitt

```bash
python src/main.py
```

### Kör på schema (Dagligen kl 06:00)

```bash
python src/main.py schedule
```

### Webbgränssnitt

```bash
streamlit run src/enhanced_gui.py --server.port 8504
```

Öppna sedan http://localhost:8504 i din webbläsare.

### Sätt upp automatisk daglig generering (Cron)

```bash
# Redigera crontab
crontab -e

# Lägg till denna rad för daglig generering kl 06:00
0 6 * * * cd /sökväg/till/morgonpodd && /sökväg/till/venv/bin/python src/main.py
```

## 📁 Projektstruktur

```
morgonpodd/
├── src/
│   ├── main.py              # Huvudorkestrator
│   ├── scraper.py           # Nyhetsscraper
│   ├── summarizer.py        # AI-skriptgenerator
│   ├── tts_generator.py     # Text-till-tal med ElevenLabs
│   ├── rss_generator.py     # RSS-feed skapare
│   ├── cloudflare_uploader.py # R2 upload-hanterare
│   ├── music_library.py     # Musikhantering
│   └── enhanced_gui.py      # Webbgränssnitt
├── sources.json             # Nyhetskällor konfiguration
├── episodes/                # Genererade ljudfiler
├── scripts/                 # Genererade textskript
├── music/                   # Musikbibliotek
└── public/                  # Statiska filer (RSS, bilder)
```

## ⚙️ Konfiguration

### Nyhetskällor

Du kan hantera nyhetskällor på två sätt:

**Via webbgränssnittet (rekommenderas):**
1. Starta GUI:n: `streamlit run src/enhanced_gui.py --server.port 8504`
2. Gå till fliken "News Sources"
3. Lägg till, redigera eller ta bort källor med grafiskt gränssnitt
4. Testa källor direkt för att verifiera att de fungerar

**Via manuell redigering av sources.json:**
```json
{
  "sources": [
    {
      "name": "SVT Nyheter",
      "url": "https://www.svt.se/nyheter/rss.xml",
      "type": "news",
      "format": "rss",
      "maxItems": 5,
      "enabled": true
    }
  ]
}
```

### Podcast-värdar

Du kan konfigurera värdpersonligheter på två sätt:

**Via webbgränssnittet:**
1. Gå till fliken "Podcast Settings" i GUI:n
2. Redigera värdpersonligheter och röstinställningar
3. Ändringarna sparas automatiskt

**Via manuell redigering av sources.json:**

```json
{
  "podcastSettings": {
    "hosts": [
      {
        "name": "Anna",
        "voice_id": "xc1ryI9pRbBLNr6aTJET",
        "personality": "Energisk och positiv morgonvärd",
        "style": "konversationell och varm"
      },
      {
        "name": "Erik",
        "voice_id": "iwNZQzqCFIBqLR6sgFpN",
        "personality": "Analytisk och noggrann, teknikspecialist",
        "style": "informativ men lättsam"
      }
    ]
  }
}
```

## 🎵 Lägga till musik

**Via webbgränssnittet (rekommenderas):**
1. Gå till fliken "Music Library" i GUI:n
2. Ladda upp MP3-filer direkt via gränssnittet
3. Organisera musik i kategorier (intro, outro, transition)
4. Förhandsgranska och hantera musikbiblioteket

**Manuellt:**
1. Placera MP3-filer i `music/` katalogen
2. Organisera efter kategori:
   - `music/intro/` - Öppningsmusik
   - `music/outro/` - Avslutningsmusik
   - `music/transition/` - Mellan segment
3. Uppdatera `music_library.json` eller använd webbgränssnittet

## 📱 Prenumerera på din podcast

När den är publicerad kommer din podcast finnas tillgänglig på:
- **RSS Feed**: `https://din-doman.com/feed.xml`
- **Webbspelare**: `https://din-doman.com/`

Lägg till i podcast-appar:
- **Apple Podcasts**: Sök → Lägg till via URL → Klistra in RSS URL
- **Spotify**: Skicka in via Spotify for Podcasters
- **Google Podcasts**: Inställningar → Lägg till via RSS
- **Overcast/Pocket Casts**: Lägg till → Lägg till via URL

## 🔧 Felsökning

### Vanliga problem

**FFmpeg-fel under ljudbearbetning:**
```bash
# Se till att FFmpeg är installerat
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Ubuntu/Debian
```

**Saknade chunks i slutgiltigt avsnitt:**
- Kontrollera `episodes/debug_chunks_*/` för alla chunk-filer
- Verifiera musikpositioner i loggar
- Se till att `maxCharsPerChunk` är satt till 1500 i `sources.json`

**API-hastighetsbegränsningar:**
- OpenAI: Implementera fördröjningar mellan förfrågningar
- ElevenLabs: Kontrollera din plans teckengränser

**Cloudflare R2 uppladdningsfel:**
- Verifiera att bucket existerar och är publik
- Kontrollera att API-uppgifterna är korrekta
- Se till att bucket-namnet matchar i `.env`

### Debug-läge

Visa detaljerade loggar:
```bash
python src/main.py 2>&1 | tee debug.log
```

## 📊 Övervakning

- **Avsnitt**: Kontrollera `episodes/` katalogen
- **Skript**: Granska `scripts/` för genererat innehåll
- **Loggar**: Övervaka konsoloutput eller loggfiler
- **RSS Feed**: Verifiera på `[publik-url]/feed.xml`

## 🤝 Bidra

1. Forka repository
2. Skapa en feature-branch
3. Gör dina ändringar
4. Testa noggrant
5. Skicka in en pull request

## 📄 Licens

MIT License - Se LICENSE-filen för detaljer

## 🙏 Tack till

- **OpenAI GPT-4** - Innehållsgenerering
- **ElevenLabs** - Text-till-tal
- **Cloudflare R2** - Lagring och distribution
- **Streamlit** - Webbgränssnitt

## 📞 Support

- GitHub Issues: [github.com/fltman/morgonradio/issues](https://github.com/fltman/morgonradio/issues)
- Dokumentation: Se `/docs` mappen

## 💡 Tips

### Optimera för svenska lyssnare
- Använd svenska nyhetskällor primärt
- Anpassa genererings-tid till svensk morgon (06:00 CET)
- Inkludera svensk väderinformation

### Kostnadsoptimering
- Begränsa antal nyhetskällor för att minska API-kostnader
- Använd kortare sammanfattningar (justera i `sources.json`)
- Övervaka ElevenLabs teckenanvändning

### Förbättra innehållet
- Experimentera med olika värdpersonligheter
- Lägg till lokal musik för unik känsla
- Anpassa prompt-mallar för din målgrupp

---

Skapad med ❤️ för automatiserad svensk podcast-produktion