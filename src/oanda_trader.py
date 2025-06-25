#!/usr/bin/env python3
"""
OANDA Automated Trading System
Places real trades with risk management and alerts
"""

import requests
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeOrder:
    """Trade order with risk management."""
    pair: str
    signal_type: str  # BUY or SELL
    entry_price: float
    target_price: float
    stop_loss: float
    confidence: float
    units: int
    risk_amount: float

class OANDATrader:
    """Automated OANDA trading system."""
    
    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment
        
        if environment == "practice":
            self.base_url = "https://api-fxpractice.oanda.com"
        else:
            self.base_url = "https://api-fxtrade.oanda.com"
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Risk management settings
        self.max_risk_per_trade = 0.02  # 2% of account per trade
        self.max_daily_risk = 0.06      # 6% of account per day
        self.min_confidence = 0.25      # Lowered to 25% for testing
        
        logger.info(f"OANDA Trader initialized for {environment} environment")

    def get_account_balance(self) -> float:
        """Get current account balance."""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                balance = float(data['account']['balance'])
                logger.info(f"Account balance: ${balance:.2f}")
                return balance
            else:
                logger.error(f"Failed to get balance: {response.text}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0

    def get_account_summary(self) -> Dict:
        """Get comprehensive account summary including margin information."""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                account = data['account']
                
                summary = {
                    'balance': float(account.get('balance', 0)),
                    'nav': float(account.get('NAV', 0)),
                    'margin_used': float(account.get('marginUsed', 0)),
                    'margin_available': float(account.get('marginAvailable', 0)),
                    'margin_rate': float(account.get('marginRate', 0.02)),  # Default 2%
                    'open_trade_count': int(account.get('openTradeCount', 0)),
                    'open_position_count': int(account.get('openPositionCount', 0)),
                    'unrealized_pl': float(account.get('unrealizedPL', 0)),
                    'currency': account.get('currency', 'USD')
                }
                
                logger.info(f"Account Summary:")
                logger.info(f"  Balance: ${summary['balance']:.2f}")
                logger.info(f"  NAV: ${summary['nav']:.2f}")
                logger.info(f"  Margin Used: ${summary['margin_used']:.2f}")
                logger.info(f"  Margin Available: ${summary['margin_available']:.2f}")
                logger.info(f"  Open Trades: {summary['open_trade_count']}")
                logger.info(f"  Unrealized P&L: ${summary['unrealized_pl']:.2f}")
                
                return summary
            else:
                logger.error(f"Failed to get account summary: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}

    def calculate_margin_required(self, pair: str, units: int) -> float:
        """Calculate margin required for a trade."""
        try:
            # Get current price for the pair
            instrument = pair.replace('/', '_')
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {"instruments": instrument}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('prices'):
                    price_info = data['prices'][0]
                    current_price = (float(price_info['bids'][0]['price']) + 
                                   float(price_info['asks'][0]['price'])) / 2
                    
                    # Calculate margin required
                    # For forex: Margin = (Units × Price) × Margin Rate
                    # Typical margin rates for 30:1 leverage: ~3.33% for majors, ~5% for minors
                    margin_rates = {
                        'EUR_USD': 0.0333, 'GBP_USD': 0.0333, 'USD_JPY': 0.0333,
                        'USD_CHF': 0.0333, 'AUD_USD': 0.0333, 'USD_CAD': 0.0333,
                        'NZD_USD': 0.05  # Higher margin for minor pairs (20:1 leverage)
                    }
                    
                    margin_rate = margin_rates.get(instrument, 0.05)  # Default 5% (20:1 leverage)
                    
                    # Fixed margin calculation logic
                    base_currency = instrument.split('_')[0]
                    
                    if base_currency == 'USD':  # USD is base currency (USD/JPY, USD/CHF, USD/CAD)
                        # Margin = units * margin_rate (since units are in USD)
                        margin_required = abs(units) * margin_rate
                    else:  # USD is quote currency (EUR/USD, GBP/USD, AUD/USD, NZD/USD)
                        # Margin = (units * price) * margin_rate (convert to USD first)
                        margin_required = abs(units) * current_price * margin_rate
                    
                    logger.info(f"Margin required for {abs(units)} units of {pair}: ${margin_required:.2f}")
                    return margin_required
                    
            logger.warning(f"Could not get price for {pair}, using conservative estimate")
            return abs(units) * 0.05  # Conservative 5% margin estimate
            
        except Exception as e:
            logger.error(f"Error calculating margin for {pair}: {e}")
            return abs(units) * 0.05  # Conservative fallback

    def check_margin_availability(self, pair: str, units: int) -> Dict:
        """Check if sufficient margin is available for a trade."""
        account_summary = self.get_account_summary()
        
        if not account_summary:
            return {'available': False, 'reason': 'Cannot get account information'}
        
        margin_required = self.calculate_margin_required(pair, units)
        margin_available = account_summary['margin_available']
        
        # Add safety buffer (keep at least $50 or 5% of balance as buffer)
        safety_buffer = max(50, account_summary['balance'] * 0.05)
        effective_margin_available = margin_available - safety_buffer
        
        result = {
            'available': effective_margin_available >= margin_required,
            'margin_required': margin_required,
            'margin_available': margin_available,
            'effective_available': effective_margin_available,
            'safety_buffer': safety_buffer,
            'current_margin_used': account_summary['margin_used'],
            'balance': account_summary['balance'],
            'reason': ''
        }
        
        if not result['available']:
            if margin_available < margin_required:
                result['reason'] = f"Insufficient margin: need ${margin_required:.2f}, have ${margin_available:.2f}"
            else:
                result['reason'] = f"Safety buffer protection: need ${margin_required:.2f}, available after buffer ${effective_margin_available:.2f}"
        
        logger.info(f"Margin Check for {pair}:")
        logger.info(f"  Required: ${margin_required:.2f}")
        logger.info(f"  Available: ${margin_available:.2f}")
        logger.info(f"  After Buffer: ${effective_margin_available:.2f}")
        logger.info(f"  Status: {'✅ APPROVED' if result['available'] else '❌ REJECTED'}")
        if result['reason']:
            logger.info(f"  Reason: {result['reason']}")
        
        return result

    def calculate_safe_position_size(self, signal, account_summary: Dict) -> int:
        """Calculate safe position size considering margin requirements."""
        # Start with risk-based calculation
        risk_amount = account_summary['balance'] * self.max_risk_per_trade
        
        # Calculate pip value and distance to stop loss
        if 'JPY' in signal.pair:
            pip_value = 0.01
        else:
            pip_value = 0.0001
        
        # Distance from entry to stop loss in pips
        if signal.signal_type == "BUY":
            stop_distance = abs(signal.entry_price - signal.stop_loss) / pip_value
        else:
            stop_distance = abs(signal.stop_loss - signal.entry_price) / pip_value
        
        # Calculate units based on risk - FIXED: Removed incorrect "* 100"
        # Pip value for 1000 units is approximately $0.10 for major pairs
        pip_value_per_1000_units = 0.10
        
        if stop_distance > 0:
            # Position size = Risk Amount / (Stop Distance Pips * Pip Value per 1000 units) * 1000
            base_units = int((risk_amount / (stop_distance * pip_value_per_1000_units)) * 1000)
        else:
            base_units = 1000  # Fallback minimum
        
        # Ensure minimum and maximum position sizes
        min_units = 1000   # Minimum trade size
        max_units = 50000  # Maximum trade size for demo
        
        risk_based_units = max(min_units, min(base_units, max_units))
        
        # Log calculation details for debugging
        logger.info(f"📊 Position size calculation for {signal.pair}:")
        logger.info(f"   Risk amount: ${risk_amount:.2f}")
        logger.info(f"   Stop distance: {stop_distance:.1f} pips")
        logger.info(f"   Pip value per 1000 units: ${pip_value_per_1000_units:.2f}")
        logger.info(f"   Calculated units: {base_units:,}")
        logger.info(f"   Final units (after limits): {risk_based_units:,}")
        
        # Now check margin constraints
        margin_check = self.check_margin_availability(signal.pair, risk_based_units)
        
        if margin_check['available']:
            logger.info(f"Risk-based position size approved: {risk_based_units} units")
            return risk_based_units
        
        # If risk-based size doesn't fit, calculate maximum safe size
        effective_margin = margin_check['effective_available']
        
        # Estimate units that would fit in available margin
        # This is approximate - we'll verify with actual margin calculation
        if margin_check['margin_required'] > 0:
            estimated_margin_per_unit = margin_check['margin_required'] / risk_based_units
            safe_units = int(effective_margin / estimated_margin_per_unit)
        else:
            safe_units = min_units
        
        # Ensure it's within our limits
        safe_units = max(min_units, min(safe_units, max_units))
        
        # Final verification
        final_check = self.check_margin_availability(signal.pair, safe_units)
        
        if final_check['available']:
            logger.info(f"Margin-adjusted position size: {safe_units} units (reduced from {risk_based_units})")
            return safe_units
        else:
            logger.warning(f"Cannot find safe position size for {signal.pair}")
            return 0  # Cannot trade safely

    def should_trade_signal(self, signal, manual_override=False) -> bool:
        """Enhanced signal validation with margin checks."""
        
        if manual_override:
            logger.info(f"🔓 MANUAL OVERRIDE ACTIVATED - Bypassing confidence checks")
            logger.info(f"   Signal: {signal.pair} {signal.signal_type}")
            logger.info(f"   Confidence: {signal.confidence:.1%} (normally requires {self.min_confidence:.1%})")
        
        # Check confidence threshold (skip if manual override)
        if not manual_override and signal.confidence < self.min_confidence:
            logger.info(f"❌ Signal confidence {signal.confidence:.1%} below minimum {self.min_confidence:.1%}")
            return False
        
        # Get account summary
        account_summary = self.get_account_summary()
        if not account_summary:
            logger.error("❌ Cannot get account information")
            return False
        
        # Check if account has sufficient balance
        if account_summary['balance'] <= 100:  # Minimum $100 balance
            logger.info(f"❌ Account balance too low: ${account_summary['balance']:.2f}")
            return False
        
        # Check if we already have a position in this pair
        open_positions = self.get_open_positions()
        for position in open_positions:
            if position['instrument'].replace('_', '/') == signal.pair:
                logger.info(f"❌ Already have position in {signal.pair}")
                return False
        
        # Check daily risk limits
        if len(open_positions) >= 8:  # Increased from 3 to 8 concurrent positions
            logger.info(f"❌ Maximum concurrent positions reached ({len(open_positions)}/8)")
            return False
        
        # Check if margin is available for minimum trade size
        margin_check = self.check_margin_availability(signal.pair, 1000)  # Check minimum size
        if not margin_check['available']:
            logger.info(f"❌ Insufficient margin for {signal.pair}: {margin_check['reason']}")
            return False
        
        # Check total margin utilization
        margin_utilization = account_summary['margin_used'] / account_summary['balance'] if account_summary['balance'] > 0 else 1
        if margin_utilization > 0.8:  # Don't use more than 80% of balance as margin
            logger.info(f"❌ Margin utilization too high: {margin_utilization:.1%}")
            return False
        
        if manual_override:
            logger.info(f"✅ Manual override signal approved: {signal.pair} {signal.signal_type}")
        else:
            logger.info(f"✅ Signal approved for trading: {signal.pair} {signal.signal_type}")
        return True

    def execute_signal(self, signal, manual_override=False) -> Optional[str]:
        """Execute a trading signal with enhanced margin management."""
        if not self.should_trade_signal(signal, manual_override=manual_override):
            return None
        
        # Get account summary
        account_summary = self.get_account_summary()
        if not account_summary:
            logger.error("❌ Unable to get account summary")
            return None
        
        # Calculate safe position size
        units = self.calculate_safe_position_size(signal, account_summary)
        
        if units <= 0:
            logger.error("❌ Cannot calculate safe position size")
            return None
        
        # Final margin check before placing order
        final_margin_check = self.check_margin_availability(signal.pair, units)
        if not final_margin_check['available']:
            logger.error(f"❌ Final margin check failed: {final_margin_check['reason']}")
            return None
        
        # Create trade order
        trade_order = TradeOrder(
            pair=signal.pair,
            signal_type=signal.signal_type,
            entry_price=signal.entry_price,
            target_price=signal.target_price,
            stop_loss=signal.stop_loss,
            confidence=signal.confidence,
            units=units,
            risk_amount=account_summary['balance'] * self.max_risk_per_trade
        )
        
        # Log pre-trade state
        logger.info(f"Pre-trade margin state:")
        logger.info(f"  Balance: ${account_summary['balance']:.2f}")
        logger.info(f"  Margin Used: ${account_summary['margin_used']:.2f}")
        logger.info(f"  Margin Available: ${account_summary['margin_available']:.2f}")
        logger.info(f"  Will use additional: ${final_margin_check['margin_required']:.2f}")
        
        # Place the order
        order_id = self.place_market_order(trade_order)
        
        if order_id:
            self.send_trade_alert(trade_order, order_id)
            
            # Log post-trade state
            post_summary = self.get_account_summary()
            if post_summary:
                logger.info(f"Post-trade margin state:")
                logger.info(f"  Balance: ${post_summary['balance']:.2f}")
                logger.info(f"  Margin Used: ${post_summary['margin_used']:.2f}")
                logger.info(f"  Margin Available: ${post_summary['margin_available']:.2f}")
        
        return order_id

    def place_market_order(self, trade_order: TradeOrder) -> Optional[str]:
        """Place a market order with stop loss and take profit."""
        try:
            # Convert pair format (EUR/USD -> EUR_USD)
            instrument = trade_order.pair.replace('/', '_')
            
            # Get current market prices to validate order levels
            current_prices = self.get_bid_ask_prices(instrument)
            if not current_prices:
                logger.error(f"❌ Cannot get current market prices for {instrument}")
                return None
            
            # Determine units (positive for buy, negative for sell)
            units = trade_order.units if trade_order.signal_type == "BUY" else -trade_order.units
            
            # Validate and adjust levels based on current market prices
            pip_size = 0.01 if 'JPY' in instrument else 0.0001
            
            # For BUY orders: use ASK price (we buy at ask)
            # For SELL orders: use BID price (we sell at bid)
            if trade_order.signal_type == "BUY":
                current_price = current_prices['ask']
                
                # For BUY: TP must be above current ask, SL must be below current bid
                if trade_order.target_price <= current_price:
                    logger.error(f"❌ Take profit {trade_order.target_price:.5f} is below/at current ask {current_price:.5f}")
                    logger.error(f"   Market has moved against the BUY signal")
                    return None
                    
                if trade_order.stop_loss >= current_prices['bid']:
                    logger.error(f"❌ Stop loss {trade_order.stop_loss:.5f} is above/at current bid {current_prices['bid']:.5f}")
                    logger.error(f"   Market has moved against the BUY signal")
                    return None
                    
            else:  # SELL
                current_price = current_prices['bid']
                
                # For SELL: TP must be below current bid, SL must be above current ask
                if trade_order.target_price >= current_price:
                    logger.error(f"❌ Take profit {trade_order.target_price:.5f} is above/at current bid {current_price:.5f}")
                    logger.error(f"   Market has moved against the SELL signal")
                    return None
                    
                if trade_order.stop_loss <= current_prices['ask']:
                    logger.error(f"❌ Stop loss {trade_order.stop_loss:.5f} is below/at current ask {current_prices['ask']:.5f}")
                    logger.error(f"   Market has moved against the SELL signal")
                    return None
            
            # Enhanced distance validation before placing order
            if trade_order.signal_type == "BUY":
                sl_distance_pips = abs(current_price - trade_order.stop_loss) / pip_size
                tp_distance_pips = abs(trade_order.target_price - current_price) / pip_size
            else:  # SELL
                sl_distance_pips = abs(trade_order.stop_loss - current_price) / pip_size
                tp_distance_pips = abs(current_price - trade_order.target_price) / pip_size
            
            # OANDA minimum distances - DRAMATICALLY INCREASED for CHF after multiple rejections
            # CHF pairs are proving extremely difficult - using professional trading minimums
            if 'CHF' in instrument:
                min_sl_distance = 80   # CHF pairs: Increased to 80+ pips (was 50, still rejected)
                min_tp_distance = 120  # CHF pairs: Increased to 120+ pips (was 60, still rejected)
                logger.warning(f"⚠️ CHF pair detected - using extra-wide minimums: {min_sl_distance} SL, {min_tp_distance} TP")
            elif 'JPY' in instrument:
                min_sl_distance = 40   # JPY pairs: slightly increased
                min_tp_distance = 70   # JPY pairs: increased for safety
            else:
                min_sl_distance = 30   # Standard for EUR/USD, GBP/USD, etc.
                min_tp_distance = 60   # Standard TP distance
            
            if sl_distance_pips < min_sl_distance:
                logger.error(f"❌ Stop loss too close: {sl_distance_pips:.1f} pips (need {min_sl_distance}+)")
                return None
                
            if tp_distance_pips < min_tp_distance:
                logger.error(f"❌ Take profit too close: {tp_distance_pips:.1f} pips (need {min_tp_distance}+)")
                return None
            
            # Log current market conditions
            logger.info(f"📊 Current market prices for {instrument}:")
            logger.info(f"   Bid: {current_prices['bid']:.5f}")
            logger.info(f"   Ask: {current_prices['ask']:.5f}")
            logger.info(f"   Spread: {current_prices['spread_pips']:.1f} pips")
            
            # Format prices with correct precision for the instrument
            if 'JPY' in instrument:
                # JPY pairs use 3 decimal places
                entry_price = f"{trade_order.entry_price:.3f}"
                target_price = f"{trade_order.target_price:.3f}"
                stop_loss = f"{trade_order.stop_loss:.3f}"
            else:
                # Other pairs use 5 decimal places
                entry_price = f"{trade_order.entry_price:.5f}"
                target_price = f"{trade_order.target_price:.5f}"
                stop_loss = f"{trade_order.stop_loss:.5f}"
            
            # Log the order details before placing
            logger.info(f"🔄 Placing order:")
            logger.info(f"   Instrument: {instrument}")
            logger.info(f"   Units: {units}")
            logger.info(f"   Entry: {entry_price}")
            logger.info(f"   Target: {target_price}")
            logger.info(f"   Stop Loss: {stop_loss}")
            
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "stopLossOnFill": {
                        "price": stop_loss
                    },
                    "takeProfitOnFill": {
                        "price": target_price
                    }
                }
            }
            
            # Log the full order data
            logger.info(f"📋 Order JSON: {json.dumps(order_data, indent=2)}")
            
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
            response = requests.post(url, headers=self.headers, json=order_data)
            
            # Log the response details
            logger.info(f"📡 Response Status: {response.status_code}")
            logger.info(f"📡 Response Headers: {dict(response.headers)}")
            logger.info(f"📡 Response Body: {response.text}")
            
            if response.status_code == 201:
                result = response.json()
                order_id = result['orderFillTransaction']['id']
                
                logger.info(f"✅ Order placed successfully!")
                logger.info(f"   Order ID: {order_id}")
                logger.info(f"   {trade_order.signal_type} {trade_order.pair}")
                logger.info(f"   Units: {units}")
                logger.info(f"   Entry: {entry_price}")
                logger.info(f"   Target: {target_price}")
                logger.info(f"   Stop Loss: {stop_loss}")
                
                return order_id
            else:
                logger.error(f"❌ Failed to place order:")
                logger.error(f"   Status Code: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    if 'errorMessage' in error_data:
                        logger.error(f"   Error Message: {error_data['errorMessage']}")
                    if 'errorCode' in error_data:
                        logger.error(f"   Error Code: {error_data['errorCode']}")
                except:
                    pass
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Exception placing order: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    def get_open_positions(self) -> List[Dict]:
        """Get all open positions."""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/positions"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                positions = []
                
                for position in data.get('positions', []):
                    # Only include positions with actual units
                    long_units = float(position['long']['units'])
                    short_units = float(position['short']['units'])
                    
                    if long_units != 0 or short_units != 0:
                        positions.append(position)
                
                return positions
            else:
                logger.error(f"Failed to get positions: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def close_position(self, instrument: str) -> Optional[str]:
        """Close an open position."""
        try:
            # First check if position exists
            positions = self.get_open_positions()
            position_exists = False
            
            for pos in positions:
                if pos['instrument'] == instrument:
                    position_exists = True
                    break
            
            if not position_exists:
                logger.warning(f"No open position found for {instrument}")
                return None
            
            # Close the position using OANDA's position close endpoint
            url = f"{self.base_url}/v3/accounts/{self.account_id}/positions/{instrument}/close"
            
            # Close both long and short sides
            close_data = {
                "longUnits": "ALL",
                "shortUnits": "ALL"
            }
            
            response = requests.put(url, headers=self.headers, json=close_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract order IDs from response
                order_ids = []
                if 'longOrderFillTransaction' in data:
                    order_ids.append(data['longOrderFillTransaction']['id'])
                if 'shortOrderFillTransaction' in data:
                    order_ids.append(data['shortOrderFillTransaction']['id'])
                
                order_id = ', '.join(order_ids) if order_ids else 'CLOSED'
                
                logger.info(f"✅ Successfully closed position for {instrument}")
                logger.info(f"   Order ID(s): {order_id}")
                
                return order_id
            else:
                logger.error(f"Failed to close position for {instrument}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error closing position for {instrument}: {e}")
            return None

    def get_current_price(self, instrument: str) -> Optional[float]:
        """Get current market price for an instrument."""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {"instruments": instrument}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('prices'):
                    price_info = data['prices'][0]
                    # Return mid price
                    bid = float(price_info['bids'][0]['price'])
                    ask = float(price_info['asks'][0]['price'])
                    mid_price = (bid + ask) / 2
                    return mid_price
                    
            logger.warning(f"Could not get current price for {instrument}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {instrument}: {e}")
            return None

    def get_bid_ask_prices(self, instrument: str) -> Optional[Dict]:
        """Get current bid/ask prices for an instrument."""
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {"instruments": instrument}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('prices'):
                    price_info = data['prices'][0]
                    bid = float(price_info['bids'][0]['price'])
                    ask = float(price_info['asks'][0]['price'])
                    mid_price = (bid + ask) / 2
                    
                    # Calculate spread in pips
                    pip_size = 0.01 if 'JPY' in instrument else 0.0001
                    spread_pips = (ask - bid) / pip_size
                    
                    return {
                        'bid': bid,
                        'ask': ask,
                        'mid': mid_price,
                        'spread_pips': spread_pips,
                        'timestamp': price_info.get('time', '')
                    }
                    
            logger.warning(f"Could not get bid/ask prices for {instrument}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting bid/ask prices for {instrument}: {e}")
            return None

    def send_trade_alert(self, trade_order: TradeOrder, order_id: str):
        """Send trade alert (placeholder for notifications)."""
        alert_message = f"""
🚨 TRADE EXECUTED 🚨

Pair: {trade_order.pair}
Action: {trade_order.signal_type}
Entry: {trade_order.entry_price:.5f}
Target: {trade_order.target_price:.5f}
Stop Loss: {trade_order.stop_loss:.5f}
Units: {trade_order.units}
Confidence: {trade_order.confidence:.1%}
Risk: ${trade_order.risk_amount:.2f}
Order ID: {order_id}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        logger.info(alert_message)
        # Here you could add email, SMS, or push notifications

def main():
    """Test the OANDA trader."""
    # Your OANDA credentials
    api_key = "fe92315bee29b117825fed529cf3fa99-173e927b8cdbb1fc244993e24e33fd93"
    account_id = "101-004-31788297-001"
    
    trader = OANDATrader(api_key, account_id, environment="practice")
    
    # Test account connection
    balance = trader.get_account_balance()
    print(f"Account Balance: ${balance:.2f}")
    
    # Test getting positions
    positions = trader.get_open_positions()
    print(f"Open Positions: {len(positions)}")

if __name__ == "__main__":
    main() 