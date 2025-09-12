import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(__file__))
from music_library import MusicLibrary

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodcastSummarizer:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OpenAI API key not found. Using fallback mode.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'sources.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Initialize music library
        self.music_library = MusicLibrary()
    
    def create_podcast_script(self, scraped_data: List[Dict[str, Any]]) -> str:
        # Prepare content for summarization
        content_sections = []
        
        for source_data in scraped_data:
            if source_data['items']:
                section = f"\n{source_data['source']} ({source_data['type']}):\n"
                for item in source_data['items']:
                    if source_data['type'] == 'weather':
                        section += f"- {item.get('description', 'Ingen väderinformation')}\n"
                    else:
                        section += f"- {item.get('title', '')}\n"
                content_sections.append(section)
        
        all_content = "\n".join(content_sections)
        
        # Get current date and time in Swedish with contextual information
        today = datetime.now()
        swedish_date = today.strftime("%d %B %Y")
        swedish_weekday = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag'][today.weekday()]
        current_time = today.strftime("%H:%M")
        
        # Add time context for morning podcast
        hour = today.hour
        if 5 <= hour < 9:
            time_context = "tidig morgon"
        elif 9 <= hour < 12:
            time_context = "förmiddag"
        elif 12 <= hour < 17:
            time_context = "eftermiddag"
        elif 17 <= hour < 21:
            time_context = "kväll"
        else:
            time_context = "sen kväll/natt"
        
        # Add seasonal and calendar context
        month = today.month
        if month in [12, 1, 2]:
            season = "vintern"
        elif month in [3, 4, 5]:
            season = "våren" 
        elif month in [6, 7, 8]:
            season = "sommaren"
        else:
            season = "hösten"
        
        # Check if it's a weekend
        is_weekend = today.weekday() >= 5
        week_context = "helger" if is_weekend else "vardagar"
        
        # Get hosts configuration
        hosts = self.config['podcastSettings'].get('hosts', [
            {'name': 'Anna', 'personality': 'Energisk morgonvärd', 'style': 'varm och konversationell'},
            {'name': 'Erik', 'personality': 'Analytisk och noggrann', 'style': 'informativ men lättsam'}
        ])
        
        host1 = hosts[0] if len(hosts) > 0 else {'name': 'Anna', 'personality': 'Energisk morgonvärd'}
        host2 = hosts[1] if len(hosts) > 1 else {'name': 'Erik', 'personality': 'Analytisk och noggrann'}
        
        # Get custom prompt template if available
        prompt_template = self.config['podcastSettings'].get('promptTemplates', {}).get('main_prompt', 
            """Du skapar ett naturligt samtal mellan {host1_name} och {host2_name}, två professionella poddvärdar.

{host1_name}: {host1_personality}
{host2_name}: {host2_personality}

Skapa ett engagerande samtal där värdarna diskuterar dagens nyheter på ett naturligt sätt."""
        )
        
        # Format the prompt with host information
        formatted_prompt = prompt_template.format(
            host1_name=host1['name'],
            host2_name=host2['name'], 
            host1_personality=host1.get('personality', 'Energisk morgonvärd'),
            host2_personality=host2.get('personality', 'Analytisk värd'),
            host1_style=host1.get('style', 'varm och konversationell'),
            host2_style=host2.get('style', 'informativ men lättsam')
        )
        
        # Get music context
        music_context = self.music_library.get_music_prompt_context()
        
        # Get music instructions from config or use default
        default_music_instructions = """OBLIGATORISK MUSIKINTEGRATION - Du MÅSTE inkludera musik enligt följande:
   - KRÄVS: Öppna med intro-musik från kategori "intro": [MUSIK: artist - titel]
   - KRÄVS: Minst 2 övergångsmusik mellan ämnen från kategori "transition": [MUSIK: artist - titel]
   - KRÄVS: Passande bakgrundsmusik för olika ämnesområden (news, tech, weather)
   - KRÄVS: Avsluta med outro-musik från kategori "outro": [MUSIK: artist - titel]
   - VIKTIGT: Använd FULLSTÄNDIGA låtar (ingen tidsbegränsning)
   - VIKTIGT: Varje låt får bara användas EN gång per avsnitt (inga dubbletter)
   - Använd ENDAST artister och titlar som finns i den tillgängliga musiklistan ovan
   - VIKTIGT: Värdarna ska ALDRIG kommentera eller presentera musiken - den ska bara spela naturligt
   - Placera [MUSIK: artist - titel] mellan samtalsavsnitt eller när det passar naturligt"""
        
        music_instructions = self.config.get('podcastSettings', {}).get('music_instructions', default_music_instructions)
        
        # Get emotional design instructions from config or use default
        default_emotional_design = """EMOTIONAL DESIGN FÖR NATURLIGT SAMTAL:
Skapa ett samtal som utnyttjar ElevenLabs nya text-to-dialogue funktionalitet med följande emotionella variation:
- EXCITED: För positiva nyheter, framgångshistorier, spännande upptäckter
- LAUGHING: För roliga nyheter, humoristiska kommentarer, lättsammare inslag
- CURIOUS: För intressanta tekniska nyheter, forskningsresultat, innovations
- CONCERNED: För allvarliga nyheter, problem, varningar, kriser
- SAD: För tragiska nyheter, sorgsna händelser
- NEUTRAL: För analyser, faktabaserad information, objektiva rapporter
- FRIENDLY: För hälsningar, övergångar, personliga kommentarer
- SURPRISED: För överraskande nyheter, häpnadsväckande upptäckter
- CONVERSATIONAL: Som bas för neutralt innehåll och naturliga övergångar

OBS: Du kan markera emotionella partier med hakparenteser [excited], [laughing], etc. men använd sparsamt - endast för tydliga emotionella höjdpunkter.

Instruktioner för optimerad text-to-dialogue:
1. Skapa ett naturligt samtal mellan värdarna
2. Variera emotionell ton baserat på innehåll - använd ord som indikerar känsla:
   - "Det här är verkligen spännande..." (CURIOUS/EXCITED)
   - "Det är oroande att höra..." (CONCERNED)
   - "Enligt nya forskningsresultat..." (PROFESSIONAL)
   - "Hej och välkommen..." (FRIENDLY)
   - "Vädret idag visar..." (CALM)
3. Låt värdarna reagera emotionellt passande på varandras kommentarer"""
        
        emotional_design = self.config.get('podcastSettings', {}).get('emotional_design', default_emotional_design)
        
        prompt = f"""{formatted_prompt}
        
TEMPORAL KONTEXT:
- Datum: {swedish_weekday} den {swedish_date}
- Tid: {current_time} ({time_context})
- Säsong: {season}
- Veckoperiod: {week_context}
- Aktuell tidskontext: Genereras klockan {current_time} under {time_context} på en {swedish_weekday}

Dagens innehåll att diskutera:
{all_content}

{music_context}

{emotional_design}
4. Inkludera naturliga övergångar med emotionell förändring
5. {host1['name']} börjar med energi anpassad till {time_context}
6. {host2['name']} balanserar med analytisk men engagerad ton
7. Använd format: "{host1['name']}: [text]" och "{host2['name']}: [text]"
8. {music_instructions}
9. Anpassa språkstil och energi till {time_context} och {week_context}
10. Skapa tydliga emotionella höjdpunkter och lugnare partier
11. Referera naturligt till temporala element ({swedish_weekday}, {season})
12. Avsluta med både värdarna i en passande känsloton för {time_context}

Mål: Ett 8-12 minuters samtal som maximerar ElevenLabs emotionella röstteknologi för naturlig, engagerande podcast-upplevelse."""

        if not self.client:
            logger.warning("No OpenAI client available, using fallback script")
            return self.create_fallback_script(scraped_data)
        
        try:
            # Get system prompt from config or use default
            system_prompt = self.config.get('podcastSettings', {}).get('system_prompt', 
                "Du är en professionell AI som hjälper till att skapa naturliga samtal mellan poddvärdar på svenska.")
            
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            script = response.choices[0].message.content
            logger.info("Podcast script generated successfully")
            return script
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return self.create_fallback_script(scraped_data)
    
    def create_fallback_script(self, scraped_data: List[Dict[str, Any]]) -> str:
        today = datetime.now()
        swedish_weekday = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag'][today.weekday()]
        
        script = f"""God morgon och välkommen till dagens podd! Det är {swedish_weekday} och här kommer en snabb överblick av vad som händer idag.

Vi har samlat nyheter från flera källor men hade tekniska problem med sammanfattningen. 
Besök nyhetssajterna direkt för fullständig information.

Ha en fantastisk dag och vi hörs igen imorgon!"""
        
        return script
    
    def save_script(self, script: str, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scripts/podcast_script_{timestamp}.txt"
        
        os.makedirs('scripts', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(script)
        
        logger.info(f"Script saved to {filename}")
        return filename

async def main():
    # Load scraped content
    with open('scraped_content.json', 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)
    
    summarizer = PodcastSummarizer()
    script = summarizer.create_podcast_script(scraped_data)
    filename = summarizer.save_script(script)
    
    return script, filename

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())