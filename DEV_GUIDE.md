# 📰 News Aggregator Platform - Developer Guide

## 🎯 Project Overview

**AI-Powered News Intelligence Platform** that fetches, enhances, and stores news articles from multiple sources with advanced deduplication and AI enhancement capabilities.

### Core Features
- 🔄 **Multi-Source Aggregation**: RSS feeds + NewsAPI integration
- 🤖 **AI Enhancement**: Gemini-powered content enrichment
- 🗄️ **Database Storage**: Supabase integration for enhanced articles only
- 🔍 **Advanced Deduplication**: Title, URL, and content similarity detection
- ⚡ **Parallel Processing**: Simultaneous RSS and NewsAPI fetching

---

## 🏗️ Architecture

### Data Flow
```
RSS Feeds + NewsAPI → Deduplication → AI Enhancement → Supabase
```

### Key Components
- **Python Backend**: News fetching, processing, and orchestration
- **Node.js AI Engine**: Gemini-powered content enhancement
- **Supabase Database**: Enhanced articles storage
- **GitHub Actions**: Automated daily aggregation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Supabase account
- NewsAPI key
- Gemini API key(s)

### Installation
```bash
# 1. Clone and setup Python environment
pip install -r requirements.txt

# 2. Install Node.js dependencies
npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the pipeline
python main.py
# Choose option 3 for full automation
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Required API Keys
NEWSAPI_KEY=your_newsapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Multiple Gemini keys for better performance
GEMINI_API_KEY_2=your_second_key
GEMINI_API_KEY_3=your_third_key
GEMINI_API_KEY_4=your_fourth_key

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Performance Tuning
GEMINI_2_0_FLASH_RPM=15          # Rate limit for Gemini 2.0 Flash
GEMINI_2_0_FLASH_LITE_RPM=30     # Rate limit for Gemini 2.0 Flash-Lite
GEMINI_1_5_FLASH_RPM=15          # Rate limit for Gemini 1.5 Flash
DEFAULT_RPM=10                   # Default conservative rate limit

# Deduplication Settings
TITLE_SIMILARITY_THRESHOLD=0.85  # Title similarity threshold (0.0-1.0)
URL_SIMILARITY_THRESHOLD=0.90    # URL similarity threshold (0.0-1.0)

# AI Enhancement Limits
MAX_ARTICLES_TO_ENHANCE=999999   # Set to specific number to limit processing
```

---

## 📁 Project Structure

```
news-aggregator/
├── main.py                     # Main orchestration script
├── enhance_news_with_ai.js     # AI enhancement engine
├── requirements.txt            # Python dependencies
├── package.json               # Node.js dependencies
├── .env.example               # Environment template
├── fetchnews/                 # News fetching modules
│   ├── rss_news_fetcher.py    # RSS feed processor
│   ├── newsapi_fetcher.py     # NewsAPI integration
│   ├── async_rss_fetcher.py   # Optimized async RSS
│   └── async_newsapi_fetcher.py # Optimized async NewsAPI
├── db/                        # Database integration
│   └── supabase_integration.py # Supabase operations
├── data/                      # Output files
│   ├── combined_news_data.json # Raw aggregated data
│   └── combined_news_data_enhanced.json # AI-enhanced data
└── .github/workflows/         # Automation
    └── daily-news-aggregation.yml # Daily pipeline
```

---

## 🔧 Core Components

### 1. News Fetching (`fetchnews/`)
- **RSS Fetcher**: Processes RSS feeds with parallel execution
- **NewsAPI Fetcher**: Triple-key system for enhanced rate limits
- **Parallel Processing**: ThreadPoolExecutor for simultaneous fetching

### 2. AI Enhancement (`enhance_news_with_ai.js`)
- **Multi-Model Support**: Gemini 2.0 Flash, Flash-Lite, 1.5 Flash
- **Dynamic Rate Limiting**: Optimizes based on successful model
- **Content Enrichment**: Adds descriptions, improves titles, extracts metadata

### 3. Database Integration (`db/supabase_integration.py`)
- **Enhanced Articles Only**: Raw data stays local, only AI-enhanced goes to DB
- **Quality Validation**: Articles must have image + title + description
- **Batch Processing**: Efficient bulk inserts


---

## 🎯 Usage Modes

### 1. Sequential Processing
```bash
python main.py
# Choose option 1: Sequential (RSS first, then NewsAPI)
```

### 2. Parallel Processing
```bash
python main.py
# Choose option 2: Parallel (Both simultaneously)
```

### 3. Full Automation Pipeline
```bash
python main.py
# Choose option 3: Full Auto (Parallel + AI + Supabase)
```

---

## 📊 Performance Metrics

### Processing Results
- **Parallel execution** for faster processing
- **Improved throughput** over sequential processing
- **Processing speed**: Typically completes in under 5 minutes


---

## 🔍 Deduplication System

### Multi-Level Detection
1. **URL Similarity**: Normalized URL comparison (configurable via `URL_SIMILARITY_THRESHOLD`, default: 90%)
2. **Title Similarity**: SequenceMatcher analysis (configurable via `TITLE_SIMILARITY_THRESHOLD`, default: 85%)
3. **Content Similarity**: TF-IDF + cosine similarity (configurable via `CONTENT_SIMILARITY_THRESHOLD`, default: 75%)

### Advanced Features
- **Smart Normalization**: Removes query parameters, fragments
- **Content Preprocessing**: HTML removal, special character handling
- **Weighted Comparison**: Title gets double weight in content analysis

---

## 🤖 AI Enhancement Features

### Content Enrichment
- **Description Generation**: Creates compelling article summaries
- **Title Optimization**: Improves clarity and engagement
- **Metadata Extraction**: Identifies topics, regions, categories
- **Image Validation**: Ensures proper image URLs
- **Database Storage**: Only enhanced articles are stored in Supabase

### Rate Limit Optimization
- **Model-Specific Limits**: Different RPM for each Gemini model
  - Gemini 2.0 Flash: 15 RPM (configurable via `GEMINI_2_0_FLASH_RPM`)
  - Gemini 2.0 Flash-Lite: 30 RPM (configurable via `GEMINI_2_0_FLASH_LITE_RPM`)
  - Gemini 1.5 Flash: 15 RPM (configurable via `GEMINI_1_5_FLASH_RPM`)
- **Multi-Key Support**: Unlimited API keys (GEMINI_API_KEY_1 through GEMINI_API_KEY_N)
- **Dynamic Key Rotation**: Automatic failover between available keys
- **Batch Processing**: Configurable article limit via `MAX_ARTICLES_TO_ENHANCE`

---

## 🗄️ Database Schema

### news_articles Table
```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    published TIMESTAMP,
    source TEXT,
    category TEXT,
    description TEXT,
    image_url TEXT,
    article_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Note:** All articles in this table are AI-enhanced by design. Raw articles remain in local JSON files only.

### aggregation_runs Table
```sql
CREATE TABLE aggregation_runs (
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
```

### Key Indexes
```sql
-- Performance indexes for news_articles table
CREATE INDEX IF NOT EXISTS idx_news_articles_link ON news_articles(link);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_news_articles_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published);

-- Performance indexes for aggregation_runs table
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON aggregation_runs(run_timestamp);
```

---

## 🚀 Deployment

### GitHub Actions Setup
```yaml
# .github/workflows/daily-news-aggregation.yml
name: Daily News Aggregation
on:
  schedule:
    - cron: '30 3 * * *'  # Daily at 3:30 AM UTC (9:00 AM IST)
  workflow_dispatch:      # Manual trigger

jobs:
  aggregate-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install
      - name: Create .env file from secrets
        run: |
          echo "NEWSAPI_KEY_PRIMARY=${{ secrets.NEWSAPI_KEY_PRIMARY }}" >> .env
          echo "NEWSAPI_KEY_SECONDARY=${{ secrets.NEWSAPI_KEY_SECONDARY }}" >> .env
          echo "NEWSAPI_KEY_TERTIARY=${{ secrets.NEWSAPI_KEY_TERTIARY }}" >> .env
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> .env
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> .env
          echo "GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}" >> .env
          echo "GEMINI_API_KEY_2=${{ secrets.GEMINI_API_KEY_2 }}" >> .env
          echo "GEMINI_API_KEY_3=${{ secrets.GEMINI_API_KEY_3 }}" >> .env
          echo "GEMINI_API_KEY_4=${{ secrets.GEMINI_API_KEY_4 }}" >> .env
          echo "TITLE_SIMILARITY_THRESHOLD=0.85" >> .env
          echo "URL_SIMILARITY_THRESHOLD=0.90" >> .env
          echo "CONTENT_SIMILARITY_THRESHOLD=0.75" >> .env
          echo "MAX_ARTICLES_TO_ENHANCE=999999" >> .env
      
      - name: Install Playwright browsers
        run: playwright install chromium
      
      - name: Download spaCy model
        run: python -m spacy download en_core_web_sm
      
      - name: Run complete automated pipeline
        run: echo "3" | python main.py
        timeout-minutes: 45
```

### Required Secrets
- `NEWSAPI_KEY_PRIMARY`: Primary NewsAPI authentication key
- `NEWSAPI_KEY_SECONDARY`: Secondary NewsAPI key (optional)
- `NEWSAPI_KEY_TERTIARY`: Tertiary NewsAPI key (optional)
- `NEWSAPI_KEY`: Fallback NewsAPI key (optional, used if PRIMARY not set)
- `GEMINI_API_KEY`: Primary Gemini API key
- `GEMINI_API_KEY_2`: Secondary Gemini key (optional)
- `GEMINI_API_KEY_3`: Tertiary Gemini key (optional)
- `GEMINI_API_KEY_4`: Fourth Gemini key (optional)
- `SUPABASE_URL`: Database URL
- `SUPABASE_KEY`: Database service key

---

## 🔧 Development Rules

### Code Standards
1. **Python**: Follow PEP 8, use type hints where possible
2. **JavaScript**: ES6+ modules, async/await for API calls
3. **Error Handling**: Graceful degradation, comprehensive logging
4. **Performance**: Prefer async operations, batch processing

### Data Flow Rules
1. **Raw Data**: Stays local in `data/combined_news_data.json`
2. **Enhanced Data**: Goes to Supabase from `data/combined_news_data_enhanced.json`
3. **No Duplicates**: Only enhanced articles reach the database
4. **Quality First**: Articles must pass validation (image + title + description)

### Environment Configuration
```bash
# Content extraction settings
MIN_DESCRIPTION_LENGTH=100          # Minimum description length for content extraction
TITLE_SIMILARITY_THRESHOLD=0.85     # Title deduplication threshold (0.0-1.0)
URL_SIMILARITY_THRESHOLD=0.90       # URL deduplication threshold (0.0-1.0)
CONTENT_SIMILARITY_THRESHOLD=0.75   # Content deduplication threshold (0.0-1.0)

# AI Enhancement settings
MAX_ARTICLES_TO_ENHANCE=999999      # Process ALL articles (or set specific limit)
GEMINI_2_0_FLASH_RPM=15            # Gemini 2.0 Flash rate limit (RPM)
GEMINI_2_0_FLASH_LITE_RPM=30       # Gemini 2.0 Flash-Lite rate limit (RPM)
GEMINI_1_5_FLASH_RPM=15            # Gemini 1.5 Flash rate limit (RPM)
DEFAULT_RPM=10                     # Default conservative rate limit
```

### Testing Guidelines
1. **Local Testing**: Use `python main.py` with option 1 or 2
2. **Full Pipeline**: Test with option 3 before deployment
3. **API Limits**: Monitor rate limits during development
4. **Data Validation**: Check output files for completeness

---

## 🐛 Troubleshooting

### Common Issues

#### API Rate Limits
```bash
# Symptoms: 429 errors, slow processing
# Solution: Adjust rate limits in .env
GEMINI_2_0_FLASH_RPM=10  # Reduce if hitting limits
```

#### Missing Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies
npm install

# Additional required installations
playwright install chromium          # For web scraping
python -m spacy download en_core_web_sm  # For NLP processing
```

#### Database Design
```sql
-- All articles in news_articles table are AI-enhanced by design
-- No enhanced_by_ai column needed since raw articles stay in JSON files
-- Database contains only processed, enhanced articles
```

#### NewsAPI Key Issues
```bash
# Multiple NewsAPI keys supported for redundancy
NEWSAPI_KEY_PRIMARY=your_primary_key     # Primary key
NEWSAPI_KEY_SECONDARY=your_backup_key    # Fallback key
NEWSAPI_KEY_TERTIARY=your_third_key      # Additional fallback
NEWSAPI_KEY=your_legacy_key              # Legacy fallback
```

#### Supabase Connection
```bash
# Check credentials in .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

#### Empty Results
- Verify RSS feeds are accessible
- Check NewsAPI key validity
- Ensure internet connectivity

---

## 📈 Monitoring & Analytics

### Key Metrics
- **Processing Time**: Target <3 minutes for full pipeline
- **Success Rate**: Aim for >95% article processing
- **Enhancement Rate**: Track AI processing success

### Log Analysis
```bash
# Check for errors
grep "❌" logs/pipeline.log

# Monitor performance
grep "execution_time" data/combined_news_data.json

# Enhancement metrics
grep "enhancement_info" data/combined_news_data_enhanced.json
```

---

## 🔮 Future Roadmap

### Current Status
- ✅ **Multi-source aggregation**: RSS feeds + NewsAPI
- ✅ **AI enhancement**: Gemini-powered content enrichment
- ✅ **Advanced deduplication**: Multi-level similarity detection
- ✅ **Parallel processing**: ThreadPoolExecutor optimization
- ✅ **Database integration**: Supabase with enhanced articles only
- ✅ **Automated pipeline**: GitHub Actions daily aggregation

---

## 🆘 Support

### Documentation
- This dev guide covers all core functionality
- Code comments explain complex algorithms
- Environment examples provided

### Debugging
- Enable verbose logging in main.py
- Check API quotas and limits
- Validate environment configuration

### Performance Tuning
- Adjust concurrency limits based on hardware
- Monitor API rate limits
- Optimize batch sizes for your data volume

---

## 🎉 Success Metrics

### Technical Achievements
- ✅ **Processing Speed**: Efficient parallel processing
- ✅ **Performance**: Improved throughput with ThreadPoolExecutor
- ✅ **AI Enhancement**: Gemini-powered content enrichment
- ✅ **Reliability**: Robust error handling and fallback mechanisms

### Business Value
- **Cost Efficiency**: Parallel processing for better resource utilization
- **User Experience**: Faster, AI-enhanced news delivery
- **Scalability**: Multi-threaded architecture ready for scaling
- **Intelligence**: AI-powered content enhancement

---

**Your News Aggregator Platform is optimized for high-performance, enterprise-grade news intelligence!** 📰⚡

*Ready for production deployment* 🚀