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
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our custom news fetchers
try:
    from fetchnews.rss_news_fetcher import RSSNewsFetcher
    from fetchnews.newsapi_fetcher import NewsAPIFetcher
    from db.supabase_integration import SupabaseNewsDB
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure all required modules are in the correct directories")
    print("Run: pip install supabase python-dotenv")
    exit(1)

class NewsAggregator:
    def __init__(self, newsapi_key=None, use_supabase=True):
        # Initialize fetchers - let NewsAPIFetcher handle its own triple key system
        self.rss_fetcher = RSSNewsFetcher()
        self.newsapi_fetcher = NewsAPIFetcher()  # No key passed - uses its own triple key system
        
        # Initialize Supabase connection
        self.use_supabase = use_supabase
        self.supabase_db = None
        if use_supabase:
            try:
                self.supabase_db = SupabaseNewsDB()
                print("🔗 Supabase integration enabled")
            except Exception as e:
                print(f"⚠️  Supabase connection failed: {e}")
                print("📝 Continuing without database storage...")
                self.use_supabase = False
        
        # Verify NewsAPI keys are available (for user feedback)
        if not (os.getenv('NEWSAPI_KEY_PRIMARY') or os.getenv('NEWSAPI_KEY')):
            print("❌ Error: No NewsAPI keys found!")
            print("Please set NEWSAPI_KEY_PRIMARY, NEWSAPI_KEY_SECONDARY, NEWSAPI_KEY_TERTIARY in your .env file")
            print("Get your free API keys from: https://newsapi.org/register")
            exit(1)
        
        # Deduplication settings (can be overridden by environment variables)
        self.title_similarity_threshold = float(os.getenv('TITLE_SIMILARITY_THRESHOLD', '0.85'))
        self.url_similarity_threshold = float(os.getenv('URL_SIMILARITY_THRESHOLD', '0.90'))
        self.content_similarity_threshold = 0.75  # 75% similarity for content matching
        
    def run_rss_fetcher(self):
        """Run RSS news fetcher"""
        print("🔄 Starting RSS News Fetcher...")
        try:
            rss_data = self.rss_fetcher.fetch_all_news()
            self.rss_fetcher.save_to_json(rss_data)
            return rss_data
        except Exception as e:
            print(f"❌ RSS Fetcher Error: {e}")
            return None
    
    def run_newsapi_fetcher(self):
        """Run NewsAPI fetcher"""
        print("🔄 Starting NewsAPI Fetcher...")
        try:
            newsapi_data = self.newsapi_fetcher.fetch_all_news()
            self.newsapi_fetcher.save_to_json(newsapi_data)
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
    
    def calculate_title_similarity(self, title1, title2):
        """Calculate similarity between two titles using SequenceMatcher"""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles for better comparison
        title1_norm = title1.lower().strip()
        title2_norm = title2.lower().strip()
        
        # Use SequenceMatcher to calculate similarity
        similarity = SequenceMatcher(None, title1_norm, title2_norm).ratio()
        return similarity
    
    def normalize_url(self, url):
        """Normalize URL for comparison by removing query parameters and fragments"""
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            # Keep only scheme, netloc, and path for comparison
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return normalized.lower().rstrip('/')
        except:
            return url.lower()
    
    def are_urls_similar(self, url1, url2):
        """Check if two URLs are similar enough to be considered duplicates"""
        if not url1 or not url2:
            return False
        
        norm_url1 = self.normalize_url(url1)
        norm_url2 = self.normalize_url(url2)
        
        # Exact match after normalization
        if norm_url1 == norm_url2:
            return True
        
        # Check similarity using SequenceMatcher
        similarity = SequenceMatcher(None, norm_url1, norm_url2).ratio()
        return similarity >= self.url_similarity_threshold
    
    def preprocess_content(self, text):
        """Preprocess text for content similarity analysis"""
        if not text:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        text = text.lower().strip()
        
        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters and keep only alphanumeric and spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def get_article_content(self, article):
        """Extract and combine all textual content from an article"""
        content_parts = []
        
        # Add title (weighted more heavily)
        title = article.get('title', '').strip()
        if title:
            content_parts.append(title + " " + title)  # Add title twice for weight
        
        # Add summary/description
        summary = article.get('summary', '').strip()
        if summary:
            content_parts.append(summary)
        
        description = article.get('description', '').strip()
        if description and description != summary:
            content_parts.append(description)
        
        # Combine all content
        full_content = " ".join(content_parts)
        return self.preprocess_content(full_content)
    
    def calculate_content_similarity(self, article1, article2):
        """Calculate content similarity between two articles using TF-IDF and cosine similarity"""
        try:
            content1 = self.get_article_content(article1)
            content2 = self.get_article_content(article2)
            
            # Skip if either content is too short
            if len(content1) < 20 or len(content2) < 20:
                return 0.0
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2),  # Use both unigrams and bigrams
                min_df=1,
                max_df=0.95
            )
            
            # Fit and transform the content
            tfidf_matrix = vectorizer.fit_transform([content1, content2])
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            similarity = similarity_matrix[0, 1]
            
            return float(similarity)
            
        except Exception as e:
            print(f"Error calculating content similarity: {e}")
            return 0.0
    
    def deduplicate_articles(self, all_articles):
        """Remove duplicate articles based on title similarity, URL matching, and content similarity"""
        duplicates_info = {
            'total_duplicates_removed': 0,
            'title_duplicates': 0,
            'url_duplicates': 0,
            'content_duplicates': 0,
            'duplicate_pairs': []
        }
        
        if not all_articles:
            return [], duplicates_info
        
        print("🔍 Starting deduplication process...")
        
        deduplicated = []
        
        for current_article in all_articles:
            is_duplicate = False
            duplicate_reason = None
            duplicate_of = None
            similarity_score = 0.0
            
            for existing_article in deduplicated:
                # Check URL similarity first (most reliable)
                if self.are_urls_similar(current_article.get('link', ''), existing_article.get('link', '')):
                    is_duplicate = True
                    duplicate_reason = 'url_match'
                    duplicate_of = existing_article
                    similarity_score = 1.0
                    duplicates_info['url_duplicates'] += 1
                    break
                
                # Check title similarity
                title_similarity = self.calculate_title_similarity(
                    current_article.get('title', ''), 
                    existing_article.get('title', '')
                )
                
                if title_similarity >= self.title_similarity_threshold:
                    is_duplicate = True
                    duplicate_reason = 'title_similarity'
                    duplicate_of = existing_article
                    similarity_score = title_similarity
                    duplicates_info['title_duplicates'] += 1
                    break
                
                # Check content similarity (most sophisticated)
                content_similarity = self.calculate_content_similarity(current_article, existing_article)
                
                if content_similarity >= self.content_similarity_threshold:
                    is_duplicate = True
                    duplicate_reason = 'content_similarity'
                    duplicate_of = existing_article
                    similarity_score = content_similarity
                    duplicates_info['content_duplicates'] += 1
                    break
            
            if not is_duplicate:
                deduplicated.append(current_article)
            else:
                duplicates_info['total_duplicates_removed'] += 1
                duplicates_info['duplicate_pairs'].append({
                    'removed_article': {
                        'title': current_article.get('title', ''),
                        'source': current_article.get('source', ''),
                        'link': current_article.get('link', '')
                    },
                    'kept_article': {
                        'title': duplicate_of.get('title', ''),
                        'source': duplicate_of.get('source', ''),
                        'link': duplicate_of.get('link', '')
                    },
                    'reason': duplicate_reason,
                    'similarity_score': similarity_score
                })
        
        print(f"✅ Deduplication complete:")
        print(f"   📰 Original articles: {len(all_articles)}")
        print(f"   📰 After deduplication: {len(deduplicated)}")
        print(f"   🗑️  Duplicates removed: {duplicates_info['total_duplicates_removed']}")
        print(f"   🔗 URL duplicates: {duplicates_info['url_duplicates']}")
        print(f"   📝 Title duplicates: {duplicates_info['title_duplicates']}")
        print(f"   📄 Content duplicates: {duplicates_info['content_duplicates']}")
        
        return deduplicated, duplicates_info

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
            'deduplication_info': {},
            'rss_data': rss_data,
            'newsapi_data': newsapi_data
        }
        
        # Collect all articles from both sources for deduplication
        all_articles = []
        original_counts = {'rss': 0, 'newsapi': 0}
        
        # Collect RSS articles
        if rss_data:
            print("✅ RSS Data: Available")
            for category, articles in rss_data.get('by_category', {}).items():
                for article in articles:
                    article['data_source'] = 'rss'
                    all_articles.append(article)
                    original_counts['rss'] += 1
        else:
            print("❌ RSS Data: Failed")
        
        # Collect NewsAPI articles
        if newsapi_data:
            print("✅ NewsAPI Data: Available")
            for category, articles in newsapi_data.get('by_category', {}).items():
                for article in articles:
                    article['data_source'] = 'newsapi'
                    all_articles.append(article)
                    original_counts['newsapi'] += 1
        else:
            print("❌ NewsAPI Data: Failed")
        
        # Apply deduplication
        deduplicated_articles, deduplication_info = self.deduplicate_articles(all_articles)
        combined_data['deduplication_info'] = deduplication_info
        combined_data['deduplication_info']['original_counts'] = original_counts
        combined_data['deduplication_info']['settings'] = {
            'title_similarity_threshold': self.title_similarity_threshold,
            'url_similarity_threshold': self.url_similarity_threshold,
            'content_similarity_threshold': self.content_similarity_threshold
        }
        
        # Reorganize deduplicated articles by category and source
        deduplicated_by_category = {}
        deduplicated_by_source = {}
        
        for article in deduplicated_articles:
            category = article.get('category', 'unknown')
            source = article.get('source', 'unknown')
            
            # Group by category
            if category not in deduplicated_by_category:
                deduplicated_by_category[category] = []
            deduplicated_by_category[category].append(article)
            
            # Group by source
            if source not in deduplicated_by_source:
                deduplicated_by_source[source] = []
            deduplicated_by_source[source].append(article)
        
        # Update combined data with deduplicated results
        combined_data['by_category_deduplicated'] = deduplicated_by_category
        combined_data['by_source_deduplicated'] = deduplicated_by_source
        
        # Calculate statistics for deduplicated data
        combined_data['total_articles'] = len(deduplicated_articles)
        combined_data['total_articles_with_images'] = sum(1 for article in deduplicated_articles if article.get('has_image', False))
        
        # Calculate overall image success rate
        if combined_data['total_articles'] > 0:
            image_rate = (combined_data['total_articles_with_images'] / combined_data['total_articles']) * 100
            combined_data['overall_image_success_rate'] = f"{image_rate:.1f}%"
        
        # Create category summary with deduplicated counts
        for category, articles in deduplicated_by_category.items():
            if category not in combined_data['category_summary']:
                combined_data['category_summary'][category] = {'rss': 0, 'newsapi': 0, 'total': 0, 'deduplicated': 0}
            
            combined_data['category_summary'][category]['deduplicated'] = len(articles)
            combined_data['category_summary'][category]['total'] = len(articles)
            
            # Count by data source
            for article in articles:
                if article.get('data_source') == 'rss':
                    combined_data['category_summary'][category]['rss'] += 1
                elif article.get('data_source') == 'newsapi':
                    combined_data['category_summary'][category]['newsapi'] += 1
        
        # Create sources summary
        combined_data['sources_summary'] = {
            'total_unique_sources': len(deduplicated_by_source),
            'rss_sources': len(rss_data.get('by_source', {})) if rss_data else 0,
            'newsapi_sources': len(newsapi_data.get('by_source', {})) if newsapi_data else 0,
            'deduplicated_sources': len(deduplicated_by_source)
        }
        
        return combined_data
    
    def save_combined_data(self, combined_data, filename='data/combined_news_data.json'):
        """Save combined data to JSON file and Supabase"""
        # Save to JSON file
        os.makedirs('data', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Combined data saved to {filename}")
        
        # Save to Supabase if enabled
        if self.use_supabase and self.supabase_db:
            self.save_to_supabase(combined_data)
    
    def save_to_supabase(self, combined_data):
        """Save aggregated news data to Supabase database"""
        try:
            print("\n🔗 Saving data to Supabase...")
            
            # Collect all deduplicated articles
            all_articles = []
            for category, articles in combined_data.get('by_category_deduplicated', {}).items():
                all_articles.extend(articles)
            
            if not all_articles:
                print("⚠️  No articles to save to database")
                return
            
            # Save articles to database
            success = self.supabase_db.insert_articles(all_articles)
            
            if success:
                # Save aggregation run metadata
                self.supabase_db.insert_aggregation_run(combined_data)
                
                # Show database stats
                stats = self.supabase_db.get_aggregation_stats()
                if stats:
                    print(f"\n📊 Database Updated (Images Only):")
                    print(f"  📰 Total articles in DB: {stats.get('total_articles', 0)}")
                    print(f"  🖼️  Articles with images: {stats.get('articles_with_images', 0)}")
                    print(f"  🔑 Articles with key points: {stats.get('articles_with_keypoints', 0)}")
                    print(f"  📈 Image success rate: {stats.get('image_success_rate', '0%')}")
                    print(f"  💡 Note: Only articles with images are saved to database")
            else:
                print("❌ Failed to save articles to database")
                
        except Exception as e:
            print(f"❌ Error saving to Supabase: {e}")
    
    def get_database_stats(self):
        """Get statistics from Supabase database"""
        if not self.use_supabase or not self.supabase_db:
            print("⚠️  Supabase not available")
            return None
        
        try:
            return self.supabase_db.get_aggregation_stats()
        except Exception as e:
            print(f"❌ Error fetching database stats: {e}")
            return None
    
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
        
        # Deduplication summary
        if 'deduplication_info' in combined_data:
            dedup_info = combined_data['deduplication_info']
            print(f"\n🔍 Deduplication Results:")
            original_total = dedup_info.get('original_counts', {}).get('rss', 0) + dedup_info.get('original_counts', {}).get('newsapi', 0)
            print(f"  📰 Original articles: {original_total}")
            print(f"  📰 After deduplication: {combined_data['total_articles']}")
            print(f"  🗑️  Duplicates removed: {dedup_info.get('total_duplicates_removed', 0)}")
            print(f"  🔗 URL duplicates: {dedup_info.get('url_duplicates', 0)}")
            print(f"  📝 Title duplicates: {dedup_info.get('title_duplicates', 0)}")
            print(f"  📄 Content duplicates: {dedup_info.get('content_duplicates', 0)}")
            
            settings = dedup_info.get('settings', {})
            print(f"  ⚙️  Title similarity threshold: {settings.get('title_similarity_threshold', 0.85)*100:.0f}%")
            print(f"  ⚙️  URL similarity threshold: {settings.get('url_similarity_threshold', 0.90)*100:.0f}%")
            print(f"  ⚙️  Content similarity threshold: {settings.get('content_similarity_threshold', 0.75)*100:.0f}%")
        
        print(f"\n📂 Category Breakdown:")
        for category, counts in combined_data['category_summary'].items():
            category_name = category.replace('_', ' ').title()
            print(f"  📁 {category_name}: {counts['total']} articles")
            print(f"     RSS: {counts['rss']} | NewsAPI: {counts['newsapi']}")
        
        print(f"\n📈 Source Distribution:")
        print(f"  📡 RSS Sources: {combined_data['sources_summary']['rss_sources']}")
        print(f"  🔑 NewsAPI Sources: {combined_data['sources_summary']['newsapi_sources']}")
        print(f"  🎯 Deduplicated Sources: {combined_data['sources_summary'].get('deduplicated_sources', 0)}")
        
        # File size information
        files_info = []
        for filename in ['data/rss_news_data.json', 'data/newsapi_data.json', 'data/combined_news_data.json']:
            if os.path.exists(filename):
                size_kb = os.path.getsize(filename) / 1024
                display_name = os.path.basename(filename)
                files_info.append(f"{display_name}: {size_kb:.1f} KB")
        
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
    print(f"📊 Check 'data/combined_news_data.json' for the complete dataset")
    
    return combined_data

if __name__ == "__main__":
    main()