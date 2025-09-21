"""
Price fetching service for real-time asset prices
"""
import logging
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
from config import Config

logger = logging.getLogger(__name__)

class PriceService:
    """Service for fetching current prices of assets"""
    
    def __init__(self):
        self.config = Config()
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
    
    def get_current_price(self, asset_symbol: str) -> Optional[float]:
        """
        Get current price for a single asset
        
        Args:
            asset_symbol: The asset symbol (e.g., 'AAPL', 'GC=F')
            
        Returns:
            Current price as float, or None if not found
        """
        try:
            # Check cache first
            cache_key = f"{asset_symbol}_{datetime.now().strftime('%Y%m%d%H%M')}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_duration):
                    return cached_data['price']
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(asset_symbol)
            info = ticker.info
            
            # Try different price fields
            price = None
            if 'currentPrice' in info and info['currentPrice'] is not None:
                price = info['currentPrice']
            elif 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                price = info['regularMarketPrice']
            elif 'previousClose' in info and info['previousClose'] is not None:
                price = info['previousClose']
            else:
                # Fallback to historical data
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
            
            if price is not None:
                # Cache the result
                self.cache[cache_key] = {
                    'price': float(price),
                    'timestamp': datetime.now()
                }
                logger.info(f"Fetched current price for {asset_symbol}: ${price:.2f}")
                return float(price)
            else:
                logger.warning(f"Could not fetch price for {asset_symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {asset_symbol}: {e}")
            return None
    
    def get_current_prices_batch(self, asset_symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get current prices for multiple assets
        
        Args:
            asset_symbols: List of asset symbols
            
        Returns:
            Dictionary mapping symbols to prices
        """
        results = {}
        
        for symbol in asset_symbols:
            results[symbol] = self.get_current_price(symbol)
        
        return results
    
    def get_portfolio_prices(self, holdings: List[Dict]) -> Dict[str, Dict]:
        """
        Get current prices for portfolio holdings
        
        Args:
            holdings: List of holding dictionaries with asset_symbol
            
        Returns:
            Dictionary with price data for each holding
        """
        results = {}
        
        for holding in holdings:
            symbol = holding.get('asset_symbol')
            if symbol:
                price = self.get_current_price(symbol)
                results[symbol] = {
                    'current_price': price,
                    'last_updated': datetime.now().isoformat(),
                    'symbol': symbol,
                    'asset_name': holding.get('asset_name', ''),
                    'asset_type': holding.get('asset_type', '')
                }
        
        return results
    
    def get_asset_info(self, asset_symbol: str) -> Dict:
        """
        Get comprehensive asset information including current price
        
        Args:
            asset_symbol: The asset symbol
            
        Returns:
            Dictionary with asset information
        """
        try:
            ticker = yf.Ticker(asset_symbol)
            info = ticker.info
            
            # Extract key information
            asset_info = {
                'symbol': asset_symbol,
                'name': info.get('longName', info.get('shortName', asset_symbol)),
                'current_price': self.get_current_price(asset_symbol),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'previous_close': info.get('previousClose'),
                'open': info.get('open'),
                'change': info.get('regularMarketChange'),
                'change_percent': info.get('regularMarketChangePercent'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'exchange': info.get('exchange'),
                'last_updated': datetime.now().isoformat()
            }
            
            return asset_info
            
        except Exception as e:
            logger.error(f"Error fetching asset info for {asset_symbol}: {e}")
            return {
                'symbol': asset_symbol,
                'name': asset_symbol,
                'current_price': None,
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
    
    def get_market_summary(self, symbols: List[str]) -> Dict:
        """
        Get market summary for multiple assets
        
        Args:
            symbols: List of asset symbols
            
        Returns:
            Market summary data
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'assets': {},
            'total_assets': len(symbols),
            'successful_fetches': 0,
            'failed_fetches': 0
        }
        
        for symbol in symbols:
            try:
                asset_info = self.get_asset_info(symbol)
                summary['assets'][symbol] = asset_info
                
                if asset_info.get('current_price') is not None:
                    summary['successful_fetches'] += 1
                else:
                    summary['failed_fetches'] += 1
                    
            except Exception as e:
                logger.error(f"Error in market summary for {symbol}: {e}")
                summary['assets'][symbol] = {
                    'symbol': symbol,
                    'error': str(e)
                }
                summary['failed_fetches'] += 1
        
        return summary
    
    def clear_cache(self):
        """Clear the price cache"""
        self.cache.clear()
        logger.info("Price cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        now = datetime.now()
        valid_entries = 0
        expired_entries = 0
        
        for key, data in self.cache.items():
            if now - data['timestamp'] < timedelta(seconds=self.cache_duration):
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_duration_seconds': self.cache_duration
        }

# Global instance
price_service = PriceService()
