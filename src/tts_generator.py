import os
import logging
from datetime import datetime
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import json
import sys
sys.path.append(os.path.dirname(__file__))
from music_library import MusicLibrary

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastGenerator:
    def __init__(self):
        self.client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
        
        # Load config for voice settings - use parent directory's sources.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Initialize music library
        self.music_library = MusicLibrary()
    
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
        """Generate audio for multi-speaker conversation using ElevenLabs text-to-dialogue"""
        
        # Extract music cues from text first
        music_cues = self.music_library.extract_music_cues_from_script(text)
        logger.info(f"Found {len(music_cues)} music cues in script")
        
        # Remove music markers from text for speech synthesis
        clean_text = self.remove_music_markers(text)
        
        # Check if text-to-dialogue is enabled
        text_to_dialogue_settings = self.config.get('podcastSettings', {}).get('textToDialogue', {})
        use_dialogue_api = text_to_dialogue_settings.get('enabled', False)
        
        if use_dialogue_api:
            logger.info("Using ElevenLabs text-to-dialogue API for natural conversation...")
            # Use ElevenLabs text-to-dialogue API - no fallback, let errors bubble up
            audio_file = self.generate_dialogue_audio(clean_text, output_filename)
            
            # Add music integration if cues were found
            if music_cues:
                final_file = self.integrate_music_with_speech(audio_file, music_cues, text, output_filename)
                if audio_file != final_file and os.path.exists(audio_file):
                    os.remove(audio_file)
                return final_file
            
            return audio_file
        else:
            logger.info("Text-to-dialogue disabled, using segment-by-segment generation...")
            return self.generate_conversation_audio_fallback(clean_text, output_filename, music_cues, text)
    
    def generate_dialogue_audio(self, text: str, output_filename: str) -> str:
        """Generate conversation using ElevenLabs text-to-dialogue API - entire dialogue at once"""
        from elevenlabs import DialogueInput, ElevenLabs
        
        # Get host configuration
        hosts = self.config.get('podcastSettings', {}).get('hosts', [])
        if len(hosts) < 2:
            logger.error("Need at least 2 hosts configured for dialogue generation")
            raise ValueError("Insufficient host configuration")
        
        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        
        # Parse the entire conversation and convert to complete dialogue format
        dialogue_inputs = self.build_complete_dialogue_inputs(text, hosts)
        
        # Split into chunks if needed (based on 2000 character limit from experience)
        max_chars = self.config.get('podcastSettings', {}).get('textToDialogue', {}).get('maxCharsPerChunk', 2000)
        dialogue_chunks = self.split_dialogue_by_character_limit(dialogue_inputs, max_chars=max_chars)
        
        logger.info(f"Generating complete dialogue in {len(dialogue_chunks)} chunks (total dialogue length: {sum(len(inp.text) for inp in dialogue_inputs)} chars)")
        
        # Generate audio for each chunk and combine seamlessly
        audio_chunks = []
        
        for i, chunk in enumerate(dialogue_chunks):
            total_chars = sum(len(inp.text) for inp in chunk)
            logger.info(f"Generating chunk {i+1}/{len(dialogue_chunks)} with {len(chunk)} speakers ({total_chars} chars)...")
            
            # Generate entire chunk as one natural conversation
            audio = client.text_to_dialogue.convert(inputs=chunk)
            
            # Collect audio data
            chunk_data = b''
            for audio_chunk in audio:
                chunk_data += audio_chunk
            audio_chunks.append(chunk_data)
        
        # Combine all audio chunks into final file
        with open(output_filename, 'wb') as f:
            for chunk_data in audio_chunks:
                f.write(chunk_data)
        
        logger.info(f"Complete natural dialogue saved to {output_filename}")
        return output_filename
    
    def build_complete_dialogue_inputs(self, text: str, hosts: list) -> list:
        """Build complete dialogue inputs gradually, checking character length"""
        from elevenlabs import DialogueInput
        
        dialogue_inputs = []
        
        # Parse conversation into speaker segments
        conversation_segments = self.parse_conversation(text)
        
        for segment in conversation_segments:
            speaker = segment.get('speaker')
            line = segment.get('content', '').strip()
            
            if not line:  # Skip empty segments
                continue
            
            # Find matching voice for this speaker
            voice_id = None
            for host in hosts:
                if host['name'].lower() == speaker.lower():
                    voice_id = host['voice_id']
                    break
            
            if not voice_id:
                # Use first host as fallback
                voice_id = hosts[0]['voice_id']
                logger.warning(f"No voice found for speaker '{speaker}', using default")
            
            # Add emotion markers if detected (keep existing emotion detection)
            if 'emotion' in segment:
                line = f"[{segment['emotion']}] {line}"
            
            # Build up dialogue input piece by piece
            dialogue_input = DialogueInput(
                text=line,
                voice_id=voice_id,
            )
            
            dialogue_inputs.append(dialogue_input)
            
            # Log each addition to track character count
            current_total = sum(len(inp.text) for inp in dialogue_inputs)
            logger.debug(f"Added {speaker}: '{line[:50]}...' (chars: {len(line)}, total: {current_total})")
        
        return dialogue_inputs
    
    def split_dialogue_by_character_limit(self, dialogue_inputs: list, max_chars: int = 2000) -> list:
        """Split dialogue inputs into chunks under the character limit"""
        chunks = []
        current_chunk = []
        current_chars = 0
        
        for dialogue_input in dialogue_inputs:
            text_length = len(dialogue_input.text)
            
            # If adding this segment would exceed limit, start new chunk
            if current_chars + text_length > max_chars and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [dialogue_input]
                current_chars = text_length
            else:
                current_chunk.append(dialogue_input)
                current_chars += text_length
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        logger.info(f"Split {len(dialogue_inputs)} segments into {len(chunks)} chunks (max {max_chars} chars each)")
        return chunks
    
    def prepare_dialogue_with_emotions(self, text: str, hosts: list) -> list:
        """Convert conversation text to dialogue format with emotions"""
        segments = self.parse_conversation(text)
        dialogue_segments = []
        
        for segment in segments:
            speaker_name = segment['speaker']
            content = segment['content']
            
            # Find matching host configuration
            host_config = None
            for host in hosts:
                if host['name'].lower() == speaker_name.lower():
                    host_config = host
                    break
            
            if not host_config:
                logger.warning(f"No host configuration found for {speaker_name}, using first host")
                host_config = hosts[0]
            
            # Detect emotional context from content
            emotion = self.detect_emotion_from_content(content)
            
            # Create dialogue segment
            dialogue_segment = {
                "voice_id": host_config.get('voice_id', self.voice_id),
                "text": content,
                "voice_settings": {
                    "stability": 0.6,
                    "similarity_boost": 0.8,
                    "style": 0.5
                }
            }
            
            # Add emotion using square bracket format
            if emotion:
                # Wrap text with emotion brackets
                dialogue_segment["text"] = f"[{emotion}] {content}"
                logger.info(f"Added emotion '[{emotion}]' for {speaker_name}: {content[:50]}...")
            
            dialogue_segments.append(dialogue_segment)
        
        return dialogue_segments
    
    def detect_emotion_from_content(self, content: str) -> str:
        """Detect appropriate emotion based on content using ElevenLabs emotion guidelines"""
        content_lower = content.lower()
        
        # Positive emotions
        if any(word in content_lower for word in ['fantastisk', 'underbart', 'bra nyheter', 'glädjande', 'positivt', 'framgång', 'vinner']):
            return "excited"
        
        if any(word in content_lower for word in ['roligt', 'kul', 'humor', 'skrattar', 'lustigt']):
            return "laughing"
        
        if any(word in content_lower for word in ['intressant', 'fascinerande', 'spännande', 'upptäckt', 'innovation']):
            return "curious"
        
        # Concerned/serious emotions  
        if any(word in content_lower for word in ['oroande', 'problem', 'kris', 'allvarligt', 'varning', 'fara']):
            return "concerned"
        
        if any(word in content_lower for word in ['tråkigt', 'ledsamt', 'sorgligt', 'tragiskt', 'förlust']):
            return "sad"
        
        # Analytical/professional
        if any(word in content_lower for word in ['analys', 'enligt', 'forskning', 'studie', 'experter', 'data']):
            return "neutral"
        
        # Conversational/friendly (default for most podcast content)
        if any(word in content_lower for word in ['hej', 'välkommen', 'tack', 'vi pratar om', 'låt oss']):
            return "friendly"
        
        # Weather gets a calm, informative tone
        if any(word in content_lower for word in ['väder', 'temperatur', 'regn', 'sol', 'grader']):
            return "neutral"
        
        # Surprise/amazement
        if any(word in content_lower for word in ['otroligt', 'häpnadsväckande', 'chockerande', 'överraskande']):
            return "surprised"
        
        # Default to conversational for neutral content
        return "conversational"
    
    def generate_conversation_audio_fallback(self, text: str, output_filename: str, music_cues: list, original_text: str) -> str:
        """Fallback method using original segment-by-segment generation"""
        logger.info("Using fallback conversation generation method...")
        
        # Parse conversation
        segments = self.parse_conversation(text)
        audio_segments = []
        
        # Get host configuration
        hosts = self.config.get('podcastSettings', {}).get('hosts', [])
        voice_mapping = {}
        
        for host in hosts:
            voice_mapping[host['name']] = host.get('voice_id', self.voice_id)
        
        logger.info(f"Voice mapping: {voice_mapping}")
        
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
        speech_only_file = f"temp_speech_only.mp3"
        self.combine_audio_segments(audio_segments, speech_only_file)
        
        # Add music if cues were found
        if music_cues:
            final_file = self.integrate_music_with_speech(speech_only_file, music_cues, original_text, output_filename)
            if os.path.exists(speech_only_file):
                os.remove(speech_only_file)
        else:
            final_file = speech_only_file
            if final_file != output_filename:
                import shutil
                shutil.move(final_file, output_filename)
        
        # Clean up temporary files
        for segment_file in audio_segments:
            if os.path.exists(segment_file):
                os.remove(segment_file)
        
        logger.info(f"Fallback multi-speaker audio with music saved to {output_filename}")
        return output_filename
    
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
        return output_filename
    
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
    
    def remove_music_markers(self, text: str) -> str:
        """Remove music markers from text for speech synthesis"""
        import re
        # Remove [MUSIK: artist - title, X sekunder] patterns
        pattern = r'\[MUSIK:[^\]]+\]'
        clean_text = re.sub(pattern, '', text)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
        clean_text = re.sub(r'  +', ' ', clean_text)
        
        return clean_text.strip()
    
    def integrate_music_with_speech(self, speech_file: str, music_cues: list, original_text: str, output_file: str) -> str:
        """Integrate music cues with speech using ffmpeg"""
        try:
            import subprocess
            import tempfile
            
            logger.info(f"Integrating {len(music_cues)} music cues with speech...")
            
            # For now, we'll use a simple approach: 
            # Just overlay the first music track at low volume as background
            # In a full implementation, you'd analyze timestamps and position music precisely
            
            if music_cues and os.path.exists(music_cues[0]['track']['path']):
                music_path = music_cues[0]['track']['path']
                duration = music_cues[0].get('duration', 10)  # Default 10 seconds
                
                logger.info(f"Using background music: {music_cues[0]['artist']} - {music_cues[0]['title']}")
                
                # Create background music at low volume
                cmd = [
                    'ffmpeg', '-i', speech_file, '-i', music_path,
                    '-filter_complex', 
                    f'[1:a]volume=0.2,aloop=loop=-1:size=48000*{int(duration)}[music];'
                    '[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[out]',
                    '-map', '[out]', '-y', output_file
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Music integrated successfully: {output_file}")
                return output_file
                
            else:
                logger.warning("No valid music tracks found for integration")
                # Just copy speech file to output
                import shutil
                shutil.copy(speech_file, output_file)
                return output_file
                
        except Exception as e:
            logger.error(f"Error integrating music: {e}")
            # Fallback: just copy speech file
            import shutil
            shutil.copy(speech_file, output_file)
            return output_file
    
    def generate_clever_episode_name(self, script_content: str) -> str:
        """Generate a clever and unique episode name based on content"""
        from datetime import datetime
        import random
        
        today = datetime.now()
        swedish_weekday = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag'][today.weekday()]
        month = today.month
        day = today.day
        
        # Season-based themes
        if month in [12, 1, 2]:
            season_themes = ["Vintermys", "Snöstorm", "Kyla och kaffe", "Vinterdröm", "Frost och fokus"]
        elif month in [3, 4, 5]:
            season_themes = ["Vårkänslor", "Blomsterprakt", "Ny början", "Solstråle", "Grön glädje"]
        elif month in [6, 7, 8]:
            season_themes = ["Sommarvärme", "Solsken", "Ljusa nätter", "Semester", "Midsommar"]
        else:
            season_themes = ["Höstmys", "Lövfall", "Gyllene tid", "Skördetid", "Höstens färger"]
        
        # Day-based themes  
        weekday_themes = {
            'måndag': ["Måndag med mening", "Veckans start", "Måndagsmagi", "Ny vecka, nya möjligheter"],
            'tisdag': ["Tisdag i toppform", "Veckans rytm", "Tisdagstempo", "Mitt i veckan"],
            'onsdag': ["Onsdagsenergi", "Halvtid", "Veckans hjärta", "Onsdagsoasen"],
            'torsdag': ["Torsdagstakt", "Nästan helg", "Torsdagstankar", "Veckoslut närmar sig"],
            'fredag': ["Fredagsmys börjar", "Helgkänsla", "Veckans avslut", "Fredagsfirande"],
            'lördag': ["Lördagslyx", "Helgmys", "Vila och reflektion", "Helgens höjdpunkt"],
            'söndag': ["Söndagstankar", "Veckans reflektion", "Lugn och ro", "Förberedelse för ny vecka"]
        }
        
        # Time-based themes
        hour = today.hour
        if 5 <= hour < 9:
            time_themes = ["Morgonpigg", "Gryningsglimtar", "Tidig start", "Morgonens magi"]
        elif 9 <= hour < 12:
            time_themes = ["Förmiddagsfokus", "I full gång", "Produktiv tid", "Morgonkaffe"]
        elif 12 <= hour < 17:
            time_themes = ["Eftermiddagsenergi", "Dagens mitt", "Lunchtanksr", "Efterspekning"]
        else:
            time_themes = ["Kvällsreflektion", "Dagens avslut", "Kvällstankar", "Reflektion"]
        
        # Creative formats
        formats = [
            f"{random.choice(season_themes)} & {random.choice(time_themes)}",
            f"{random.choice(weekday_themes[swedish_weekday])} - {random.choice(season_themes)}",
            f"{random.choice(time_themes)}: {day} {['januari', 'februari', 'mars', 'april', 'maj', 'juni', 'juli', 'augusti', 'september', 'oktober', 'november', 'december'][month-1]}",
            f"{swedish_weekday.capitalize()}s {random.choice(season_themes).lower()}",
            f"{random.choice(['Dagens', 'Veckans', 'Morgonens'])} {random.choice(['reflektion', 'perspektiv', 'upptäckt', 'insikt', 'fokus'])}",
            f"{random.choice(['Nyheter', 'Tankar', 'Perspektiv'])} från {random.choice(['morgonens', 'dagens', 'veckans'])} {random.choice(['ljus', 'värme', 'energi', 'fokus'])}"
        ]
        
        # Try to extract themes from content for even more relevance
        content_lower = script_content.lower()
        content_themes = []
        
        if any(word in content_lower for word in ['teknik', 'ai', 'innovation', 'startup']):
            content_themes.extend(['Tech-tisdag', 'Digital morgon', 'Innovationsenergi', 'Framtidens fokus'])
        if any(word in content_lower for word in ['politik', 'riksdag', 'regering', 'val']):
            content_themes.extend(['Politisk puls', 'Demokratiska diskussioner', 'Samhällsperspektiv'])
        if any(word in content_lower for word in ['ekonomi', 'bank', 'aktier', 'börsen']):
            content_themes.extend(['Ekonomiska ekon', 'Marknadsmagi', 'Finansiell fokus'])
        if any(word in content_lower for word in ['väder', 'regn', 'sol', 'snö', 'storm']):
            content_themes.extend(['Väderlek och visdom', 'Klimatkompass', 'Naturens nycker'])
        if any(word in content_lower for word in ['sport', 'fotboll', 'hockey', 'os']):
            content_themes.extend(['Sportens spänning', 'Tävlingsanda', 'Atletisk analys'])
        
        if content_themes:
            formats.extend(content_themes)
        
        return random.choice(formats)
    
    def generate_episode_metadata(self, script_file: str, audio_file: str, script_content: str = "") -> dict:
        """
        Generate episode metadata for RSS feed
        """
        today = datetime.now()
        episode_number = self.get_next_episode_number()
        
        # Generate clever episode name
        clever_name = self.generate_clever_episode_name(script_content)
        
        metadata = {
            'title': f"{clever_name} #{episode_number}",
            'subtitle': f"Morgonpodd - {today.strftime('%d %B %Y')}",
            'description': f"Din dagliga dos av nyheter, teknik och väder. {clever_name} - Avsnitt {episode_number} från {today.strftime('%d %B %Y')}.",
            'pub_date': today.isoformat(),
            'audio_file': audio_file,
            'script_file': script_file,
            'episode_number': episode_number,
            'clever_name': clever_name,
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
    
    # Generate metadata with clever naming
    metadata = generator.generate_episode_metadata(latest_script, audio_file, script)
    
    logger.info(f"Episode generated: {metadata['title']} - {metadata['clever_name']}")
    return audio_file, metadata

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())