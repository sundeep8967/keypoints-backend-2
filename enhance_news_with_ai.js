#!/usr/bin/env node
/**
 * AI News Enhancement Script (Node.js version)
 * Reads combined_news_data.json and creates enhanced version with catchy titles and 60-word descriptions
 */

import { GoogleGenAI } from "@google/genai";
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class NewsEnhancer {
    constructor() {
        // Initialize multiple API keys for rotation
        this.apiKeys = this.initializeApiKeys();
        
        if (this.apiKeys.length === 0) {
            throw new Error("No Gemini API keys found. Please set GEMINI_API_KEY or GEMINI_API_KEY_2 in your .env file");
        }
        
        // Initialize multiple Gemini clients for key rotation
        this.aiClients = this.apiKeys.map(key => new GoogleGenAI({ apiKey: key }));
        this.currentKeyIndex = 0;
        this.keyUsageStats = this.apiKeys.map(() => ({ requests: 0, errors: 0, lastUsed: 0 }));
        
        console.log(`🤖 Using Gemini API with ${this.apiKeys.length} key(s) for rotation`);
        
        // Rate limiting settings based on Gemini model capabilities
        this.modelRateLimits = {
            "gemini-2.0-flash-exp": parseInt(process.env.GEMINI_2_0_FLASH_RPM || '15'),      // Gemini 2.0 Flash: 15 RPM
            "gemini-2.0-flash-lite": parseInt(process.env.GEMINI_2_0_FLASH_LITE_RPM || '30'), // Gemini 2.0 Flash-Lite: 30 RPM  
            "gemini-1.5-flash": parseInt(process.env.GEMINI_1_5_FLASH_RPM || '15')           // Conservative fallback
        };
        this.currentModel = null;
        
        // Calculate effective rate limit with multiple keys
        this.baseRequestsPerMinute = parseInt(process.env.DEFAULT_RPM || '10');
        this.effectiveRequestsPerMinute = this.baseRequestsPerMinute * this.apiKeys.length;
        this.requestInterval = (60 / this.effectiveRequestsPerMinute) * 1000; // milliseconds
        this.lastRequestTimes = this.apiKeys.map(() => 0);
        
        // Enhancement settings
        this.maxArticles = parseInt(process.env.MAX_ARTICLES_TO_ENHANCE || '999999'); // Process ALL articles by default
        
        console.log("✅ Gemini AI enhancer initialized");
        console.log(`📊 Max articles to enhance: ${this.maxArticles}`);
        console.log(`🔄 Effective rate limit: ${this.effectiveRequestsPerMinute} RPM (${this.baseRequestsPerMinute} RPM per key)`);
    }
    
    initializeApiKeys() {
        const keys = [];
        
        // Primary API key
        if (process.env.GEMINI_API_KEY) {
            keys.push(process.env.GEMINI_API_KEY);
        }
        
        // Secondary API key
        if (process.env.GEMINI_API_KEY_2) {
            keys.push(process.env.GEMINI_API_KEY_2);
        }
        
        // Additional keys (GEMINI_API_KEY_3, etc.)
        let keyIndex = 3;
        while (process.env[`GEMINI_API_KEY_${keyIndex}`]) {
            keys.push(process.env[`GEMINI_API_KEY_${keyIndex}`]);
            keyIndex++;
        }
        
        return keys;
    }
    
    selectNextApiKey() {
        // Simple round-robin selection
        const selectedIndex = this.currentKeyIndex;
        this.currentKeyIndex = (this.currentKeyIndex + 1) % this.apiKeys.length;
        
        // Update usage stats
        this.keyUsageStats[selectedIndex].lastUsed = Date.now();
        
        return {
            index: selectedIndex,
            client: this.aiClients[selectedIndex],
            keyPreview: `...${this.apiKeys[selectedIndex].slice(-8)}`
        };
    }
    
    logKeyUsageStats() {
        console.log("\n📊 API Key Usage Statistics:");
        this.keyUsageStats.forEach((stats, index) => {
            const keyPreview = `...${this.apiKeys[index].slice(-8)}`;
            const errorRate = stats.requests > 0 ? (stats.errors / stats.requests * 100).toFixed(1) : '0.0';
            console.log(`   Key ${index + 1} (${keyPreview}): ${stats.requests} requests, ${stats.errors} errors (${errorRate}%)`);
        });
    }
    
    updateRateLimitForModel(modelName) {
        if (this.modelRateLimits[modelName] && this.currentModel !== modelName) {
            this.currentModel = modelName;
            this.baseRequestsPerMinute = this.modelRateLimits[modelName];
            this.effectiveRequestsPerMinute = this.baseRequestsPerMinute * this.apiKeys.length;
            this.requestInterval = (60 / this.effectiveRequestsPerMinute) * 1000;
            console.log(`🔧 Updated rate limit for ${modelName}: ${this.effectiveRequestsPerMinute} RPM total (${this.baseRequestsPerMinute} RPM per key)`);
        }
    }

    async rateLimit(keyIndex) {
        const currentTime = Date.now();
        const timeSinceLastRequest = currentTime - this.lastRequestTimes[keyIndex];
        const perKeyInterval = (60 / this.baseRequestsPerMinute) * 1000; // Individual key rate limit
        
        if (timeSinceLastRequest < perKeyInterval) {
            const sleepTime = perKeyInterval - timeSinceLastRequest;
            const keyPreview = `...${this.apiKeys[keyIndex].slice(-8)}`;
            console.log(`⏳ Rate limiting key ${keyIndex + 1} (${keyPreview}): waiting ${(sleepTime/1000).toFixed(1)} seconds...`);
            await new Promise(resolve => setTimeout(resolve, sleepTime));
        }
        
        this.lastRequestTimes[keyIndex] = Date.now();
    }
    
    async generateContentWithRetry(prompt, maxRetries = 3) {
        const models = [
            "gemini-2.0-flash-lite",      
            "gemini-2.0-flash-exp",    // Primary: Latest Gemini 2.0 Flash
            "gemini-1.5-flash"           
        ];
        
        // Try each model with all available API keys
        for (const model of models) {
            // Try each API key for this model
            for (let keyAttempt = 0; keyAttempt < this.apiKeys.length; keyAttempt++) {
                const keyInfo = this.selectNextApiKey();
                
                for (let attempt = 1; attempt <= maxRetries; attempt++) {
                    try {
                        // Apply rate limiting for this specific key
                        await this.rateLimit(keyInfo.index);
                        
                        // Track request for this key
                        this.keyUsageStats[keyInfo.index].requests++;
                        
                        const response = await keyInfo.client.models.generateContent({
                            model: model,
                            contents: prompt
                        });
                        
                        // Update rate limit for successful model
                        this.updateRateLimitForModel(model);
                        
                        // Log successful model and key if not the primary ones
                        if (model !== "gemini-2.0-flash-lite" || keyInfo.index !== 0) {
                            console.log(`✅ Success with ${model} using key ${keyInfo.index + 1} (${keyInfo.keyPreview})`);
                        }
                        
                        return response;
                    } catch (error) {
                        // Track error for this key
                        this.keyUsageStats[keyInfo.index].errors++;
                        
                        // Handle quota exceeded (429) - try next key or model
                        if (error.message.includes('429') || error.message.includes('quota') || error.message.includes('RESOURCE_EXHAUSTED')) {
                            console.log(`⚠️  Quota exceeded for ${model} with key ${keyInfo.index + 1} (${keyInfo.keyPreview}), trying next key/model...`);
                            break; // Try next key for this model
                        }
                        
                        // Handle overloaded (503) - retry same model/key
                        if (error.message.includes('503') || error.message.includes('overloaded')) {
                            if (attempt < maxRetries) {
                                const waitTime = attempt * 2000; // Exponential backoff: 2s, 4s, 6s
                                console.log(`⚠️  ${model} overloaded with key ${keyInfo.index + 1} (attempt ${attempt}/${maxRetries}), waiting ${waitTime/1000}s...`);
                                await new Promise(resolve => setTimeout(resolve, waitTime));
                                continue;
                            }
                        }
                        
                        // For other errors, try next key immediately
                        console.log(`❌ Error with ${model} using key ${keyInfo.index + 1} (${keyInfo.keyPreview}): ${error.message.substring(0, 100)}...`);
                        break; // Try next key for this model
                    }
                }
            }
        }
        
        // If all models and keys failed
        throw new Error("All fallback models and API keys failed");
    }
    
    async enhanceBatchArticles(articles) {
        try {
            // Filter out articles without titles
            const validArticles = articles.filter(article => (article.title || '').trim());
            
            if (validArticles.length === 0) {
                console.log("⚠️  No valid articles in batch");
                return articles;
            }
            
            // Create batch prompt for multiple articles
            let prompt = `You are a professional news editor. Rewrite the following ${validArticles.length} news articles into engaging content.  

For each article:  
1. Create a catchy, easy-to-understand title suitable for an Indian audience.  
2. Write a compelling description of about 55–65 words. If the original content is shorter, expand it naturally to fit the length while keeping it clear, informative, and engaging.

`;
            
            validArticles.forEach((article, index) => {
                const originalTitle = (article.title || '').trim();
                const originalDescription = article.description || article.summary || '';
                
                prompt += `ARTICLE ${index + 1}:
Original Title: "${originalTitle}"
Original Description: "${originalDescription}"

`;
            });
            
            prompt += `Format your response EXACTLY as:
ARTICLE 1:
TITLE: [catchy title for article 1]
DESCRIPTION: [60-word description for article 1]

ARTICLE 2:
TITLE: [catchy title for article 2]
DESCRIPTION: [60-word description for article 2]

Continue this pattern for all ${validArticles.length} articles. Keep content factual and professional while making it more engaging.`;
            
            // Generate enhanced content with retry logic
            const response = await this.generateContentWithRetry(prompt, 3);
            
            if (!response.text) {
                console.log("⚠️  Empty response from Gemini");
                return articles;
            }
            
            // Parse batch response
            const enhancedData = this.parseBatchResponse(response.text, validArticles);
            
            // Map enhanced data back to original articles
            const enhancedArticles = [];
            let validIndex = 0;
            
            for (const article of articles) {
                if ((article.title || '').trim()) {
                    const enhanced = enhancedData[validIndex] || {};
                    const enhancedArticle = { ...article };
                    
                    if (enhanced.title) {
                        enhancedArticle.title = enhanced.title;
                        
                    }
                    
                    if (enhanced.description) {
                        enhancedArticle.description = enhanced.description;
                        
                    }
                    
                    // Article is enhanced - no flag needed since all DB articles are enhanced
                    enhancedArticles.push(enhancedArticle);
                    validIndex++;
                } else {
                    enhancedArticles.push(article);
                }
            }
            
            return enhancedArticles;
            
        } catch (error) {
            console.log(`❌ Error enhancing batch: ${error.message}`);
            return articles;
        }
    }
    
    parseBatchResponse(responseText, originalArticles) {
        try {
            const enhancedData = [];
            const lines = responseText.trim().split('\n');
            
            let currentArticleIndex = -1;
            let currentTitle = null;
            let currentDescription = null;
            
            for (const line of lines) {
                const trimmedLine = line.trim();
                
                // Check for article marker
                const articleMatch = trimmedLine.match(/^ARTICLE (\d+):/);
                if (articleMatch) {
                    // Save previous article if exists
                    if (currentArticleIndex >= 0) {
                        enhancedData[currentArticleIndex] = {
                            title: currentTitle,
                            description: currentDescription
                        };
                    }
                    
                    // Start new article
                    currentArticleIndex = parseInt(articleMatch[1]) - 1;
                    currentTitle = null;
                    currentDescription = null;
                    continue;
                }
                
                // Parse title and description
                if (trimmedLine.startsWith('TITLE:')) {
                    currentTitle = trimmedLine.replace('TITLE:', '').trim();
                } else if (trimmedLine.startsWith('DESCRIPTION:')) {
                    currentDescription = trimmedLine.replace('DESCRIPTION:', '').trim();
                    
                    // Validate description word count
                    if (currentDescription) {
                        const words = currentDescription.split(' ');
                        if (words.length > 60) {
                            currentDescription = words.slice(0, 60).join(' ') + '...';
                        }
                    }
                }
            }
            
            // Save last article
            if (currentArticleIndex >= 0) {
                enhancedData[currentArticleIndex] = {
                    title: currentTitle,
                    description: currentDescription
                };
            }
            
            // Fill in missing articles with empty data
            for (let i = 0; i < originalArticles.length; i++) {
                if (!enhancedData[i]) {
                    enhancedData[i] = { title: null, description: null };
                }
            }
            
            return enhancedData;
            
        } catch (error) {
            console.log(`❌ Error parsing batch response: ${error.message}`);
            return originalArticles.map(() => ({ title: null, description: null }));
        }
    }
    
    async enhanceNewsData(inputFile = 'data/combined_news_data.json', outputFile = 'data/combined_news_data_enhanced.json') {
        console.log(`📖 Reading news data from: ${inputFile}`);
        
        // Read input file
        let newsData;
        try {
            const fileContent = await fs.readFile(inputFile, 'utf-8');
            newsData = JSON.parse(fileContent);
        } catch (error) {
            if (error.code === 'ENOENT') {
                console.log(`❌ File not found: ${inputFile}`);
                console.log("Please run the main news aggregation first to generate combined_news_data.json");
                return false;
            } else {
                console.log(`❌ Error reading file: ${error.message}`);
                return false;
            }
        }
        
        console.log("✅ Loaded news data successfully");
        
        // Create enhanced copy of the data structure
        const enhancedData = { ...newsData };
        enhancedData.enhancement_timestamp = new Date().toISOString();
        enhancedData.enhancement_info = {
            api_version: '@google/genai',
            model_used: 'gemini-2.0-flash-exp',
            max_articles_limit: this.maxArticles,
            total_articles_processed: 0,
            articles_enhanced: 0,
            articles_skipped: 0
        };
        
        // Collect all articles from deduplicated data
        const allArticles = [];
        if (newsData.by_category_deduplicated) {
            for (const [category, articles] of Object.entries(newsData.by_category_deduplicated)) {
                allArticles.push(...articles);
            }
        }
        
        if (allArticles.length === 0) {
            console.log("❌ No articles found in the input data");
            return false;
        }
        
        console.log(`📊 Found ${allArticles.length} articles to process`);
        console.log(`🎯 Will enhance up to ${this.maxArticles} articles`);
        
        // Enhance articles in batches of 10
        const enhancedArticles = [];
        const articlesToProcess = Math.min(allArticles.length, this.maxArticles);
        const batchSize = 10;
        
        for (let i = 0; i < articlesToProcess; i += batchSize) {
            const batch = allArticles.slice(i, Math.min(i + batchSize, articlesToProcess));
            const batchNumber = Math.floor(i / batchSize) + 1;
            const totalBatches = Math.ceil(articlesToProcess / batchSize);
            
            console.log(`🔄 Enhancing batch ${batchNumber}/${totalBatches} (${batch.length} articles)...`);
            
            // Show titles of articles in this batch
            batch.forEach((article, index) => {
                console.log(`   ${i + index + 1}. ${(article.title || 'No title').substring(0, 60)}...`);
            });
            
            const enhancedBatch = await this.enhanceBatchArticles(batch);
            enhancedArticles.push(...enhancedBatch);
            
            // Update statistics
            for (const article of enhancedBatch) {
                enhancedData.enhancement_info.total_articles_processed++;
                // All articles in enhanced batch are considered enhanced
                enhancedData.enhancement_info.articles_enhanced++;
            }
            
            console.log(`✅ Batch ${batchNumber} completed\n`);
        }
        
        // Add remaining articles without enhancement if we hit the limit
        if (allArticles.length > this.maxArticles) {
            const remainingArticles = allArticles.slice(this.maxArticles);
            for (const article of remainingArticles) {
                enhancedArticles.push(article);
                enhancedData.enhancement_info.articles_skipped++;
            }
        }
        
        // Reorganize enhanced articles back into category structure
        const enhancedByCategory = {};
        for (const article of enhancedArticles) {
            const category = article.category || 'unknown';
            if (!enhancedByCategory[category]) {
                enhancedByCategory[category] = [];
            }
            enhancedByCategory[category].push(article);
        }
        
        // Update the enhanced data structure
        enhancedData.by_category_enhanced = enhancedByCategory;
        enhancedData.total_articles = enhancedArticles.length;
        
        // Calculate enhancement rate
        const totalEnhanced = enhancedData.enhancement_info.articles_enhanced;
        const totalProcessed = enhancedArticles.length;
        const enhancementRate = totalProcessed > 0 ? (totalEnhanced / totalProcessed * 100) : 0;
        enhancedData.enhancement_info.enhancement_rate = `${enhancementRate.toFixed(1)}%`;
        
        // Save enhanced data
        try {
            await fs.mkdir(path.dirname(outputFile), { recursive: true });
            await fs.writeFile(outputFile, JSON.stringify(enhancedData, null, 2), 'utf-8');
        } catch (error) {
            console.log(`❌ Error saving file: ${error.message}`);
            return false;
        }
        
        console.log("\n✅ Enhancement complete!");
        console.log(`💾 Enhanced data saved to: ${outputFile}`);
        console.log("📊 Statistics:");
        console.log(`   📰 Total articles: ${totalProcessed}`);
        console.log(`   🤖 Enhanced by AI: ${totalEnhanced}`);
        console.log(`   ⏭️  Skipped: ${enhancedData.enhancement_info.articles_skipped}`);
        console.log(`   📈 Enhancement rate: ${enhancementRate.toFixed(1)}%`);
        
        // Log API key usage statistics
        this.logKeyUsageStats();
        
        return true;
    }
}

async function main() {
    console.log("🤖 AI News Enhancement Tool (Node.js)");
    console.log("=".repeat(50));
    
    try {
        const enhancer = new NewsEnhancer();
        
        // Check if input file exists
        const inputFile = 'data/combined_news_data.json';
        try {
            await fs.access(inputFile);
        } catch {
            console.log(`❌ Input file not found: ${inputFile}`);
            console.log("Please run the main news aggregation script first:");
            console.log("python main.py");
            return;
        }
        
        // Run enhancement
        const success = await enhancer.enhanceNewsData();
        
        if (success) {
            console.log("\n🎉 Enhancement completed successfully!");
            console.log("📁 Check 'data/combined_news_data_enhanced.json' for results");
        } else {
            console.log("\n❌ Enhancement failed!");
        }
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
        console.log("Make sure you have:");
        console.log("1. Set GEMINI_API_KEY in your .env file");
        console.log("2. Installed required dependencies: npm install @google/genai dotenv");
        console.log("3. Run the main aggregation script first");
    }
}

// Run if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}