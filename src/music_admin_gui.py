import streamlit as st
import os
import sys
from pathlib import Path
from music_library import MusicLibrary

st.set_page_config(
    page_title="Music Library Admin",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🎵 Morgonpodd Music Library Administration")
    st.markdown("---")
    
    # Initialize music library
    music_lib = MusicLibrary()
    
    # Sidebar with statistics
    st.sidebar.header("📊 Library Stats")
    tracks = music_lib.get_all_tracks()
    st.sidebar.metric("Total Tracks", len(tracks))
    
    # Category breakdown
    categories = {}
    for track in tracks:
        for cat in track.get('categories', []):
            categories[cat] = categories.get(cat, 0) + 1
    
    if categories:
        st.sidebar.subheader("📂 Categories")
        for cat, count in categories.items():
            st.sidebar.text(f"{cat}: {count}")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🔄 Upload Music", "📚 Browse Library", "⚙️ Settings"])
    
    with tab1:
        upload_music_interface(music_lib)
    
    with tab2:
        browse_library_interface(music_lib)
    
    with tab3:
        settings_interface(music_lib)

def upload_music_interface(music_lib):
    st.header("📁 Upload New Music")
    
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
                    # Extract default values from filename
                    name_parts = uploaded_file.name.replace('.mp3', '').replace('_', ' ').replace('-', ' - ')
                    
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
    st.header("📚 Music Library Browser")
    
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
    st.subheader(f"📼 Found {len(filtered_tracks)} track(s)")
    
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
                if st.button("🗑️ Delete", key=f"delete_{track['id']}"):
                    if music_lib.remove_track(track['id']):
                        st.success(f"✅ Deleted '{track['artist']} - {track['title']}'")
                        st.rerun()

def settings_interface(music_lib):
    st.header("⚙️ Library Settings")
    
    # Category management
    st.subheader("📂 Manage Categories")
    
    categories = music_lib.library["categories"]
    
    # Add new category
    with st.expander("➕ Add New Category"):
        col1, col2 = st.columns(2)
        with col1:
            new_cat_id = st.text_input("Category ID", placeholder="e.g., 'action'")
        with col2:
            new_cat_name = st.text_input("Category Name", placeholder="e.g., 'Action and Adventure'")
        
        if st.button("Add Category") and new_cat_id and new_cat_name:
            music_lib.library["categories"][new_cat_id] = new_cat_name
            music_lib.save_library()
            st.success(f"Added category: {new_cat_name}")
            st.rerun()
    
    # Current categories
    st.write("**Current Categories:**")
    for cat_id, cat_name in categories.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(f"{cat_id}: {cat_name}")
        with col2:
            if st.button("🗑️", key=f"del_cat_{cat_id}"):
                del music_lib.library["categories"][cat_id]
                music_lib.save_library()
                st.success(f"Deleted category: {cat_name}")
                st.rerun()
    
    st.divider()
    
    # Mood management
    st.subheader("🎭 Manage Moods")
    
    moods = music_lib.library["moods"]
    
    # Add new mood
    with st.expander("➕ Add New Mood"):
        col1, col2 = st.columns(2)
        with col1:
            new_mood_id = st.text_input("Mood ID", placeholder="e.g., 'energetic'")
        with col2:
            new_mood_name = st.text_input("Mood Name", placeholder="e.g., 'High Energy and Exciting'")
        
        if st.button("Add Mood") and new_mood_id and new_mood_name:
            music_lib.library["moods"][new_mood_id] = new_mood_name
            music_lib.save_library()
            st.success(f"Added mood: {new_mood_name}")
            st.rerun()
    
    # Current moods
    st.write("**Current Moods:**")
    for mood_id, mood_name in moods.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(f"{mood_id}: {mood_name}")
        with col2:
            if st.button("🗑️", key=f"del_mood_{mood_id}"):
                del music_lib.library["moods"][mood_id]
                music_lib.save_library()
                st.success(f"Deleted mood: {mood_name}")
                st.rerun()
    
    st.divider()
    
    # AI Preview
    st.subheader("🤖 AI Context Preview")
    
    if st.button("👁️ Preview AI Music Context"):
        context = music_lib.get_music_prompt_context()
        st.code(context, language="markdown")
        
    st.divider()
    
    # Export/Import
    st.subheader("💾 Backup & Restore")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
    
    with col2:
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

if __name__ == "__main__":
    main()