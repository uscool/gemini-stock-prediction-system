"""
Main Commodity Market Analysis Application
Orchestrates NLP sentiment analysis, historical data analysis, and AI-powered trading decisions
"""
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from config import Config
from nlp_analyzer import CommodityNLPAnalyzer
from data_analyzer import CommodityDataAnalyzer
from gemini_advisor import GeminiCommodityAdvisor
from email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommodityMarketAnalyzer:
    """
    Main application class that orchestrates the complete commodity analysis pipeline
    """
    
    def __init__(self, website_logger=None):
        self.config = Config()
        self.nlp_analyzer = None
        self.data_analyzer = None
        self.gemini_advisor = None
        self.email_service = None
        self.website_logger = website_logger
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all analysis components"""
        try:
            logger.info("Initializing Commodity Market Analyzer...")
            
            # Validate configuration
            self.config.validate_config()
            
            # Initialize components
            self.data_analyzer = CommodityDataAnalyzer()
            self.gemini_advisor = GeminiCommodityAdvisor()
            self.nlp_analyzer = CommodityNLPAnalyzer(
                gemini_advisor=self.gemini_advisor,
                website_logger=self.website_logger
            )
            self.email_service = EmailService(gemini_advisor=self.gemini_advisor)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def _get_asset_type(self, asset: str) -> str:
        """Determine if asset is a commodity or stock"""
        if asset.lower() in self.config.COMMODITY_SYMBOLS:
            return 'commodity'
        elif asset.lower() in self.config.STOCK_SYMBOLS:
            return 'stock'
        else:
            return 'unknown'
    
    async def analyze_asset(self, asset: str, timeframe_days: int = 30, 
                           send_email: bool = True, risk_tolerance: str = 'moderate', 
                           user_email: str = None) -> Dict:
        """
        Perform complete analysis for a single asset (commodity or stock)
        
        Args:
            asset: Asset name (e.g., 'gold', 'apple', 'tesla', 'wheat')
            timeframe_days: Analysis timeframe in days
            send_email: Whether to send email to broker
            risk_tolerance: User's risk tolerance ('conservative', 'moderate', 'aggressive', 'very_aggressive')
            user_email: User's email for portfolio context (optional)
            
        Returns:
            Dict containing complete analysis results
        """
        try:
            # Determine asset type
            asset_type = self._get_asset_type(asset)
            logger.info(f"Starting {asset_type} analysis for {asset} over {timeframe_days} days")
            
            # Step 1: Collect News Articles
            logger.info("Step 1: Collecting news articles...")
            articles = await self.nlp_analyzer._collect_asset_news(asset, timeframe_days)
            logger.info(f"Collected {len(articles)} articles for {asset}")
            
            # Step 2: NLP Sentiment Analysis
            logger.info("Step 2: Performing NLP sentiment analysis...")
            sentiment_analysis = await self.nlp_analyzer.analyze_asset_sentiment(
                asset, articles
            )
            
            if 'error' in sentiment_analysis:
                logger.warning(f"Sentiment analysis error for {asset}: {sentiment_analysis['error']}")
            else:
                logger.info(f"Sentiment analysis completed - Score: {sentiment_analysis.get('normalized_score', 'N/A')}/100")
            
            # Step 3: Historical Data Analysis
            logger.info("Step 3: Performing historical data analysis...")
            data_analysis = await self.data_analyzer.analyze_asset_data(
                asset, timeframe_days
            )
            
            if 'error' in data_analysis:
                logger.warning(f"Data analysis error for {commodity}: {data_analysis['error']}")
            else:
                logger.info(f"Data analysis completed - Trend Score: {data_analysis.get('trend_score', 'N/A')}/100")
            
            # Step 4: AI Trading Decision
            logger.info("Step 4: Generating AI trading decision...")
            trading_decision = await self.gemini_advisor.make_trading_decision(
                asset, sentiment_analysis, data_analysis, timeframe_days, risk_tolerance, user_email
            )
            
            if 'error' in trading_decision:
                logger.warning(f"Trading decision error for {asset}: {trading_decision['error']}")
            else:
                decision = trading_decision.get('decision', 'UNKNOWN')
                confidence = trading_decision.get('confidence', 0.0)
                logger.info(f"Trading decision: {decision} (Confidence: {confidence:.0%})")
            
            # Step 4: Send Email (if requested and no critical errors)
            email_result = None
            if send_email and 'error' not in trading_decision:
                logger.info("Step 4: Sending email to broker...")
                email_result = await self.email_service.send_trading_recommendation(
                    trading_decision, sentiment_analysis, data_analysis
                )
                
                if email_result.get('status') == 'success':
                    logger.info("Email sent successfully")
                else:
                    logger.error(f"Email sending failed: {email_result.get('error')}")
            
            # Compile complete results
            complete_analysis = {
                'asset': asset,
                'asset_type': asset_type,
                'timeframe_days': timeframe_days,
                'risk_tolerance': risk_tolerance,
                'analysis_timestamp': datetime.now().isoformat(),
                'sentiment_analysis': sentiment_analysis,
                'data_analysis': data_analysis,
                'trading_decision': trading_decision,
                'email_result': email_result,
                'status': 'completed'
            }
            
            logger.info(f"Complete analysis for {asset} finished successfully")
            return complete_analysis
            
        except Exception as e:
            logger.error(f"Error in asset analysis for {asset}: {e}")
            return {
                'asset': asset,
                'asset_type': asset_type,
                'timeframe_days': timeframe_days,
                'analysis_timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            }
    
    async def analyze_multiple_assets(self, assets: List[str], 
                                     timeframe_days: int = 30,
                                     send_individual_emails: bool = False,
                                     send_summary_email: bool = True,
                                     risk_tolerance: str = 'moderate',
                                     user_email: str = None) -> Dict:
        """
        Analyze multiple assets (commodities and/or stocks) and generate market summary
        
        Args:
            assets: List of asset names (commodities and/or stocks)
            timeframe_days: Analysis timeframe in days
            send_individual_emails: Send individual emails for each asset
            send_summary_email: Send comprehensive market summary email
            risk_tolerance: User's risk tolerance level
            user_email: User's email for portfolio context (optional)
            
        Returns:
            Dict containing all analyses and market summary
        """
        try:
            logger.info(f"Starting multi-asset analysis for {len(assets)} assets")
            
            # Analyze all assets concurrently
            tasks = []
            for asset in assets:
                task = self.analyze_asset(asset, timeframe_days, send_individual_emails, risk_tolerance, user_email)
                tasks.append(task)
            
            # Wait for all analyses to complete
            commodity_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful analyses
            successful_analyses = []
            failed_analyses = []
            
            for result in commodity_results:
                if isinstance(result, Exception):
                    failed_analyses.append({'error': str(result)})
                elif result.get('status') == 'completed':
                    successful_analyses.append(result)
                else:
                    failed_analyses.append(result)
            
            logger.info(f"Completed {len(successful_analyses)} successful analyses, {len(failed_analyses)} failed")
            
            # Generate market summary if we have successful analyses
            market_summary = None
            summary_email_result = None
            
            if successful_analyses:
                logger.info("Generating market summary...")
                
                # Extract trading decisions for summary
                trading_decisions = [
                    analysis['trading_decision'] for analysis in successful_analyses
                    if 'trading_decision' in analysis and 'error' not in analysis['trading_decision']
                ]
                
                if trading_decisions:
                    market_summary = await self.gemini_advisor.generate_market_summary(trading_decisions)
                    
                    # Send summary email if requested
                    if send_summary_email and market_summary and 'error' not in market_summary:
                        logger.info("Sending market summary email...")
                        summary_email_result = await self.email_service.send_market_summary_email(
                            market_summary, trading_decisions
                        )
            
            # Compile complete results
            complete_results = {
                'analysis_type': 'multi_commodity',
                'commodities_requested': commodities,
                'commodities_analyzed': len(successful_analyses),
                'timeframe_days': timeframe_days,
                'analysis_timestamp': datetime.now().isoformat(),
                'successful_analyses': successful_analyses,
                'failed_analyses': failed_analyses,
                'market_summary': market_summary,
                'summary_email_result': summary_email_result,
                'status': 'completed'
            }
            
            logger.info(f"Multi-commodity analysis completed successfully")
            return complete_results
            
        except Exception as e:
            logger.error(f"Error in multi-commodity analysis: {e}")
            return {
                'analysis_type': 'multi_commodity',
                'commodities_requested': commodities,
                'error': str(e),
                'status': 'failed',
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def get_available_assets(self) -> Dict[str, List[str]]:
        """Get list of available assets for analysis"""
        return {
            'commodities': list(self.config.COMMODITY_SYMBOLS.keys()),
            'stocks': list(self.config.STOCK_SYMBOLS.keys()),
            'all': list(self.config.ALL_SYMBOLS.keys())
        }
    
    def get_available_commodities(self) -> List[str]:
        """Get list of available commodities for analysis (backward compatibility)"""
        return list(self.config.COMMODITY_SYMBOLS.keys())
    
    def get_available_stocks(self) -> List[str]:
        """Get list of available stocks for analysis"""
        return list(self.config.STOCK_SYMBOLS.keys())
    
    def save_analysis_results(self, results: Dict, filename: Optional[str] = None) -> str:
        """
        Save analysis results to JSON file
        
        Args:
            results: Analysis results to save
            filename: Optional custom filename
            
        Returns:
            Path to saved file
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                commodity = results.get('commodity', 'multi_commodity')
                filename = f"analysis_{commodity}_{timestamp}.json"
            
            # Ensure results directory exists
            results_dir = Path('results')
            results_dir.mkdir(exist_ok=True)
            
            filepath = results_dir / filename
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Analysis results saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            return ""

def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Commodity Market Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single asset (commodity or stock)
  python main.py --asset gold --timeframe 30 --email
  python main.py --stock apple --timeframe 14 --email
  
  # Analyze multiple assets (mixed)
  python main.py --assets gold apple tesla crude_oil --summary-email
  
  # Analyze multiple stocks
  python main.py --stocks apple microsoft tesla --timeframe 7 --summary-email

  # List available assets
  python main.py --list-assets
  python main.py --list-stocks
  
  # Backward compatibility (commodities only)
  python main.py --commodity gold --timeframe 30 --email
  python main.py --commodities gold silver --summary-email
        """
    )
    
    # Asset selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--asset', '-a', type=str,
                      help='Single asset to analyze (commodity or stock)')
    group.add_argument('--assets', '-as', nargs='+',
                      help='Multiple assets to analyze (commodities and/or stocks)')
    group.add_argument('--commodity', '-c', type=str,
                      help='Single commodity to analyze (backward compatibility)')
    group.add_argument('--commodities', '-cs', nargs='+',
                      help='Multiple commodities to analyze (backward compatibility)')
    group.add_argument('--stock', type=str,
                      help='Single stock to analyze')
    group.add_argument('--stocks', nargs='+',
                      help='Multiple stocks to analyze')
    group.add_argument('--list-assets', '-la', action='store_true',
                      help='List available assets (commodities and stocks)')
    group.add_argument('--list-commodities', '-lc', action='store_true',
                      help='List available commodities')
    group.add_argument('--list-stocks', '-ls', action='store_true',
                      help='List available stocks')
    
    # Analysis parameters
    parser.add_argument('--timeframe', '-t', type=int, default=30,
                       help='Analysis timeframe in days (default: 30)')
    
    # Email options
    parser.add_argument('--email', action='store_true',
                       help='Send individual commodity emails')
    parser.add_argument('--no-email', action='store_true',
                       help='Do not send any emails')
    parser.add_argument('--summary-email', action='store_true',
                       help='Send market summary email (for multiple commodities)')
    
    # Output options
    parser.add_argument('--save-results', '-s', action='store_true',
                       help='Save analysis results to JSON file')
    parser.add_argument('--output-file', '-o', type=str,
                       help='Custom output filename')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    return parser

async def main():
    """Main application entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize analyzer
        analyzer = CommodityMarketAnalyzer()
        
        # Handle list commands
        if args.list_assets:
            assets = analyzer.get_available_assets()
            print("\n🏦 Available Assets for Analysis:")
            print("=" * 80)
            
            print(f"\n📊 COMMODITIES ({len(assets['commodities'])} available):")
            for i, commodity in enumerate(assets['commodities'], 1):
                symbol = analyzer.config.COMMODITY_SYMBOLS[commodity]
                print(f"{i:2d}. {commodity.upper().replace('_', ' ')} ({symbol})")
            
            print(f"\n📈 STOCKS ({len(assets['stocks'])} available):")
            for i, stock in enumerate(assets['stocks'], 1):
                symbol = analyzer.config.STOCK_SYMBOLS[stock]
                print(f"{i:2d}. {stock.upper().replace('_', ' ')} ({symbol})")
            
            print(f"\n🎯 TOTAL: {len(assets['all'])} assets available")
            return
        
        if args.list_commodities:
            commodities = analyzer.get_available_commodities()
            print("\n📊 Available Commodities:")
            print("=" * 50)
            for i, commodity in enumerate(commodities, 1):
                symbol = analyzer.config.COMMODITY_SYMBOLS[commodity]
                print(f"{i:2d}. {commodity.upper().replace('_', ' ')} ({symbol})")
            print(f"\nTotal: {len(commodities)} commodities available")
            return
        
        if args.list_stocks:
            stocks = analyzer.get_available_stocks()
            print("\n📈 Available Stocks:")
            print("=" * 50)
            for i, stock in enumerate(stocks, 1):
                symbol = analyzer.config.STOCK_SYMBOLS[stock]
                print(f"{i:2d}. {stock.upper().replace('_', ' ')} ({symbol})")
            print(f"\nTotal: {len(stocks)} stocks available")
            return
        
        # Determine email settings
        send_individual_emails = args.email and not args.no_email
        send_summary_email = args.summary_email and not args.no_email
        
        # Validate timeframe
        if args.timeframe < 1 or args.timeframe > 365:
            print("Error: Timeframe must be between 1 and 365 days")
            return
        
        # Determine which asset(s) to analyze
        target_asset = None
        target_assets = None
        
        if args.asset:
            target_asset = args.asset
        elif args.commodity:
            target_asset = args.commodity
        elif args.stock:
            target_asset = args.stock
        elif args.assets:
            target_assets = args.assets
        elif args.commodities:
            target_assets = args.commodities
        elif args.stocks:
            target_assets = args.stocks
        
        # Perform analysis
        if target_asset:
            # Single asset analysis
            asset_type = analyzer._get_asset_type(target_asset)
            print(f"\n🔍 Starting {asset_type} analysis for {target_asset.upper()}")
            print(f"📅 Timeframe: {args.timeframe} days")
            print(f"📧 Email: {'Yes' if send_individual_emails else 'No'}")
            print("=" * 60)
            
            results = await analyzer.analyze_asset(
                target_asset, args.timeframe, send_individual_emails
            )
            
            # Display results summary
            if results.get('status') == 'completed':
                trading_decision = results.get('trading_decision', {})
                decision = trading_decision.get('decision', 'UNKNOWN')
                confidence = trading_decision.get('confidence', 0.0)
                
                print(f"\n✅ Analysis completed successfully!")
                print(f"📊 Recommendation: {decision}")
                print(f"🎯 Confidence: {confidence:.0%}")
                
                if 'sentiment_analysis' in results:
                    sentiment_score = results['sentiment_analysis'].get('normalized_score', 50)
                    print(f"📰 Sentiment Score: {sentiment_score:.1f}/100")
                
                if 'data_analysis' in results:
                    trend_score = results['data_analysis'].get('trend_score', 50)
                    current_price = results['data_analysis'].get('current_price', 0)
                    print(f"📈 Trend Score: {trend_score:.1f}/100")
                    print(f"💰 Current Price: ${current_price:.4f}")
                
                if results.get('email_result', {}).get('status') == 'success':
                    print(f"📧 Email sent successfully")
            else:
                print(f"\n❌ Analysis failed: {results.get('error', 'Unknown error')}")
        
        elif target_assets:
            # Multiple assets analysis
            asset_types = [analyzer._get_asset_type(asset) for asset in target_assets]
            type_counts = {}
            for asset_type in asset_types:
                type_counts[asset_type] = type_counts.get(asset_type, 0) + 1
            
            type_summary = ", ".join([f"{count} {asset_type}{'s' if count > 1 else ''}" 
                                    for asset_type, count in type_counts.items()])
            
            print(f"\n🔍 Starting multi-asset analysis")
            print(f"📋 Assets: {', '.join([a.upper() for a in target_assets])}")
            print(f"📊 Types: {type_summary}")
            print(f"📅 Timeframe: {args.timeframe} days")
            print(f"📧 Individual emails: {'Yes' if send_individual_emails else 'No'}")
            print(f"📧 Summary email: {'Yes' if send_summary_email else 'No'}")
            print("=" * 80)
            
            results = await analyzer.analyze_multiple_assets(
                target_assets, args.timeframe, 
                send_individual_emails, send_summary_email
            )
            
            # Display results summary
            if results.get('status') == 'completed':
                successful = len(results.get('successful_analyses', []))
                failed = len(results.get('failed_analyses', []))
                
                print(f"\n✅ Multi-commodity analysis completed!")
                print(f"📊 Successful analyses: {successful}")
                print(f"❌ Failed analyses: {failed}")
                
                # Show individual recommendations
                for analysis in results.get('successful_analyses', []):
                    asset = analysis.get('asset', 'Unknown').upper()
                    asset_type = analysis.get('asset_type', 'unknown')
                    decision = analysis.get('trading_decision', {}).get('decision', 'UNKNOWN')
                    confidence = analysis.get('trading_decision', {}).get('confidence', 0.0)
                    type_icon = "📊" if asset_type == "commodity" else "📈" if asset_type == "stock" else "📋"
                    print(f"   {type_icon} {asset}: {decision} ({confidence:.0%})")
                
                # Show market summary
                market_summary = results.get('market_summary', {})
                if market_summary and 'error' not in market_summary:
                    overall_sentiment = market_summary.get('overall_market_sentiment', 'NEUTRAL')
                    market_confidence = market_summary.get('market_confidence', 0.5)
                    print(f"\n🌍 Overall Market: {overall_sentiment} ({market_confidence:.0%} confidence)")
                
                if results.get('summary_email_result', {}).get('status') == 'success':
                    print(f"📧 Market summary email sent successfully")
            else:
                print(f"\n❌ Multi-commodity analysis failed: {results.get('error', 'Unknown error')}")
        
        # Save results if requested
        if args.save_results:
            filepath = analyzer.save_analysis_results(results, args.output_file)
            if filepath:
                print(f"\n💾 Results saved to: {filepath}")
        
        print(f"\n🏁 Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Analysis interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Application error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
