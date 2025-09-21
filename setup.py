"""
Setup script for Commodity Market Analysis System
"""
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
        return True

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ All packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("\n📄 Creating .env file from template...")
            env_file.write_text(env_example.read_text())
            print("✅ .env file created")
            print("⚠️  Please edit .env file with your API keys and configuration")
        else:
            print("❌ .env.example file not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def create_results_directory():
    """Create results directory for saving analysis outputs"""
    results_dir = Path("results")
    
    if not results_dir.exists():
        results_dir.mkdir()
        print("✅ Created results directory")
    else:
        print("✅ Results directory already exists")
    
    return True

def validate_env_file():
    """Validate .env file configuration"""
    print("\n🔧 Validating configuration...")
    
    try:
        from config import Config
        config = Config()
        
        # Check required fields
        required_fields = [
            ('GEMINI_API_KEY', 'Gemini AI API Key'),
            ('EMAIL_ADDRESS', 'Email Address'),
            ('EMAIL_PASSWORD', 'Email Password'),
            ('BROKER_EMAIL', 'Broker Email')
        ]
        
        missing_fields = []
        for field, description in required_fields:
            value = getattr(config, field, None)
            if not value:
                missing_fields.append(f"  - {field} ({description})")
            else:
                print(f"✅ {description}: {'*' * min(len(str(value)), 8)}...")
        
        if missing_fields:
            print("⚠️  Missing required configuration:")
            for field in missing_fields:
                print(field)
            print("\n   Please edit .env file with your credentials")
            return False
        else:
            print("✅ All required configuration present")
            return True
            
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    print("\n🧪 Testing module imports...")
    
    modules = [
        'torch',
        'transformers',
        'pandas',
        'numpy',
        'requests',
        'yfinance',
        'google.generativeai',
        'nltk'
    ]
    
    failed_imports = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("   Try running: pip install -r requirements.txt")
        return False
    else:
        print("✅ All modules imported successfully")
        return True

def download_nltk_data():
    """Download required NLTK data"""
    print("\n📚 Downloading NLTK data...")
    
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✅ NLTK data downloaded")
        return True
    except Exception as e:
        print(f"❌ Failed to download NLTK data: {e}")
        return False

def test_basic_functionality():
    """Test basic system functionality"""
    print("\n🔍 Testing basic functionality...")
    
    try:
        # Test configuration loading
        from config import Config
        config = Config()
        
        # Test available commodities
        commodities = list(config.COMMODITY_SYMBOLS.keys())
        print(f"✅ Found {len(commodities)} available commodities")
        
        # Test utility functions
        from utils import validate_commodity_name, validate_timeframe
        
        # Test commodity validation
        test_commodity = validate_commodity_name("gold")
        assert test_commodity == "gold"
        
        # Test timeframe validation
        test_timeframe = validate_timeframe(30)
        assert test_timeframe == 30
        
        print("✅ Basic functionality tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def print_next_steps():
    """Print next steps for user"""
    print("\n" + "="*60)
    print("🎉 Setup completed successfully!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your API keys:")
    print("   - Get Gemini API key from: https://aistudio.google.com/app/apikey")
    print("   - Configure your email SMTP settings")
    print("   - Set your broker's email address")
    
    print("\n2. Test the system:")
    print("   python main.py --list-commodities")
    print("   python main.py --commodity gold --timeframe 7 --no-email --save-results")
    
    print("\n3. Run full analysis:")
    print("   python main.py --commodity gold --timeframe 30 --email")
    
    print("\n📖 For more information, see README.md")
    print("\n⚠️  Remember: This is for educational purposes only!")
    print("   Always do your own research before making investment decisions.")

def main():
    """Main setup function"""
    print("🚀 Commodity Market Analysis System Setup")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Create results directory
    if not create_results_directory():
        sys.exit(1)
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    # Download NLTK data
    if not download_nltk_data():
        sys.exit(1)
    
    # Test basic functionality
    if not test_basic_functionality():
        sys.exit(1)
    
    # Validate configuration (optional - may fail if not configured yet)
    validate_env_file()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
