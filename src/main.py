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
from intro_generator import IntroGenerator

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MorgonPoddService:
    def __init__(self):
        # Define config path for all services
        config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
        
        self.scraper = NewsScraper(sources_file=config_path)
        self.summarizer = PodcastSummarizer()
        self.tts_generator = PodcastGenerator()
        self.rss_generator = RSSGenerator()
        self.uploader = CloudflareUploader()
        self.intro_generator = IntroGenerator()
        
        # Load config for main service
        with open(config_path, 'r', encoding='utf-8') as f:
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
            
            # Step 3: Generate intro audio
            logger.info("Step 3a: Generating intro...")
            intro_file = self.intro_generator.generate_intro_audio()
            if intro_file:
                intro_file = self.intro_generator.combine_with_jingle(intro_file)
            
            # Step 3b: Generate main audio
            logger.info("Step 3b: Generating main content audio with ElevenLabs...")
            main_audio_file = self.tts_generator.generate_audio(script)
            
            # Step 3c: Combine intro + main content
            if intro_file and os.path.exists(intro_file):
                logger.info("Step 3c: Combining intro with main content...")
                audio_file = self.combine_intro_and_main(intro_file, main_audio_file)
            else:
                logger.info("No intro generated, using main content only")
                audio_file = main_audio_file
            
            # Step 4: Generate metadata
            logger.info("Step 4: Creating episode metadata...")
            metadata = self.tts_generator.generate_episode_metadata(script_file, audio_file, script)
            
            # Step 5: Update RSS feed
            logger.info("Step 5: Updating RSS feed...")
            self.rss_generator.generate_feed()
            
            # Step 6: Upload to Cloudflare
            logger.info("Step 6: Uploading to Cloudflare R2...")
            self.uploader.upload_episode(audio_file, metadata)
            self.uploader.upload_feed()
            self.uploader.upload_static_files()
            
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
    
    def combine_intro_and_main(self, intro_file: str, main_file: str) -> str:
        """Combine intro and main content with smooth crossfade transition"""
        import time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() % 10000)}"
        output_file = f"episodes/final_episode_{timestamp}.mp3"
        
        try:
            import subprocess
            
            # Get intro settings for crossfade configuration
            intro_settings = self.config.get('podcastSettings', {}).get('intro', {})
            crossfade_duration = intro_settings.get('crossfade_duration', 1.5)  # 1.5 seconds crossfade
            
            # Pre-normalize both files to avoid frame padding issues
            # Save normalized files in episodes directory for debugging
            timestamp_debug = datetime.now().strftime("%Y%m%d_%H%M%S")
            intro_norm = f"episodes/debug_intro_norm_{timestamp_debug}.wav"
            main_norm = f"episodes/debug_main_norm_{timestamp_debug}.wav"
            
            # Normalize intro to stereo 44.1kHz WAV
            subprocess.run([
                'ffmpeg', '-y', '-i', intro_file,
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                intro_norm
            ], check=True, capture_output=True)
            
            # Normalize main to stereo 44.1kHz WAV  
            subprocess.run([
                'ffmpeg', '-y', '-i', main_file,
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', 
                main_norm
            ], check=True, capture_output=True)
            
            # Now create crossfade with normalized files
            cmd = [
                'ffmpeg', '-i', intro_norm, '-i', main_norm,
                '-filter_complex', 
                f'[0:a]afade=t=out:st=end-{crossfade_duration}:d={crossfade_duration}[intro_fade];'
                f'[1:a]afade=t=in:st=0:d={crossfade_duration}[main_fade];'
                f'[intro_fade][main_fade]concat=n=2:v=0:a=1[out]',
                '-map', '[out]', '-acodec', 'libmp3lame', '-ar', '44100', '-ac', '2',
                '-y', output_file
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Combined episode with crossfade transition created: {output_file}")
            
            # Keep temporary files for debugging - don't clean up yet
            logger.info(f"Preserved files for debugging:")
            logger.info(f"  Intro file: {intro_file}")
            logger.info(f"  Main file: {main_file}")
            logger.info(f"  Combined file: {output_file}")
            # TODO: Remove cleanup to allow inspection of intermediate files
            # if os.path.exists(intro_file):
            #     os.remove(intro_file)
            # if os.path.exists(main_file) and main_file != output_file:
            #     os.remove(main_file)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error combining intro and main content with crossfade: {e}")
            
            # Fallback to simple concatenation without crossfade
            try:
                # Use same two-step normalization approach for consistency
                # Save normalized files in episodes directory for debugging
                timestamp_debug_fb = datetime.now().strftime("%Y%m%d_%H%M%S")
                intro_norm_fb = f"episodes/debug_intro_norm_fb_{timestamp_debug_fb}.wav"
                main_norm_fb = f"episodes/debug_main_norm_fb_{timestamp_debug_fb}.wav"
                
                # Normalize both files to stereo 44.1kHz WAV
                subprocess.run([
                    'ffmpeg', '-y', '-i', intro_file,
                    '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                    intro_norm_fb
                ], check=True, capture_output=True)
                
                subprocess.run([
                    'ffmpeg', '-y', '-i', main_file,
                    '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', 
                    main_norm_fb
                ], check=True, capture_output=True)
                
                # Simple concatenation with normalized files
                cmd = [
                    'ffmpeg', '-i', intro_norm_fb, '-i', main_norm_fb,
                    '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]',
                    '-map', '[out]', '-acodec', 'libmp3lame', '-ar', '44100', '-ac', '2',
                    '-y', output_file
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Combined episode created (fallback): {output_file}")
                
                # Keep temporary files for debugging - don't clean up yet
                logger.info(f"Preserved files for debugging (fallback):")
                logger.info(f"  Intro file: {intro_file}")
                logger.info(f"  Main file: {main_file}")
                logger.info(f"  Combined file: {output_file}")
                # TODO: Remove cleanup to allow inspection of intermediate files
                # if os.path.exists(intro_file):
                #     os.remove(intro_file)
                # if os.path.exists(main_file) and main_file != output_file:
                #     os.remove(main_file)
                
                return output_file
            except Exception as fallback_error:
                logger.error(f"Fallback concatenation also failed: {fallback_error}")
                return main_file
    
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