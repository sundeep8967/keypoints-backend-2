#!/usr/bin/env python3
"""
News Quality Scoring Module
Extracted from Playwright-based news summarization system
Calculates quality scores for news articles based on content, importance, and source trustworthiness
"""

import re
import hashlib
from typing import Dict, List, Optional


class NewsQualityScorer:
    """
    Calculates quality scores for news articles based on multiple factors:
    - Breaking/urgent news importance
    - Political/economic significance  
    - Social/cultural relevance
    - Regional importance (India/Bengaluru specific)
    - Content quality (title, summary, images, description)
    - Source trustworthiness
    """
    
    def __init__(self):
        # BREAKING/URGENT NEWS - Highest Priority (800-1000 points)
        self.breaking_keywords = [
            'breaking', 'urgent', 'alert', 'emergency', 'crisis', 'disaster',
            'war', 'attack', 'bomb', 'terror', 'earthquake', 'tsunami',
            'pandemic', 'outbreak', 'death', 'killed', 'died', 'accident',
            'fire', 'explosion', 'crash', 'rescue', 'evacuation'
        ]
        
        # MAJOR POLITICAL/ECONOMIC NEWS (600-800 points)
        self.major_political_keywords = [
            'election', 'prime minister', 'president', 'government', 'parliament',
            'budget', 'policy', 'law', 'court', 'supreme court', 'verdict',
            'resignation', 'appointed', 'cabinet', 'minister', 'opposition'
        ]
        
        # IMPORTANT SOCIAL/CULTURAL NEWS (400-600 points)
        self.important_social_keywords = [
            'protest', 'strike', 'rally', 'demonstration', 'movement',
            'festival', 'celebration', 'award', 'achievement', 'record',
            'innovation', 'breakthrough', 'discovery', 'launch', 'announcement'
        ]
        
        # REGIONAL IMPORTANCE - India/Bengaluru specific (200-400 points boost)
        self.regional_keywords = [
            'bengaluru', 'bangalore', 'karnataka', 'india', 'indian',
            'mumbai', 'delhi', 'chennai', 'hyderabad', 'pune', 'kolkata'
        ]
        
        # Trusted news sources
        self.trusted_sources = [
            'reuters', 'bbc', 'cnn', 'ap news', 'npr', 'bloomberg',
            'times of india', 'hindustan times', 'indian express', 
            'ndtv', 'news18', 'zee news', 'deccan herald', 'the hindu',
            'economic times', 'business standard', 'mint', 'livemint',
            'the guardian', 'washington post', 'new york times'
        ]
    
    def is_valid_news_title(self, title: str) -> bool:
        """Check if title is a valid news article title (not metadata/schedule)"""
        if not title or len(title.strip()) < 10:
            return False
        
        title_lower = title.lower().strip()
        
        # Reject broadcast schedule metadata
        schedule_patterns = [
            'at ', 'a.m.', 'p.m.', 'edt', 'est', 'pst', 'cst',
            'news at', 'in brief', 'breaking news at',
            'updates at', 'live at', 'tonight at'
        ]
        
        # Reject social media/generic references
        generic_patterns = [
            "'s posts", "news posts", "latest posts", "updates from",
            "follow us", "subscribe", "watch live", "tune in"
        ]
        
        # Reject if title is mostly schedule/metadata
        for pattern in schedule_patterns + generic_patterns:
            if pattern in title_lower:
                return False
        
        # Reject titles that are just source names + time
        if any(time_word in title_lower for time_word in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            if any(news_word in title_lower for news_word in ['news', 'update', 'brief']):
                return False
        
        return True

    def calculate_content_quality_score(self, title: str, summary: str, image_url: str, 
                                      description: str, source: str) -> float:
        """
        Calculate a quality score for the article content (0-1000).
        Prioritizes breaking news, important events, and high-impact stories.
        
        Args:
            title: Article title
            summary: Generated summary or article summary
            image_url: Image URL
            description: Article description
            source: News source
            
        Returns:
            Quality score between 0-1000
        """
        # First check if title is valid (not metadata/schedule)
        if not self.is_valid_news_title(title):
            return 0.0  # Reject invalid titles completely
        
        score = 0.0
        
        # Combine title, summary and description for importance analysis
        full_text = f"{title} {summary} {description}".lower()
        
        # Check for breaking/urgent news
        breaking_score = 0
        for keyword in self.breaking_keywords:
            if keyword in full_text:
                breaking_score = 900  # Very high priority
                break
        
        # Check for major political/economic news
        political_score = 0
        for keyword in self.major_political_keywords:
            if keyword in full_text:
                political_score = max(political_score, 700)
        
        # Check for important social/cultural news
        social_score = 0
        for keyword in self.important_social_keywords:
            if keyword in full_text:
                social_score = max(social_score, 500)
        
        # Regional importance boost
        regional_boost = 0
        for keyword in self.regional_keywords:
            if keyword in full_text:
                regional_boost = 200
                break
        
        # Base content quality (0-300 points)
        base_score = 0
        
        # Title quality (0-80 points)
        if title and len(title.strip()) > 10:
            title_words = len(title.split())
            if 5 <= title_words <= 15:  # Optimal title length
                base_score += 80
            elif title_words > 3:
                base_score += 60
            else:
                base_score += 20
        
        # Summary quality (0-120 points)
        if summary and summary != "No content available for summarization.":
            summary_words = len(summary.split())
            if 30 <= summary_words <= 80:  # Optimal summary length
                base_score += 120
            elif summary_words >= 15:
                base_score += 80
            else:
                base_score += 40
        
        # Image quality (0-60 points)
        if image_url and 'placeholder' not in image_url.lower():
            if any(domain in image_url for domain in ['cdn', 'static', 'images', 'img']):
                base_score += 60  # Likely a proper image CDN
            else:
                base_score += 40
        
        # Description availability (0-40 points)
        if description and len(description.strip()) > 20:
            base_score += 40
        elif description:
            base_score += 20
        
        # Source trustworthiness multiplier (1.0x to 1.5x)
        source_multiplier = 1.5 if self.is_trusted_source(source) else 1.0
        
        # Calculate final score
        importance_score = max(breaking_score, political_score, social_score)
        final_score = (importance_score + base_score + regional_boost) * source_multiplier
        
        return min(final_score, 1000.0)
    
    def is_trusted_source(self, source: str) -> bool:
        """Check if the source is from a trusted news organization."""
        if not source:
            return False
        
        source_lower = source.lower()
        return any(trusted in source_lower for trusted in self.trusted_sources)
    
    def calculate_image_quality_score(self, src: str, alt_text: str, width: str, 
                                    height: str, class_name: str) -> int:
        """Calculate quality score for an image based on multiple factors"""
        score = 0
        src_lower = src.lower()
        alt_lower = alt_text.lower()
        class_lower = class_name.lower()
        
        # Boost for news-related alt text
        news_keywords = ['news', 'article', 'story', 'report', 'photo', 'image']
        for keyword in news_keywords:
            if keyword in alt_lower:
                score += 20
                break
        
        # Boost for proper image hosting (CDN/static)
        if any(domain in src_lower for domain in ['cdn', 'static', 'images', 'img', 'media']):
            score += 30
        
        # Penalize common ad/placeholder patterns
        ad_patterns = ['ad', 'banner', 'sponsor', 'placeholder', 'logo', 'icon', 'avatar']
        for pattern in ad_patterns:
            if pattern in src_lower or pattern in class_lower:
                score -= 50
                break
        
        # Boost for reasonable dimensions
        try:
            w, h = int(width or 0), int(height or 0)
            if w >= 300 and h >= 200:  # Good size for news images
                score += 40
            elif w >= 200 and h >= 150:  # Acceptable size
                score += 20
            elif w < 100 or h < 100:  # Too small
                score -= 30
        except (ValueError, TypeError):
            pass
        
        # Boost for article-related class names
        article_classes = ['article', 'content', 'main', 'hero', 'featured']
        for cls in article_classes:
            if cls in class_lower:
                score += 15
                break
        
        return max(0, score)
    
    def is_valid_news_image(self, image_candidate: dict) -> bool:
        """Validate if an image is suitable for news articles"""
        src = image_candidate['src'].lower()
        alt = image_candidate['alt'].lower()
        width = image_candidate['width']
        height = image_candidate['height']
        
        # Reject obvious non-news images
        reject_patterns = [
            'logo', 'icon', 'avatar', 'profile', 'thumbnail',
            'ad', 'banner', 'sponsor', 'widget', 'button',
            'social', 'facebook', 'twitter', 'instagram',
            'placeholder', 'default', 'blank', 'spacer'
        ]
        
        for pattern in reject_patterns:
            if pattern in src or pattern in alt:
                return False
        
        # Require minimum dimensions
        if width and height:
            if width < 200 or height < 150:
                return False
        
        # Require reasonable aspect ratio (not too wide or tall)
        if width and height and width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio > 4 or aspect_ratio < 0.25:  # Too wide or too tall
                return False
        
        # Must have reasonable quality score
        if image_candidate['score'] < 10:
            return False
        
        return True
    
    def validate_summary_quality(self, summary: str, title: str) -> bool:
        """Validate if the generated summary meets quality standards"""
        if not summary or len(summary.strip()) < 20:
            return False
        
        # Check if summary contains key elements from title
        title_words = set(title.lower().split())
        summary_words = set(summary.lower().split())
        
        # At least 20% overlap with title words (excluding common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        title_meaningful = title_words - common_words
        summary_meaningful = summary_words - common_words
        
        if title_meaningful:
            overlap = len(title_meaningful.intersection(summary_meaningful))
            overlap_ratio = overlap / len(title_meaningful)
            if overlap_ratio < 0.2:  # Less than 20% overlap
                return False
        
        # Check for common boilerplate phrases
        boilerplate_phrases = [
            'click here', 'read more', 'subscribe', 'follow us',
            'terms of service', 'privacy policy', 'cookie policy'
        ]
        
        summary_lower = summary.lower()
        for phrase in boilerplate_phrases:
            if phrase in summary_lower:
                return False
        
        return True
    
    def generate_article_id(self, url: str, title: str, source: str) -> str:
        """Generate a unique ID for an article"""
        combined = f"{url}|{title}|{source}"
        hash_obj = hashlib.md5(combined.encode())
        return hash_obj.hexdigest()
    
    def add_quality_score_to_article(self, article: Dict) -> Dict:
        """
        Add quality_score to an existing article dictionary
        
        Args:
            article: Dictionary containing article data with keys like:
                    'title', 'summary', 'description', 'image_url', 'source'
        
        Returns:
            Updated article dictionary with 'quality_score' field
        """
        # Extract article fields with fallbacks
        title = article.get('title', '')
        summary = article.get('summary', '')
        description = article.get('description', '')
        image_url = article.get('image_url', '')
        source = article.get('source', '')
        
        # Calculate quality score
        quality_score = self.calculate_content_quality_score(
            title=title,
            summary=summary, 
            image_url=image_url,
            description=description,
            source=source
        )
        
        # Add quality score to article
        article['quality_score'] = round(quality_score, 1)
        
        return article
    
    def add_quality_scores_to_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Add quality scores to a list of articles
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            List of articles with quality_score field added
        """
        scored_articles = []
        
        for article in articles:
            scored_article = self.add_quality_score_to_article(article)
            scored_articles.append(scored_article)
        
        return scored_articles
    
    def sort_articles_by_quality(self, articles: List[Dict], reverse: bool = True) -> List[Dict]:
        """
        Sort articles by their quality score
        
        Args:
            articles: List of article dictionaries with quality_score field
            reverse: If True, sort in descending order (highest quality first)
            
        Returns:
            Sorted list of articles
        """
        return sorted(articles, key=lambda x: x.get('quality_score', 0), reverse=reverse)