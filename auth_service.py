"""
Authentication and portfolio management service
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from models import db, User, Portfolio, Holding, Transaction, AnalysisRecommendation
from config import Config

logger = logging.getLogger(__name__)

class AuthService:
    """Service for user authentication and management"""
    
    @staticmethod
    def register_user(username: str, email: str, password: str, 
                     first_name: str = None, last_name: str = None) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user
        
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Check if user already exists
            if User.query.filter(or_(User.username == username, User.email == email)).first():
                return False, "Username or email already exists", None
            
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {username}")
            return True, "User registered successfully", user
            
        except IntegrityError:
            db.session.rollback()
            return False, "Username or email already exists", None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {e}")
            return False, f"Registration failed: {str(e)}", None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get user by email address
        
        Args:
            email: User's email address
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return User.query.filter_by(email=email).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate a user
        
        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Find user by username or email
            user = User.query.filter(
                or_(User.username == username_or_email, User.email == username_or_email)
            ).first()
            
            if not user:
                return False, "Invalid credentials", None
            
            if not user.is_active:
                return False, "Account is deactivated", None
            
            if not user.check_password(password):
                return False, "Invalid credentials", None
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"User authenticated: {user.username}")
            return True, "Authentication successful", user
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return False, f"Authentication failed: {str(e)}", None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def update_user_profile(user_id: int, **kwargs) -> Tuple[bool, str]:
        """Update user profile"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            allowed_fields = ['first_name', 'last_name', 'email']
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(user, field, value)
            
            db.session.commit()
            return True, "Profile updated successfully"
            
        except IntegrityError:
            db.session.rollback()
            return False, "Email already exists"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user profile: {e}")
            return False, f"Update failed: {str(e)}"
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            if not user.check_password(old_password):
                return False, "Current password is incorrect"
            
            user.set_password(new_password)
            db.session.commit()
            
            logger.info(f"Password changed for user: {user.username}")
            return True, "Password changed successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error changing password: {e}")
            return False, f"Password change failed: {str(e)}"

class PortfolioService:
    """Service for portfolio management"""
    
    @staticmethod
    def create_portfolio(user_id: int, name: str, description: str = None) -> Tuple[bool, str, Optional[Portfolio]]:
        """Create a new portfolio"""
        try:
            portfolio = Portfolio(
                user_id=user_id,
                name=name,
                description=description
            )
            
            db.session.add(portfolio)
            db.session.commit()
            
            logger.info(f"Portfolio created: {name} for user {user_id}")
            return True, "Portfolio created successfully", portfolio
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating portfolio: {e}")
            return False, f"Portfolio creation failed: {str(e)}", None
    
    @staticmethod
    def get_user_portfolios(user_id: int) -> List[Portfolio]:
        """Get all portfolios for a user"""
        return Portfolio.query.filter_by(user_id=user_id, is_active=True).all()
    
    @staticmethod
    def get_portfolio(user_id: int, portfolio_id: int) -> Optional[Portfolio]:
        """Get a specific portfolio"""
        return Portfolio.query.filter_by(
            id=portfolio_id, 
            user_id=user_id, 
            is_active=True
        ).first()
    
    @staticmethod
    def update_portfolio(user_id: int, portfolio_id: int, **kwargs) -> Tuple[bool, str]:
        """Update portfolio"""
        try:
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return False, "Portfolio not found"
            
            allowed_fields = ['name', 'description']
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    setattr(portfolio, field, value)
            
            portfolio.updated_at = datetime.utcnow()
            db.session.commit()
            
            return True, "Portfolio updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating portfolio: {e}")
            return False, f"Update failed: {str(e)}"
    
    @staticmethod
    def delete_portfolio(user_id: int, portfolio_id: int) -> Tuple[bool, str]:
        """Delete portfolio (soft delete)"""
        try:
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return False, "Portfolio not found"
            
            portfolio.is_active = False
            portfolio.updated_at = datetime.utcnow()
            
            # Also deactivate all holdings
            for holding in portfolio.holdings:
                holding.is_active = False
            
            db.session.commit()
            
            logger.info(f"Portfolio deleted: {portfolio.name}")
            return True, "Portfolio deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting portfolio: {e}")
            return False, f"Delete failed: {str(e)}"
    
    @staticmethod
    def add_holding(user_id: int, portfolio_id: int, asset_symbol: str, 
                   asset_name: str, asset_type: str, quantity: float, 
                   price_per_share: float, transaction_date: datetime = None) -> Tuple[bool, str, Optional[Holding]]:
        """Add or update a holding in a portfolio"""
        try:
            # Verify portfolio ownership
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return False, "Portfolio not found", None
            
            # Check if holding already exists
            holding = Holding.query.filter_by(
                portfolio_id=portfolio_id,
                asset_symbol=asset_symbol,
                is_active=True
            ).first()
            
            if holding:
                # Update existing holding
                holding.add_shares(quantity, price_per_share)
                holding.asset_name = asset_name  # Update name in case it changed
                holding.asset_type = asset_type
            else:
                # Create new holding
                holding = Holding(
                    portfolio_id=portfolio_id,
                    asset_symbol=asset_symbol,
                    asset_name=asset_name,
                    asset_type=asset_type,
                    quantity=quantity,
                    avg_cost_per_share=price_per_share
                )
                db.session.add(holding)
            
            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                portfolio_id=portfolio_id,
                holding_id=holding.id,
                transaction_type='buy',
                asset_symbol=asset_symbol,
                asset_name=asset_name,
                quantity=quantity,
                price_per_share=price_per_share,
                total_amount=quantity * price_per_share,
                transaction_date=transaction_date or datetime.utcnow()
            )
            db.session.add(transaction)
            
            db.session.commit()
            
            logger.info(f"Holding added: {asset_symbol} to portfolio {portfolio_id}")
            return True, "Holding added successfully", holding
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding holding: {e}")
            return False, f"Add holding failed: {str(e)}", None
    
    @staticmethod
    def remove_holding(user_id: int, portfolio_id: int, asset_symbol: str, 
                      quantity: float, price_per_share: float, 
                      transaction_date: datetime = None) -> Tuple[bool, str]:
        """Remove shares from a holding (sell)"""
        try:
            # Verify portfolio ownership
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return False, "Portfolio not found"
            
            # Find holding
            holding = Holding.query.filter_by(
                portfolio_id=portfolio_id,
                asset_symbol=asset_symbol,
                is_active=True
            ).first()
            
            if not holding:
                return False, "Holding not found"
            
            if holding.quantity < quantity:
                return False, "Insufficient shares to sell"
            
            # Update holding
            holding.remove_shares(quantity)
            
            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                portfolio_id=portfolio_id,
                holding_id=holding.id,
                transaction_type='sell',
                asset_symbol=asset_symbol,
                asset_name=holding.asset_name,
                quantity=quantity,
                price_per_share=price_per_share,
                total_amount=quantity * price_per_share,
                transaction_date=transaction_date or datetime.utcnow()
            )
            db.session.add(transaction)
            
            db.session.commit()
            
            logger.info(f"Holding reduced: {asset_symbol} from portfolio {portfolio_id}")
            return True, "Shares sold successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing holding: {e}")
            return False, f"Sell failed: {str(e)}"
    
    @staticmethod
    def get_portfolio_holdings(user_id: int, portfolio_id: int) -> List[Holding]:
        """Get all holdings for a portfolio"""
        # Verify portfolio ownership
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not portfolio:
            return []
        
        return Holding.query.filter_by(
            portfolio_id=portfolio_id,
            is_active=True
        ).all()
    
    @staticmethod
    def get_portfolio_transactions(user_id: int, portfolio_id: int, limit: int = 50) -> List[Transaction]:
        """Get transaction history for a portfolio"""
        # Verify portfolio ownership
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not portfolio:
            return []
        
        return Transaction.query.filter_by(
            portfolio_id=portfolio_id
        ).order_by(Transaction.transaction_date.desc()).limit(limit).all()
    
    @staticmethod
    def update_holding_prices(user_id: int, portfolio_id: int, price_updates: Dict[str, float]) -> Tuple[bool, str]:
        """Update current prices for holdings"""
        try:
            # Verify portfolio ownership
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return False, "Portfolio not found"
            
            # Update prices for holdings
            updated_count = 0
            for asset_symbol, new_price in price_updates.items():
                holding = Holding.query.filter_by(
                    portfolio_id=portfolio_id,
                    asset_symbol=asset_symbol,
                    is_active=True
                ).first()
                
                if holding:
                    holding.update_price(new_price)
                    updated_count += 1
            
            db.session.commit()
            
            logger.info(f"Updated prices for {updated_count} holdings in portfolio {portfolio_id}")
            return True, f"Updated prices for {updated_count} holdings"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating holding prices: {e}")
            return False, f"Price update failed: {str(e)}"

class AnalysisService:
    """Service for storing and retrieving analysis recommendations"""
    
    @staticmethod
    def store_recommendation(user_id: int, portfolio_id: int, asset_symbol: str,
                           analysis_type: str, recommendation: str, confidence: float,
                           target_price: float = None, stop_loss: float = None,
                           reasoning: str = None, analysis_data: Dict = None,
                           expires_hours: int = 24) -> Tuple[bool, str, Optional[AnalysisRecommendation]]:
        """Store an analysis recommendation"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            recommendation_obj = AnalysisRecommendation(
                user_id=user_id,
                portfolio_id=portfolio_id,
                asset_symbol=asset_symbol,
                analysis_type=analysis_type,
                recommendation=recommendation,
                confidence=confidence,
                target_price=target_price,
                stop_loss=stop_loss,
                reasoning=reasoning,
                analysis_data=analysis_data,
                expires_at=expires_at
            )
            
            db.session.add(recommendation_obj)
            db.session.commit()
            
            logger.info(f"Analysis recommendation stored: {asset_symbol} - {recommendation}")
            return True, "Recommendation stored successfully", recommendation_obj
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing recommendation: {e}")
            return False, f"Storage failed: {str(e)}", None
    
    @staticmethod
    def get_user_recommendations(user_id: int, portfolio_id: int = None, 
                               asset_symbol: str = None, limit: int = 50) -> List[AnalysisRecommendation]:
        """Get analysis recommendations for a user"""
        query = AnalysisRecommendation.query.filter_by(
            user_id=user_id,
            is_active=True
        )
        
        if portfolio_id:
            query = query.filter_by(portfolio_id=portfolio_id)
        
        if asset_symbol:
            query = query.filter_by(asset_symbol=asset_symbol)
        
        return query.filter(
            AnalysisRecommendation.expires_at > datetime.utcnow()
        ).order_by(AnalysisRecommendation.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_portfolio_analysis_summary(user_id: int, portfolio_id: int) -> Dict:
        """Get analysis summary for a portfolio"""
        try:
            # Verify portfolio ownership
            portfolio = Portfolio.query.filter_by(
                id=portfolio_id, 
                user_id=user_id, 
                is_active=True
            ).first()
            
            if not portfolio:
                return {}
            
            # Get recent recommendations for portfolio holdings
            holdings = PortfolioService.get_portfolio_holdings(user_id, portfolio_id)
            asset_symbols = [h.asset_symbol for h in holdings]
            
            recommendations = AnalysisRecommendation.query.filter(
                AnalysisRecommendation.user_id == user_id,
                AnalysisRecommendation.portfolio_id == portfolio_id,
                AnalysisRecommendation.asset_symbol.in_(asset_symbols),
                AnalysisRecommendation.is_active == True,
                AnalysisRecommendation.expires_at > datetime.utcnow()
            ).order_by(AnalysisRecommendation.created_at.desc()).all()
            
            # Group by asset
            analysis_by_asset = {}
            for rec in recommendations:
                if rec.asset_symbol not in analysis_by_asset:
                    analysis_by_asset[rec.asset_symbol] = []
                analysis_by_asset[rec.asset_symbol].append(rec)
            
            # Create summary
            summary = {
                'portfolio_id': portfolio_id,
                'total_holdings': len(holdings),
                'holdings_with_analysis': len(analysis_by_asset),
                'analysis_by_asset': {}
            }
            
            for asset_symbol, recs in analysis_by_asset.items():
                # Get latest recommendation
                latest_rec = recs[0]
                summary['analysis_by_asset'][asset_symbol] = {
                    'latest_recommendation': latest_rec.recommendation,
                    'confidence': float(latest_rec.confidence),
                    'target_price': float(latest_rec.target_price) if latest_rec.target_price else None,
                    'stop_loss': float(latest_rec.stop_loss) if latest_rec.stop_loss else None,
                    'reasoning': latest_rec.reasoning,
                    'created_at': latest_rec.created_at.isoformat(),
                    'total_recommendations': len(recs)
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting portfolio analysis summary: {e}")
            return {}
