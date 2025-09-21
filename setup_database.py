#!/usr/bin/env python3
"""
Database setup script for Financial Analysis System
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

from web_app import app, db
from models import User, Portfolio, Holding, Transaction, AnalysisRecommendation

def setup_database():
    """Set up the database tables"""
    print("🗄️  Setting up database...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if we can connect
            db.session.execute('SELECT 1')
            print("✅ Database connection verified")
            
            return True
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False

def create_sample_data():
    """Create sample data for testing"""
    print("\n📊 Creating sample data...")
    
    with app.app_context():
        try:
            # Check if sample user already exists
            existing_user = User.query.filter_by(username='demo_user').first()
            if existing_user:
                print("ℹ️  Sample user already exists, skipping sample data creation")
                return True
            
            # Create sample user
            user = User(
                username='demo_user',
                email='demo@example.com',
                first_name='Demo',
                last_name='User'
            )
            user.set_password('demo123')
            
            db.session.add(user)
            db.session.commit()
            
            print("✅ Sample user created: demo_user / demo123")
            
            # Create sample portfolio
            portfolio = Portfolio(
                user_id=user.id,
                name='My Investment Portfolio',
                description='A sample portfolio for testing the system'
            )
            
            db.session.add(portfolio)
            db.session.commit()
            
            print("✅ Sample portfolio created")
            
            # Create sample holdings
            sample_holdings = [
                {
                    'asset_symbol': 'gold',
                    'asset_name': 'Gold',
                    'asset_type': 'commodity',
                    'quantity': 10.0,
                    'avg_cost_per_share': 1800.0,
                    'current_price': 1850.0
                },
                {
                    'asset_symbol': 'apple',
                    'asset_name': 'Apple Inc.',
                    'asset_type': 'stock',
                    'quantity': 50.0,
                    'avg_cost_per_share': 150.0,
                    'current_price': 155.0
                },
                {
                    'asset_symbol': 'tesla',
                    'asset_name': 'Tesla Inc.',
                    'asset_type': 'stock',
                    'quantity': 25.0,
                    'avg_cost_per_share': 200.0,
                    'current_price': 190.0
                }
            ]
            
            for holding_data in sample_holdings:
                holding = Holding(
                    portfolio_id=portfolio.id,
                    **holding_data
                )
                db.session.add(holding)
            
            db.session.commit()
            
            print("✅ Sample holdings created")
            print("\n🎉 Sample data setup complete!")
            print("   You can now log in with:")
            print("   Username: demo_user")
            print("   Password: demo123")
            
            return True
            
        except Exception as e:
            print(f"❌ Sample data creation failed: {e}")
            db.session.rollback()
            return False

def main():
    """Main setup function"""
    print("🚀 Financial Analysis System - Database Setup")
    print("=" * 50)
    
    # Check environment variables
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/financial_analyzer')
    print(f"📋 Database URL: {database_url}")
    
    if 'postgresql://localhost/financial_analyzer' in database_url:
        print("⚠️  Warning: Using default database URL")
        print("   Please set DATABASE_URL environment variable for production")
    
    # Setup database
    if not setup_database():
        print("\n❌ Database setup failed. Please check your PostgreSQL connection.")
        return 1
    
    # Create sample data
    create_sample = input("\n📊 Create sample data for testing? (y/n): ").lower().strip()
    if create_sample in ['y', 'yes']:
        if not create_sample_data():
            print("\n❌ Sample data creation failed.")
            return 1
    
    print("\n✅ Database setup completed successfully!")
    print("\n🌐 You can now start the web application with:")
    print("   python web_app.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
