"""
Database models for user authentication and portfolio tracking
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
from typing import Dict, List, Optional
import json

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password: str):
        """Set password hash"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check password"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Portfolio(db.Model):
    """Portfolio model for tracking user investments"""
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    holdings = db.relationship('Holding', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    
    def get_total_value(self) -> float:
        """Calculate total portfolio value"""
        return sum(holding.current_value for holding in self.holdings if holding.is_active)
    
    def get_total_cost(self) -> float:
        """Calculate total cost basis"""
        return sum(holding.total_cost for holding in self.holdings if holding.is_active)
    
    def get_total_gain_loss(self) -> float:
        """Calculate total gain/loss"""
        return self.get_total_value() - self.get_total_cost()
    
    def get_total_gain_loss_percent(self) -> float:
        """Calculate total gain/loss percentage"""
        total_cost = self.get_total_cost()
        if total_cost == 0:
            return 0.0
        return (self.get_total_gain_loss() / total_cost) * 100
    
    def get_holdings_summary(self) -> Dict:
        """Get portfolio holdings summary"""
        holdings = [h for h in self.holdings if h.is_active]
        
        summary = {
            'total_holdings': len(holdings),
            'total_value': self.get_total_value(),
            'total_cost': self.get_total_cost(),
            'total_gain_loss': self.get_total_gain_loss(),
            'total_gain_loss_percent': self.get_total_gain_loss_percent(),
            'holdings_by_asset': {}
        }
        
        for holding in holdings:
            asset = holding.asset_symbol
            if asset not in summary['holdings_by_asset']:
                summary['holdings_by_asset'][asset] = {
                    'quantity': 0,
                    'total_value': 0,
                    'total_cost': 0,
                    'avg_price': 0
                }
            
            summary['holdings_by_asset'][asset]['quantity'] += holding.quantity
            summary['holdings_by_asset'][asset]['total_value'] += holding.current_value
            summary['holdings_by_asset'][asset]['total_cost'] += holding.total_cost
        
        # Calculate average prices
        for asset_data in summary['holdings_by_asset'].values():
            if asset_data['quantity'] > 0:
                asset_data['avg_price'] = float(asset_data['total_cost']) / float(asset_data['quantity'])
        
        return summary
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'summary': self.get_holdings_summary()
        }
    
    def __repr__(self):
        return f'<Portfolio {self.name}>'

class Holding(db.Model):
    """Individual holding within a portfolio"""
    __tablename__ = 'holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    asset_symbol = db.Column(db.String(20), nullable=False, index=True)
    asset_name = db.Column(db.String(100), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # 'stock', 'commodity', 'crypto', etc.
    quantity = db.Column(db.Numeric(15, 6), nullable=False, default=0)
    avg_cost_per_share = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    current_price = db.Column(db.Numeric(10, 4), nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Calculated properties
    @property
    def total_cost(self) -> float:
        """Total cost basis for this holding"""
        return float(self.quantity * self.avg_cost_per_share)
    
    @property
    def current_value(self) -> float:
        """Current market value"""
        if self.current_price is None:
            return 0.0
        return float(self.quantity * self.current_price)
    
    @property
    def gain_loss(self) -> float:
        """Gain/loss amount"""
        return self.current_value - self.total_cost
    
    @property
    def gain_loss_percent(self) -> float:
        """Gain/loss percentage"""
        if self.total_cost == 0:
            return 0.0
        return (self.gain_loss / self.total_cost) * 100
    
    def update_price(self, new_price: float):
        """Update current price"""
        self.current_price = new_price
        self.last_updated = datetime.utcnow()
    
    def add_shares(self, quantity: float, price: float):
        """Add shares to holding (for purchases)"""
        if quantity <= 0:
            return
        
        # Calculate new average cost
        total_cost = self.total_cost + (quantity * price)
        total_quantity = float(self.quantity) + quantity
        self.avg_cost_per_share = total_cost / total_quantity
        self.quantity = total_quantity
        self.last_updated = datetime.utcnow()
    
    def remove_shares(self, quantity: float):
        """Remove shares from holding (for sales)"""
        if quantity <= 0 or quantity > float(self.quantity):
            return
        
        self.quantity = float(self.quantity) - quantity
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'asset_symbol': self.asset_symbol,
            'asset_name': self.asset_name,
            'asset_type': self.asset_type,
            'quantity': float(self.quantity),
            'avg_cost_per_share': float(self.avg_cost_per_share),
            'current_price': float(self.current_price) if self.current_price else None,
            'total_cost': self.total_cost,
            'current_value': self.current_value,
            'gain_loss': self.gain_loss,
            'gain_loss_percent': self.gain_loss_percent,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Holding {self.asset_symbol}: {self.quantity} shares>'

class Transaction(db.Model):
    """Transaction history for portfolio tracking"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    holding_id = db.Column(db.Integer, db.ForeignKey('holdings.id'), nullable=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'buy', 'sell', 'dividend', 'split'
    asset_symbol = db.Column(db.String(20), nullable=False, index=True)
    asset_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Numeric(15, 6), nullable=False)
    price_per_share = db.Column(db.Numeric(10, 4), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    fees = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'portfolio_id': self.portfolio_id,
            'holding_id': self.holding_id,
            'transaction_type': self.transaction_type,
            'asset_symbol': self.asset_symbol,
            'asset_name': self.asset_name,
            'quantity': float(self.quantity),
            'price_per_share': float(self.price_per_share),
            'total_amount': float(self.total_amount),
            'fees': float(self.fees) if self.fees else 0,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.asset_symbol}: {self.quantity} @ {self.price_per_share}>'

class AnalysisRecommendation(db.Model):
    """Store AI analysis recommendations for portfolio optimization"""
    __tablename__ = 'analysis_recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=True)
    asset_symbol = db.Column(db.String(20), nullable=False, index=True)
    analysis_type = db.Column(db.String(50), nullable=False)  # 'sentiment', 'technical', 'ai_decision'
    recommendation = db.Column(db.String(20), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    confidence = db.Column(db.Numeric(5, 4), nullable=False)  # 0.0 to 1.0
    target_price = db.Column(db.Numeric(10, 4), nullable=True)
    stop_loss = db.Column(db.Numeric(10, 4), nullable=True)
    reasoning = db.Column(db.Text, nullable=True)
    analysis_data = db.Column(db.JSON, nullable=True)  # Store full analysis results
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'portfolio_id': self.portfolio_id,
            'asset_symbol': self.asset_symbol,
            'analysis_type': self.analysis_type,
            'recommendation': self.recommendation,
            'confidence': float(self.confidence),
            'target_price': float(self.target_price) if self.target_price else None,
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'reasoning': self.reasoning,
            'analysis_data': self.analysis_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<AnalysisRecommendation {self.asset_symbol}: {self.recommendation} ({self.confidence:.0%})>'
