"""
Gemini AI Integration for Commodity Trading Decisions
Analyzes sentiment and data to make buy/sell/hold recommendations
"""
import google.generativeai as genai
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from config import Config
from models import db, Portfolio, Holding
from auth_service import AuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiCommodityAdvisor:
    """
    Uses Gemini AI to make commodity trading decisions based on NLP sentiment and data analysis
    """
    
    def __init__(self):
        self.config = Config()
        self.auth_service = AuthService()
        self._initialize_gemini()
        
    def _initialize_gemini(self):
        """Initialize Gemini AI"""
        try:
            if not self.config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not found in configuration")
            
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            # Configure the model
            generation_config = {
                "temperature": 0.3,  # Lower temperature for more consistent financial advice
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info("Gemini AI initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Gemini AI: {e}")
            raise
    
    def get_portfolio_context(self, user_email: str, asset_symbol: str = None, portfolio_id: int = None) -> Dict:
        """
        Get portfolio context for a user, optionally filtered by asset or portfolio
        
        Args:
            user_email: User's email address
            asset_symbol: Optional asset symbol to filter by
            portfolio_id: Optional portfolio ID to filter by
            
        Returns:
            Dict containing portfolio context
        """
        try:
            # Get user by email
            user = self.auth_service.get_user_by_email(user_email)
            if not user:
                logger.warning(f"User not found for email: {user_email}")
                return {"error": "User not found"}
            
            # Get portfolios for the user (filter by portfolio_id if provided)
            query = Portfolio.query.filter_by(
                user_id=user.id, 
                is_active=True
            )
            
            if portfolio_id:
                query = query.filter_by(id=portfolio_id)
            
            portfolios = query.all()
            
            if not portfolios:
                logger.info(f"No portfolios found for user: {user_email}")
                return {"portfolios": [], "total_value": 0, "asset_exposure": {}}
            
            portfolio_context = {
                "portfolios": [],
                "total_value": 0,
                "asset_exposure": {},
                "diversification_score": 0
            }
            
            all_holdings = []
            
            for portfolio in portfolios:
                # Get holdings for this portfolio
                holdings = Holding.query.filter_by(
                    portfolio_id=portfolio.id,
                    is_active=True
                ).all()
                
                portfolio_data = {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "description": portfolio.description,
                    "holdings": [],
                    "total_value": 0,
                    "total_cost": 0,
                    "gain_loss": 0,
                    "gain_loss_percent": 0
                }
                
                for holding in holdings:
                    holding_data = {
                        "asset_symbol": holding.asset_symbol,
                        "asset_name": holding.asset_name,
                        "quantity": float(holding.quantity),
                        "avg_cost": float(holding.avg_cost_per_share),
                        "current_price": float(holding.current_price) if holding.current_price else None,
                        "current_value": float(holding.current_value),
                        "gain_loss": float(holding.gain_loss),
                        "gain_loss_percent": float(holding.gain_loss_percent)
                    }
                    
                    portfolio_data["holdings"].append(holding_data)
                    portfolio_data["total_value"] += holding_data["current_value"]
                    portfolio_data["total_cost"] += holding_data["quantity"] * holding_data["avg_cost"]
                    
                    # Track asset exposure across all portfolios
                    if holding.asset_symbol in portfolio_context["asset_exposure"]:
                        portfolio_context["asset_exposure"][holding.asset_symbol] += holding_data["current_value"]
                    else:
                        portfolio_context["asset_exposure"][holding.asset_symbol] = holding_data["current_value"]
                    
                    all_holdings.append(holding_data)
                
                # Calculate portfolio-level metrics
                if portfolio_data["total_cost"] > 0:
                    portfolio_data["gain_loss"] = portfolio_data["total_value"] - portfolio_data["total_cost"]
                    portfolio_data["gain_loss_percent"] = (portfolio_data["gain_loss"] / portfolio_data["total_cost"]) * 100
                
                portfolio_context["portfolios"].append(portfolio_data)
                portfolio_context["total_value"] += portfolio_data["total_value"]
            
            # Calculate diversification score (number of unique assets / total value)
            unique_assets = len(portfolio_context["asset_exposure"])
            if portfolio_context["total_value"] > 0:
                portfolio_context["diversification_score"] = min(unique_assets * 10, 100)  # Max 100
            
            # Check if user has exposure to the specific asset being analyzed
            if asset_symbol:
                asset_exposure = portfolio_context["asset_exposure"].get(asset_symbol, 0)
                portfolio_context["current_asset_exposure"] = {
                    "symbol": asset_symbol,
                    "value": asset_exposure,
                    "percentage": (asset_exposure / portfolio_context["total_value"] * 100) if portfolio_context["total_value"] > 0 else 0,
                    "has_position": asset_exposure > 0
                }
            
            logger.info(f"Retrieved portfolio context for {user_email}: {len(portfolios)} portfolios, ${portfolio_context['total_value']:.2f} total value")
            return portfolio_context
            
        except Exception as e:
            logger.error(f"Error getting portfolio context for {user_email}: {e}")
            return {"error": str(e)}
    
    async def make_trading_decision(self, commodity: str, sentiment_analysis: Dict, 
                                  data_analysis: Dict, timeframe_days: int, risk_tolerance: str = 'moderate',
                                  user_email: str = None, portfolio_context: Dict = None) -> Dict:
        """
        Make a trading decision based on sentiment and data analysis
        
        Args:
            commodity: Commodity name
            sentiment_analysis: Results from NLP sentiment analysis
            data_analysis: Results from historical data analysis
            timeframe_days: Analysis timeframe
            risk_tolerance: User's risk tolerance level
            user_email: User's email for portfolio context (optional)
            portfolio_context: Pre-fetched portfolio context (optional)
            
        Returns:
            Dict containing trading decision and reasoning
        """
        try:
            logger.info(f"Making trading decision for {commodity}")
            
            # Get portfolio context if user_email is provided and portfolio_context is not already provided
            if user_email and not portfolio_context:
                logger.info(f"Fetching portfolio context for user: {user_email}")
                portfolio_context = self.get_portfolio_context(user_email, commodity)
                if "error" in portfolio_context:
                    logger.warning(f"Could not get portfolio context: {portfolio_context['error']}")
                    portfolio_context = None
                else:
                    logger.info(f"Successfully retrieved portfolio context for {user_email}")
            elif not user_email:
                logger.info(f"No user email provided - analysis will proceed without portfolio context")
            
            # Create comprehensive prompt
            prompt = self._create_analysis_prompt(
                commodity, sentiment_analysis, data_analysis, timeframe_days, risk_tolerance, portfolio_context
            )
            
            # Get Gemini's analysis
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("Empty response from Gemini AI")
            
            # Parse the response
            decision_data = self._parse_gemini_response(response.text, commodity)
            
            # Add metadata
            decision_data.update({
                'commodity': commodity,
                'timeframe_days': timeframe_days,
                'analysis_timestamp': datetime.now().isoformat(),
                'sentiment_score': sentiment_analysis.get('normalized_score', 50.0),
                'trend_score': data_analysis.get('trend_score', 50.0),
                'current_price': data_analysis.get('current_price', 0.0)
            })
            
            logger.info(f"Trading decision for {commodity}: {decision_data.get('decision', 'UNKNOWN')}")
            return decision_data
            
        except Exception as e:
            logger.error(f"Error making trading decision for {commodity}: {e}")
            return self._create_error_decision(commodity, str(e))
    
    def _create_analysis_prompt(self, commodity: str, sentiment_analysis: Dict, 
                               data_analysis: Dict, timeframe_days: int, risk_tolerance: str = 'moderate',
                               portfolio_context: Dict = None) -> str:
        """Create comprehensive prompt for Gemini analysis"""
        
        # Extract key metrics
        sentiment_score = sentiment_analysis.get('normalized_score', 50.0)
        sentiment_label = sentiment_analysis.get('aggregate_sentiment', {}).get('label', 'neutral')
        sentiment_confidence = sentiment_analysis.get('aggregate_sentiment', {}).get('confidence', 0.0)
        total_articles = sentiment_analysis.get('total_articles', 0)
        
        trend_score = data_analysis.get('trend_score', 50.0)
        current_price = data_analysis.get('current_price', 0.0)
        
        # Get enhanced price analysis data
        price_analysis_data = data_analysis.get('price_analysis', {})
        decision_period_change = price_analysis_data.get('decision_period_change', 0.0)
        full_period_change = price_analysis_data.get('full_period_change', 0.0)
        performance_percentile = price_analysis_data.get('performance_percentile', 50.0)
        historical_periods = price_analysis_data.get('historical_periods_analyzed', 0)
        analysis_depth = price_analysis_data.get('analysis_depth_days', 0)
        
        trend_direction = data_analysis.get('trend_analysis', {}).get('trend_direction', 'sideways')
        volatility = data_analysis.get('volatility_analysis', {}).get('annualized_volatility', 0.0)
        
        # Technical indicators
        technical = data_analysis.get('technical_indicators', {})
        rsi = technical.get('rsi', 50)
        macd_trend = technical.get('macd_trend', 'neutral')
        
        prompt = f"""
You are an expert commodity trading advisor analyzing {commodity.upper()} for investment decisions.

ANALYSIS PERIOD: {timeframe_days} days (with {analysis_depth} days of historical context)

SENTIMENT ANALYSIS:
- Sentiment Score: {sentiment_score}/100 (where 0=very negative, 50=neutral, 100=very positive)
- Overall Sentiment: {sentiment_label} (confidence: {sentiment_confidence:.2f})
- Articles Analyzed: {total_articles}
- Sentiment Distribution: {sentiment_analysis.get('sentiment_breakdown', {})}

ENHANCED PRICE ANALYSIS (Extended Historical Context):
- Current Price: ${current_price:.4f}
- Decision Period Change: {decision_period_change:.2f}% (last {timeframe_days} days)
- Full Historical Change: {full_period_change:.2f}% (over {analysis_depth} days)
- Performance vs Historical: {performance_percentile:.1f}th percentile (better than {performance_percentile:.1f}% of similar periods)
- Historical Periods Analyzed: {historical_periods} comparable periods
- Trend Direction: {trend_direction}
- Trend Score: {trend_score}/100 (where 0=strong bearish, 50=neutral, 100=strong bullish)
- Annualized Volatility: {volatility:.2f}%

TECHNICAL INDICATORS:
- RSI: {rsi} (30=oversold, 70=overbought)
- MACD Trend: {macd_trend}

VOLUME & MOMENTUM:
- Volume Trend: {data_analysis.get('volume_analysis', {}).get('volume_trend', 'neutral')}
- Short-term Momentum: {price_analysis_data.get('momentum_short_term', 0):.2f}%
- Medium-term Momentum: {price_analysis_data.get('momentum_medium_term', 0):.2f}%
- Long-term Momentum: {price_analysis_data.get('momentum_long_term', 0):.2f}%
- Recent vs Historical Performance: {price_analysis_data.get('recent_vs_historical', 0):+.2f}% difference

SUPPORT & RESISTANCE:
- Nearest Support: ${data_analysis.get('support_resistance', {}).get('nearest_support', 'N/A')}
- Nearest Resistance: ${data_analysis.get('support_resistance', {}).get('nearest_resistance', 'N/A')}

USER RISK TOLERANCE: {risk_tolerance.upper()}
{self._get_risk_tolerance_description(risk_tolerance)}

{self._get_portfolio_context_section(portfolio_context, commodity)}

TASK: Provide a comprehensive trading recommendation in the following JSON format:

{{
    "decision": "BUY" | "SELL" | "HOLD",
    "confidence": 0.0-1.0,
    "target_price": "price target if BUY/SELL, null if HOLD",
    "stop_loss": "stop loss level if BUY/SELL, null if HOLD",
    "position_size": "SMALL" | "MEDIUM" | "LARGE",
    "time_horizon": "SHORT" | "MEDIUM" | "LONG",
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "key_factors": ["list", "of", "key", "decision", "factors"],
    "reasoning": "detailed explanation of the decision",
    "risks": "key risks to consider",
    "market_outlook": "overall market perspective for this commodity",
    "portfolio_adjustments": {{
        "current_position_action": "INCREASE" | "DECREASE" | "MAINTAIN" | "CLOSE" | "N/A",
        "recommended_position_size": "percentage of portfolio (e.g., '5%', '10%', '15%')",
        "position_change_rationale": "explanation for position adjustment",
        "rebalancing_impact": "how this affects overall portfolio balance",
        "risk_impact": "impact on portfolio risk profile",
        "sell_recommendations": "specific recommendations for selling existing positions to fund this trade",
        "total_portfolio_value": "current total portfolio value",
        "diversification_score": "portfolio diversification score (0-100)",
        "asset_exposure": "current exposure to this asset type/sector"
    }},
    "email_subject": "Professional email subject for broker",
    "email_body": "Professional email body for broker with specific trade instructions and position recommendations"
}}

GUIDELINES:
1. Consider both sentiment and technical analysis equally
2. Factor in volatility and risk management
3. IMPORTANT: Adjust recommendations based on user's risk tolerance level
4. Consider current market conditions and economic factors
5. Provide specific, actionable recommendations
6. Include proper risk management (stop-loss, position sizing) appropriate for risk tolerance
7. Write professional email content suitable for a bank broker
8. Ensure all recommendations are financially sound and well-reasoned
9. Conservative users should get safer recommendations with tighter stops
10. Aggressive users can handle higher risk/reward scenarios
11. PORTFOLIO-AWARE DECISIONS: Consider existing positions and portfolio diversification
12. If user has existing position: consider whether to add, reduce, or maintain
13. If user has no position: consider portfolio diversification impact of new position
14. Position sizing should be appropriate for total portfolio value
15. Email should reference current portfolio context and specific trade rationale
16. POSITION ADJUSTMENT RECOMMENDATIONS: Always provide specific position adjustment advice
17. For existing positions: recommend INCREASE, DECREASE, MAINTAIN, or CLOSE based on analysis
18. For new positions: recommend appropriate portfolio percentage allocation
19. Consider portfolio rebalancing needs and risk impact of position changes
20. Provide clear rationale for all position adjustment recommendations
21. SELL RECOMMENDATIONS: Always suggest which existing positions to sell to fund new trades
22. Consider selling underperforming or overexposed positions to fund better opportunities
23. Recommend selling positions that conflict with new trade thesis or risk management
24. Include specific asset names and quantities to sell when recommending position changes
25. Explain the rationale for sell recommendations in portfolio context

Respond with ONLY the JSON object, no additional text.
"""
        
        return prompt
    
    def _get_portfolio_context_section(self, portfolio_context: Dict, commodity: str) -> str:
        """Generate portfolio context section for the prompt"""
        if not portfolio_context or "error" in portfolio_context:
            return """
PORTFOLIO CONTEXT: No portfolio information available
- Treating as new investor with no existing positions
- Recommendations should consider starting a new position
"""
        
        total_value = portfolio_context.get("total_value", 0)
        portfolios = portfolio_context.get("portfolios", [])
        asset_exposure = portfolio_context.get("asset_exposure", {})
        diversification_score = portfolio_context.get("diversification_score", 0)
        current_asset_exposure = portfolio_context.get("current_asset_exposure", {})
        
        portfolio_section = f"""
PORTFOLIO CONTEXT:
- Total Portfolio Value: ${total_value:,.2f}
- Number of Portfolios: {len(portfolios)}
- Diversification Score: {diversification_score}/100
- Current Asset Holdings: {len(asset_exposure)} different assets
"""
        
        # Add current asset exposure if available
        if current_asset_exposure:
            has_position = current_asset_exposure.get("has_position", False)
            exposure_value = current_asset_exposure.get("value", 0)
            exposure_percent = current_asset_exposure.get("percentage", 0)
            
            if has_position:
                portfolio_section += f"""
- CURRENT POSITION IN {commodity.upper()}: ${exposure_value:,.2f} ({exposure_percent:.1f}% of portfolio)
- This is an EXISTING POSITION - consider whether to add, reduce, or maintain
"""
            else:
                portfolio_section += f"""
- NO CURRENT POSITION IN {commodity.upper()}
- This would be a NEW POSITION - consider portfolio diversification impact
"""
        
        # Add top holdings for context and sell recommendations
        if asset_exposure:
            sorted_holdings = sorted(asset_exposure.items(), key=lambda x: x[1], reverse=True)
            top_holdings = sorted_holdings[:5]  # Top 5 holdings
            
            portfolio_section += f"""
- TOP HOLDINGS (for potential sell recommendations):
"""
            for asset, value in top_holdings:
                percentage = (value / total_value * 100) if total_value > 0 else 0
                portfolio_section += f"  • {asset}: ${value:,.2f} ({percentage:.1f}%)\n"
        
        # Add portfolio-specific guidance
        portfolio_section += f"""
PORTFOLIO CONSIDERATIONS:
- Diversification: {'Well diversified' if diversification_score > 70 else 'Could benefit from more diversification' if diversification_score < 40 else 'Moderately diversified'}
- Position Sizing: Consider current portfolio size (${total_value:,.2f}) when recommending position size
- Risk Management: Existing positions may affect overall portfolio risk
- Rebalancing: Consider if this trade helps achieve better portfolio balance

POSITION ADJUSTMENT GUIDANCE:
- Current Portfolio Value: ${total_value:,.2f}
- Recommended position sizes: 5-10% for conservative, 10-15% for moderate, 15-25% for aggressive
- If user has existing position: Provide specific INCREASE/DECREASE/MAINTAIN/CLOSE recommendation
- If user has no position: Recommend appropriate portfolio percentage allocation
- Consider impact on overall portfolio risk and diversification
- Factor in user's risk tolerance when recommending position sizes

SELL RECOMMENDATIONS GUIDANCE:
- ALWAYS suggest which existing positions to sell to fund new trades
- Consider selling underperforming positions to fund better opportunities
- Recommend selling overexposed positions to improve diversification
- Include specific asset names and quantities in sell recommendations
- Explain rationale for sell recommendations in portfolio context
- Consider selling positions that conflict with new trade thesis
"""
        
        return portfolio_section
    
    def _get_risk_tolerance_description(self, risk_tolerance: str) -> str:
        """Get detailed description for risk tolerance level"""
        descriptions = {
            'conservative': """
- Prioritize capital preservation over growth
- Prefer stable, dividend-paying assets with low volatility
- Use tight stop-losses (2-5% maximum)
- Smaller position sizes (SMALL to MEDIUM)
- Avoid speculative trades and high-volatility periods
- Focus on well-established, liquid markets""",
            'moderate': """
- Balance growth potential with reasonable risk management
- Accept moderate volatility for steady returns
- Use standard stop-losses (5-10% range)
- Medium position sizes typically appropriate
- Mix of conservative and growth-oriented strategies
- Consider both technical and fundamental factors equally""",
            'aggressive': """
- Prioritize growth potential over safety
- Accept higher volatility for potentially higher returns
- Use wider stop-losses (10-15% range) to avoid premature exits
- Larger position sizes acceptable (MEDIUM to LARGE)
- Willing to take contrarian positions
- Focus on momentum and growth opportunities""",
            'very_aggressive': """
- Maximum growth potential is the primary goal
- Accept very high volatility and significant drawdown risk
- Use wide stop-losses (15-20%+ range) or no stops for long-term positions
- Large position sizes acceptable
- Comfortable with speculative trades and emerging opportunities
- May ignore short-term market noise for long-term gains"""
        }
        return descriptions.get(risk_tolerance, descriptions['moderate'])
    
    def _parse_gemini_response(self, response_text: str, commodity: str) -> Dict:
        """Parse Gemini's JSON response"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            decision_data = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['decision', 'confidence', 'reasoning']
            for field in required_fields:
                if field not in decision_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate decision value
            valid_decisions = ['BUY', 'SELL', 'HOLD']
            if decision_data['decision'] not in valid_decisions:
                raise ValueError(f"Invalid decision: {decision_data['decision']}")
            
            # Ensure confidence is between 0 and 1
            confidence = float(decision_data['confidence'])
            if not 0.0 <= confidence <= 1.0:
                confidence = max(0.0, min(1.0, confidence))
                decision_data['confidence'] = confidence
            
            # Set defaults for optional fields
            defaults = {
                'target_price': None,
                'stop_loss': None,
                'position_size': 'MEDIUM',
                'time_horizon': 'MEDIUM',
                'risk_level': 'MEDIUM',
                'key_factors': [],
                'risks': 'Standard market risks apply',
                'market_outlook': 'Market analysis pending',
                'email_subject': f'{commodity.upper()} Trading Recommendation',
                'email_body': 'Trading recommendation analysis attached.'
            }
            
            for key, default_value in defaults.items():
                if key not in decision_data:
                    decision_data[key] = default_value
            
            return decision_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {response_text}")
            return self._create_fallback_decision(commodity, response_text)
        
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return self._create_fallback_decision(commodity, response_text)
    
    def _create_fallback_decision(self, commodity: str, response_text: str) -> Dict:
        """Create a fallback decision when parsing fails"""
        logger.warning(f"Creating fallback decision for {commodity}")
        
        # Try to extract decision from text
        decision = 'HOLD'  # Default conservative decision
        confidence = 0.3   # Low confidence due to parsing failure
        
        text_lower = response_text.lower()
        if 'buy' in text_lower and 'sell' not in text_lower:
            decision = 'BUY'
            confidence = 0.4
        elif 'sell' in text_lower and 'buy' not in text_lower:
            decision = 'SELL'
            confidence = 0.4
        
        return {
            'decision': decision,
            'confidence': confidence,
            'target_price': None,
            'stop_loss': None,
            'position_size': 'SMALL',
            'time_horizon': 'SHORT',
            'risk_level': 'HIGH',
            'key_factors': ['Parsing error occurred'],
            'reasoning': f'Fallback decision due to response parsing error. Original response: {response_text[:200]}...',
            'risks': 'High risk due to parsing error in AI response',
            'market_outlook': 'Unable to determine due to parsing error',
            'email_subject': f'{commodity.upper()} Trading Recommendation - Review Required',
            'email_body': f'Please review the {commodity} analysis manually due to system parsing error.',
            'parsing_error': True
        }
    
    def _create_error_decision(self, commodity: str, error_message: str) -> Dict:
        """Create error decision result"""
        return {
            'commodity': commodity,
            'decision': 'HOLD',
            'confidence': 0.0,
            'target_price': None,
            'stop_loss': None,
            'position_size': 'NONE',
            'time_horizon': 'N/A',
            'risk_level': 'HIGH',
            'key_factors': ['System error'],
            'reasoning': f'Unable to make trading decision due to error: {error_message}',
            'risks': 'System error prevents proper risk assessment',
            'market_outlook': 'Unable to assess due to system error',
            'email_subject': f'{commodity.upper()} Analysis Error',
            'email_body': f'Error occurred during {commodity} analysis: {error_message}',
            'error': error_message,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    async def generate_market_summary(self, commodity_analyses: List[Dict]) -> Dict:
        """
        Generate a comprehensive market summary for multiple commodities
        
        Args:
            commodity_analyses: List of analysis results for multiple commodities
            
        Returns:
            Dict containing market summary and insights
        """
        try:
            if not commodity_analyses:
                return {'error': 'No commodity analyses provided'}
            
            # Create summary prompt
            summary_prompt = self._create_summary_prompt(commodity_analyses)
            
            # Get Gemini's market summary
            response = self.model.generate_content(summary_prompt)
            
            if not response.text:
                raise ValueError("Empty response from Gemini AI")
            
            # Parse the summary
            summary_data = self._parse_summary_response(response.text)
            
            # Add metadata
            summary_data.update({
                'commodities_analyzed': len(commodity_analyses),
                'analysis_timestamp': datetime.now().isoformat()
            })
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return {
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    async def generate_search_terms(self, asset: str, timeframe_days: int) -> List[str]:
        """
        Generate intelligent, relevant search terms for asset news scraping
        
        Args:
            asset: Asset name (commodity or stock)
            timeframe_days: Analysis timeframe
            
        Returns:
            List of optimized search terms
        """
        try:
            # Determine asset type
            from config import Config
            config = Config()
            
            if asset.lower() in config.COMMODITY_SYMBOLS:
                asset_type = "commodity"
                market_context = "commodity markets"
            elif asset.lower() in config.STOCK_SYMBOLS:
                asset_type = "stock"
                market_context = "stock markets and equity analysis"
            else:
                asset_type = "unknown"
                market_context = "financial markets"
            
            logger.info(f"Generating intelligent search terms for {asset} ({asset_type})")
            
            prompt = f"""
You are an expert financial analyst specializing in {market_context}. Generate the most effective search terms for finding recent news articles about {asset.upper()} that would impact trading decisions.

ASSET: {asset.upper()}
ASSET TYPE: {asset_type.upper()}
ANALYSIS TIMEFRAME: {timeframe_days} days

Generate search terms that will find:
1. Price movement news and analysis
2. Company/supply fundamentals (earnings, production, demand)
3. Economic indicators affecting this asset
4. Geopolitical events impacting the market
5. Industry-specific developments and disruptions
6. Technical analysis and trading signals
7. Analyst upgrades/downgrades (for stocks)
8. Regulatory news and policy changes

GUIDELINES FOR {asset_type.upper()}S:
- Use specific terminology that financial news sites would use
- Include both the asset name and related market/sector terms
- Consider earnings seasons, economic cycles, and market events
- Mix broad and specific terms for comprehensive coverage
- Include terms that traders and analysts would search for
- For stocks: Include company name, ticker symbol, sector terms
- For commodities: Include supply/demand factors, seasonal patterns

Return exactly 8-12 highly relevant search terms as a JSON array.
Focus on terms that would appear in headlines and articles about market-moving events.

Example format: ["term1", "term2", "term3", ...]

Respond with ONLY the JSON array, no additional text.
"""
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("Empty response from Gemini AI")
            
            # Parse the JSON response
            search_terms = self._parse_search_terms_response(response.text, asset)
            
            logger.info(f"Generated {len(search_terms)} search terms for {asset}: {search_terms}")
            return search_terms
            
        except Exception as e:
            logger.error(f"Error generating search terms for {asset}: {e}")
            # Fallback to enhanced default terms
            return self._get_fallback_search_terms(asset)
    
    def _parse_search_terms_response(self, response_text: str, commodity: str) -> List[str]:
        """Parse Gemini's search terms response"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            search_terms = json.loads(response_text)
            
            # Validate and clean terms
            if isinstance(search_terms, list):
                cleaned_terms = []
                for term in search_terms:
                    if isinstance(term, str) and len(term.strip()) > 2:
                        cleaned_terms.append(term.strip())
                
                if len(cleaned_terms) >= 3:  # Minimum viable terms
                    return cleaned_terms[:15]  # Limit to 15 terms max
            
            raise ValueError("Invalid search terms format")
            
        except Exception as e:
            logger.warning(f"Error parsing search terms response: {e}")
            return self._get_fallback_search_terms(commodity)
    
    def _get_fallback_search_terms(self, asset: str) -> List[str]:
        """Generate enhanced fallback search terms for assets"""
        base_terms = [asset, asset.replace('_', ' ')]
        
        # Determine asset type for better fallback terms
        from config import Config
        config = Config()
        
        if asset.lower() in config.STOCK_SYMBOLS:
            # Stock-specific fallback terms
            symbol = config.STOCK_SYMBOLS[asset.lower()]
            base_terms.extend([
                f'{asset} stock analysis', f'{asset} earnings', f'{asset} price target',
                f'{asset} analyst rating', f'{symbol} stock', f'{asset} quarterly results',
                f'{asset} revenue growth', f'{asset} stock forecast', f'{asset} market cap',
                f'{asset} investment outlook'
            ])
        else:
            # Commodity fallback terms (existing logic)
            pass
        
        # Enhanced commodity-specific terms
        enhanced_terms = {
            'gold': [
                'gold price forecast', 'gold market analysis', 'gold futures trading',
                'precious metals outlook', 'gold inflation hedge', 'central bank gold reserves',
                'gold mining stocks', 'gold ETF flows', 'dollar gold correlation'
            ],
            'silver': [
                'silver price prediction', 'silver industrial demand', 'silver mining supply',
                'silver gold ratio', 'precious metals rally', 'silver investment demand',
                'silver market fundamentals', 'silver futures analysis'
            ],
            'crude_oil': [
                'oil price forecast', 'crude oil inventory', 'OPEC production cuts',
                'oil demand outlook', 'refinery capacity', 'oil geopolitics',
                'WTI crude analysis', 'energy market trends', 'oil supply disruption'
            ],
            'natural_gas': [
                'natural gas price forecast', 'gas storage levels', 'LNG exports',
                'gas demand winter', 'pipeline capacity', 'gas production growth',
                'energy transition gas', 'gas market fundamentals'
            ],
            'copper': [
                'copper price outlook', 'copper demand china', 'copper mine supply',
                'industrial metals forecast', 'copper construction demand', 'EV copper demand',
                'copper inventory levels', 'base metals analysis'
            ],
            'wheat': [
                'wheat price forecast', 'wheat crop conditions', 'grain export restrictions',
                'wheat supply outlook', 'agricultural commodities', 'food inflation wheat',
                'wheat harvest estimates', 'grain market analysis'
            ],
            'corn': [
                'corn price prediction', 'corn crop yield', 'ethanol demand corn',
                'grain export demand', 'corn planting progress', 'feed demand corn',
                'agricultural weather corn', 'corn futures analysis'
            ],
            'soybeans': [
                'soybean price outlook', 'soy crop conditions', 'china soybean imports',
                'soybean crush margins', 'agricultural trade war', 'soy meal demand',
                'brazil soybean harvest', 'oilseed market trends'
            ]
        }
        
        if asset in enhanced_terms:
            base_terms.extend(enhanced_terms[asset])
        else:
            # Generic asset terms
            base_terms.extend([
                f'{asset} price analysis', f'{asset} market outlook',
                f'{asset} supply demand', f'{asset} futures trading',
                f'{asset} investment forecast'
            ])
        
        return base_terms
    
    def _create_summary_prompt(self, analyses: List[Dict]) -> str:
        """Create prompt for market summary"""
        
        commodity_summaries = []
        for analysis in analyses:
            commodity = analysis.get('commodity', 'Unknown')
            decision = analysis.get('decision', 'HOLD')
            confidence = analysis.get('confidence', 0.0)
            sentiment_score = analysis.get('sentiment_score', 50.0)
            trend_score = analysis.get('trend_score', 50.0)
            
            commodity_summaries.append(f"- {commodity.upper()}: {decision} (confidence: {confidence:.2f}, sentiment: {sentiment_score:.1f}/100, trend: {trend_score:.1f}/100)")
        
        prompt = f"""
You are a senior commodity market analyst providing a comprehensive market overview.

INDIVIDUAL COMMODITY ANALYSES:
{chr(10).join(commodity_summaries)}

TASK: Provide a comprehensive market summary in the following JSON format:

{{
    "overall_market_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
    "market_confidence": 0.0-1.0,
    "key_themes": ["list", "of", "market", "themes"],
    "sector_outlook": {{
        "energy": "outlook for energy commodities",
        "metals": "outlook for metal commodities", 
        "agriculture": "outlook for agricultural commodities"
    }},
    "top_opportunities": ["commodity1", "commodity2", "commodity3"],
    "top_risks": ["risk1", "risk2", "risk3"],
    "diversification_advice": "portfolio diversification recommendations",
    "market_summary": "comprehensive market overview and outlook",
    "recommended_actions": ["action1", "action2", "action3"]
}}

Provide strategic insights based on the individual commodity analyses.
Respond with ONLY the JSON object, no additional text.
Take into account general market trends and macroeconomic factors for the commodity.
"""
        
        return prompt
    
    def _parse_summary_response(self, response_text: str) -> Dict:
        """Parse market summary response"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            summary_data = json.loads(response_text)
            
            # Set defaults for missing fields
            defaults = {
                'overall_market_sentiment': 'NEUTRAL',
                'market_confidence': 0.5,
                'key_themes': [],
                'sector_outlook': {
                    'energy': 'Neutral outlook',
                    'metals': 'Neutral outlook',
                    'agriculture': 'Neutral outlook'
                },
                'top_opportunities': [],
                'top_risks': [],
                'diversification_advice': 'Maintain diversified portfolio',
                'market_summary': 'Market analysis completed',
                'recommended_actions': []
            }
            
            for key, default_value in defaults.items():
                if key not in summary_data:
                    summary_data[key] = default_value
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error parsing summary response: {e}")
            return {
                'overall_market_sentiment': 'NEUTRAL',
                'market_confidence': 0.0,
                'error': f'Parsing error: {str(e)}',
                'market_summary': 'Unable to generate market summary due to parsing error'
            }
    
    async def analyze_portfolio(self, user_email: str, portfolio_id: int, timeframe_days: int = 30) -> Dict:
        """
        Perform comprehensive portfolio analysis using Gemini AI
        
        Args:
            user_email: User's email address
            portfolio_id: Portfolio ID to analyze
            timeframe_days: Analysis timeframe in days
            
        Returns:
            Dict containing comprehensive portfolio analysis
        """
        try:
            logger.info(f"Starting portfolio analysis for user {user_email}, portfolio {portfolio_id}")
            
            # Get portfolio context
            portfolio_context = self.get_portfolio_context(user_email, portfolio_id=portfolio_id)
            if "error" in portfolio_context:
                logger.error(f"Could not get portfolio context: {portfolio_context['error']}")
                return {
                    'success': False,
                    'error': f"Could not get portfolio context: {portfolio_context['error']}"
                }
            
            # Extract holdings from portfolio context
            all_holdings = []
            for portfolio in portfolio_context.get('portfolios', []):
                all_holdings.extend(portfolio.get('holdings', []))
            
            if not all_holdings:
                return {
                    'success': False,
                    'error': 'No holdings found in portfolio'
                }
            
            # Collect data for all holdings
            holdings_data = {}
            sentiment_data = {}
            
            for holding in all_holdings:
                asset_symbol = holding['asset_symbol']
                logger.info(f"Collecting data for {asset_symbol}")
                
                # Get yfinance data
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(asset_symbol)
                    hist = ticker.history(period=f"{timeframe_days}d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        price_change = ((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                        volume_avg = hist['Volume'].mean()
                        
                        holdings_data[asset_symbol] = {
                            'current_price': float(current_price),
                            'price_change_percentage': float(price_change),
                            'volume_avg': float(volume_avg),
                            'high_52w': float(hist['High'].max()),
                            'low_52w': float(hist['Low'].min()),
                            'volatility': float(hist['Close'].pct_change().std() * 100),
                            'data_points': len(hist)
                        }
                    else:
                        holdings_data[asset_symbol] = {
                            'error': 'No data available from yfinance'
                        }
                except Exception as e:
                    logger.error(f"Error fetching yfinance data for {asset_symbol}: {e}")
                    holdings_data[asset_symbol] = {
                        'error': f'Data fetch error: {str(e)}'
                    }
                
                # Get sentiment analysis (simplified for portfolio analysis)
                try:
                    from nlp_analyzer import CommodityNLPAnalyzer
                    nlp_analyzer = CommodityNLPAnalyzer()
                    
                    # Get asset name for sentiment analysis
                    asset_name = holding.get('asset_name', asset_symbol)
                    sentiment_result = await nlp_analyzer.analyze_sentiment_async(asset_name, timeframe_days)
                    
                    sentiment_data[asset_symbol] = {
                        'sentiment_score': sentiment_result.get('normalized_score', 50.0),
                        'total_articles': sentiment_result.get('total_articles', 0),
                        'sentiment_label': sentiment_result.get('sentiment_label', 'neutral')
                    }
                except Exception as e:
                    logger.error(f"Error getting sentiment for {asset_symbol}: {e}")
                    sentiment_data[asset_symbol] = {
                        'sentiment_score': 50.0,
                        'total_articles': 0,
                        'sentiment_label': 'neutral',
                        'error': f'Sentiment error: {str(e)}'
                    }
            
            # Generate comprehensive portfolio analysis using Gemini
            analysis_result = await self._generate_portfolio_analysis(
                portfolio_context, holdings_data, sentiment_data, timeframe_days
            )
            
            return {
                'success': True,
                'portfolio_id': portfolio_id,
                'analysis_date': datetime.now().isoformat(),
                'timeframe_days': timeframe_days,
                'holdings_data': holdings_data,
                'sentiment_data': sentiment_data,
                'portfolio_context': portfolio_context,
                'analysis': analysis_result
            }
            
        except Exception as e:
            logger.error(f"Error in portfolio analysis: {e}")
            return {
                'success': False,
                'error': f'Portfolio analysis failed: {str(e)}'
            }
    
    async def _generate_portfolio_analysis(self, portfolio_context: Dict, holdings_data: Dict, 
                                         sentiment_data: Dict, timeframe_days: int) -> Dict:
        """Generate comprehensive portfolio analysis using Gemini AI"""
        try:
            # Create comprehensive prompt for portfolio analysis
            prompt = self._create_portfolio_analysis_prompt(
                portfolio_context, holdings_data, sentiment_data, timeframe_days
            )
            
            logger.info("Generating portfolio analysis with Gemini AI")
            response = self.model.generate_content(prompt)
            
            if not response:
                return self._create_fallback_portfolio_analysis(portfolio_context, holdings_data, sentiment_data)
            
            # Parse the response
            analysis_result = self._parse_portfolio_analysis_response(response.text)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error generating portfolio analysis: {e}")
            return self._create_fallback_portfolio_analysis(portfolio_context, holdings_data, sentiment_data)
    
    def _create_portfolio_analysis_prompt(self, portfolio_context: Dict, holdings_data: Dict, 
                                        sentiment_data: Dict, timeframe_days: int) -> str:
        """Create comprehensive prompt for portfolio analysis"""
        
        # Portfolio summary
        total_value = portfolio_context.get('total_value', 0)
        total_cost = portfolio_context.get('total_cost', 0)
        total_gain_loss = portfolio_context.get('total_gain_loss', 0)
        # Calculate total holdings count
        holdings_count = 0
        for portfolio in portfolio_context.get('portfolios', []):
            holdings_count += len(portfolio.get('holdings', []))
        
        prompt = f"""
You are a professional financial advisor analyzing a complete investment portfolio. Provide a comprehensive analysis in JSON format.

PORTFOLIO OVERVIEW:
- Total Portfolio Value: ${total_value:,.2f}
- Total Cost Basis: ${total_cost:,.2f}
- Total Gain/Loss: ${total_gain_loss:,.2f} ({((total_gain_loss/total_cost)*100 if total_cost > 0 else 0):.2f}%)
- Number of Holdings: {holdings_count}
- Analysis Timeframe: {timeframe_days} days

HOLDINGS DETAILED ANALYSIS:
"""
        
        # Add detailed analysis for each holding
        all_holdings = []
        for portfolio in portfolio_context.get('portfolios', []):
            all_holdings.extend(portfolio.get('holdings', []))
        
        for holding in all_holdings:
            asset_symbol = holding['asset_symbol']
            asset_name = holding.get('asset_name', asset_symbol)
            quantity = holding.get('quantity', 0)
            avg_cost = holding.get('avg_cost', 0)
            current_value = holding.get('current_value', 0)
            gain_loss = holding.get('gain_loss', 0)
            gain_loss_pct = holding.get('gain_loss_percentage', 0)
            
            # Get market data
            market_data = holdings_data.get(asset_symbol, {})
            sentiment_info = sentiment_data.get(asset_symbol, {})
            
            prompt += f"""
{asset_symbol} ({asset_name}):
- Position: {quantity} shares @ ${avg_cost:.2f} avg cost
- Current Value: ${current_value:,.2f}
- Gain/Loss: ${gain_loss:,.2f} ({gain_loss_pct:+.2f}%)
- Current Price: ${market_data.get('current_price', 'N/A')}
- Price Change ({timeframe_days}d): {market_data.get('price_change_percentage', 0):+.2f}%
- Volatility: {market_data.get('volatility', 0):.2f}%
- Sentiment Score: {sentiment_info.get('sentiment_score', 50):.1f}/100
- News Articles Analyzed: {sentiment_info.get('total_articles', 0)}
- Sentiment: {sentiment_info.get('sentiment_label', 'neutral')}
"""
        
        prompt += f"""

ANALYSIS REQUIREMENTS:
Provide a comprehensive portfolio analysis in the following JSON format:

{{
    "overall_assessment": {{
        "portfolio_health": "EXCELLENT|GOOD|FAIR|POOR",
        "risk_level": "LOW|MEDIUM|HIGH",
        "diversification_score": "0-100",
        "performance_rating": "A|B|C|D|F"
    }},
    "key_metrics": {{
        "total_return_percentage": "calculated percentage",
        "best_performer": "asset_symbol with best performance",
        "worst_performer": "asset_symbol with worst performance",
        "most_volatile": "asset_symbol with highest volatility",
        "least_volatile": "asset_symbol with lowest volatility"
    }},
    "sector_analysis": {{
        "sector_allocation": "breakdown by sector/asset type",
        "concentration_risk": "assessment of concentration",
        "diversification_recommendations": "specific recommendations"
    }},
    "individual_holdings_analysis": {{
        "strong_holds": ["list of assets to maintain or increase"],
        "weak_holds": ["list of assets to reduce or sell"],
        "new_opportunities": ["suggested new positions"],
        "position_sizing_recommendations": "specific recommendations for each holding"
    }},
    "risk_assessment": {{
        "market_risk": "assessment of overall market exposure",
        "concentration_risk": "risk from over-concentration",
        "volatility_risk": "portfolio volatility assessment",
        "liquidity_risk": "liquidity concerns"
    }},
    "recommendations": {{
        "immediate_actions": ["specific actions to take now"],
        "rebalancing_suggestions": ["how to rebalance the portfolio"],
        "new_investments": ["suggested new positions"],
        "exit_strategies": ["positions to consider selling"]
    }},
    "market_outlook": {{
        "overall_sentiment": "BULLISH|BEARISH|NEUTRAL",
        "key_drivers": ["main factors affecting portfolio"],
        "sector_rotation_opportunities": ["sectors to rotate into/out of"],
        "economic_indicators_impact": "how economic factors affect this portfolio"
    }},
    "executive_summary": "2-3 sentence summary of portfolio status and key recommendations"
}}

GUIDELINES:
1. Be specific and actionable in all recommendations
2. Consider the current market sentiment and economic conditions
3. Focus on risk-adjusted returns and diversification
4. Provide clear rationale for all recommendations
5. Consider tax implications of any suggested changes
6. Balance growth opportunities with risk management
7. Consider the investor's time horizon and risk tolerance
8. Provide specific percentage allocations where relevant
9. Consider correlation between holdings
10. Factor in transaction costs for rebalancing suggestions

Generate the analysis now:
"""
        
        return prompt
    
    def _parse_portfolio_analysis_response(self, response_text: str) -> Dict:
        """Parse Gemini's portfolio analysis response"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # If no JSON found, create structured response from text
                return {
                    'overall_assessment': {
                        'portfolio_health': 'FAIR',
                        'risk_level': 'MEDIUM',
                        'diversification_score': 70,
                        'performance_rating': 'B'
                    },
                    'executive_summary': response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    'raw_response': response_text
                }
        except Exception as e:
            logger.error(f"Error parsing portfolio analysis response: {e}")
            return {
                'overall_assessment': {
                    'portfolio_health': 'FAIR',
                    'risk_level': 'MEDIUM',
                    'diversification_score': 70,
                    'performance_rating': 'B'
                },
                'executive_summary': 'Analysis completed with parsing issues',
                'raw_response': response_text,
                'parsing_error': str(e)
            }
    
    def _create_fallback_portfolio_analysis(self, portfolio_context: Dict, holdings_data: Dict, 
                                          sentiment_data: Dict) -> Dict:
        """Create fallback portfolio analysis when Gemini fails"""
        total_value = portfolio_context.get('total_value', 0)
        total_cost = portfolio_context.get('total_cost', 0)
        total_gain_loss = portfolio_context.get('total_gain_loss', 0)
        
        return {
            'overall_assessment': {
                'portfolio_health': 'GOOD' if total_gain_loss >= 0 else 'FAIR',
                'risk_level': 'MEDIUM',
                'diversification_score': 75,
                'performance_rating': 'B' if total_gain_loss >= 0 else 'C'
            },
            'key_metrics': {
                'total_return_percentage': f"{((total_gain_loss/total_cost)*100 if total_cost > 0 else 0):.2f}%",
                'best_performer': 'Analysis unavailable',
                'worst_performer': 'Analysis unavailable',
                'most_volatile': 'Analysis unavailable',
                'least_volatile': 'Analysis unavailable'
            },
            'executive_summary': f"Portfolio analysis completed. Total value: ${total_value:,.2f}, Gain/Loss: ${total_gain_loss:,.2f}. Detailed analysis unavailable due to technical issues.",
            'fallback': True
        }
