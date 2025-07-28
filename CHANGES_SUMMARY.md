# Source Extraction and URL Mapping Changes

## ✅ Changes Implemented

### 1. **NewsAPI Fetcher (`fetchnews/newsapi_fetcher.py`)**

#### Source Extraction:
- **Before**: Used generic source names or fallback values
- **After**: Extracts actual source names from NewsAPI response
```python
# Extract proper source name from NewsAPI response
source_info = article.get('source', {})
source_name = source_info.get('name', source_name) if isinstance(source_info, dict) else source_name
```
- **Result**: Now gets proper names like "Salon.com", "BBC News", "TechCrunch", etc.

#### URL Field Mapping:
- **Before**: Used `'link'` field
- **After**: Uses `'url'` field for Supabase compatibility
```python
'url': article.get('url', ''),  # Changed from 'link' to 'url'
```

#### Additional Fields Added:
```python
'source': source_name,  # Use extracted source name
'api_source': 'newsapi',
'has_image': bool(article.get('urlToImage')),
'tags': [],
'content_extracted': False
```

### 2. **RSS News Fetcher (`fetchnews/rss_news_fetcher.py`)**

#### Source Extraction:
- **Before**: Used feed names inconsistently
- **After**: Uses the RSS source name directly
```python
'source': source_name,  # Use the RSS source name
```

#### URL Field Mapping:
- **Before**: Used `'link'` field
- **After**: Uses `'url'` field
```python
'url': entry.get('link', ''),  # Changed from 'link' to 'url'
```

#### Additional Fields Added:
```python
'source': source_name,
'api_source': 'rss',
'rss_url': feed_url,
'has_image': False,  # Set to True when image found
'tags': [tag.term for tag in entry.get('tags', [])],
'content_extracted': False
```

#### Image Detection:
```python
if image_url:
    article['image_url'] = image_url
    article['has_image'] = True  # Properly set has_image flag
```

### 3. **Supabase Integration (`db/supabase_integration.py`)**

#### URL Field Support:
- **Before**: Only supported `'link'` field
- **After**: Supports both `'url'` and `'link'` for backward compatibility
```python
'url': article.get('url', '') or article.get('link', ''),  # Support both
```

#### Additional Fields:
```python
'has_image': bool(article.get('image_url', '').strip()),
'api_source': article.get('api_source', 'unknown'),
```

#### Database Schema Updates:
- Index changed from `idx_news_articles_link` to `idx_news_articles_url`
- Added `idx_news_articles_api_source` index

## 🎯 **Benefits**

### 1. **Proper Source Names**
- ✅ "Salon.com" instead of generic names
- ✅ "BBC News" instead of "bbc-news"
- ✅ "TechCrunch" instead of feed URL

### 2. **Supabase Compatibility**
- ✅ `url` field instead of `link` for better database naming
- ✅ Proper `has_image` boolean field
- ✅ `api_source` to track data origin (newsapi/rss)

### 3. **Enhanced Metadata**
- ✅ Better categorization with specific metadata
- ✅ Proper image detection and flagging
- ✅ Content extraction tracking

## 📊 **Example Output**

### Before:
```json
{
  "title": "Article Title",
  "link": "https://example.com/article",
  "source": "generic-source",
  "has_image": undefined
}
```

### After:
```json
{
  "title": "Article Title", 
  "url": "https://example.com/article",
  "source": "Salon.com",
  "api_source": "newsapi",
  "has_image": true,
  "content_extracted": false
}
```

## 🚀 **Ready for Production**

All changes are backward compatible and ready for Supabase integration. The data structure now properly maps to database fields and provides better source attribution.