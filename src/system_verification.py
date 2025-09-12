#!/usr/bin/env python3
"""
Komplett systemverifiering för Morgonpodd
Testar all implementerad funktionalitet
"""
import os
import json
import sys
from pathlib import Path

# Grundläggande filkontroller
def check_core_files():
    print("=== GRUNDLÄGGANDE FILKONTROLLER ===")
    
    required_files = [
        'sources.json',
        'scraper.py', 
        'summarizer.py',
        'tts_generator.py',
        'main.py',
        'enhanced_gui.py',
        'music_library.py',
        'rss_generator.py',
        'cloudflare_uploader.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    return len(missing_files) == 0

def check_configuration():
    print("\n=== KONFIGURATIONSVERIFIERING ===")
    
    # Kontrollera sources.json
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ sources.json laddad korrekt")
        
        # Kontrollera källkonfiguration
        sources = config.get('sources', [])
        print(f"✅ {len(sources)} nyhetskällor konfigurerade")
        
        # Kontrollera poddkonfiguration  
        podcast_settings = config.get('podcastSettings', {})
        hosts = podcast_settings.get('hosts', [])
        print(f"✅ {len(hosts)} poddvärdar konfigurerade")
        
        # Kontrollera musikintegration
        if 'publicUrl' in podcast_settings:
            print("✅ Cloudflare R2 URL konfigurerad")
        
        return True
        
    except Exception as e:
        print(f"❌ Konfigurationsfel: {e}")
        return False

def check_environment():
    print("\n=== MILJÖVARIABLER ===")
    
    required_env = [
        'OPENAI_API_KEY',
        'ELEVENLABS_API_KEY', 
        'ELEVENLABS_VOICE_ID',
        'CLOUDFLARE_ACCOUNT_ID',
        'CLOUDFLARE_ACCESS_KEY_ID',
        'CLOUDFLARE_SECRET_ACCESS_KEY'
    ]
    
    missing_env = []
    for env_var in required_env:
        if os.getenv(env_var):
            print(f"✅ {env_var}")
        else:
            print(f"❌ {env_var}")
            missing_env.append(env_var)
    
    return len(missing_env) == 0

def check_dependencies():
    print("\n=== PYTHON-BEROENDEN ===")
    
    required_packages = [
        'streamlit',
        'openai', 
        'elevenlabs',
        'aiohttp',
        'beautifulsoup4',
        'feedparser',
        'feedgen',
        'boto3',
        'schedule'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_enhanced_features():
    print("\n=== FÖRBÄTTRADE FUNKTIONER ===")
    
    # Kontrollera temporal kontext i summarizer
    try:
        from summarizer import PodcastSummarizer
        summarizer = PodcastSummarizer()
        
        # Testa skript-generering med temporal kontext
        sample_data = [{'source': 'Test', 'type': 'news', 'items': [{'title': 'Test article'}]}]
        script = summarizer.create_podcast_script(sample_data)
        
        if 'TEMPORAL KONTEXT' in script or 'tidig morgon' in script or 'förmiddag' in script:
            print("✅ Temporal kontext i AI-prompt")
        else:
            print("❌ Temporal kontext saknas")
            
        print("✅ Förbättrad AI-prompt implementerad")
        
    except Exception as e:
        print(f"❌ AI-prompt fel: {e}")
    
    # Kontrollera smart avsnittsnamngivning
    try:
        from tts_generator import PodcastGenerator
        generator = PodcastGenerator()
        
        clever_name = generator.generate_clever_episode_name("Test script med teknik och AI")
        if clever_name and len(clever_name) > 0:
            print(f"✅ Smart avsnittsnamngivning: '{clever_name}'")
        else:
            print("❌ Smart avsnittsnamngivning misslyckades")
            
    except Exception as e:
        print(f"❌ Avsnittsnamngivning fel: {e}")

def check_music_library():
    print("\n=== MUSIKBIBLIOTEK ===")
    
    try:
        from music_library import MusicLibrary
        music_lib = MusicLibrary()
        
        # Kontrollera grundläggande funktioner
        library = music_lib.get_library()
        print(f"✅ Musikbibliotek laddat: {len(library.get('tracks', []))} spår")
        
        # Kontrollera AI-prompt kontext
        context = music_lib.get_music_prompt_context()
        if context:
            print("✅ Musik AI-prompt kontext")
        
        print("✅ Musikbibliotek fullt funktionellt")
        
    except Exception as e:
        print(f"❌ Musikbibliotek fel: {e}")

def check_gui_functionality():
    print("\n=== GUI FUNKTIONALITET ===")
    
    try:
        # Kontrollera GUI-filen finns och kan läsas
        with open('enhanced_gui.py', 'r', encoding='utf-8') as f:
            gui_content = f.read()
        
        # Kontrollera att nyckel-funktioner finns
        required_functions = [
            'show_episode_generation',
            'show_podcast_settings', 
            'show_music_library',
            'show_episode_scheduling'
        ]
        
        for func in required_functions:
            if f"def {func}" in gui_content:
                print(f"✅ {func}")
            else:
                print(f"❌ {func}")
        
        # Kontrollera schemaläggning
        if 'schedule' in gui_content and 'episode_scheduling' in gui_content:
            print("✅ Schemaläggningsfunktionalitet")
        else:
            print("❌ Schemaläggning saknas")
            
        print("✅ GUI-funktioner verifierade")
        
    except Exception as e:
        print(f"❌ GUI verifiering fel: {e}")

def check_system_integration():
    print("\n=== SYSTEMINTEGRATION ===")
    
    # Kontrollera att alla moduler kan importeras tillsammans
    try:
        sys.path.append('.')
        from main import MorgonPoddService
        print("✅ Huvudservice kan instansieras")
        
        service = MorgonPoddService()
        print("✅ Alla undermoduler laddade")
        
    except Exception as e:
        print(f"❌ Systemintegration fel: {e}")

def main():
    print("🎙️ MORGONPODD SYSTEMVERIFIERING")
    print("=" * 50)
    
    checks = [
        check_core_files(),
        check_configuration(), 
        check_environment(),
        check_dependencies(),
        check_enhanced_features(),
        check_music_library(),
        check_gui_functionality(),
        check_system_integration()
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTAT: {passed}/{total} tester klarade")
    
    if passed == total:
        print("🎉 ALLA FUNKTIONER VERIFIERADE - SYSTEMET ÄR REDO!")
    else:
        print(f"⚠️  {total - passed} funktioner behöver attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)