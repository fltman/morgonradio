#!/usr/bin/env python3
"""
Test script for the enhanced features:
1. Temporal context in AI prompt
2. Clever episode naming system
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from summarizer import PodcastSummarizer
from tts_generator import PodcastGenerator
from datetime import datetime
import json

def test_temporal_context():
    """Test the enhanced AI prompt with temporal context"""
    print("=== Testing Enhanced AI Prompt with Temporal Context ===")
    
    # Create sample scraped data
    sample_data = [
        {
            'source': 'SVT Nyheter',
            'type': 'news', 
            'items': [
                {'title': 'Nya AI-innovationer förändrar arbetsmarknaden'},
                {'title': 'Väderprognos: Snö väntas i helgen'}
            ]
        },
        {
            'source': 'TechCrunch',
            'type': 'tech',
            'items': [
                {'title': 'OpenAI releases new breakthrough model'},
                {'title': 'Startup funding reaches new highs'}
            ]
        }
    ]
    
    summarizer = PodcastSummarizer()
    
    # Test without calling OpenAI (use fallback)
    summarizer.client = None
    script = summarizer.create_podcast_script(sample_data)
    
    print("Generated fallback script:")
    print(script)
    print("\n")
    
    # Show what the prompt would look like with temporal context
    print("=== Temporal Context Information ===")
    today = datetime.now()
    swedish_weekday = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag'][today.weekday()]
    current_time = today.strftime("%H:%M")
    
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
    
    month = today.month
    if month in [12, 1, 2]:
        season = "vintern"
    elif month in [3, 4, 5]:
        season = "våren" 
    elif month in [6, 7, 8]:
        season = "sommaren"
    else:
        season = "hösten"
    
    is_weekend = today.weekday() >= 5
    week_context = "helger" if is_weekend else "vardagar"
    
    print(f"Datum: {swedish_weekday} den {today.strftime('%d %B %Y')}")
    print(f"Tid: {current_time} ({time_context})")
    print(f"Säsong: {season}")
    print(f"Veckoperiod: {week_context}")
    print()

def test_clever_naming():
    """Test the clever episode naming system"""
    print("=== Testing Clever Episode Naming System ===")
    
    generator = PodcastGenerator()
    
    # Test with different types of content
    test_scripts = [
        "Anna: God morgon! Idag pratar vi om nya AI-innovationer och teknik.\nErik: Ja, det är spännande utveckling inom startup-världen.",
        "Anna: Välkommen till dagens podd! Vi har väder och politik att diskutera.\nErik: Regeringen har nya förslag om ekonomiska åtgärder.",
        "Anna: Hej och välkommen! Idag fokuserar vi på sport och fotboll.\nErik: Ja, det var en spännande match igår kväll.",
        "Anna: God morgon allesamman! Snö och regn väntas idag.\nErik: Ja, vädret blir intressant att följa."
    ]
    
    print("Generated clever episode names:")
    for i, script in enumerate(test_scripts, 1):
        clever_name = generator.generate_clever_episode_name(script)
        print(f"{i}. {clever_name}")
    
    print()

def test_metadata_generation():
    """Test the enhanced metadata generation"""
    print("=== Testing Enhanced Metadata Generation ===")
    
    generator = PodcastGenerator()
    
    sample_script = """Anna: God morgon och välkommen till dagens morgonpodd! 
    Idag är det en fantastisk måndag och vi har massor av spännande nyheter att dela med oss av.

    Erik: Absolut Anna! Det har hänt mycket inom tech-världen över helgen, 
    och vi har också intressant väderinformation att gå igenom."""
    
    # Test metadata generation
    metadata = generator.generate_episode_metadata(
        "test_script.txt", 
        "test_audio.mp3", 
        sample_script
    )
    
    print("Generated metadata:")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print()

if __name__ == "__main__":
    print(f"Testing enhancements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_temporal_context()
    test_clever_naming()
    test_metadata_generation()
    
    print("=" * 60)
    print("All tests completed successfully! ✅")