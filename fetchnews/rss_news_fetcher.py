#!/usr/bin/env python3
"""
RSS News Fetcher
Fetches news articles from major RSS feeds with image extraction
"""
import json
import datetime
import requests
import feedparser
from urllib.parse import urlparse
import os
from bs4 import BeautifulSoup
import time
import concurrent.futures
from threading import Lock
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import re
from collections import Counter

class RSSNewsFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.lock = Lock()
        
        # RSS feeds organized by category - EXACTLY as you specified
        self.rss_feeds = {
            'international': {
                'BBC News': 'http://feeds.bbci.co.uk/news/rss.xml',
                'CNN': 'http://rss.cnn.com/rss/edition.rss',
                'Reuters': 'https://www.reuters.com/tools/rss',
                'AP News': 'https://apnews.com/apf-topnews',
                'The Guardian': 'https://www.theguardian.com/world/rss'
            },
            'us_news': {
                'NPR': 'https://feeds.npr.org/1001/rss.xml',
                'Fox News': 'https://moxie.foxnews.com/google-publisher/latest.xml',
                'CBS News': 'https://www.cbsnews.com/latest/rss/main',
                'ABC News': 'https://abcnews.go.com/abcnews/topstories'
            },
            'technology': {
                'TechCrunch': 'https://techcrunch.com/feed/',
                'The Verge': 'https://www.theverge.com/rss/index.xml',
                'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
                'Wired': 'https://www.wired.com/feed/rss',
                'NDTV Technology': 'http://feeds.feedburner.com/NDTV-Tech',
                'The Hindu Science': 'https://www.thehindu.com/sci-tech/science/service=rss',
                'Indian Express Tech': 'https://indianexpress.com/technology/feed/',
                'Zee Science & Tech': 'http://zeenews.india.com/rss/science-technology-news.xml'
            },
            'business': {
                'Financial Times': 'https://www.ft.com/rss/home',
                'Wall Street Journal': 'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
                'Bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
                'Forbes': 'https://www.forbes.com/real-time/feed2/',
                'Economic Times': 'https://economictimes.indiatimes.com/rssfeedsdefault.cms',
                'Business Standard': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
                'Livemint': 'http://www.livemint.com/rss/latestnews.xml',
                'Moneycontrol': 'http://www.moneycontrol.com/rss/latestnews.xml',
                'NDTV Profit': 'http://feeds.feedburner.com/NDTV-Business?format=xml',
                'Reuters India Business': 'http://feeds.reuters.com/reuters/INbusinessNews'
            },
            'sports': {
                'ESPN': 'https://www.espn.com/espn/rss/news',
                'BBC Sport': 'http://feeds.bbci.co.uk/sport/rss.xml',
                'Sky Sports': 'https://www.skysports.com/rss/12040',
                'NDTV Sports': 'http://feeds.feedburner.com/NDTV-Sports',
                'ESPNCricinfo': 'http://www.espncricinfo.com/rss/content/story/feeds/6.xml',
                'Times of India Sports': 'https://timesofindia.indiatimes.com/rssfeeds/4719148.cms',
                'Cricbuzz': 'http://live-feeds.cricbuzz.com/CricbuzzFeed'
            },
            'indian_news': {
                'NDTV': 'https://feeds.feedburner.com/ndtvnews-top-stories',
                'Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
                'The Hindu': 'https://www.thehindu.com/feeder/default.rss',
                'Indian Express': 'http://indianexpress.com/print/front-page/feed/',
                'India Today': 'https://www.indiatoday.in/rss/home',
                'BBC News India': 'http://feeds.bbci.co.uk/news/world/asia/india/rss.xml',
                'The Guardian India': 'https://www.theguardian.com/world/india/rss',
                'Scroll.in': 'http://feeds.feedburner.com/ScrollinArticles.rss',
                'Google News India': 'https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en'
            }
        }

    def extract_image_from_article(self, article_url, timeout=10):
        """Extract image URL from article content"""
        try:
            response = self.session.get(article_url, timeout=timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try multiple methods to find images
                image_selectors = [
                    ('meta', {'property': 'og:image'}),
                    ('meta', {'name': 'twitter:image'}),
                    ('meta', {'property': 'twitter:image'}),
                    ('meta', {'name': 'og:image'}),
                    ('img', {'class': lambda x: x and any(term in x.lower() for term in ['hero', 'featured', 'main', 'article'])})
                ]
                
                for tag, attrs in image_selectors:
                    element = soup.find(tag, attrs)
                    if element:
                        if tag == 'meta':
                            image_url = element.get('content')
                        else:
                            image_url = element.get('src') or element.get('data-src')
                        
                        if image_url:
                            # Make relative URLs absolute
                            if image_url.startswith('//'):
                                image_url = 'https:' + image_url
                            elif image_url.startswith('/'):
                                parsed_url = urlparse(article_url)
                                image_url = f"{parsed_url.scheme}://{parsed_url.netloc}{image_url}"
                            
                            # Validate image URL
                            if image_url.startswith('http') and any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                return image_url
                            
        except Exception as e:
            print(f"Error extracting image from {article_url}: {e}")
        
        return None

    def extract_article_content(self, article_url, timeout=15):
        """Extract full article content when description is too short"""
        try:
            response = self.session.get(article_url, timeout=timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                    element.decompose()
                
                # Try multiple content selectors (common article content containers)
                content_selectors = [
                    'article',
                    '[data-component="text-block"]',
                    '.article-content',
                    '.post-content', 
                    '.entry-content',
                    '.content',
                    '.story-body',
                    '.article-body',
                    '[data-module="ArticleBody"]',
                    '.gel-body-copy',
                    'main p',
                    '.main-content p'
                ]
                
                extracted_content = ""
                
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        # Get text from all matching elements
                        for element in elements:
                            # Get all paragraph text
                            paragraphs = element.find_all('p') if element.name != 'p' else [element]
                            for p in paragraphs:
                                text = p.get_text(strip=True)
                                if text and len(text) > 50:  # Only meaningful paragraphs
                                    extracted_content += text + " "
                                    
                        if len(extracted_content.strip()) > 200:  # If we got good content, break
                            break
                
                # Fallback: get all paragraphs from the page
                if len(extracted_content.strip()) < 200:
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 50:
                            extracted_content += text + " "
                            if len(extracted_content) > 500:  # Limit content length
                                break
                
                # Clean up the content
                if extracted_content:
                    # Remove extra whitespace and limit to first few sentences
                    content = ' '.join(extracted_content.split())
                    
                    # Split into sentences and take first 3-4 sentences
                    sentences = content.split('. ')
                    if len(sentences) > 4:
                        content = '. '.join(sentences[:4]) + '.'
                    
                    # Limit total length
                    if len(content) > 800:
                        content = content[:800] + '...'
                    
                    return content.strip()
                            
        except Exception as e:
            print(f"Error extracting content from {article_url}: {e}")
        
        return None

    def extract_content_with_selenium(self, article_url, timeout=20):
        """Extract content using Selenium for JavaScript-heavy sites"""
        driver = None
        try:
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Initialize driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(timeout)
            
            # Load the page
            driver.get(article_url)
            
            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try multiple content selectors
            content_selectors = [
                'article',
                '[data-component="text-block"]',
                '.article-content',
                '.post-content', 
                '.entry-content',
                '.content',
                '.story-body',
                '.article-body',
                '[data-module="ArticleBody"]',
                '.gel-body-copy',
                'main',
                '.main-content'
            ]
            
            extracted_content = ""
            
            for selector in content_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        for element in elements:
                            # Get all paragraph elements within this container
                            paragraphs = element.find_elements(By.TAG_NAME, "p")
                            for p in paragraphs:
                                text = p.text.strip()
                                if text and len(text) > 50:  # Only meaningful paragraphs
                                    extracted_content += text + " "
                        
                        if len(extracted_content.strip()) > 200:  # If we got good content, break
                            break
                except:
                    continue
            
            # Fallback: get all paragraphs from the page
            if len(extracted_content.strip()) < 200:
                try:
                    paragraphs = driver.find_elements(By.TAG_NAME, "p")
                    for p in paragraphs:
                        text = p.text.strip()
                        if text and len(text) > 50:
                            extracted_content += text + " "
                            if len(extracted_content) > 800:  # Limit content length
                                break
                except:
                    pass
            
            # Clean up the content
            if extracted_content:
                # Remove extra whitespace and limit to first few sentences
                content = ' '.join(extracted_content.split())
                
                # Split into sentences and take first 4-5 sentences
                sentences = content.split('. ')
                if len(sentences) > 5:
                    content = '. '.join(sentences[:5]) + '.'
                
                # Limit total length
                if len(content) > 1000:
                    content = content[:1000] + '...'
                
                return content.strip()
                        
        except Exception as e:
            print(f"Selenium extraction error for {article_url}: {e}")
        finally:
            if driver:
                driver.quit()
        
        return None

    def extract_key_points(self, title, description, max_points=5):
        """Extract key points from article title and description"""
        if not description or len(description.strip()) < 100:
            return []
        
        try:
            # Combine title and description for analysis
            full_text = f"{title}. {description}"
            
            # Clean and normalize text
            text = re.sub(r'[^\w\s\.\,\;\:\!\?\-]', '', full_text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Split into sentences
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            
            if len(sentences) < 2:
                return []
            
            # Score sentences based on various factors
            sentence_scores = {}
            
            # Extract important keywords (nouns, proper nouns, numbers)
            important_words = set()
            for sentence in sentences:
                words = sentence.lower().split()
                for word in words:
                    # Add numbers, capitalized words, and longer words
                    if (word.isdigit() or 
                        any(char.isupper() for char in word) or 
                        len(word) > 6):
                        important_words.add(word.lower())
            
            # Score each sentence
            for i, sentence in enumerate(sentences):
                score = 0
                words = sentence.lower().split()
                
                # Position bonus (first and last sentences often important)
                if i == 0:
                    score += 2
                elif i == len(sentences) - 1:
                    score += 1
                
                # Length bonus (not too short, not too long)
                if 30 <= len(sentence) <= 150:
                    score += 2
                elif 20 <= len(sentence) <= 200:
                    score += 1
                
                # Important words bonus
                for word in words:
                    if word in important_words:
                        score += 1
                
                # Keywords that indicate importance
                important_indicators = [
                    'announced', 'revealed', 'confirmed', 'reported', 'said',
                    'according', 'new', 'first', 'major', 'significant',
                    'breaking', 'latest', 'update', 'million', 'billion',
                    'percent', '%', 'year', 'month', 'week', 'today'
                ]
                
                for indicator in important_indicators:
                    if indicator in sentence.lower():
                        score += 1
                
                # Numbers and dates bonus
                if re.search(r'\d+', sentence):
                    score += 1
                
                sentence_scores[sentence] = score
            
            # Sort sentences by score and select top ones
            sorted_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Select key points (avoid duplicates and maintain order)
            key_points = []
            used_words = set()
            
            for sentence, score in sorted_sentences:
                if len(key_points) >= max_points:
                    break
                
                # Check for significant overlap with existing points
                sentence_words = set(sentence.lower().split())
                overlap = len(sentence_words.intersection(used_words))
                
                # Add if not too similar to existing points
                if overlap < len(sentence_words) * 0.6:  # Less than 60% overlap
                    # Clean up the sentence
                    clean_sentence = sentence.strip()
                    if not clean_sentence.endswith('.'):
                        clean_sentence += '.'
                    
                    key_points.append(clean_sentence)
                    used_words.update(sentence_words)
            
            # Ensure we have at least 2 points if possible
            if len(key_points) < 2 and len(sentences) >= 2:
                # Add first and last sentence if not already included
                first_sentence = sentences[0].strip()
                last_sentence = sentences[-1].strip()
                
                if first_sentence not in [kp.rstrip('.') for kp in key_points]:
                    if not first_sentence.endswith('.'):
                        first_sentence += '.'
                    key_points.insert(0, first_sentence)
                
                if (len(key_points) < max_points and 
                    last_sentence not in [kp.rstrip('.') for kp in key_points] and
                    len(sentences) > 1):
                    if not last_sentence.endswith('.'):
                        last_sentence += '.'
                    key_points.append(last_sentence)
            
            return key_points[:max_points]
            
        except Exception as e:
            print(f"Error extracting key points: {e}")
            return []

    def extract_image_from_feed_entry(self, entry):
        """Extract image from RSS feed entry itself"""
        # Check for media content in feed
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('type', '').startswith('image/'):
                    return media.get('url')
        
        # Check for enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    return enclosure.get('href')
        
        # Check for media thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        
        # Check summary/description for images
        content = entry.get('summary', '') or entry.get('description', '')
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            img = soup.find('img')
            if img:
                return img.get('src')
        
        return None

    def process_feed(self, source_name, feed_url, category):
        """Process a single RSS feed"""
        articles = []
        try:
            print(f"Fetching {source_name} ({category})...")
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo and feed.bozo_exception:
                print(f"Warning: Feed parsing issue for {source_name}: {feed.bozo_exception}")
            
            for entry in feed.entries[:20]:  # Limit to 20 articles per source
                # Extract basic article info
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', '').strip(),
                    'description': entry.get('description', '').strip(),
                    'source': source_name,
                    'category': category,
                    'rss_url': feed_url,
                    'image_url': '',
                    'has_image': False,
                    'author': entry.get('author', ''),
                    'tags': [tag.term for tag in entry.get('tags', [])],
                    'content_extracted': False
                }
                
                # Skip articles without title or link
                if not article['title'] or not article['link']:
                    continue
                
                # Check if description is too short and extract full content if needed
                current_description = article['description'] or article['summary']
                MIN_DESCRIPTION_LENGTH = 100  # Minimum description length threshold
                
                if not current_description or len(current_description.strip()) < MIN_DESCRIPTION_LENGTH:
                    print(f"    📄 Short description detected for '{article['title'][:50]}...', extracting full content...")
                    
                    # Try regular extraction first
                    extracted_content = self.extract_article_content(article['link'])
                    if extracted_content and len(extracted_content) > MIN_DESCRIPTION_LENGTH:
                        article['description'] = extracted_content
                        article['content_extracted'] = True
                        article['extraction_method'] = 'requests'
                        print(f"    ✅ Enhanced description: {len(extracted_content)} characters (requests)")
                    else:
                        # Fallback to Selenium for difficult sites
                        print(f"    🔄 Regular extraction failed, trying Selenium...")
                        selenium_content = self.extract_content_with_selenium(article['link'])
                        if selenium_content and len(selenium_content) > MIN_DESCRIPTION_LENGTH:
                            article['description'] = selenium_content
                            article['content_extracted'] = True
                            article['extraction_method'] = 'selenium'
                            print(f"    ✅ Enhanced description: {len(selenium_content)} characters (Selenium)")
                        else:
                            print(f"    ⚠️  Both extraction methods failed, keeping original")
                
                # Try to extract image from feed entry first
                image_url = self.extract_image_from_feed_entry(entry)
                
                # If no image in feed, try to extract from article page
                if not image_url and article['link']:
                    image_url = self.extract_image_from_article(article['link'])
                
                if image_url:
                    article['image_url'] = image_url
                    article['has_image'] = True
                
                # Generate key points for articles with images
                if article['has_image'] and article.get('description'):
                    print(f"    🔑 Generating key points for '{article['title'][:50]}...'")
                    key_points = self.extract_key_points(article['title'], article['description'])
                    if key_points:
                        article['key_points'] = key_points
                        article['has_key_points'] = True
                        print(f"    ✅ Generated {len(key_points)} key points")
                    else:
                        article['key_points'] = []
                        article['has_key_points'] = False
                else:
                    article['key_points'] = []
                    article['has_key_points'] = False
                
                articles.append(article)
                
        except Exception as e:
            print(f"Error processing feed {source_name}: {e}")
        
        return articles

    def fetch_all_news(self, max_workers=5):
        """Fetch news from all RSS feeds"""
        print("🚀 Starting RSS news extraction...")
        print(f"📡 Processing {sum(len(feeds) for feeds in self.rss_feeds.values())} RSS feeds...")
        
        news_data = {
            'extraction_timestamp': datetime.datetime.now().isoformat(),
            'total_articles': 0,
            'articles_with_images': 0,
            'image_success_rate': '0%',
            'sources_processed': 0,
            'categories': list(self.rss_feeds.keys()),
            'by_category': {},
            'by_source': {},
            'feed_status': {}
        }
        
        # Initialize category data
        for category in self.rss_feeds.keys():
            news_data['by_category'][category] = []
        
        all_tasks = []
        
        # Prepare all feed processing tasks
        for category, feeds in self.rss_feeds.items():
            for source_name, feed_url in feeds.items():
                all_tasks.append((source_name, feed_url, category))
        
        # Process feeds concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.process_feed, source_name, feed_url, category): (source_name, category)
                for source_name, feed_url, category in all_tasks
            }
            
            for future in concurrent.futures.as_completed(future_to_task):
                source_name, category = future_to_task[future]
                try:
                    articles = future.result()
                    
                    # Add articles to category
                    news_data['by_category'][category].extend(articles)
                    
                    # Add articles to source
                    news_data['by_source'][source_name] = articles
                    
                    # Track feed status
                    news_data['feed_status'][source_name] = {
                        'status': 'success',
                        'articles_count': len(articles),
                        'category': category
                    }
                    
                    print(f"✅ {source_name}: {len(articles)} articles")
                    
                except Exception as e:
                    print(f"❌ {source_name}: Failed - {e}")
                    news_data['feed_status'][source_name] = {
                        'status': 'failed',
                        'error': str(e),
                        'category': category
                    }
        
        # Calculate statistics
        all_articles = []
        for category, articles in news_data['by_category'].items():
            all_articles.extend(articles)
        
        news_data['total_articles'] = len(all_articles)
        news_data['articles_with_images'] = sum(1 for article in all_articles if article['has_image'])
        news_data['sources_processed'] = len([status for status in news_data['feed_status'].values() if status['status'] == 'success'])
        
        if news_data['total_articles'] > 0:
            image_success_rate = (news_data['articles_with_images'] / news_data['total_articles']) * 100
            news_data['image_success_rate'] = f"{image_success_rate:.1f}%"
        
        return news_data

    def save_to_json(self, news_data, filename='data/rss_news_data.json'):
        """Save news data to JSON file"""
        os.makedirs('data', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
        print(f"💾 News data saved to {filename}")

def main():
    fetcher = RSSNewsFetcher()
    
    # Fetch news from all RSS feeds
    news_data = fetcher.fetch_all_news()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 RSS NEWS EXTRACTION SUMMARY")
    print("="*60)
    print(f"📰 Total articles extracted: {news_data['total_articles']}")
    print(f"🖼️  Articles with images: {news_data['articles_with_images']} ({news_data['image_success_rate']})")
    print(f"✅ Sources processed successfully: {news_data['sources_processed']}")
    print(f"📂 Categories: {', '.join(news_data['categories'])}")
    
    print("\n📊 By Category:")
    for category, articles in news_data['by_category'].items():
        print(f"  📁 {category.replace('_', ' ').title()}: {len(articles)} articles")
    
    print("\n🔍 Feed Status:")
    for source, status in news_data['feed_status'].items():
        status_icon = "✅" if status['status'] == 'success' else "❌"
        if status['status'] == 'success':
            print(f"  {status_icon} {source}: {status['articles_count']} articles")
        else:
            print(f"  {status_icon} {source}: {status.get('error', 'Unknown error')}")
    
    # Save to JSON file
    fetcher.save_to_json(news_data)
    
    print(f"\n🎉 Complete! Your news data is saved in 'rss_news_data.json'")
    print(f"📁 File size: {os.path.getsize('rss_news_data.json') / 1024:.1f} KB")
    
    return news_data

if __name__ == "__main__":
    main()