# 📰 News Aggregator Platform - Technical Specification

## 🔧 System Overview

**News Aggregator Platform** is a high-performance news intelligence system that automatically collects, processes, and deduplicates news content from multiple sources using advanced ML algorithms and concurrent processing.

### **Technical Specifications:**
- **Language:** Python 3.11+
- **Architecture:** Async/concurrent processing
- **Performance:** 42.9% improvement over sequential processing
- **Processing Speed:** 2-3 minutes for full aggregation cycle
- **Deduplication:** ML-based similarity detection (85% title, 90% URL, 75% content)

---

## 🏗️ Core Technical Components

### **1. News Fetchers**
- **RSS News Fetcher:** `fetchnews/rss_news_fetcher.py` (sync) / `fetchnews/async_rss_fetcher.py` (async)
  - Handles 50+ RSS feeds across 7 categories
  - Playwright-based content extraction
  - Concurrent processing: 5 feeds, 3 articles simultaneously
  
- **NewsAPI Fetcher:** `fetchnews/newsapi_fetcher.py` (sync) / `fetchnews/async_newsapi_fetcher.py` (async)
  - Triple API key rotation system
  - Rate limiting and quota management
  - 70,000+ source coverage
  - Concurrent requests: 5 API calls, 3 extractions simultaneously

### **2. Aggregation Engine**
- **Main Controller:** `main.py`
  - Orchestrates both fetchers
  - Implements deduplication algorithms
  - Manages parallel/sequential execution modes
  - ML-based content similarity analysis

### **3. Database Layer**
- **Supabase Integration:** `db/supabase_integration.py`
  - Cloud-native PostgreSQL storage
  - Real-time data synchronization
  - Row-level security
  - Automatic schema management

### **4. Automation Layer**
- **GitHub Actions:** `.github/workflows/daily-news-aggregation.yml`
  - Automated daily execution (6 AM UTC)
  - Environment management
  - Artifact generation and reporting
  - Error handling and notifications

---

## 🔧 Technology Stack

### **Core Dependencies:**
```
Python 3.11+
playwright>=1.40.0          # Async web scraping (42.9% performance improvement)
beautifulsoup4>=4.11.1      # HTML parsing
requests>=2.28.1            # HTTP requests
feedparser>=6.0.8           # RSS feed parsing
supabase>=2.0.0             # Database integration
python-dotenv>=1.0.0        # Environment management
```

### **ML/NLP Stack:**
```
scikit-learn<1.3.0          # TF-IDF vectorization, cosine similarity
spacy>=3.4.0,<3.7.0        # Natural language processing
numpy<2.0.0                 # Numerical computations
```

### **Performance Optimizations:**
- **Async Processing:** 1.8x faster than sequential
- **Concurrent Limits:** Configurable semaphore-based rate limiting
- **Resource Blocking:** Ads, trackers, unnecessary assets filtered
- **Smart Caching:** Content caching with TTL management

---

## 📊 Data Flow Architecture

### **1. Data Ingestion Pipeline**
```
RSS Feeds (50+) → RSS Fetcher → Raw Articles
NewsAPI (70k+) → NewsAPI Fetcher → Raw Articles
```

### **2. Content Processing Pipeline**
```
Raw Articles → Content Enhancement → Image Extraction → Metadata Standardization
```

### **3. Deduplication Pipeline**
```
All Articles → URL Matching (90%) → Title Similarity (85%) → Content Similarity (75%) → Deduplicated Dataset
```

### **4. Storage Pipeline**
```
Deduplicated Articles → Supabase Database + JSON Files → API Endpoints
```

### **5. Analytics Pipeline**
```
Processed Data → Statistics Generation → Performance Reports → Metrics Dashboard
```

---

## ⚙️ Configuration Management

### **Environment Variables:**
```bash
# NewsAPI Configuration
NEWSAPI_KEY_PRIMARY=your_primary_key
NEWSAPI_KEY_SECONDARY=your_secondary_key  # Optional
NEWSAPI_KEY_TERTIARY=your_tertiary_key    # Optional

# Database Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Deduplication Thresholds
TITLE_SIMILARITY_THRESHOLD=0.85    # 85% title similarity
URL_SIMILARITY_THRESHOLD=0.90      # 90% URL similarity
CONTENT_SIMILARITY_THRESHOLD=0.75  # 75% content similarity

# Performance Tuning
MAX_CONCURRENT_FEEDS=5              # RSS feeds processed simultaneously
MAX_CONCURRENT_ARTICLES=3           # Articles processed per feed
MAX_CONCURRENT_REQUESTS=5           # NewsAPI requests simultaneously
PLAYWRIGHT_TIMEOUT=15000            # Browser timeout (ms)
```

### **Execution Modes:**
1. **Sequential Mode** - Stable, resource-efficient (recommended for CI/CD)
2. **Parallel Mode** - Fast, resource-intensive (recommended for local development)
3. **Async Mode** - Optimized, 42.9% faster (recommended for production)

---

## 📈 Performance Metrics & Benchmarks

### **Current Performance Benchmarks:**
- **Processing Speed:** 2-3 minutes for full aggregation (42.9% improvement)
- **Article Volume:** 500-1000 articles per run
- **Deduplication Rate:** 15-25% duplicate removal
- **Image Success Rate:** 60-80% articles with images
- **Source Coverage:** 50+ RSS feeds + 70,000+ NewsAPI sources
- **Concurrent Processing:** 1.8x faster than sequential approach

### **Resource Usage:**
- **Memory:** 512MB-1GB peak usage
- **Storage:** 1-5MB per aggregation run
- **Network:** 100-500 HTTP requests per run
- **CPU:** Moderate usage during ML processing

### **Optimization Results:**
```json
{
  "sequential_processing": {
    "execution_time": "20.04 seconds",
    "avg_time_per_url": "4.01 seconds"
  },
  "concurrent_processing": {
    "execution_time": "11.45 seconds", 
    "avg_time_per_url": "2.29 seconds"
  },
  "improvement": {
    "time_reduction": "42.9%",
    "speed_multiplier": "1.8x"
  }
}
```

---

## 🔍 Deduplication Algorithm

### **Multi-Layer Deduplication System:**

#### **Layer 1: URL Matching (90% threshold)**
```python
def normalize_url(url):
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return normalized.lower().rstrip('/')

def are_urls_similar(url1, url2):
    similarity = SequenceMatcher(None, norm_url1, norm_url2).ratio()
    return similarity >= 0.90
```

#### **Layer 2: Title Similarity (85% threshold)**
```python
def calculate_title_similarity(title1, title2):
    title1_norm = title1.lower().strip()
    title2_norm = title2.lower().strip()
    similarity = SequenceMatcher(None, title1_norm, title2_norm).ratio()
    return similarity >= 0.85
```

#### **Layer 3: Content Similarity (75% threshold)**
```python
def calculate_content_similarity(article1, article2):
    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_features=1000,
        ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform([content1, content2])
    similarity = cosine_similarity(tfidf_matrix)[0, 1]
    return similarity >= 0.75
```

---

## 🗄️ Database Schema

### **News Articles Table:**
```sql
CREATE TABLE news_articles (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    summary TEXT,
    description TEXT,
    published TIMESTAMP,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    has_image BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    extraction_method TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Performance optimization indexes
    INDEX idx_source (source),
    INDEX idx_category (category),
    INDEX idx_published (published),
    INDEX idx_created_at (created_at)
);
```

### **Aggregation Runs Table:**
```sql
CREATE TABLE aggregation_runs (
    id BIGSERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT NOW(),
    total_articles INTEGER,
    total_sources INTEGER,
    execution_time_seconds DECIMAL,
    deduplication_stats JSONB,
    performance_metrics JSONB
);
```

---

## 🚀 API Endpoints (Supabase Auto-Generated)

### **Articles Endpoint:**
```
GET /rest/v1/news_articles
POST /rest/v1/news_articles
PATCH /rest/v1/news_articles?id=eq.{id}
DELETE /rest/v1/news_articles?id=eq.{id}
```

### **Query Examples:**
```sql
-- Get latest articles
SELECT * FROM news_articles 
ORDER BY published DESC 
LIMIT 50;

-- Get articles by category
SELECT * FROM news_articles 
WHERE category = 'technology' 
ORDER BY published DESC;

-- Get articles with images
SELECT * FROM news_articles 
WHERE has_image = true 
ORDER BY published DESC;
```

---

## 🔧 Development Setup

### **Installation:**
```bash
# Clone repository
git clone <repository-url>
cd news-aggregator

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Setup environment
cp .env.example .env
# Edit .env with your API keys
```

### **Local Development:**
```bash
# Run RSS fetcher only
python fetchnews/rss_news_fetcher.py

# Run NewsAPI fetcher only
python fetchnews/newsapi_fetcher.py

# Run full aggregation
python main.py

# Run async optimized version
python fetchnews/async_rss_fetcher.py
```

### **Testing:**
```bash
# Test database connection
python db/supabase_integration.py

# Performance benchmark
python PLAYWRIGHT_OPTIMIZATION_GUIDE.md  # See benchmark section
```

---

## 🔄 CI/CD Pipeline

### **GitHub Actions Workflow:**
```yaml
name: Daily News Aggregation
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  workflow_dispatch:      # Manual trigger

jobs:
  aggregate-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m playwright install chromium
      - run: echo "1" | python main.py  # Sequential mode for CI
```

### **Environment Secrets:**
- `NEWSAPI_KEY_PRIMARY`
- `NEWSAPI_KEY_SECONDARY` (optional)
- `NEWSAPI_KEY_TERTIARY` (optional)
- `SUPABASE_URL`
- `SUPABASE_KEY`

---

## 📊 Monitoring & Analytics

### **Built-in Metrics:**
```python
{
    'total_articles': 847,
    'total_sources': 23,
    'execution_time_seconds': 142.5,
    'deduplication_info': {
        'total_duplicates_removed': 156,
        'url_duplicates': 89,
        'title_duplicates': 45,
        'content_duplicates': 22
    },
    'performance_metrics': {
        'success_rate': 94.2,
        'articles_per_second': 5.9,
        'cache_hit_rate': 23.1
    }
}
```

### **Performance Tracking:**
- Execution time per run
- Success/failure rates
- Deduplication effectiveness
- Resource utilization
- Cache performance

---

## 🔧 Optimization Features

### **Async Implementation Benefits:**
- **42.9% faster processing** than sequential
- **Concurrent feed processing** (5 feeds simultaneously)
- **Parallel content extraction** (3 articles per feed)
- **Smart resource management** with semaphores
- **Network optimization** (blocks ads, trackers)

### **Caching Strategy:**
- **Content caching** with TTL (1 hour default)
- **Failed request caching** (prevents retries)
- **Image URL validation** and caching
- **RSS feed response caching**

### **Error Handling:**
- **Graceful degradation** on source failures
- **Automatic retry logic** with exponential backoff
- **API key rotation** on rate limits
- **Comprehensive error logging**

---

## 🛠️ Troubleshooting

### **Common Issues:**
1. **Playwright Installation:** `python -m playwright install`
2. **Memory Issues:** Reduce concurrent limits in .env
3. **Rate Limits:** Ensure API key rotation is working
4. **Timeouts:** Adjust PLAYWRIGHT_TIMEOUT setting

### **Performance Tuning:**
- Monitor system resources during execution
- Adjust concurrency limits based on available CPU/memory
- Use async implementations for production workloads
- Implement request queuing for high-volume scenarios

### **Debug Commands:**
```bash
# Check environment variables
python -c "import os; print(os.getenv('NEWSAPI_KEY_PRIMARY'))"

# Test database connection
python -c "from db.supabase_integration import SupabaseNewsDB; db = SupabaseNewsDB()"

# Validate RSS feeds
python -c "import feedparser; print(feedparser.parse('http://feeds.bbci.co.uk/news/rss.xml').entries[0])"
```

---

## 📋 Technical Roadmap

### **Phase 1: Foundation (Complete)**
- ✅ Multi-source aggregation
- ✅ Advanced deduplication
- ✅ Supabase integration
- ✅ GitHub Actions automation

### **Phase 2: Intelligence Enhancement (In Progress)**
- 🔄 Location-based news categorization
- 🔄 Sentiment analysis integration
- 🔄 Topic modeling and clustering
- 🔄 Real-time news alerts

### **Phase 3: Scale & Performance (75% Complete)**
- ✅ Horizontal scaling architecture - Async foundation implemented
- ✅ Advanced caching mechanisms - Framework ready
- ✅ API rate optimization - 42.9% performance improvement achieved
- 📋 Multi-language support

### **Phase 4: Enterprise Features (Planned)**
- 📋 Custom source integration APIs
- 📋 Advanced analytics dashboard
- 📋 White-label deployment options
- 📋 Enterprise API management

---

*Technical Specification Version: 2.0*  
*Last Updated: December 2024*  
*Performance Optimized: 42.9% improvement achieved*