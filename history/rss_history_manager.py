#!/usr/bin/env python3
"""
RSS History Manager
Maintains local history files for each RSS feed and performs advanced duplicate detection
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

class RSSHistoryManager:
    def __init__(self, history_dir='data/rss_history'):
        """Initialize RSS History Manager"""
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
        # Advanced duplicate detection settings
        self.url_similarity_threshold = 0.90
        self.title_similarity_threshold = 0.85
        self.content_similarity_threshold = 0.75
        self.fuzzy_title_threshold = 0.80
        
        print(f"📂 RSS History Manager initialized: {history_dir}")
    
    def _get_feed_history_file(self, source_name: str) -> str:
        """Get the history file path for a specific RSS source"""
        # Sanitize source name for filename
        safe_name = "".join(c for c in source_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        return os.path.join(self.history_dir, f"{safe_name}_history.json")
    
    def _load_feed_history(self, source_name: str) -> Dict:
        """Load historical articles for a specific RSS feed"""
        history_file = self._get_feed_history_file(source_name)
        
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading history for {source_name}: {e}")
        
        # Return empty history structure
        return {
            'source': source_name,
            'articles': [],
            'url_hashes': set(),
            'title_hashes': set(),
            'last_updated': None,
            'total_articles_seen': 0
        }
    
    def _save_feed_history(self, source_name: str, history: Dict):
        """Save historical articles for a specific RSS feed"""
        history_file = self._get_feed_history_file(source_name)
        
        try:
            # Convert sets to lists for JSON serialization
            history_copy = history.copy()
            history_copy['url_hashes'] = list(history.get('url_hashes', set()))
            history_copy['title_hashes'] = list(history.get('title_hashes', set()))
            history_copy['last_updated'] = datetime.datetime.now().isoformat()
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_copy, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"❌ Error saving history for {source_name}: {e}")
    
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
        # Combine title and description for content hashing
        title = article.get('title', '').strip().lower()
        description = article.get('description', '').strip().lower()
        
        # Remove extra whitespace and special characters
        import re
        title = re.sub(r'\s+', ' ', title)
        description = re.sub(r'\s+', ' ', description)
        
        # Create combined content
        content = f"{title}|{description}"
        
        # Create hash
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
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
    
    def check_duplicates_advanced(self, new_articles: List[Dict], source_name: str) -> Tuple[List[Dict], Dict]:
        """
        Advanced duplicate detection using multiple algorithms and historical data
        """
        print(f"🔍 Advanced duplicate checking for {source_name} ({len(new_articles)} articles)...")
        
        # Load historical data for this RSS feed
        history = self._load_feed_history(source_name)
        
        # Convert sets back from JSON
        url_hashes = set(history.get('url_hashes', []))
        title_hashes = set(history.get('title_hashes', []))
        historical_articles = history.get('articles', [])
        
        duplicate_stats = {
            'total_checked': len(new_articles),
            'duplicates_found': 0,
            'url_duplicates': 0,
            'title_duplicates': 0,
            'content_duplicates': 0,
            'fuzzy_duplicates': 0,
            'new_articles': 0,
            'detection_methods': []
        }
        
        new_unique_articles = []
        
        for article in new_articles:
            is_duplicate = False
            detection_method = None
            similarity_score = 0.0
            
            article_url = article.get('link', '') or article.get('url', '')
            article_title = article.get('title', '').strip()
            
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
            
            # Method 3: Fuzzy title matching against recent articles
            if not is_duplicate and article_title:
                # Check against last 100 historical articles for performance
                recent_articles = historical_articles[-100:] if len(historical_articles) > 100 else historical_articles
                
                for hist_article in recent_articles:
                    hist_title = hist_article.get('title', '')
                    title_similarity = self._calculate_title_similarity(article_title, hist_title)
                    
                    if title_similarity >= self.fuzzy_title_threshold:
                        is_duplicate = True
                        detection_method = 'title_fuzzy'
                        similarity_score = title_similarity
                        duplicate_stats['fuzzy_duplicates'] += 1
                        break
            
            # Method 4: Content similarity detection
            if not is_duplicate:
                # Check content similarity against recent articles
                recent_articles = historical_articles[-50:] if len(historical_articles) > 50 else historical_articles
                
                for hist_article in recent_articles:
                    content_similarity = self._calculate_content_similarity(article, hist_article)
                    
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
                
                # Add to history
                historical_articles.append({
                    'title': article_title,
                    'url': article_url,
                    'published': article.get('published', ''),
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
            
            else:
                duplicate_stats['duplicates_found'] += 1
                duplicate_stats['detection_methods'].append({
                    'method': detection_method,
                    'similarity': similarity_score,
                    'title': article_title[:50] + '...' if len(article_title) > 50 else article_title
                })
        
        # Update and save history
        history.update({
            'articles': historical_articles[-1000:],  # Keep last 1000 articles
            'url_hashes': url_hashes,
            'title_hashes': title_hashes,
            'total_articles_seen': history.get('total_articles_seen', 0) + len(new_articles)
        })
        
        self._save_feed_history(source_name, history)
        
        # Print detailed results
        print(f"  📊 Advanced duplicate detection results:")
        print(f"    🔍 Articles checked: {duplicate_stats['total_checked']}")
        print(f"    🔄 Duplicates found: {duplicate_stats['duplicates_found']}")
        print(f"    🔗 URL duplicates: {duplicate_stats['url_duplicates']}")
        print(f"    📝 Title duplicates: {duplicate_stats['title_duplicates']}")
        print(f"    🧠 Fuzzy duplicates: {duplicate_stats['fuzzy_duplicates']}")
        print(f"    📄 Content duplicates: {duplicate_stats['content_duplicates']}")
        print(f"    🆕 New unique articles: {duplicate_stats['new_articles']}")
        print(f"    📚 Historical articles: {len(historical_articles)}")
        
        return new_unique_articles, duplicate_stats
    
    def get_feed_statistics(self, source_name: str) -> Dict:
        """Get statistics for a specific RSS feed"""
        history = self._load_feed_history(source_name)
        
        return {
            'source': source_name,
            'total_articles_seen': history.get('total_articles_seen', 0),
            'historical_articles_stored': len(history.get('articles', [])),
            'url_hashes_count': len(history.get('url_hashes', [])),
            'title_hashes_count': len(history.get('title_hashes', [])),
            'last_updated': history.get('last_updated'),
            'history_file_exists': os.path.exists(self._get_feed_history_file(source_name))
        }
    
    def cleanup_old_history(self, days_to_keep: int = 30):
        """Clean up old historical data to prevent files from growing too large"""
        print(f"🧹 Cleaning up RSS history older than {days_to_keep} days...")
        
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        for filename in os.listdir(self.history_dir):
            if filename.endswith('_history.json'):
                filepath = os.path.join(self.history_dir, filename)
                source_name = filename.replace('_history.json', '').replace('_', ' ').title()
                
                try:
                    history = self._load_feed_history(source_name)
                    original_count = len(history.get('articles', []))
                    
                    # Filter articles newer than cutoff date
                    filtered_articles = []
                    for article in history.get('articles', []):
                        added_date_str = article.get('added_date')
                        if added_date_str:
                            try:
                                added_date = datetime.datetime.fromisoformat(added_date_str.replace('Z', '+00:00'))
                                if added_date > cutoff_date:
                                    filtered_articles.append(article)
                            except:
                                # Keep articles with invalid dates
                                filtered_articles.append(article)
                        else:
                            # Keep articles without dates
                            filtered_articles.append(article)
                    
                    if len(filtered_articles) < original_count:
                        history['articles'] = filtered_articles
                        self._save_feed_history(source_name, history)
                        print(f"  🗑️  {source_name}: Removed {original_count - len(filtered_articles)} old articles")
                
                except Exception as e:
                    print(f"⚠️  Error cleaning {source_name}: {e}")
        
        print("✅ History cleanup completed")

def main():
    """Test the RSS History Manager"""
    manager = RSSHistoryManager()
    
    # Test with sample articles
    test_articles = [
        {
            'title': 'Test Article 1 - Breaking News',
            'link': 'https://example.com/news/article-1',
            'description': 'This is a test article about breaking news that happened today.',
            'published': '2024-01-01T10:00:00Z'
        },
        {
            'title': 'Test Article 2 - Technology Update',
            'link': 'https://example.com/tech/article-2',
            'description': 'This is a test article about the latest technology updates.',
            'published': '2024-01-01T11:00:00Z'
        }
    ]
    
    print("🧪 Testing RSS History Manager...")
    
    # First run - should be all new
    new_articles, stats = manager.check_duplicates_advanced(test_articles, "Test Source")
    print(f"First run: {len(new_articles)} new articles")
    
    # Second run - should detect duplicates
    new_articles, stats = manager.check_duplicates_advanced(test_articles, "Test Source")
    print(f"Second run: {len(new_articles)} new articles")
    
    # Show statistics
    feed_stats = manager.get_feed_statistics("Test Source")
    print(f"Feed statistics: {feed_stats}")

if __name__ == "__main__":
    main()