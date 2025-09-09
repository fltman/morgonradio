import os
import json
import logging
import boto3
from botocore.config import Config
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudflareUploader:
    def __init__(self):
        # Configure S3 client for Cloudflare R2
        endpoint_url = os.getenv('CLOUDFLARE_R2_ENDPOINT')
        if not endpoint_url:
            account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
            if account_id:
                endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
            else:
                # Fallback to jurisdiction-specific endpoint
                endpoint_url = "https://f3ff16684b278292a1862429e0262527.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv('CLOUDFLARE_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY'),
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3},
                connect_timeout=60,
                read_timeout=60
            ),
            region_name='auto'
        )
        self.bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET', 'lipsync-tool')
        self.public_url = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', 'https://morgonpodd.example.com')
    
    def upload_file(self, local_path: str, remote_path: str = None, content_type: str = None) -> str:
        """Upload a file to Cloudflare R2"""
        if not remote_path:
            remote_path = os.path.basename(local_path)
        
        # Determine content type
        if not content_type:
            if local_path.endswith('.mp3'):
                content_type = 'audio/mpeg'
            elif local_path.endswith('.xml'):
                content_type = 'application/xml'
            elif local_path.endswith('.json'):
                content_type = 'application/json'
            elif local_path.endswith('.html'):
                content_type = 'text/html'
            elif local_path.endswith('.jpg') or local_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif local_path.endswith('.png'):
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'
        
        try:
            with open(local_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=remote_path,
                    Body=f,
                    ContentType=content_type,
                    CacheControl='public, max-age=3600'
                )
            
            public_url = f"{self.public_url}/{remote_path}"
            logger.info(f"Uploaded {local_path} to {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Upload failed for {local_path}: {e}")
            raise
    
    def upload_episode(self, audio_file: str, metadata: Dict) -> Dict:
        """Upload an episode and its metadata"""
        episode_number = metadata['episode_number']
        
        # Upload audio file
        audio_remote = f"episodes/episode_{episode_number}.mp3"
        audio_url = self.upload_file(audio_file, audio_remote)
        
        # Update metadata with public URL
        metadata['audio_url'] = audio_url
        metadata['uploaded_at'] = datetime.now().isoformat()
        
        # Save and upload metadata
        meta_file = f"episodes/episode_{episode_number}_meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        meta_remote = f"episodes/episode_{episode_number}_meta.json"
        self.upload_file(meta_file, meta_remote)
        
        return metadata
    
    def upload_feed(self, feed_file: str = 'public/feed.xml'):
        """Upload RSS feed"""
        self.upload_file(feed_file, 'feed.xml')
        
        # Also upload the JSON version if it exists
        json_file = feed_file.replace('.xml', '.json')
        if os.path.exists(json_file):
            self.upload_file(json_file, 'feed.json')
    
    def upload_static_files(self):
        """Upload static files like images and HTML"""
        # Load config to get cover image path
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                cover_image_path = config.get('podcastSettings', {}).get('cover_image', 'public/cover.jpg')
        except:
            cover_image_path = 'public/cover.jpg'
        
        static_files = [
            ('public/index.html', 'index.html'),
            (cover_image_path, os.path.basename(cover_image_path))
        ]
        
        # Add legacy logo.png if it exists
        if os.path.exists('public/logo.png'):
            static_files.append(('public/logo.png', 'logo.png'))
        
        for local, remote in static_files:
            if os.path.exists(local):
                self.upload_file(local, remote)
                logger.info(f"Uploaded static file: {local} -> {remote}")
            else:
                logger.warning(f"Static file not found: {local}")
    
    def sync_all_episodes(self):
        """Sync all local episodes to Cloudflare R2"""
        episodes_dir = 'episodes'
        if not os.path.exists(episodes_dir):
            logger.warning("No episodes directory found")
            return
        
        # Find all audio files
        audio_files = [f for f in os.listdir(episodes_dir) if f.endswith('.mp3')]
        
        for audio_file in audio_files:
            audio_path = os.path.join(episodes_dir, audio_file)
            
            # Find corresponding metadata
            meta_file = audio_file.replace('.mp3', '_metadata.json')
            meta_path = os.path.join(episodes_dir, meta_file)
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Upload episode
                self.upload_episode(audio_path, metadata)
        
        logger.info(f"Synced {len(audio_files)} episodes to Cloudflare R2")

def main():
    uploader = CloudflareUploader()
    
    # Upload latest episode if it exists
    episodes_dir = 'episodes'
    if os.path.exists(episodes_dir):
        audio_files = [f for f in os.listdir(episodes_dir) if f.endswith('.mp3')]
        if audio_files:
            latest = max(audio_files, key=lambda x: os.path.getctime(os.path.join(episodes_dir, x)))
            audio_path = os.path.join(episodes_dir, latest)
            
            # Load metadata
            meta_file = latest.replace('.mp3', '_metadata.json')
            meta_path = os.path.join(episodes_dir, meta_file)
            
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Upload episode
                uploader.upload_episode(audio_path, metadata)
    
    # Upload feed
    if os.path.exists('public/feed.xml'):
        uploader.upload_feed()
    
    # Upload static files
    uploader.upload_static_files()
    
    logger.info("Upload completed")

if __name__ == "__main__":
    main()