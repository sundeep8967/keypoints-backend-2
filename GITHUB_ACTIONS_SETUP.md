# 🚀 GitHub Actions Setup Guide

This guide will help you set up automated daily news aggregation using GitHub Actions.

## **📋 Prerequisites**

1. **GitHub Repository** - Your code should be in a GitHub repository
2. **NewsAPI Keys** - Get free API keys from [newsapi.org](https://newsapi.org/register)
3. **Supabase Account** - Set up your database at [supabase.com](https://supabase.com)

---

## **🔐 Step 1: Configure GitHub Secrets**

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### **Required Secrets:**

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `NEWSAPI_KEY_PRIMARY` | Your primary NewsAPI key | `abc123def456...` |
| `NEWSAPI_KEY_SECONDARY` | Your secondary NewsAPI key (optional) | `xyz789uvw012...` |
| `NEWSAPI_KEY_TERTIARY` | Your tertiary NewsAPI key (optional) | `mno345pqr678...` |
| `SUPABASE_URL` | Your Supabase project URL | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase anon/public key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Your Supabase service role key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |

### **How to Add Secrets:**

1. **NewsAPI Keys:**
   - Go to [newsapi.org](https://newsapi.org/register)
   - Sign up for free accounts (you can create multiple)
   - Copy your API keys
   - Add them as secrets in GitHub

2. **Supabase Keys:**
   - Go to your Supabase project dashboard
   - Navigate to **Settings** → **API**
   - Copy the **Project URL** and **API Keys**
   - Add them as secrets in GitHub

---

## **🗄️ Step 2: Set Up Supabase Database**

### **2.1 Create the `news_articles` Table:**

Execute this SQL in your Supabase SQL Editor:

```sql
-- Create news_articles table
CREATE TABLE IF NOT EXISTS news_articles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  content TEXT,
  summary TEXT,
  description TEXT,
  link TEXT UNIQUE,
  source TEXT,
  category TEXT,
  published_at TIMESTAMP,
  image_url TEXT,
  has_image BOOLEAN DEFAULT FALSE,
  author TEXT,
  tags TEXT[],
  data_source TEXT, -- 'rss' or 'newsapi'
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Location fields (for future location-based features)
  primary_location TEXT,
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  location_hierarchy TEXT[],
  nearby_locations TEXT[],
  location_confidence DECIMAL(3,2)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS news_articles_published_at_idx ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS news_articles_source_idx ON news_articles(source);
CREATE INDEX IF NOT EXISTS news_articles_category_idx ON news_articles(category);
CREATE INDEX IF NOT EXISTS news_articles_has_image_idx ON news_articles(has_image);
CREATE INDEX IF NOT EXISTS news_articles_link_idx ON news_articles(link);

-- Create text search index
CREATE INDEX IF NOT EXISTS news_articles_search_idx ON news_articles USING GIN(
  to_tsvector('english', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(content, ''))
);
```

### **2.2 Create Aggregation Runs Table (Optional):**

```sql
-- Create table to track aggregation runs
CREATE TABLE IF NOT EXISTS aggregation_runs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_timestamp TIMESTAMP DEFAULT NOW(),
  total_articles INTEGER,
  articles_with_images INTEGER,
  image_success_rate TEXT,
  execution_time_seconds DECIMAL,
  sources_count INTEGER,
  duplicates_removed INTEGER,
  rss_articles INTEGER,
  newsapi_articles INTEGER,
  status TEXT DEFAULT 'completed',
  error_message TEXT
);
```

---

## **📁 Step 3: Verify File Structure**

Make sure your repository has this structure:

```
your-repo/
├── .github/
│   └── workflows/
│       └── daily-news-aggregation.yml  ✅
├── fetchnews/
│   ├── __init__.py
│   ├── newsapi_fetcher.py
│   └── rss_news_fetcher.py
├── db/
│   ├── __init__.py
│   └── supabase_integration.py
├── data/                               # Will be created automatically
├── main.py                             # Interactive version
├── main_ci.py                          # CI/Automated version ✅
├── pyproject.toml
└── requirements.txt (optional)
```

---

## **⚙️ Step 4: Configure the Workflow**

The workflow is already configured to:

- **Run daily at 6:00 AM UTC** (11:30 AM IST)
- **Allow manual triggers** from GitHub Actions tab
- **Upload results as artifacts**
- **Generate detailed reports**
- **Commit data back to repository** (optional)

### **Customize the Schedule:**

Edit `.github/workflows/daily-news-aggregation.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'  # 6:00 AM UTC daily
  # Change to your preferred time:
  # - cron: '30 5 * * *'  # 5:30 AM UTC
  # - cron: '0 12 * * *'  # 12:00 PM UTC
```

---

## **🧪 Step 5: Test the Setup**

### **5.1 Manual Test:**

1. Go to your GitHub repository
2. Click **Actions** tab
3. Click **Daily News Aggregation** workflow
4. Click **Run workflow** button
5. Select execution mode and click **Run workflow**

### **5.2 Check Results:**

After the workflow completes:

1. **View the summary** in the workflow run page
2. **Download artifacts** to see the generated JSON files
3. **Check your Supabase database** for new articles
4. **Review the logs** for any errors

---

## **📊 Step 6: Monitor and Maintain**

### **6.1 Workflow Monitoring:**

- **GitHub Actions tab** - View all workflow runs
- **Email notifications** - GitHub will email you on failures
- **Workflow summary** - Detailed reports for each run

### **6.2 Troubleshooting Common Issues:**

| Issue | Solution |
|-------|----------|
| **"No NewsAPI keys found"** | Check that secrets are properly set |
| **"Supabase connection failed"** | Verify Supabase URL and keys |
| **"No articles aggregated"** | Check NewsAPI quota and RSS feed availability |
| **"Import errors"** | Ensure all dependencies are in `pyproject.toml` |

### **6.3 Maintenance Tasks:**

- **Monitor NewsAPI quota** - Free tier has 1000 requests/month
- **Check Supabase storage** - Monitor database size
- **Update dependencies** - Keep packages up to date
- **Review logs** - Check for any recurring errors

---

## **🎯 Step 7: Advanced Configuration**

### **7.1 Adjust Deduplication Thresholds:**

Add these optional secrets to fine-tune deduplication:

| Secret Name | Default | Description |
|-------------|---------|-------------|
| `TITLE_SIMILARITY_THRESHOLD` | `0.85` | Title similarity threshold (0.0-1.0) |
| `URL_SIMILARITY_THRESHOLD` | `0.90` | URL similarity threshold (0.0-1.0) |
| `CONTENT_SIMILARITY_THRESHOLD` | `0.75` | Content similarity threshold (0.0-1.0) |

### **7.2 Enable Data Commits:**

The workflow can automatically commit aggregated data back to your repository. This is enabled by default for scheduled runs.

To disable, remove this section from the workflow:

```yaml
- name: Commit and push data (optional)
  if: github.event_name == 'schedule'
  # ... remove this entire step
```

---

## **✅ Verification Checklist**

- [ ] GitHub secrets are configured
- [ ] Supabase database tables are created
- [ ] File structure is correct
- [ ] Workflow runs successfully
- [ ] Articles appear in Supabase
- [ ] Artifacts are generated
- [ ] Summary reports are readable

---

## **🆘 Getting Help**

If you encounter issues:

1. **Check the workflow logs** for specific error messages
2. **Verify all secrets** are correctly set
3. **Test your NewsAPI keys** manually
4. **Check Supabase connection** from your local environment
5. **Review the file structure** and imports

**Your automated news aggregation system is now ready! 🎉**