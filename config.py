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
        
        # Indian Stocks (NSE/BSE)
        # Banking & Financial Services
        'hdfc_bank': 'HDFCBANK.NS',
        'icici_bank': 'ICICIBANK.NS',
        'sbi': 'SBIN.NS',
        'kotak_mahindra': 'KOTAKBANK.NS',
        'axis_bank': 'AXISBANK.NS',
        'bajaj_finserv': 'BAJFINANCE.NS',
        'bajaj_finance': 'BAJFINANCE.NS',
        'hdfc_life': 'HDFCLIFE.NS',
        'sbi_life': 'SBILIFE.NS',
        'icici_prudential': 'ICICIPRULI.NS',
        
        # Technology & IT
        'tcs': 'TCS.NS',
        'infosys': 'INFY.NS',
        'wipro': 'WIPRO.NS',
        'hcl_tech': 'HCLTECH.NS',
        'tech_mahindra': 'TECHM.NS',
        'lti_mindtree': 'LTIM.NS',
        'mphasis': 'MPHASIS.NS',
        'persistent': 'PERSISTENT.NS',
        'cyient': 'CYIENT.NS',
        'cognizant': 'CTSH',  # US listed
        
        # Reliance Group
        'reliance': 'RELIANCE.NS',
        'jio_financial': 'JIOFIN.NS',
        
        # Automobile
        'maruti_suzuki': 'MARUTI.NS',
        'tata_motors': 'TATAMOTORS.NS',
        'mahindra_mahindra': 'M&M.NS',
        'bajaj_auto': 'BAJAJ-AUTO.NS',
        'hero_motocorp': 'HEROMOTOCO.NS',
        'eicher_motors': 'EICHERMOT.NS',
        'ashok_leyland': 'ASHOKLEY.NS',
        
        # Pharmaceuticals
        'sun_pharma': 'SUNPHARMA.NS',
        'dr_reddys': 'DRREDDY.NS',
        'cipla': 'CIPLA.NS',
        'divis_labs': 'DIVISLAB.NS',
        'lupin': 'LUPIN.NS',
        'aurobindo_pharma': 'AUROPHARMA.NS',
        'biocon': 'BIOCON.NS',
        'cadila_healthcare': 'ZYDUSLIFE.NS',
        
        # FMCG & Consumer
        'hindustan_unilever': 'HINDUNILVR.NS',
        'itc': 'ITC.NS',
        'nestle_india': 'NESTLEIND.NS',
        'titan': 'TITAN.NS',
        'tata_consumer': 'TATACONSUM.NS',
        'britannia': 'BRITANNIA.NS',
        'dabur': 'DABUR.NS',
        'godrej_consumer': 'GODREJCP.NS',
        'marico': 'MARICO.NS',
        
        # Energy & Oil
        'ongc': 'ONGC.NS',
        'oil_india': 'OIL.NS',
        'indian_oil': 'IOC.NS',
        'bharat_petroleum': 'BPCL.NS',
        'hindustan_petroleum': 'HINDPETRO.NS',
        'gail': 'GAIL.NS',
        'petronet_lng': 'PETRONET.NS',
        
        # Metals & Mining
        'tata_steel': 'TATASTEEL.NS',
        'jsw_steel': 'JSWSTEEL.NS',
        'hindalco': 'HINDALCO.NS',
        'vedanta': 'VEDL.NS',
        'coal_india': 'COALINDIA.NS',
        'nmdc': 'NMDC.NS',
        'sail': 'SAIL.NS',
        
        # Infrastructure & Construction
        'larsen_toubro': 'LT.NS',
        'adani_ports': 'ADANIPORTS.NS',
        'ultra_cement': 'ULTRACEMCO.NS',
        'shree_cement': 'SHREECEM.NS',
        'grasim': 'GRASIM.NS',
        'ambuja_cement': 'AMBUJACEM.NS',
        'acc': 'ACC.NS',
        
        # Telecom
        'bharti_airtel': 'BHARTIARTL.NS',
        'vodafone_idea': 'IDEA.NS',
        
        # Power & Utilities
        'ntpc': 'NTPC.NS',
        'power_grid': 'POWERGRID.NS',
        'tata_power': 'TATAPOWER.NS',
        'adani_green': 'ADANIGREEN.NS',
        'adani_transmission': 'ADANITRANS.NS',
        
        # Media & Entertainment
        'zee_entertainment': 'ZEEL.NS',
        'sun_tv': 'SUNTV.NS',
        'network18': 'NETWORK18.NS',
        
        # Real Estate
        'dlf': 'DLF.NS',
        'godrej_properties': 'GODREJPROP.NS',
        'brigade_enterprises': 'BRIGADE.NS',
        
        # Indian ETFs
        'nifty_50': 'NIFTY50.NS',
        'nifty_bank': 'NIFTYBANK.NS',
        'sensex': 'SENSEX.NS',
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
