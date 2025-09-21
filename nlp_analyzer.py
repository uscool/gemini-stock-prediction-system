"""
FinBERT-based NLP Analysis for Commodity Market Sentiment - Scrapy Only Version
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging
import nltk
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from config import Config

# Scrapy integration
try:
    from simple_scrapy_runner import run_simple_scraping
    SCRAPY_AVAILABLE = True
except ImportError:
    SCRAPY_AVAILABLE = False
    logging.error("Scrapy is required for news collection. Please install scrapy: pip install scrapy")

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommodityNLPAnalyzer:
    """NLP Analyzer using FinBERT for sentiment analysis with Scrapy for news collection"""
    
    def __init__(self, gemini_advisor=None, website_logger=None):
        self.config = Config()
        self.tokenizer = None
        self.model = None
        self.gemini_advisor = gemini_advisor
        self.website_logger = website_logger
        self.cache = {}  # Simple in-memory cache
        self.executor = ThreadPoolExecutor(max_workers=8)  # For CPU-bound tasks
        self._load_finbert_model()
    
    def _load_finbert_model(self):
        """Load FinBERT model for sentiment analysis"""
        try:
            logger.info("Loading FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.FINBERT_MODEL)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.config.FINBERT_MODEL)
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading FinBERT model: {e}")
            logger.warning("Continuing with fallback sentiment analysis...")
            self.tokenizer = None
            self.model = None
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
    
    async def analyze_asset_sentiment(self, asset: str, articles: List[Dict]) -> Dict:
        """Analyze sentiment of articles for a specific asset"""
        if not articles:
            return self._create_error_sentiment_result(asset, "No articles found for analysis")
        
        try:
            logger.info(f"Starting sentiment analysis for {asset} over {len(articles)} articles")
            
            # Process articles for sentiment analysis
            sentiment_results = []
            for i, article in enumerate(articles):
                try:
                    # Combine title and content for analysis
                    text = f"{article.get('title', '')} {article.get('content', '')}"
                    
                    if len(text.strip()) < 10:  # Skip very short texts
                        continue
                    
                    # Analyze sentiment
                    sentiment = self._analyze_text_sentiment(text)
                    sentiment['article_index'] = i
                    sentiment['title'] = article.get('title', '')
                    sentiment['source'] = article.get('source', '')
                    sentiment['date'] = article.get('date', datetime.now())
                    sentiment['url'] = article.get('url', '')
                    
                    sentiment_results.append(sentiment)
                    
                except Exception as e:
                    logger.warning(f"Error analyzing article {i}: {e}")
                    continue
            
            if not sentiment_results:
                return self._create_error_sentiment_result(asset, "No valid articles for sentiment analysis")
            
            # Calculate aggregate sentiment
            aggregate_sentiment = self._calculate_aggregate_sentiment(sentiment_results)
            
            # Normalize score to 0-100 scale
            normalized_score = max(0, min(100, 50 + (aggregate_sentiment['score'] * 50)))
            
            result = {
                'asset': asset,
                'total_articles': len(articles),
                'analyzed_articles': len(sentiment_results),
                'sentiment_breakdown': aggregate_sentiment['sentiment_breakdown'],
                'aggregate_sentiment': aggregate_sentiment,
                'normalized_score': normalized_score,
                'individual_results': sentiment_results,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Sentiment analysis completed for {asset}: {aggregate_sentiment['label']} (score: {aggregate_sentiment['score']:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for {asset}: {e}")
            return self._create_error_sentiment_result(asset, str(e))
    
    async def _collect_asset_news(self, asset: str, timeframe_days: int) -> List[Dict]:
        """Collect news articles related to the asset using Scrapy"""
        if not SCRAPY_AVAILABLE:
            raise ImportError("Scrapy is required for news collection. Please install scrapy: pip install scrapy")
        
        logger.info(f"Using Scrapy for news collection for {asset}")
        articles = await run_simple_scraping(
            search_term=asset,
            asset_type='commodity',
            days_back=timeframe_days,
            max_articles=100
        )
        
        logger.info(f"Scrapy collected {len(articles)} articles for {asset}")
        return articles
    
    @lru_cache(maxsize=100)
    def _get_cached_search_terms(self, asset: str) -> List[str]:
        """Get cached search terms to avoid regeneration"""
        return self._generate_search_terms(asset)
    
    async def _get_intelligent_search_terms(self, asset: str, timeframe_days: int) -> List[str]:
        """Get intelligent search terms from Gemini AI"""
        try:
            # Use cached search terms first
            cached_terms = self._get_cached_search_terms(asset)
            
            # Use provided Gemini advisor if available and not using cache
            if self.gemini_advisor and timeframe_days > 7:  # Only use AI for longer timeframes
                try:
                    search_terms = await asyncio.wait_for(
                        self.gemini_advisor.generate_search_terms(asset, timeframe_days),
                        timeout=5.0  # 5 second timeout for AI generation
                    )
                    
                    logger.info(f"Using AI-generated search terms for {asset}: {search_terms[:3]}..." + 
                           f" ({len(search_terms)} total terms)")
                
                    return search_terms[:5]  # Limit to 5 terms for speed
                except asyncio.TimeoutError:
                    logger.warning(f"AI search term generation timed out for {asset}, using cached terms")
                    return cached_terms
            else:
                logger.info(f"Using cached search terms for {asset}")
                return cached_terms
            
        except Exception as e:
            logger.warning(f"Error getting search terms for {asset}: {e}")
            logger.info(f"Falling back to basic search terms")
            return [asset]  # Minimal fallback
    
    def _generate_search_terms(self, asset: str) -> List[str]:
        """Generate search terms for asset news"""
        base_terms = [asset, asset.replace('_', ' ')]
        
        # Add asset-specific terms (optimized list)
        asset_terms = {
            'gold': ['gold price', 'precious metals'],
            'silver': ['silver price', 'precious metals'],
            'crude_oil': ['oil price', 'energy market'],
            'natural_gas': ['natural gas', 'energy market'],
            'copper': ['copper price', 'industrial metals'],
            'wheat': ['wheat price', 'agricultural commodities'],
            'corn': ['corn price', 'agricultural commodities'],
            'soybeans': ['soybean price', 'agricultural commodities'],
            'coffee': ['coffee price', 'soft commodities'],
            'sugar': ['sugar price', 'soft commodities'],
            'cotton': ['cotton price', 'soft commodities'],
            'platinum': ['platinum price', 'precious metals'],
            'palladium': ['palladium price', 'precious metals'],
            'aluminum': ['aluminum price', 'industrial metals'],
            'zinc': ['zinc price', 'industrial metals']
        }
        
        # Get asset-specific terms
        specific_terms = asset_terms.get(asset, [])
        
        # Combine and limit terms
        all_terms = base_terms + specific_terms[:2]  # Limit to 2 specific terms
        return all_terms[:4]  # Limit total to 4 terms
    
    def _get_cache_key(self, source_url: str, search_term: str, timeframe_days: int) -> str:
        """Generate cache key for scraping results"""
        key_data = f"{source_url}:{search_term}:{timeframe_days}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title_normalized = article['title'].lower().strip()
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_articles.append(article)
        
        return unique_articles
    
    def _calculate_aggregate_sentiment(self, sentiment_results: List[Dict]) -> Dict:
        """Calculate aggregate sentiment from individual results"""
        if not sentiment_results:
            return {'label': 'neutral', 'confidence': 0.0, 'score': 0.0}
        
        # Weight recent articles more heavily
        total_weighted_score = 0.0
        total_weight = 0.0
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for i, result in enumerate(sentiment_results):
            # More recent articles get higher weight
            weight = 1.0 / (i + 1)  # Decreasing weight for older articles
            total_weighted_score += result['score'] * weight
            total_weight += weight
            sentiment_counts[result['sentiment']] += 1
        
        avg_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Determine overall label
        if avg_score > self.config.SENTIMENT_THRESHOLD:
            overall_label = 'positive'
        elif avg_score < -self.config.SENTIMENT_THRESHOLD:
            overall_label = 'negative'
        else:
            overall_label = 'neutral'
        
        # Calculate confidence based on consistency
        total_articles = len(sentiment_results)
        max_count = max(sentiment_counts.values())
        confidence = max_count / total_articles if total_articles > 0 else 0.0
        
        return {
            'label': overall_label,
            'confidence': confidence,
            'score': avg_score,
            'total_articles': total_articles,
            'sentiment_breakdown': sentiment_counts
        }
    
    def _create_error_sentiment_result(self, asset: str, error_message: str) -> Dict:
        """Create error sentiment result"""
        return {
            'asset': asset,
            'aggregate_sentiment': {'label': 'neutral', 'confidence': 0.0, 'score': 0.0},
            'normalized_score': 50.0,
            'individual_results': [],
            'analysis_timestamp': datetime.now().isoformat(),
            'error': error_message
        }
    
    def _analyze_text_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of a single text using FinBERT or fallback"""
        if self.model and self.tokenizer:
            return self._analyze_with_finbert(text)
        else:
            return self._analyze_with_fallback(text)
    
    def _analyze_with_finbert(self, text: str) -> Dict:
        """Analyze sentiment using FinBERT model"""
        try:
            # Tokenize and truncate if necessary
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # Get model prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Get sentiment labels and scores
            labels = ['negative', 'neutral', 'positive']
            scores = predictions[0].tolist()
            
            # Find the highest scoring sentiment
            max_score_idx = scores.index(max(scores))
            sentiment = labels[max_score_idx]
            confidence = scores[max_score_idx]
            
            # Convert to -1 to 1 scale
            score = (max_score_idx - 1) * confidence  # -1 for negative, 0 for neutral, 1 for positive
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'score': score,
                'raw_scores': dict(zip(labels, scores))
            }
            
        except Exception as e:
            logger.warning(f"FinBERT analysis failed: {e}, using fallback")
            return self._analyze_with_fallback(text)
    
    def _analyze_with_fallback(self, text: str) -> Dict:
        """Fallback sentiment analysis using simple keyword matching"""
        positive_keywords = [
            'bullish', 'rise', 'increase', 'gain', 'up', 'positive', 'strong', 'growth',
            'surge', 'rally', 'boost', 'improve', 'better', 'optimistic', 'recovery'
        ]
        negative_keywords = [
            'bearish', 'fall', 'decrease', 'drop', 'down', 'negative', 'weak', 'decline',
            'crash', 'plunge', 'worry', 'concern', 'risk', 'uncertainty', 'volatile'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            score = min(0.5, positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = 'negative'
            score = max(-0.5, -negative_count * 0.1)
        else:
            sentiment = 'neutral'
            score = 0.0
        
        return {
            'sentiment': sentiment,
            'confidence': 0.6,  # Lower confidence for fallback
            'score': score,
            'method': 'fallback'
        }
