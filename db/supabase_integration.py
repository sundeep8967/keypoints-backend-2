#!/usr/bin/env python3
"""
Supabase Integration Module
Handles storing and retrieving news data from Supabase database
"""
import os
import json
import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseNewsDB:
    def __init__(self):
        """Initialize Supabase client with local caching for duplicate prevention"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        self.supabase: Client = create_client(self.url, self.key)
        print(f"🔗 Connected to Supabase: {self.url}")
        
        # Local cache for duplicate prevention
        self._url_cache = set()
        self._title_cache = set()
        self._cache_loaded = False
        self._cache_file = 'data/article_cache.json'
    
    def create_tables(self):
        """Add missing columns to existing news_articles table"""
        try:
            # Add only essential missing columns to existing news_articles table
            alter_table_sql = """
            -- Add essential missing columns to news_articles table
            ALTER TABLE news_articles 
            ADD COLUMN IF NOT EXISTS description TEXT,
            """
            
            # Create aggregation_runs table to track each run
            runs_schema = """
            CREATE TABLE IF NOT EXISTS aggregation_runs (
                id SERIAL PRIMARY KEY,
                run_timestamp TIMESTAMP DEFAULT NOW(),
                execution_time_seconds FLOAT,
                total_articles INTEGER,
                articles_with_images INTEGER,
                image_success_rate TEXT,
                total_duplicates_removed INTEGER,
                title_duplicates INTEGER,
                url_duplicates INTEGER,
                content_duplicates INTEGER,
                rss_sources INTEGER,
                newsapi_sources INTEGER,
                api_requests_used INTEGER,
                primary_key_requests INTEGER,
                secondary_key_requests INTEGER,
                tertiary_key_requests INTEGER,
                current_api_key TEXT,
                data_sources_active JSONB,
                deduplication_settings JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_news_articles_link ON news_articles(link);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published);",
                "CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON aggregation_runs(run_timestamp);"
            ]
            
            print("🔧 Adding missing columns to existing news_articles table...")
            
            # Note: Supabase Python client doesn't support raw SQL execution
            # You'll need to run these SQL commands in the Supabase dashboard
            print("⚠️  Please run the following SQL in your Supabase dashboard:")
            print("\n" + "="*60)
            print(alter_table_sql)
            print(runs_schema)
            for index in indexes:
                print(index)
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
    
    def insert_articles(self, articles: List[Dict[str, Any]], is_enhanced: bool = False) -> bool:
        """Insert articles into the database (enhanced or raw) with duplicate checking"""
        try:
            if not articles:
                print("⚠️  No articles to insert")
                return True
            
            # Enhanced validation: articles must have image + title + description
            validation_stats = {
                'total_articles': len(articles),
                'missing_image': 0,
                'missing_title': 0,
                'missing_description': 0,
                'passed_validation': 0
            }
            
            validated_articles = []
            
            for article in articles:
                # Validation Rule 1: Must have image
                if not article.get('image_url', '').strip():
                    validation_stats['missing_image'] += 1
                    continue
                
                # Validation Rule 2: Must have title (minimum 10 characters)
                if not article.get('title') or len(article.get('title', '').strip()) < 10:
                    validation_stats['missing_title'] += 1
                    continue
                
                # Validation Rule 3: Must have description (at least 50 characters)
                has_description = article.get('description') and len(article.get('description', '').strip()) > 50
                
                if not has_description:
                    validation_stats['missing_description'] += 1
                    continue
                
                # Article passed all validation rules
                validation_stats['passed_validation'] += 1
                validated_articles.append(article)
            
            # Print validation summary
            print(f"\n📊 Article Validation Summary:")
            print(f"  📰 Total articles processed: {validation_stats['total_articles']}")
            print(f"  🖼️  Missing image: {validation_stats['missing_image']}")
            print(f"  📝 Missing/short title: {validation_stats['missing_title']}")
            print(f"  📄 Missing/short description: {validation_stats['missing_description']}")
            print(f"  ✅ Passed validation: {validation_stats['passed_validation']}")
            
            if not validated_articles:
                print("⚠️  No articles passed validation rules")
                print("💡 Validation requires: image + title (10+ chars) + description (50+ chars)")
                return True
            
            print(f"🎯 Validation filter: {(validation_stats['passed_validation']/validation_stats['total_articles']*100):.1f}% articles met validation standards")
            
            # NEW: Check for existing articles in database to prevent duplicates
            print(f"🔍 Checking for existing articles in database...")
            new_articles = self._filter_existing_articles(validated_articles)
            
            if not new_articles:
                print("⚠️  All articles already exist in database - no new articles to insert")
                return True
            
            print(f"📊 Duplicate Check Results:")
            print(f"  📰 Articles after validation: {len(validated_articles)}")
            print(f"  🆕 New articles to insert: {len(new_articles)}")
            print(f"  🔄 Existing articles skipped: {len(validated_articles) - len(new_articles)}")
            print(f"🖼️  Inserting {len(new_articles)} new articles into Supabase...")
            
            # Prepare articles for insertion - only essential fields
            processed_articles = []
            for article in new_articles:
                # Generate article_id if not present (using hash of link/url)
                article_id = article.get('article_id')
                article_link = article.get('link', '') or article.get('url', '')
                if not article_id and article_link:
                    import hashlib
                    article_id = hashlib.md5(article_link.encode()).hexdigest()
                
                # Determine category - use specific metadata if available, otherwise use main category
                category = article.get('category', '')
                
                # Override category with specific metadata if present
                if article.get('indian_topic'):
                    # Map indian_economy -> economy, indian_politics -> politics
                    topic = article.get('indian_topic', '').lower().replace(' ', '')
                    if 'economy' in topic:
                        category = 'economy'
                    elif 'politics' in topic:
                        category = 'politics'
                    else:
                        category = 'india'
                elif article.get('geopolitical_topic'):
                    # All geopolitical topics -> geopolitics
                    category = 'geopolitics'
                elif article.get('region') and article.get('region').lower() == 'india':
                    # regional_india -> india
                    category = 'india'
                elif article.get('region'):
                    # Other regions keep their name (no underscores for frontend)
                    category = article.get('region', '').lower().replace(' ', '').replace('_', '')
                elif article.get('state') or article.get('city'):
                    # Indian states/cities -> india
                    category = 'india'
                
                processed_article = {
                    'title': article.get('title', ''),
                    'link': article.get('link', '') or article.get('url', ''),  # Use 'link' as primary field
                    'published': self._parse_datetime(article.get('published')),
                    'source': article.get('source', ''),
                    'category': category,
                    'description': article.get('description', ''),
                    'image_url': article.get('image_url', ''),
                    'article_id': article_id
                }
                
                # Description is now always included as primary content field
                
                processed_articles.append(processed_article)
            
            # Insert in batches to avoid timeout
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(processed_articles), batch_size):
                batch = processed_articles[i:i + batch_size]
                
                try:
                    result = self.supabase.table('news_articles').insert(batch).execute()
                    
                    total_inserted += len(batch)
                    print(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} articles")
                    
                except Exception as batch_error:
                    print(f"❌ Error inserting batch {i//batch_size + 1}: {batch_error}")
                    continue
            
            print(f"🎉 Successfully inserted {total_inserted} validated articles")
            
            # Update cache with newly inserted articles
            self._update_cache(processed_articles)
            print(f"📋 Cache updated with {len(processed_articles)} new articles")
            
            return True
            
        except Exception as e:
            print(f"❌ Error inserting articles: {e}")
            return False
    
    def insert_aggregation_run(self, combined_data: Dict[str, Any]) -> bool:
        """Insert aggregation run metadata (simplified - just log for now)"""
        try:
            dedup_info = combined_data.get('deduplication_info', {})
            api_usage = combined_data.get('newsapi_data', {}).get('api_usage', {})
            
            print("📊 Run Summary:")
            print(f"  ⏱️  Execution time: {combined_data.get('execution_time_seconds', 0)} seconds")
            print(f"  📰 Total articles: {combined_data.get('total_articles', 0)}")
            print(f"  🖼️  Articles with images: {combined_data.get('total_articles_with_images', 0)}")
            print(f"  🗑️  Duplicates removed: {dedup_info.get('total_duplicates_removed', 0)}")
            print(f"  🔑 API requests used: {api_usage.get('total_requests', 0)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error logging run metadata: {e}")
            return False
    
    def insert_enhancement_run(self, enhancement_metadata: Dict[str, Any]) -> bool:
        """Insert AI enhancement run metadata"""
        try:
            enhancement_info = enhancement_metadata.get('enhancement_info', {})
            
            print("📊 AI Enhancement Run Summary:")
            print(f"  🤖 Total articles processed: {enhancement_info.get('total_articles_processed', 0)}")
            print(f"  ✨ Articles enhanced: {enhancement_info.get('articles_enhanced', 0)}")
            print(f"  ⏭️  Articles skipped: {enhancement_info.get('articles_skipped', 0)}")
            print(f"  📈 Enhancement rate: {enhancement_info.get('enhancement_rate', '0%')}")
            print(f"  🔧 API version: {enhancement_info.get('api_version', 'N/A')}")
            print(f"  🧠 Model used: {enhancement_info.get('model_used', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error logging enhancement metadata: {e}")
            return False
    
    def get_recent_articles(self, limit: int = 100, category: Optional[str] = None) -> List[Dict]:
        """Get recent articles from database"""
        try:
            query = self.supabase.table('news_articles').select('*').order('created_at', desc=True)
            
            if category:
                query = query.eq('category', category)
            
            result = query.limit(limit).execute()
            return result.data
            
        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            return []
    
    def cleanup_invalid_titles(self) -> Dict[str, int]:
        """Remove articles with invalid titles (metadata/schedule) from database"""
        cleanup_stats = {
            'total_checked': 0,
            'invalid_titles_found': 0,
            'articles_removed': 0
        }
        
        try:
            # Get all articles to check titles
            response = self.supabase.table('news_articles').select('id, title').execute()
            articles = response.data
            cleanup_stats['total_checked'] = len(articles)
            
            invalid_article_ids = []
            
            for article in articles:
                title = article.get('title', '')
                # Basic title validation
                if len(title.strip()) < 10:
                    invalid_article_ids.append(article['id'])
                    cleanup_stats['invalid_titles_found'] += 1
                    print(f"❌ Invalid title found: '{title[:60]}...'")
            
            # Remove invalid articles in batches
            if invalid_article_ids:
                print(f"\n🧹 Removing {len(invalid_article_ids)} articles with invalid titles...")
                
                # Remove in batches of 100
                batch_size = 100
                for i in range(0, len(invalid_article_ids), batch_size):
                    batch = invalid_article_ids[i:i + batch_size]
                    
                    delete_response = self.supabase.table('news_articles').delete().in_('id', batch).execute()
                    cleanup_stats['articles_removed'] += len(batch)
                    print(f"  🗑️  Removed batch {i//batch_size + 1}: {len(batch)} articles")
            
            print(f"\n✅ Cleanup completed!")
            print(f"  📊 Total articles checked: {cleanup_stats['total_checked']}")
            print(f"  ❌ Invalid titles found: {cleanup_stats['invalid_titles_found']}")
            print(f"  🗑️  Articles removed: {cleanup_stats['articles_removed']}")
            
            return cleanup_stats
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return cleanup_stats

    def get_articles_with_images(self, limit: int = 50) -> List[Dict]:
        """Get validated articles that passed validation (images + title + description)"""
        try:
            # Filter articles that have image_url and description
            result = self.supabase.table('news_articles').select('*').neq('image_url', '').neq('description', '').order('id', desc=True).limit(limit).execute()
            
            # Additional client-side validation for extra assurance
            validated_articles = []
            for article in result.data:
                if (article.get('image_url') and 
                    article.get('title') and len(article.get('title', '')) > 10 and
                    (article.get('description') and 
                     (article.get('description') and len(article.get('description', '')) > 50))):
                    validated_articles.append(article)
            
            return validated_articles
            
        except Exception as e:
            print(f"❌ Error fetching validated articles: {e}")
            return []
    
    def get_aggregation_stats(self) -> Dict:
        """Get aggregation statistics"""
        try:
            # Get total articles
            total_result = self.supabase.table('news_articles').select('id', count='exact').execute()
            total_articles = total_result.count
            
            # Get articles with images (non-empty image_url)
            images_result = self.supabase.table('news_articles').select('id', count='exact').neq('image_url', '').execute()
            articles_with_images = images_result.count
            
            # Get articles with descriptions
            descriptions_result = self.supabase.table('news_articles').select('id', count='exact').neq('description', '').execute()
            articles_with_descriptions = descriptions_result.count
            
            return {
                'total_articles': total_articles,
                'articles_with_images': articles_with_images,
                'articles_with_descriptions': articles_with_descriptions,
                'image_success_rate': f"{(articles_with_images/total_articles*100):.1f}%" if total_articles > 0 else "0%"
            }
            
        except Exception as e:
            print(f"❌ Error fetching stats: {e}")
            return {}
    
    def _load_cache(self):
        """Load existing URLs and titles from local cache file"""
        try:
            if self._cache_loaded:
                return
            
            print("📂 Loading article cache for duplicate prevention...")
            
            # Try to load from cache file first
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self._url_cache = set(cache_data.get('urls', []))
                    self._title_cache = set(cache_data.get('titles', []))
                    print(f"  📋 Loaded cache: {len(self._url_cache)} URLs, {len(self._title_cache)} titles")
            else:
                # First time - build cache from database
                print("  🔄 Building initial cache from database...")
                self._build_cache_from_database()
            
            self._cache_loaded = True
            
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
            print("  🔄 Building cache from database...")
            self._build_cache_from_database()
            self._cache_loaded = True
    
    def _build_cache_from_database(self):
        """Build cache by fetching all existing URLs and titles from database"""
        try:
            # Fetch all URLs and titles from database
            result = self.supabase.table('news_articles').select('link, title').execute()
            
            for row in result.data:
                if row.get('link'):
                    self._url_cache.add(row['link'])
                if row.get('title'):
                    self._title_cache.add(row['title'])
            
            print(f"  ✅ Built cache: {len(self._url_cache)} URLs, {len(self._title_cache)} titles")
            self._save_cache()
            
        except Exception as e:
            print(f"❌ Error building cache from database: {e}")
    
    def _save_cache(self):
        """Save cache to local file"""
        try:
            os.makedirs('data', exist_ok=True)
            cache_data = {
                'urls': list(self._url_cache),
                'titles': list(self._title_cache),
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️  Error saving cache: {e}")
    
    def _update_cache(self, articles: List[Dict[str, Any]]):
        """Update cache with newly inserted articles"""
        for article in articles:
            url = article.get('link', '') or article.get('url', '')
            title = article.get('title', '').strip()
            
            if url:
                self._url_cache.add(url)
            if title:
                self._title_cache.add(title)
        
        # Save updated cache
        self._save_cache()
    
    def _filter_existing_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out articles using fast local cache (no database queries during filtering)"""
        try:
            if not articles:
                return []
            
            # Load cache if not already loaded
            self._load_cache()
            
            new_articles = []
            duplicate_stats = {
                'checked': 0,
                'duplicates_found': 0,
                'url_matches': 0,
                'title_matches': 0
            }
            
            print(f"🚀 Fast cache-based duplicate checking for {len(articles)} articles...")
            
            for article in articles:
                duplicate_stats['checked'] += 1
                article_url = article.get('link', '') or article.get('url', '')
                article_title = article.get('title', '').strip()
                
                is_duplicate = False
                
                # Check 1: URL-based duplicate detection using cache
                if article_url and article_url in self._url_cache:
                    is_duplicate = True
                    duplicate_stats['url_matches'] += 1
                
                # Check 2: Title-based duplicate detection using cache
                elif article_title and article_title in self._title_cache:
                    is_duplicate = True
                    duplicate_stats['title_matches'] += 1
                
                if not is_duplicate:
                    new_articles.append(article)
                else:
                    duplicate_stats['duplicates_found'] += 1
            
            print(f"  📊 Cache-based duplicate check summary:")
            print(f"    🔍 Articles checked: {duplicate_stats['checked']}")
            print(f"    🔄 Duplicates found: {duplicate_stats['duplicates_found']}")
            print(f"    🔗 URL matches: {duplicate_stats['url_matches']}")
            print(f"    📝 Title matches: {duplicate_stats['title_matches']}")
            print(f"    🆕 New articles: {len(new_articles)}")
            print(f"    ⚡ Cache performance: No database queries needed!")
            
            return new_articles
            
        except Exception as e:
            print(f"❌ Error in cache-based filtering: {e}")
            print("⚠️  Proceeding with all articles (cache check failed)")
            return articles
    
    def refresh_cache(self):
        """Manually refresh the cache from database (useful for maintenance)"""
        print("🔄 Refreshing article cache from database...")
        self._cache_loaded = False
        self._url_cache.clear()
        self._title_cache.clear()
        self._load_cache()
        print("✅ Cache refreshed successfully")
    
    def get_cache_stats(self):
        """Get cache statistics"""
        if not self._cache_loaded:
            self._load_cache()
        
        return {
            'urls_cached': len(self._url_cache),
            'titles_cached': len(self._title_cache),
            'cache_file_exists': os.path.exists(self._cache_file),
            'cache_loaded': self._cache_loaded
        }
    
    def _parse_datetime(self, date_str: str) -> Optional[str]:
        """Parse various datetime formats to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try parsing common formats
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.isoformat()
        except:
            return None
    
    def test_connection(self) -> bool:
        """Test the Supabase connection"""
        try:
            # Try a simple query
            result = self.supabase.table('news_articles').select('id').limit(1).execute()
            print("✅ Supabase connection successful")
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False

def main():
    """Test the Supabase integration"""
    try:
        db = SupabaseNewsDB()
        
        # Test connection
        if db.test_connection():
            print("🎉 Supabase integration ready!")
            
            # Show stats if tables exist
            stats = db.get_aggregation_stats()
            if stats:
                print(f"\n📊 Database Stats:")
                print(f"  Total articles: {stats.get('total_articles', 0)}")
                print(f"  Articles with images: {stats.get('articles_with_images', 0)}")
                print(f"  Articles with descriptions: {stats.get('articles_with_descriptions', 0)}")
        else:
            print("❌ Please check your Supabase credentials")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()