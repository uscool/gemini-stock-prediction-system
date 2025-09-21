"""
Historical Data Analysis for Commodity Markets
Scrapes and analyzes historical price data and trends
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import requests
import json
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommodityDataAnalyzer:
    """
    Analyzes historical commodity data and calculates trends
    """
    
    def __init__(self):
        self.config = Config()
        self.scaler = StandardScaler()
    
    async def analyze_asset_data(self, asset: str, timeframe_days: int = 30) -> Dict:
        """
        Analyze historical data for an asset (commodity or stock)
        
        Args:
            asset: Asset name (commodity or stock)
            timeframe_days: Number of days to analyze
            
        Returns:
            Dict containing comprehensive data analysis
        """
        try:
            logger.info(f"Starting data analysis for {asset} over {timeframe_days} days")
            
            # Get asset symbol and type
            symbol = self._get_symbol(asset)
            if not symbol:
                return self._create_error_result(asset, f"Unknown asset: {asset}")
            
            asset_type = self._get_asset_type(asset)
            
            # Fetch historical data
            historical_data = await self._fetch_historical_data(symbol, timeframe_days)
            if historical_data.empty:
                return self._create_error_result(asset, "No historical data available")
            
            # Perform comprehensive analysis with extended context
            price_analysis = self._analyze_price_trends(historical_data, timeframe_days)
            volume_analysis = self._analyze_volume_trends(historical_data, timeframe_days)
            volatility_analysis = self._analyze_volatility(historical_data, timeframe_days)
            technical_indicators = self._calculate_technical_indicators(historical_data, timeframe_days)
            trend_analysis = self._perform_trend_analysis(historical_data, timeframe_days)
            support_resistance = self._find_support_resistance_levels(historical_data, timeframe_days)
            
            # Calculate overall trend score
            trend_score = self._calculate_trend_score(
                price_analysis, volume_analysis, volatility_analysis, 
                technical_indicators, trend_analysis
            )
            
            # Generate summary statistics
            summary_stats = self._generate_summary_statistics(historical_data)
            
            return {
                'asset': asset,
                'asset_type': asset_type,
                'symbol': symbol,
                'timeframe_days': timeframe_days,
                'data_points': len(historical_data),
                'date_range': {
                    'start': historical_data.index[0].strftime('%Y-%m-%d'),
                    'end': historical_data.index[-1].strftime('%Y-%m-%d')
                },
                'current_price': float(historical_data['Close'].iloc[-1]),
                'price_analysis': price_analysis,
                'volume_analysis': volume_analysis,
                'volatility_analysis': volatility_analysis,
                'technical_indicators': technical_indicators,
                'trend_analysis': trend_analysis,
                'support_resistance': support_resistance,
                'trend_score': trend_score,
                'summary_statistics': summary_stats,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in data analysis for {commodity}: {e}")
            return self._create_error_result(commodity, str(e))
    
    def _get_symbol(self, asset: str) -> Optional[str]:
        """Get Yahoo Finance symbol for asset (commodity or stock)"""
        return self.config.ALL_SYMBOLS.get(asset.lower())
    
    def _get_asset_type(self, asset: str) -> str:
        """Determine if asset is a commodity or stock"""
        if asset.lower() in self.config.COMMODITY_SYMBOLS:
            return 'commodity'
        elif asset.lower() in self.config.STOCK_SYMBOLS:
            return 'stock'
        else:
            return 'unknown'
    
    async def _fetch_historical_data(self, symbol: str, timeframe_days: int) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance with extended lookback for better analysis"""
        try:
            end_date = datetime.now()
            
            # Calculate extended lookback period for better context
            # For short timeframes, look back much further for comparison
            if timeframe_days <= 7:
                lookback_multiplier = 15  # 7 days -> look at 105 days (3.5 months)
            elif timeframe_days <= 30:
                lookback_multiplier = 12  # 30 days -> look at 360 days (1 year)
            elif timeframe_days <= 90:
                lookback_multiplier = 8   # 90 days -> look at 720 days (2 years)
            else:
                lookback_multiplier = 5   # Longer periods -> 5x lookback
            
            total_lookback_days = timeframe_days * lookback_multiplier
            start_date = end_date - timedelta(days=total_lookback_days + 30)  # Extra buffer
            
            logger.info(f"Fetching {total_lookback_days} days of data for {timeframe_days}-day analysis")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"No data returned for symbol {symbol}")
                return pd.DataFrame()
            
            # Ensure we have the required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.warning(f"Missing columns for {symbol}: {missing_columns}")
                return pd.DataFrame()
            
            # Clean the data
            data = data.dropna()
            data = data[data['Volume'] > 0]  # Remove zero volume days
            
            logger.info(f"Fetched {len(data)} data points for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _analyze_price_trends(self, data: pd.DataFrame, timeframe_days: int) -> Dict:
        """Analyze price trends and movements with extended historical context"""
        try:
            prices = data['Close']
            
            # Calculate returns
            daily_returns = prices.pct_change().dropna()
            cumulative_returns = (1 + daily_returns).cumprod() - 1
            
            # Get recent period for decision-making vs full historical context
            recent_period = prices.tail(timeframe_days)
            
            # Price change analysis for the decision timeframe
            decision_period_change = float((recent_period.iloc[-1] / recent_period.iloc[0] - 1) * 100)
            
            # Full period change for context
            full_period_change = float((prices.iloc[-1] / prices.iloc[0] - 1) * 100)
            
            # Compare recent performance vs historical average
            # Split data into periods for comparison
            total_days = len(prices)
            period_size = max(timeframe_days, 7)  # Minimum 7-day periods
            
            # Calculate performance across multiple periods
            period_returns = []
            for i in range(0, total_days - period_size, period_size):
                period_data = prices.iloc[i:i+period_size]
                if len(period_data) >= period_size:
                    period_return = (period_data.iloc[-1] / period_data.iloc[0] - 1) * 100
                    period_returns.append(period_return)
            
            # Recent trend analysis with extended context
            recent_avg = float(recent_period.mean())
            historical_avg = float(prices.iloc[:-timeframe_days].mean()) if len(prices) > timeframe_days else recent_avg
            recent_trend = 'bullish' if recent_avg > historical_avg else 'bearish'
            
            # Enhanced momentum calculations
            momentum_short = float((prices.iloc[-1] / prices.iloc[-min(5, len(prices)//4)] - 1) * 100) if len(prices) >= 5 else 0.0
            momentum_medium = float((prices.iloc[-1] / prices.iloc[-min(20, len(prices)//2)] - 1) * 100) if len(prices) >= 20 else 0.0
            momentum_long = float((prices.iloc[-1] / prices.iloc[-min(60, len(prices)*3//4)] - 1) * 100) if len(prices) >= 60 else 0.0
            
            # Relative performance vs historical periods
            if period_returns:
                avg_period_return = np.mean(period_returns)
                recent_vs_historical = decision_period_change - avg_period_return
                performance_percentile = (len([r for r in period_returns if r < decision_period_change]) / len(period_returns)) * 100
            else:
                recent_vs_historical = 0.0
                performance_percentile = 50.0
            
            return {
                'decision_period_change': round(decision_period_change, 2),
                'full_period_change': round(full_period_change, 2),
                'recent_trend': recent_trend,
                'momentum_short_term': round(momentum_short, 2),
                'momentum_medium_term': round(momentum_medium, 2),
                'momentum_long_term': round(momentum_long, 2),
                'recent_vs_historical': round(recent_vs_historical, 2),
                'performance_percentile': round(performance_percentile, 1),
                'historical_periods_analyzed': len(period_returns),
                'daily_return_mean': round(float(daily_returns.mean() * 100), 4),
                'daily_return_std': round(float(daily_returns.std() * 100), 4),
                'cumulative_return': round(float(cumulative_returns.iloc[-1] * 100), 2),
                'max_drawdown': round(float((cumulative_returns.cummax() - cumulative_returns).max() * 100), 2),
                'total_data_points': len(prices),
                'analysis_depth_days': total_days
            }
            
        except Exception as e:
            logger.error(f"Error in price trend analysis: {e}")
            return {}
    
    def _analyze_volume_trends(self, data: pd.DataFrame, timeframe_days: int = 30) -> Dict:
        """Analyze trading volume trends"""
        try:
            volume = data['Volume']
            
            # Volume statistics
            avg_volume = float(volume.mean())
            recent_volume = float(volume.tail(5).mean())
            volume_trend = 'increasing' if recent_volume > avg_volume else 'decreasing'
            
            # Volume-price correlation
            price_volume_corr = float(data['Close'].corr(data['Volume']))
            
            # Volume momentum
            volume_momentum = float((recent_volume / avg_volume - 1) * 100)
            
            return {
                'average_volume': int(avg_volume),
                'recent_average_volume': int(recent_volume),
                'volume_trend': volume_trend,
                'volume_momentum': round(volume_momentum, 2),
                'price_volume_correlation': round(price_volume_corr, 3),
                'volume_volatility': round(float(volume.std() / avg_volume * 100), 2)
            }
            
        except Exception as e:
            logger.error(f"Error in volume trend analysis: {e}")
            return {}
    
    def _analyze_volatility(self, data: pd.DataFrame, timeframe_days: int = 30) -> Dict:
        """Analyze price volatility"""
        try:
            prices = data['Close']
            returns = prices.pct_change().dropna()
            
            # Calculate different volatility measures
            daily_vol = float(returns.std())
            annualized_vol = float(daily_vol * np.sqrt(252))  # Assuming 252 trading days
            
            # Rolling volatility
            rolling_vol_20d = returns.rolling(window=20).std()
            current_vol = float(rolling_vol_20d.iloc[-1]) if not rolling_vol_20d.empty else daily_vol
            
            # Volatility trend
            recent_vol = float(rolling_vol_20d.tail(5).mean()) if len(rolling_vol_20d) >= 5 else current_vol
            historical_vol = float(rolling_vol_20d.mean()) if not rolling_vol_20d.empty else daily_vol
            
            vol_trend = 'increasing' if recent_vol > historical_vol else 'decreasing'
            
            # High-low range analysis
            high_low_range = ((data['High'] - data['Low']) / data['Close']).mean()
            
            return {
                'daily_volatility': round(daily_vol * 100, 4),
                'annualized_volatility': round(annualized_vol * 100, 2),
                'current_volatility_20d': round(current_vol * 100, 4),
                'volatility_trend': vol_trend,
                'average_daily_range': round(float(high_low_range * 100), 2),
                'volatility_percentile': round(float((current_vol - rolling_vol_20d.min()) / 
                                                  (rolling_vol_20d.max() - rolling_vol_20d.min()) * 100), 1) 
                                                  if len(rolling_vol_20d) > 1 else 50.0
            }
            
        except Exception as e:
            logger.error(f"Error in volatility analysis: {e}")
            return {}
    
    def _calculate_technical_indicators(self, data: pd.DataFrame, timeframe_days: int = 30) -> Dict:
        """Calculate technical indicators"""
        try:
            prices = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            
            indicators = {}
            
            # Moving averages
            if len(prices) >= 5:
                indicators['sma_5'] = float(prices.rolling(window=5).mean().iloc[-1])
            if len(prices) >= 10:
                indicators['sma_10'] = float(prices.rolling(window=10).mean().iloc[-1])
            if len(prices) >= 20:
                indicators['sma_20'] = float(prices.rolling(window=20).mean().iloc[-1])
                indicators['ema_20'] = float(prices.ewm(span=20).mean().iloc[-1])
            
            current_price = float(prices.iloc[-1])
            
            # Moving average signals
            if 'sma_20' in indicators:
                indicators['price_vs_sma_20'] = 'above' if current_price > indicators['sma_20'] else 'below'
                indicators['sma_20_slope'] = self._calculate_slope(prices.rolling(window=20).mean().tail(5))
            
            # RSI (Relative Strength Index)
            if len(prices) >= 14:
                rsi = self._calculate_rsi(prices, 14)
                indicators['rsi'] = round(float(rsi.iloc[-1]), 2)
                
                if indicators['rsi'] > 70:
                    indicators['rsi_signal'] = 'overbought'
                elif indicators['rsi'] < 30:
                    indicators['rsi_signal'] = 'oversold'
                else:
                    indicators['rsi_signal'] = 'neutral'
            
            # MACD
            if len(prices) >= 26:
                macd_line, signal_line, histogram = self._calculate_macd(prices)
                indicators['macd'] = round(float(macd_line.iloc[-1]), 4)
                indicators['macd_signal'] = round(float(signal_line.iloc[-1]), 4)
                indicators['macd_histogram'] = round(float(histogram.iloc[-1]), 4)
                indicators['macd_trend'] = 'bullish' if indicators['macd'] > indicators['macd_signal'] else 'bearish'
            
            # Bollinger Bands
            if len(prices) >= 20:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(prices, 20, 2)
                indicators['bb_upper'] = round(float(bb_upper.iloc[-1]), 4)
                indicators['bb_middle'] = round(float(bb_middle.iloc[-1]), 4)
                indicators['bb_lower'] = round(float(bb_lower.iloc[-1]), 4)
                
                bb_position = (current_price - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
                indicators['bb_position'] = round(bb_position, 3)
                
                if bb_position > 0.8:
                    indicators['bb_signal'] = 'near_upper'
                elif bb_position < 0.2:
                    indicators['bb_signal'] = 'near_lower'
                else:
                    indicators['bb_signal'] = 'middle'
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20, num_std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        rolling_mean = prices.rolling(window=window).mean()
        rolling_std = prices.rolling(window=window).std()
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        return upper_band, rolling_mean, lower_band
    
    def _calculate_slope(self, series: pd.Series) -> str:
        """Calculate slope trend of a series"""
        if len(series) < 2:
            return 'neutral'
        
        x = np.arange(len(series))
        y = series.values
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 0.001:
            return 'upward'
        elif slope < -0.001:
            return 'downward'
        else:
            return 'neutral'
    
    def _perform_trend_analysis(self, data: pd.DataFrame, timeframe_days: int = 30) -> Dict:
        """Perform comprehensive trend analysis"""
        try:
            prices = data['Close']
            
            # Linear regression trend
            x = np.arange(len(prices)).reshape(-1, 1)
            y = prices.values
            
            model = LinearRegression()
            model.fit(x, y)
            trend_slope = float(model.coef_[0])
            r_squared = float(r2_score(y, model.predict(x)))
            
            # Trend classification
            if trend_slope > 0.01:
                trend_direction = 'strong_uptrend'
            elif trend_slope > 0.001:
                trend_direction = 'uptrend'
            elif trend_slope < -0.01:
                trend_direction = 'strong_downtrend'
            elif trend_slope < -0.001:
                trend_direction = 'downtrend'
            else:
                trend_direction = 'sideways'
            
            # Trend strength based on R-squared
            if r_squared > 0.8:
                trend_strength = 'very_strong'
            elif r_squared > 0.6:
                trend_strength = 'strong'
            elif r_squared > 0.4:
                trend_strength = 'moderate'
            else:
                trend_strength = 'weak'
            
            # Higher highs and higher lows analysis
            highs = data['High']
            lows = data['Low']
            
            recent_high = float(highs.tail(10).max())
            previous_high = float(highs.iloc[-20:-10].max()) if len(highs) >= 20 else recent_high
            
            recent_low = float(lows.tail(10).min())
            previous_low = float(lows.iloc[-20:-10].min()) if len(lows) >= 20 else recent_low
            
            higher_highs = recent_high > previous_high
            higher_lows = recent_low > previous_low
            
            if higher_highs and higher_lows:
                pattern = 'bullish_trend'
            elif not higher_highs and not higher_lows:
                pattern = 'bearish_trend'
            else:
                pattern = 'mixed_signals'
            
            return {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'trend_slope': round(trend_slope, 6),
                'r_squared': round(r_squared, 3),
                'pattern': pattern,
                'higher_highs': higher_highs,
                'higher_lows': higher_lows
            }
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return {}
    
    def _find_support_resistance_levels(self, data: pd.DataFrame, timeframe_days: int = 30) -> Dict:
        """Find support and resistance levels"""
        try:
            highs = data['High']
            lows = data['Low']
            closes = data['Close']
            
            # Find recent support and resistance levels
            recent_data = data.tail(50)  # Last 50 days
            
            # Resistance levels (recent highs)
            resistance_levels = []
            for i in range(2, len(recent_data) - 2):
                if (recent_data['High'].iloc[i] > recent_data['High'].iloc[i-1] and 
                    recent_data['High'].iloc[i] > recent_data['High'].iloc[i+1] and
                    recent_data['High'].iloc[i] > recent_data['High'].iloc[i-2] and
                    recent_data['High'].iloc[i] > recent_data['High'].iloc[i+2]):
                    resistance_levels.append(float(recent_data['High'].iloc[i]))
            
            # Support levels (recent lows)
            support_levels = []
            for i in range(2, len(recent_data) - 2):
                if (recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i-1] and 
                    recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i+1] and
                    recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i-2] and
                    recent_data['Low'].iloc[i] < recent_data['Low'].iloc[i+2]):
                    support_levels.append(float(recent_data['Low'].iloc[i]))
            
            current_price = float(closes.iloc[-1])
            
            # Find nearest support and resistance
            resistance_levels = sorted(set(resistance_levels), reverse=True)
            support_levels = sorted(set(support_levels), reverse=True)
            
            nearest_resistance = None
            nearest_support = None
            
            for level in resistance_levels:
                if level > current_price:
                    nearest_resistance = level
                    break
            
            for level in support_levels:
                if level < current_price:
                    nearest_support = level
                    break
            
            return {
                'current_price': round(current_price, 4),
                'nearest_resistance': round(nearest_resistance, 4) if nearest_resistance else None,
                'nearest_support': round(nearest_support, 4) if nearest_support else None,
                'resistance_levels': [round(level, 4) for level in resistance_levels[:5]],
                'support_levels': [round(level, 4) for level in support_levels[:5]],
                'distance_to_resistance': round(((nearest_resistance - current_price) / current_price * 100), 2) if nearest_resistance else None,
                'distance_to_support': round(((current_price - nearest_support) / current_price * 100), 2) if nearest_support else None
            }
            
        except Exception as e:
            logger.error(f"Error finding support/resistance levels: {e}")
            return {}
    
    def _calculate_trend_score(self, price_analysis: Dict, volume_analysis: Dict, 
                             volatility_analysis: Dict, technical_indicators: Dict, 
                             trend_analysis: Dict) -> float:
        """Calculate overall trend score (0-100)"""
        try:
            score = 50.0  # Start neutral
            
            # Price trend component (30% weight)
            if price_analysis.get('recent_trend') == 'bullish':
                score += 10
            elif price_analysis.get('recent_trend') == 'bearish':
                score -= 10
            
            momentum_5d = price_analysis.get('momentum_5d', 0)
            score += min(max(momentum_5d * 0.5, -10), 10)  # Cap at ±10
            
            # Technical indicators component (25% weight)
            if technical_indicators.get('rsi_signal') == 'overbought':
                score -= 5
            elif technical_indicators.get('rsi_signal') == 'oversold':
                score += 5
            
            if technical_indicators.get('macd_trend') == 'bullish':
                score += 7
            elif technical_indicators.get('macd_trend') == 'bearish':
                score -= 7
            
            if technical_indicators.get('price_vs_sma_20') == 'above':
                score += 5
            elif technical_indicators.get('price_vs_sma_20') == 'below':
                score -= 5
            
            # Trend analysis component (25% weight)
            trend_direction = trend_analysis.get('trend_direction', 'sideways')
            trend_strength = trend_analysis.get('trend_strength', 'weak')
            
            direction_scores = {
                'strong_uptrend': 12,
                'uptrend': 8,
                'sideways': 0,
                'downtrend': -8,
                'strong_downtrend': -12
            }
            
            strength_multipliers = {
                'very_strong': 1.0,
                'strong': 0.8,
                'moderate': 0.6,
                'weak': 0.4
            }
            
            trend_score = direction_scores.get(trend_direction, 0)
            trend_multiplier = strength_multipliers.get(trend_strength, 0.5)
            score += trend_score * trend_multiplier
            
            # Volume component (10% weight)
            if volume_analysis.get('volume_trend') == 'increasing':
                score += 3
            elif volume_analysis.get('volume_trend') == 'decreasing':
                score -= 2
            
            # Volatility component (10% weight)
            vol_trend = volatility_analysis.get('volatility_trend', 'neutral')
            if vol_trend == 'increasing':
                score -= 2  # High volatility is generally negative
            elif vol_trend == 'decreasing':
                score += 2
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            return round(score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating trend score: {e}")
            return 50.0
    
    def _generate_summary_statistics(self, data: pd.DataFrame) -> Dict:
        """Generate summary statistics"""
        try:
            prices = data['Close']
            volume = data['Volume']
            
            return {
                'period_high': round(float(data['High'].max()), 4),
                'period_low': round(float(data['Low'].min()), 4),
                'average_price': round(float(prices.mean()), 4),
                'median_price': round(float(prices.median()), 4),
                'price_std': round(float(prices.std()), 4),
                'total_volume': int(volume.sum()),
                'average_volume': int(volume.mean()),
                'trading_days': len(data),
                'price_range': round(float(data['High'].max() - data['Low'].min()), 4),
                'current_vs_high': round(float((prices.iloc[-1] / data['High'].max() - 1) * 100), 2),
                'current_vs_low': round(float((prices.iloc[-1] / data['Low'].min() - 1) * 100), 2)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary statistics: {e}")
            return {}
    
    def _create_error_result(self, commodity: str, error_message: str) -> Dict:
        """Create error result"""
        return {
            'commodity': commodity,
            'symbol': None,
            'timeframe_days': 0,
            'data_points': 0,
            'error': error_message,
            'analysis_timestamp': datetime.now().isoformat()
        }
