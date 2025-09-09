import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

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
        with open('sources.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
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
        
        # Get current date in Swedish
        today = datetime.now()
        swedish_date = today.strftime("%d %B %Y")
        swedish_weekday = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag'][today.weekday()]
        
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
        
        prompt = f"""{formatted_prompt}
        
Dagens datum: {swedish_weekday} den {swedish_date}

Dagens innehåll att diskutera:
{all_content}

Instruktioner:
1. Skapa ett naturligt samtal mellan {host1['name']} och {host2['name']}
2. Låt dem diskutera nyheterna som ett äkta samtal, inte bara läsa upp punkter  
3. Inkludera naturliga övergångar och reaktioner
4. {host1['name']} börjar ofta med hälsningar och översikter
5. {host2['name']} fokuserar mer på analys och detaljer
6. Använd format: "{host1['name']}: [text]" och "{host2['name']}: [text]"
7. Markera pauser med "..." och låt samtalet flyta naturligt
8. Avsluta med båda värdarna som säger adjö på sitt sätt

Skapa ett 8-12 minuters samtal på svenska."""

        if not self.client:
            logger.warning("No OpenAI client available, using fallback script")
            return self.create_fallback_script(scraped_data)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "Du är en professionell AI som hjälper till att skapa naturliga samtal mellan poddvärdar på svenska."},
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