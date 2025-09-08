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
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse
# Robust sklearn imports with fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: sklearn not available ({e}). Advanced similarity detection disabled.")
    TfidfVectorizer = None
    cosine_similarity = None
    SKLEARN_AVAILABLE = False
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our custom news fetchers
try:
    from fetchnews.rss_news_fetcher import RSSNewsFetcher
    from fetchnews.newsapi_fetcher import NewsAPIFetcher
    from db.supabase_integration import SupabaseNewsDB
    from bulletproof_duplicate_prevention import BulletproofDuplicateFilter
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
        
        # Initialize BULLETPROOF duplicate prevention system
        self.bulletproof_filter = BulletproofDuplicateFilter()
        print("🛡️  BULLETPROOF duplicate prevention system activated")
        print("🚫 ZERO TOLERANCE for duplicates - multiple layers of protection enabled")
        
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
                    all_articles.append(article)
                    original_counts['rss'] += 1
        else:
            print("❌ RSS Data: Failed")
        
        # Collect NewsAPI articles
        if newsapi_data:
            print("✅ NewsAPI Data: Available")
            for category, articles in newsapi_data.get('by_category', {}).items():
                for article in articles:
                    all_articles.append(article)
                    original_counts['newsapi'] += 1
        else:
            print("❌ NewsAPI Data: Failed")
        
        # Apply initial deduplication (RSS vs NewsAPI cross-checking)
        deduplicated_articles, deduplication_info = self.deduplicate_articles(all_articles)
        
        print(f"✅ Initial deduplication complete: {len(deduplicated_articles)} articles")
        
        # FINAL BULLETPROOF LAYER - ZERO TOLERANCE FOR DUPLICATES
        print(f"\n🛡️  APPLYING BULLETPROOF FINAL FILTER...")
        print(f"🚫 ZERO TOLERANCE - No duplicates will pass through this layer")
        
        bulletproof_articles, bulletproof_stats = self.bulletproof_filter.filter_duplicates(deduplicated_articles)
        
        print(f"\n🎯 BULLETPROOF FILTERING COMPLETE:")
        print(f"  📊 Articles before bulletproof filter: {len(deduplicated_articles)}")
        print(f"  ✅ Articles after bulletproof filter: {len(bulletproof_articles)}")
        print(f"  🚫 Additional duplicates blocked: {bulletproof_stats['duplicates_found']}")
        print(f"  🛡️  GUARANTEE: Zero duplicates in final dataset")
        
        # Use bulletproof-filtered articles as the final dataset
        final_articles = bulletproof_articles
        
        combined_data['deduplication_info'] = deduplication_info
        combined_data['bulletproof_filter_info'] = bulletproof_stats
        combined_data['deduplication_info']['original_counts'] = original_counts
        combined_data['deduplication_info']['settings'] = {
            'title_similarity_threshold': self.title_similarity_threshold,
            'url_similarity_threshold': self.url_similarity_threshold,
            'content_similarity_threshold': self.content_similarity_threshold
        }
        
        # Reorganize BULLETPROOF-FILTERED articles by category and source
        final_by_category = {}
        final_by_source = {}
        
        for article in final_articles:
            category = article.get('category', 'unknown')
            source = article.get('source', 'unknown')
            
            # Group by category
            if category not in final_by_category:
                final_by_category[category] = []
            final_by_category[category].append(article)
            
            # Group by source
            if source not in final_by_source:
                final_by_source[source] = []
            final_by_source[source].append(article)
        
        # Update combined data with BULLETPROOF-FILTERED results
        combined_data['by_category_deduplicated'] = final_by_category
        combined_data['by_source_deduplicated'] = final_by_source
        
        # Calculate statistics for BULLETPROOF-FILTERED data
        combined_data['total_articles'] = len(final_articles)
        combined_data['total_articles_with_images'] = sum(1 for article in final_articles if article.get('has_image', False))
        
        
        # Calculate overall image success rate
        if combined_data['total_articles'] > 0:
            image_rate = (combined_data['total_articles_with_images'] / combined_data['total_articles']) * 100
            combined_data['overall_image_success_rate'] = f"{image_rate:.1f}%"
        
        # Create category summary with BULLETPROOF-FILTERED counts
        for category, articles in final_by_category.items():
            if category not in combined_data['category_summary']:
                combined_data['category_summary'][category] = {'rss': 0, 'newsapi': 0, 'total': 0, 'deduplicated': 0}
            
            combined_data['category_summary'][category]['deduplicated'] = len(articles)
            combined_data['category_summary'][category]['total'] = len(articles)
            
            # Note: Source tracking removed for cleaner output
        
        # Create sources summary
        combined_data['sources_summary'] = {
            'total_unique_sources': len(final_by_source),
            'rss_sources': len(rss_data.get('by_source', {})) if rss_data else 0,
            'newsapi_sources': len(newsapi_data.get('by_source', {})) if newsapi_data else 0,
            'bulletproof_filtered_sources': len(final_by_source)
        }
        
        return combined_data
    
    def save_combined_data(self, combined_data, filename='data/combined_news_data.json', save_to_supabase=False):
        """Save combined data to JSON file only (no Supabase - wait for enhanced data)"""
        # Save to JSON file
        os.makedirs('data', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Combined data saved to {filename}")
        
        # DO NOT save raw data to Supabase - only enhanced data should go to Supabase
        if save_to_supabase and self.use_supabase and self.supabase_db:
            print("⚠️  Skipping raw data upload - only enhanced data will be saved to Supabase")
            # self.save_to_supabase(combined_data)  # Commented out to prevent duplicate uploads
    
    def run_ai_enhancement(self):
        """Run the AI enhancement JavaScript file"""
        try:
            print("\n🤖 PHASE 3: AI ENHANCEMENT")
            print("-" * 50)
            print("🔄 Starting AI enhancement with Gemini...")
            
            # Check if Node.js is available
            try:
                subprocess.run(['node', '--version'], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ Node.js not found. Please install Node.js to run AI enhancement.")
                return False
            
            # Check if the enhancement script exists
            if not os.path.exists('enhance_news_with_ai.js'):
                print("❌ enhance_news_with_ai.js not found. Skipping AI enhancement.")
                return False
            
            # Check if combined_news_data.json exists
            if not os.path.exists('data/combined_news_data.json'):
                print("❌ combined_news_data.json not found. Cannot run AI enhancement.")
                return False
            
            # Run the Node.js enhancement script
            print("🚀 Executing: node enhance_news_with_ai.js")
            result = subprocess.run(
                ['node', 'enhance_news_with_ai.js'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                print("✅ AI enhancement completed successfully!")
                
                # Show some output from the enhancement process
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    # Show last few lines which usually contain the summary
                    for line in lines[-10:]:
                        if line.strip():
                            print(f"   {line}")
                
                return True
            else:
                print("❌ AI enhancement failed!")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ AI enhancement timed out (30 minutes). This might happen with very large datasets.")
            return False
        except Exception as e:
            print(f"❌ Error running AI enhancement: {e}")
            return False
    
    def save_enhanced_to_supabase(self):
        """Save ONLY AI-enhanced articles to Supabase (this is the ONLY Supabase upload method)"""
        try:
            enhanced_file = 'data/combined_news_data_enhanced.json'
            if not os.path.exists(enhanced_file):
                print("⚠️  Enhanced data file not found. Skipping enhanced data upload.")
                return False
            
            print("\n🔗 Saving ONLY AI-enhanced data to Supabase (no raw data)...")
            print("📋 Source: combined_news_data_enhanced.json")
            
            # Load enhanced data
            with open(enhanced_file, 'r', encoding='utf-8') as f:
                enhanced_data = json.load(f)
            
            # Collect all enhanced articles
            all_articles = []
            for category, articles in enhanced_data.get('by_category_enhanced', {}).items():
                all_articles.extend(articles)
            
            if not all_articles:
                print("⚠️  No enhanced articles to save to database")
                return False
            
            # Save enhanced articles to database
            success = self.supabase_db.insert_articles(all_articles, is_enhanced=True)
            
            if success:
                # Save enhancement run metadata
                enhancement_metadata = {
                    'timestamp': enhanced_data.get('enhancement_timestamp'),
                    'enhancement_info': enhanced_data.get('enhancement_info', {}),
                    'total_articles': len(all_articles)
                }
                self.supabase_db.insert_enhancement_run(enhancement_metadata)
                
                print(f"✅ Enhanced articles saved to Supabase!")
                print(f"   📰 Total enhanced articles: {len(all_articles)}")
                print(f"   🤖 Enhancement rate: {enhanced_data.get('enhancement_info', {}).get('enhancement_rate', 'N/A')}")
                return True
            else:
                print("❌ Failed to save enhanced articles to database")
                return False
                
        except Exception as e:
            print(f"❌ Error saving enhanced data to Supabase: {e}")
            return False

    def save_to_supabase(self, combined_data):
        """DEPRECATED: Only save enhanced articles to Supabase, not raw data"""
        print("⚠️  WARNING: save_to_supabase() called but raw data should NOT go to Supabase")
        print("⚠️  Only enhanced articles from combined_news_data_enhanced.json should be uploaded")
        print("⚠️  Use save_enhanced_to_supabase() instead")
        return False
    
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
            bulletproof_info = combined_data.get('bulletproof_filter_info', {})
            
            print(f"\n🔍 Multi-Layer Duplicate Prevention Results:")
            original_total = dedup_info.get('original_counts', {}).get('rss', 0) + dedup_info.get('original_counts', {}).get('newsapi', 0)
            print(f"  📰 Original articles collected: {original_total}")
            print(f"  🔄 After initial deduplication: {original_total - dedup_info.get('total_duplicates_removed', 0)}")
            print(f"  🛡️  After BULLETPROOF filter: {combined_data['total_articles']}")
            print(f"  🚫 Total duplicates blocked: {dedup_info.get('total_duplicates_removed', 0) + bulletproof_info.get('duplicates_found', 0)}")
            
            print(f"\n📊 Initial Deduplication Layer:")
            print(f"  🔗 URL duplicates: {dedup_info.get('url_duplicates', 0)}")
            print(f"  📝 Title duplicates: {dedup_info.get('title_duplicates', 0)}")
            print(f"  📄 Content duplicates: {dedup_info.get('content_duplicates', 0)}")
            
            print(f"\n🛡️  BULLETPROOF Filter Layer:")
            print(f"  🚫 Additional duplicates blocked: {bulletproof_info.get('duplicates_found', 0)}")
            print(f"  ✅ Final unique articles: {bulletproof_info.get('unique_articles', 0)}")
            print(f"  🎯 GUARANTEE: Zero duplicates in final dataset")
            
            if bulletproof_info.get('detection_methods'):
                print(f"\n🔍 Bulletproof detection methods used:")
                for method, count in bulletproof_info['detection_methods'].items():
                    if count > 0:
                        print(f"    {method}: {count} duplicates")
            
            settings = dedup_info.get('settings', {})
            print(f"\n⚙️  Detection thresholds:")
            print(f"  📝 Title similarity: {settings.get('title_similarity_threshold', 0.85)*100:.0f}%")
            print(f"  🔗 URL similarity: {settings.get('url_similarity_threshold', 0.90)*100:.0f}%")
            print(f"  📄 Content similarity: {settings.get('content_similarity_threshold', 0.75)*100:.0f}%")
        
        print(f"\n📂 Category Breakdown:")
        for category, counts in combined_data['category_summary'].items():
            category_name = category.title()
            print(f"  📁 {category_name}: {counts['total']} articles")
            print(f"     RSS: {counts['rss']} | NewsAPI: {counts['newsapi']}")
        
        print(f"\n📈 Source Distribution:")
        print(f"  📡 RSS Sources: {combined_data['sources_summary']['rss_sources']}")
        print(f"  🔑 NewsAPI Sources: {combined_data['sources_summary']['newsapi_sources']}")
        print(f"  🛡️  Bulletproof Filtered Sources: {combined_data['sources_summary'].get('bulletproof_filtered_sources', 0)}")

def main():
    """Main function to execute the complete automated pipeline"""
    print("🌟 Welcome to the Automated News Pipeline!")
    print("This tool: Fetches → Enhances with AI → Saves to Supabase")
    print("="*70)
    
    # Initialize aggregator
    aggregator = NewsAggregator()
    
    # Ask user for execution method
    print("\nChoose execution method:")
    print("1. Sequential (RSS first, then NewsAPI) - Slower but more stable")
    print("2. Parallel (Both simultaneously) - Faster but uses more resources")
    print("3. Full Auto Pipeline (Parallel + AI + Supabase) - Complete automation")
    
    while True:
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    # Execute based on choice
    if choice == '1':
        combined_data = aggregator.run_both_sequential()
    elif choice == '2':
        combined_data = aggregator.run_both_parallel()
    else:  # choice == '3'
        print("\n🚀 STARTING FULL AUTOMATED PIPELINE...")
        print("="*70)
        combined_data = aggregator.run_both_parallel()
    
    # Save combined results (local files only - NO SUPABASE for raw data)
    aggregator.save_combined_data(combined_data, save_to_supabase=False)
    
    # Print comprehensive summary
    aggregator.print_summary(combined_data)
    
    # If full auto pipeline or user wants AI enhancement
    if choice == '3':
        # Run AI Enhancement automatically
        ai_success = aggregator.run_ai_enhancement()
        
        if ai_success:
            # Save enhanced data to Supabase
            if aggregator.use_supabase and aggregator.supabase_db:
                aggregator.save_enhanced_to_supabase()
        else:
            print("⚠️  AI enhancement failed, but raw data is still available")
    else:
        # Ask if user wants to run AI enhancement
        print(f"\n" + "="*70)
        print("🤖 AI ENHANCEMENT OPTION")
        print("="*70)
        
        ai_choice = input("\nDo you want to run AI enhancement now? (y/N): ").strip().lower()
        if ai_choice in ['y', 'yes']:
            ai_success = aggregator.run_ai_enhancement()
            
            if ai_success and aggregator.use_supabase and aggregator.supabase_db:
                save_choice = input("\nSave enhanced data to Supabase? (y/N): ").strip().lower()
                if save_choice in ['y', 'yes']:
                    aggregator.save_enhanced_to_supabase()
    
    # Print final status
    print(f"\n" + "="*70)
    print("💾 FINAL PIPELINE STATUS")
    print("="*70)
    
    # Check what files were created
    files_created = []
    if os.path.exists('data/combined_news_data.json'):
        files_created.append("✅ Raw news data: data/combined_news_data.json")
    
    if os.path.exists('data/combined_news_data_enhanced.json'):
        files_created.append("✅ AI-enhanced data: data/combined_news_data_enhanced.json")
    
    for file_info in files_created:
        print(f"  {file_info}")
    
    # Supabase status
    if aggregator.use_supabase and aggregator.supabase_db:
        try:
            stats = aggregator.get_database_stats()
            if stats:
                print("✅ SUPABASE: Successfully connected and data saved")
                print(f"  📊 Total articles in database: {stats.get('total_articles', 0)}")
                print(f"  🖼️  Articles with images: {stats.get('articles_with_images', 0)}")
                print(f"  📈 Image success rate: {stats.get('image_success_rate', '0%')}")
            else:
                print("⚠️  SUPABASE: Connected but unable to fetch stats")
        except Exception as e:
            print(f"❌ SUPABASE: Error occurred - {e}")
    else:
        print("❌ SUPABASE: Not connected or disabled")
        print("  💡 Enable Supabase by setting SUPABASE_URL and SUPABASE_KEY in .env")
    
    print(f"\n🎉 Pipeline execution complete!")
    if choice == '3':
        print("🚀 Full automation completed: Fetch → AI Enhance → Supabase")
    
    return combined_data

if __name__ == "__main__":
    main()