import os
import json
import logging
from datetime import datetime, timezone
import pytz
from feedgen.feed import FeedGenerator
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSGenerator:
    def __init__(self):
        self.fg = FeedGenerator()
        self.base_url = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', 'https://morgonpodd.example.com')
        
        # Load podcast settings from parent directory
        config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.settings = config['podcastSettings']
        
        self.setup_feed()
    
    def setup_feed(self):
        """Setup the basic feed information"""
        self.fg.load_extension('podcast')
        
        # Basic feed info
        self.fg.title(os.getenv('PODCAST_TITLE', self.settings['title']))
        self.fg.description(self.settings['description'])
        self.fg.author({
            'name': os.getenv('PODCAST_AUTHOR', self.settings['author']),
            'email': os.getenv('PODCAST_EMAIL', 'podcast@example.com')
        })
        self.fg.link(href=self.base_url, rel='alternate')
        self.fg.language(self.settings['language'])
        
        # Podcast-specific settings
        self.fg.podcast.itunes_author(self.settings['author'])
        self.fg.podcast.itunes_category(self.settings['category'])
        self.fg.podcast.itunes_explicit('no' if not self.settings['explicit'] else 'yes')
        self.fg.podcast.itunes_owner(
            name=os.getenv('PODCAST_AUTHOR', self.settings['author']),
            email=os.getenv('PODCAST_EMAIL', 'podcast@example.com')
        )
        self.fg.podcast.itunes_summary(self.settings['description'])
        
        # Use configured cover image or default
        cover_image_filename = os.path.basename(self.settings.get('cover_image', 'public/cover.jpg'))
        self.fg.podcast.itunes_image(f"{self.base_url}/{cover_image_filename}")
        
        # Feed logo/image
        self.fg.logo(f"{self.base_url}/{cover_image_filename}")
        self.fg.image(url=f"{self.base_url}/{cover_image_filename}", 
                     title=self.settings['title'],
                     link=self.base_url)
    
    def add_episode(self, episode_metadata: Dict):
        """Add an episode to the feed"""
        fe = self.fg.add_entry()
        
        # Basic episode info
        fe.id(episode_metadata['guid'])
        fe.title(episode_metadata['title'])
        fe.description(episode_metadata['description'])
        
        # Publication date - ensure timezone info
        pub_date = datetime.fromisoformat(episode_metadata['pub_date'])
        if pub_date.tzinfo is None:
            # Add Stockholm timezone if missing
            stockholm_tz = pytz.timezone('Europe/Stockholm')
            pub_date = stockholm_tz.localize(pub_date)
        fe.published(pub_date)
        
        # Audio file - use the standardized episode filename format
        episode_number = episode_metadata['episode_number']
        audio_url = f"{self.base_url}/episodes/episode_{episode_number}.mp3"
        
        # Try to get file size from metadata, or use a reasonable default
        file_size = episode_metadata.get('file_size', 0)
        if file_size == 0 and 'audio_file' in episode_metadata:
            # Try to get size from local file if available
            try:
                if os.path.exists(episode_metadata['audio_file']):
                    file_size = os.path.getsize(episode_metadata['audio_file'])
            except:
                pass
        
        # Use a reasonable default if still 0 (about 5MB for 10min episode)
        if file_size == 0:
            file_size = 5 * 1024 * 1024  # 5MB default
            
        fe.enclosure(audio_url, file_size, 'audio/mpeg')
        
        # Link to episode page
        fe.link(href=f"{self.base_url}/episode/{episode_metadata['episode_number']}")
        
        # iTunes specific
        fe.podcast.itunes_duration(episode_metadata.get('duration', '10:00'))
        fe.podcast.itunes_episode(episode_metadata['episode_number'])
        
        logger.info(f"Added episode: {episode_metadata['title']}")
    
    def load_all_episodes(self):
        """Load all existing episodes from metadata files"""
        episodes_dir = 'episodes'
        if not os.path.exists(episodes_dir):
            logger.warning("No episodes directory found")
            return
        
        meta_files = [f for f in os.listdir(episodes_dir) if f.endswith('_meta.json')]
        episodes = []
        
        for meta_file in meta_files:
            try:
                with open(os.path.join(episodes_dir, meta_file), 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    episodes.append(metadata)
            except Exception as e:
                logger.error(f"Error loading {meta_file}: {e}")
        
        # Sort by date (newest first)
        episodes.sort(key=lambda x: x['pub_date'], reverse=True)
        
        # Add to feed (limit to last 50 episodes)
        for episode in episodes[:50]:
            self.add_episode(episode)
    
    def generate_feed(self, output_file: str = 'public/feed.xml'):
        """Generate the RSS feed file"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Load all episodes
        self.load_all_episodes()
        
        # Write the feed
        self.fg.rss_file(output_file)
        logger.info(f"RSS feed generated: {output_file}")
        
        # Also generate a JSON version for debugging
        json_file = output_file.replace('.xml', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            # Extract basic info for JSON
            feed_info = {
                'title': self.settings['title'],
                'description': self.settings['description'],
                'episode_count': len(self.fg.entry()),
                'last_updated': datetime.now().isoformat(),
                'feed_url': f"{self.base_url}/feed.xml"
            }
            json.dump(feed_info, f, ensure_ascii=False, indent=2)
        
        return output_file

def main():
    generator = RSSGenerator()
    feed_file = generator.generate_feed()
    logger.info(f"Feed generated successfully: {feed_file}")
    return feed_file

if __name__ == "__main__":
    main()