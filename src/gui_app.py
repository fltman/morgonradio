import streamlit as st
import json
import os
import asyncio
from datetime import datetime
import subprocess
import sys
from pathlib import Path

# Import our modules
try:
    from main import MorgonPoddService
    from scraper import NewsScraper
except ImportError as e:
    # Handle missing dependencies gracefully
    MorgonPoddService = None
    NewsScraper = None
    st.warning(f"Some features unavailable due to missing dependencies. Install requirements to enable full functionality.")

from music_library import MusicLibrary

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
            "Music Library",
            "API Keys", 
            "Generate Episode"
        ])
    
    if page == "Dashboard":
        show_dashboard(config)
    elif page == "Podcast Settings":
        show_podcast_settings(config)
    elif page == "News Sources":
        show_news_sources(config)
    elif page == "Music Library":
        show_music_library()
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
    
    # RSS Feed Information
    st.subheader("🎙️ Podcast Feed")
    
    # Get RSS feed URL from environment
    env_vars = load_env()
    public_url = env_vars.get('CLOUDFLARE_R2_PUBLIC_URL', 'https://your-domain.com')
    rss_url = f"{public_url}/feed.xml"
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.text_input("RSS Feed URL", value=rss_url, key="rss_url_display")
    
    with col2:
        st.write("")  # Spacer
        if st.button("📋 Copy RSS URL", use_container_width=True):
            st.success("URL copied to clipboard!")
            st.code(rss_url)
    
    # Podcast app links
    st.write("**Subscribe in podcast apps:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        apple_url = f"podcast://{rss_url.replace('https://', '')}"
        st.markdown(f"[📱 Apple Podcasts]({apple_url})")
    
    with col2:
        google_url = f"https://podcasts.google.com/feed/{rss_url.replace('https://', '')}"
        st.markdown(f"[🎵 Google Podcasts]({google_url})")
    
    with col3:
        spotify_url = f"https://open.spotify.com/show/add-podcast?uri={rss_url}"
        st.markdown(f"[🎧 Spotify]({spotify_url})")
    
    # Instructions
    with st.expander("📖 How to subscribe"):
        st.markdown(f"""
        ### Adding to podcast apps:
        
        1. **Copy the RSS URL:** `{rss_url}`
        
        2. **In your podcast app:**
           - **Apple Podcasts:** Search → "Add by URL" → Paste URL
           - **Spotify:** Not directly supported, use RSS readers
           - **Google Podcasts:** Settings → "Add by RSS" → Paste URL
           - **Overcast:** + → "Add by URL" → Paste URL
           - **Pocket Casts:** Discover → Search → Paste URL
        
        3. **Alternative:** Use any RSS reader app and paste the feed URL
        
        ### Public URL Setup:
        To make your podcast publicly available, configure a custom domain in Cloudflare R2 settings and update `CLOUDFLARE_R2_PUBLIC_URL` in your environment variables.
        """)
    
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
    
    # Intro Settings
    st.subheader("🎵 Intro Settings")
    
    if 'intro' not in settings:
        settings['intro'] = {
            'enabled': True,
            'prompt': 'Välkommen till {podcast_title}! Idag är det {date}. Här kommer din dagliga sammanfattning av nyheter, teknik och väder.',
            'voice_id': '21m00Tcm4TlvDq8ikWAM',
            'jingle_file': 'audio/jingle.mp3',
            'mix_type': 'sequence'
        }
    
    intro_settings = settings['intro']
    
    col1, col2 = st.columns(2)
    
    with col1:
        intro_settings['enabled'] = st.checkbox("Enable Intro", value=intro_settings.get('enabled', True))
        
        intro_settings['prompt'] = st.text_area(
            "Intro Text Template",
            value=intro_settings.get('prompt', ''),
            help="Use {podcast_title}, {date}, {author} as placeholders"
        )
        
        intro_settings['voice_id'] = st.text_input(
            "Intro Voice ID",
            value=intro_settings.get('voice_id', ''),
            help="ElevenLabs Voice ID for intro"
        )
    
    with col2:
        intro_settings['jingle_file'] = st.text_input(
            "Jingle File Path",
            value=intro_settings.get('jingle_file', 'audio/jingle.mp3'),
            help="Path to jingle MP3 file"
        )
        
        intro_settings['mix_type'] = st.selectbox(
            "Intro Mix Type",
            ['sequence', 'overlay'],
            index=0 if intro_settings.get('mix_type', 'sequence') == 'sequence' else 1,
            help="sequence: jingle then voice, overlay: voice over jingle"
        )
        
        # Upload jingle file
        uploaded_jingle = st.file_uploader(
            "Upload Jingle (MP3)",
            type=['mp3'],
            help="Upload a jingle file to use as intro music"
        )
        
        if uploaded_jingle is not None:
            # Save uploaded file
            os.makedirs('audio', exist_ok=True)
            jingle_path = 'audio/jingle.mp3'
            with open(jingle_path, 'wb') as f:
                f.write(uploaded_jingle.read())
            intro_settings['jingle_file'] = jingle_path
            st.success(f"Jingle uploaded: {jingle_path}")
    
    # Voice settings for intro
    with st.expander("🎛️ Advanced Intro Voice Settings"):
        intro_settings['stability'] = st.slider("Stability", 0.0, 1.0, intro_settings.get('stability', 0.6))
        intro_settings['similarity_boost'] = st.slider("Similarity Boost", 0.0, 1.0, intro_settings.get('similarity_boost', 0.8))
        intro_settings['style'] = st.slider("Style", 0.0, 1.0, intro_settings.get('style', 0.3))
    
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

def show_music_library():
    st.header("🎵 Music Library")
    
    # Initialize music library
    music_lib = MusicLibrary()
    
    # Upload section
    st.subheader("📁 Upload Music")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload Music Files",
            type=['mp3', 'wav', 'flac', 'm4a'],
            accept_multiple_files=True,
            help="Upload music files to use in your podcast"
        )
    
    with col2:
        st.info("""
        **Supported formats:**
        - MP3
        - WAV 
        - FLAC
        - M4A
        
        **Recommendations:**
        - Use short clips (3-30 seconds)
        - Ensure copyright compliance
        - Name files descriptively
        """)
    
    # Process uploaded files
    if uploaded_files:
        with st.expander("📝 Add Track Information", expanded=True):
            for uploaded_file in uploaded_files:
                st.subheader(f"🎵 {uploaded_file.name}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    artist = st.text_input(f"Artist", key=f"artist_{uploaded_file.name}")
                    title = st.text_input(f"Title", key=f"title_{uploaded_file.name}", 
                                        value=uploaded_file.name.rsplit('.', 1)[0])
                
                with col2:
                    available_categories = list(music_lib.library["categories"].keys())
                    categories = st.multiselect(
                        "Categories",
                        available_categories,
                        key=f"cat_{uploaded_file.name}",
                        help="What type of content does this music fit?"
                    )
                    
                    available_moods = list(music_lib.library["moods"].keys())
                    moods = st.multiselect(
                        "Moods",
                        available_moods,
                        key=f"mood_{uploaded_file.name}",
                        help="What mood does this music convey?"
                    )
                
                with col3:
                    description = st.text_area(
                        "Description",
                        key=f"desc_{uploaded_file.name}",
                        help="Describe when this music should be used"
                    )
                    
                    duration = st.number_input(
                        "Duration (seconds)",
                        min_value=1.0,
                        max_value=300.0,
                        value=10.0,
                        step=0.5,
                        key=f"dur_{uploaded_file.name}"
                    )
                
                if st.button(f"💾 Save {uploaded_file.name}", key=f"save_{uploaded_file.name}"):
                    if artist and title:
                        try:
                            # Save uploaded file temporarily
                            temp_path = f"/tmp/{uploaded_file.name}"
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.read())
                            
                            # Add to library
                            track_id = music_lib.add_track(
                                temp_path, artist, title,
                                categories=categories,
                                moods=moods,
                                duration=duration,
                                description=description
                            )
                            
                            st.success(f"✅ Added: {artist} - {title} (ID: {track_id})")
                            
                            # Clean up temp file
                            os.remove(temp_path)
                            
                            # Rerun to refresh library
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error adding track: {e}")
                    else:
                        st.error("Please fill in Artist and Title")
                
                st.divider()
    
    # Current library
    st.subheader("🎼 Current Music Library")
    
    tracks = music_lib.get_all_tracks()
    
    if not tracks:
        st.info("No music tracks in library yet. Upload some music above!")
    else:
        st.write(f"**{len(tracks)} tracks available**")
        
        # Search and filter
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("🔍 Search", placeholder="Search artist, title, or description")
        
        with col2:
            filter_category = st.selectbox(
                "Filter by Category",
                ["All"] + list(music_lib.library["categories"].keys())
            )
        
        with col3:
            filter_mood = st.selectbox(
                "Filter by Mood", 
                ["All"] + list(music_lib.library["moods"].keys())
            )
        
        # Apply filters
        filtered_tracks = tracks
        
        if search_query:
            filtered_tracks = music_lib.search_tracks(search_query)
        
        if filter_category != "All":
            filtered_tracks = [t for t in filtered_tracks if filter_category in t.get("categories", [])]
        
        if filter_mood != "All":
            filtered_tracks = [t for t in filtered_tracks if filter_mood in t.get("moods", [])]
        
        # Display tracks
        for track in filtered_tracks:
            with st.expander(f"🎵 {track['artist']} - {track['title']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Artist:** {track['artist']}")
                    st.write(f"**Title:** {track['title']}")
                    st.write(f"**Duration:** {track.get('duration', 'Unknown')} seconds")
                    st.write(f"**File:** {track['filename']}")
                
                with col2:
                    if track.get('categories'):
                        st.write(f"**Categories:** {', '.join(track['categories'])}")
                    if track.get('moods'):
                        st.write(f"**Moods:** {', '.join(track['moods'])}")
                    if track.get('description'):
                        st.write(f"**Description:** {track['description']}")
                
                with col3:
                    # Audio player
                    if os.path.exists(track['path']):
                        with open(track['path'], 'rb') as audio_file:
                            audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/mp3')
                    
                    if st.button(f"🗑️ Delete", key=f"delete_{track['id']}"):
                        if music_lib.remove_track(track['id']):
                            st.success(f"Deleted: {track['artist']} - {track['title']}")
                            st.rerun()
    
    # Music usage guide
    with st.expander("📖 Music Usage Guide"):
        st.markdown("""
        ### How AI uses your music:
        
        Your uploaded music will be available to the AI when generating podcast scripts. The AI will:
        
        1. **Analyze available music** by categories and moods
        2. **Choose appropriate tracks** based on the content and flow
        3. **Insert music cues** in the script like: `[MUSIK: Artist - Title, 5 sekunder]`
        4. **Consider context** - news segments get serious music, tech segments get upbeat music
        
        ### Categories explained:
        - **Intro**: Opening music and show theme
        - **News**: Serious news segments
        - **Tech**: Technology and innovation content
        - **Transition**: Between different topics
        - **Weather**: Weather segments and closings
        - **Upbeat**: Positive, energetic content
        - **Calm**: Relaxed, background ambience
        - **Outro**: Closing and farewell music
        
        ### Best practices:
        - Upload short clips (3-30 seconds work best)
        - Use royalty-free or original music
        - Tag music accurately so AI can choose well
        - Include variety of moods and styles
        """)
    
    # Preview music context for AI
    if st.button("👁️ Preview AI Music Context"):
        context = music_lib.get_music_prompt_context()
        st.code(context)

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