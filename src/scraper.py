import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import json
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScraper:
    def __init__(self, sources_file: str = "sources.json"):
        with open(sources_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.sources = self.config['sources']
    
    async def fetch_url(self, session: aiohttp.ClientSession, url: str) -> str:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    async def scrape_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Scraping {source['name']}...")
        html = await self.fetch_url(session, source['url'])
        
        if not html:
            return {
                'source': source['name'],
                'type': source['type'],
                'items': [],
                'error': 'Failed to fetch'
            }
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        if source['type'] == 'weather':
            # Special handling for weather
            weather_info = self.extract_weather(soup)
            items = [weather_info] if weather_info else []
        else:
            # Extract news/tech items
            elements = soup.select(source.get('selector', 'h2'))[:source.get('maxItems', 5)]
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    items.append({
                        'title': text,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return {
            'source': source['name'],
            'type': source['type'],
            'priority': source.get('priority', 3),
            'items': items
        }
    
    def extract_weather(self, soup: BeautifulSoup) -> Dict[str, str]:
        try:
            # SMHI specific extraction - adjust based on actual structure
            temp = soup.select_one('.temperature')
            desc = soup.select_one('.weather-description')
            
            if temp and desc:
                return {
                    'temperature': temp.get_text(strip=True),
                    'description': desc.get_text(strip=True),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Weather extraction error: {e}")
        
        return {
            'description': 'Väderinformation ej tillgänglig',
            'timestamp': datetime.now().isoformat()
        }
    
    async def scrape_all(self) -> List[Dict[str, Any]]:
        results = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.scrape_source(session, source) for source in self.sources]
            results = await asyncio.gather(*tasks)
        
        # Sort by priority
        results.sort(key=lambda x: x.get('priority', 99))
        return results

async def main():
    scraper = NewsScraper()
    results = await scraper.scrape_all()
    
    with open('scraped_content.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info("Scraping completed")
    return results

if __name__ == "__main__":
    asyncio.run(main())