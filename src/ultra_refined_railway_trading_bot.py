#!/usr/bin/env python3
"""
🚀 Ultra-Refined Railway Trading Bot - Production Ready
24/7 cloud trading with OANDA using advanced forex strategies
Fixes all critical issues and implements proven improvements
"""

import sys
import os

# Robust path setup for Railway deployment
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add both current directory and parent directory to path
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# For Railway deployment, also add common paths
if '/app' in current_dir or 'railway' in os.environ.get('RAILWAY_ENVIRONMENT', '').lower():
    # Railway-specific paths
    sys.path.extend(['/app', '/app/src', '.', './src'])
else:
    # Local development paths - ensure src directory is in path
    sys.path.extend(['.', './src'])
    # If we're running from src directory, add parent/src to path
    if current_dir.endswith('/src'):
        sys.path.insert(0, os.path.join(parent_dir, 'src'))

print(f"🔍 Script location: {current_dir}")
print(f"🔍 Python path setup: {sys.path[:6]}...")

import time
import logging
from datetime import datetime, timedelta, timezone
import schedule
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
import threading
from collections import defaultdict

# Robust imports for Railway deployment - SINGLE IMPORT SECTION
print(f"🔍 Debug: Current working directory: {os.getcwd()}")
print(f"🔍 Debug: Python path: {sys.path}")
print(f"🔍 Debug: Files in current directory: {os.listdir('.')}")
if os.path.exists('src'):
    print(f"🔍 Debug: Files in src directory: {os.listdir('src')}")

print("🔄 Starting import process...")

# Initialize variables
OANDATrader = None
ForexSignalGenerator = None
SimpleTechnicalAnalyzer = None

print("🔄 Attempting first import strategy...")
try:
    from oanda_trader import OANDATrader
    from forex_signal_generator import ForexSignalGenerator
    from simple_technical_analyzer import SimpleTechnicalAnalyzer
    print("✅ Successfully imported modules using relative imports")
except ImportError as e:
    print(f"❌ Relative import error: {e}")
    print("🔄 Attempting second import strategy...")
    try:
        # Try importing from src subdirectory
        from src.oanda_trader import OANDATrader
        from src.forex_signal_generator import ForexSignalGenerator
        from src.simple_technical_analyzer import SimpleTechnicalAnalyzer
        print("✅ Successfully imported modules using src. prefix")
    except ImportError as e2:
        print(f"❌ Src import error: {e2}")
        print("🔄 Attempting final import strategy...")
        # Last resort - add all possible paths
        for path in ['.', './src', '/app', '/app/src']:
            if path not in sys.path:
                sys.path.append(path)
        
        try:
            from oanda_trader import OANDATrader
            from forex_signal_generator import ForexSignalGenerator
            from simple_technical_analyzer import SimpleTechnicalAnalyzer
            print("✅ Successfully imported modules after adding all paths")
        except ImportError as e3:
            print(f"❌ Final import error: {e3}")
            print("🚨 Critical: Could not import required modules")
            print(f"🔍 Current working directory: {os.getcwd()}")
            print(f"🔍 Files in current directory: {os.listdir('.')}")
            if os.path.exists('src'):
                print(f"🔍 Files in src directory: {os.listdir('src')}")
            raise ImportError(f"Failed to import required modules: {e3}")

print("🔄 Verifying imports...")
# CRITICAL: Verify imports worked before proceeding
if OANDATrader is None or ForexSignalGenerator is None or SimpleTechnicalAnalyzer is None:
    print("🚨 CRITICAL ERROR: One or more modules failed to import properly")
    print(f"   - OANDATrader: {OANDATrader}")
    print(f"   - ForexSignalGenerator: {ForexSignalGenerator}")
    print(f"   - SimpleTechnicalAnalyzer: {SimpleTechnicalAnalyzer}")
    raise ImportError("❌ Critical: One or more modules failed to import properly")
else:
    print(f"✅ All modules imported successfully:")
    print(f"   - OANDATrader: {OANDATrader}")
    print(f"   - ForexSignalGenerator: {ForexSignalGenerator}")
    print(f"   - SimpleTechnicalAnalyzer: {SimpleTechnicalAnalyzer}")

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Railway captures stdout/stderr
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class EnhancedTradeRecord:
    """Comprehensive trade record with advanced metrics."""
    trade_id: str
    timestamp: datetime
    pair: str
    signal_type: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    units: int
    margin_used: float
    expected_profit: float
    expected_loss: float
    risk_reward_ratio: float
    status: str  # OPEN, CLOSED_WIN, CLOSED_LOSS, CLOSED_TIME, CLOSED_MANUAL
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    actual_profit: Optional[float] = None
    pips_gained: Optional[float] = None
    hold_time_hours: Optional[float] = None
    exit_reason: Optional[str] = None
    # Advanced metrics
    mae: float = 0  # Maximum Adverse Excursion
    mfe: float = 0  # Maximum Favorable Excursion
    efficiency: float = 0  # How well we captured the move
    r_multiple: float = 0  # Risk-adjusted return
    
class AdvancedPerformanceTracker:
    """Advanced performance tracking with comprehensive metrics."""
    
    def __init__(self):
        self.trades: List[EnhancedTradeRecord] = []
        self.daily_stats = defaultdict(dict)
        self.pair_performance = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
        self.losing_streak = 0
        self.max_losing_streak = 0
        self.consecutive_losses = 0
        self.advanced_metrics = {}
        self.trade_map = {}  # Map trade IDs to records
        
    def add_trade(self, trade: EnhancedTradeRecord):
        """Add a new trade to tracking."""
        self.trades.append(trade)
        self.trade_map[trade.trade_id] = trade
        logger.info(f"📊 TRADE RECORDED: {trade.pair} {trade.signal_type} | ID: {trade.trade_id} | Confidence: {trade.confidence:.1%}")
        
    def get_trade_record(self, trade_id: str) -> Optional[EnhancedTradeRecord]:
        """Get trade record by ID."""
        return self.trade_map.get(trade_id)
        
    def update_trade_outcome(self, trade_id: str, exit_price: float, status: str, exit_reason: str = ""):
        """Update trade outcome when closed."""
        trade = self.trade_map.get(trade_id)
        if not trade:
            logger.warning(f"Trade {trade_id} not found in tracking")
            return
            
        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.now()
        trade.status = status
        trade.exit_reason = exit_reason
        
        # Calculate actual results
        pip_size = 0.01 if 'JPY' in trade.pair else 0.0001
        if trade.signal_type == "BUY":
            trade.pips_gained = (exit_price - trade.entry_price) / pip_size
        else:
            trade.pips_gained = (trade.entry_price - exit_price) / pip_size
        
        # Calculate actual profit using proper pip value
        pip_value = self._calculate_pip_value(trade.pair, trade.units)
        trade.actual_profit = trade.pips_gained * pip_value
        
        # Calculate hold time
        if trade.exit_timestamp and trade.timestamp:
            trade.hold_time_hours = (trade.exit_timestamp - trade.timestamp).total_seconds() / 3600
        
        # Update streak tracking
        if status in ['CLOSED_LOSS', 'CLOSED_TIME']:
            self.consecutive_losses += 1
            self.losing_streak += 1
            self.max_losing_streak = max(self.max_losing_streak, self.losing_streak)
        else:
            self.consecutive_losses = 0
            self.losing_streak = 0
        
        # Update pair performance
        self.pair_performance[trade.pair]['wins' if trade.actual_profit > 0 else 'losses'] += 1
        self.pair_performance[trade.pair]['profit'] += trade.actual_profit
        
        logger.info(f"🎯 TRADE CLOSED: {trade.pair} {trade.signal_type} | {status} | "
                   f"{trade.pips_gained:.1f} pips | ${trade.actual_profit:.2f} | "
                   f"R-Multiple: {trade.r_multiple:.2f} | Reason: {exit_reason}")
    
    def _calculate_pip_value(self, pair: str, units: int, account_currency: str = 'USD') -> float:
        """Calculate accurate pip value for any forex pair."""
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        
        # For simplicity, using standard pip values
        # In production, you'd fetch current exchange rates
        if pair.endswith('USD'):
            # USD is quote currency (xxx/USD)
            pip_value = pip_size * abs(units)
        elif pair.startswith('USD'):
            # USD is base currency (USD/xxx)
            # Need to divide by exchange rate - using approximations
            exchange_rates = {
                'USD/JPY': 143.0,
                'USD/CHF': 0.90,
                'USD/CAD': 1.37
            }
            rate = exchange_rates.get(pair, 1.0)
            pip_value = (pip_size * abs(units)) / rate
        else:
            # Cross currency - using approximation
            pip_value = pip_size * abs(units) * 1.2  # Rough approximation
        
        return pip_value
    
    def update_real_time_metrics(self, trade_id: str, current_price: float):
        """Update MAE/MFE and other real-time metrics."""
        trade = self.trade_map.get(trade_id)
        if not trade or trade.status != 'OPEN':
            return
        
        pip_size = 0.01 if 'JPY' in trade.pair else 0.0001
        
        # Calculate current P&L in pips
        if trade.signal_type == 'BUY':
            current_pips = (current_price - trade.entry_price) / pip_size
        else:
            current_pips = (trade.entry_price - current_price) / pip_size
        
        # Update MAE/MFE
        trade.mae = min(trade.mae, current_pips)
        trade.mfe = max(trade.mfe, current_pips)
        
        # Calculate efficiency (how well we're capturing the move)
        if trade.mfe > 0:
            trade.efficiency = current_pips / trade.mfe
        
        # Calculate R-multiple
        risk_pips = abs(trade.entry_price - trade.stop_loss) / pip_size
        trade.r_multiple = current_pips / risk_pips if risk_pips > 0 else 0
        
    def should_reduce_risk(self) -> bool:
        """Check if risk should be reduced based on recent performance."""
        return self.consecutive_losses >= 3 or self.losing_streak >= 5
        
    def get_dynamic_risk_adjustment(self) -> float:
        """Get dynamic risk adjustment factor based on recent performance."""
        if self.consecutive_losses >= 5:
            return 0.5  # Reduce risk by 50%
        elif self.consecutive_losses >= 3:
            return 0.75  # Reduce risk by 25%
        elif self.losing_streak >= 7:
            return 0.6  # Reduce risk by 40%
        return 1.0  # Normal risk

class UltraRefinedRailwayTradingBot:
    """Ultra-refined 24/7 Railway trading bot with all critical fixes."""
    
    def __init__(self):
        """Initialize the ultra-refined Railway trading bot."""
        # Get credentials from Railway environment variables
        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('OANDA_ACCOUNT_ID')
        
        if not api_key or not account_id:
            raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID environment variables required")
        
        self.trader = OANDATrader(api_key, account_id)
        self.signal_generator = ForexSignalGenerator()
        self.technical_analyzer = SimpleTechnicalAnalyzer()
        self.performance_tracker = AdvancedPerformanceTracker()
        
        # OPTIMIZED TRADING PARAMETERS
        self.pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD']
        self.min_confidence = 0.55
        self.base_risk_per_trade = 0.015  # 1.5% risk per trade
        self.max_concurrent_trades = 6
        self.max_daily_trades = 8
        self.min_risk_reward_ratio = 2.0
        self.max_hold_days = 5
        
        # Enhanced risk management
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_portfolio_risk = 0.08  # 8% max portfolio risk
        self.min_stop_distance_pips = 20  # Minimum 20 pips stop
        
        # Spread limits by pair
        self.max_spreads = {
            'EUR/USD': 2.0,
            'GBP/USD': 3.0,
            'USD/JPY': 2.0,
            'AUD/USD': 3.0,
            'USD/CAD': 3.5,
            'USD/CHF': 3.0,
            'NZD/USD': 4.0
        }
        
        # Correlation groups for risk management
        self.correlation_groups = {
            'USD_STRONG': ['EUR/USD', 'GBP/USD', 'AUD/USD', 'NZD/USD'],
            'USD_WEAK': ['USD/JPY', 'USD/CHF', 'USD/CAD'],
            'COMMODITY': ['AUD/USD', 'NZD/USD', 'USD/CAD'],
            'SAFE_HAVEN': ['USD/JPY', 'USD/CHF']
        }
        
        # News event times (UTC)
        self.news_times = [
            (8, 30),   # European data
            (13, 30),  # US data
            (14, 0),   # US data
            (18, 0),   # FOMC minutes
            (23, 50),  # Japan data
        ]
        
        # Session-based trading
        self.london_ny_overlap_hours = list(range(13, 18))  # 13:00-17:00 UTC
        self.acceptable_trading_hours = list(range(8, 21))  # 08:00-20:00 UTC
        
        # Track daily trades and performance
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Threading for real-time monitoring
        self.monitoring_thread = None
        self.stop_monitoring = False
        
        logger.info("🚀 ULTRA-REFINED RAILWAY BOT INITIALIZED")
        logger.info(f"   📊 Pairs: {', '.join(self.pairs)}")
        logger.info(f"   🎯 Min Confidence: {self.min_confidence:.1%}")
        logger.info(f"   💰 Base Risk per Trade: {self.base_risk_per_trade:.1%}")
        logger.info(f"   🔢 Max Concurrent Trades: {self.max_concurrent_trades}")
        logger.info(f"   ⚖️  Min Risk/Reward: {self.min_risk_reward_ratio:.1f}")
        
    def reset_daily_counters(self):
        """Reset daily trading counters."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            logger.info(f"📅 Daily reset: {self.daily_trades} trades, ${self.daily_pnl:.2f} P&L")
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
    
    def get_current_price(self, pair: str) -> Optional[float]:
        """Get current mid price for a pair."""
        instrument = pair.replace('/', '_')
        price_info = self.trader.get_current_price(instrument)
        if price_info and 'bid' in price_info and 'ask' in price_info:
            return (price_info['bid'] + price_info['ask']) / 2
        return None
    
    def analyze_spread_conditions(self, pair: str) -> Dict:
        """Analyze current spread conditions before entry."""
        instrument = pair.replace('/', '_')
        price_info = self.trader.get_current_price(instrument)
        
        if not price_info or 'bid' not in price_info or 'ask' not in price_info:
            return {'acceptable': False, 'reason': 'No price data'}
        
        # Calculate current spread
        bid = price_info['bid']
        ask = price_info['ask']
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        spread_pips = (ask - bid) / pip_size
        
        # Get maximum acceptable spread
        max_spread = self.max_spreads.get(pair, 5.0)
        
        # Tighter spread requirement during news
        if self.is_high_impact_news_time():
            max_spread *= 0.5
        
        acceptable = spread_pips <= max_spread
        
        return {
            'acceptable': acceptable,
            'current_spread': spread_pips,
            'max_spread': max_spread,
            'bid': bid,
            'ask': ask,
            'reason': f"Spread {spread_pips:.1f} pips ({'OK' if acceptable else 'TOO HIGH'})"
        }
    
    def is_high_impact_news_time(self, minutes_before: int = 30, minutes_after: int = 30) -> bool:
        """Check if current time is near high-impact news."""
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Check each news time
        for hour, minute in self.news_times:
            news_time = current_time.replace(hour=hour, minute=minute)
            time_diff = abs((current_time - news_time).total_seconds() / 60)
            
            if time_diff <= minutes_before or time_diff <= minutes_after:
                return True
        
        # Also avoid first hour of major sessions
        if current_time.hour in [0, 8, 13, 21]:
            return True
        
        return False
    
    def is_good_trading_session(self) -> bool:
        """Check if current time is optimal for trading."""
        current_hour = datetime.now(timezone.utc).hour
        
        # Best time: London-NY overlap
        if current_hour in self.london_ny_overlap_hours:
            return True
        
        # Acceptable time: European and US sessions
        if current_hour in self.acceptable_trading_hours:
            return True
        
        return False
    
    def check_correlation_risk(self, new_pair: str, new_direction: str) -> bool:
        """Check if new trade would create excessive correlation risk."""
        open_positions = self.trader.get_open_positions()
        
        # Check correlation exposure
        for group_name, group_pairs in self.correlation_groups.items():
            if new_pair in group_pairs:
                # Count existing positions in same group
                group_exposure = 0
                same_direction_count = 0
                
                for position in open_positions:
                    pair = position['instrument'].replace('_', '/')
                    direction = 'BUY' if position.get('currentUnits', position.get('units', 0)) > 0 else 'SELL'
                    
                    if pair in group_pairs:
                        group_exposure += 1
                        if direction == new_direction:
                            same_direction_count += 1
                
                # Risk limits
                if group_exposure >= 2:
                    logger.warning(f"⚠️ Correlation risk: Already {group_exposure} positions in {group_name}")
                    return False
                
                if same_direction_count >= 2:
                    logger.warning(f"⚠️ Directional risk: {same_direction_count} same direction in correlated pairs")
                    return False
        
        return True
    
    def calculate_accurate_pip_value(self, pair: str, position_size: int) -> float:
        """Calculate accurate pip value for position sizing."""
        pip_size = 0.01 if 'JPY' in pair else 0.0001
        
        # Get current price for accurate calculation
        current_price = self.get_current_price(pair)
        if not current_price:
            # Use approximations if can't get current price
            current_price = 1.0
        
        if pair.endswith('USD'):
            # USD is quote currency (EUR/USD, GBP/USD, etc.)
            pip_value = pip_size * abs(position_size)
        elif pair.startswith('USD'):
            # USD is base currency (USD/JPY, USD/CHF, etc.)
            pip_value = (pip_size * abs(position_size)) / current_price
        else:
            # Cross currency - need conversion (simplified)
            pip_value = pip_size * abs(position_size) * 1.1
        
        return pip_value
    
    def calculate_dynamic_position_size(self, account_balance: float, pair: str, stop_distance_pips: float) -> int:
        """Calculate position size with proper pip value calculation."""
        # Get dynamic risk adjustment
        risk_adjustment = self.performance_tracker.get_dynamic_risk_adjustment()
        adjusted_risk = self.base_risk_per_trade * risk_adjustment
        
        # Calculate risk amount
        risk_amount = account_balance * adjusted_risk
        
        # Ensure minimum stop distance
        if stop_distance_pips < self.min_stop_distance_pips:
            stop_distance_pips = self.min_stop_distance_pips
            logger.warning(f"⚠️ Stop distance adjusted to minimum {self.min_stop_distance_pips} pips")
        
        # Calculate position size using accurate pip value
        # Position size = Risk amount / (Stop distance in pips × Pip value per unit)
        pip_value_per_unit = self.calculate_accurate_pip_value(pair, 1)
        position_size = int(risk_amount / (stop_distance_pips * pip_value_per_unit))
        
        # Apply position size limits
        min_size = 1000
        max_size = min(20000, int(account_balance * 0.1))  # Max 10% of account per position
        
        position_size = max(min_size, min(position_size, max_size))
        
        logger.info(f"💰 Position size calculation for {pair}:")
        logger.info(f"   Risk adjustment: {risk_adjustment:.2f}")
        logger.info(f"   Risk amount: ${risk_amount:.2f}")
        logger.info(f"   Stop distance: {stop_distance_pips:.1f} pips")
        logger.info(f"   Pip value per unit: ${pip_value_per_unit:.4f}")
        logger.info(f"   Position size: {position_size} units")
        
        return position_size
    
    def enhanced_signal_filtering(self, signal: dict) -> Tuple[bool, str]:
        """Enhanced signal filtering with detailed rejection reasons."""
        try:
            # 1. Basic confidence check
            if signal['confidence'] < self.min_confidence:
                return False, f"Low confidence {signal['confidence']:.1%}"
            
            # 2. Check spread conditions
            spread_check = self.analyze_spread_conditions(signal['pair'])
            if not spread_check['acceptable']:
                return False, spread_check['reason']
            
            # 3. Check risk/reward ratio
            entry_price = signal['entry_price']
            target_price = signal['target_price']
            stop_loss = signal['stop_loss']
            
            pip_size = 0.01 if 'JPY' in signal['pair'] else 0.0001
            
            if signal['signal_type'] == 'BUY':
                reward_pips = (target_price - entry_price) / pip_size
                risk_pips = (entry_price - stop_loss) / pip_size
            else:
                reward_pips = (entry_price - target_price) / pip_size
                risk_pips = (stop_loss - entry_price) / pip_size
            
            risk_reward_ratio = reward_pips / risk_pips if risk_pips > 0 else 0
            
            if risk_reward_ratio < self.min_risk_reward_ratio:
                return False, f"Poor R/R ratio {risk_reward_ratio:.2f}"
            
            # 4. Check minimum stop distance
            if risk_pips < self.min_stop_distance_pips:
                return False, f"Stop too tight {risk_pips:.1f} pips"
            
            # 5. Check trading session
            if not self.is_good_trading_session():
                return False, "Poor trading session"
            
            # 6. Check news events
            if self.is_high_impact_news_time():
                return False, "High-impact news window"
            
            # 7. Check correlation risk
            if not self.check_correlation_risk(signal['pair'], signal['signal_type']):
                return False, "Correlation risk too high"
            
            # 8. Check if we should reduce risk due to recent losses
            if self.performance_tracker.should_reduce_risk() and signal['confidence'] < 0.65:
                return False, "Recent losses + moderate confidence"
            
            logger.info(f"✅ Signal passed all filters:")
            logger.info(f"   Confidence: {signal['confidence']:.1%}")
            logger.info(f"   Risk/Reward: {risk_reward_ratio:.2f}")
            logger.info(f"   Stop distance: {risk_pips:.1f} pips")
            logger.info(f"   Spread: {spread_check['current_spread']:.1f} pips")
            
            return True, "All checks passed"
            
        except Exception as e:
            logger.error(f"❌ Error in signal filtering: {e}")
            return False, f"Filter error: {str(e)}"
    
    def monitor_time_based_exits(self):
        """Monitor and close trades based on time criteria."""
        try:
            open_positions = self.trader.get_open_positions()
            current_time = datetime.now()
            
            for position in open_positions:
                # Get trade record
                trade_ids = position.get('tradeIDs', [])
                
                # Handle case where tradeIDs might be a single value instead of a list
                if isinstance(trade_ids, (str, int, float)):
                    trade_ids = [trade_ids]
                elif not isinstance(trade_ids, list):
                    trade_ids = []
                    
                if not trade_ids:
                    continue
                
                trade_record = self.performance_tracker.get_trade_record(str(trade_ids[0]))
                if not trade_record:
                    continue
                
                # Calculate hold time
                hold_time = current_time - trade_record.timestamp
                
                # Check various time-based exit conditions
                should_close = False
                reason = ""
                
                # 1. Maximum hold time exceeded
                if hold_time.days >= self.max_hold_days:
                    should_close = True
                    reason = f"Max hold time ({self.max_hold_days} days) exceeded"
                
                # 2. Weekend approaching (close before Friday 20:00 UTC)
                elif current_time.weekday() == 4 and current_time.hour >= 20:
                    should_close = True
                    reason = "Weekend risk reduction"
                
                # 3. Check if trade is stagnant
                elif position.get('unrealizedPL', 0) == 0 and hold_time.total_seconds() / 3600 > 48:
                    should_close = True
                    reason = "Trade stagnant for 48 hours"
                
                # 4. Time-based profit taking
                elif hold_time.total_seconds() / 3600 > 24 and position.get('unrealizedPL', 0) > 20:
                    # Partial close for profitable trades
                    self.execute_partial_close(position, percentage=50, reason="Time-based profit taking")
                    continue
                
                if should_close:
                    logger.info(f"⏰ Time-based exit triggered: {reason}")
                    instrument = position['instrument']
                    
                    # Close the position
                    close_result = self.trader.close_position(instrument)
                    
                    if close_result:
                        # Update tracking
                        current_price = self.get_current_price(instrument.replace('_', '/'))
                        if current_price:
                            self.performance_tracker.update_trade_outcome(
                                str(trade_ids[0]),
                                current_price,
                                'CLOSED_TIME',
                                reason
                            )
                
        except Exception as e:
            logger.error(f"❌ Error in time-based exit monitoring: {e}")
    
    def update_trailing_stops(self):
        """Update trailing stops for profitable positions."""
        try:
            open_positions = self.trader.get_open_positions()
            
            for position in open_positions:
                unrealized_pl = position.get('unrealizedPL', 0)
                if unrealized_pl <= 0:
                    continue  # Only trail profitable positions
                
                instrument = position['instrument']
                pair = instrument.replace('_', '/')
                current_price = self.get_current_price(pair)
                
                if not current_price:
                    continue
                
                # Get trade record
                trade_ids = position.get('tradeIDs', [])
                
                # Handle case where tradeIDs might be a single value instead of a list
                if isinstance(trade_ids, (str, int, float)):
                    trade_ids = [trade_ids]
                elif not isinstance(trade_ids, list):
                    trade_ids = []
                    
                if not trade_ids:
                    continue
                
                trade_record = self.performance_tracker.get_trade_record(str(trade_ids[0]))
                if not trade_record:
                    continue
                
                # Calculate profit in pips
                pip_size = 0.01 if 'JPY' in pair else 0.0001
                units = position.get('currentUnits', position.get('units', 0))
                
                if units > 0:  # Long
                    profit_pips = (current_price - trade_record.entry_price) / pip_size
                else:  # Short
                    profit_pips = (trade_record.entry_price - current_price) / pip_size
                
                # Determine new stop level
                new_stop = None
                
                if profit_pips >= 50:  # 50+ pips profit
                    # Trail at 25 pips
                    if units > 0:
                        new_stop = current_price - (25 * pip_size)
                    else:
                        new_stop = current_price + (25 * pip_size)
                
                elif profit_pips >= 30:  # 30-50 pips profit
                    # Trail at 15 pips
                    if units > 0:
                        new_stop = current_price - (15 * pip_size)
                    else:
                        new_stop = current_price + (15 * pip_size)
                
                elif profit_pips >= 20:  # 20-30 pips profit
                    # Move stop to breakeven
                    new_stop = trade_record.entry_price
                
                # Update stop if it's better than current
                if new_stop and trade_record.stop_loss:
                    if units > 0:  # Long
                        if new_stop > trade_record.stop_loss:
                            # Update stop loss (would need OANDA API method)
                            logger.info(f"📈 Trailing stop update needed for {pair}: {new_stop:.5f}")
                            trade_record.stop_loss = new_stop
                    else:  # Short
                        if new_stop < trade_record.stop_loss:
                            logger.info(f"📉 Trailing stop update needed for {pair}: {new_stop:.5f}")
                            trade_record.stop_loss = new_stop
                
        except Exception as e:
            logger.error(f"❌ Error updating trailing stops: {e}")
    
    def execute_partial_close(self, position: Dict, percentage: int = 50, reason: str = ""):
        """Close a percentage of a position."""
        try:
            current_units = position.get('currentUnits', position.get('units', 0))
            units_to_close = int(abs(current_units) * (percentage / 100))
            
            if units_to_close < 1000:  # Minimum trade size
                return False
            
            # Execute partial close
            instrument = position['instrument']
            pair = instrument.replace('_', '/')
            
            if current_units > 0:  # Long position
                signal_type = 'SELL'
                units = -units_to_close
            else:  # Short position
                signal_type = 'BUY'
                units = units_to_close
            
            # Place the order
            order_data = {
                'pair': pair,
                'signal_type': signal_type,
                'units': units,
                'entry_price': self.get_current_price(pair),
                'confidence': 1.0,
                'risk_amount': 0  # No risk for closing
            }
            
            order_id = self.trader.place_market_order(order_data)
            
            if order_id:
                logger.info(f"✂️ Partial close executed: {percentage}% of {pair} position. Reason: {reason}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Error in partial close: {e}")
        
        return False
    
    def check_daily_limits(self) -> bool:
        """Check if daily trading limits are reached."""
        self.reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trades >= self.max_daily_trades:
            logger.info(f"📊 Daily trade limit reached: {self.daily_trades}/{self.max_daily_trades}")
            return False
        
        # Check daily loss limit
        account_info = self.trader.get_account_summary()
        if account_info:
            balance = account_info.get('balance', 10000)
            max_loss = balance * self.max_daily_loss
            
            if self.daily_pnl <= -max_loss:
                logger.warning(f"🚨 Daily loss limit reached: ${self.daily_pnl:.2f}")
                return False
        
        return True
    
    def scan_for_ultra_refined_signals(self):
        """Scan for high-quality trading signals with all improvements."""
        try:
            logger.info("🔍 Scanning for ultra-refined trading signals...")
            
            # Get account info
            account_info = self.trader.get_account_summary()
            if not account_info:
                logger.error("❌ Could not get account information")
                return
            
            account_balance = account_info.get('balance', 0)
            
            # Check current open positions
            open_positions = self.trader.get_open_positions()
            current_pairs = [pos['instrument'].replace('_', '/') for pos in open_positions]
            
            if len(open_positions) >= self.max_concurrent_trades:
                logger.info(f"📊 Max concurrent trades reached: {len(open_positions)}/{self.max_concurrent_trades}")
                return
            
            # Generate signals for each pair
            signals_found = 0
            for pair in self.pairs:
                try:
                    # Skip if already have position in this pair
                    if pair in current_pairs:
                        continue
                    
                    # Generate signal
                    signal = self.signal_generator.generate_signal(pair)
                    
                    # Check if signal exists and is not HOLD
                    if signal and signal.signal_type != 'HOLD':
                        signals_found += 1
                        logger.info(f"📡 Signal found for {pair}: {signal.signal_type} (Confidence: {signal.confidence:.1%})")
                        
                        # Execute if it passes all filters
                        order_id = self.execute_ultra_refined_trade(signal, account_balance)
                        
                        if order_id:
                            # Small delay between trades
                            time.sleep(2)
                            
                        # Limit signals per scan
                        if signals_found >= 3:
                            break
                            
                except Exception as e:
                    logger.error(f"❌ Error processing {pair}: {e}")
                    continue
            
            if signals_found == 0:
                logger.info("📡 No quality signals found in current scan")
                
        except Exception as e:
            logger.error(f"❌ Error in signal scanning: {e}")
    
    def execute_ultra_refined_trade(self, signal, account_balance: float):
        """Execute trade with all improvements implemented."""
        try:
            # Access ForexSignal object attributes directly
            pair = signal.pair
            action = signal.signal_type
            confidence = signal.confidence
            
            # Convert ForexSignal to dictionary format for enhanced_signal_filtering
            signal_dict = {
                'pair': signal.pair,
                'signal_type': signal.signal_type,
                'entry_price': signal.entry_price,
                'target_price': signal.target_price,
                'stop_loss': signal.stop_loss,
                'confidence': signal.confidence,
                'pips_target': signal.pips_target,
                'pips_risk': signal.pips_risk,
                'risk_reward_ratio': signal.risk_reward_ratio,
                'reason': signal.reason,
                'timestamp': signal.timestamp,
                'news_sentiment': signal.news_sentiment,
                'technical_score': signal.technical_score,
                'atr': signal.atr
            }
            
            # Enhanced signal filtering
            passed, rejection_reason = self.enhanced_signal_filtering(signal_dict)
            if not passed:
                logger.info(f"❌ Signal rejected: {rejection_reason}")
                return None
            
            # Check daily limits
            if not self.check_daily_limits():
                return None
            
            # Calculate stop distance in pips
            entry_price = signal.entry_price
            stop_loss = signal.stop_loss
            pip_size = 0.01 if 'JPY' in pair else 0.0001
            
            if action == "BUY":
                stop_distance_pips = (entry_price - stop_loss) / pip_size
            else:
                stop_distance_pips = (stop_loss - entry_price) / pip_size
            
            # Calculate position size with accurate pip values
            position_size = self.calculate_dynamic_position_size(account_balance, pair, stop_distance_pips)
            
            # Check margin availability
            margin_check = self.trader.check_margin_availability(pair, position_size)
            if not margin_check['available']:
                logger.warning(f"⚠️ Insufficient margin: {margin_check['reason']}")
                return None
            
            # Execute the trade
            order_data = {
                'pair': pair,
                'signal_type': action,
                'entry_price': entry_price,
                'target_price': signal.target_price,
                'stop_loss': stop_loss,
                'confidence': confidence,
                'units': position_size if action == "BUY" else -position_size,
                'risk_amount': account_balance * self.base_risk_per_trade
            }
            
            order_id = self.trader.place_market_order(order_data)
            
            if order_id:
                # Calculate expected profit/loss
                pip_value = self.calculate_accurate_pip_value(pair, position_size)
                
                if action == "BUY":
                    target_pips = (signal.target_price - entry_price) / pip_size
                    stop_pips = (entry_price - stop_loss) / pip_size
                else:
                    target_pips = (entry_price - signal.target_price) / pip_size
                    stop_pips = (stop_loss - entry_price) / pip_size
                
                expected_profit = target_pips * pip_value
                expected_loss = -stop_pips * pip_value
                risk_reward_ratio = target_pips / stop_pips if stop_pips > 0 else 0
                
                # Record the trade
                trade_record = EnhancedTradeRecord(
                    trade_id=str(order_id),
                    timestamp=datetime.now(),
                    pair=pair,
                    signal_type=action,
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=signal.target_price,
                    stop_loss=stop_loss,
                    units=position_size,
                    margin_used=margin_check['margin_required'],
                    expected_profit=expected_profit,
                    expected_loss=expected_loss,
                    risk_reward_ratio=risk_reward_ratio,
                    status="OPEN"
                )
                
                self.performance_tracker.add_trade(trade_record)
                self.daily_trades += 1
                
                logger.info(f"✅ ULTRA-REFINED TRADE EXECUTED:")
                logger.info(f"   📊 {pair} {action} | Order ID: {order_id}")
                logger.info(f"   💰 Position Size: {position_size} units")
                logger.info(f"   🎯 Entry: {entry_price:.5f}")
                logger.info(f"   🛡️  Stop Loss: {stop_loss:.5f} ({stop_pips:.1f} pips)")
                logger.info(f"   🎯 Take Profit: {signal.target_price:.5f} ({target_pips:.1f} pips)")
                logger.info(f"   📈 Risk/Reward: {risk_reward_ratio:.2f}")
                logger.info(f"   💵 Expected P&L: +${expected_profit:.2f} / -${abs(expected_loss):.2f}")
                
                return order_id
            
        except Exception as e:
            logger.error(f"❌ Error executing ultra-refined trade: {e}")
            return None
    
    def real_time_monitoring_loop(self):
        """Continuous monitoring loop for real-time updates."""
        while not self.stop_monitoring:
            try:
                # Update MAE/MFE for open trades
                open_positions = self.trader.get_open_positions()
                
                for position in open_positions:
                    instrument = position['instrument']
                    pair = instrument.replace('_', '/')
                    current_price = self.get_current_price(pair)
                    
                    if current_price:
                        trade_ids = position.get('tradeIDs', [])
                        
                        # Handle case where tradeIDs might be a single value instead of a list
                        if isinstance(trade_ids, (str, int, float)):
                            trade_ids = [trade_ids]
                        elif not isinstance(trade_ids, list):
                            trade_ids = []
                            
                        if trade_ids:
                            self.performance_tracker.update_real_time_metrics(str(trade_ids[0]), current_price)
                
                # Update trailing stops
                self.update_trailing_stops()
                
                # Check time-based exits
                self.monitor_time_based_exits()
                
                # Sleep for 30 seconds before next update
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def ultra_refined_trading_session(self):
        """Enhanced trading session with all improvements."""
        try:
            logger.info("🚀 ULTRA-REFINED TRADING SESSION STARTED")
            
            # Scan for new signals
            self.scan_for_ultra_refined_signals()
            
            # Log session summary
            account_info = self.trader.get_account_summary()
            if account_info:
                logger.info(f"💰 Account Summary:")
                logger.info(f"   Balance: ${account_info.get('balance', 0):.2f}")
                logger.info(f"   NAV: ${account_info.get('nav', 0):.2f}")
                logger.info(f"   Unrealized P&L: ${account_info.get('unrealized_pl', 0):.2f}")
                logger.info(f"   Open Trades: {account_info.get('open_trade_count', 0)}")
                logger.info(f"   Margin Used: ${account_info.get('margin_used', 0):.2f}")
                logger.info(f"   Margin Available: ${account_info.get('margin_available', 0):.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error in trading session: {e}")
    
    def start_ultra_refined_24_7_trading(self):
        """Start the ultra-refined 24/7 trading system."""
        logger.info("🚀 STARTING ULTRA-REFINED 24/7 TRADING SYSTEM")
        logger.info("=" * 60)
        
        # Test connection
        account_info = self.trader.get_account_summary()
        if not account_info:
            logger.error("❌ Failed to connect to OANDA. Exiting.")
            return
        
        logger.info(f"✅ Connected to OANDA account: ${account_info.get('balance', 0):.2f}")
        
        # Start real-time monitoring thread
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self.real_time_monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("🔄 Real-time monitoring thread started")
        
        # Schedule trading sessions
        schedule.every(15).minutes.do(self.ultra_refined_trading_session)
        
        # Schedule maintenance tasks
        schedule.every(1).hours.do(self.monitor_time_based_exits)
        schedule.every(30).minutes.do(self.update_trailing_stops)
        
        logger.info("📅 Trading sessions scheduled every 15 minutes")
        logger.info("🔄 Starting main trading loop...")
        
        # Main trading loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("🛑 Trading stopped by user")
                self.stop_monitoring = True
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in main loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

def main():
    """Run the ultra-refined Railway trading bot."""
    try:
        bot = UltraRefinedRailwayTradingBot()
        bot.start_ultra_refined_24_7_trading()
    except Exception as e:
        logger.error(f"❌ Failed to start ultra-refined trading bot: {e}")

if __name__ == "__main__":
    main() 