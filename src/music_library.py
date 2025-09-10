import os
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicLibrary:
    def __init__(self, music_dir: str = "audio/music", config_file: str = "music_library.json"):
        self.music_dir = Path(music_dir)
        self.config_file = config_file
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.library = self.load_library()
    
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
        
        # Generate unique ID for track
        track_id = f"{artist}_{title}".lower().replace(" ", "_").replace("-", "_")
        track_id = ''.join(c for c in track_id if c.isalnum() or c == '_')
        
        # Copy file to music directory
        file_extension = Path(file_path).suffix
        new_filename = f"{track_id}{file_extension}"
        new_path = self.music_dir / new_filename
        
        if new_path.exists():
            # Add timestamp if file exists
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{track_id}_{timestamp}{file_extension}"
            new_path = self.music_dir / new_filename
            track_id = f"{track_id}_{timestamp}"
        
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
        
        context = "Tillgänglig bakgrundsmusik:\n\n"
        
        # Group by category
        for category_id, category_name in self.library["categories"].items():
            tracks = self.get_tracks_by_category(category_id)
            if tracks:
                context += f"**{category_name}:**\n"
                for track in tracks:
                    duration_info = f" ({track['duration']:.1f}s)" if track.get('duration') else ""
                    context += f"- {track['artist']} - {track['title']}{duration_info}\n"
                    if track.get('description'):
                        context += f"  Beskrivning: {track['description']}\n"
                context += "\n"
        
        context += """
Instruktioner för musikanvändning:
- Använd musik sparsamt och endast när det förbättrar upplevelsen
- Markera musikinsättningar i ditt manus som: [MUSIK: artist - titel, X sekunder]
- Välj musik som passar ämnet och stämningen
- Typiska användningsområden:
  * Intro/outro musik (5-10 sekunder)
  * Övergångar mellan ämnen (3-5 sekunder)
  * Understryka viktiga nyheter (2-3 sekunder under tal)
  * Väder-segment (bakgrundsmusik)
"""
        
        return context
    
    def extract_music_cues_from_script(self, script: str) -> List[Dict[str, Any]]:
        """Extract music cues from script"""
        import re
        
        # Find music markers like [MUSIK: artist - title] or [MUSIK: artist - title, X sekunder]
        pattern = r'\[MUSIK:\s*([^-]+?)\s*-\s*([^\],]+?)(?:,\s*(\d+(?:\.\d+)?)\s*sekunder?)?\]'
        matches = re.findall(pattern, script)
        
        cues = []
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
                cue = {
                    "artist": artist,
                    "title": title,
                    "duration": duration,
                    "track": matching_tracks[0],
                    "marker": f"[MUSIK: {artist} - {title}" + (f", {duration} sekunder]" if duration else "]")
                }
                cues.append(cue)
                logger.info(f"Found music cue: {artist} - {title}")
            else:
                logger.warning(f"Music track not found: {artist} - {title}")
        
        return cues

def main():
    library = MusicLibrary()
    print("Music library initialized")
    print(f"Total tracks: {len(library.get_all_tracks())}")

if __name__ == "__main__":
    main()