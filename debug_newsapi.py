#!/usr/bin/env python3
"""
Debug NewsAPI File Creation Issues
"""
import os
from dotenv import load_dotenv

load_dotenv()

def debug_newsapi_setup():
    """Debug NewsAPI setup and file creation"""
    print("🔍 DEBUGGING NEWSAPI FILE CREATION")
    print("=" * 50)
    
    # Check 1: Environment Variables
    print("\n1. 🔑 API Key Check:")
    primary_key = os.getenv('NEWSAPI_KEY_PRIMARY')
    fallback_key = os.getenv('NEWSAPI_KEY')
    
    if primary_key:
        print(f"   ✅ NEWSAPI_KEY_PRIMARY: Found ({primary_key[:10]}...)")
    else:
        print("   ❌ NEWSAPI_KEY_PRIMARY: Not found")
    
    if fallback_key:
        print(f"   ✅ NEWSAPI_KEY: Found ({fallback_key[:10]}...)")
    else:
        print("   ❌ NEWSAPI_KEY: Not found")
    
    if not primary_key and not fallback_key:
        print("   🚨 ISSUE: No API keys found - this will cause exit(1)")
        return False
    
    # Check 2: Import Dependencies
    print("\n2. 📦 Import Check:")
    try:
        from fetchnews.newsapi_fetcher import NewsAPIFetcher
        print("   ✅ NewsAPIFetcher: Import successful")
    except ImportError as e:
        print(f"   ❌ NewsAPIFetcher: Import failed - {e}")
        return False
    
    try:
        from newsapi_history_manager import NewsAPIHistoryManager
        print("   ✅ NewsAPIHistoryManager: Import successful")
    except ImportError as e:
        print(f"   ❌ NewsAPIHistoryManager: Import failed - {e}")
        print("   ⚠️  This might cause the fetcher to fail")
    
    # Check 3: Directory Structure
    print("\n3. 📁 Directory Check:")
    data_dir = "data"
    if os.path.exists(data_dir):
        print(f"   ✅ {data_dir}/ directory exists")
    else:
        print(f"   ⚠️  {data_dir}/ directory missing - will be created")
    
    # Check 4: Test NewsAPI Fetcher Initialization
    print("\n4. 🚀 NewsAPI Fetcher Test:")
    try:
        fetcher = NewsAPIFetcher()
        print("   ✅ NewsAPIFetcher initialized successfully")
        
        # Test a simple API call
        print("   🔍 Testing API connectivity...")
        sources = fetcher.get_available_sources()
        if sources:
            print(f"   ✅ API working - found {len(sources.get('sources', []))} sources")
        else:
            print("   ❌ API call failed - no sources returned")
            return False
            
    except Exception as e:
        print(f"   ❌ NewsAPIFetcher initialization failed: {e}")
        return False
    
    # Check 5: Test File Creation
    print("\n5. 💾 File Creation Test:")
    try:
        # Create a minimal test file
        test_data = {
            "test": True,
            "timestamp": "2024-01-01T00:00:00",
            "total_articles": 0
        }
        
        fetcher.save_to_json(test_data, "data/newsapi_test.json")
        
        if os.path.exists("data/newsapi_test.json"):
            print("   ✅ File creation successful")
            os.remove("data/newsapi_test.json")  # Clean up
            return True
        else:
            print("   ❌ File creation failed")
            return False
            
    except Exception as e:
        print(f"   ❌ File creation error: {e}")
        return False

def debug_existing_files():
    """Check what files currently exist"""
    print("\n6. 📋 Existing Files Check:")
    
    files_to_check = [
        "data/rss_news_data.json",
        "data/newsapi_data.json", 
        "data/combined_news_data.json",
        "data/combined_news_data_enhanced.json"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024
            print(f"   ✅ {file_path}: Exists ({size:.1f} KB)")
        else:
            print(f"   ❌ {file_path}: Missing")

def main():
    """Run complete diagnosis"""
    success = debug_newsapi_setup()
    debug_existing_files()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ DIAGNOSIS: NewsAPI should work correctly")
        print("💡 If files still aren't created, the issue is likely:")
        print("   - Network connectivity problems")
        print("   - API rate limiting")
        print("   - Exception during fetch_all_news()")
    else:
        print("❌ DIAGNOSIS: NewsAPI has setup issues")
        print("💡 Fix the issues above before running the main script")
    
    print("\n🔧 NEXT STEPS:")
    print("1. Fix any issues shown above")
    print("2. Run: python debug_newsapi.py")
    print("3. If successful, run: python main.py")

if __name__ == "__main__":
    main()