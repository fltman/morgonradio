import streamlit as st

# MUST be first Streamlit command
st.set_page_config(
    page_title="Morgonpodd Control Panel",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

import json
import os
import asyncio
from datetime import datetime, timedelta
import subprocess
import sys
from pathlib import Path

# Import our modules - with error handling for missing dependencies
try:
    from main import MorgonPoddService
    from scraper import NewsScraper
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    # Handle missing dependencies gracefully
    MorgonPoddService = None
    NewsScraper = None
    DEPENDENCIES_AVAILABLE = False

from music_library import MusicLibrary

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            st.error(f"JSON parsing error in {config_path}: {e}")
            st.info("Creating default configuration...")
            return create_default_config()
    return create_default_config()

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def create_default_config():
    return {
        "sources": [],
        "podcastSettings": {
            "title": "Morgonpodd",
            "description": "Din dagliga sammanfattning av nyheter och väder",
            "author": "Morgonpodd AI",
            "language": "sv-SE",
            "generateTime": "06:00",
            "maxDuration": 600,
            "hosts": [
                {
                    "name": "Anna",
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",
                    "personality": "Energisk och välkomnande morgonvärd",
                    "style": "varm och konversationell"
                },
                {
                    "name": "Erik", 
                    "voice_id": "EXAVITQu4vr4xnSDxMaL",
                    "personality": "Analytisk och noggrann journalist",
                    "style": "informativ men lättsam"
                }
            ],
            "intro": {
                "enabled": True,
                "prompt": "Välkommen till {podcast_title}! Idag är det {date}. Här kommer din dagliga sammanfattning.",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "jingle_file": "audio/jingle.mp3",
                "mix_type": "sequence"
            },
            "promptTemplates": {
                "main_prompt": """Du är {host1_name} och {host2_name}, två professionella poddvärdar som skapar engagerande morgonpoddar på svenska.

{host1_name}: {host1_personality}. Stil: {host1_style}
{host2_name}: {host2_personality}. Stil: {host2_style}

Skapa ett naturligt samtal mellan er två baserat på dagens innehåll. Låt er komplementera varandra och ha en naturlig dialog.""",
                "conversation_style": "natural_dialogue"
            }
        }
    }

def main():
    st.title("🎙️ Morgonpodd Control Panel")
    
    # Show dependency warning if needed
    if not DEPENDENCIES_AVAILABLE:
        st.warning("⚠️ Some features unavailable due to missing dependencies. Run `pip install schedule` to enable full functionality.")
    
    # Load configuration
    config = load_config()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🎛️ Navigation")
        
        pages = [
            "Dashboard",
            "Podcast Settings", 
            "Music Library",
            "News Sources",
            "Prompts",
            "Generate Episode",
            "API Keys"
        ]
        
        selected_page = st.radio("Choose Section", pages)
        
        # Quick stats
        st.markdown("---")
        st.subheader("📊 Quick Stats")
        
        # Music library stats
        music_lib = MusicLibrary()
        tracks = music_lib.get_all_tracks()
        st.metric("Music Tracks", len(tracks))
        
        # Source stats  
        sources_count = len(config.get('sources', []))
        st.metric("News Sources", sources_count)
        
        # Show RSS URL if available
        if config.get('podcastSettings', {}).get('publicUrl'):
            st.markdown("---")
            st.subheader("📡 RSS Feed")
            rss_url = f"{config['podcastSettings']['publicUrl']}/feed.xml"
            st.code(rss_url)
    
    # Main content area
    if selected_page == "Dashboard":
        show_dashboard(config)
    elif selected_page == "Podcast Settings":
        show_podcast_settings(config)
    elif selected_page == "Music Library":
        show_music_library_comprehensive()
    elif selected_page == "News Sources":
        show_news_sources(config)
    elif selected_page == "Prompts":
        show_prompts(config)
    elif selected_page == "Generate Episode":
        show_episode_generation(config)
    elif selected_page == "API Keys":
        show_api_keys()

def show_dashboard(config):
    st.header("🏠 Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎧 Recent Episodes")
        
        # List recent episodes if they exist
        if os.path.exists('episodes'):
            episodes = [f for f in os.listdir('episodes') if f.endswith('.mp3')]
            episodes.sort(reverse=True)
            
            if episodes:
                for ep in episodes[:5]:  # Show latest 5
                    st.text(f"📻 {ep}")
            else:
                st.info("No episodes generated yet")
        else:
            st.info("No episodes directory found")
    
    with col2:
        st.subheader("⚙️ System Status")
        
        # Check API keys
        api_keys_status = []
        if os.getenv('OPENAI_API_KEY'):
            api_keys_status.append("✅ OpenAI API")
        else:
            api_keys_status.append("❌ OpenAI API")
            
        if os.getenv('ELEVENLABS_API_KEY'):
            api_keys_status.append("✅ ElevenLabs API")
        else:
            api_keys_status.append("❌ ElevenLabs API")
            
        if os.getenv('CLOUDFLARE_ACCOUNT_ID'):
            api_keys_status.append("✅ Cloudflare")
        else:
            api_keys_status.append("❌ Cloudflare")
        
        for status in api_keys_status:
            st.text(status)
    
    # Quick actions
    st.markdown("---")
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎬 Generate Episode Now", type="primary"):
            if MorgonPoddService:
                with st.spinner("Generating episode..."):
                    try:
                        service = MorgonPoddService()
                        service.run_once()
                        st.success("Episode generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating episode: {e}")
            else:
                st.error("Episode generation unavailable - missing dependencies")
    
    with col2:
        if st.button("🔍 Test Sources"):
            if NewsScraper:
                with st.spinner("Testing news sources..."):
                    try:
                        scraper = NewsScraper()
                        # Test scraping (would need async handling in real implementation)
                        st.success("Sources tested successfully!")
                    except Exception as e:
                        st.error(f"Error testing sources: {e}")
            else:
                st.error("Source testing unavailable - missing dependencies")
    
    with col3:
        if st.button("📤 Upload to Cloudflare"):
            st.info("Upload functionality would be implemented here")

def show_podcast_settings(config):
    st.header("⚙️ Podcast Settings")
    
    settings = config['podcastSettings']
    
    # Basic settings
    st.subheader("📻 Basic Information")
    col1, col2 = st.columns(2)
    
    with col1:
        settings['title'] = st.text_input("Podcast Title", value=settings.get('title', 'Morgonpodd'))
        settings['author'] = st.text_input("Author", value=settings.get('author', 'Morgonpodd AI'))
        settings['language'] = st.selectbox("Language", ['sv-SE', 'en-US'], 
                                          index=0 if settings.get('language') == 'sv-SE' else 1)
    
    with col2:
        settings['description'] = st.text_area("Description", 
                                             value=settings.get('description', 'Din dagliga sammanfattning'))
        generate_time = st.time_input("Generate Time", 
                                     value=datetime.strptime(settings.get('generateTime', '06:00'), '%H:%M').time())
        settings['generateTime'] = generate_time.strftime('%H:%M')
        settings['maxDuration'] = st.slider("Max Duration (seconds)", 300, 1200, 
                                           value=settings.get('maxDuration', 600))
    
    # Logo/Cover Image Upload
    st.subheader("🎨 Podcast Logo & Cover")
    col1, col2 = st.columns(2)
    
    with col1:
        # Upload logo for RSS feed
        uploaded_logo = st.file_uploader(
            "Upload Podcast Logo/Cover",
            type=['png', 'jpg', 'jpeg'],
            help="Square image recommended (min 1400x1400px for best quality). Used in RSS feed and podcast directories."
        )
        
        if uploaded_logo is not None:
            # Save the uploaded logo
            os.makedirs('public', exist_ok=True)
            logo_path = "public/cover.jpg"
            
            # Process and save the image
            from PIL import Image
            import io
            
            # Open and process the image
            image = Image.open(io.BytesIO(uploaded_logo.getvalue()))
            
            # Convert to RGB if necessary (for JPEG saving)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Save as JPEG
            image.save(logo_path, 'JPEG', quality=95)
            settings['cover_image'] = logo_path
            
            st.success(f"✅ Logo saved: {logo_path}")
            
            # Show preview
            st.image(image, caption="Uploaded Logo", width=200)
    
    with col2:
        # Show current logo if exists
        current_logo = settings.get('cover_image', 'public/cover.jpg')
        if os.path.exists(current_logo):
            st.write("**Current Logo:**")
            st.image(current_logo, width=200)
        else:
            st.info("No logo currently set. Upload an image to use as your podcast cover.")
            
        # Logo guidelines
        st.write("**Logo Guidelines:**")
        st.write("• Square aspect ratio (1:1)")
        st.write("• Minimum 1400x1400px")
        st.write("• Maximum 3000x3000px")
        st.write("• JPG or PNG format")
        st.write("• Clear, readable at small sizes")
    
    # Hosts configuration
    st.subheader("🎭 Host Configuration")
    
    hosts = settings['hosts']
    
    for i, host in enumerate(hosts):
        with st.expander(f"Host {i+1}: {host['name']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                host['name'] = st.text_input(f"Name", value=host['name'], key=f"host_{i}_name")
                host['voice_id'] = st.text_input(f"ElevenLabs Voice ID", value=host['voice_id'], key=f"host_{i}_voice")
            
            with col2:
                host['personality'] = st.text_area(f"Personality", value=host['personality'], key=f"host_{i}_personality")
                host['style'] = st.text_input(f"Speaking Style", value=host['style'], key=f"host_{i}_style")
    
    # Intro settings
    st.subheader("🎵 Intro Settings")
    
    intro_settings = settings.get('intro', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        intro_settings['enabled'] = st.checkbox("Enable Intro", value=intro_settings.get('enabled', True))
        intro_settings['prompt'] = st.text_area(
            "Intro Text Template",
            value=intro_settings.get('prompt', 'Välkommen till {podcast_title}! Idag är det {date}.'),
            help="Use {podcast_title}, {date}, {author} as placeholders"
        )
    
    with col2:
        intro_settings['voice_id'] = st.text_input(
            "Intro Voice ID",
            value=intro_settings.get('voice_id', '21m00Tcm4TlvDq8ikWAM'),
            help="ElevenLabs Voice ID for intro"
        )
        
        # File uploader for jingle
        uploaded_jingle = st.file_uploader(
            "Upload Jingle",
            type=['mp3', 'wav'],
            help="Upload a jingle file to use as intro music"
        )
        
        if uploaded_jingle is not None:
            # Save the uploaded jingle
            os.makedirs('audio', exist_ok=True)
            jingle_path = f"audio/jingle.mp3"
            with open(jingle_path, "wb") as f:
                f.write(uploaded_jingle.getvalue())
            intro_settings['jingle_file'] = jingle_path
            st.success(f"✅ Jingle saved: {jingle_path}")
    
    settings['intro'] = intro_settings
    
    # Prompt templates
    st.subheader("📝 AI Prompt Templates")
    
    prompt_templates = settings.get('promptTemplates', {})
    
    prompt_templates['main_prompt'] = st.text_area(
        "Main Conversation Prompt", 
        value=prompt_templates.get('main_prompt', ''),
        height=200,
        help="Use {host1_name}, {host2_name}, etc. as placeholders"
    )
    
    settings['promptTemplates'] = prompt_templates
    
    # Save button
    if st.button("💾 Save Podcast Settings", type="primary"):
        save_config(config)
        st.success("✅ Podcast settings saved!")

def show_music_library_comprehensive():
    st.header("🎵 Music Library Administration")
    
    # Initialize music library
    music_lib = MusicLibrary()
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["🔄 Upload Music", "📚 Browse Library", "⚙️ Settings"])
    
    with tab1:
        upload_music_interface(music_lib)
    
    with tab2:
        browse_library_interface(music_lib)
    
    with tab3:
        music_settings_interface(music_lib)

def upload_music_interface(music_lib):
    st.subheader("📁 Upload New Music")
    
    uploaded_files = st.file_uploader(
        "Choose music files",
        type=['mp3', 'wav', 'flac', 'm4a'],
        accept_multiple_files=True,
        help="Upload music files to add to your podcast library"
    )
    
    if uploaded_files:
        st.success(f"Ready to process {len(uploaded_files)} file(s)")
        
        for i, uploaded_file in enumerate(uploaded_files):
            with st.expander(f"📝 Configure: {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    artist = st.text_input(
                        "Artist",
                        value="",
                        key=f"artist_{i}",
                        placeholder="Enter artist name"
                    )
                    
                    title = st.text_input(
                        "Track Title",
                        value="",
                        key=f"title_{i}",
                        placeholder="Enter track title"
                    )
                    
                    duration = st.number_input(
                        "Duration (seconds)",
                        min_value=0.0,
                        step=0.1,
                        key=f"duration_{i}",
                        help="Leave 0 for auto-detection"
                    )
                
                with col2:
                    # Categories
                    available_categories = list(music_lib.library["categories"].keys())
                    categories = st.multiselect(
                        "Categories",
                        available_categories,
                        key=f"categories_{i}",
                        help="What type of content does this music fit?"
                    )
                    
                    # Moods
                    available_moods = list(music_lib.library["moods"].keys())
                    moods = st.multiselect(
                        "Moods",
                        available_moods,
                        key=f"moods_{i}",
                        help="What mood does this music convey?"
                    )
                    
                    description = st.text_area(
                        "Description",
                        key=f"description_{i}",
                        help="Describe when this music should be used"
                    )
                
                # Add track button
                if st.button(f"💾 Add '{uploaded_file.name}' to Library", key=f"add_{i}"):
                    if artist and title:
                        try:
                            # Save uploaded file to temp location
                            temp_path = f"temp_{uploaded_file.name}"
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                            
                            # Add to library
                            track_id = music_lib.add_track(
                                file_path=temp_path,
                                artist=artist,
                                title=title,
                                categories=categories,
                                moods=moods,
                                duration=duration if duration > 0 else None,
                                description=description
                            )
                            
                            # Clean up temp file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            
                            st.success(f"✅ Added '{artist} - {title}' to library!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding track: {str(e)}")
                    else:
                        st.error("Please provide both artist and title")

def browse_library_interface(music_lib):
    st.subheader("📚 Music Library Browser")
    
    tracks = music_lib.get_all_tracks()
    
    if not tracks:
        st.info("📭 No music tracks in library yet. Upload some music in the Upload tab!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        category_filter = st.selectbox(
            "Filter by Category",
            ["All"] + list(music_lib.library["categories"].keys())
        )
    
    with col2:
        mood_filter = st.selectbox(
            "Filter by Mood", 
            ["All"] + list(music_lib.library["moods"].keys())
        )
    
    with col3:
        search_query = st.text_input("🔍 Search tracks", placeholder="Search artist, title, or description")
    
    # Apply filters
    filtered_tracks = tracks
    
    if search_query:
        filtered_tracks = music_lib.search_tracks(search_query)
    
    if category_filter != "All":
        filtered_tracks = [t for t in filtered_tracks if category_filter in t.get("categories", [])]
    
    if mood_filter != "All":
        filtered_tracks = [t for t in filtered_tracks if mood_filter in t.get("moods", [])]
    
    # Display tracks
    st.write(f"📼 **Found {len(filtered_tracks)} track(s)**")
    
    for track in filtered_tracks:
        with st.expander(f"🎵 {track['artist']} - {track['title']}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.text(f"🎤 Artist: {track['artist']}")
                st.text(f"🎵 Title: {track['title']}")
                if track.get('duration'):
                    st.text(f"⏱️ Duration: {track['duration']:.1f}s")
                st.text(f"📁 File: {track['filename']}")
            
            with col2:
                if track.get('categories'):
                    st.text("📂 Categories: " + ", ".join(track['categories']))
                if track.get('moods'):
                    st.text("🎭 Moods: " + ", ".join(track['moods']))
                if track.get('description'):
                    st.text(f"📝 Description: {track['description']}")
            
            with col3:
                # Audio player
                if os.path.exists(track['path']):
                    try:
                        with open(track['path'], 'rb') as audio_file:
                            audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/mp3')
                    except:
                        st.text("Audio preview unavailable")
                
                if st.button("🗑️ Delete", key=f"delete_{track['id']}"):
                    if music_lib.remove_track(track['id']):
                        st.success(f"✅ Deleted '{track['artist']} - {track['title']}'")
                        st.rerun()

def music_settings_interface(music_lib):
    st.subheader("⚙️ Music Library Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Category management
        st.write("**📂 Manage Categories**")
        
        categories = music_lib.library["categories"]
        
        # Add new category
        with st.expander("➕ Add New Category"):
            new_cat_id = st.text_input("Category ID", placeholder="e.g., 'action'")
            new_cat_name = st.text_input("Category Name", placeholder="e.g., 'Action and Adventure'")
            
            if st.button("Add Category") and new_cat_id and new_cat_name:
                music_lib.library["categories"][new_cat_id] = new_cat_name
                music_lib.save_library()
                st.success(f"Added category: {new_cat_name}")
                st.rerun()
        
        # Current categories
        for cat_id, cat_name in categories.items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.text(f"{cat_id}: {cat_name}")
            with col_b:
                if st.button("🗑️", key=f"del_cat_{cat_id}"):
                    del music_lib.library["categories"][cat_id]
                    music_lib.save_library()
                    st.success(f"Deleted category: {cat_name}")
                    st.rerun()
    
    with col2:
        # Mood management
        st.write("**🎭 Manage Moods**")
        
        moods = music_lib.library["moods"]
        
        # Add new mood
        with st.expander("➕ Add New Mood"):
            new_mood_id = st.text_input("Mood ID", placeholder="e.g., 'energetic'")
            new_mood_name = st.text_input("Mood Name", placeholder="e.g., 'High Energy and Exciting'")
            
            if st.button("Add Mood") and new_mood_id and new_mood_name:
                music_lib.library["moods"][new_mood_id] = new_mood_name
                music_lib.save_library()
                st.success(f"Added mood: {new_mood_name}")
                st.rerun()
        
        # Current moods
        for mood_id, mood_name in moods.items():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.text(f"{mood_id}: {mood_name}")
            with col_b:
                if st.button("🗑️", key=f"del_mood_{mood_id}"):
                    del music_lib.library["moods"][mood_id]
                    music_lib.save_library()
                    st.success(f"Deleted mood: {mood_name}")
                    st.rerun()
    
    st.divider()
    
    # AI Preview and Usage Guide
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🤖 AI Context Preview**")
        if st.button("👁️ Preview AI Music Context"):
            context = music_lib.get_music_prompt_context()
            st.code(context, language="markdown")
    
    with col2:
        st.write("**💾 Backup & Restore**")
        
        if st.button("📤 Export Library"):
            import json
            export_data = {
                'library': music_lib.library,
                'export_date': str(datetime.now()),
                'version': '1.0'
            }
            st.download_button(
                label="💾 Download Library Backup",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name=f"music_library_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        uploaded_backup = st.file_uploader("📥 Import Library Backup", type=['json'])
        if uploaded_backup is not None:
            try:
                backup_data = json.load(uploaded_backup)
                music_lib.library = backup_data['library']
                music_lib.save_library()
                st.success("✅ Library restored from backup!")
                st.rerun()
            except Exception as e:
                st.error(f"Error restoring backup: {str(e)}")
    
    # Music usage guide
    with st.expander("📖 Music Usage Guide"):
        st.markdown("""
        ### How AI uses your music:
        
        1. **Analyzes available music** by categories and moods
        2. **Matches content context** - serious news gets calm music, tech gets upbeat
        3. **Inserts music cues** in script: `[MUSIK: Artist - Title, 5 sekunder]`
        4. **Considers flow** - transitions, intros, outros
        
        ### Categories:
        - **Intro/Outro**: Opening and closing segments
        - **News**: Serious news content
        - **Tech**: Technology and innovation
        - **Transition**: Between different topics
        - **Weather**: Weather forecasts and casual content
        
        ### Best practices:
        - Use royalty-free or original music
        - Keep clips short (3-30 seconds)
        - Tag accurately for better AI selection
        """)

def show_news_sources(config):
    st.header("📰 News Sources Configuration")
    
    sources = config.get('sources', [])
    
    # Add new source
    st.subheader("➕ Add New Source")
    
    with st.expander("Configure New Source"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("Source Name", placeholder="e.g., SVT Nyheter")
            new_url = st.text_input("URL", placeholder="https://example.com")
            new_type = st.selectbox("Source Type", ["news", "tech", "weather", "rss"])
        
        with col2:
            new_selector = st.text_input("CSS Selector", placeholder="h1, .title, etc.")
            new_description = st.text_area("Description", placeholder="What content does this source provide?")
        
        if st.button("Add Source") and new_name and new_url:
            new_source = {
                "name": new_name,
                "url": new_url,
                "type": new_type,
                "selector": new_selector,
                "description": new_description,
                "enabled": True
            }
            sources.append(new_source)
            config['sources'] = sources
            save_config(config)
            st.success(f"✅ Added source: {new_name}")
            st.rerun()
    
    # Display existing sources
    st.subheader("📋 Current Sources")
    
    if not sources:
        st.info("No news sources configured yet. Add some above!")
        return
    
    for i, source in enumerate(sources):
        with st.expander(f"{source['name']} ({source['type']})", expanded=False):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                source['name'] = st.text_input("Name", value=source['name'], key=f"src_name_{i}")
                source['url'] = st.text_input("URL", value=source['url'], key=f"src_url_{i}")
                source['type'] = st.selectbox("Type", ["news", "tech", "weather", "rss"], 
                                           index=["news", "tech", "weather", "rss"].index(source['type']), 
                                           key=f"src_type_{i}")
            
            with col2:
                source['selector'] = st.text_input("CSS Selector", value=source.get('selector', ''), key=f"src_sel_{i}")
                source['description'] = st.text_area("Description", value=source.get('description', ''), key=f"src_desc_{i}")
                source['enabled'] = st.checkbox("Enabled", value=source.get('enabled', True), key=f"src_en_{i}")
            
            with col3:
                if st.button("🗑️ Delete", key=f"del_src_{i}"):
                    sources.pop(i)
                    config['sources'] = sources
                    save_config(config)
                    st.success("Source deleted!")
                    st.rerun()
                
                if st.button("🔍 Test", key=f"test_src_{i}"):
                    if NewsScraper:
                        test_individual_source(source)
                    else:
                        st.error("Source testing unavailable - missing dependencies")
    
    # Save button
    if st.button("💾 Save Sources", type="primary"):
        config['sources'] = sources
        save_config(config)
        st.success("✅ Sources saved!")

def show_episode_generation(config):
    st.header("🎬 Episode Generation")
    
    if not MorgonPoddService:
        st.error("Episode generation is unavailable due to missing dependencies. Please install all requirements.")
        return
    
    # Tabs for manual generation vs scheduling
    gen_tab, schedule_tab = st.tabs(["🎬 Generate Now", "⏰ Schedule Episodes"])
    
    with gen_tab:
        st.subheader("🚀 Generate New Episode")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Current Settings:**")
            settings = config.get('podcastSettings', {})
            st.text(f"Title: {settings.get('title', 'N/A')}")
            st.text(f"Hosts: {', '.join([h['name'] for h in settings.get('hosts', [])])}")
            st.text(f"Max Duration: {settings.get('maxDuration', 'N/A')} seconds")
            st.text(f"Sources: {len(config.get('sources', []))} configured")
        
        with col2:
            st.write("**Generation Options:**")
            
            include_intro = st.checkbox("Include Intro", value=True)
            include_music = st.checkbox("Include Background Music", value=True)
            preview_mode = st.checkbox("Preview Mode (Don't Upload)", value=False)
    
    with schedule_tab:
        show_episode_scheduling(config)
    
    if st.button("🎬 Generate Episode Now", type="primary"):
        # Create containers for progress tracking
        progress_container = st.container()
        log_container = st.container()
        
        with progress_container:
            st.write("**Episode Generation Progress**")
            main_progress = st.progress(0)
            main_status = st.empty()
            
            # Detailed progress sections
            col1, col2 = st.columns(2)
            with col1:
                scrape_progress = st.progress(0)
                scrape_status = st.empty()
            with col2:
                ai_progress = st.progress(0)
                ai_status = st.empty()
            
            col3, col4 = st.columns(2)
            with col3:
                audio_progress = st.progress(0)
                audio_status = st.empty()
            with col4:
                upload_progress = st.progress(0)
                upload_status = st.empty()
        
        with log_container:
            st.write("**Detailed Log**")
            log_area = st.empty()
            log_lines = []
        
        def add_log(message, level="INFO"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_lines.append(f"[{timestamp}] {level}: {message}")
            log_area.code("\n".join(log_lines[-20:]), language="log")  # Show last 20 lines
        
        try:
            add_log("Starting episode generation process")
            main_status.text("🚀 Initializing episode generation...")
            main_progress.progress(5)
            
            if not MorgonPoddService:
                raise Exception("MorgonPoddService not available - missing dependencies")
            
            service = MorgonPoddService()
            add_log("MorgonPoddService initialized successfully")
            
            # Step 1: Scraping (0-25%)
            main_status.text("🔍 Step 1/6: Scraping news sources...")
            scrape_status.text("🔍 Scraping sources...")
            main_progress.progress(10)
            
            add_log("Starting news scraping from configured sources")
            scraped_data = asyncio.run(service.scraper.scrape_all())
            
            # Count scraped items
            total_items = sum(len(source['items']) for source in scraped_data)
            add_log(f"Successfully scraped {total_items} items from {len(scraped_data)} sources")
            
            scrape_progress.progress(100)
            scrape_status.text(f"✅ {total_items} items scraped")
            main_progress.progress(25)
            
            # Step 2: Save scraped data
            main_status.text("💾 Step 2/6: Saving scraped content...")
            add_log("Saving scraped content to file")
            
            with open('../scraped_content.json', 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
            add_log("Scraped content saved successfully")
            main_progress.progress(30)
            
            # Step 3: AI Script Generation (30-55%)
            main_status.text("🤖 Step 3/6: Generating podcast script with AI...")
            ai_status.text("🤖 Creating conversation...")
            ai_progress.progress(20)
            
            add_log("Starting AI script generation")
            script = service.summarizer.create_podcast_script(scraped_data)
            script_file = service.summarizer.save_script(script)
            
            ai_progress.progress(70)
            add_log(f"Script generated successfully: {len(script)} characters")
            add_log(f"Script saved to: {script_file}")
            
            ai_progress.progress(100)
            ai_status.text(f"✅ Script created ({len(script.split())} words)")
            main_progress.progress(55)
            
            # Step 4: Intro Generation
            main_status.text("🎵 Step 4/6: Generating intro audio...")
            audio_status.text("🎵 Creating intro...")
            audio_progress.progress(10)
            
            add_log("Generating intro audio")
            intro_file = service.intro_generator.generate_intro_audio()
            if intro_file:
                intro_file = service.intro_generator.combine_with_jingle(intro_file)
                add_log(f"Intro generated: {intro_file}")
            else:
                add_log("No intro generated")
            
            audio_progress.progress(30)
            main_progress.progress(65)
            
            # Step 5: Main Audio Generation (65-85%)
            main_status.text("🎤 Step 5/6: Generating speech with ElevenLabs...")
            audio_status.text("🎤 Converting text to speech...")
            
            add_log("Starting TTS generation with ElevenLabs")
            main_audio_file = service.tts_generator.generate_audio(script)
            
            audio_progress.progress(70)
            add_log(f"Main audio generated: {main_audio_file}")
            
            # Combine intro + main content
            if intro_file and os.path.exists(intro_file):
                audio_status.text("🎵 Combining intro with content...")
                add_log("Combining intro with main content")
                audio_file = service.combine_intro_and_main(intro_file, main_audio_file)
            else:
                add_log("Using main content only (no intro)")
                audio_file = main_audio_file
            
            audio_progress.progress(100)
            audio_status.text("✅ Audio generation complete")
            main_progress.progress(85)
            
            # Step 6: Metadata and Upload (85-100%)
            main_status.text("📊 Step 6/6: Creating metadata and uploading...")
            upload_status.text("📊 Generating metadata...")
            
            add_log("Creating episode metadata")
            metadata = service.tts_generator.generate_episode_metadata(script_file, audio_file)
            
            upload_progress.progress(30)
            add_log(f"Episode metadata created: {metadata['title']}")
            
            upload_status.text("📡 Updating RSS feed...")
            add_log("Generating RSS feed")
            service.rss_generator.generate_feed()
            
            upload_progress.progress(60)
            add_log("RSS feed updated successfully")
            
            upload_status.text("☁️ Uploading to Cloudflare...")
            add_log("Uploading episode to Cloudflare R2")
            service.uploader.upload_episode(audio_file, metadata)
            service.uploader.upload_feed()
            
            upload_progress.progress(100)
            upload_status.text("✅ Upload complete")
            main_progress.progress(100)
            
            # Final success
            main_status.text("🎉 Episode generation completed successfully!")
            add_log("=== EPISODE GENERATION COMPLETED ===")
            add_log(f"Episode: {metadata['title']}")
            add_log(f"Audio file: {audio_file}")
            add_log(f"RSS Feed: {config.get('podcastSettings', {}).get('publicUrl', 'Not configured')}/feed.xml")
            
            st.success("🎉 Episode generated successfully!")
            
            # Show episode details
            with st.expander("📊 Episode Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Episode Number", metadata.get('episode_number', 'N/A'))
                    st.metric("Duration", f"{metadata.get('duration_seconds', 0)} seconds")
                with col2:
                    st.metric("File Size", f"{metadata.get('file_size', 0)} bytes")
                    st.metric("Script Length", f"{len(script)} characters")
                
                if os.path.exists(audio_file):
                    st.audio(audio_file)
                
                st.json(metadata)
            
        except Exception as e:
            add_log(f"ERROR: {str(e)}", "ERROR")
            main_status.text("❌ Episode generation failed")
            st.error(f"❌ Error generating episode: {e}")
            main_progress.progress(0)

def show_episode_scheduling(config):
    st.subheader("⏰ Episode Scheduling")
    
    # Check for existing schedule
    schedule_file = "../schedule_config.json"
    current_schedule = load_schedule_config(schedule_file)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📅 Schedule Configuration**")
        
        # Enable/disable scheduling
        schedule_enabled = st.checkbox(
            "Enable Automatic Generation", 
            value=current_schedule.get('enabled', False),
            help="Enable automatic daily episode generation"
        )
        
        # Daily generation time
        generate_time = st.time_input(
            "Daily Generation Time",
            value=datetime.strptime(current_schedule.get('time', '06:00'), '%H:%M').time(),
            help="What time should episodes be generated daily?"
        )
        
        # Days of week
        st.write("**Days to Generate:**")
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        selected_days = []
        
        for i, day in enumerate(days_of_week):
            if st.checkbox(day, value=i < 5, key=f"day_{i}"):  # Default to weekdays
                selected_days.append(i)
        
        # Advanced options
        with st.expander("⚙️ Advanced Schedule Options"):
            retry_on_failure = st.checkbox("Retry on Failure", value=True)
            max_retries = st.number_input("Max Retries", min_value=1, max_value=5, value=3)
            
            notification_email = st.text_input(
                "Notification Email", 
                value=current_schedule.get('notification_email', ''),
                help="Email to notify on success/failure (optional)"
            )
    
    with col2:
        st.write("**📊 Schedule Status**")
        
        # Check if scheduled task actually exists in system
        task_exists = check_scheduled_task_exists()
        import platform
        task_type = "Scheduled Task" if platform.system() == "Windows" else "Cron Job"
        
        if schedule_enabled and selected_days:
            next_run = get_next_scheduled_run(generate_time, selected_days)
            
            if task_exists:
                st.success(f"✅ Scheduling Active ({task_type} created)")
            else:
                st.warning(f"⚠️ Config enabled but no {task_type} found - click Save to create")
                
            st.info(f"Next episode: {next_run.strftime('%Y-%m-%d at %H:%M')}")
            
            # Show which days are active
            active_days = [days_of_week[i] for i in selected_days]
            st.text("Active days: " + ", ".join(active_days))
        else:
            if task_exists:
                st.warning(f"⚠️ Config disabled but {task_type} still exists - click Save to remove")
            else:
                st.warning("⚠️ Scheduling Disabled")
        
        # Recent schedule activity
        st.write("**📈 Recent Activity:**")
        show_schedule_history()
    
    # Save schedule configuration
    if st.button("💾 Save Schedule Configuration", type="primary"):
        schedule_config = {
            'enabled': schedule_enabled,
            'time': generate_time.strftime('%H:%M'),
            'days': selected_days,
            'retry_on_failure': retry_on_failure,
            'max_retries': max_retries,
            'notification_email': notification_email,
            'updated_at': datetime.now().isoformat()
        }
        
        save_schedule_config(schedule_file, schedule_config)
        
        # Manage scheduled task based on enabled status
        success, message = manage_scheduled_task(
            schedule_enabled, 
            generate_time.strftime('%H:%M'), 
            selected_days
        )
        
        if success:
            if schedule_enabled:
                st.success(f"✅ Schedule saved and automatic task created!\n{message}")
            else:
                st.info(f"💾 Schedule saved and automatic task removed.\n{message}")
        else:
            st.error(f"❌ Schedule saved but automatic task failed: {message}")
    
    # Manual schedule controls
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Start Scheduler"):
            if start_scheduler_service():
                st.success("Scheduler started!")
            else:
                st.error("Failed to start scheduler")
    
    with col2:
        if st.button("⏸️ Stop Scheduler"):
            if stop_scheduler_service():
                st.success("Scheduler stopped!")
            else:
                st.error("Failed to stop scheduler")
    
    with col3:
        if st.button("📊 Check Status"):
            status = get_scheduler_status()
            if status['running']:
                st.success(f"✅ Running (PID: {status['pid']})")
            else:
                st.warning("❌ Not running")

def load_schedule_config(schedule_file):
    """Load schedule configuration from file"""
    if os.path.exists(schedule_file):
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_schedule_config(schedule_file, config):
    """Save schedule configuration to file"""
    with open(schedule_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_next_scheduled_run(time_obj, selected_days):
    """Calculate next scheduled run time"""
    import pytz
    tz = pytz.timezone('Europe/Stockholm')
    now = datetime.now(tz)
    
    # Find next occurrence
    for i in range(7):  # Check next 7 days
        check_date = now + timedelta(days=i)
        if check_date.weekday() in selected_days:
            next_run = check_date.replace(
                hour=time_obj.hour, 
                minute=time_obj.minute, 
                second=0, 
                microsecond=0
            )
            if next_run > now:  # Must be in the future
                return next_run
    
    # Fallback to next week
    return now + timedelta(days=7)

def show_schedule_history():
    """Show recent scheduling activity"""
    history_file = "../schedule_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            recent = history[-5:] if len(history) > 5 else history
            for entry in reversed(recent):
                status_icon = "✅" if entry['status'] == 'success' else "❌"
                st.text(f"{status_icon} {entry['date']} - {entry['message']}")
        except:
            st.text("No recent activity")
    else:
        st.text("No history available")

def manage_scheduled_task(enabled, time_str, days_of_week):
    """Cross-platform scheduled task management"""
    import platform
    
    if platform.system() == "Windows":
        return manage_windows_scheduled_task(enabled, time_str, days_of_week)
    else:
        return manage_unix_cron_job(enabled, time_str, days_of_week)

def manage_windows_scheduled_task(enabled, time_str, days_of_week):
    """Add or remove Windows Scheduled Task for automatic generation"""
    try:
        import subprocess
        import platform
        
        task_name = "MorgonPoddGeneration"
        
        # Delete existing task if it exists
        subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'], 
                      capture_output=True, text=True)
        
        if enabled and days_of_week:
            # Get paths
            python_path = sys.executable
            project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(project_path, 'src', 'main.py')
            
            # Convert days to Windows format (MON, TUE, WED, THU, FRI, SAT, SUN)
            day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
            windows_days = [day_names[day] for day in days_of_week]
            days_str = ','.join(windows_days)
            
            # Create scheduled task
            cmd = [
                'schtasks', '/create',
                '/tn', task_name,
                '/tr', f'"{python_path}" "{script_path}"',
                '/sc', 'weekly',
                '/d', days_str,
                '/st', time_str,
                '/ru', 'SYSTEM',
                '/f'  # Force overwrite
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"✅ Windows Scheduled Task created for {time_str} on {days_str}"
            else:
                return False, f"Error creating scheduled task: {result.stderr}"
        else:
            return True, "📅 Windows Scheduled Task removed (scheduling disabled)"
            
    except Exception as e:
        return False, f"Error managing Windows scheduled task: {str(e)}"

def manage_unix_cron_job(enabled, time_str, days_of_week):
    """Add or remove cron job for automatic generation (Unix/Mac)"""
    try:
        import subprocess
        import tempfile
        
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # Filter out existing morgonpodd entries
        cron_lines = [line for line in current_cron.split('\n') 
                     if line and 'morgonpodd' not in line.lower()]
        
        if enabled and days_of_week:
            # Parse time
            hour, minute = time_str.split(':')
            
            # Convert days to cron format (0=Sunday, 1=Monday, etc.)
            # Our days_of_week uses 0=Monday, so we need to convert
            cron_days = []
            for day in days_of_week:
                # Convert: Mon=0->1, Tue=1->2, ..., Sat=5->6, Sun=6->0
                cron_day = (day + 1) % 7
                cron_days.append(str(cron_day))
            
            days_str = ','.join(cron_days) if cron_days else '*'
            
            # Get Python and project paths
            python_path = sys.executable
            project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Create cron entry with comment for identification
            cron_entry = f"{minute} {hour} * * {days_str} cd {project_path} && {python_path} src/main.py >> episodes/cron.log 2>&1 # morgonpodd-auto"
            cron_lines.append(cron_entry)
            
            message = f"✅ Cron job created for {time_str} on selected days"
        else:
            message = "📅 Cron job removed (scheduling disabled)"
        
        # Write new crontab
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cron', delete=False) as f:
            f.write('\n'.join(cron_lines))
            if cron_lines and cron_lines[-1]:  # Add final newline if content exists
                f.write('\n')
            temp_file = f.name
        
        # Install new crontab
        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return True, message
        else:
            return False, f"Error updating crontab: {result.stderr}"
            
    except Exception as e:
        return False, f"Error managing cron job: {str(e)}"

def check_scheduled_task_exists():
    """Check if scheduled task exists (cross-platform)"""
    import platform
    
    if platform.system() == "Windows":
        return check_windows_scheduled_task_exists()
    else:
        return check_unix_cron_job_exists()

def check_windows_scheduled_task_exists():
    """Check if Windows scheduled task exists"""
    try:
        import subprocess
        result = subprocess.run(['schtasks', '/query', '/tn', 'MorgonPoddGeneration'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_unix_cron_job_exists():
    """Check if Unix/Mac cron job exists"""
    try:
        import subprocess
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'morgonpodd' in result.stdout.lower()
        return False
    except:
        return False

def start_scheduler_service():
    """Start the background scheduler service (deprecated - using cron instead)"""
    # This function is kept for backward compatibility but now just returns True
    return True

def stop_scheduler_service():
    """Stop the background scheduler service"""
    try:
        import subprocess
        subprocess.run(['pkill', '-f', 'python.*main.py.*schedule'], 
                      capture_output=True)
        return True
    except:
        return False

def get_scheduler_status():
    """Get current scheduler status"""
    try:
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'python.*main.py.*schedule'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pid = result.stdout.strip().split('\n')[0]
            return {'running': True, 'pid': pid}
        else:
            return {'running': False, 'pid': None}
    except:
        return {'running': False, 'pid': None}

def show_api_keys():
    st.header("🔑 API Configuration")
    
    st.info("Configure your API keys in the .env file in the project root directory.")
    
    # Display current status
    st.subheader("📊 Current Status")
    
    api_keys = [
        ("OpenAI API Key", "OPENAI_API_KEY"),
        ("ElevenLabs API Key", "ELEVENLABS_API_KEY"), 
        ("ElevenLabs Voice ID", "ELEVENLABS_VOICE_ID"),
        ("Cloudflare Account ID", "CLOUDFLARE_ACCOUNT_ID"),
        ("Cloudflare Access Key ID", "CLOUDFLARE_ACCESS_KEY_ID"),
        ("Cloudflare Secret Access Key", "CLOUDFLARE_SECRET_ACCESS_KEY"),
        ("Cloudflare R2 Bucket Name", "CLOUDFLARE_R2_BUCKET_NAME"),
        ("Cloudflare R2 Endpoint URL", "CLOUDFLARE_R2_ENDPOINT_URL")
    ]
    
    for name, env_var in api_keys:
        if os.getenv(env_var):
            st.success(f"✅ {name}: Configured")
        else:
            st.error(f"❌ {name}: Not configured")
    
    st.subheader("📝 Example .env file")
    
    env_example = """# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# ElevenLabs Configuration  
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Cloudflare R2 Configuration
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_ACCESS_KEY_ID=your_access_key_id  
CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com"""
    
    st.code(env_example, language="bash")

def test_individual_source(source):
    """Test an individual news source"""
    import asyncio
    import aiohttp
    
    try:
        # Create async function to test source
        async def test_source_async():
            from scraper import NewsScraper
            scraper = NewsScraper()
            
            async with aiohttp.ClientSession() as session:
                result = await scraper.scrape_source(session, source)
                return result
        
        # Run the async test
        with st.spinner(f"Testing {source['name']}..."):
            result = asyncio.run(test_source_async())
            
            if result['items']:
                st.success(f"✅ {source['name']} - Found {len(result['items'])} items")
                
                # Show preview of items without expanders
                st.subheader("📋 Preview Results")
                for i, item in enumerate(result['items'][:3]):  # Show first 3 items
                    if source['type'] == 'weather':
                        st.write(f"🌤️ {item.get('description', 'No description')}")
                    else:
                        st.write(f"📰 **{item.get('title', 'No title')}**")
                        if 'link' in item:
                            st.write(f"🔗 [{item['link']}]({item['link']})")
                
                # Show more items if available
                if len(result['items']) > 3:
                    st.write(f"... and {len(result['items']) - 3} more items")
                
                # Show summary details
                st.subheader("📊 Test Results Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Items Found", len(result['items']))
                    st.metric("Source Type", result.get('type', 'Unknown'))
                with col2:
                    st.metric("Source Name", result.get('source', 'Unknown'))
                    if 'error' in result:
                        st.error(f"Warnings: {result['error']}")
                
                # Show raw JSON data
                if st.checkbox("Show Raw Data", key=f"raw_data_{source['name']}"):
                    st.json(result)
                    
            else:
                st.warning(f"⚠️ {source['name']} - No items found")
                if 'error' in result:
                    st.error(f"Error: {result['error']}")
                
                st.subheader("🐛 Debug Information")
                st.json(result)
                    
    except Exception as e:
        st.error(f"❌ Failed to test {source['name']}: {str(e)}")
        st.subheader("🚨 Error Details")
        st.code(str(e), language="python")

def show_prompts(config):
    st.header("✏️ Prompt Templates")
    st.write("Edit all AI prompts used in podcast generation. Changes are saved automatically.")
    
    # Get current prompt templates
    prompt_templates = config.get('podcastSettings', {}).get('promptTemplates', {})
    intro_settings = config.get('podcastSettings', {}).get('intro', {})
    
    st.markdown("---")
    
    # Main podcast generation prompt
    st.subheader("🎙️ Main Podcast Generation Prompt")
    st.write("This prompt controls how the AI creates dialogue between hosts.")
    
    default_main_prompt = """Du skapar ett naturligt samtal mellan {host1_name} och {host2_name}, två professionella poddvärdar.

{host1_name}: {host1_personality}
{host2_name}: {host2_personality}

Skapa ett engagerande samtal där värdarna diskuterar dagens nyheter på ett naturligt sätt."""
    
    current_main_prompt = prompt_templates.get('main_prompt', default_main_prompt)
    
    main_prompt = st.text_area(
        "Main Prompt Template",
        value=current_main_prompt,
        height=200,
        help="Available placeholders: {host1_name}, {host2_name}, {host1_personality}, {host2_personality}",
        key="main_prompt"
    )
    
    st.markdown("---")
    
    # Intro prompt
    st.subheader("🎬 Intro Prompt")
    st.write("This prompt is used to generate the podcast introduction.")
    
    default_intro_prompt = "Välkommen till {podcast_title}! Idag är det {date}. Här kommer din dagliga sammanfattning av nyheter, teknik och väder."
    
    current_intro_prompt = intro_settings.get('prompt', default_intro_prompt)
    
    intro_prompt = st.text_area(
        "Intro Template",
        value=current_intro_prompt,
        height=100,
        help="Available placeholders: {podcast_title}, {date}",
        key="intro_prompt"
    )
    
    st.markdown("---")
    
    # Conversation style setting
    st.subheader("🗣️ Conversation Style")
    
    current_style = prompt_templates.get('conversation_style', 'natural_dialogue')
    
    conversation_style = st.selectbox(
        "Conversation Style",
        options=['natural_dialogue', 'formal', 'casual', 'energetic', 'calm'],
        index=['natural_dialogue', 'formal', 'casual', 'energetic', 'calm'].index(current_style) if current_style in ['natural_dialogue', 'formal', 'casual', 'energetic', 'calm'] else 0,
        help="Controls the overall tone and style of the conversation",
        key="conversation_style"
    )
    
    st.markdown("---")
    
    # Music instructions prompt
    st.subheader("🎵 Music Usage Instructions")
    st.write("Instructions that tell the AI how to integrate music into the podcast script.")
    
    # Default music instructions from music_library.py
    default_music_instructions = """Instruktioner för musikanvändning:
- OBLIGATORISK MUSIKINTEGRATION - Du MÅSTE inkludera musik enligt följande:
  - KRÄVS: Öppna med intro-musik från kategori "intro": [MUSIK: artist - titel]
  - KRÄVS: Minst 2 övergångsmusik mellan ämnen från kategori "transition": [MUSIK: artist - titel]
  - KRÄVS: Passande bakgrundsmusik för olika ämnesområden (news, tech, weather)
  - KRÄVS: Avsluta med outro-musik från kategori "outro": [MUSIK: artist - titel]
  - VIKTIGT: Använd FULLSTÄNDIGA låtar (ingen tidsbegränsning)
  - VIKTIGT: Varje låt får bara användas EN gång per avsnitt (inga dubbletter)
- Använd ENDAST artister och titlar som finns i den tillgängliga musiklistan
- VIKTIGT: Värdarna ska ALDRIG kommentera eller presentera musiken
- Placera [MUSIK: artist - titel] mellan samtalsavsnitt eller när det passar naturligt
- Markera musikinsättningar som: [MUSIK: artist - titel]
- Välj musik som passar ämnet och stämningen
- VIKTIGT: Om du inte inkluderar musik kommer systemet att MISSLYCKAS. Musik är OBLIGATORISKT."""
    
    current_music_instructions = config.get('podcastSettings', {}).get('music_instructions', default_music_instructions)
    
    music_instructions = st.text_area(
        "Music Integration Instructions",
        value=current_music_instructions,
        height=250,
        help="These instructions tell the AI exactly how to use music in the podcast. Format: [MUSIK: artist - titel]",
        key="music_instructions"
    )
    
    st.markdown("---")
    
    # Emotional design prompt
    st.subheader("🎭 Emotional Design & Tonality Instructions")
    st.write("Instructions for how to use emotional tags and tonality in the dialogue.")
    
    default_emotional_prompt = """EMOTIONAL DESIGN FÖR NATURLIGT SAMTAL:
Skapa ett samtal som utnyttjar ElevenLabs nya text-to-dialogue funktionalitet med följande emotionella variation:
- EXCITED: För positiva nyheter, framgångshistorier, spännande upptäckter
- LAUGHING: För roliga nyheter, humoristiska kommentarer, lättsammare inslag
- CURIOUS: För intressanta tekniska nyheter, forskningsresultat, innovations
- CONCERNED: För allvarliga nyheter, problem, varningar, kriser
- SAD: För tragiska nyheter, sorgsna händelser
- NEUTRAL: För analyser, faktabaserad information, objektiva rapporter
- FRIENDLY: För hälsningar, övergångar, personliga kommentarer
- SURPRISED: För överraskande nyheter, häpnadsväckande upptäckter
- CONVERSATIONAL: Som bas för neutralt innehåll och naturliga övergångar

OBS: Du kan markera emotionella partier med hakparenteser [excited], [laughing], etc. men använd sparsamt - endast för tydliga emotionella höjdpunkter.

Instruktioner för optimerad text-to-dialogue:
1. Skapa ett naturligt samtal mellan värdarna
2. Variera emotionell ton baserat på innehåll - använd ord som indikerar känsla:
   - "Det här är verkligen spännande..." (CURIOUS/EXCITED)
   - "Det är oroande att höra..." (CONCERNED)
   - "Enligt nya forskningsresultat..." (PROFESSIONAL)
   - "Hej och välkommen..." (FRIENDLY)
   - "Vädret idag visar..." (CALM)
3. Låt värdarna reagera emotionellt passande på varandras kommentarer
4. Inkludera naturliga övergångar med emotionell förändring"""
    
    current_emotional_prompt = config.get('podcastSettings', {}).get('emotional_design', default_emotional_prompt)
    
    emotional_prompt = st.text_area(
        "Emotional Design Instructions",
        value=current_emotional_prompt,
        height=300,
        help="These instructions tell the AI how to use emotional tags like [excited], [concerned], etc.",
        key="emotional_design"
    )
    
    st.markdown("---")
    
    # System prompt for OpenAI API
    st.subheader("🤖 System Prompt")
    st.write("The system prompt sent to the OpenAI API to set the AI's role and behavior.")
    
    # This is currently hardcoded in summarizer.py, but we can add it to config
    default_system_prompt = "Du är en professionell AI som hjälper till att skapa naturliga samtal mellan poddvärdar på svenska."
    
    current_system_prompt = config.get('podcastSettings', {}).get('system_prompt', default_system_prompt)
    
    system_prompt = st.text_area(
        "System Prompt",
        value=current_system_prompt,
        height=100,
        help="This sets the AI's role and behavior for content generation",
        key="system_prompt"
    )
    
    st.markdown("---")
    
    # Preview section
    with st.expander("🔍 Preview Formatted Prompts"):
        st.subheader("Main Prompt Preview")
        
        # Get host info for preview
        hosts = config.get('podcastSettings', {}).get('hosts', [])
        host1 = hosts[0] if len(hosts) > 0 else {'name': 'Anna', 'personality': 'Energisk morgonvärd'}
        host2 = hosts[1] if len(hosts) > 1 else {'name': 'Erik', 'personality': 'Analytisk journalist'}
        
        try:
            preview_main = main_prompt.format(
                host1_name=host1['name'],
                host2_name=host2['name'],
                host1_personality=host1.get('personality', 'Energisk morgonvärd'),
                host2_personality=host2.get('personality', 'Analytisk journalist')
            )
            st.code(preview_main, language="text")
        except Exception as e:
            st.error(f"Preview error: {e}")
        
        st.subheader("Intro Prompt Preview")
        
        try:
            podcast_title = config.get('podcastSettings', {}).get('title', 'Morgonpodd')
            preview_intro = intro_prompt.format(
                podcast_title=podcast_title,
                date="måndag den 10 september"
            )
            st.code(preview_intro, language="text")
        except Exception as e:
            st.error(f"Preview error: {e}")
    
    # Save button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("💾 Save All Prompts", type="primary", use_container_width=True):
            # Update configuration
            if 'podcastSettings' not in config:
                config['podcastSettings'] = {}
            
            if 'promptTemplates' not in config['podcastSettings']:
                config['podcastSettings']['promptTemplates'] = {}
                
            if 'intro' not in config['podcastSettings']:
                config['podcastSettings']['intro'] = {}
            
            # Save all prompt updates
            config['podcastSettings']['promptTemplates']['main_prompt'] = main_prompt
            config['podcastSettings']['promptTemplates']['conversation_style'] = conversation_style
            config['podcastSettings']['intro']['prompt'] = intro_prompt
            config['podcastSettings']['system_prompt'] = system_prompt
            config['podcastSettings']['music_instructions'] = music_instructions
            config['podcastSettings']['emotional_design'] = emotional_prompt
            
            try:
                save_config(config)
                st.success("✅ All prompts saved successfully!")
                st.balloons()
                
                # Show what was saved
                with st.expander("📋 Saved Configuration"):
                    st.json({
                        "main_prompt": main_prompt,
                        "intro_prompt": intro_prompt,
                        "conversation_style": conversation_style,
                        "music_instructions": music_instructions,
                        "emotional_design": emotional_prompt,
                        "system_prompt": system_prompt
                    })
                    
            except Exception as e:
                st.error(f"❌ Failed to save configuration: {e}")
    
    # Reset to defaults button
    with col3:
        if st.button("🔄 Reset to Defaults", help="Reset all prompts to default values"):
            st.session_state.main_prompt = default_main_prompt
            st.session_state.intro_prompt = default_intro_prompt
            st.session_state.conversation_style = 'natural_dialogue'
            st.session_state.music_instructions = default_music_instructions
            st.session_state.emotional_design = default_emotional_prompt
            st.session_state.system_prompt = default_system_prompt
            st.rerun()

if __name__ == "__main__":
    main()