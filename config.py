"""
Configuration settings for the Commodity Market Analyzer
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    BROKER_EMAIL = os.getenv('BROKER_EMAIL')
    
    # Application Settings
    DEFAULT_TIMEFRAME = int(os.getenv('DEFAULT_TIMEFRAME', '30'))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
    CACHE_DURATION = int(os.getenv('CACHE_DURATION', '3600'))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///financial_analyzer.db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
    
    # Portfolio Settings
    MAX_PORTFOLIOS_PER_USER = int(os.getenv('MAX_PORTFOLIOS_PER_USER', '10'))
    MAX_HOLDINGS_PER_PORTFOLIO = int(os.getenv('MAX_HOLDINGS_PER_PORTFOLIO', '100'))
    PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', '3600'))  # 1 hour
    
    # Daemon/Scheduler Settings
    DAEMON_ENABLED = os.getenv('DAEMON_ENABLED', 'false').lower() == 'true'
    ANALYSIS_INTERVAL_MINUTES = int(os.getenv('ANALYSIS_INTERVAL_MINUTES', '60'))  # Default: 1 hour
    WATCHLIST = os.getenv('WATCHLIST', 'gold,silver,crude_oil').split(',')  # Assets to monitor
    SEND_EMAILS = os.getenv('SEND_EMAILS', 'true').lower() == 'true'
    DAEMON_LOG_LEVEL = os.getenv('DAEMON_LOG_LEVEL', 'INFO')
    
    # Commodity Symbols
    COMMODITY_SYMBOLS = {
        'gold': 'GC=F',
        'silver': 'SI=F', 
        'crude_oil': 'CL=F',
        'natural_gas': 'NG=F',
        'copper': 'HG=F',
        'wheat': 'ZW=F',
        'corn': 'ZC=F',
        'soybeans': 'ZS=F',
        'coffee': 'KC=F',
        'sugar': 'SB=F',
        'cotton': 'CT=F',
        'platinum': 'PL=F',
        'palladium': 'PA=F',
        'aluminum': 'ALI=F',
        'zinc': 'ZNC=F'
    }
    
    # Stock Symbols - Major stocks across different sectors
    STOCK_SYMBOLS = {
        # Technology
        'apple': 'AAPL',
        'microsoft': 'MSFT',
        'google': 'GOOGL',
        'amazon': 'AMZN',
        'tesla': 'TSLA',
        'nvidia': 'NVDA',
        'meta': 'META',
        'netflix': 'NFLX',
        'adobe': 'ADBE',
        'salesforce': 'CRM',
        'oracle': 'ORCL',
        'intel': 'INTC',
        'amd': 'AMD',
        'cisco': 'CSCO',
        'ibm': 'IBM',
        
        # Financial Services
        'berkshire_hathaway': 'BRK-B',
        'jpmorgan': 'JPM',
        'bank_of_america': 'BAC',
        'wells_fargo': 'WFC',
        'goldman_sachs': 'GS',
        'morgan_stanley': 'MS',
        'american_express': 'AXP',
        'visa': 'V',
        'mastercard': 'MA',
        'paypal': 'PYPL',
        
        # Healthcare & Pharma
        'johnson_johnson': 'JNJ',
        'pfizer': 'PFE',
        'moderna': 'MRNA',
        'abbvie': 'ABBV',
        'merck': 'MRK',
        'bristol_myers': 'BMY',
        'eli_lilly': 'LLY',
        'unitedhealth': 'UNH',
        
        # Consumer & Retail
        'walmart': 'WMT',
        'coca_cola': 'KO',
        'pepsi': 'PEP',
        'procter_gamble': 'PG',
        'nike': 'NKE',
        'mcdonalds': 'MCD',
        'starbucks': 'SBUX',
        'home_depot': 'HD',
        'target': 'TGT',
        
        # Energy
        'exxon_mobil': 'XOM',
        'chevron': 'CVX',
        'conocophillips': 'COP',
        'marathon_petroleum': 'MPC',
        
        # Industrial & Transportation
        'boeing': 'BA',
        'caterpillar': 'CAT',
        'general_electric': 'GE',
        'fedex': 'FDX',
        'ups': 'UPS',
        
        # Communication
        'verizon': 'VZ',
        'att': 'T',
        'comcast': 'CMCSA',
        
        # ETFs & Indices
        'spy': 'SPY',  # S&P 500 ETF
        'qqq': 'QQQ',  # Nasdaq ETF
        'dia': 'DIA',  # Dow Jones ETF
        'vti': 'VTI',  # Total Stock Market ETF
        'voo': 'VOO',  # S&P 500 ETF
    }
    
    # Combined symbols for unified access
    ALL_SYMBOLS = {**COMMODITY_SYMBOLS, **STOCK_SYMBOLS}
    
    # News Sources for NLP Analysis (prioritized by reliability)
    NEWS_SOURCES = [
        'https://finance.yahoo.com/commodities/',
        'https://www.cnbc.com/commodities/',
        'https://www.marketwatch.com/investing/commodities',
        'https://www.investing.com/commodities/',
        'https://www.reuters.com/markets/commodities/',
        'https://www.bloomberg.com/markets/commodities'
    ]
    
    # FinBERT Model Configuration
    FINBERT_MODEL = 'ProsusAI/finbert'
    SENTIMENT_THRESHOLD = 0.1  # Threshold for neutral sentiment
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        required_keys = ['GEMINI_API_KEY', 'EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'BROKER_EMAIL']
        missing_keys = [key for key in required_keys if not getattr(cls, key)]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
        
        return True
