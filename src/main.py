#!/usr/bin/env python3
import asyncio
import os
import logging
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
import json

# Import our modules
from scraper import NewsScraper
from summarizer import PodcastSummarizer
from tts_generator import PodcastGenerator
from rss_generator import RSSGenerator
from cloudflare_uploader import CloudflareUploader

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MorgonPoddService:
    def __init__(self):
        self.scraper = NewsScraper()
        self.summarizer = PodcastSummarizer()
        self.tts_generator = PodcastGenerator()
        self.rss_generator = RSSGenerator()
        self.uploader = CloudflareUploader()
        
        # Load config
        with open('sources.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    async def generate_episode(self):
        """Generate a complete podcast episode"""
        try:
            logger.info("=== Starting podcast generation ===")
            start_time = datetime.now()
            
            # Step 1: Scrape content
            logger.info("Step 1: Scraping content...")
            scraped_data = await self.scraper.scrape_all()
            
            # Save scraped data
            with open('scraped_content.json', 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
            # Step 2: Generate script
            logger.info("Step 2: Generating podcast script...")
            script = self.summarizer.create_podcast_script(scraped_data)
            script_file = self.summarizer.save_script(script)
            
            # Step 3: Generate audio
            logger.info("Step 3: Generating audio with ElevenLabs...")
            audio_file = self.tts_generator.generate_audio(script)
            
            # Step 4: Generate metadata
            logger.info("Step 4: Creating episode metadata...")
            metadata = self.tts_generator.generate_episode_metadata(script_file, audio_file)
            
            # Step 5: Update RSS feed
            logger.info("Step 5: Updating RSS feed...")
            self.rss_generator.generate_feed()
            
            # Step 6: Upload to Cloudflare
            logger.info("Step 6: Uploading to Cloudflare R2...")
            self.uploader.upload_episode(audio_file, metadata)
            self.uploader.upload_feed()
            
            # Calculate total time
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"=== Episode generated successfully in {duration:.1f} seconds ===")
            logger.info(f"Episode: {metadata['title']}")
            logger.info(f"Audio file: {audio_file}")
            logger.info(f"Public URL: {self.config['podcastSettings'].get('publicUrl', 'Not configured')}/feed.xml")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error generating episode: {e}")
            raise
    
    def run_scheduled(self):
        """Run the podcast generation on schedule"""
        generate_time = self.config['podcastSettings'].get('generateTime', '06:00')
        
        # Schedule daily generation
        schedule.every().day.at(generate_time).do(
            lambda: asyncio.run(self.generate_episode())
        )
        
        logger.info(f"Scheduled daily podcast generation at {generate_time}")
        logger.info("Service running... Press Ctrl+C to stop")
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_once(self):
        """Generate a single episode now"""
        asyncio.run(self.generate_episode())

def main():
    import sys
    
    service = MorgonPoddService()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'schedule':
        # Run on schedule
        service.run_scheduled()
    else:
        # Generate once
        service.run_once()

if __name__ == "__main__":
    main()