"""
Email Service for Sending Trading Recommendations to Brokers
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
import pandas as pd
from io import StringIO
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    """
    Service for sending trading recommendations via email
    """
    
    def __init__(self, gemini_advisor=None):
        self.config = Config()
        self.gemini_advisor = gemini_advisor
        self._validate_email_config()
    
    def _validate_email_config(self):
        """Validate email configuration"""
        required_fields = ['EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'BROKER_EMAIL']
        missing_fields = []
        
        for field in required_fields:
            if not getattr(self.config, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing email configuration: {', '.join(missing_fields)}")
    
    async def send_trading_recommendation(self, trading_decision: Dict, 
                                        sentiment_analysis: Dict, 
                                        data_analysis: Dict) -> Dict:
        """
        Send trading recommendation email to broker
        
        Args:
            trading_decision: Gemini trading decision
            sentiment_analysis: NLP sentiment analysis results
            data_analysis: Historical data analysis results
            
        Returns:
            Dict containing send status and details
        """
        try:
            # Skip sending emails for HOLD positions
            decision = trading_decision.get('decision', 'HOLD')
            if decision == 'HOLD':
                logger.info(f"Skipping email for {trading_decision.get('commodity', 'Unknown')} - HOLD position")
                return {
                    'success': True,
                    'message': 'Email skipped for HOLD position',
                    'decision': decision
                }
            
            logger.info(f"Sending trading recommendation for {trading_decision.get('commodity', 'Unknown')}")
            
            # Create email content
            email_subject = self._create_email_subject(trading_decision, data_analysis)
            email_body = await self._create_email_body(trading_decision, sentiment_analysis, data_analysis)
            
            # Create and send email
            msg = self._create_email_message(email_subject, email_body)
            
            # Attach analysis report
            analysis_attachment = self._create_analysis_attachment(
                trading_decision, sentiment_analysis, data_analysis
            )
            if analysis_attachment:
                msg.attach(analysis_attachment)
            
            # Send email
            send_result = self._send_email(msg)
            
            return {
                'status': 'success' if send_result else 'failed',
                'commodity': trading_decision.get('commodity', 'Unknown'),
                'decision': trading_decision.get('decision', 'HOLD'),
                'recipient': self.config.BROKER_EMAIL,
                'subject': email_subject,
                'timestamp': datetime.now().isoformat(),
                'error': None if send_result else 'Failed to send email'
            }
            
        except Exception as e:
            logger.error(f"Error sending trading recommendation: {e}")
            return {
                'status': 'error',
                'commodity': trading_decision.get('commodity', 'Unknown'),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_email_subject(self, trading_decision: Dict, data_analysis: Dict = None) -> str:
        """Create email subject line"""
        commodity = trading_decision.get('commodity', 'Unknown').upper()
        decision = trading_decision.get('decision', 'HOLD')
        confidence = trading_decision.get('confidence', 0.0)
        
        # Get current price from data analysis if available
        current_price = 0.0
        if data_analysis:
            current_price = data_analysis.get('current_price', 0.0)
        
        # Use Gemini's subject if available, otherwise create one
        if 'email_subject' in trading_decision and trading_decision['email_subject']:
            return trading_decision['email_subject']
        
        # Generate order-focused subject line
        if decision == 'BUY':
            return f"Order Request: BUY {commodity} - ${current_price:.2f}"
        elif decision == 'SELL':
            return f"Order Request: SELL {commodity} - ${current_price:.2f}"
        else:
            return f"Portfolio Update: HOLD {commodity} - ${current_price:.2f}"
    
    def _generate_human_email_content(self, trading_decision: Dict, 
                                    sentiment_analysis: Dict, 
                                    data_analysis: Dict) -> str:
        """Generate human-like email content using Gemini AI"""
        
        commodity = trading_decision.get('commodity', 'Unknown').upper()
        decision = trading_decision.get('decision', 'HOLD')
        confidence = trading_decision.get('confidence', 0.0)
        reasoning = trading_decision.get('reasoning', '')
        
        # Get key metrics
        current_price = data_analysis.get('current_price', 0.0)
        price_change = data_analysis.get('price_analysis', {}).get('price_change_percentage', 0.0)
        sentiment_score = sentiment_analysis.get('normalized_score', 50.0)
        trend_score = data_analysis.get('trend_score', 50.0)
        total_articles = sentiment_analysis.get('total_articles', 0)
        timeframe_days = trading_decision.get('timeframe_days', 30)
        
        # Get portfolio adjustment information
        portfolio_adjustments = trading_decision.get('portfolio_adjustments', {})
        position_action = portfolio_adjustments.get('current_position_action', 'N/A')
        recommended_size = portfolio_adjustments.get('recommended_position_size', 'N/A')
        position_rationale = portfolio_adjustments.get('position_change_rationale', '')
        rebalancing_impact = portfolio_adjustments.get('rebalancing_impact', '')
        risk_impact = portfolio_adjustments.get('risk_impact', '')
        total_portfolio_value = portfolio_adjustments.get('total_portfolio_value', 'N/A')
        
        # Check if we have meaningful portfolio data
        has_portfolio_data = (
            portfolio_adjustments and 
            position_action != 'N/A' and 
            total_portfolio_value != 'N/A' and 
            total_portfolio_value != 0 and
            str(total_portfolio_value).strip() != ''
        )
        
        # Create prompt for Gemini
        prompt = f"""
        Write a professional email to Ujjwal, my broker, placing a trading order for {commodity}.
        
        Key Information:
        - Asset: {commodity}
        - Order Type: {decision}
        - Confidence: {confidence:.0%}
        - Current Price: ${current_price:.4f}
        - Price Change: {price_change:+.2f}%
        - Sentiment Score: {sentiment_score:.1f}/100 (based on {total_articles} news articles)
        - Technical Trend Score: {trend_score:.1f}/100
        - Trading Timeframe: {timeframe_days} days
        - Timeframe Category: {trading_decision.get('timeframe_analysis', {}).get('timeframe_category', 'MEDIUM')}
        - Expected Holding Period: {trading_decision.get('timeframe_analysis', {}).get('expected_holding_period', f'{timeframe_days} days')}
        - Analysis Reasoning: {reasoning}"""

        # Only include portfolio information if we have meaningful data
        if has_portfolio_data:
            prompt += f"""
        
        Portfolio Position Instructions:
        - Position Action: {position_action}
        - Recommended Position Size: {recommended_size}
        - Position Rationale: {position_rationale}
        - Portfolio Impact: {rebalancing_impact}
        - Risk Impact: {risk_impact}
        - Current Portfolio Value: ${total_portfolio_value}"""
        
        prompt += f"""
        
        Requirements:
        1. Write as a client placing an actual trading order with their broker
        2. Address Ujjwal professionally but personally
        3. Be direct and clear about the order you want to place
        4. Include specific order details and reasoning
        5. Sound confident but not arrogant
        6. Keep it concise and actionable
        7. End with "Best regards, FinSys acting on behalf of Ujjwal"
        8. Use natural, conversational language
        9. Make it sound like a real client-broker communication
        10. EXPLAIN WHY the decision was made - include specific reasons based on the analysis
        11. Reference the key metrics (sentiment score, trend score, price movement) in your explanation
        12. Make the decision rationale clear and compelling
        13. EMPHASIZE the {timeframe_days}-day trading timeframe and how it affects the strategy
        14. Explain why this timeframe is optimal for the current market conditions
        15. Include timeframe-specific risk considerations and exit strategy"""

        # Add portfolio-specific requirements only if we have portfolio data
        if has_portfolio_data:
            prompt += f"""
        16. ALWAYS reference current portfolio context and holdings
        17. Include recommendations for selling existing positions if it makes sense
        18. Explain how this trade fits into overall portfolio strategy
        19. Comment on portfolio diversification and risk management"""
        else:
            prompt += f"""
        16. Focus on the standalone trade opportunity without portfolio context
        17. Emphasize the individual asset's potential and market conditions"""
        
        prompt += f"""
        
        Write the email body only (no subject line):
        """
        
        try:
            # Use Gemini to generate the email content (synchronous call to avoid event loop issues)
            response = self.gemini_advisor.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating email content with Gemini: {e}")
            return self._create_fallback_email_body(trading_decision, sentiment_analysis, data_analysis)
    
    def _create_fallback_email_body(self, trading_decision: Dict, 
                                  sentiment_analysis: Dict, 
                                  data_analysis: Dict) -> str:
        """Create fallback email body if Gemini fails"""
        commodity = trading_decision.get('commodity', 'Unknown').upper()
        decision = trading_decision.get('decision', 'HOLD')
        confidence = trading_decision.get('confidence', 0.0)
        reasoning = trading_decision.get('reasoning', 'Based on comprehensive market analysis')
        
        # Get key metrics for decision explanation
        current_price = data_analysis.get('current_price', 0.0)
        price_change = data_analysis.get('price_analysis', {}).get('price_change_percentage', 0.0)
        sentiment_score = sentiment_analysis.get('normalized_score', 50.0)
        trend_score = data_analysis.get('trend_score', 50.0)
        total_articles = sentiment_analysis.get('total_articles', 0)
        timeframe_days = trading_decision.get('timeframe_days', 30)
        
        # Check if we have meaningful portfolio data for fallback email
        portfolio_adjustments = trading_decision.get('portfolio_adjustments', {})
        total_portfolio_value = portfolio_adjustments.get('total_portfolio_value', 'N/A')
        
        has_portfolio_data = (
            portfolio_adjustments and 
            total_portfolio_value != 'N/A' and 
            total_portfolio_value != 0 and
            str(total_portfolio_value).strip() != ''
        )
        
        # Build email body
        email_body = f"""
Dear Ujjwal,

I hope this email finds you well. I wanted to reach out with an important trading recommendation for {commodity}.

=== TRADING RECOMMENDATION ===
After conducting a comprehensive analysis of market sentiment and technical indicators, I'm recommending a {decision} position with {confidence:.0%} confidence.

=== DECISION RATIONALE ===
{reasoning}

=== KEY ANALYSIS METRICS ===
• Current Market Price: ${current_price:.4f}
• Price Movement: {price_change:+.2f}%
• Market Sentiment Score: {sentiment_score:.1f}/100 (based on {total_articles} news articles)
• Technical Trend Score: {trend_score:.1f}/100
• Risk Level: {trading_decision.get('risk_level', 'MEDIUM')}
• Investment Horizon: {trading_decision.get('time_horizon', 'MEDIUM')}
• Trading Timeframe: {timeframe_days} days
• Timeframe Category: {trading_decision.get('timeframe_analysis', {}).get('timeframe_category', 'MEDIUM')}
• Expected Holding Period: {trading_decision.get('timeframe_analysis', {}).get('expected_holding_period', f'{timeframe_days} days')}"""

        # Only add portfolio section if we have meaningful portfolio data
        if has_portfolio_data:
            email_body += f"""

=== PORTFOLIO CONTEXT & RECOMMENDATIONS ===
• Current Portfolio Value: ${total_portfolio_value}
• Diversification Score: {portfolio_adjustments.get('diversification_score', 'N/A')}/100
• Asset Exposure: {portfolio_adjustments.get('asset_exposure', 'N/A')}
• Recommended Actions: {portfolio_adjustments.get('sell_recommendations', 'Consider current holdings for rebalancing')}"""

        email_body += f"""

Please review the detailed analysis and let me know if you have any questions or need clarification on the recommendation.

Best regards,
FinSys acting on behalf of Ujjwal
"""
        
        return email_body
    
    async def _create_email_body(self, trading_decision: Dict, sentiment_analysis: Dict, 
                          data_analysis: Dict) -> str:
        """Create comprehensive email body using Gemini for human-like content"""
        
        commodity = trading_decision.get('commodity', 'Unknown').upper()
        decision = trading_decision.get('decision', 'HOLD')
        confidence = trading_decision.get('confidence', 0.0)
        
        # Generate human-like email content using Gemini
        if self.gemini_advisor:
            try:
                gemini_body = self._generate_human_email_content(
                    trading_decision, sentiment_analysis, data_analysis
                )
            except Exception as e:
                logger.warning(f"Failed to generate Gemini email content: {e}")
                gemini_body = "Please see detailed analysis below."
        else:
            gemini_body = "Please see detailed analysis below."
        
        # Get key metrics
        current_price = data_analysis.get('current_price', 0.0)
        price_change = data_analysis.get('price_analysis', {}).get('price_change_percentage', 0.0)
        sentiment_score = sentiment_analysis.get('normalized_score', 50.0)
        trend_score = data_analysis.get('trend_score', 50.0)
        
        # Use Gemini-generated content as the main email body
        email_body = gemini_body
        
        # Add order details section if needed
        if decision in ['BUY', 'SELL']:
            target_price = trading_decision.get('target_price')
            stop_loss = trading_decision.get('stop_loss')
            
            email_body += f"""

=== ORDER DETAILS ===
Order Type: {decision} {commodity}
Entry Price: ${target_price if target_price else 'Market Order'} 
Stop Loss: ${stop_loss if stop_loss else 'To be set after entry'}
Current Market Price: ${current_price:.4f}
Price Movement: {price_change:+.2f}%
"""
        
        # Add portfolio position recommendations section only if portfolio data is available
        portfolio_adjustments = trading_decision.get('portfolio_adjustments', {})
        position_action = portfolio_adjustments.get('current_position_action', 'N/A')
        recommended_size = portfolio_adjustments.get('recommended_position_size', 'N/A')
        position_rationale = portfolio_adjustments.get('position_change_rationale', '')
        rebalancing_impact = portfolio_adjustments.get('rebalancing_impact', '')
        risk_impact = portfolio_adjustments.get('risk_impact', '')
        total_portfolio_value = portfolio_adjustments.get('total_portfolio_value', 'N/A')
        
        # Check if we have meaningful portfolio data
        has_portfolio_data = (
            portfolio_adjustments and 
            position_action != 'N/A' and 
            total_portfolio_value != 'N/A' and 
            total_portfolio_value != 0 and
            str(total_portfolio_value).strip() != ''
        )
        
        if has_portfolio_data:
            email_body += f"""

=== PORTFOLIO POSITION INSTRUCTIONS ===
• Position Action: {position_action}
• Target Allocation: {recommended_size}
• Reasoning: {position_rationale}
• Portfolio Impact: {rebalancing_impact}
• Risk Management: {risk_impact}

=== PORTFOLIO CONTEXT & RECOMMENDATIONS ===
• Current Portfolio Value: ${total_portfolio_value}
• Diversification Score: {portfolio_adjustments.get('diversification_score', 'N/A')}/100
• Asset Exposure: {portfolio_adjustments.get('asset_exposure', 'N/A')}
• Recommended Actions: {portfolio_adjustments.get('sell_recommendations', 'Consider current holdings for rebalancing')}
"""
        
        # Add analysis summary section
        email_body += f"""

=== ANALYSIS SUMMARY ===
• Market Sentiment: {sentiment_score:.1f}/100 (based on {sentiment_analysis.get('total_articles', 0)} news articles)
• Technical Analysis: {trend_score:.1f}/100
• Risk Assessment: {trading_decision.get('risk_level', 'MEDIUM')}
• Investment Horizon: {trading_decision.get('time_horizon', 'MEDIUM')}
• Position Size: {trading_decision.get('position_size', 'MEDIUM')}
"""
        
        # Add detailed reasoning if available
        if trading_decision.get('reasoning'):
            email_body += f"""

=== ORDER RATIONALE ===
{trading_decision.get('reasoning')}
"""
        
        # Add order confirmation request
        email_body += f"""

---
Please confirm this order and let me know if you need any additional information.
I'm available to discuss the position sizing and risk management if needed.

Best regards,
FinSys acting on behalf of Ujjwal
"""
        
        return email_body
    
    def _create_email_message(self, subject: str, body: str) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart()
        msg['From'] = self.config.EMAIL_ADDRESS
        msg['To'] = self.config.BROKER_EMAIL
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        return msg
    
    def _create_analysis_attachment(self, trading_decision: Dict, sentiment_analysis: Dict, 
                                  data_analysis: Dict) -> Optional[MIMEBase]:
        """Create detailed analysis attachment"""
        try:
            # Create comprehensive analysis report
            report_data = {
                'trading_recommendation': trading_decision,
                'sentiment_analysis': sentiment_analysis,
                'technical_analysis': data_analysis,
                'generated_timestamp': datetime.now().isoformat()
            }
            
            # Convert to JSON string
            json_report = json.dumps(report_data, indent=2, default=str)
            
            # Create attachment
            attachment = MIMEBase('application', 'json')
            attachment.set_payload(json_report.encode())
            encoders.encode_base64(attachment)
            
            commodity = trading_decision.get('commodity', 'unknown')
            filename = f"{commodity}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Error creating analysis attachment: {e}")
            return None
    
    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Send email via SMTP"""
        try:
            # Create SMTP session
            context = ssl.create_default_context()
            
            # Use SSL for Zoho Mail (port 465) or STARTTLS for other providers (port 587)
            if self.config.SMTP_PORT == 465:
                # SSL connection for Zoho Mail
                with smtplib.SMTP_SSL(self.config.SMTP_SERVER, self.config.SMTP_PORT, context=context) as server:
                    server.login(self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD)
                    
                    # Send email
                    text = msg.as_string()
                    server.sendmail(self.config.EMAIL_ADDRESS, self.config.BROKER_EMAIL, text)
            else:
                # STARTTLS connection for other providers
                with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                    server.starttls(context=context)  # Enable security
                    server.login(self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD)
                    
                    # Send email
                    text = msg.as_string()
                    server.sendmail(self.config.EMAIL_ADDRESS, self.config.BROKER_EMAIL, text)
            
            logger.info(f"Email sent successfully to {self.config.BROKER_EMAIL}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def send_market_summary_email(self, market_summary: Dict, 
                                      commodity_analyses: List[Dict]) -> Dict:
        """
        Send market summary email with multiple commodity analyses
        
        Args:
            market_summary: Overall market summary from Gemini
            commodity_analyses: List of individual commodity analyses
            
        Returns:
            Dict containing send status
        """
        try:
            logger.info("Sending market summary email")
            
            # Create email content
            subject = self._create_summary_subject(market_summary, commodity_analyses)
            body = self._create_summary_body(market_summary, commodity_analyses)
            
            # Create and send email
            msg = self._create_email_message(subject, body)
            
            # Attach detailed analysis
            summary_attachment = self._create_summary_attachment(market_summary, commodity_analyses)
            if summary_attachment:
                msg.attach(summary_attachment)
            
            # Send email
            send_result = self._send_email(msg)
            
            return {
                'status': 'success' if send_result else 'failed',
                'type': 'market_summary',
                'commodities_count': len(commodity_analyses),
                'recipient': self.config.BROKER_EMAIL,
                'subject': subject,
                'timestamp': datetime.now().isoformat(),
                'error': None if send_result else 'Failed to send email'
            }
            
        except Exception as e:
            logger.error(f"Error sending market summary email: {e}")
            return {
                'status': 'error',
                'type': 'market_summary',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_summary_subject(self, market_summary: Dict, commodity_analyses: List[Dict]) -> str:
        """Create market summary email subject"""
        market_sentiment = market_summary.get('overall_market_sentiment', 'NEUTRAL')
        commodities_count = len(commodity_analyses)
        
        return f"Daily Commodity Market Summary - {market_sentiment} Outlook ({commodities_count} commodities analyzed)"
    
    def _create_summary_body(self, market_summary: Dict, commodity_analyses: List[Dict]) -> str:
        """Create market summary email body"""
        
        market_sentiment = market_summary.get('overall_market_sentiment', 'NEUTRAL')
        market_confidence = market_summary.get('market_confidence', 0.5)
        
        email_body = f"""
Dear Trading Team,

Please find below our comprehensive daily commodity market analysis covering {len(commodity_analyses)} key commodities.

=== MARKET OVERVIEW ===
Overall Market Sentiment: {market_sentiment}
Market Confidence: {market_confidence:.0%}
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}

{market_summary.get('market_summary', 'Comprehensive market analysis completed')}

=== KEY MARKET THEMES ===
"""
        
        key_themes = market_summary.get('key_themes', [])
        if key_themes:
            for i, theme in enumerate(key_themes, 1):
                email_body += f"{i}. {theme}\n"
        else:
            email_body += "• Mixed market signals across commodity sectors\n"
        
        email_body += f"""

=== INDIVIDUAL COMMODITY RECOMMENDATIONS ===
"""
        
        # Group by decision type
        buy_recommendations = []
        sell_recommendations = []
        hold_recommendations = []
        
        for analysis in commodity_analyses:
            commodity = analysis.get('commodity', 'Unknown').upper()
            decision = analysis.get('decision', 'HOLD')
            confidence = analysis.get('confidence', 0.0)
            
            recommendation_line = f"• {commodity}: {decision} (Confidence: {confidence:.0%})"
            
            if decision == 'BUY':
                buy_recommendations.append(recommendation_line)
            elif decision == 'SELL':
                sell_recommendations.append(recommendation_line)
            else:
                hold_recommendations.append(recommendation_line)
        
        if buy_recommendations:
            email_body += "\nBUY RECOMMENDATIONS:\n" + "\n".join(buy_recommendations) + "\n"
        
        if sell_recommendations:
            email_body += "\nSELL RECOMMENDATIONS:\n" + "\n".join(sell_recommendations) + "\n"
        
        if hold_recommendations:
            email_body += "\nHOLD RECOMMENDATIONS:\n" + "\n".join(hold_recommendations) + "\n"
        
        email_body += f"""

=== SECTOR OUTLOOK ===
Energy Commodities: {market_summary.get('sector_outlook', {}).get('energy', 'Neutral outlook')}
Metal Commodities: {market_summary.get('sector_outlook', {}).get('metals', 'Neutral outlook')}
Agricultural Commodities: {market_summary.get('sector_outlook', {}).get('agriculture', 'Neutral outlook')}

=== TOP OPPORTUNITIES ===
"""
        
        opportunities = market_summary.get('top_opportunities', [])
        if opportunities:
            for i, opportunity in enumerate(opportunities, 1):
                email_body += f"{i}. {opportunity.upper()}\n"
        else:
            email_body += "• Opportunities under evaluation\n"
        
        email_body += f"""

=== KEY RISKS ===
"""
        
        risks = market_summary.get('top_risks', [])
        if risks:
            for i, risk in enumerate(risks, 1):
                email_body += f"{i}. {risk}\n"
        else:
            email_body += "• Standard market volatility risks\n"
        
        email_body += f"""

=== DIVERSIFICATION ADVICE ===
{market_summary.get('diversification_advice', 'Maintain balanced portfolio across commodity sectors')}

=== RECOMMENDED ACTIONS ===
"""
        
        actions = market_summary.get('recommended_actions', [])
        if actions:
            for i, action in enumerate(actions, 1):
                email_body += f"{i}. {action}\n"
        else:
            email_body += "• Monitor market developments closely\n• Review individual commodity positions\n"
        
        email_body += f"""

Detailed individual commodity analyses are attached for your review.

Please review these recommendations and execute trades according to your risk management protocols.

Best regards,
Automated Commodity Analysis System
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

---
DISCLAIMER: This analysis is generated by an automated system. Please conduct your own 
due diligence before executing any trades. All trading involves risk of loss.
"""
        
        return email_body
    
    def _create_summary_attachment(self, market_summary: Dict, 
                                 commodity_analyses: List[Dict]) -> Optional[MIMEBase]:
        """Create market summary attachment"""
        try:
            # Create comprehensive summary report
            report_data = {
                'market_summary': market_summary,
                'individual_analyses': commodity_analyses,
                'generated_timestamp': datetime.now().isoformat(),
                'total_commodities': len(commodity_analyses)
            }
            
            # Convert to JSON string
            json_report = json.dumps(report_data, indent=2, default=str)
            
            # Create attachment
            attachment = MIMEBase('application', 'json')
            attachment.set_payload(json_report.encode())
            encoders.encode_base64(attachment)
            
            filename = f"market_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Error creating summary attachment: {e}")
            return None
