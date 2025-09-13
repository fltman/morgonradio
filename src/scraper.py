import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import json
import logging
from typing import List, Dict, Any
import feedparser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScraper:
    def __init__(self, sources_file: str = "sources.json"):
        with open(sources_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.sources = self.config['sources']
    
    async def fetch_url(self, session: aiohttp.ClientSession, url: str, source_type: str = None) -> str:
        try:
            # Use different user agents for different source types
            if source_type == 'weather' and 'wttr.in' in url:
                # Use curl-like user agent for wttr.in to get plain text
                headers = {
                    'User-Agent': 'curl/7.68.0'
                }
            else:
                # Use browser-like user agent for regular websites
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            
            logger.info(f"🌐 Fetching {url} with User-Agent: {headers['User-Agent'][:50]}...")
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                content = await response.text()
                logger.info(f"✅ Successfully fetched {len(content)} characters from {url}")
                logger.info(f"📝 Content preview: {content[:200]}...")
                return content
        except Exception as e:
            logger.error(f"❌ Error fetching {url}: {e}")
            return ""
    
    async def scrape_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"🔍 Scraping {source['name']} ({source['url']})...")
        
        # Check if this is an RSS feed
        if source.get('format') == 'rss' or source['url'].endswith('.rss') or '/rss' in source['url'] or '/feed' in source['url']:
            return await self.scrape_rss_source(session, source)
        else:
            return await self.scrape_html_source(session, source)
    
    async def fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch full article content from URL"""
        try:
            content = await self.fetch_url(session, url, 'html')
            if not content:
                return ""
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script, style, nav, and comment form elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                element.decompose()
            
            # Also remove common comment/reply sections
            for element in soup.find_all(class_=['comment-form', 'comments', 'respond', 'comment-respond', 'reply']):
                element.decompose()
            
            # Common article content selectors (in priority order)
            article_selectors = [
                'article .entry-content',  # WordPress common
                'article .post-content',   # Blog common
                '.article-body',           # News sites
                '.story-body',             # BBC-style
                '.content-body',           # Generic
                'article',                 # Full article tag
                '.entry-content',          # WordPress
                '.post-content',           # Blogs
                '.article-content',        # News
                '.content',                # Generic
                'main article',            # Semantic HTML
                '.wp-block-post-content',  # WordPress blocks
                '.entry',                  # Generic blog
                '.post',                   # Generic blog
                'main'                     # Main content
            ]
            
            best_text = ""
            best_length = 0
            
            for selector in article_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements[:2]:  # Check first 2 matches
                        # Get text from this element
                        text = element.get_text(separator=' ', strip=True)
                        
                        # Clean up the text
                        text = ' '.join(text.split())  # Normalize whitespace
                        
                        # Skip if too short or looks like navigation/comments
                        if len(text) < 100:
                            continue
                        if any(skip_word in text[:100].lower() for skip_word in [
                            'menu', 'search', 'subscribe', 'lämna ett svar', 
                            'din e-postadress', 'obligatoriska fält', 'comment', 'reply'
                        ]):
                            continue
                        
                        # Keep the longest quality text found
                        if len(text) > best_length:
                            best_text = text
                            best_length = len(text)
                except:
                    continue
            
            if best_text:
                return best_text[:5000]  # Increased limit to 5000 chars for better content
            
            # Fallback: get all paragraph text
            paragraphs = soup.find_all('p')
            if paragraphs:
                # Filter out short paragraphs and comment form text
                good_paragraphs = []
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 30:
                        # Skip if it looks like comment form
                        if any(skip in p_text.lower() for skip in [
                            'din e-postadress', 'obligatoriska fält', 
                            'lämna ett svar', 'avbryt svar'
                        ]):
                            continue
                        good_paragraphs.append(p_text)
                
                if good_paragraphs:
                    text = ' '.join(good_paragraphs)
                    return text[:5000] if text else ""  # Increased limit for better content
            
            return ""
        except Exception as e:
            logger.debug(f"Could not fetch article content from {url}: {e}")
            return ""
    
    async def scrape_rss_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"📡 RSS feed detected for {source['name']}")
        
        try:
            feed_data = await self.fetch_url(session, source['url'], source.get('type'))
            if not feed_data:
                logger.warning(f"❌ Failed to fetch RSS feed from {source['name']}")
                return self.create_empty_result(source, 'Failed to fetch RSS feed')
            
            logger.info(f"✅ Successfully fetched RSS feed ({len(feed_data)} characters)")
            
            # Parse RSS feed
            feed = feedparser.parse(feed_data)
            
            if feed.bozo:
                logger.warning(f"⚠️ RSS feed may have parsing issues: {feed.bozo_exception}")
            
            logger.info(f"📡 RSS feed parsed: {len(feed.entries)} entries found")
            
            items = []
            
            # Dynamic max items: if few sources, get more items per source
            total_sources = len([s for s in self.sources if s.get('enabled', True)])
            if total_sources <= 2:
                max_items = source.get('maxItems', 15)  # Get many items when very few sources
            elif total_sources <= 4:
                max_items = source.get('maxItems', 10)  # Get moderate items
            elif total_sources <= 6:
                max_items = source.get('maxItems', 7)   # Standard amount
            else:
                max_items = source.get('maxItems', 5)   # Limit when many sources
            
            logger.info(f"📊 Using max {max_items} items (total sources: {total_sources})")
            
            for entry in feed.entries[:max_items]:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '').strip()
                
                # Use title, or summary if no title
                text = title if title else summary
                
                if text and len(text) > 10:
                    item = {
                        'title': text,
                        'link': entry.get('link', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Add published date if available
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            pub_date = datetime(*entry.published_parsed[:6])
                            item['published'] = pub_date.isoformat()
                        except:
                            pass
                    
                    # Check if summary is too short or generic
                    # We should fetch full content for most RSS feeds as they often only provide teasers
                    needs_full_content = False
                    if not summary or len(summary) < 200:
                        needs_full_content = True
                    elif any(generic in summary.lower() for generic in [
                        'inlägget', 'dök först upp på', 'läs mer', 'read more', 
                        'continue reading', 'click here', '...', 'the post',
                        'appeared first on', 'fortsätt läsa', 'dök först upp'
                    ]):
                        needs_full_content = True
                    # Also fetch if summary is mostly links/HTML (or has any HTML tags)
                    elif summary.count('<') > 0 or summary.count('http') > 2:
                        needs_full_content = True
                    # Also if very short and generic sounding
                    elif len(summary) < 150 and ('dök' in summary or 'inlägg' in summary):
                        needs_full_content = True
                    
                    # Fetch full article content if needed
                    if needs_full_content and entry.get('link'):
                        logger.debug(f"  📄 Fetching full content for: {title[:50]}...")
                        article_content = await self.fetch_article_content(session, entry.get('link'))
                        if article_content:
                            item['summary'] = article_content[:2000] + '...' if len(article_content) > 2000 else article_content
                            logger.debug(f"  ✓ Got {len(article_content)} chars of article content")
                        elif summary:
                            item['summary'] = summary[:1000] + '...' if len(summary) > 1000 else summary
                    else:
                        # Use existing summary if it's good enough
                        if summary and summary != title and len(summary) > 10:
                            item['summary'] = summary[:2000] + '...' if len(summary) > 2000 else summary
                    
                    items.append(item)
                    logger.debug(f"  ✓ Added RSS item: {text[:80]}...")
            
            logger.info(f"✅ Successfully extracted {len(items)} RSS items from {source['name']}")
            
            return {
                'source': source['name'],
                'type': source['type'],
                'priority': source.get('priority', 3),
                'items': items,
                'scraped_count': len(items),
                'format': 'rss',
                'feed_title': feed.feed.get('title', source['name'])
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing RSS feed from {source['name']}: {e}")
            return self.create_empty_result(source, f'RSS parsing error: {str(e)}')
    
    async def scrape_html_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> Dict[str, Any]:
        html = await self.fetch_url(session, source['url'], source.get('type'))
        
        if not html:
            logger.warning(f"❌ Failed to fetch HTML content from {source['name']}")
            return self.create_empty_result(source, 'Failed to fetch HTML')
        
        logger.info(f"✅ Successfully fetched HTML ({len(html)} characters from {source['name']})")
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        if source['type'] == 'weather':
            # Special handling for weather
            logger.info(f"🌤️ Extracting weather information...")
            weather_info = self.extract_weather(soup)
            items = [weather_info] if weather_info else []
            if items:
                logger.info(f"✅ Found weather info: {items[0].get('description', 'N/A')}")
            else:
                logger.warning(f"❌ No weather information found")
        else:
            # Extract news/tech items from HTML
            selector = source.get('selector', 'h2')
            max_items = source.get('maxItems', 5)
            logger.info(f"🔎 Looking for HTML elements with selector: '{selector}' (max {max_items} items)")
            
            elements = soup.select(selector)
            logger.info(f"📰 Found {len(elements)} total HTML elements matching selector")
            
            processed = 0
            for elem in elements[:max_items]:
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    # Try to get link if element is or contains a link
                    link = ''
                    if elem.name == 'a':
                        link = elem.get('href', '')
                    else:
                        link_elem = elem.find('a')
                        if link_elem:
                            link = link_elem.get('href', '')
                    
                    items.append({
                        'title': text,
                        'link': link,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.debug(f"  ✓ Added HTML item: {text[:80]}...")
                    processed += 1
                else:
                    logger.debug(f"  ✗ Skipped (too short): {text[:40]}...")
            
            logger.info(f"✅ Successfully extracted {processed} HTML items from {source['name']}")
        
        return {
            'source': source['name'],
            'type': source['type'],
            'priority': source.get('priority', 3),
            'items': items,
            'scraped_count': len(items),
            'format': 'html'
        }
    
    def create_empty_result(self, source: Dict[str, Any], error: str) -> Dict[str, Any]:
        return {
            'source': source['name'],
            'type': source['type'],
            'items': [],
            'error': error
        }
    
    def extract_weather(self, soup: BeautifulSoup) -> Dict[str, str]:
        try:
            # Get the raw text content from the page
            text_content = soup.get_text(strip=True)
            logger.info(f"🌤️ Raw weather text ({len(text_content)} chars): {text_content[:300]}...")
            
            # For plain text responses (like wttr.in format=3), the content might be minimal
            if text_content and len(text_content) < 500:  # Likely plain text weather
                # Clean up the text
                weather_text = text_content.strip()
                
                # If it looks like wttr.in format (city: emoji temp)
                if ':' in weather_text and any(char in weather_text for char in ['°C', '°F', '🌤', '☀', '🌧', '🌫', '❄', '⛅', '🌩', '⛈', '🌦']):
                    logger.info(f"✅ Detected wttr.in plain text format")
                    
                    return {
                        'description': weather_text,
                        'temperature': self.extract_temperature_from_text(weather_text),
                        'location': self.extract_location_from_text(weather_text),
                        'timestamp': datetime.now().isoformat(),
                        'raw_content': text_content,
                        'format': 'wttr_plain'
                    }
                
                # Any other short text with temperature
                elif any(temp_indicator in weather_text for temp_indicator in ['°C', '°F']):
                    logger.info(f"✅ Detected plain text weather format")
                    return {
                        'description': weather_text,
                        'temperature': self.extract_temperature_from_text(weather_text),
                        'timestamp': datetime.now().isoformat(),
                        'raw_content': text_content,
                        'format': 'plain_text'
                    }
            
            # Check if this is wttr.in HTML format  
            if 'wttr.in' in str(soup) or any(char in text_content for char in ['°C', '°F', '🌤', '☀', '🌧', '🌫', '❄', '⛅']):
                # This is likely wttr.in or similar weather service with HTML
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                
                if lines:
                    # Look for weather information in the lines
                    for line in lines:
                        if any(char in line for char in ['°C', '°F', '🌤', '☀', '🌧', '🌫', '❄', '⛅']):
                            return {
                                'description': line,
                                'temperature': self.extract_temperature_from_text(line),
                                'location': self.extract_location_from_text(line),
                                'timestamp': datetime.now().isoformat(),
                                'raw_content': text_content[:500],
                                'format': 'wttr_html'
                            }
            
            # Fallback: Try SMHI or other HTML-based weather sites
            temp = soup.select_one('.temperature')
            desc = soup.select_one('.weather-description')
            
            if temp and desc:
                return {
                    'temperature': temp.get_text(strip=True),
                    'description': desc.get_text(strip=True),
                    'timestamp': datetime.now().isoformat(),
                    'format': 'html_structured'
                }
            
            # If no structured data found, use the text content
            if text_content:
                return {
                    'description': text_content[:200] + '...' if len(text_content) > 200 else text_content,
                    'timestamp': datetime.now().isoformat(),
                    'raw_content': text_content[:500],
                    'format': 'fallback'
                }
                
        except Exception as e:
            logger.error(f"❌ Weather extraction error: {e}")
        
        return {
            'description': 'Väderinformation ej tillgänglig',
            'timestamp': datetime.now().isoformat(),
            'error': 'extraction_failed'
        }
    
    def extract_temperature_from_text(self, text: str) -> str:
        """Extract temperature from text like 'kalmar: 🌫 +20°C'"""
        import re
        temp_match = re.search(r'[+-]?\d+°[CF]', text)
        return temp_match.group(0) if temp_match else ''
    
    def extract_location_from_text(self, text: str) -> str:
        """Extract location from text like 'kalmar: 🌫 +20°C'"""
        if ':' in text:
            location = text.split(':')[0].strip()
            return location.title() if location else ''
        return ''
    
    async def scrape_all(self) -> List[Dict[str, Any]]:
        logger.info(f"🚀 Starting scraping from {len(self.sources)} sources...")
        results = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.scrape_source(session, source) for source in self.sources]
            results = await asyncio.gather(*tasks)
        
        # Sort by priority
        results.sort(key=lambda x: x.get('priority', 99))
        
        # Log summary
        total_items = sum(len(result.get('items', [])) for result in results)
        successful_sources = len([r for r in results if r.get('items')])
        
        logger.info(f"📊 Scraping Summary:")
        logger.info(f"  • Total sources: {len(self.sources)}")
        logger.info(f"  • Successful sources: {successful_sources}")
        logger.info(f"  • Total items extracted: {total_items}")
        
        for result in results:
            item_count = len(result.get('items', []))
            status = "✅" if item_count > 0 else "❌"
            logger.info(f"  {status} {result['source']}: {item_count} items")
        
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