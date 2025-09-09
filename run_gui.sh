#!/bin/bash

echo "🎙️ Starting Morgonpodd GUI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install Streamlit if not already installed
pip install streamlit pytz

# Check if required files exist
if [ ! -f "sources.json" ]; then
    echo "⚠️  sources.json not found, creating default configuration..."
    cat > sources.json << 'EOF'
{
  "sources": [
    {
      "name": "SVT Nyheter",
      "url": "https://www.svt.se/nyheter/",
      "type": "news",
      "selector": "article h2",
      "priority": 1,
      "maxItems": 5
    },
    {
      "name": "DN",
      "url": "https://www.dn.se/",
      "type": "news", 
      "selector": "article h2",
      "priority": 1,
      "maxItems": 3
    }
  ],
  "podcastSettings": {
    "title": "Morgonpodd",
    "description": "Din dagliga sammanfattning av nyheter",
    "author": "AI Podcast",
    "language": "sv-SE",
    "generateTime": "06:00",
    "maxDuration": 600,
    "hosts": [
      {
        "name": "Anna",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "personality": "Energisk och positiv morgonvärd som älskar nyheter",
        "style": "konversationell och varm"
      },
      {
        "name": "Erik", 
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "personality": "Analytisk och noggrann, specialist på teknik och ekonomi",
        "style": "informativ men lättsam"
      }
    ],
    "promptTemplates": {
      "main_prompt": "Du skapar ett naturligt samtal mellan {host1_name} och {host2_name}, två professionella poddvärdar.\n\n{host1_name}: {host1_personality}\n{host2_name}: {host2_personality}\n\nSkapa ett engagerande samtal där värdarna diskuterar dagens nyheter på ett naturligt sätt.",
      "conversation_style": "natural_dialogue"
    }
  }
}
EOF
fi

if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found, copying from template..."
    cp .env.example .env
    echo "Please edit .env with your API keys before using the service."
fi

# Start Streamlit GUI
echo "🚀 Starting GUI on http://localhost:8501"
streamlit run src/gui_app.py --server.port 8501

echo "GUI closed."