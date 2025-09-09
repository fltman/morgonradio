import streamlit as st
import json
import os
import asyncio
from datetime import datetime
import subprocess
import sys
from pathlib import Path

# Import our modules
from main import MorgonPoddService
from scraper import NewsScraper

st.set_page_config(
    page_title="Morgonpodd Control Panel",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_config():
    """Load current configuration"""
    if os.path.exists('sources.json'):
        with open('sources.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration"""
    with open('sources.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_env():
    """Load environment variables"""
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

def save_env(env_vars):
    """Save environment variables"""
    with open('.env', 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

def main():
    st.title("🎙️ Morgonpodd Control Panel")
    st.markdown("---")
    
    # Load current config
    config = load_config()
    env_vars = load_env()
    
    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox("Choose page", [
            "Dashboard", 
            "Podcast Settings", 
            "News Sources", 
            "API Keys", 
            "Generate Episode"
        ])
    
    if page == "Dashboard":
        show_dashboard(config)
    elif page == "Podcast Settings":
        show_podcast_settings(config)
    elif page == "News Sources":
        show_news_sources(config)
    elif page == "API Keys":
        show_api_keys(env_vars)
    elif page == "Generate Episode":
        show_generate_episode()

def show_dashboard(config):
    st.header("📊 Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Sources Configured", len(config.get('sources', [])))
    
    with col2:
        episodes_dir = Path('episodes')
        episode_count = len(list(episodes_dir.glob('*.mp3'))) if episodes_dir.exists() else 0
        st.metric("Episodes Generated", episode_count)
    
    with col3:
        last_generated = "Never"
        if episodes_dir.exists():
            episodes = list(episodes_dir.glob('*.mp3'))
            if episodes:
                latest = max(episodes, key=lambda x: x.stat().st_mtime)
                last_generated = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        st.metric("Last Generated", last_generated)
    
    # Recent episodes
    st.subheader("Recent Episodes")
    if episodes_dir.exists():
        episodes = sorted(episodes_dir.glob('*.mp3'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        for episode in episodes:
            with st.expander(f"🎵 {episode.stem}"):
                st.text(f"Size: {episode.stat().st_size / 1024 / 1024:.1f} MB")
                st.text(f"Created: {datetime.fromtimestamp(episode.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Audio player
                with open(episode, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/mp3')

def show_podcast_settings(config):
    st.header("🎙️ Podcast Settings")
    
    # Initialize podcast settings if not exists
    if 'podcastSettings' not in config:
        config['podcastSettings'] = {
            'title': 'Min Morgonpodd',
            'description': 'Din dagliga sammanfattning av nyheter, teknik och väder',
            'author': 'Morgonpodd AI',
            'language': 'sv-SE'
        }
    
    # Initialize hosts if not exists
    if 'hosts' not in config['podcastSettings']:
        config['podcastSettings']['hosts'] = [
            {
                'name': 'Anna',
                'voice_id': '21m00Tcm4TlvDq8ikWAM',  # Rachel
                'personality': 'Energisk och positiv morgonvärd som älskar nyheter',
                'style': 'konversationell och varm'
            },
            {
                'name': 'Erik',
                'voice_id': 'pNInz6obpgDQGcFmaJgB',  # Adam
                'personality': 'Analytisk och noggrann, specialist på teknik och ekonomi',
                'style': 'informativ men lättsam'
            }
        ]
    
    settings = config['podcastSettings']
    
    # Basic settings
    st.subheader("Basic Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        settings['title'] = st.text_input("Podcast Title", value=settings.get('title', 'Min Morgonpodd'))
        settings['author'] = st.text_input("Author", value=settings.get('author', 'Morgonpodd AI'))
        settings['language'] = st.selectbox("Language", ['sv-SE', 'en-US'], 
                                          index=0 if settings.get('language') == 'sv-SE' else 1)
    
    with col2:
        settings['description'] = st.text_area("Description", 
                                             value=settings.get('description', 'Din dagliga sammanfattning'))
        settings['generateTime'] = st.time_input("Generate Time", 
                                                value=datetime.strptime(settings.get('generateTime', '06:00'), '%H:%M').time())
        settings['maxDuration'] = st.slider("Max Duration (seconds)", 300, 1200, 
                                           value=settings.get('maxDuration', 600))
    
    # Hosts configuration
    st.subheader("🎭 Hosts Configuration")
    
    hosts = settings['hosts']
    
    for i, host in enumerate(hosts):
        with st.expander(f"Host {i+1}: {host['name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                host['name'] = st.text_input(f"Name", value=host['name'], key=f"host_{i}_name")
                host['voice_id'] = st.text_input(f"ElevenLabs Voice ID", value=host['voice_id'], key=f"host_{i}_voice")
            
            with col2:
                host['personality'] = st.text_area(f"Personality", value=host['personality'], key=f"host_{i}_personality")
                host['style'] = st.text_input(f"Speaking Style", value=host['style'], key=f"host_{i}_style")
    
    # Prompt templates
    st.subheader("📝 Prompt Templates")
    
    if 'promptTemplates' not in settings:
        settings['promptTemplates'] = {
            'main_prompt': """Du är {host1_name} och {host2_name}, två professionella poddvärdar som skapar engagerande morgonpoddar på svenska.

{host1_name}: {host1_personality}. Stil: {host1_style}
{host2_name}: {host2_personality}. Stil: {host2_style}

Skapa ett naturligt samtal mellan er två baserat på dagens innehåll. Låt er komplementera varandra och ha en naturlig dialog.""",
            'conversation_style': 'natural_dialogue'
        }
    
    prompt_templates = settings['promptTemplates']
    
    prompt_templates['main_prompt'] = st.text_area(
        "Main Prompt Template", 
        value=prompt_templates.get('main_prompt', ''),
        height=200,
        help="Use {host1_name}, {host2_name}, etc. as placeholders"
    )
    
    prompt_templates['conversation_style'] = st.selectbox(
        "Conversation Style",
        ['natural_dialogue', 'interview_style', 'news_anchor', 'casual_chat'],
        index=['natural_dialogue', 'interview_style', 'news_anchor', 'casual_chat'].index(
            prompt_templates.get('conversation_style', 'natural_dialogue')
        )
    )
    
    # Save button
    if st.button("💾 Save Podcast Settings", type="primary"):
        # Convert time to string
        settings['generateTime'] = settings['generateTime'].strftime('%H:%M')
        config['podcastSettings'] = settings
        save_config(config)
        st.success("Settings saved successfully!")
        st.rerun()

def show_news_sources(config):
    st.header("📰 News Sources")
    
    if 'sources' not in config:
        config['sources'] = []
    
    sources = config['sources']
    
    # Add new source
    with st.expander("➕ Add New Source"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("Source Name")
            new_url = st.text_input("URL")
            new_type = st.selectbox("Type", ['news', 'tech', 'weather', 'sports'])
        
        with col2:
            new_selector = st.text_input("CSS Selector", placeholder="e.g., article h2")
            new_priority = st.slider("Priority", 1, 5, 3)
            new_max_items = st.slider("Max Items", 1, 20, 5)
        
        if st.button("Add Source") and new_name and new_url:
            new_source = {
                'name': new_name,
                'url': new_url,
                'type': new_type,
                'selector': new_selector,
                'priority': new_priority,
                'maxItems': new_max_items
            }
            sources.append(new_source)
            save_config(config)
            st.success(f"Added source: {new_name}")
            st.rerun()
    
    # Existing sources
    st.subheader("Configured Sources")
    
    for i, source in enumerate(sources):
        with st.expander(f"📰 {source['name']} ({source['type']})"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                source['name'] = st.text_input("Name", value=source['name'], key=f"src_{i}_name")
                source['url'] = st.text_input("URL", value=source['url'], key=f"src_{i}_url")
                source['selector'] = st.text_input("CSS Selector", value=source.get('selector', ''), key=f"src_{i}_sel")
            
            with col2:
                source['type'] = st.selectbox("Type", ['news', 'tech', 'weather', 'sports'], 
                                            index=['news', 'tech', 'weather', 'sports'].index(source['type']), 
                                            key=f"src_{i}_type")
                source['priority'] = st.slider("Priority", 1, 5, value=source.get('priority', 3), key=f"src_{i}_pri")
                source['maxItems'] = st.slider("Max Items", 1, 20, value=source.get('maxItems', 5), key=f"src_{i}_max")
            
            with col3:
                st.write("")
                st.write("")
                if st.button("🗑️ Delete", key=f"del_{i}"):
                    sources.pop(i)
                    save_config(config)
                    st.rerun()
                
                if st.button("🧪 Test", key=f"test_{i}"):
                    with st.spinner("Testing source..."):
                        # Test the source
                        test_result = test_source(source)
                        if test_result:
                            st.success(f"✅ Found {len(test_result)} items")
                            for item in test_result[:3]:
                                st.write(f"- {item}")
                        else:
                            st.error("❌ No items found")
    
    # Save button
    if st.button("💾 Save Sources", type="primary"):
        save_config(config)
        st.success("Sources saved successfully!")

def show_api_keys(env_vars):
    st.header("🔑 API Keys")
    
    st.warning("⚠️ Keep your API keys secure! Never share them publicly.")
    
    # OpenAI
    with st.expander("OpenAI Settings"):
        env_vars['OPENAI_API_KEY'] = st.text_input(
            "OpenAI API Key", 
            value=env_vars.get('OPENAI_API_KEY', ''),
            type="password",
            help="Get from https://platform.openai.com/api-keys"
        )
    
    # ElevenLabs
    with st.expander("ElevenLabs Settings"):
        env_vars['ELEVENLABS_API_KEY'] = st.text_input(
            "ElevenLabs API Key",
            value=env_vars.get('ELEVENLABS_API_KEY', ''),
            type="password",
            help="Get from https://elevenlabs.io"
        )
        env_vars['ELEVENLABS_VOICE_ID'] = st.text_input(
            "Default Voice ID",
            value=env_vars.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM'),
            help="Voice ID from ElevenLabs"
        )
    
    # Cloudflare R2
    with st.expander("Cloudflare R2 Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            env_vars['CLOUDFLARE_ACCOUNT_ID'] = st.text_input(
                "Account ID", 
                value=env_vars.get('CLOUDFLARE_ACCOUNT_ID', ''),
                type="password"
            )
            env_vars['CLOUDFLARE_ACCESS_KEY_ID'] = st.text_input(
                "Access Key ID", 
                value=env_vars.get('CLOUDFLARE_ACCESS_KEY_ID', ''),
                type="password"
            )
        
        with col2:
            env_vars['CLOUDFLARE_SECRET_ACCESS_KEY'] = st.text_input(
                "Secret Access Key", 
                value=env_vars.get('CLOUDFLARE_SECRET_ACCESS_KEY', ''),
                type="password"
            )
            env_vars['CLOUDFLARE_R2_BUCKET'] = st.text_input(
                "Bucket Name", 
                value=env_vars.get('CLOUDFLARE_R2_BUCKET', 'morgonpodd')
            )
        
        env_vars['CLOUDFLARE_R2_PUBLIC_URL'] = st.text_input(
            "Public URL", 
            value=env_vars.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://morgonpodd.example.com'),
            help="Your custom domain for the R2 bucket"
        )
    
    # Save button
    if st.button("💾 Save API Keys", type="primary"):
        save_env(env_vars)
        st.success("API keys saved successfully!")

def show_generate_episode():
    st.header("🎬 Generate Episode")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Quick Generation")
        
        if st.button("🚀 Generate Now", type="primary", use_container_width=True):
            with st.spinner("Generating episode... This may take a few minutes."):
                try:
                    # Run the podcast generation
                    result = subprocess.run([
                        sys.executable, 'src/main.py'
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        st.success("✅ Episode generated successfully!")
                        st.code(result.stdout)
                    else:
                        st.error("❌ Generation failed!")
                        st.code(result.stderr)
                        
                except subprocess.TimeoutExpired:
                    st.error("⏱️ Generation timed out after 5 minutes")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with col2:
        st.subheader("Generation Log")
        
        # Show recent logs if available
        log_files = list(Path('logs').glob('*.log')) if Path('logs').exists() else []
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            with open(latest_log, 'r') as f:
                st.text_area("Recent Log", value=f.read(), height=300)

@st.cache_data
def test_source(source):
    """Test a news source"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(source['url'], timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        elements = soup.select(source.get('selector', 'h2'))[:3]
        return [elem.get_text(strip=True) for elem in elements if elem.get_text(strip=True)]
    except Exception as e:
        st.error(f"Error testing source: {e}")
        return []

if __name__ == "__main__":
    main()