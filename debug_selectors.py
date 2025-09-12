#!/usr/bin/env python3
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

async def analyze_site(url, site_name):
    print(f"\n🔍 Analyzing {site_name}: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try different selectors
        selectors_to_try = [
            'h1', 'h2', 'h3', 
            '.article-title', '.headline', '.title',
            'article h1', 'article h2', 'article h3',
            '[class*="title"]', '[class*="headline"]',
            'a[class*="title"]', 'a[class*="headline"]'
        ]
        
        print(f"📄 Page loaded: {len(html)} characters")
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if len(elements) >= 3:  # We want at least 3 headlines
                print(f"✅ '{selector}': {len(elements)} elements found")
                
                # Show first few examples
                for i, elem in enumerate(elements[:3]):
                    text = elem.get_text(strip=True)
                    if len(text) > 10:
                        print(f"   {i+1}. {text[:80]}...")
                
                print(f"   → Suggested selector: '{selector}'")
                break
            elif len(elements) > 0:
                print(f"⚠️  '{selector}': {len(elements)} elements (too few)")
        
    except Exception as e:
        print(f"❌ Error analyzing {site_name}: {e}")

async def main():
    sources = [
        ("https://www.svt.se/nyheter/", "SVT Nyheter"),
        ("https://www.dn.se/", "Dagens Nyheter"),  
        ("https://techcrunch.com/", "TechCrunch"),
    ]
    
    for url, name in sources:
        await analyze_site(url, name)
    
    print(f"\n🎯 Recommendations:")
    print(f"Update sources.json with the suggested selectors above")

if __name__ == "__main__":
    asyncio.run(main())