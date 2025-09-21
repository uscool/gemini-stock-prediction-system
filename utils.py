"""
Utility functions and error handling for the Commodity Market Analyzer
"""
import logging
import traceback
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime
import asyncio
import aiohttp
from aiohttp import ClientTimeout, ClientError
import time
import json

logger = logging.getLogger(__name__)

class CommodityAnalysisError(Exception):
    """Base exception for commodity analysis errors"""
    pass

class ConfigurationError(CommodityAnalysisError):
    """Configuration-related errors"""
    pass

class DataFetchError(CommodityAnalysisError):
    """Data fetching and processing errors"""
    pass

class AIAnalysisError(CommodityAnalysisError):
    """AI/ML analysis errors"""
    pass

class EmailError(CommodityAnalysisError):
    """Email sending errors"""
    pass

def error_handler(default_return=None, log_error=True):
    """
    Decorator for comprehensive error handling
    
    Args:
        default_return: Default value to return on error
        log_error: Whether to log the error
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                # Return error information in a structured format
                if default_return is None:
                    return {
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'function': func.__name__,
                        'timestamp': datetime.now().isoformat()
                    }
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if default_return is None:
                    return {
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'function': func.__name__,
                        'timestamp': datetime.now().isoformat()
                    }
                return default_return
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def retry_on_failure(max_attempts=3, delay=1.0, backoff_factor=2.0, 
                    exceptions=(Exception,)):
    """
    Decorator for retrying failed operations
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Factor to multiply delay by after each failure
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        """Acquire permission to make a request"""
        now = time.time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.acquire()
        
        # Record this request
        self.requests.append(now)

class SafeHTTPSession:
    """Safe HTTP session with timeouts and error handling"""
    
    def __init__(self, timeout=30, max_retries=3):
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @retry_on_failure(max_attempts=3, exceptions=(ClientError, asyncio.TimeoutError))
    async def get(self, url, **kwargs):
        """Safe GET request with retries"""
        if not self.session:
            raise RuntimeError("Session not initialized - use as context manager")
        
        try:
            async with self.session.get(url, **kwargs) as response:
                response.raise_for_status()
                return response
        except Exception as e:
            logger.error(f"HTTP GET error for {url}: {e}")
            raise

def validate_commodity_name(commodity: str) -> str:
    """
    Validate and normalize commodity name
    
    Args:
        commodity: Commodity name to validate
        
    Returns:
        Normalized commodity name
        
    Raises:
        ValueError: If commodity name is invalid
    """
    if not commodity or not isinstance(commodity, str):
        raise ValueError("Commodity name must be a non-empty string")
    
    # Normalize the name
    normalized = commodity.lower().strip().replace(' ', '_').replace('-', '_')
    
    # Basic validation
    if not normalized.isalnum() and '_' not in normalized:
        raise ValueError(f"Invalid commodity name format: {commodity}")
    
    return normalized

def validate_timeframe(timeframe_days: int) -> int:
    """
    Validate timeframe parameter
    
    Args:
        timeframe_days: Number of days for analysis
        
    Returns:
        Validated timeframe
        
    Raises:
        ValueError: If timeframe is invalid
    """
    if not isinstance(timeframe_days, int):
        try:
            timeframe_days = int(timeframe_days)
        except (ValueError, TypeError):
            raise ValueError("Timeframe must be an integer")
    
    if timeframe_days < 1:
        raise ValueError("Timeframe must be at least 1 day")
    
    if timeframe_days > 365:
        raise ValueError("Timeframe cannot exceed 365 days")
    
    return timeframe_days

def validate_email_address(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email pattern check
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert {value} to float, using default {default}")
        return default

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Int value or default
    """
    try:
        if value is None or value == '':
            return default
        return int(float(value))  # Handle string floats like "3.0"
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert {value} to int, using default {default}")
        return default

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system operations
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized

def format_currency(amount: float, currency_symbol: str = '$') -> str:
    """
    Format currency amount for display
    
    Args:
        amount: Amount to format
        currency_symbol: Currency symbol
        
    Returns:
        Formatted currency string
    """
    try:
        if abs(amount) >= 1000000:
            return f"{currency_symbol}{amount/1000000:.2f}M"
        elif abs(amount) >= 1000:
            return f"{currency_symbol}{amount/1000:.2f}K"
        else:
            return f"{currency_symbol}{amount:.2f}"
    except (TypeError, ValueError):
        return f"{currency_symbol}0.00"

def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    Format percentage for display
    
    Args:
        value: Value to format (as decimal, e.g., 0.05 for 5%)
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    try:
        return f"{value * 100:.{decimal_places}f}%"
    except (TypeError, ValueError):
        return "0.00%"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change (as decimal)
    """
    try:
        if old_value == 0:
            return 0.0 if new_value == 0 else float('inf')
        return (new_value - old_value) / old_value
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging
    
    Returns:
        Dictionary with system information
    """
    import platform
    import sys
    import psutil
    
    try:
        return {
            'platform': platform.platform(),
            'python_version': sys.version,
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {'error': str(e)}

class PerformanceMonitor:
    """Monitor performance of operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            logger.info(f"Completed {self.operation_name} in {duration:.2f} seconds")
        else:
            logger.error(f"Failed {self.operation_name} after {duration:.2f} seconds: {exc_val}")
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

def create_safe_json_encoder():
    """Create JSON encoder that handles special types safely"""
    
    class SafeJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                if hasattr(obj, 'isoformat'):  # datetime objects
                    return obj.isoformat()
                elif hasattr(obj, '__dict__'):  # custom objects
                    return obj.__dict__
                elif isinstance(obj, (set, frozenset)):
                    return list(obj)
                else:
                    return str(obj)
            except Exception:
                return f"<{type(obj).__name__} object>"
    
    return SafeJSONEncoder

def log_function_call(func: Callable) -> Callable:
    """Decorator to log function calls with parameters and results"""
    
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"Calling {func_name} with args={args[:2]}... kwargs={list(kwargs.keys())}")
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func_name} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func_name} failed after {duration:.3f}s: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"Calling {func_name} with args={args[:2]}... kwargs={list(kwargs.keys())}")
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func_name} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func_name} failed after {duration:.3f}s: {e}")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
