import os
import logging
from datetime import datetime
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import json
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntroGenerator:
    def __init__(self):
        self.client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        
        # Load config from parent directory
        config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def generate_intro_audio(self, date_str: str = None) -> str:
        """Generate intro audio with jingle and voice-over"""
        
        intro_settings = self.config.get('podcastSettings', {}).get('intro', {})
        
        if not intro_settings.get('enabled', False):
            logger.info("Intro generation disabled")
            return None
        
        # Get date string
        if not date_str:
            today = datetime.now()
            swedish_date = today.strftime("%A den %d %B %Y")
            swedish_weekdays = {
                'Monday': 'måndag', 'Tuesday': 'tisdag', 'Wednesday': 'onsdag',
                'Thursday': 'torsdag', 'Friday': 'fredag', 'Saturday': 'lördag', 'Sunday': 'söndag'
            }
            swedish_months = {
                'January': 'januari', 'February': 'februari', 'March': 'mars',
                'April': 'april', 'May': 'maj', 'June': 'juni',
                'July': 'juli', 'August': 'augusti', 'September': 'september',
                'October': 'oktober', 'November': 'november', 'December': 'december'
            }
            
            # Replace English with Swedish
            for eng, swe in swedish_weekdays.items():
                swedish_date = swedish_date.replace(eng, swe)
            for eng, swe in swedish_months.items():
                swedish_date = swedish_date.replace(eng, swe)
            
            date_str = swedish_date
        
        # Get intro text template
        intro_template = intro_settings.get('prompt', 
            "Välkommen till {podcast_title}! Idag är det {date}. Här kommer din dagliga sammanfattning av nyheter, teknik och väder.")
        
        intro_text = intro_template.format(
            podcast_title=self.config['podcastSettings'].get('title', 'Morgonpodd'),
            date=date_str,
            author=self.config['podcastSettings'].get('author', 'AI')
        )
        
        logger.info(f"Generating intro: {intro_text}")
        
        # Generate audio
        voice_id = intro_settings.get('voice_id', os.getenv('ELEVENLABS_VOICE_ID'))
        
        try:
            # Use regular text-to-speech for intro (single voice)
            # text-to-dialogue is better for conversations with multiple speakers
            import requests
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": os.getenv('ELEVENLABS_API_KEY')
            }
            
            payload = {
                "text": intro_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": intro_settings.get('stability', 0.6),
                    "similarity_boost": intro_settings.get('similarity_boost', 0.8),
                    "style": intro_settings.get('style', 0.3)
                },
                "output_format": "mp3_44100_128"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Save intro audio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            intro_file = f"audio/intro_{timestamp}.mp3"
            os.makedirs('audio', exist_ok=True)
            
            with open(intro_file, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Intro audio saved: {intro_file}")
            return intro_file
            
        except Exception as e:
            logger.error(f"Error generating intro audio: {e}")
            return None
    
    def combine_with_jingle(self, intro_voice_file: str, output_file: str = None) -> str:
        """Combine jingle with intro voice with smooth fade transitions"""
        
        intro_settings = self.config.get('podcastSettings', {}).get('intro', {})
        jingle_file = intro_settings.get('jingle_file')
        
        if not jingle_file or not os.path.exists(jingle_file):
            logger.warning("No jingle file found, using voice-only intro")
            return intro_voice_file
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"audio/intro_complete_{timestamp}.mp3"
        
        try:
            import subprocess
            
            # Mix jingle and voice using ffmpeg with fade effects
            mix_type = intro_settings.get('mix_type', 'fade_overlay')  # 'fade_overlay', 'overlay', 'sequence'
            fade_duration = intro_settings.get('fade_duration', 2.0)  # 2 seconds fade
            
            if mix_type == 'fade_overlay':
                # Simple approach: get voice length, fade music at that exact point
                import subprocess
                
                # Get exact voice file duration
                try:
                    duration_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                                   '-of', 'default=noprint_wrappers=1:nokey=1', intro_voice_file]
                    duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
                    
                    if duration_result.returncode == 0 and duration_result.stdout.strip():
                        voice_duration = float(duration_result.stdout.strip())
                        logger.info(f"Voice duration: {voice_duration:.2f}s")
                    else:
                        raise Exception("Could not get voice duration")
                    
                except Exception as e:
                    logger.error(f"Error getting voice duration: {e}")
                    return intro_voice_file
                
                # Add a small buffer after voice ends before fading
                buffer_after_voice = 1.0  # 1 second buffer after voice ends
                fade_start = voice_duration + buffer_after_voice
                total_duration = fade_start + fade_duration  # Voice + buffer + fade time
                
                logger.info(f"Creating intro: voice plays for {voice_duration:.2f}s, music continues for {buffer_after_voice}s, then fades at {fade_start:.2f}s over {fade_duration:.2f}s")
                
                # Mix voice over music, fade music after buffer, cut to final length
                cmd = [
                    'ffmpeg', '-i', jingle_file, '-i', intro_voice_file,
                    '-filter_complex', 
                    f'[0:a]afade=t=out:st={fade_start}:d={fade_duration}[music_faded];'
                    f'[music_faded][1:a]amix=inputs=2:duration=first[out]',
                    '-map', '[out]',
                    '-t', str(total_duration),  # Cut output to exact duration
                    '-y', output_file
                ]
            elif mix_type == 'overlay':
                # Voice over jingle (original behavior)
                cmd = [
                    'ffmpeg', '-i', jingle_file, '-i', intro_voice_file,
                    '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[out]',
                    '-map', '[out]', '-y', output_file
                ]
            else:  # sequence
                # Jingle then voice with crossfade
                cmd = [
                    'ffmpeg', '-i', jingle_file, '-i', intro_voice_file,
                    '-filter_complex', 
                    f'[0:a]afade=t=out:st=3:d={fade_duration}[jingle_out];'
                    f'[1:a]afade=t=in:st=0:d={fade_duration}[voice_in];'
                    f'[jingle_out][voice_in]concat=n=2:v=0:a=1[out]',
                    '-map', '[out]', '-y', output_file
                ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Combined intro with fade transitions created: {output_file}")
            
            # Clean up voice-only file if different from output
            if intro_voice_file != output_file and os.path.exists(intro_voice_file):
                os.remove(intro_voice_file)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error combining intro with jingle: {e}")
            return intro_voice_file

def main():
    generator = IntroGenerator()
    voice_file = generator.generate_intro_audio()
    
    if voice_file:
        final_intro = generator.combine_with_jingle(voice_file)
        logger.info(f"Final intro ready: {final_intro}")
        return final_intro
    
    return None

if __name__ == "__main__":
    main()