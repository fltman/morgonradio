#!/bin/bash

echo "🎙️ Setting up Morgonpodd..."

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install boto3 for Cloudflare R2
pip install boto3

# Create necessary directories
echo "Creating directories..."
mkdir -p episodes
mkdir -p scripts
mkdir -p public
mkdir -p logs

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys"
fi

# Create default images if they don't exist
if [ ! -f public/cover.jpg ]; then
    echo "Creating placeholder cover image..."
    # Create a simple placeholder using ImageMagick if available
    if command -v convert &> /dev/null; then
        convert -size 1400x1400 xc:skyblue \
                -gravity center -pointsize 100 \
                -annotate +0+0 'Morgonpodd' \
                public/cover.jpg
    else
        echo "Please add a cover.jpg (1400x1400px) to the public/ directory"
    fi
fi

if [ ! -f public/logo.png ]; then
    echo "Creating placeholder logo..."
    if command -v convert &> /dev/null; then
        convert -size 512x512 xc:skyblue \
                -gravity center -pointsize 60 \
                -annotate +0+0 'MP' \
                public/logo.png
    else
        echo "Please add a logo.png (512x512px) to the public/ directory"
    fi
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys:"
echo "   - OpenAI API key"
echo "   - ElevenLabs API key"
echo "   - Cloudflare R2 credentials"
echo ""
echo "2. Customize sources.json with your preferred news sources"
echo ""
echo "3. Run the service:"
echo "   - Generate one episode: python src/main.py"
echo "   - Run on schedule: python src/main.py schedule"
echo ""
echo "4. For automatic daily generation, add to crontab:"
echo "   0 6 * * * cd $(pwd) && venv/bin/python src/main.py"