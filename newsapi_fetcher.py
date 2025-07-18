#!/usr/bin/env python3
"""
NewsAPI Fetcher
Fetches news articles from NewsAPI with comprehensive source coverage
API Documentation: https://newsapi.org/docs
"""
import json
import datetime
import requests
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import re
from collections import Counter

# Load environment variables
load_dotenv()

class NewsAPIFetcher:
    def __init__(self, api_key=None):
        # Support for multiple API keys with smart rotation
        self.primary_key = api_key or os.getenv('NEWSAPI_KEY_PRIMARY') or os.getenv('NEWSAPI_KEY')
        self.secondary_key = os.getenv('NEWSAPI_KEY_SECONDARY')
        self.tertiary_key = os.getenv('NEWSAPI_KEY_TERTIARY')
        
        if not self.primary_key:
            print("❌ Error: No NewsAPI key found!")
            print("Please set NEWSAPI_KEY_PRIMARY in your .env file")
            print("Current environment variables:")
            print(f"  NEWSAPI_KEY_PRIMARY: {'✅ Set' if os.getenv('NEWSAPI_KEY_PRIMARY') else '❌ Not found'}")
            print(f"  NEWSAPI_KEY: {'✅ Set' if os.getenv('NEWSAPI_KEY') else '❌ Not found'}")
            exit(1)
        
        # Set up key rotation system
        self.available_keys = [self.primary_key]
        if self.secondary_key:
            self.available_keys.append(self.secondary_key)
        if self.tertiary_key:
            self.available_keys.append(self.tertiary_key)
        
        self.current_key_index = 0
        self.current_key = self.available_keys[0]
        self.base_url = "https://newsapi.org/v2"
        self.session = requests.Session()
        self._update_session_headers()
        
        # Track API usage for better management
        self.requests_made = {'primary': 0, 'secondary': 0, 'tertiary': 0}
        self.exhausted_keys = set()
        
        key_count = len(self.available_keys)
        total_requests = key_count * 100
        print(f"🔑 NewsAPI initialized with {key_count} API keys ({total_requests} requests/day total)")
        
        # NewsAPI source mappings to match your RSS categories
        self.source_categories = {
            'international': [
                'bbc-news', 'cnn', 'reuters', 'associated-press', 'the-guardian-uk',
                'al-jazeera-english', 'independent', 'the-times-of-india'
            ],
            'us_news': [
                'abc-news', 'cbs-news', 'nbc-news', 'fox-news', 'usa-today',
                'the-washington-post', 'the-new-york-times', 'npr'
            ],
            'technology': [
                'techcrunch', 'the-verge', 'wired', 'ars-technica', 'engadget',
                'techradar', 'the-next-web', 'hacker-news'
            ],
            'business': [
                'bloomberg', 'the-wall-street-journal', 'financial-times', 'fortune',
                'business-insider', 'cnbc', 'marketwatch', 'forbes'
            ],
            'sports': [
                'espn', 'bbc-sport', 'fox-sports', 'the-sport-bible',
                'nfl-news', 'nba-news', 'mlb-news'
            ],
            'indian_news': [
                'the-times-of-india', 'the-hindu', 'google-news-in'
            ],
            'geopolitics': [
                'bbc-news', 'cnn', 'reuters', 'associated-press', 'the-guardian-uk',
                'al-jazeera-english', 'the-washington-post', 'the-new-york-times',
                'financial-times', 'the-economist'
            ]
        }
    
    def _update_session_headers(self):
        """Update session headers with current API key"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'X-API-Key': self.current_key
        })
    
    def _switch_api_key(self):
        """Switch to next available API key"""
        # Mark current key as exhausted
        self.exhausted_keys.add(self.current_key_index)
        
        # Find next available key
        for i in range(len(self.available_keys)):
            if i not in self.exhausted_keys:
                self.current_key_index = i
                self.current_key = self.available_keys[i]
                self._update_session_headers()
                
                key_names = ['primary', 'secondary', 'tertiary']
                key_name = key_names[i] if i < len(key_names) else f'key_{i+1}'
                print(f"🔄 Switching to {key_name} API key due to rate limit...")
                return True
        
        print("❌ All API keys exhausted!")
        return False
    
    def _handle_rate_limit(self, response):
        """Handle rate limit errors by switching API keys"""
        if response.status_code == 429:
            print("⚠️  Rate limit hit on current API key")
            if self._switch_api_key():
                print("✅ Switched to backup API key, retrying...")
                return True
            else:
                print("❌ No more backup API keys available")
                return False
        return False
    
    def _track_request(self):
        """Track API requests for monitoring"""
        key_names = ['primary', 'secondary', 'tertiary']
        if self.current_key_index < len(key_names):
            key_name = key_names[self.current_key_index]
            self.requests_made[key_name] += 1
        
        # Indian states for targeted news search
        self.indian_states = [
            'Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Gujarat', 
            'Rajasthan', 'West Bengal', 'Uttar Pradesh', 'Andhra Pradesh',
            'Telangana', 'Kerala', 'Punjab', 'Haryana', 'Madhya Pradesh',
            'Bihar', 'Odisha', 'Jharkhand', 'Assam', 'Chhattisgarh',
            'Himachal Pradesh', 'Uttarakhand', 'Goa', 'Tripura', 'Meghalaya',
            'Manipur', 'Nagaland', 'Mizoram', 'Arunachal Pradesh', 'Sikkim',
            'Jammu and Kashmir', 'Ladakh'
        ]
        
        # Major Indian cities for more targeted news
        self.indian_cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata',
            'Pune', 'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Kanpur',
            'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri',
            'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik'
        ]
        
        # Geopolitical keywords and topics
        self.geopolitical_keywords = [
            'diplomacy', 'sanctions', 'trade war', 'military alliance', 'NATO',
            'UN Security Council', 'G7', 'G20', 'BRICS', 'territorial dispute',
            'cyber warfare', 'nuclear weapons', 'arms deal', 'peace treaty',
            'international relations', 'foreign policy', 'summit meeting',
            'border conflict', 'refugee crisis', 'humanitarian aid'
        ]
        
        # Key geopolitical regions and conflicts
        self.geopolitical_regions = [
            'Ukraine Russia', 'China Taiwan', 'Middle East', 'South China Sea',
            'North Korea', 'Iran nuclear', 'Afghanistan', 'Syria conflict',
            'Israel Palestine', 'Kashmir dispute', 'Brexit', 'EU relations',
            'US China relations', 'India Pakistan', 'Turkey Greece'
        ]

    def extract_image_from_article(self, article_url, timeout=10):
        """Extract better image from article content if needed"""
        try:
            response = self.session.get(article_url, timeout=timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try multiple methods to find high-quality images
                image_selectors = [
                    ('meta', {'property': 'og:image'}),
                    ('meta', {'name': 'twitter:image:src'}),
                    ('meta', {'name': 'twitter:image'}),
                    ('meta', {'property': 'twitter:image'}),
                    ('img', {'class': lambda x: x and any(term in x.lower() for term in ['hero', 'featured', 'main', 'article', 'lead'])})
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
                            
                            # Validate and prefer high-quality images
                            if image_url.startswith('http') and not any(skip in image_url.lower() for skip in ['logo', 'icon', 'avatar']):
                                return image_url
                            
        except Exception as e:
            print(f"Error extracting enhanced image from {article_url}: {e}")
        
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

    def fetch_top_headlines(self, category=None, sources=None, country='us', page_size=100):
        """Fetch top headlines from NewsAPI with fallback support"""
        url = f"{self.base_url}/top-headlines"
        params = {
            'apiKey': self.current_key,
            'pageSize': page_size,
            'language': 'en'
        }
        
        if category:
            params['category'] = category
        if sources:
            params['sources'] = ','.join(sources)
        if country and not sources:  # Can't use both country and sources
            params['country'] = country
            
        try:
            self._track_request()
            response = self.session.get(url, params=params)
            
            # Handle rate limiting with fallback
            if response.status_code == 429 and self._handle_rate_limit(response):
                # Retry with new key
                params['apiKey'] = self.current_key
                self._track_request()
                response = self.session.get(url, params=params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching headlines: {e}")
            return None

    def fetch_everything(self, query, sources=None, from_date=None, page_size=100):
        """Fetch articles using everything endpoint with fallback support"""
        url = f"{self.base_url}/everything"
        params = {
            'apiKey': self.current_key,
            'q': query,
            'pageSize': page_size,
            'language': 'en',
            'sortBy': 'publishedAt'
        }
        
        if sources:
            params['sources'] = ','.join(sources)
        if from_date:
            params['from'] = from_date
            
        try:
            self._track_request()
            response = self.session.get(url, params=params)
            
            # Handle rate limiting with fallback
            if response.status_code == 429 and self._handle_rate_limit(response):
                # Retry with new key
                params['apiKey'] = self.current_key
                self._track_request()
                response = self.session.get(url, params=params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching everything: {e}")
            return None

    def fetch_indian_state_news(self, max_states=10):
        """Fetch news specifically about Indian states and cities"""
        print("🇮🇳 Fetching Indian state-specific news...")
        
        indian_articles = []
        
        # Get yesterday's date for recent news
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Fetch news for major states (limit to avoid API quota)
        major_states = self.indian_states[:max_states]  # Top 10 states
        major_cities = self.indian_cities[:8]  # Top 8 cities
        
        # Search for state-specific news
        for state in major_states:
            try:
                query = f'"{state}" India news'
                print(f"  🔍 Searching for {state} news...")
                
                state_data = self.fetch_everything(
                    query=query,
                    from_date=yesterday,
                    page_size=5  # Limit per state to manage API quota
                )
                
                if state_data and 'articles' in state_data:
                    articles = self.process_articles(state_data, 'indian_states', f"{state} News")
                    for article in articles:
                        article['state'] = state
                        article['region'] = 'India'
                    indian_articles.extend(articles)
                    print(f"    ✅ {state}: {len(articles)} articles")
                else:
                    print(f"    ⚠️  {state}: No articles found")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ {state}: Error - {e}")
        
        # Search for city-specific news
        for city in major_cities:
            try:
                query = f'"{city}" India news'
                print(f"  🏙️  Searching for {city} news...")
                
                city_data = self.fetch_everything(
                    query=query,
                    from_date=yesterday,
                    page_size=3  # Limit per city
                )
                
                if city_data and 'articles' in city_data:
                    articles = self.process_articles(city_data, 'indian_cities', f"{city} News")
                    for article in articles:
                        article['city'] = city
                        article['region'] = 'India'
                    indian_articles.extend(articles)
                    print(f"    ✅ {city}: {len(articles)} articles")
                else:
                    print(f"    ⚠️  {city}: No articles found")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ {city}: Error - {e}")
        
        return indian_articles

    def fetch_geopolitics_news(self, max_topics=8):
        """Fetch geopolitics and international relations news"""
        print("🌍 Fetching Geopolitics & International Relations news...")
        
        geopolitics_articles = []
        
        # Get yesterday's date for recent news
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Fetch news for key geopolitical regions/conflicts
        selected_regions = self.geopolitical_regions[:max_topics]
        
        for region in selected_regions:
            try:
                query = f'"{region}" geopolitics OR diplomacy OR conflict'
                print(f"  🔍 Searching for {region} geopolitics...")
                
                region_data = self.fetch_everything(
                    query=query,
                    from_date=yesterday,
                    page_size=4  # Limit per region
                )
                
                if region_data and 'articles' in region_data:
                    articles = self.process_articles(region_data, 'geopolitics', f"{region} Geopolitics")
                    for article in articles:
                        article['geopolitical_region'] = region
                        article['topic_type'] = 'regional_conflict'
                    geopolitics_articles.extend(articles)
                    print(f"    ✅ {region}: {len(articles)} articles")
                else:
                    print(f"    ⚠️  {region}: No articles found")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ {region}: Error - {e}")
        
        # Fetch news for general geopolitical keywords
        selected_keywords = self.geopolitical_keywords[:6]  # Top 6 keywords
        
        for keyword in selected_keywords:
            try:
                query = f'"{keyword}" international OR global'
                print(f"  🔍 Searching for {keyword} news...")
                
                keyword_data = self.fetch_everything(
                    query=query,
                    from_date=yesterday,
                    page_size=3  # Limit per keyword
                )
                
                if keyword_data and 'articles' in keyword_data:
                    articles = self.process_articles(keyword_data, 'geopolitics', f"{keyword.title()} News")
                    for article in articles:
                        article['geopolitical_keyword'] = keyword
                        article['topic_type'] = 'thematic'
                    geopolitics_articles.extend(articles)
                    print(f"    ✅ {keyword}: {len(articles)} articles")
                else:
                    print(f"    ⚠️  {keyword}: No articles found")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"    ❌ {keyword}: Error - {e}")
        
        # Fetch from dedicated geopolitical sources
        print("  📰 Fetching from geopolitical sources...")
        geo_sources = ['bbc-news', 'reuters', 'al-jazeera-english', 'the-guardian-uk']
        available_geo_sources = [source for source in geo_sources if source in self.get_available_sources_list()]
        
        if available_geo_sources:
            try:
                geo_headlines = self.fetch_top_headlines(sources=available_geo_sources, page_size=15)
                if geo_headlines and 'articles' in geo_headlines:
                    # Filter for geopolitical content
                    geo_articles = []
                    for article in geo_headlines['articles']:
                        title_lower = (article.get('title') or '').lower()
                        desc_lower = (article.get('description') or '').lower()
                        
                        # Check if article contains geopolitical keywords
                        if any(keyword.lower() in title_lower or keyword.lower() in desc_lower 
                               for keyword in self.geopolitical_keywords + [region.split()[0] for region in self.geopolitical_regions]):
                            geo_articles.append(article)
                    
                    if geo_articles:
                        articles = self.process_articles({'articles': geo_articles}, 'geopolitics', 'Geopolitical Sources')
                        for article in articles:
                            article['topic_type'] = 'source_based'
                        geopolitics_articles.extend(articles)
                        print(f"    ✅ Geopolitical sources: {len(articles)} articles")
                        
            except Exception as e:
                print(f"    ❌ Geopolitical sources: Error - {e}")
        
        return geopolitics_articles

    def get_available_sources_list(self):
        """Helper method to get list of available source IDs"""
        sources_response = self.get_available_sources()
        if sources_response and 'sources' in sources_response:
            return [source['id'] for source in sources_response['sources']]
        return []

    def get_available_sources(self):
        """Get all available sources from NewsAPI with fallback support"""
        url = f"{self.base_url}/sources"
        params = {
            'apiKey': self.current_key,
            'language': 'en'
        }
        
        try:
            self._track_request()
            response = self.session.get(url, params=params)
            
            # Handle rate limiting with fallback
            if response.status_code == 429 and self._handle_rate_limit(response):
                # Retry with new key
                params['apiKey'] = self.current_key
                self._track_request()
                response = self.session.get(url, params=params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching sources: {e}")
            return None

    def process_articles(self, articles_data, category, source_name=None):
        """Process and enhance articles from NewsAPI response"""
        processed_articles = []
        
        if not articles_data or 'articles' not in articles_data:
            return processed_articles
            
        for article in articles_data['articles']:
            # Skip articles without essential data
            if not article.get('title') or not article.get('url'):
                continue
                
            processed_article = {
                'title': (article.get('title') or '').strip(),
                'link': article.get('url', ''),
                'published': article.get('publishedAt', ''),
                'summary': (article.get('description') or '').strip(),
                'description': (article.get('content') or '').strip(),
                'source': source_name or article.get('source', {}).get('name', 'Unknown'),
                'category': category,
                'api_source': 'newsapi',
                'image_url': article.get('urlToImage', '') or '',
                'has_image': bool(article.get('urlToImage')),
                'author': article.get('author', '') or '',
                'tags': [],
                'content_extracted': False
            }
            
            # Check if description is too short and extract full content if needed
            current_description = processed_article['description'] or processed_article['summary']
            MIN_DESCRIPTION_LENGTH = 100  # Minimum description length threshold
            
            if not current_description or len(current_description.strip()) < MIN_DESCRIPTION_LENGTH:
                print(f"    📄 Short description detected for '{processed_article['title'][:50]}...', extracting full content...")
                
                # Try regular extraction first
                extracted_content = self.extract_article_content(processed_article['link'])
                if extracted_content and len(extracted_content) > MIN_DESCRIPTION_LENGTH:
                    processed_article['description'] = extracted_content
                    processed_article['content_extracted'] = True
                    processed_article['extraction_method'] = 'requests'
                    print(f"    ✅ Enhanced description: {len(extracted_content)} characters (requests)")
                else:
                    # Fallback to Selenium for difficult sites
                    print(f"    🔄 Regular extraction failed, trying Selenium...")
                    selenium_content = self.extract_content_with_selenium(processed_article['link'])
                    if selenium_content and len(selenium_content) > MIN_DESCRIPTION_LENGTH:
                        processed_article['description'] = selenium_content
                        processed_article['content_extracted'] = True
                        processed_article['extraction_method'] = 'selenium'
                        print(f"    ✅ Enhanced description: {len(selenium_content)} characters (Selenium)")
                    else:
                        print(f"    ⚠️  Both extraction methods failed, keeping original")
            
            # Try to get better image if current one is low quality or missing
            if not processed_article['image_url'] or 'placeholder' in processed_article['image_url'].lower():
                enhanced_image = self.extract_image_from_article(processed_article['link'])
                if enhanced_image:
                    processed_article['image_url'] = enhanced_image
                    processed_article['has_image'] = True
            
            # Generate key points for articles with images
            if processed_article['has_image'] and processed_article.get('description'):
                print(f"    🔑 Generating key points for '{processed_article['title'][:50]}...'")
                key_points = self.extract_key_points(processed_article['title'], processed_article['description'])
                if key_points:
                    processed_article['key_points'] = key_points
                    processed_article['has_key_points'] = True
                    print(f"    ✅ Generated {len(key_points)} key points")
                else:
                    processed_article['key_points'] = []
                    processed_article['has_key_points'] = False
            else:
                processed_article['key_points'] = []
                processed_article['has_key_points'] = False
            
            processed_articles.append(processed_article)
            
        return processed_articles

    def fetch_all_news(self):
        """Fetch news from all categories using NewsAPI"""
        print("🚀 Starting NewsAPI news extraction...")
        print(f"🔑 Using API key: {self.current_key[:10]}...")
        
        news_data = {
            'extraction_timestamp': datetime.datetime.now().isoformat(),
            'total_articles': 0,
            'articles_with_images': 0,
            'image_success_rate': '0%',
            'sources_processed': 0,
            'api_source': 'newsapi.org',
            'categories': list(self.source_categories.keys()),
            'by_category': {},
            'by_source': {},
            'api_status': {}
        }
        
        # Initialize category data
        for category in self.source_categories.keys():
            news_data['by_category'][category] = []
        
        # Get available sources first
        print("📡 Fetching available sources...")
        sources_response = self.get_available_sources()
        available_sources = []
        if sources_response and 'sources' in sources_response:
            available_sources = [source['id'] for source in sources_response['sources']]
            print(f"✅ Found {len(available_sources)} available sources")
        
        # Strategic fetching with 300 requests - prioritize high-value content
        print(f"\n🎯 Strategic fetching with {len(self.available_keys)} API keys (300 requests total)")
        
        # Phase 1: Core Categories (High Priority) - 50 requests
        core_categories = ['international', 'us_news', 'technology', 'business']
        print(f"\n📊 PHASE 1: Core Categories (High Priority)")
        
        for category in core_categories:
            if category in self.source_categories:
                preferred_sources = self.source_categories[category]
                print(f"\n📂 Processing {category.replace('_', ' ').title()} category...")
                
                # Filter sources that are actually available
                valid_sources = [source for source in preferred_sources if source in available_sources]
                
                if valid_sources:
                    print(f"📰 Using sources: {', '.join(valid_sources[:4])}")  # Limit to top 4 sources
                    
                    # Fetch more articles for core categories
                    headlines_data = self.fetch_top_headlines(sources=valid_sources[:4], page_size=30)
                    
                    if headlines_data:
                        articles = self.process_articles(headlines_data, category)
                        news_data['by_category'][category].extend(articles)
                        
                        # Group by source
                        for article in articles:
                            source_name = article['source']
                            if source_name not in news_data['by_source']:
                                news_data['by_source'][source_name] = []
                            news_data['by_source'][source_name].append(article)
                        
                        news_data['api_status'][category] = {
                            'status': 'success',
                            'articles_count': len(articles),
                            'sources_used': valid_sources[:4]
                        }
                        
                        print(f"✅ {category}: {len(articles)} articles from {len(valid_sources[:4])} premium sources")
                    else:
                        print(f"❌ {category}: Failed to fetch data")
                
                time.sleep(0.3)  # Reduced delay for efficiency
        
        # Phase 2: Sports + Specialized Content - 30 requests
        print(f"\n📊 PHASE 2: Sports & Specialized Content")
        
        # Sports with targeted approach
        if 'sports' in self.source_categories:
            sports_sources = [source for source in self.source_categories['sports'] if source in available_sources]
            if sports_sources:
                print(f"🏈 Fetching sports from: {', '.join(sports_sources[:2])}")
                sports_data = self.fetch_top_headlines(sources=sports_sources[:2], page_size=25)
                if sports_data:
                    articles = self.process_articles(sports_data, 'sports')
                    news_data['by_category']['sports'].extend(articles)
                    print(f"✅ Sports: {len(articles)} articles")
        
        # Phase 3: Trending Topics & Breaking News - 40 requests
        print(f"\n📊 PHASE 3: Trending Topics & Breaking News")
        
        # Get trending topics with targeted searches
        trending_queries = [
            'breaking news',
            'AI artificial intelligence',
            'climate change',
            'cryptocurrency bitcoin',
            'space exploration',
            'health medical breakthrough'
        ]
        
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        for query in trending_queries[:6]:  # Limit to 6 trending topics
            print(f"🔥 Searching trending: {query}")
            trending_data = self.fetch_everything(
                query=query,
                from_date=yesterday,
                page_size=15
            )
            
            if trending_data and 'articles' in trending_data:
                articles = self.process_articles(trending_data, 'trending', f"Trending: {query.title()}")
                
                # Add to appropriate category or create trending category
                if 'trending' not in news_data['by_category']:
                    news_data['by_category']['trending'] = []
                    news_data['categories'].append('trending')
                
                news_data['by_category']['trending'].extend(articles)
                print(f"✅ {query}: {len(articles)} trending articles")
            
            time.sleep(0.2)
        
        # Phase 4: Regional Focus (Reduced) - 20 requests
        print(f"\n📊 PHASE 4: Strategic Regional Coverage")
        
        # Focus on major regions only
        major_regions = ['India', 'China', 'Europe', 'Middle East']
        for region in major_regions:
            print(f"🌍 Fetching {region} news...")
            regional_data = self.fetch_everything(
                query=f'"{region}" news',
                from_date=yesterday,
                page_size=12
            )
            
            if regional_data and 'articles' in regional_data:
                articles = self.process_articles(regional_data, 'regional', f"{region} News")
                
                if 'regional' not in news_data['by_category']:
                    news_data['by_category']['regional'] = []
                    news_data['categories'].append('regional')
                
                news_data['by_category']['regional'].extend(articles)
                print(f"✅ {region}: {len(articles)} articles")
            
            time.sleep(0.2)
        
        # Phase 5: Strategic Indian Coverage - 15 requests
        print(f"\n📊 PHASE 5: Strategic Indian Coverage")
        
        # Focus on major Indian topics only
        indian_topics = ['India economy', 'India politics', 'India technology']
        indian_articles = []
        
        for topic in indian_topics:
            print(f"🇮🇳 Fetching {topic}...")
            indian_data = self.fetch_everything(
                query=f'"{topic}" OR "Indian {topic.split()[1]}"',
                from_date=yesterday,
                page_size=10
            )
            
            if indian_data and 'articles' in indian_data:
                articles = self.process_articles(indian_data, 'indian_news', f"{topic.title()}")
                for article in articles:
                    article['indian_topic'] = topic
                    article['region'] = 'India'
                indian_articles.extend(articles)
                print(f"✅ {topic}: {len(articles)} articles")
            
            time.sleep(0.2)
        
        if indian_articles:
            news_data['by_category']['indian_news'] = indian_articles
            if 'indian_news' not in news_data['categories']:
                news_data['categories'].append('indian_news')
            
            # Group by source
            for article in indian_articles:
                source_name = article['source']
                if source_name not in news_data['by_source']:
                    news_data['by_source'][source_name] = []
                news_data['by_source'][source_name].append(article)
            
            news_data['api_status']['indian_news'] = {
                'status': 'success',
                'articles_count': len(indian_articles),
                'topics_covered': len(set(a.get('indian_topic') for a in indian_articles))
            }
        
        # Phase 6: Strategic Geopolitics - 10 requests
        print(f"\n📊 PHASE 6: Strategic Geopolitics")
        
        # Focus on current major geopolitical issues
        geopolitical_topics = ['Ukraine war', 'China Taiwan', 'Middle East conflict']
        geopolitics_articles = []
        
        for topic in geopolitical_topics:
            print(f"🌍 Fetching {topic}...")
            geo_data = self.fetch_everything(
                query=f'"{topic}" OR "{topic.replace(" ", "-")}"',
                from_date=yesterday,
                page_size=8
            )
            
            if geo_data and 'articles' in geo_data:
                articles = self.process_articles(geo_data, 'geopolitics', f"{topic.title()}")
                for article in articles:
                    article['geopolitical_topic'] = topic
                    article['topic_type'] = 'current_conflict'
                geopolitics_articles.extend(articles)
                print(f"✅ {topic}: {len(articles)} articles")
            
            time.sleep(0.2)
        
        if geopolitics_articles:
            news_data['by_category']['geopolitics'] = geopolitics_articles
            if 'geopolitics' not in news_data['categories']:
                news_data['categories'].append('geopolitics')
            
            # Group by source
            for article in geopolitics_articles:
                source_name = article['source']
                if source_name not in news_data['by_source']:
                    news_data['by_source'][source_name] = []
                news_data['by_source'][source_name].append(article)
            
            news_data['api_status']['geopolitics'] = {
                'status': 'success',
                'total_articles': len(geopolitics_articles),
                'topics_covered': len(set(a.get('geopolitical_topic') for a in geopolitics_articles))
            }
        
        # Summary of strategic approach
        total_estimated_requests = 4 + 1 + 6 + 4 + 3 + 3 + 1  # ~22 strategic requests
        print(f"\n📊 Strategic Summary: ~{total_estimated_requests} requests used efficiently")
        print(f"🎯 Remaining quota: ~{300 - total_estimated_requests} requests for future runs")
        
        # Calculate statistics
        all_articles = []
        for category, articles in news_data['by_category'].items():
            all_articles.extend(articles)
        
        news_data['total_articles'] = len(all_articles)
        news_data['articles_with_images'] = sum(1 for article in all_articles if article['has_image'])
        news_data['sources_processed'] = len(news_data['by_source'])
        
        if news_data['total_articles'] > 0:
            image_success_rate = (news_data['articles_with_images'] / news_data['total_articles']) * 100
            news_data['image_success_rate'] = f"{image_success_rate:.1f}%"
        
        # Add API usage tracking
        total_requests = sum(self.requests_made.values())
        key_names = ['primary', 'secondary', 'tertiary']
        current_key_name = key_names[self.current_key_index] if self.current_key_index < len(key_names) else f'key_{self.current_key_index+1}'
        
        news_data['api_usage'] = {
            'primary_key_requests': self.requests_made['primary'],
            'secondary_key_requests': self.requests_made['secondary'],
            'tertiary_key_requests': self.requests_made['tertiary'],
            'total_requests': total_requests,
            'available_keys': len(self.available_keys),
            'exhausted_keys': len(self.exhausted_keys),
            'current_key': current_key_name,
            'remaining_quota': (len(self.available_keys) - len(self.exhausted_keys)) * 100 - (
                self.requests_made[current_key_name] if current_key_name in self.requests_made else 0
            )
        }
        
        return news_data

    def save_to_json(self, news_data, filename='newsapi_data.json'):
        """Save news data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
        print(f"💾 NewsAPI data saved to {filename}")

def main():
    # Get API key from environment variable
    API_KEY = os.getenv('NEWSAPI_KEY')
    
    if not API_KEY:
        print("❌ Error: NewsAPI key not found!")
        print("Please set NEWSAPI_KEY in your .env file")
        print("Get your free API key from: https://newsapi.org/register")
        return None
    
    fetcher = NewsAPIFetcher(API_KEY)
    
    # Fetch news from NewsAPI
    news_data = fetcher.fetch_all_news()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 NEWSAPI EXTRACTION SUMMARY")
    print("="*60)
    print(f"📰 Total articles extracted: {news_data['total_articles']}")
    print(f"🖼️  Articles with images: {news_data['articles_with_images']} ({news_data['image_success_rate']})")
    print(f"✅ Sources processed: {news_data['sources_processed']}")
    print(f"📂 Categories: {', '.join(news_data['categories'])}")
    
    # Show API usage statistics
    api_usage = news_data.get('api_usage', {})
    print(f"\n🔑 API Usage Statistics:")
    print(f"  📊 Total requests made: {api_usage.get('total_requests', 0)}")
    print(f"  🔑 Primary key requests: {api_usage.get('primary_key_requests', 0)}")
    print(f"  🔄 Secondary key requests: {api_usage.get('secondary_key_requests', 0)}")
    print(f"  🔄 Tertiary key requests: {api_usage.get('tertiary_key_requests', 0)}")
    print(f"  🎯 Current active key: {api_usage.get('current_key', 'primary')}")
    print(f"  📈 Available keys: {api_usage.get('available_keys', 1)}")
    print(f"  ⚠️  Exhausted keys: {api_usage.get('exhausted_keys', 0)}")
    print(f"  🔋 Remaining quota: ~{api_usage.get('remaining_quota', 0)} requests")
    
    # Show key switching status
    if api_usage.get('exhausted_keys', 0) > 0:
        print(f"  🔄 Key rotation occurred due to rate limits")
    
    print("\n📊 By Category:")
    for category, articles in news_data['by_category'].items():
        print(f"  📁 {category.replace('_', ' ').title()}: {len(articles)} articles")
    
    print("\n🔍 API Status:")
    for category, status in news_data['api_status'].items():
        status_icon = "✅" if status['status'] == 'success' else "❌"
        if status['status'] == 'success':
            print(f"  {status_icon} {category}: {status['articles_count']} articles")
        else:
            print(f"  {status_icon} {category}: {status.get('error', 'Unknown error')}")
    
    # Save to JSON file
    fetcher.save_to_json(news_data)
    
    print(f"\n🎉 Complete! Your NewsAPI data is saved in 'newsapi_data.json'")
    if os.path.exists('newsapi_data.json'):
        print(f"📁 File size: {os.path.getsize('newsapi_data.json') / 1024:.1f} KB")
    
    return news_data

if __name__ == "__main__":
    main()