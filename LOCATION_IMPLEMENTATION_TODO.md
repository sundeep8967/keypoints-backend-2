# 📋 Location-Based News Implementation To-Do List

## **🗄️ Phase 1: Database Setup (Supabase)**

### **1.1 Add Location Columns to `news_articles` Table:**
```sql
-- Execute in Supabase SQL Editor
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS primary_location TEXT;
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8);
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8);
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS location_hierarchy TEXT[];
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS nearby_locations TEXT[];
ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS location_confidence DECIMAL(3,2);
```

### **1.2 Create Indexes for Performance:**
```sql
-- Execute in Supabase SQL Editor
CREATE INDEX IF NOT EXISTS news_articles_location_idx ON news_articles USING GIST(
  ll_to_earth(latitude, longitude)
) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX IF NOT EXISTS news_articles_location_text_idx ON news_articles USING GIN(
  to_tsvector('english', primary_location)
) WHERE primary_location IS NOT NULL;
```

### **1.3 Create Location-Based Query Function:**
```sql
-- Execute in Supabase SQL Editor
CREATE OR REPLACE FUNCTION get_location_based_news_single_table(
  user_lat DECIMAL,
  user_lng DECIMAL,
  user_city TEXT,
  radius_km INTEGER DEFAULT 100,
  result_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  content TEXT,
  source TEXT,
  published_at TIMESTAMP,
  image_url TEXT,
  primary_location TEXT,
  distance_km DECIMAL,
  location_relevance_score INTEGER,
  is_local BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  WITH scored_articles AS (
    SELECT 
      na.id,
      na.title,
      na.content,
      na.source,
      na.published_at,
      na.image_url,
      na.primary_location,
      
      -- Calculate distance (only if article has coordinates)
      CASE 
        WHEN na.latitude IS NOT NULL AND na.longitude IS NOT NULL THEN
          earth_distance(
            ll_to_earth(user_lat, user_lng),
            ll_to_earth(na.latitude, na.longitude)
          ) / 1000
        ELSE NULL
      END as distance_km,
      
      -- Calculate location relevance score
      CASE 
        -- Exact city match
        WHEN LOWER(na.primary_location) = LOWER(user_city) THEN 100
        
        -- User city mentioned in nearby locations
        WHEN user_city = ANY(na.nearby_locations) THEN 90
        
        -- Article location in user's nearby areas (Bellary-Hospet proximity)
        WHEN na.primary_location = ANY(ARRAY['Hospet', 'Hampi']) AND LOWER(user_city) = 'bellary' THEN 85
        WHEN na.primary_location = ANY(ARRAY['Bellary', 'Ballari']) AND LOWER(user_city) = 'hospet' THEN 85
        
        -- Geographic proximity (if coordinates available)
        WHEN na.latitude IS NOT NULL AND na.longitude IS NOT NULL AND
             earth_distance(
               ll_to_earth(user_lat, user_lng),
               ll_to_earth(na.latitude, na.longitude)
             ) / 1000 < 25 THEN 80
             
        WHEN na.latitude IS NOT NULL AND na.longitude IS NOT NULL AND
             earth_distance(
               ll_to_earth(user_lat, user_lng),
               ll_to_earth(na.latitude, na.longitude)
             ) / 1000 < 50 THEN 70
             
        WHEN na.latitude IS NOT NULL AND na.longitude IS NOT NULL AND
             earth_distance(
               ll_to_earth(user_lat, user_lng),
               ll_to_earth(na.latitude, na.longitude)
             ) / 1000 < radius_km THEN 60
        
        -- State level match (Karnataka)
        WHEN 'Karnataka' = ANY(na.location_hierarchy) AND user_city IN (
          'Bellary', 'Ballari', 'Hospet', 'Bangalore', 'Mysore', 'Hubli'
        ) THEN 40
        
        -- Country level (India)
        WHEN 'India' = ANY(na.location_hierarchy) THEN 20
        
        ELSE 0
      END as relevance_score,
      
      -- Mark as local news
      CASE 
        WHEN LOWER(na.primary_location) = LOWER(user_city) OR
             user_city = ANY(na.nearby_locations) OR
             (na.latitude IS NOT NULL AND na.longitude IS NOT NULL AND
              earth_distance(
                ll_to_earth(user_lat, user_lng),
                ll_to_earth(na.latitude, na.longitude)
              ) / 1000 < 50) THEN true
        ELSE false
      END as is_local
      
    FROM news_articles na
    WHERE na.published_at > NOW() - INTERVAL '7 days'
      AND na.title IS NOT NULL
  )
  
  SELECT 
    sa.id,
    sa.title,
    sa.content,
    sa.source,
    sa.published_at,
    sa.image_url,
    sa.primary_location,
    sa.distance_km,
    sa.relevance_score,
    sa.is_local
  FROM scored_articles sa
  WHERE sa.relevance_score > 0
  ORDER BY 
    sa.relevance_score DESC,
    sa.distance_km ASC NULLS LAST,
    sa.published_at DESC
  LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;
```

---

## **🐍 Phase 2: Python Backend Updates**

### **2.1 Install Required Packages:**
```bash
pip install geopy spacy
python -m spacy download en_core_web_sm
```

### **2.2 Create Location Processor Class:**
- [ ] Create `location_processor.py` in your project
- [ ] Add location proximity mappings for Indian cities
- [ ] Implement location extraction logic

### **2.3 Update Article Processing Pipeline:**
- [ ] Import `LocationProcessor` in your news fetchers
- [ ] Add location extraction to `process_articles()` method
- [ ] Update Supabase insertion to include location fields

### **2.4 Modify `fetchnews/newsapi_fetcher.py`:**
```python
# Add to process_articles method
def process_articles(self, articles_data, category, source_name=None):
    # ... existing code ...
    
    # Add location processing
    location_processor = LocationProcessor()
    for article in processed_articles:
        article = location_processor.extract_location_from_article(article)
    
    return processed_articles
```

### **2.5 Modify `fetchnews/rss_news_fetcher.py`:**
- [ ] Add same location processing to RSS fetcher

---

## **📱 Phase 3: Flutter App Updates**

### **3.1 Add Dependencies to `pubspec.yaml`:**
```yaml
dependencies:
  geolocator: ^9.0.2
  geocoding: ^2.1.0
  permission_handler: ^10.4.3
```

### **3.2 Add Location Permissions:**

**Android (`android/app/src/main/AndroidManifest.xml`):**
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

**iOS (`ios/Runner/Info.plist`):**
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>This app needs location access to show local news</string>
```

### **3.3 Create Location Service:**
- [ ] Create `lib/services/location_service.dart`
- [ ] Implement `getUserLocation()` method
- [ ] Implement `getCityFromCoordinates()` method

### **3.4 Create News Service:**
- [ ] Create `lib/services/news_service.dart`
- [ ] Implement `getLocationBasedNews()` method
- [ ] Add Supabase RPC call

### **3.5 Create Location-Based News Screen:**
- [ ] Create `lib/screens/location_news_screen.dart`
- [ ] Implement local vs national news sections
- [ ] Add location permission handling

### **3.6 Update Main App:**
- [ ] Add location-based news screen to navigation
- [ ] Handle location permissions on app start

---

## **🧪 Phase 4: Testing & Validation**

### **4.1 Test Location Extraction:**
- [ ] Test with Bellary/Ballari news articles
- [ ] Verify Hospet proximity detection
- [ ] Check coordinate accuracy

### **4.2 Test Database Functions:**
- [ ] Test Supabase function with sample coordinates
- [ ] Verify distance calculations
- [ ] Check relevance scoring

### **4.3 Test Flutter Integration:**
- [ ] Test location permission flow
- [ ] Verify API calls to Supabase
- [ ] Test local vs national news separation

### **4.4 Test Proximity Scenarios:**
- [ ] User in Hospet should see Bellary news
- [ ] User in Bellary should see Hospet news
- [ ] Distance-based relevance working

---

## **🚀 Phase 5: Deployment & Optimization**

### **5.1 Performance Optimization:**
- [ ] Add caching for location lookups
- [ ] Optimize database queries
- [ ] Add pagination for large result sets

### **5.2 Error Handling:**
- [ ] Handle location permission denied
- [ ] Handle network errors
- [ ] Fallback to national news if location fails

### **5.3 User Experience:**
- [ ] Add loading indicators
- [ ] Add pull-to-refresh
- [ ] Add location change detection

---

## **📊 Phase 6: Monitoring & Analytics**

### **6.1 Add Logging:**
- [ ] Log location extraction accuracy
- [ ] Track user location preferences
- [ ] Monitor query performance

### **6.2 User Feedback:**
- [ ] Add "Is this relevant?" feedback
- [ ] Track click-through rates for local news
- [ ] Improve location detection based on feedback

---

## **🎯 Priority Order:**

1. **Start with Phase 1** (Database setup) - Foundation
2. **Phase 2** (Python backend) - Core functionality  
3. **Phase 3** (Flutter app) - User interface
4. **Phase 4** (Testing) - Validation
5. **Phase 5 & 6** (Optimization) - Enhancement

**Estimated Timeline:** 2-3 weeks for full implementation

---

## **📝 Progress Tracking:**

### **Completed Tasks:**
- [ ] Phase 1.1: Database columns added
- [ ] Phase 1.2: Indexes created
- [ ] Phase 1.3: Function created
- [ ] Phase 2.1: Packages installed
- [ ] Phase 2.2: Location processor created
- [ ] Phase 2.3: Article processing updated
- [ ] Phase 3.1: Flutter dependencies added
- [ ] Phase 3.2: Permissions configured
- [ ] Phase 3.3: Location service created
- [ ] Phase 3.4: News service created
- [ ] Phase 3.5: Location screen created
- [ ] Phase 4: Testing completed
- [ ] Phase 5: Optimization completed

### **Notes:**
- Remember to test Bellary-Hospet proximity scenario
- Focus on Indian city name variations (Bellary/Ballari, Bangalore/Bengaluru)
- Consider adding more location proximity mappings as needed

---

**🚀 Ready to start with Phase 1? Check off each task as you complete it!**