"""
Simplified Scrapy runner for financial news scraping
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import feedparser
import aiohttp
# Removed scrapy_items import - using simple dictionaries instead

logger = logging.getLogger(__name__)

class SimpleScrapyRunner:
    """Simplified runner that uses RSS feeds and basic HTTP requests"""
    
    def __init__(self):
        self.session = None
        
    async def scrape_news(self, search_term: str, asset_type: str = 'commodity', 
                         days_back: int = 7, max_articles: int = 100) -> List[Dict]:
        """
        Scrape news using RSS feeds and simple HTTP requests
        
        Args:
            search_term: Term to search for
            asset_type: Type of asset (commodity, stock, etc.)
            days_back: Number of days to look back
            max_articles: Maximum number of articles to collect
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"Starting simple scraping for '{search_term}' ({asset_type})")
        
        articles = []
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Define working RSS feeds with better rate limiting
        rss_feeds = [
            {
                'name': 'MarketWatch',
                'urls': [
                    'https://feeds.content.dowjones.io/public/rss/mw_marketpulse'
                ]
            },
            {
                'name': 'CNBC',
                'urls': [
                    'https://www.cnbc.com/id/19854910/device/rss/rss.html'
                ]
            },
            {
                'name': 'Financial Times',
                'urls': [
                    'https://www.ft.com/rss/home'
                ]
            },
            {
                'name': 'Economic Times',
                'urls': [
                    'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
                    'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms'
                ]
            },
            {
                'name': 'Business Standard',
                'urls': [
                    'https://www.business-standard.com/rss/markets-106.rss',
                    'https://www.business-standard.com/rss/stock-market-107.rss'
                ]
            },
            {
                'name': 'Moneycontrol',
                'urls': [
                    'https://www.moneycontrol.com/rss/business.xml',
                    'https://www.moneycontrol.com/rss/market.xml'
                ]
            },
            {
                'name': 'Livemint',
                'urls': [
                    'https://www.livemint.com/rss/markets',
                    'https://www.livemint.com/rss/companies'
                ]
            },
            {
                'name': 'Financial Express',
                'urls': [
                    'https://www.financialexpress.com/market/rss/',
                    'https://www.financialexpress.com/industry/rss/'
                ]
            }
        ]
        
        # Create aiohttp session with proper headers
        timeout = aiohttp.ClientTimeout(total=15)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            self.session = session
            
            # Scrape each RSS feed with delays
            for i, feed_info in enumerate(rss_feeds):
                try:
                    # Add delay between requests to avoid rate limiting
                    if i > 0:
                        await asyncio.sleep(2)
                    
                    feed_articles = await self._scrape_rss_feed(
                        feed_info, search_term, start_date, max_articles // len(rss_feeds)
                    )
                    articles.extend(feed_articles)
                    
                    if len(articles) >= max_articles:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error scraping {feed_info['name']}: {e}")
                    continue
        
        # Remove duplicates and sort by date
        articles = self._deduplicate_articles(articles)
        articles.sort(key=lambda x: x.get('date', datetime.now()), reverse=True)
        
        logger.info(f"Simple scraping completed. Found {len(articles)} articles")
        return articles[:max_articles]
    
    async def _scrape_rss_feed(self, feed_info: Dict, search_term: str, 
                              start_date: datetime, max_articles: int) -> List[Dict]:
        """Scrape a single RSS feed"""
        articles = []
        
        for rss_url in feed_info['urls']:
            try:
                async with self.session.get(rss_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        if not hasattr(feed, 'entries') or not feed.entries:
                            continue
                        
                        for entry in feed.entries[:max_articles]:
                            try:
                                # Check if article is recent enough
                                article_date = datetime.now()  # Default to now
                                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                    try:
                                        article_date = datetime(*entry.published_parsed[:6])
                                        if article_date < start_date:
                                            continue
                                    except (ValueError, TypeError):
                                        article_date = datetime.now()
                                
                                # Check if title contains our search term (be more lenient)
                                title = getattr(entry, 'title', '')
                                description = getattr(entry, 'description', '')
                                
                                # For general terms, commodities, and Indian stocks, be more inclusive
                                general_terms = [
                                    'market', 'finance', 'trading', 'investment', 'stock', 'equity', 'share',
                                    'gold', 'silver', 'oil', 'crude', 'copper', 'wheat', 'corn',
                                    'sensex', 'nifty', 'bse', 'nse', 'indian', 'india', 'mumbai', 'delhi',
                                    'tata', 'reliance', 'infosys', 'tcs', 'hdfc', 'icici', 'sbi', 'bharti',
                                    'adani', 'wipro', 'hcl', 'maruti', 'bajaj', 'mahindra', 'itc', 'hindalco'
                                ]
                                
                                if search_term.lower() in general_terms:
                                    # Accept all financial news for general terms, commodities, and major Indian stocks
                                    pass
                                elif not self._contains_search_term(title + ' ' + description, search_term):
                                    continue
                                
                                # Create article
                                article = {
                                    'title': title,
                                    'content': f"{title}. {description}",
                                    'url': getattr(entry, 'link', rss_url),
                                    'source': feed_info['name'],
                                    'date': article_date,
                                    'author': getattr(entry, 'author', ''),
                                    'search_term': search_term,
                                    'asset_type': 'commodity',
                                    'asset_name': search_term,
                                    'word_count': len((title + ' ' + description).split()),
                                    'response_url': rss_url,
                                    'response_status': response.status
                                }
                                
                                articles.append(article)
                                
                            except Exception as e:
                                logger.debug(f"Error processing RSS entry: {e}")
                                continue
                        
                        if articles:
                            break  # If we got articles from this feed, move to next feed
                            
            except Exception as e:
                logger.debug(f"Error scraping RSS feed {rss_url}: {e}")
                continue
        
        return articles
    
    def _contains_search_term(self, text: str, search_term: str) -> bool:
        """Check if text contains the search term (case insensitive)"""
        if not text or not search_term:
            return True
        
        search_terms = search_term.lower().split()
        text_lower = text.lower()
        
        # Check if any search term is in the text
        return any(term in text_lower for term in search_terms)
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return unique_articles

# Convenience function
async def run_simple_scraping(search_term: str, asset_type: str = 'commodity', 
                             days_back: int = 7, max_articles: int = 100) -> List[Dict]:
    """
    Convenience function to run simple scraping
    
    Args:
        search_term: Term to search for
        asset_type: Type of asset
        days_back: Number of days to look back
        max_articles: Maximum number of articles
        
    Returns:
        List of articles in legacy format
    """
    runner = SimpleScrapyRunner()
    return await runner.scrape_news(
        search_term=search_term,
        asset_type=asset_type,
        days_back=days_back,
        max_articles=max_articles
    )
