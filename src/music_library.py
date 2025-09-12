import os
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
import shutil
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicLibrary:
    def __init__(self, music_dir: str = "audio/music", config_file: str = "music_library.json", sources_config_file: str = "sources.json"):
        self.music_dir = Path(music_dir)
        self.config_file = config_file
        self.sources_config_file = sources_config_file
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.library = self.load_library()
        self.sources_config = self.load_sources_config()
    
    def load_library(self) -> Dict[str, Any]:
        """Load music library from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading music library: {e}")
        
        return {
            "tracks": {},
            "categories": {
                "intro": "Intro och öppning",
                "news": "Nyheter och seriöst innehåll", 
                "tech": "Teknik och innovation",
                "transition": "Övergångar mellan ämnen",
                "weather": "Väder och avslutning",
                "upbeat": "Energisk och positiv",
                "calm": "Lugn och avslappnande",
                "outro": "Avslutning och outro"
            },
            "moods": {
                "serious": "Seriös och professionell",
                "upbeat": "Energisk och positiv", 
                "calm": "Lugn och avslappnande",
                "mysterious": "Mystisk och spännande",
                "dramatic": "Dramatisk och intensiv",
                "playful": "Lekfull och avslappnad"
            }
        }
    
    def load_sources_config(self) -> Dict[str, Any]:
        """Load sources configuration file"""
        if os.path.exists(self.sources_config_file):
            try:
                with open(self.sources_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading sources config: {e}")
        return {}
    
    def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:8]  # Use first 8 characters for shorter ID
    
    def save_library(self):
        """Save music library to config file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.library, f, ensure_ascii=False, indent=2)
            logger.info("Music library saved")
        except Exception as e:
            logger.error(f"Error saving music library: {e}")
    
    def add_track(self, file_path: str, artist: str, title: str, 
                  categories: List[str] = None, moods: List[str] = None,
                  duration: float = None, description: str = "") -> str:
        """Add a track to the music library"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Music file not found: {file_path}")
        
        # Generate unique ID based on MD5 hash of file
        track_id = self._calculate_md5(file_path)
        
        # Check if track already exists
        if track_id in self.library["tracks"]:
            logger.info(f"Track already exists with ID: {track_id}")
            return track_id
        
        # Copy file to music directory
        file_extension = Path(file_path).suffix
        new_filename = f"{track_id}{file_extension}"
        new_path = self.music_dir / new_filename
        
        shutil.copy2(file_path, new_path)
        logger.info(f"Copied music file to: {new_path}")
        
        # Add track metadata
        track_metadata = {
            "id": track_id,
            "artist": artist,
            "title": title,
            "filename": new_filename,
            "path": str(new_path),
            "categories": categories or [],
            "moods": moods or [],
            "duration": duration,
            "description": description,
            "added_at": datetime.now().isoformat(),
            "file_size": os.path.getsize(new_path)
        }
        
        self.library["tracks"][track_id] = track_metadata
        self.save_library()
        
        logger.info(f"Added track: {artist} - {title} (ID: {track_id})")
        return track_id
    
    def get_tracks_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tracks by category"""
        return [
            track for track in self.library["tracks"].values()
            if category in track.get("categories", [])
        ]
    
    def get_tracks_by_mood(self, mood: str) -> List[Dict[str, Any]]:
        """Get tracks by mood"""
        return [
            track for track in self.library["tracks"].values()
            if mood in track.get("moods", [])
        ]
    
    def search_tracks(self, query: str) -> List[Dict[str, Any]]:
        """Search tracks by artist, title, or description"""
        query = query.lower()
        results = []
        
        for track in self.library["tracks"].values():
            if (query in track["artist"].lower() or 
                query in track["title"].lower() or
                query in track.get("description", "").lower()):
                results.append(track)
        
        return results
    
    def remove_track(self, track_id: str) -> bool:
        """Remove a track from library"""
        if track_id not in self.library["tracks"]:
            return False
        
        track = self.library["tracks"][track_id]
        
        # Remove file
        if os.path.exists(track["path"]):
            os.remove(track["path"])
            logger.info(f"Removed music file: {track['path']}")
        
        # Remove from library
        del self.library["tracks"][track_id]
        self.save_library()
        
        logger.info(f"Removed track: {track['artist']} - {track['title']}")
        return True
    
    def get_all_tracks(self) -> List[Dict[str, Any]]:
        """Get all tracks"""
        return list(self.library["tracks"].values())
    
    def get_music_prompt_context(self) -> str:
        """Generate context for AI prompt about available music"""
        if not self.library["tracks"]:
            return "Ingen bakgrundsmusik är tillgänglig."
        
        context = "Tillgänglig bakgrundsmusik (använd ID för att referera):\n\n"
        
        # Group by category
        for category_id, category_name in self.library["categories"].items():
            tracks = self.get_tracks_by_category(category_id)
            if tracks:
                context += f"**{category_name}:**\n"
                for track in tracks:
                    duration_info = f" ({track['duration']:.1f}s)" if track.get('duration') else ""
                    context += f"- ID: {track['id']} | {track['artist']} - {track['title']}{duration_info}\n"
                    if track.get('description'):
                        context += f"  Beskrivning: {track['description']}\n"
                context += "\n"
        
        context += "\nVIKTIGT: Använd [MUSIK: ID] format där ID är den 8-siffriga koden ovan (t.ex. [MUSIK: a1b2c3d4])\n"
        context += "Använd ALDRIG artistnamn eller låttitlar i musikmarkörerna - endast ID:n.\n\n"
        
        return context
    
    def extract_music_cues_from_script(self, script: str) -> List[Dict[str, Any]]:
        """Extract music cues from script"""
        import re
        
        cues = []
        
        # First, try to find new ID-based format: [MUSIK: a1b2c3d4]
        id_pattern = r'\[MUSIK:\s*([a-f0-9]{8})\]'
        id_matches = re.findall(id_pattern, script, re.IGNORECASE)
        
        for track_id in id_matches:
            track_id = track_id.lower()
            if track_id in self.library["tracks"]:
                track = self.library["tracks"][track_id]
                cue = {
                    "artist": track["artist"],
                    "title": track["title"],
                    "duration": None,  # Use full track
                    "track": track,
                    "marker": f"[MUSIK: {track_id}]",
                    "id": track_id
                }
                cues.append(cue)
                logger.info(f"Found music cue by ID: {track_id} ({track['artist']} - {track['title']})")
            else:
                logger.warning(f"Music track ID not found: {track_id}")
        
        # If no ID-based markers found, fall back to old format: [MUSIK: artist - title]
        if not cues:
            artist_title_pattern = r'\[MUSIK:\s*([^-]+?)\s*-\s*([^\],]+?)(?:,\s*(\d+(?:\.\d+)?)\s*sekunder?)?\]'
            matches = re.findall(artist_title_pattern, script)
            
            for match in matches:
                artist, title, duration = match
                artist = artist.strip()
                title = title.strip()
                duration = float(duration) if duration else None
                
                # Find matching track
                matching_tracks = [
                    track for track in self.library["tracks"].values()
                    if (track["artist"].lower() == artist.lower() and 
                        track["title"].lower() == title.lower())
                ]
                
                if matching_tracks:
                    track = matching_tracks[0]
                    cue = {
                        "artist": artist,
                        "title": title,
                        "duration": duration,
                        "track": track,
                        "marker": f"[MUSIK: {artist} - {title}" + (f", {duration} sekunder]" if duration else "]"),
                        "id": track["id"]
                    }
                    cues.append(cue)
                    logger.info(f"Found music cue: {artist} - {title} (ID: {track['id']})")
                else:
                    logger.warning(f"Music track not found: {artist} - {title}")
        
        return cues
    
    def migrate_existing_tracks(self):
        """Migrate existing tracks to use MD5-based IDs"""
        logger.info("Starting migration to MD5-based track IDs...")
        
        # Get all existing tracks
        old_tracks = self.library["tracks"].copy()
        updated_tracks = {}
        
        for old_id, track_data in old_tracks.items():
            try:
                # Skip if already using MD5 format (8 hex characters)
                if len(old_id) == 8 and all(c in '0123456789abcdef' for c in old_id):
                    updated_tracks[old_id] = track_data
                    continue
                
                file_path = track_data.get("path")
                if not file_path or not os.path.exists(file_path):
                    logger.warning(f"Track file not found: {file_path}, skipping migration")
                    continue
                
                # Calculate new MD5-based ID
                new_id = self._calculate_md5(file_path)
                
                # Update track data with new ID
                track_data["id"] = new_id
                
                # Rename file to match new ID
                old_path = Path(file_path)
                new_filename = f"{new_id}{old_path.suffix}"
                new_path = self.music_dir / new_filename
                
                # Move file if names differ
                if old_path.name != new_filename:
                    shutil.move(str(old_path), str(new_path))
                    track_data["filename"] = new_filename
                    track_data["path"] = str(new_path)
                    logger.info(f"Migrated: {track_data['artist']} - {track_data['title']} (ID: {old_id} → {new_id})")
                
                updated_tracks[new_id] = track_data
                
            except Exception as e:
                logger.error(f"Failed to migrate track {old_id}: {e}")
                # Keep old track on error
                updated_tracks[old_id] = track_data
        
        # Update library
        self.library["tracks"] = updated_tracks
        self.save_library()
        
        logger.info(f"Migration complete. Total tracks: {len(updated_tracks)}")
        return len(updated_tracks)

def main():
    library = MusicLibrary()
    print("Music library initialized")
    
    # Run migration
    track_count = library.migrate_existing_tracks()
    print(f"Migration completed. Total tracks: {track_count}")
    
    # Show example of music prompt context
    context = library.get_music_prompt_context()
    print("\nMusic prompt context:")
    print(context)

if __name__ == "__main__":
    main()