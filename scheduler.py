"""
Scheduler for periodic financial analysis and email notifications
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import uuid

from main import CommodityMarketAnalyzer
from config import Config

logger = logging.getLogger(__name__)

class AnalysisScheduler:
    """Manages scheduled analysis tasks"""
    
    def __init__(self):
        self.schedules_file = Path('schedules.json')
        self.schedules = self._load_schedules()
        self.running = False
        self.scheduler_thread = None
        self.analyzer = None
        self._initialize_analyzer()
    
    def _initialize_analyzer(self):
        """Initialize the market analyzer"""
        try:
            self.analyzer = CommodityMarketAnalyzer()
            logger.info("Scheduler analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing scheduler analyzer: {e}")
            self.analyzer = None
    
    def _load_schedules(self) -> Dict:
        """Load schedules from file"""
        try:
            if self.schedules_file.exists():
                with open(self.schedules_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading schedules: {e}")
            return {}
    
    def _save_schedules(self):
        """Save schedules to file"""
        try:
            with open(self.schedules_file, 'w') as f:
                json.dump(self.schedules, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving schedules: {e}")
    
    def create_schedule(self, name: str, assets: List[str], timeframe: int = 30,
                       frequency: str = 'daily', time_of_day: str = '09:00',
                       risk_tolerance: str = 'moderate', send_email: bool = True,
                       enabled: bool = True, user_email: str = None) -> str:
        """
        Create a new analysis schedule
        
        Args:
            name: Human-readable name for the schedule
            assets: List of assets to analyze
            timeframe: Analysis timeframe in days
            frequency: 'daily', 'weekly', 'monthly'
            time_of_day: Time to run (HH:MM format)
            risk_tolerance: Risk tolerance level
            send_email: Whether to send email notifications
            enabled: Whether the schedule is active
            user_email: User's email for portfolio context (optional)
            
        Returns:
            Schedule ID
        """
        schedule_id = str(uuid.uuid4())
        
        schedule = {
            'id': schedule_id,
            'name': name,
            'assets': assets,
            'timeframe': timeframe,
            'frequency': frequency,
            'time_of_day': time_of_day,
            'risk_tolerance': risk_tolerance,
            'send_email': send_email,
            'enabled': enabled,
            'user_email': user_email,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'next_run': self._calculate_next_run(frequency, time_of_day),
            'run_count': 0,
            'success_count': 0,
            'error_count': 0
        }
        
        self.schedules[schedule_id] = schedule
        self._save_schedules()
        
        logger.info(f"Created schedule '{name}' for assets: {', '.join(assets)}")
        return schedule_id
    
    def update_schedule(self, schedule_id: str, **kwargs) -> bool:
        """Update an existing schedule"""
        if schedule_id not in self.schedules:
            return False
        
        schedule = self.schedules[schedule_id]
        
        # Update allowed fields
        allowed_fields = ['name', 'assets', 'timeframe', 'frequency', 'time_of_day',
                         'risk_tolerance', 'send_email', 'enabled']
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                schedule[field] = value
        
        # Recalculate next run if frequency or time changed
        if 'frequency' in kwargs or 'time_of_day' in kwargs:
            schedule['next_run'] = self._calculate_next_run(
                schedule['frequency'], schedule['time_of_day']
            )
        
        self._save_schedules()
        logger.info(f"Updated schedule {schedule_id}")
        return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule"""
        if schedule_id in self.schedules:
            schedule_name = self.schedules[schedule_id]['name']
            del self.schedules[schedule_id]
            self._save_schedules()
            logger.info(f"Deleted schedule '{schedule_name}' ({schedule_id})")
            return True
        return False
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        """Get a specific schedule"""
        return self.schedules.get(schedule_id)
    
    def get_all_schedules(self) -> Dict:
        """Get all schedules"""
        return self.schedules.copy()
    
    def get_enabled_schedules(self) -> Dict:
        """Get only enabled schedules"""
        return {sid: sched for sid, sched in self.schedules.items() if sched.get('enabled', True)}
    
    def _calculate_next_run(self, frequency: str, time_of_day: str) -> str:
        """Calculate the next run time for a schedule"""
        try:
            hour, minute = map(int, time_of_day.split(':'))
            now = datetime.now()
            
            if frequency == 'daily':
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            
            elif frequency == 'weekly':
                # Run on Monday of next week
                days_ahead = 7 - now.weekday()  # Monday is 0
                if days_ahead == 7:  # Today is Monday
                    days_ahead = 0
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            elif frequency == 'monthly':
                # Run on the 1st of next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1, 
                                         hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1, 
                                         hour=hour, minute=minute, second=0, microsecond=0)
            
            else:
                # Default to daily
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            
            return next_run.isoformat()
            
        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            # Default to tomorrow at the same time
            return (datetime.now() + timedelta(days=1)).isoformat()
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        if not self.analyzer:
            logger.error("Cannot start scheduler: analyzer not initialized")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Analysis scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Analysis scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                now = datetime.now()
                enabled_schedules = self.get_enabled_schedules()
                
                for schedule_id, schedule in enabled_schedules.items():
                    try:
                        next_run = datetime.fromisoformat(schedule['next_run'])
                        
                        # Check if it's time to run this schedule
                        if now >= next_run:
                            logger.info(f"Running scheduled analysis: {schedule['name']}")
                            
                            # Run the analysis in a separate thread to avoid blocking
                            analysis_thread = threading.Thread(
                                target=self._run_scheduled_analysis,
                                args=(schedule_id, schedule),
                                daemon=True
                            )
                            analysis_thread.start()
                            
                            # Update next run time
                            schedule['next_run'] = self._calculate_next_run(
                                schedule['frequency'], schedule['time_of_day']
                            )
                            self._save_schedules()
                    
                    except Exception as e:
                        logger.error(f"Error processing schedule {schedule_id}: {e}")
                
                # Sleep for 1 minute before checking again
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Continue running even if there's an error
    
    def _run_scheduled_analysis(self, schedule_id: str, schedule: Dict):
        """Run a scheduled analysis"""
        try:
            schedule['last_run'] = datetime.now().isoformat()
            schedule['run_count'] = schedule.get('run_count', 0) + 1
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the analysis
                if len(schedule['assets']) == 1:
                    # Single asset analysis
                    result = loop.run_until_complete(
                        self.analyzer.analyze_asset(
                            schedule['assets'][0],
                            schedule['timeframe'],
                            schedule['send_email'],
                            schedule['risk_tolerance'],
                            schedule.get('user_email')
                        )
                    )
                else:
                    # Multiple asset analysis
                    result = loop.run_until_complete(
                        self.analyzer.analyze_multiple_assets(
                            schedule['assets'],
                            schedule['timeframe'],
                            False,  # Don't send individual emails
                            schedule['send_email'],  # Send summary email
                            schedule['risk_tolerance'],
                            schedule.get('user_email')
                        )
                    )
                
                if result.get('status') == 'completed':
                    schedule['success_count'] = schedule.get('success_count', 0) + 1
                    logger.info(f"Scheduled analysis completed successfully: {schedule['name']}")
                else:
                    schedule['error_count'] = schedule.get('error_count', 0) + 1
                    logger.error(f"Scheduled analysis failed: {schedule['name']} - {result.get('error', 'Unknown error')}")
            
            finally:
                loop.close()
            
            # Save updated schedule
            self._save_schedules()
            
        except Exception as e:
            schedule['error_count'] = schedule.get('error_count', 0) + 1
            logger.error(f"Error running scheduled analysis {schedule['name']}: {e}")
            self._save_schedules()
    
    def run_schedule_now(self, schedule_id: str) -> bool:
        """Manually trigger a schedule to run immediately"""
        if schedule_id not in self.schedules:
            return False
        
        schedule = self.schedules[schedule_id]
        logger.info(f"Manually triggering schedule: {schedule['name']}")
        
        # Run in a separate thread
        analysis_thread = threading.Thread(
            target=self._run_scheduled_analysis,
            args=(schedule_id, schedule),
            daemon=True
        )
        analysis_thread.start()
        
        return True
    
    def get_scheduler_status(self) -> Dict:
        """Get scheduler status information"""
        enabled_schedules = self.get_enabled_schedules()
        
        return {
            'running': self.running,
            'total_schedules': len(self.schedules),
            'enabled_schedules': len(enabled_schedules),
            'analyzer_initialized': self.analyzer is not None,
            'next_scheduled_run': min(
                (sched['next_run'] for sched in enabled_schedules.values()),
                default=None
            )
        }

# Global scheduler instance
scheduler = AnalysisScheduler()
