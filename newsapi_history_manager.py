#!/usr/bin/env python3
"""
NewsAPI History Manager
Maintains local history for NewsAPI articles with advanced duplicate detection
"""
import os
import json
import hashlib
import datetime
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class NewsAPIHistoryManager:
    def __init__(self, history_dir='data/newsapi_history'):
        """Initialize NewsAPI History Manager"""
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
        # NewsAPI-specific duplicate detection settings
        self.url_similarity_threshold = 0.90
        self.title_similarity_threshold = 0.85
        self.content_similarity_threshold = 0.75
        self.fuzzy_title_threshold = 0.80
        self.time_window_hours = 72  # Consider articles within 72 hours for duplicates
        
        # NewsAPI history files
        self.global_history_file = os.path.join(history_dir, 'newsapi_global_history.json')
        self.daily_history_file = os.path.join(history_dir, f'newsapi_{datetime.date.today().isoformat()}.json')
        
        print(f"📂 NewsAPI History Manager initialized: {history_dir}")
    
    def _load_global_history(self) -> Dict:
        """Load global NewsAPI history (last 7 days)"""
        if os.path.exists(self.global_history_file):
            try:
                with open(self.global_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading global NewsAPI history: {e}")
        
        return {
            'articles': [],
            'url_hashes': set(),
            'title_hashes': set(),
            'content_hashes': set(),
            'last_updated': None,
            'total_articles_processed': 0
        }
    
    def _save_global_history(self, history: Dict):
        """Save global NewsAPI history"""
        try:
            # Convert sets to lists for JSON serialization
            history_copy = history.copy()
            history_copy['url_hashes'] = list(history.get('url_hashes', set()))
            history_copy['title_hashes'] = list(history.get('title_hashes', set()))
            history_copy['content_hashes'] = list(history.get('content_hashes', set()))
            history_copy['last_updated'] = datetime.datetime.now().isoformat()
            
            with open(self.global_history_file, 'w', encoding='utf-8') as f:
                json.dump(history_copy, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving global NewsAPI history: {e}")
    
    def _load_recent_daily_files(self, days_back=7) -> List[Dict]:
        """Load recent daily history files for comprehensive duplicate checking"""
        recent_articles = []
        
        for i in range(days_back):
            date = datetime.date.today() - datetime.timedelta(days=i)
            daily_file = os.path.join(self.history_dir, f'newsapi_{date.isoformat()}.json')
            
            if os.path.exists(daily_file):
                try:
                    with open(daily_file, 'r', encoding='utf-8') as f:
                        daily_data = json.load(f)
                        recent_articles.extend(daily_data.get('articles', []))
                except Exception as e:
                    print(f"⚠️  Error loading daily file {daily_file}: {e}")
        
        return recent_articles
    
    def _save_daily_history(self, articles: List[Dict]):
        """Save today's articles to daily history file"""
        try:
            daily_data = {
                'date': datetime.date.today().isoformat(),
                'articles': articles,
                'total_articles': len(articles),
                'created_at': datetime.datetime.now().isoformat()
            }
            
            with open(self.daily_history_file, 'w', encoding='utf-8') as f:
                json.dump(daily_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving daily NewsAPI history: {e}")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""
        
        # Remove common URL variations
        url = url.lower().strip()
        
        # Remove protocol variations
        for protocol in ['https://', 'http://']:
            if url.startswith(protocol):
                url = url[len(protocol):]
                break
        
        # Remove www prefix
        if url.startswith('www.'):
            url = url[4:]
        
        # Remove trailing slash and query parameters
        url = url.split('?')[0].split('#')[0].rstrip('/')
        
        return url
    
    def _create_content_hash(self, article: Dict) -> str:
        """Create a hash from article content for duplicate detection"""
        # Combine title, description, and source for content hashing
        title = article.get('title', '').strip().lower()
        description = article.get('description', '').strip().lower()
        source = article.get('source', {}).get('name', '').strip().lower()
        
        # Remove extra whitespace and special characters
        import re
        title = re.sub(r'\s+', ' ', title)
        description = re.sub(r'\s+', ' ', description)
        
        # Create combined content
        content = f"{source}|{title}|{description}"
        
        # Create hash
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _is_within_time_window(self, article_date: str) -> bool:
        """Check if article is within the time window for duplicate checking"""
        try:
            if not article_date:
                return True  # Include articles without dates
            
            # Parse article date
            from dateutil import parser
            article_datetime = parser.parse(article_date)
            
            # Check if within time window
            cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=self.time_window_hours)
            return article_datetime > cutoff_time
            
        except Exception as e:
            print(f"⚠️  Error parsing date {article_date}: {e}")
            return True  # Include articles with unparseable dates
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using multiple methods"""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        title1 = title1.lower().strip()
        title2 = title2.lower().strip()
        
        # Method 1: Exact match
        if title1 == title2:
            return 1.0
        
        # Method 2: Sequence matcher
        seq_similarity = SequenceMatcher(None, title1, title2).ratio()
        
        # Method 3: Word-based similarity
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if words1 and words2:
            word_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            word_similarity = 0.0
        
        # Return the maximum similarity
        return max(seq_similarity, word_similarity)
    
    def _calculate_content_similarity(self, article1: Dict, article2: Dict) -> float:
        """Calculate content similarity using TF-IDF and cosine similarity"""
        try:
            # Extract content
            content1 = f"{article1.get('title', '')} {article1.get('description', '')}"
            content2 = f"{article2.get('title', '')} {article2.get('description', '')}"
            
            # Skip if content is too short
            if len(content1.strip()) < 20 or len(content2.strip()) < 20:
                return 0.0
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2),
                min_df=1
            )
            
            tfidf_matrix = vectorizer.fit_transform([content1, content2])
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return float(similarity_matrix[0, 1])
            
        except Exception as e:
            print(f"⚠️  Error calculating content similarity: {e}")
            return 0.0
    
    def check_newsapi_duplicates(self, new_articles: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Advanced duplicate detection for NewsAPI articles using global and daily history
        """
        print(f"🔍 NewsAPI duplicate checking for {len(new_articles)} articles...")
        
        # Load global history and recent daily files
        global_history = self._load_global_history()
        recent_articles = self._load_recent_daily_files()
        
        # Convert sets back from JSON
        url_hashes = set(global_history.get('url_hashes', []))
        title_hashes = set(global_history.get('title_hashes', []))
        content_hashes = set(global_history.get('content_hashes', []))
        
        duplicate_stats = {
            'total_checked': len(new_articles),
            'duplicates_found': 0,
            'url_duplicates': 0,
            'title_duplicates': 0,
            'content_duplicates': 0,
            'fuzzy_duplicates': 0,
            'time_filtered': 0,
            'new_articles': 0,
            'detection_methods': []
        }
        
        new_unique_articles = []
        processed_articles = []
        
        for article in new_articles:
            is_duplicate = False
            detection_method = None
            similarity_score = 0.0
            
            article_url = article.get('url', '')
            article_title = article.get('title', '').strip()
            article_date = article.get('publishedAt', '')
            
            # Filter by time window first
            if not self._is_within_time_window(article_date):
                duplicate_stats['time_filtered'] += 1
                continue
            
            # Method 1: URL-based duplicate detection
            if article_url:
                normalized_url = self._normalize_url(article_url)
                url_hash = hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
                
                if url_hash in url_hashes:
                    is_duplicate = True
                    detection_method = 'url_exact'
                    similarity_score = 1.0
                    duplicate_stats['url_duplicates'] += 1
            
            # Method 2: Title hash duplicate detection
            if not is_duplicate and article_title:
                title_hash = hashlib.md5(article_title.lower().encode('utf-8')).hexdigest()
                
                if title_hash in title_hashes:
                    is_duplicate = True
                    detection_method = 'title_exact'
                    similarity_score = 1.0
                    duplicate_stats['title_duplicates'] += 1
            
            # Method 3: Content hash duplicate detection
            if not is_duplicate:
                content_hash = self._create_content_hash(article)
                
                if content_hash in content_hashes:
                    is_duplicate = True
                    detection_method = 'content_hash'
                    similarity_score = 1.0
                    duplicate_stats['content_duplicates'] += 1
            
            # Method 4: Fuzzy title matching against recent articles
            if not is_duplicate and article_title:
                # Check against recent articles (last 100 for performance)
                recent_check = recent_articles[-100:] if len(recent_articles) > 100 else recent_articles
                
                for recent_article in recent_check:
                    recent_title = recent_article.get('title', '')
                    title_similarity = self._calculate_title_similarity(article_title, recent_title)
                    
                    if title_similarity >= self.fuzzy_title_threshold:
                        is_duplicate = True
                        detection_method = 'title_fuzzy'
                        similarity_score = title_similarity
                        duplicate_stats['fuzzy_duplicates'] += 1
                        break
            
            # Method 5: Content similarity detection
            if not is_duplicate:
                # Check content similarity against recent articles
                recent_check = recent_articles[-50:] if len(recent_articles) > 50 else recent_articles
                
                for recent_article in recent_check:
                    content_similarity = self._calculate_content_similarity(article, recent_article)
                    
                    if content_similarity >= self.content_similarity_threshold:
                        is_duplicate = True
                        detection_method = 'content_similarity'
                        similarity_score = content_similarity
                        duplicate_stats['content_duplicates'] += 1
                        break
            
            if not is_duplicate:
                # Article is unique - add to results and update history
                new_unique_articles.append(article)
                duplicate_stats['new_articles'] += 1
                
                # Add to processed articles for history
                processed_articles.append({
                    'title': article_title,
                    'url': article_url,
                    'publishedAt': article_date,
                    'source': article.get('source', {}).get('name', ''),
                    'added_date': datetime.datetime.now().isoformat(),
                    'content_hash': self._create_content_hash(article)
                })
                
                # Update hash sets
                if article_url:
                    normalized_url = self._normalize_url(article_url)
                    url_hash = hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
                    url_hashes.add(url_hash)
                
                if article_title:
                    title_hash = hashlib.md5(article_title.lower().encode('utf-8')).hexdigest()
                    title_hashes.add(title_hash)
                
                content_hash = self._create_content_hash(article)
                content_hashes.add(content_hash)
            
            else:
                duplicate_stats['duplicates_found'] += 1
                duplicate_stats['detection_methods'].append({
                    'method': detection_method,
                    'similarity': similarity_score,
                    'title': article_title[:50] + '...' if len(article_title) > 50 else article_title
                })
        
        # Update and save global history
        all_historical = global_history.get('articles', []) + processed_articles
        global_history.update({
            'articles': all_historical[-2000:],  # Keep last 2000 articles
            'url_hashes': url_hashes,
            'title_hashes': title_hashes,
            'content_hashes': content_hashes,
            'total_articles_processed': global_history.get('total_articles_processed', 0) + len(new_articles)
        })
        
        self._save_global_history(global_history)
        
        # Save daily history
        if processed_articles:
            self._save_daily_history(processed_articles)
        
        # Print detailed results
        print(f"  📊 NewsAPI duplicate detection results:")
        print(f"    🔍 Articles checked: {duplicate_stats['total_checked']}")
        print(f"    ⏰ Time filtered: {duplicate_stats['time_filtered']}")
        print(f"    🔄 Duplicates found: {duplicate_stats['duplicates_found']}")
        print(f"    🔗 URL duplicates: {duplicate_stats['url_duplicates']}")
        print(f"    📝 Title duplicates: {duplicate_stats['title_duplicates']}")
        print(f"    📄 Content duplicates: {duplicate_stats['content_duplicates']}")
        print(f"    🧠 Fuzzy duplicates: {duplicate_stats['fuzzy_duplicates']}")
        print(f"    🆕 New unique articles: {duplicate_stats['new_articles']}")
        print(f"    📚 Total historical articles: {len(all_historical)}")
        
        return new_unique_articles, duplicate_stats
    
    def get_newsapi_statistics(self) -> Dict:
        """Get NewsAPI history statistics"""
        global_history = self._load_global_history()
        
        # Count daily files
        daily_files = [f for f in os.listdir(self.history_dir) if f.startswith('newsapi_') and f.endswith('.json') and f != 'newsapi_global_history.json']
        
        return {
            'total_articles_processed': global_history.get('total_articles_processed', 0),
            'historical_articles_stored': len(global_history.get('articles', [])),
            'url_hashes_count': len(global_history.get('url_hashes', [])),
            'title_hashes_count': len(global_history.get('title_hashes', [])),
            'content_hashes_count': len(global_history.get('content_hashes', [])),
            'daily_files_count': len(daily_files),
            'last_updated': global_history.get('last_updated'),
            'time_window_hours': self.time_window_hours
        }
    
    def cleanup_old_newsapi_history(self, days_to_keep: int = 7):
        """Clean up old NewsAPI daily history files"""
        print(f"🧹 Cleaning up NewsAPI history older than {days_to_keep} days...")
        
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        cleaned_count = 0
        
        for filename in os.listdir(self.history_dir):
            if filename.startswith('newsapi_') and filename.endswith('.json') and filename != 'newsapi_global_history.json':
                try:
                    # Extract date from filename
                    date_str = filename.replace('newsapi_', '').replace('.json', '')
                    file_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    if file_date < cutoff_date:
                        filepath = os.path.join(self.history_dir, filename)
                        os.remove(filepath)
                        cleaned_count += 1
                        print(f"  🗑️  Removed old file: {filename}")
                
                except Exception as e:
                    print(f"⚠️  Error processing file {filename}: {e}")
        
        print(f"✅ NewsAPI history cleanup completed: {cleaned_count} files removed")

def main():
    """Test the NewsAPI History Manager"""
    manager = NewsAPIHistoryManager()
    
    # Test with sample NewsAPI articles
    test_articles = [
        {
            'title': 'Breaking: Major Tech Company Announces New Product',
            'url': 'https://example.com/tech-news/new-product-announcement',
            'description': 'A major technology company has announced a revolutionary new product that will change the industry.',
            'publishedAt': '2024-01-01T10:00:00Z',
            'source': {'name': 'TechNews'}
        },
        {
            'title': 'Market Update: Stocks Rise on Positive Economic Data',
            'url': 'https://example.com/finance/market-update-stocks-rise',
            'description': 'Stock markets showed strong gains today following the release of positive economic indicators.',
            'publishedAt': '2024-01-01T11:00:00Z',
            'source': {'name': 'FinanceDaily'}
        }
    ]
    
    print("🧪 Testing NewsAPI History Manager...")
    
    # First run - should be all new
    new_articles, stats = manager.check_newsapi_duplicates(test_articles)
    print(f"First run: {len(new_articles)} new articles")
    
    # Second run - should detect duplicates
    new_articles, stats = manager.check_newsapi_duplicates(test_articles)
    print(f"Second run: {len(new_articles)} new articles")
    
    # Show statistics
    newsapi_stats = manager.get_newsapi_statistics()
    print(f"NewsAPI statistics: {newsapi_stats}")

if __name__ == "__main__":
    main()