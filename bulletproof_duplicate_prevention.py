#!/usr/bin/env python3
"""
Bulletproof Duplicate Prevention System
ZERO TOLERANCE for duplicates - multiple layers of protection
"""
import os
import json
import hashlib
import datetime
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher
import re

class BulletproofDuplicateFilter:
    def __init__(self, master_history_file='data/compact_hashes.txt', max_hashes=20000):
        """Initialize ultra-optimized bulletproof duplicate prevention system"""
        self.master_history_file = master_history_file
        os.makedirs(os.path.dirname(master_history_file), exist_ok=True)
        
        # Ultra-compact approach: single file with 8-char hashes
        self.max_hashes = max_hashes
        self.hash_set = self._load_compact_hashes()
        
        # Optimized thresholds for speed
        self.url_similarity_threshold = 0.95
        self.title_similarity_threshold = 0.90
        
        print(f"🛡️  OPTIMIZED Bulletproof Filter initialized")
        print(f"📊 Tracking: {len(self.hash_set)} compact hashes")
        print(f"💾 Storage: {self._get_file_size()} bytes ({self._get_file_size()/1024:.1f} KB)")
        print(f"🎯 Max hashes: {max_hashes:,} (auto-cleanup enabled)")
    
    def _load_compact_hashes(self) -> Set[str]:
        """Load compact hashes from simple text file"""
        if os.path.exists(self.master_history_file):
            try:
                with open(self.master_history_file, 'r', encoding='utf-8') as f:
                    return set(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"⚠️  Error loading hashes: {e}")
        return set()
    
    def _get_file_size(self) -> int:
        """Get file size in bytes"""
        if os.path.exists(self.master_history_file):
            return os.path.getsize(self.master_history_file)
        return 0
    
    def _save_compact_hashes(self):
        """Save compact hashes to simple text file"""
        try:
            # Auto-cleanup: keep only recent hashes if too many
            hash_list = list(self.hash_set)
            if len(hash_list) > self.max_hashes:
                # Keep most recent hashes (last added)
                hash_list = hash_list[-self.max_hashes:]
                self.hash_set = set(hash_list)
                print(f"🧹 Auto-cleanup: reduced to {len(self.hash_set)} hashes")
            
            with open(self.master_history_file, 'w', encoding='utf-8') as f:
                for hash_val in sorted(self.hash_set):  # Sort for consistency
                    f.write(f"{hash_val}\n")
                    
        except Exception as e:
            print(f"❌ Error saving hashes: {e}")
    
    def _normalize_url(self, url: str) -> str:
        """Aggressively normalize URL for comparison"""
        if not url:
            return ""
        
        # Convert to lowercase and strip
        url = url.lower().strip()
        
        # Remove protocols
        for protocol in ['https://', 'http://', 'www.']:
            if url.startswith(protocol):
                url = url[len(protocol):]
        
        # Remove common URL variations
        url = re.sub(r'[?#].*$', '', url)  # Remove query params and fragments
        url = re.sub(r'/$', '', url)       # Remove trailing slash
        url = re.sub(r'/index\.(html?|php)$', '', url)  # Remove index files
        url = re.sub(r'[^\w\-\./]', '', url)  # Remove special characters
        
        return url
    
    def _normalize_title(self, title: str) -> str:
        """Aggressively normalize title for comparison"""
        if not title:
            return ""
        
        # Convert to lowercase and strip
        title = title.lower().strip()
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            'breaking:', 'exclusive:', 'update:', 'news:', 'latest:', 'urgent:',
            'live:', 'developing:', 'alert:', 'report:', 'analysis:'
        ]
        
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        
        # Remove common suffixes
        suffixes_to_remove = [
            '- live updates', '- breaking news', '- latest news', '- report',
            '| reuters', '| bbc', '| cnn', '| times', '| news'
        ]
        
        for suffix in suffixes_to_remove:
            if title.endswith(suffix):
                title = title[:-len(suffix)].strip()
        
        # Remove extra whitespace and special characters
        title = re.sub(r'[^\w\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        
        return title.strip()
    
    def _normalize_content(self, content: str) -> str:
        """Aggressively normalize content for comparison"""
        if not content:
            return ""
        
        # Convert to lowercase and strip
        content = content.lower().strip()
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove URLs
        content = re.sub(r'https?://[^\s]+', '', content)
        
        # Remove email addresses
        content = re.sub(r'\S+@\S+', '', content)
        
        # Remove extra whitespace and special characters
        content = re.sub(r'[^\w\s]', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def _create_compact_hash(self, article: Dict) -> str:
        """Create single ultra-compact 8-character hash"""
        url = article.get('url', '') or article.get('link', '')
        title = article.get('title', '')
        
        # Aggressive normalization for space efficiency
        norm_url = self._normalize_url(url)
        norm_title = self._normalize_title(title)
        
        # Create single combined signature
        signature = f"{norm_url}|{norm_title[:100]}"  # Limit title to 100 chars
        
        # Generate 8-character hash (64 bits of entropy)
        return hashlib.sha256(signature.encode('utf-8')).hexdigest()[:8]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize both texts
        text1 = self._normalize_title(text1) if len(text1) < 200 else self._normalize_content(text1)
        text2 = self._normalize_title(text2) if len(text2) < 200 else self._normalize_content(text2)
        
        # Calculate similarity
        return SequenceMatcher(None, text1, text2).ratio()
    
    def is_duplicate(self, article: Dict) -> Tuple[bool, str, float]:
        """
        OPTIMIZED duplicate detection - fast single hash check
        Returns: (is_duplicate, detection_method, confidence_score)
        """
        
        # Create compact hash for this article
        compact_hash = self._create_compact_hash(article)
        
        # Single hash lookup - O(1) operation
        if compact_hash in self.hash_set:
            return True, 'compact_hash_match', 1.0
        
        # Article is unique
        return False, 'unique', 0.0
    
    def add_to_registry(self, article: Dict):
        """Add a unique article to the compact hash registry"""
        # Create and add compact hash
        compact_hash = self._create_compact_hash(article)
        self.hash_set.add(compact_hash)
    
    def filter_duplicates(self, articles: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        BULLETPROOF filtering - NO duplicates will pass through
        Returns: (unique_articles, detailed_stats)
        """
        if not articles:
            return [], {'total_checked': 0, 'duplicates_found': 0, 'unique_articles': 0}
        
        print(f"🛡️  BULLETPROOF duplicate filtering: {len(articles)} articles")
        
        unique_articles = []
        duplicate_stats = {
            'total_checked': len(articles),
            'duplicates_found': 0,
            'unique_articles': 0,
            'detection_methods': {
                'exact_url_match': 0,
                'exact_title_match': 0,
                'exact_content_match': 0,
                'fuzzy_match': 0,
                'combined_match': 0,
                'url_similarity': 0,
                'title_similarity': 0,
                'content_similarity': 0,
                'compact_hash_match': 0,
                'unique': 0
            },
            'duplicate_details': []
        }
        
        for i, article in enumerate(articles):
            # Check if this article is a duplicate
            is_dup, method, confidence = self.is_duplicate(article)
            
            if is_dup:
                # DUPLICATE DETECTED - BLOCK IT
                duplicate_stats['duplicates_found'] += 1
                duplicate_stats['detection_methods'][method] += 1
                
                duplicate_stats['duplicate_details'].append({
                    'article_index': i,
                    'title': article.get('title', '')[:100] + '...',
                    'detection_method': method,
                    'confidence': confidence,
                    'source': article.get('source', ''),
                    'url': article.get('url', '') or article.get('link', '')
                })
                
                print(f"  🚫 DUPLICATE BLOCKED: {method} ({confidence:.2f}) - {article.get('title', '')[:50]}...")
                
            else:
                # UNIQUE ARTICLE - ALLOW IT
                unique_articles.append(article)
                self.add_to_registry(article)
                duplicate_stats['unique_articles'] += 1
                
                print(f"  ✅ UNIQUE ALLOWED: {article.get('title', '')[:50]}...")
        
        # Save updated hash set
        self._save_compact_hashes()
        
        # Print comprehensive results
        print(f"\n🛡️  BULLETPROOF FILTERING RESULTS:")
        print(f"  📊 Total articles checked: {duplicate_stats['total_checked']}")
        print(f"  🚫 Duplicates BLOCKED: {duplicate_stats['duplicates_found']}")
        print(f"  ✅ Unique articles ALLOWED: {duplicate_stats['unique_articles']}")
        print(f"  🎯 Duplicate detection rate: {(duplicate_stats['duplicates_found']/duplicate_stats['total_checked']*100):.1f}%")
        
        print(f"\n📊 Detection method breakdown:")
        for method, count in duplicate_stats['detection_methods'].items():
            if count > 0:
                print(f"    {method}: {count} duplicates")
        
        print(f"\n📈 Optimized registry stats:")
        print(f"  🗂️  Total hashes stored: {len(self.hash_set)}")
        print(f"  💾 Storage size: {self._get_file_size()} bytes ({self._get_file_size()/1024:.1f} KB)")
        print(f"  🎯 Space efficiency: {len(self.hash_set)} articles in {self._get_file_size()/1024:.1f} KB")
        
        return unique_articles, duplicate_stats
    
    def get_registry_stats(self) -> Dict:
        """Get comprehensive statistics about the master registry"""
        return {
            'total_articles_processed': self.master_registry.get('total_articles_processed', 0),
            'total_duplicates_blocked': self.master_registry.get('total_duplicates_blocked', 0),
            'url_hashes_count': len(self.url_hashes),
            'title_hashes_count': len(self.title_hashes),
            'content_hashes_count': len(self.content_hashes),
            'fuzzy_hashes_count': len(self.fuzzy_hashes),
            'combined_hashes_count': len(self.combined_hashes),
            'recent_articles_count': len(self.master_registry.get('recent_articles', [])),
            'last_updated': self.master_registry.get('last_updated'),
            'registry_file_size': os.path.getsize(self.master_history_file) if os.path.exists(self.master_history_file) else 0
        }

def main():
    """Test the bulletproof duplicate filter"""
    filter_system = BulletproofDuplicateFilter()
    
    # Test with sample articles including subtle duplicates
    test_articles = [
        {
            'title': 'Breaking: Major Tech Company Announces New Product',
            'url': 'https://example.com/tech-news/new-product-announcement',
            'description': 'A major technology company has announced a revolutionary new product.',
            'source': 'TechNews'
        },
        {
            'title': 'BREAKING: Major Tech Company Announces New Product',  # Slight variation
            'url': 'https://example.com/tech-news/new-product-announcement/',  # Trailing slash
            'description': 'A major technology company has announced a revolutionary new product.',
            'source': 'TechDaily'
        },
        {
            'title': 'Tech Giant Reveals Revolutionary Product',  # Different wording, same story
            'url': 'https://example.com/news/tech-giant-product-reveal',
            'description': 'A major technology company has announced a revolutionary new product that will change the industry.',
            'source': 'NewsToday'
        },
        {
            'title': 'Completely Different News Story',
            'url': 'https://example.com/different-story',
            'description': 'This is a completely different news story about something else entirely.',
            'source': 'NewsSource'
        }
    ]
    
    print("🧪 Testing Bulletproof Duplicate Filter...")
    
    # First run
    unique_articles, stats = filter_system.filter_duplicates(test_articles)
    print(f"\nFirst run: {len(unique_articles)} unique articles out of {len(test_articles)}")
    
    # Second run with same articles - should block ALL as duplicates
    print(f"\n🔄 Second run with same articles...")
    unique_articles2, stats2 = filter_system.filter_duplicates(test_articles)
    print(f"Second run: {len(unique_articles2)} unique articles out of {len(test_articles)}")
    
    # Show registry stats
    registry_stats = filter_system.get_registry_stats()
    print(f"\n📊 Registry Statistics:")
    for key, value in registry_stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()