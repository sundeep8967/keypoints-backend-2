#!/usr/bin/env python3
"""
News Aggregator - Main Controller
Executes both RSS News Fetcher and NewsAPI Fetcher
Combines and analyzes data from multiple sources
"""
import json
import datetime
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our custom news fetchers
try:
    from rss_news_fetcher import RSSNewsFetcher
    from newsapi_fetcher import NewsAPIFetcher
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure both rss_news_fetcher.py and newsapi_fetcher.py are in the same directory")
    exit(1)

class NewsAggregator:
    def __init__(self, newsapi_key="945895608b4e41aeab5835c4538cf927"):
        self.newsapi_key = newsapi_key
        self.rss_fetcher = RSSNewsFetcher()
        self.newsapi_fetcher = NewsAPIFetcher(newsapi_key)
        
    def run_rss_fetcher(self):
        """Run RSS news fetcher"""
        print("🔄 Starting RSS News Fetcher...")
        try:
            rss_data = self.rss_fetcher.fetch_all_news()
            self.rss_fetcher.save_to_json(rss_data, 'rss_news_data.json')
            return rss_data
        except Exception as e:
            print(f"❌ RSS Fetcher Error: {e}")
            return None
    
    def run_newsapi_fetcher(self):
        """Run NewsAPI fetcher"""
        print("🔄 Starting NewsAPI Fetcher...")
        try:
            newsapi_data = self.newsapi_fetcher.fetch_all_news()
            self.newsapi_fetcher.save_to_json(newsapi_data, 'newsapi_data.json')
            return newsapi_data
        except Exception as e:
            print(f"❌ NewsAPI Fetcher Error: {e}")
            return None
    
    def run_both_sequential(self):
        """Run both fetchers one after another"""
        print("🚀 Starting Sequential News Aggregation...")
        print("="*70)
        
        start_time = time.time()
        
        # Run RSS fetcher first
        print("\n📡 PHASE 1: RSS NEWS EXTRACTION")
        print("-" * 50)
        rss_data = self.run_rss_fetcher()
        
        print("\n📡 PHASE 2: NEWSAPI EXTRACTION")
        print("-" * 50)
        newsapi_data = self.run_newsapi_fetcher()
        
        end_time = time.time()
        
        # Combine and analyze results
        combined_data = self.combine_results(rss_data, newsapi_data, end_time - start_time)
        
        return combined_data
    
    def run_both_parallel(self):
        """Run both fetchers in parallel for faster execution"""
        print("🚀 Starting Parallel News Aggregation...")
        print("="*70)
        
        start_time = time.time()
        
        # Run both fetchers in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            print("\n📡 RUNNING BOTH FETCHERS IN PARALLEL...")
            print("-" * 50)
            
            # Submit both tasks
            rss_future = executor.submit(self.run_rss_fetcher)
            newsapi_future = executor.submit(self.run_newsapi_fetcher)
            
            # Collect results as they complete
            rss_data = None
            newsapi_data = None
            
            for future in as_completed([rss_future, newsapi_future]):
                if future == rss_future:
                    rss_data = future.result()
                    print("✅ RSS Fetcher completed")
                elif future == newsapi_future:
                    newsapi_data = future.result()
                    print("✅ NewsAPI Fetcher completed")
        
        end_time = time.time()
        
        # Combine and analyze results
        combined_data = self.combine_results(rss_data, newsapi_data, end_time - start_time)
        
        return combined_data
    
    def combine_results(self, rss_data, newsapi_data, execution_time):
        """Combine results from both fetchers and create comprehensive analysis"""
        print("\n📊 COMBINING & ANALYZING RESULTS...")
        print("-" * 50)
        
        combined_data = {
            'aggregation_timestamp': datetime.datetime.now().isoformat(),
            'execution_time_seconds': round(execution_time, 2),
            'data_sources': {
                'rss_feeds': bool(rss_data),
                'newsapi': bool(newsapi_data)
            },
            'total_articles': 0,
            'total_articles_with_images': 0,
            'overall_image_success_rate': '0%',
            'sources_summary': {},
            'category_summary': {},
            'rss_data': rss_data,
            'newsapi_data': newsapi_data
        }
        
        # Analyze RSS data
        if rss_data:
            print("✅ RSS Data: Available")
            combined_data['total_articles'] += rss_data.get('total_articles', 0)
            combined_data['total_articles_with_images'] += rss_data.get('articles_with_images', 0)
            
            # Add RSS categories to summary
            for category, articles in rss_data.get('by_category', {}).items():
                if category not in combined_data['category_summary']:
                    combined_data['category_summary'][category] = {'rss': 0, 'newsapi': 0, 'total': 0}
                combined_data['category_summary'][category]['rss'] = len(articles)
                combined_data['category_summary'][category]['total'] += len(articles)
        else:
            print("❌ RSS Data: Failed")
        
        # Analyze NewsAPI data
        if newsapi_data:
            print("✅ NewsAPI Data: Available")
            combined_data['total_articles'] += newsapi_data.get('total_articles', 0)
            combined_data['total_articles_with_images'] += newsapi_data.get('articles_with_images', 0)
            
            # Add NewsAPI categories to summary
            for category, articles in newsapi_data.get('by_category', {}).items():
                if category not in combined_data['category_summary']:
                    combined_data['category_summary'][category] = {'rss': 0, 'newsapi': 0, 'total': 0}
                combined_data['category_summary'][category]['newsapi'] = len(articles)
                combined_data['category_summary'][category]['total'] += len(articles)
        else:
            print("❌ NewsAPI Data: Failed")
        
        # Calculate overall image success rate
        if combined_data['total_articles'] > 0:
            image_rate = (combined_data['total_articles_with_images'] / combined_data['total_articles']) * 100
            combined_data['overall_image_success_rate'] = f"{image_rate:.1f}%"
        
        # Create sources summary
        all_sources = set()
        if rss_data:
            all_sources.update(rss_data.get('by_source', {}).keys())
        if newsapi_data:
            all_sources.update(newsapi_data.get('by_source', {}).keys())
        
        combined_data['sources_summary'] = {
            'total_unique_sources': len(all_sources),
            'rss_sources': len(rss_data.get('by_source', {})) if rss_data else 0,
            'newsapi_sources': len(newsapi_data.get('by_source', {})) if newsapi_data else 0
        }
        
        return combined_data
    
    def save_combined_data(self, combined_data, filename='combined_news_data.json'):
        """Save combined data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Combined data saved to {filename}")
    
    def print_summary(self, combined_data):
        """Print comprehensive summary of aggregated news data"""
        print("\n" + "="*70)
        print("📊 COMPREHENSIVE NEWS AGGREGATION SUMMARY")
        print("="*70)
        
        print(f"⏱️  Total execution time: {combined_data['execution_time_seconds']} seconds")
        print(f"📰 Total articles collected: {combined_data['total_articles']}")
        print(f"🖼️  Articles with images: {combined_data['total_articles_with_images']} ({combined_data['overall_image_success_rate']})")
        print(f"📡 Unique sources: {combined_data['sources_summary']['total_unique_sources']}")
        
        print(f"\n📊 Data Sources:")
        print(f"  📡 RSS Feeds: {'✅ Active' if combined_data['data_sources']['rss_feeds'] else '❌ Failed'}")
        print(f"  🔑 NewsAPI: {'✅ Active' if combined_data['data_sources']['newsapi'] else '❌ Failed'}")
        
        print(f"\n📂 Category Breakdown:")
        for category, counts in combined_data['category_summary'].items():
            category_name = category.replace('_', ' ').title()
            print(f"  📁 {category_name}: {counts['total']} articles")
            print(f"     RSS: {counts['rss']} | NewsAPI: {counts['newsapi']}")
        
        print(f"\n📈 Source Distribution:")
        print(f"  📡 RSS Sources: {combined_data['sources_summary']['rss_sources']}")
        print(f"  🔑 NewsAPI Sources: {combined_data['sources_summary']['newsapi_sources']}")
        
        # File size information
        files_info = []
        for filename in ['rss_news_data.json', 'newsapi_data.json', 'combined_news_data.json']:
            if os.path.exists(filename):
                size_kb = os.path.getsize(filename) / 1024
                files_info.append(f"{filename}: {size_kb:.1f} KB")
        
        if files_info:
            print(f"\n📁 Generated Files:")
            for file_info in files_info:
                print(f"  💾 {file_info}")

def main():
    """Main function to execute both news fetchers"""
    print("🌟 Welcome to the Comprehensive News Aggregator!")
    print("This tool fetches news from RSS feeds AND NewsAPI")
    print("="*70)
    
    # Initialize aggregator
    aggregator = NewsAggregator()
    
    # Ask user for execution method
    print("\nChoose execution method:")
    print("1. Sequential (RSS first, then NewsAPI) - Slower but more stable")
    print("2. Parallel (Both simultaneously) - Faster but uses more resources")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    # Execute based on choice
    if choice == '1':
        combined_data = aggregator.run_both_sequential()
    else:
        combined_data = aggregator.run_both_parallel()
    
    # Save combined results
    aggregator.save_combined_data(combined_data)
    
    # Print comprehensive summary
    aggregator.print_summary(combined_data)
    
    print(f"\n🎉 News aggregation complete!")
    print(f"📊 Check 'combined_news_data.json' for the complete dataset")
    
    return combined_data

if __name__ == "__main__":
    main()