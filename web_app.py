"""
Web Interface for Commodity and Stock Market Analysis System
"""
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List
import os
from pathlib import Path
import sys

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from main import CommodityMarketAnalyzer
from config import Config
from scheduler import scheduler
from models import db, User, Portfolio, Holding, Transaction, AnalysisRecommendation
from auth_service import AuthService, PortfolioService, AnalysisService
from price_service import price_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app)  # Enable CORS for API access
csrf = CSRFProtect(app)

# Configure CSRF to exempt API routes
csrf.exempt('login')
csrf.exempt('register')
csrf.exempt('user_profile')
csrf.exempt('change_password')
csrf.exempt('portfolios')
csrf.exempt('portfolio_detail')
csrf.exempt('portfolio_holdings')
csrf.exempt('remove_holding')
csrf.exempt('portfolio_transactions')
csrf.exempt('update_portfolio_prices')
csrf.exempt('fetch_portfolio_prices')
csrf.exempt('portfolio_analysis')
csrf.exempt('get_current_price')
csrf.exempt('get_current_prices_batch')
csrf.exempt('get_market_summary')
csrf.exempt('get_asset_info')

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Global analyzer instance
analyzer = None
analysis_cache = {}
website_access_log = []

def init_analyzer():
    """Initialize the market analyzer"""
    global analyzer
    try:
        analyzer = CommodityMarketAnalyzer(website_logger=log_website_access)
        logger.info("Market analyzer initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing analyzer: {e}")
        return False

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/csrf-token')
def get_csrf_token():
    """Get CSRF token for AJAX requests"""
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

@app.route('/api/prices/<symbol>', methods=['GET'])
def get_current_price(symbol):
    """Get current price for a single asset"""
    try:
        price = price_service.get_current_price(symbol)
        if price is not None:
            return jsonify({
                'success': True,
                'symbol': symbol,
                'current_price': price,
                'last_updated': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': f'Could not fetch price for {symbol}'}), 404
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices/batch', methods=['POST'])
@csrf.exempt
def get_current_prices_batch():
    """Get current prices for multiple assets"""
    try:
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({'error': 'Symbols list required'}), 400
        
        symbols = data['symbols']
        if not isinstance(symbols, list):
            return jsonify({'error': 'Symbols must be a list'}), 400
        
        prices = price_service.get_current_prices_batch(symbols)
        
        return jsonify({
            'success': True,
            'prices': prices,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching batch prices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices/market-summary', methods=['POST'])
@csrf.exempt
def get_market_summary():
    """Get market summary for multiple assets"""
    try:
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({'error': 'Symbols list required'}), 400
        
        symbols = data['symbols']
        if not isinstance(symbols, list):
            return jsonify({'error': 'Symbols must be a list'}), 400
        
        summary = price_service.get_market_summary(symbols)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error fetching market summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices/asset-info/<symbol>', methods=['GET'])
def get_asset_info(symbol):
    """Get comprehensive asset information"""
    try:
        asset_info = price_service.get_asset_info(symbol)
        
        return jsonify({
            'success': True,
            'asset_info': asset_info
        })
        
    except Exception as e:
        logger.error(f"Error fetching asset info for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username_or_email = data.get('username_or_email', '').strip()
        password = data.get('password', '')
        
        success, message, user = AuthService.authenticate_user(username_or_email, password)
        
        if success and user:
            login_user(user, remember=True)
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'user': user.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('index'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 401
            else:
                flash(message, 'error')
    
    if request.is_json:
        return jsonify({'success': False, 'message': 'Method not allowed'}), 405
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        success, message, user = AuthService.register_user(
            username, email, password, first_name, last_name
        )
        
        if success and user:
            login_user(user, remember=True)
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'user': user.to_dict()})
            else:
                flash(message, 'success')
                return redirect(url_for('index'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            else:
                flash(message, 'error')
    
    if request.is_json:
        return jsonify({'success': False, 'message': 'Method not allowed'}), 405
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/api/user/profile', methods=['GET', 'PUT'])
@login_required
def user_profile():
    """Get or update user profile"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'data': current_user.to_dict()
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        success, message = AuthService.update_user_profile(current_user.id, **data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': current_user.to_dict()
            })
        else:
            return jsonify({'success': False, 'message': message}), 400

@app.route('/api/user/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    success, message = AuthService.change_password(current_user.id, old_password, new_password)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/assets')
def get_assets():
    """Get available assets"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        assets = analyzer.get_available_assets()
        return jsonify({
            'success': True,
            'data': assets,
            'total_count': len(assets['all'])
        })
    except Exception as e:
        logger.error(f"Error getting assets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_asset():
    """Analyze a single asset"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        asset = data.get('asset', '').lower()
        timeframe = data.get('timeframe', 30)
        send_email = data.get('send_email', False)
        risk_tolerance = data.get('risk_tolerance', 'moderate')
        
        if not asset:
            return jsonify({'error': 'Asset name is required'}), 400
        
        # Validate asset
        available_assets = analyzer.get_available_assets()['all']
        if asset not in available_assets:
            return jsonify({'error': f'Unknown asset: {asset}'}), 400
        
        # Clear website access log for this analysis
        global website_access_log
        website_access_log = []
        
        # Run analysis asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get user email if user is logged in
        user_email = None
        if current_user and current_user.is_authenticated:
            user_email = current_user.email
        
        try:
            result = loop.run_until_complete(
                analyzer.analyze_asset(asset, timeframe, send_email, risk_tolerance, user_email)
            )
            
            # Add website access log to result
            result['websites_accessed'] = website_access_log.copy()
            result['total_websites_accessed'] = len(website_access_log)
            
            # Cache the result
            cache_key = f"{asset}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H')}"
            analysis_cache[cache_key] = result
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in asset analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-multiple', methods=['POST'])
def analyze_multiple_assets():
    """Analyze multiple assets"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        assets = data.get('assets', [])
        timeframe = data.get('timeframe', 30)
        send_individual_emails = data.get('send_individual_emails', False)
        send_summary_email = data.get('send_summary_email', False)
        risk_tolerance = data.get('risk_tolerance', 'moderate')
        
        if not assets or len(assets) == 0:
            return jsonify({'error': 'At least one asset is required'}), 400
        
        # Validate assets
        available_assets = analyzer.get_available_assets()['all']
        invalid_assets = [asset for asset in assets if asset.lower() not in available_assets]
        if invalid_assets:
            return jsonify({'error': f'Unknown assets: {", ".join(invalid_assets)}'}), 400
        
        # Clear website access log for this analysis
        global website_access_log
        website_access_log = []
        
        # Run analysis asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get user email if user is logged in
        user_email = None
        if current_user and current_user.is_authenticated:
            user_email = current_user.email
        
        try:
            result = loop.run_until_complete(
                analyzer.analyze_multiple_assets(
                    [asset.lower() for asset in assets], 
                    timeframe, 
                    send_individual_emails, 
                    send_summary_email,
                    risk_tolerance,
                    user_email
                )
            )
            
            # Add website access log to result
            result['websites_accessed'] = website_access_log.copy()
            result['total_websites_accessed'] = len(website_access_log)
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in multiple asset analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-terms/<asset>')
def get_search_terms(asset):
    """Get AI-generated search terms for an asset"""
    try:
        if not analyzer:
            return jsonify({'error': 'Analyzer not initialized'}), 500
        
        timeframe = request.args.get('timeframe', 30, type=int)
        
        # Run search term generation asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            search_terms = loop.run_until_complete(
                analyzer.gemini_advisor.generate_search_terms(asset.lower(), timeframe)
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'asset': asset,
                    'timeframe': timeframe,
                    'search_terms': search_terms,
                    'count': len(search_terms)
                }
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error generating search terms: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/website-log')
def get_website_log():
    """Get the current website access log"""
    return jsonify({
        'success': True,
        'data': {
            'websites_accessed': website_access_log,
            'total_count': len(website_access_log),
            'timestamp': datetime.now().isoformat()
        }
    })

@app.route('/api/cache')
def get_cache():
    """Get cached analysis results"""
    return jsonify({
        'success': True,
        'data': {
            'cached_analyses': list(analysis_cache.keys()),
            'count': len(analysis_cache)
        }
    })

@app.route('/api/cache/<cache_key>')
def get_cached_analysis(cache_key):
    """Get specific cached analysis"""
    if cache_key in analysis_cache:
        return jsonify({
            'success': True,
            'data': analysis_cache[cache_key]
        })
    else:
        return jsonify({'error': 'Analysis not found in cache'}), 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'analyzer_initialized': analyzer is not None,
        'timestamp': datetime.now().isoformat()
    })

# Portfolio Management API endpoints
@app.route('/api/portfolios', methods=['GET', 'POST'])
@login_required
def portfolios():
    """Get user portfolios or create new portfolio"""
    if request.method == 'GET':
        try:
            portfolios = PortfolioService.get_user_portfolios(current_user.id)
            return jsonify({
                'success': True,
                'data': [portfolio.to_dict() for portfolio in portfolios]
            })
        except Exception as e:
            logger.error(f"Error getting portfolios: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                return jsonify({'error': 'Portfolio name is required'}), 400
            
            success, message, portfolio = PortfolioService.create_portfolio(
                current_user.id, name, description
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': portfolio.to_dict()
                })
            else:
                return jsonify({'error': message}), 400
                
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def portfolio_detail(portfolio_id):
    """Get, update, or delete a specific portfolio"""
    if request.method == 'GET':
        try:
            portfolio = PortfolioService.get_portfolio(current_user.id, portfolio_id)
            if portfolio:
                return jsonify({
                    'success': True,
                    'data': portfolio.to_dict()
                })
            else:
                return jsonify({'error': 'Portfolio not found'}), 404
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            success, message = PortfolioService.update_portfolio(
                current_user.id, portfolio_id, **data
            )
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'error': message}), 400
                
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            success, message = PortfolioService.delete_portfolio(current_user.id, portfolio_id)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'error': message}), 400
                
        except Exception as e:
            logger.error(f"Error deleting portfolio: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/holdings', methods=['GET', 'POST'])
@login_required
def portfolio_holdings(portfolio_id):
    """Get or add holdings to a portfolio"""
    if request.method == 'GET':
        try:
            holdings = PortfolioService.get_portfolio_holdings(current_user.id, portfolio_id)
            return jsonify({
                'success': True,
                'data': [holding.to_dict() for holding in holdings]
            })
        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            required_fields = ['asset_symbol', 'asset_name', 'asset_type', 'quantity', 'price_per_share']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            success, message, holding = PortfolioService.add_holding(
                current_user.id,
                portfolio_id,
                data['asset_symbol'],
                data['asset_name'],
                data['asset_type'],
                float(data['quantity']),
                float(data['price_per_share']),
                datetime.fromisoformat(data['transaction_date']) if data.get('transaction_date') else None
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': holding.to_dict()
                })
            else:
                return jsonify({'error': message}), 400
                
        except Exception as e:
            logger.error(f"Error adding holding: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/holdings/<asset_symbol>', methods=['DELETE'])
@login_required
def remove_holding(portfolio_id, asset_symbol):
    """Remove shares from a holding"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        quantity = float(data.get('quantity', 0))
        price_per_share = float(data.get('price_per_share', 0))
        
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400
        
        success, message = PortfolioService.remove_holding(
            current_user.id,
            portfolio_id,
            asset_symbol,
            quantity,
            price_per_share,
            datetime.fromisoformat(data['transaction_date']) if data.get('transaction_date') else None
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error removing holding: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/transactions', methods=['GET'])
@login_required
def portfolio_transactions(portfolio_id):
    """Get transaction history for a portfolio"""
    try:
        limit = request.args.get('limit', 50, type=int)
        transactions = PortfolioService.get_portfolio_transactions(current_user.id, portfolio_id, limit)
        return jsonify({
            'success': True,
            'data': [transaction.to_dict() for transaction in transactions]
        })
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/update-prices', methods=['POST'])
@login_required
def update_portfolio_prices(portfolio_id):
    """Update current prices for portfolio holdings"""
    try:
        data = request.get_json()
        if not data or 'price_updates' not in data:
            return jsonify({'error': 'Price updates data required'}), 400
        
        success, message = PortfolioService.update_holding_prices(
            current_user.id, portfolio_id, data['price_updates']
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error updating prices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/fetch-prices', methods=['POST'])
@csrf.exempt
@login_required
def fetch_portfolio_prices(portfolio_id):
    """Fetch and update current prices for portfolio holdings automatically"""
    try:
        # Get portfolio holdings
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, 
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        # Get all holdings for this portfolio
        holdings = Holding.query.filter_by(
            portfolio_id=portfolio_id,
            is_active=True
        ).all()
        
        if not holdings:
            return jsonify({'error': 'No holdings found in portfolio'}), 400
        
        # Prepare symbols for price fetching
        symbols = [holding.asset_symbol for holding in holdings]
        
        # Fetch current prices
        price_updates = {}
        updated_count = 0
        
        for symbol in symbols:
            current_price = price_service.get_current_price(symbol)
            if current_price is not None:
                price_updates[symbol] = current_price
                updated_count += 1
        
        if not price_updates:
            return jsonify({'error': 'Could not fetch any prices'}), 400
        
        # Update holdings with new prices
        success, message = PortfolioService.update_holding_prices(
            current_user.id, portfolio_id, price_updates
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Updated prices for {updated_count} holdings',
                'price_updates': price_updates
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error fetching portfolio prices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/analysis', methods=['GET'])
@login_required
def portfolio_analysis(portfolio_id):
    """Get analysis summary for a portfolio"""
    try:
        summary = AnalysisService.get_portfolio_analysis_summary(current_user.id, portfolio_id)
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error getting portfolio analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolios/<int:portfolio_id>/comprehensive-analysis', methods=['POST'])
@login_required
def comprehensive_portfolio_analysis(portfolio_id):
    """Perform comprehensive portfolio analysis using Gemini AI with yfinance data and sentiment analysis"""
    try:
        data = request.get_json() or {}
        timeframe_days = data.get('timeframe_days', 30)
        
        # Verify portfolio ownership
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, 
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if not portfolio:
            return jsonify({'error': 'Portfolio not found'}), 404
        
        # Get user email for analysis
        user_email = current_user.email
        
        # Run comprehensive analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                analyzer.gemini_advisor.analyze_portfolio(user_email, portfolio_id, timeframe_days)
            )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'data': result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Analysis failed')
                }), 500
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in comprehensive portfolio analysis: {e}")
        return jsonify({'error': str(e)}), 500

# Scheduling API endpoints
@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Get all schedules"""
    try:
        schedules = scheduler.get_all_schedules()
        return jsonify({
            'success': True,
            'data': schedules
        })
    except Exception as e:
        logger.error(f"Error getting schedules: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Create a new schedule"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['name', 'assets']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get user email if user is logged in
        user_email = None
        if current_user and current_user.is_authenticated:
            user_email = current_user.email
        
        schedule_id = scheduler.create_schedule(
            name=data['name'],
            assets=data['assets'],
            timeframe=data.get('timeframe', 30),
            frequency=data.get('frequency', 'daily'),
            time_of_day=data.get('time_of_day', '09:00'),
            risk_tolerance=data.get('risk_tolerance', 'moderate'),
            send_email=data.get('send_email', True),
            enabled=data.get('enabled', True),
            user_email=user_email
        )
        
        return jsonify({
            'success': True,
            'data': {
                'schedule_id': schedule_id,
                'message': 'Schedule created successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Get a specific schedule"""
    try:
        schedule = scheduler.get_schedule(schedule_id)
        if schedule:
            return jsonify({
                'success': True,
                'data': schedule
            })
        else:
            return jsonify({'error': 'Schedule not found'}), 404
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Update a schedule"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        success = scheduler.update_schedule(schedule_id, **data)
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': 'Schedule updated successfully'
                }
            })
        else:
            return jsonify({'error': 'Schedule not found'}), 404
            
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a schedule"""
    try:
        success = scheduler.delete_schedule(schedule_id)
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': 'Schedule deleted successfully'
                }
            })
        else:
            return jsonify({'error': 'Schedule not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>/run', methods=['POST'])
def run_schedule_now(schedule_id):
    """Manually trigger a schedule to run immediately"""
    try:
        success = scheduler.run_schedule_now(schedule_id)
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'message': 'Schedule triggered successfully'
                }
            })
        else:
            return jsonify({'error': 'Schedule not found'}), 404
            
    except Exception as e:
        logger.error(f"Error running schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status"""
    try:
        status = scheduler.get_scheduler_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the scheduler"""
    try:
        scheduler.start_scheduler()
        return jsonify({
            'success': True,
            'data': {
                'message': 'Scheduler started successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the scheduler"""
    try:
        scheduler.stop_scheduler()
        return jsonify({
            'success': True,
            'data': {
                'message': 'Scheduler stopped successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        return jsonify({'error': str(e)}), 500

# Website access tracking function
def log_website_access(url: str, source: str, search_term: str = "", status: str = "accessed"):
    """Log website access for transparency"""
    global website_access_log
    
    access_entry = {
        'timestamp': datetime.now().isoformat(),
        'url': url,
        'source': source,
        'search_term': search_term,
        'status': status
    }
    
    website_access_log.append(access_entry)
    logger.info(f"Website accessed: {source} - {url}")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Financial Analysis Web Interface...")
    print("=" * 60)
    
    # Initialize database
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            print("   Please check your PostgreSQL connection and DATABASE_URL")
            sys.exit(1)
    
    # Initialize analyzer
    if init_analyzer():
        print("✅ Market analyzer initialized successfully")
        
        # Get asset counts
        assets = analyzer.get_available_assets()
        print(f"📊 Available: {len(assets['commodities'])} commodities, {len(assets['stocks'])} stocks")
        
        # Start the scheduler
        try:
            scheduler.start_scheduler()
            print("✅ Analysis scheduler started successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not start scheduler: {e}")
        
        print("\n🌐 Starting web server...")
        print("📍 Access the web interface at: http://localhost:5000")
        print("📍 API documentation at: http://localhost:5000/api/health")
        print("📍 Scheduler status at: http://localhost:5000/api/scheduler/status")
        print("📍 Portfolio management: http://localhost:5000/portfolios")
        print("\n⚠️  Press Ctrl+C to stop the server")
        
        try:
            # Start Flask app
            app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            scheduler.stop_scheduler()
            print("✅ Scheduler stopped")
    else:
        print("❌ Failed to initialize market analyzer")
        print("   Please check your .env configuration")
        sys.exit(1)
