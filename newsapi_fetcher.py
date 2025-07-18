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

class NewsAPIFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'X-API-Key': self.api_key
        })
        
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

    def fetch_top_headlines(self, category=None, sources=None, country='us', page_size=100):
        """Fetch top headlines from NewsAPI"""
        url = f"{self.base_url}/top-headlines"
        params = {
            'apiKey': self.api_key,
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
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching headlines: {e}")
            return None

    def fetch_everything(self, query, sources=None, from_date=None, page_size=100):
        """Fetch articles using everything endpoint"""
        url = f"{self.base_url}/everything"
        params = {
            'apiKey': self.api_key,
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
        """Get all available sources from NewsAPI"""
        url = f"{self.base_url}/sources"
        params = {
            'apiKey': self.api_key,
            'language': 'en'
        }
        
        try:
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
                'tags': []
            }
            
            # Try to get better image if current one is low quality or missing
            if not processed_article['image_url'] or 'placeholder' in processed_article['image_url'].lower():
                enhanced_image = self.extract_image_from_article(processed_article['link'])
                if enhanced_image:
                    processed_article['image_url'] = enhanced_image
                    processed_article['has_image'] = True
            
            processed_articles.append(processed_article)
            
        return processed_articles

    def fetch_all_news(self):
        """Fetch news from all categories using NewsAPI"""
        print("🚀 Starting NewsAPI news extraction...")
        print(f"🔑 Using API key: {self.api_key[:10]}...")
        
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
        
        # Process each category
        for category, preferred_sources in self.source_categories.items():
            print(f"\n📂 Processing {category.replace('_', ' ').title()} category...")
            
            # Filter sources that are actually available
            valid_sources = [source for source in preferred_sources if source in available_sources]
            
            if valid_sources:
                print(f"📰 Using sources: {', '.join(valid_sources)}")
                
                # Fetch headlines from specific sources
                headlines_data = self.fetch_top_headlines(sources=valid_sources, page_size=20)
                
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
                        'sources_used': valid_sources
                    }
                    
                    print(f"✅ {category}: {len(articles)} articles from {len(valid_sources)} sources")
                else:
                    news_data['api_status'][category] = {
                        'status': 'failed',
                        'error': 'No data returned from API',
                        'sources_attempted': valid_sources
                    }
                    print(f"❌ {category}: Failed to fetch data")
            else:
                # Fallback: use category-based search
                print(f"⚠️  No valid sources found, trying category search...")
                category_map = {
                    'international': 'general',
                    'us_news': 'general',
                    'technology': 'technology',
                    'business': 'business',
                    'sports': 'sports'
                }
                
                if category in category_map:
                    headlines_data = self.fetch_top_headlines(category=category_map[category], page_size=20)
                    if headlines_data:
                        articles = self.process_articles(headlines_data, category)
                        news_data['by_category'][category].extend(articles)
                        print(f"✅ {category}: {len(articles)} articles via category search")
            
            # Small delay to respect API rate limits
            time.sleep(0.5)
        
        # Fetch Indian state-specific news
        print(f"\n🇮🇳 Processing Indian States & Cities...")
        indian_articles = self.fetch_indian_state_news(max_states=10)
        
        if indian_articles:
            # Separate by states and cities
            state_articles = [article for article in indian_articles if 'state' in article]
            city_articles = [article for article in indian_articles if 'city' in article]
            
            news_data['by_category']['indian_states'] = state_articles
            news_data['by_category']['indian_cities'] = city_articles
            
            # Add to categories list
            if state_articles:
                news_data['categories'].append('indian_states')
            if city_articles:
                news_data['categories'].append('indian_cities')
            
            # Group by source for Indian news
            for article in indian_articles:
                source_name = article['source']
                if source_name not in news_data['by_source']:
                    news_data['by_source'][source_name] = []
                news_data['by_source'][source_name].append(article)
            
            news_data['api_status']['indian_states'] = {
                'status': 'success',
                'articles_count': len(state_articles),
                'states_covered': len(set(article.get('state') for article in state_articles if 'state' in article))
            }
            
            news_data['api_status']['indian_cities'] = {
                'status': 'success', 
                'articles_count': len(city_articles),
                'cities_covered': len(set(article.get('city') for article in city_articles if 'city' in article))
            }
            
            print(f"✅ Indian States: {len(state_articles)} articles")
            print(f"✅ Indian Cities: {len(city_articles)} articles")
        
        # Fetch Geopolitics news
        print(f"\n🌍 Processing Geopolitics & International Relations...")
        geopolitics_articles = self.fetch_geopolitics_news(max_topics=8)
        
        if geopolitics_articles:
            news_data['by_category']['geopolitics'] = geopolitics_articles
            
            # Add to categories list
            if 'geopolitics' not in news_data['categories']:
                news_data['categories'].append('geopolitics')
            
            # Group by source for geopolitics news
            for article in geopolitics_articles:
                source_name = article['source']
                if source_name not in news_data['by_source']:
                    news_data['by_source'][source_name] = []
                news_data['by_source'][source_name].append(article)
            
            # Count different types of geopolitical coverage
            regional_articles = [a for a in geopolitics_articles if a.get('topic_type') == 'regional_conflict']
            thematic_articles = [a for a in geopolitics_articles if a.get('topic_type') == 'thematic']
            source_articles = [a for a in geopolitics_articles if a.get('topic_type') == 'source_based']
            
            news_data['api_status']['geopolitics'] = {
                'status': 'success',
                'total_articles': len(geopolitics_articles),
                'regional_conflicts': len(regional_articles),
                'thematic_coverage': len(thematic_articles),
                'source_based': len(source_articles),
                'regions_covered': len(set(a.get('geopolitical_region') for a in regional_articles if a.get('geopolitical_region'))),
                'keywords_covered': len(set(a.get('geopolitical_keyword') for a in thematic_articles if a.get('geopolitical_keyword')))
            }
            
            print(f"✅ Geopolitics: {len(geopolitics_articles)} articles")
            print(f"   📍 Regional conflicts: {len(regional_articles)} articles")
            print(f"   🏷️  Thematic coverage: {len(thematic_articles)} articles") 
            print(f"   📰 Source-based: {len(source_articles)} articles")
        
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
        
        return news_data

    def save_to_json(self, news_data, filename='newsapi_data.json'):
        """Save news data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
        print(f"💾 NewsAPI data saved to {filename}")

def main():
    # Your API key
    API_KEY = "945895608b4e41aeab5835c4538cf927"
    
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