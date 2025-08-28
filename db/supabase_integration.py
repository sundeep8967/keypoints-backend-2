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
                "CREATE INDEX IF NOT EXISTS idx_news_articles_quality_score ON news_articles(quality_score DESC);",
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
            
            # Enhanced validation: articles must have image + title + (summary OR keypoints)
            validation_stats = {
                'total_articles': len(articles),
                'missing_image': 0,
                'missing_title': 0,
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
                
                # Validation Rule 3: Must have description
                has_description = article.get('description') and len(article.get('description', '').strip()) > 50
                
                if not has_description:
                    validation_stats['missing_summary_and_keypoints'] += 1
                    continue
                
                # Article passed all validation rules
                validation_stats['passed_validation'] += 1
                validated_articles.append(article)
            
            # Print validation summary
            print(f"\n📊 Article Validation Summary:")
            print(f"  📰 Total articles processed: {validation_stats['total_articles']}")
            print(f"  🖼️  Missing image: {validation_stats['missing_image']}")
            print(f"  📝 Missing/short title: {validation_stats['missing_title']}")
            print(f"  📄 Missing description: {validation_stats['missing_summary_and_keypoints']}")
            print(f"  ✅ Passed validation: {validation_stats['passed_validation']}")
            
            if not validated_articles:
                print("⚠️  No articles passed validation rules")
                print("💡 Validation requires: image + title (10+ chars) + description")
                return True
            
            print(f"🎯 Quality filter: {(validation_stats['passed_validation']/validation_stats['total_articles']*100):.1f}% articles met quality standards")
            print(f"🖼️  Inserting {len(validated_articles)} high-quality articles into Supabase...")
            
            # Prepare articles for insertion - only essential fields
            processed_articles = []
            for article in validated_articles:
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
            
            print(f"🎉 Successfully inserted {total_inserted} high-quality articles")
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
        """Get high-quality articles that passed validation (images + title + description)"""
        try:
            # Filter articles that have image_url and description
            result = self.supabase.table('news_articles').select('*').neq('image_url', '').neq('description', '').order('id', desc=True).limit(limit).execute()
            
            # Additional client-side validation for extra quality assurance
            validated_articles = []
            for article in result.data:
                if (article.get('image_url') and 
                    article.get('title') and len(article.get('title', '')) > 10 and
                    (article.get('description') and 
                     (article.get('description') and len(article.get('description', '')) > 50))):
                    validated_articles.append(article)
            
            return validated_articles
            
        except Exception as e:
            print(f"❌ Error fetching high-quality articles: {e}")
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