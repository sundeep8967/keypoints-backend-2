#!/usr/bin/env python3
"""
Advanced Space Optimization System
Implements intelligent file management, compression, and cleanup strategies
"""
import os
import json
import gzip
import sqlite3
import datetime
import hashlib
from typing import Dict, List, Any
from pathlib import Path

class SpaceOptimizer:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Database for efficient storage
        self.db_path = self.data_dir / 'news_history.db'
        self.init_database()
        
        # Compression settings
        self.compress_after_days = 1  # Compress files older than 1 day
        self.delete_after_days = 30   # Delete files older than 30 days
        
        print(f"🗜️  Space Optimizer initialized: {self.data_dir}")
    
    def init_database(self):
        """Initialize SQLite database for efficient storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_hash TEXT UNIQUE,
                    title_hash TEXT,
                    content_hash TEXT,
                    source TEXT,
                    category TEXT,
                    published_date TEXT,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    url TEXT,
                    description_snippet TEXT,  -- Only first 200 chars
                    is_enhanced BOOLEAN DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_articles INTEGER,
                    unique_articles INTEGER,
                    duplicates_removed INTEGER,
                    sources_count INTEGER,
                    file_size_mb REAL
                )
            ''')
            
            # Create indexes for fast lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_url_hash ON articles(url_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_title_hash ON articles(title_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_content_hash ON articles(content_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created_date ON articles(created_date)')
            
            conn.commit()
    
    def compress_old_files(self):
        """Compress JSON files older than specified days"""
        print(f"🗜️  Compressing files older than {self.compress_after_days} days...")
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.compress_after_days)
        compressed_count = 0
        space_saved = 0
        
        for json_file in self.data_dir.glob('*.json'):
            if json_file.stat().st_mtime < cutoff_date.timestamp():
                # Skip if already compressed version exists
                gz_file = json_file.with_suffix('.json.gz')
                if gz_file.exists():
                    continue
                
                try:
                    # Read and compress
                    with open(json_file, 'rb') as f_in:
                        original_size = json_file.stat().st_size
                        with gzip.open(gz_file, 'wb') as f_out:
                            f_out.write(f_in.read())
                    
                    compressed_size = gz_file.stat().st_size
                    space_saved += (original_size - compressed_size)
                    
                    # Remove original
                    json_file.unlink()
                    compressed_count += 1
                    
                    compression_ratio = (1 - compressed_size/original_size) * 100
                    print(f"  🗜️  {json_file.name}: {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({compression_ratio:.1f}% saved)")
                
                except Exception as e:
                    print(f"❌ Error compressing {json_file}: {e}")
        
        print(f"✅ Compressed {compressed_count} files, saved {space_saved/1024/1024:.2f}MB")
    
    def cleanup_old_files(self):
        """Remove old compressed files and history"""
        print(f"🧹 Cleaning up files older than {self.delete_after_days} days...")
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.delete_after_days)
        deleted_count = 0
        space_freed = 0
        
        # Clean up compressed files
        for gz_file in self.data_dir.glob('*.gz'):
            if gz_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    file_size = gz_file.stat().st_size
                    gz_file.unlink()
                    deleted_count += 1
                    space_freed += file_size
                    print(f"  🗑️  Deleted: {gz_file.name}")
                except Exception as e:
                    print(f"❌ Error deleting {gz_file}: {e}")
        
        # Clean up history directories
        for history_dir in ['rss_history', 'newsapi_history']:
            history_path = self.data_dir / history_dir
            if history_path.exists():
                deleted_count += self._cleanup_history_dir(history_path, cutoff_date)
        
        print(f"✅ Deleted {deleted_count} files, freed {space_freed/1024/1024:.2f}MB")
    
    def _cleanup_history_dir(self, history_dir: Path, cutoff_date: datetime.datetime) -> int:
        """Clean up history directory"""
        deleted_count = 0
        
        for history_file in history_dir.glob('*.json'):
            if history_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    history_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Error deleting {history_file}: {e}")
        
        return deleted_count
    
    def store_articles_efficiently(self, articles: List[Dict], source_type: str = 'combined'):
        """Store articles in database instead of large JSON files"""
        print(f"💾 Storing {len(articles)} articles efficiently in database...")
        
        stored_count = 0
        duplicate_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for article in articles:
                try:
                    # Create hashes
                    url = article.get('url', '') or article.get('link', '')
                    title = article.get('title', '')
                    description = article.get('description', '')
                    
                    url_hash = hashlib.md5(url.encode()).hexdigest() if url else None
                    title_hash = hashlib.md5(title.lower().encode()).hexdigest() if title else None
                    content_hash = hashlib.md5(f"{title}{description}".encode()).hexdigest()
                    
                    # Check if already exists
                    existing = conn.execute(
                        'SELECT id FROM articles WHERE url_hash = ? OR content_hash = ?',
                        (url_hash, content_hash)
                    ).fetchone()
                    
                    if existing:
                        duplicate_count += 1
                        continue
                    
                    # Store efficiently (only essential data)
                    conn.execute('''
                        INSERT INTO articles (
                            url_hash, title_hash, content_hash, source, category,
                            published_date, title, url, description_snippet, is_enhanced
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        url_hash,
                        title_hash,
                        content_hash,
                        article.get('source', ''),
                        article.get('category', ''),
                        article.get('published', '') or article.get('publishedAt', ''),
                        title,
                        url,
                        description[:200] if description else '',  # Only first 200 chars
                        1 if 'enhanced' in str(article) else 0
                    ))
                    
                    stored_count += 1
                
                except Exception as e:
                    print(f"⚠️  Error storing article: {e}")
            
            conn.commit()
        
        print(f"✅ Stored {stored_count} new articles, skipped {duplicate_count} duplicates")
        return stored_count, duplicate_count
    
    def create_minimal_json_output(self, articles: List[Dict], filename: str) -> str:
        """Create minimal JSON output with only essential data"""
        minimal_articles = []
        
        for article in articles:
            minimal_article = {
                'title': article.get('title', ''),
                'url': article.get('url', '') or article.get('link', ''),
                'source': article.get('source', ''),
                'category': article.get('category', ''),
                'published': article.get('published', '') or article.get('publishedAt', ''),
                'description': article.get('description', '')[:300] if article.get('description') else ''  # Limit description
            }
            
            # Only include image if it exists and is not a placeholder
            image_url = article.get('image_url', '')
            if image_url and 'placeholder' not in image_url.lower():
                minimal_article['image_url'] = image_url
            
            minimal_articles.append(minimal_article)
        
        # Create minimal output
        output_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'total_articles': len(minimal_articles),
            'articles': minimal_articles,
            'space_optimized': True,
            'note': 'Minimal output - full data in database'
        }
        
        output_path = self.data_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, separators=(',', ':'), ensure_ascii=False)  # Compact JSON
        
        file_size = output_path.stat().st_size
        print(f"💾 Created minimal output: {filename} ({file_size/1024:.1f}KB)")
        
        return str(output_path)
    
    def get_storage_statistics(self) -> Dict:
        """Get comprehensive storage statistics"""
        stats = {
            'database_size_mb': 0,
            'json_files_size_mb': 0,
            'compressed_files_size_mb': 0,
            'total_articles_in_db': 0,
            'json_files_count': 0,
            'compressed_files_count': 0,
            'space_saved_by_compression_mb': 0
        }
        
        # Database size
        if self.db_path.exists():
            stats['database_size_mb'] = self.db_path.stat().st_size / 1024 / 1024
        
        # Count articles in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('SELECT COUNT(*) FROM articles').fetchone()
                stats['total_articles_in_db'] = result[0] if result else 0
        except:
            pass
        
        # JSON files
        json_size = 0
        for json_file in self.data_dir.glob('*.json'):
            json_size += json_file.stat().st_size
            stats['json_files_count'] += 1
        stats['json_files_size_mb'] = json_size / 1024 / 1024
        
        # Compressed files
        compressed_size = 0
        for gz_file in self.data_dir.glob('*.gz'):
            compressed_size += gz_file.stat().st_size
            stats['compressed_files_count'] += 1
        stats['compressed_files_size_mb'] = compressed_size / 1024 / 1024
        
        # Estimate space saved (rough calculation)
        stats['space_saved_by_compression_mb'] = stats['compressed_files_size_mb'] * 2  # Assume 50% compression
        
        return stats
    
    def optimize_all(self):
        """Run complete optimization process"""
        print("🚀 Running complete space optimization...")
        
        # Step 1: Compress old files
        self.compress_old_files()
        
        # Step 2: Clean up very old files
        self.cleanup_old_files()
        
        # Step 3: Show statistics
        stats = self.get_storage_statistics()
        
        print("\n📊 Storage Optimization Summary:")
        print(f"  💾 Database: {stats['database_size_mb']:.2f}MB ({stats['total_articles_in_db']} articles)")
        print(f"  📄 JSON files: {stats['json_files_count']} files ({stats['json_files_size_mb']:.2f}MB)")
        print(f"  🗜️  Compressed: {stats['compressed_files_count']} files ({stats['compressed_files_size_mb']:.2f}MB)")
        print(f"  💰 Space saved: ~{stats['space_saved_by_compression_mb']:.2f}MB")
        
        total_size = stats['database_size_mb'] + stats['json_files_size_mb'] + stats['compressed_files_size_mb']
        print(f"  📊 Total storage: {total_size:.2f}MB")
        
        return stats

def main():
    """Test the space optimizer"""
    optimizer = SpaceOptimizer()
    
    # Run optimization
    stats = optimizer.optimize_all()
    
    print(f"\n✅ Space optimization completed!")
    print(f"📊 Final storage usage: {stats}")

if __name__ == "__main__":
    main()