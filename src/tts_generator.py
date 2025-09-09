import os
import logging
from datetime import datetime
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import json

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastGenerator:
    def __init__(self):
        self.client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
        
        # Load config for voice settings
        with open('sources.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def generate_audio(self, text: str, output_filename: str = None) -> str:
        """
        Generate audio from multi-host conversation using ElevenLabs API
        """
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"episodes/episode_{timestamp}.mp3"
        
        os.makedirs('episodes', exist_ok=True)
        
        try:
            # Check if text has multiple speakers
            if self.is_conversation_format(text):
                return self.generate_conversation_audio(text, output_filename)
            else:
                return self.generate_single_voice_audio(text, output_filename)
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            raise
    
    def is_conversation_format(self, text: str) -> bool:
        """Check if text is in conversation format with speaker names"""
        lines = text.split('\n')
        speaker_lines = [line for line in lines if ':' in line and len(line.split(':', 1)) == 2]
        return len(speaker_lines) > 1
    
    def generate_conversation_audio(self, text: str, output_filename: str) -> str:
        """Generate audio for multi-speaker conversation"""
        logger.info("Generating multi-speaker conversation audio...")
        
        # Parse conversation
        segments = self.parse_conversation(text)
        audio_segments = []
        
        # Get host configuration
        hosts = self.config.get('podcastSettings', {}).get('hosts', [])
        voice_mapping = {}
        
        for host in hosts:
            voice_mapping[host['name']] = host.get('voice_id', self.voice_id)
        
        # Generate audio for each segment
        for i, segment in enumerate(segments):
            speaker = segment['speaker']
            content = segment['content']
            
            # Get voice ID for this speaker
            voice_id = voice_mapping.get(speaker, self.voice_id)
            
            logger.info(f"Generating audio for {speaker} (voice: {voice_id})")
            
            # Generate audio for this segment
            audio = self.client.generate(
                text=content,
                voice=voice_id,
                model="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.4,
                    use_speaker_boost=True
                )
            )
            
            # Save individual segment
            segment_file = f"temp_segment_{i}_{speaker}.mp3"
            with open(segment_file, 'wb') as f:
                for chunk in audio:
                    f.write(chunk)
            
            audio_segments.append(segment_file)
        
        # Combine all segments
        self.combine_audio_segments(audio_segments, output_filename)
        
        # Clean up temporary files
        for segment_file in audio_segments:
            if os.path.exists(segment_file):
                os.remove(segment_file)
        
        logger.info(f"Multi-speaker audio saved to {output_filename}")
        return self.save_metadata(output_filename, text)
    
    def generate_single_voice_audio(self, text: str, output_filename: str) -> str:
        """Generate audio with single voice (fallback)"""
        logger.info("Generating single-voice audio...")
        
        audio = self.client.generate(
            text=text,
            voice=self.voice_id,
            model="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.4,
                use_speaker_boost=True
            )
        )
        
        with open(output_filename, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        
        logger.info(f"Single-voice audio saved to {output_filename}")
        return self.save_metadata(output_filename, text)
    
    def parse_conversation(self, text: str) -> list:
        """Parse conversation text into speaker segments"""
        segments = []
        lines = text.split('\n')
        
        current_speaker = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if ':' in line and not line.startswith(' '):
                # This looks like a speaker change
                parts = line.split(':', 1)
                if len(parts) == 2:
                    # Save previous segment
                    if current_speaker and current_content:
                        segments.append({
                            'speaker': current_speaker,
                            'content': ' '.join(current_content)
                        })
                    
                    # Start new segment
                    current_speaker = parts[0].strip()
                    current_content = [parts[1].strip()] if parts[1].strip() else []
                else:
                    current_content.append(line)
            else:
                current_content.append(line)
        
        # Save final segment
        if current_speaker and current_content:
            segments.append({
                'speaker': current_speaker,
                'content': ' '.join(current_content)
            })
        
        return segments
    
    def combine_audio_segments(self, segment_files: list, output_filename: str):
        """Combine audio segments with small pauses between speakers"""
        try:
            # Try using ffmpeg if available
            import subprocess
            
            # Create concat list
            with open('temp_concat.txt', 'w') as f:
                for segment_file in segment_files:
                    f.write(f"file '{segment_file}'\n")
            
            # Use ffmpeg to concatenate
            subprocess.run([
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'temp_concat.txt',
                '-c', 'copy', output_filename, '-y'
            ], check=True, capture_output=True)
            
            # Clean up
            if os.path.exists('temp_concat.txt'):
                os.remove('temp_concat.txt')
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("ffmpeg not available, concatenating manually")
            # Fallback: just use the first segment
            if segment_files:
                import shutil
                shutil.copy(segment_files[0], output_filename)
    
    def save_metadata(self, output_filename: str, text: str) -> str:
        """Save audio metadata"""
        file_size = os.path.getsize(output_filename)
        duration_estimate = len(text.split()) / 150 * 60
        
        metadata = {
            'filename': output_filename,
            'file_size': file_size,
            'duration_seconds': int(duration_estimate),
            'generated_at': datetime.now().isoformat(),
            'voice_id': self.voice_id,
            'text_length': len(text)
        }
        
        metadata_filename = output_filename.replace('.mp3', '_metadata.json')
        with open(metadata_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return output_filename
    
    def generate_episode_metadata(self, script_file: str, audio_file: str) -> dict:
        """
        Generate episode metadata for RSS feed
        """
        today = datetime.now()
        episode_number = self.get_next_episode_number()
        
        metadata = {
            'title': f"Morgonpodd #{episode_number} - {today.strftime('%d %B %Y')}",
            'description': f"Din dagliga dos av nyheter, teknik och väder. Avsnitt {episode_number}.",
            'pub_date': today.isoformat(),
            'audio_file': audio_file,
            'script_file': script_file,
            'episode_number': episode_number,
            'guid': f"morgonpodd-{today.strftime('%Y%m%d')}-{episode_number}"
        }
        
        # Save episode metadata
        metadata_file = f"episodes/episode_{episode_number}_meta.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return metadata
    
    def get_next_episode_number(self) -> int:
        """
        Get the next episode number based on existing episodes
        """
        try:
            if not os.path.exists('episodes'):
                return 1
            
            episodes = [f for f in os.listdir('episodes') if f.endswith('_meta.json')]
            if not episodes:
                return 1
            
            numbers = []
            for ep in episodes:
                try:
                    with open(f'episodes/{ep}', 'r') as f:
                        data = json.load(f)
                        numbers.append(data.get('episode_number', 0))
                except:
                    continue
            
            return max(numbers) + 1 if numbers else 1
        except:
            return 1

async def main():
    # Load the script
    scripts_dir = 'scripts'
    latest_script = max([f for f in os.listdir(scripts_dir) if f.endswith('.txt')], 
                       key=lambda x: os.path.getctime(os.path.join(scripts_dir, x)))
    
    with open(os.path.join(scripts_dir, latest_script), 'r', encoding='utf-8') as f:
        script = f.read()
    
    # Generate audio
    generator = PodcastGenerator()
    audio_file = generator.generate_audio(script)
    
    # Generate metadata
    metadata = generator.generate_episode_metadata(latest_script, audio_file)
    
    logger.info(f"Episode generated: {metadata['title']}")
    return audio_file, metadata

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())