"""
FetchNews Package
Contains news fetchers for RSS feeds and NewsAPI
"""

from .rss_news_fetcher import RSSNewsFetcher
from .newsapi_fetcher import NewsAPIFetcher

__all__ = ['RSSNewsFetcher', 'NewsAPIFetcher']