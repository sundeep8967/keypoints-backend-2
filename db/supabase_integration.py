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
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        self.supabase: Client = create_client(self.url, self.key)
        print(f"🔗 Connected to Supabase: {self.url}")
    
    def create_tables(self):
        """Add missing columns to existing news_articles table"""
        try:
            # Add only essential missing columns to existing news_articles table
            alter_table_sql = """
            -- Add essential missing columns to news_articles table
            ALTER TABLE news_articles 
            ADD COLUMN IF NOT EXISTS description TEXT,
            ADD COLUMN IF NOT EXISTS key_points TEXT[];
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
                "CREATE INDEX IF NOT EXISTS idx_news_articles_url ON news_articles(url);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published);",
                "CREATE INDEX IF NOT EXISTS idx_news_articles_api_source ON news_articles(api_source);",
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
    
    def insert_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """Insert only articles with images into the database"""
        try:
            if not articles:
                print("⚠️  No articles to insert")
                return True
            
            # Filter to only articles with a valid image_url
            articles_with_images = [
                article for article in articles 
                if article.get('image_url', '').strip()
            ]
            
            if not articles_with_images:
                print("⚠️  No articles with images to insert")
                return True
            
            print(f"📝 Filtering {len(articles)} articles → {len(articles_with_images)} articles with images")
            print(f"🖼️  Inserting {len(articles_with_images)} articles with images into Supabase...")
            
            # Prepare articles for insertion - only essential fields
            processed_articles = []
            for article in articles_with_images:
                # Generate article_id if not present (using hash of url/link)
                article_id = article.get('article_id')
                article_url = article.get('url') or article.get('link', '')
                if not article_id and article_url:
                    import hashlib
                    article_id = hashlib.md5(article_url.encode()).hexdigest()
                
                # Determine category - use specific metadata if available, otherwise use main category
                category = article.get('category', '')
                
                # Override category with specific metadata if present
                if article.get('indian_topic'):
                    category = f"indian_{article.get('indian_topic', '').lower().replace(' ', '_')}"
                elif article.get('geopolitical_topic'):
                    category = f"geopolitics_{article.get('geopolitical_topic', '').lower().replace(' ', '_')}"
                elif article.get('region'):
                    category = f"regional_{article.get('region', '').lower().replace(' ', '_')}"
                elif article.get('state'):
                    category = f"indian_state_{article.get('state', '').lower().replace(' ', '_')}"
                elif article.get('city'):
                    category = f"indian_city_{article.get('city', '').lower().replace(' ', '_')}"
                
                processed_article = {
                    'title': article.get('title', ''),
                    'url': article.get('url', '') or article.get('link', ''),  # Support both 'url' and 'link'
                    'published': self._parse_datetime(article.get('published')),
                    'source': article.get('source', ''),
                    'category': category,
                    'summary': article.get('summary', ''),
                    'image_url': article.get('image_url', ''),
                    'api_source': article.get('api_source', 'unknown'),
                    'article_id': article_id
                }
                
                # Add optional fields only if they have content
                if article.get('description'):
                    processed_article['description'] = article.get('description', '')
                
                if article.get('key_points') and len(article.get('key_points', [])) > 0:
                    processed_article['key_points'] = article.get('key_points', [])
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
            
            print(f"🎉 Successfully inserted {total_inserted} articles")
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
    
    def get_articles_with_images(self, limit: int = 50) -> List[Dict]:
        """Get articles that have images and key points"""
        try:
            # Filter articles that have image_url and key_points
            result = self.supabase.table('news_articles').select('*').neq('image_url', '').neq('key_points', '{}').order('id', desc=True).limit(limit).execute()
            return result.data
            
        except Exception as e:
            print(f"❌ Error fetching articles with images: {e}")
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
            
            # Get articles with key points (non-empty key_points array)
            keypoints_result = self.supabase.table('news_articles').select('id', count='exact').neq('key_points', '{}').execute()
            articles_with_keypoints = keypoints_result.count
            
            return {
                'total_articles': total_articles,
                'articles_with_images': articles_with_images,
                'articles_with_keypoints': articles_with_keypoints,
                'image_success_rate': f"{(articles_with_images/total_articles*100):.1f}%" if total_articles > 0 else "0%"
            }
            
        except Exception as e:
            print(f"❌ Error fetching stats: {e}")
            return {}
    
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
                print(f"  Articles with key points: {stats.get('articles_with_keypoints', 0)}")
        else:
            print("❌ Please check your Supabase credentials")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()