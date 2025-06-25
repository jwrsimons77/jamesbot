#!/usr/bin/env python3
"""
🔍 Live Trading Performance Analyzer
Connects to Railway logs and OANDA API to analyze trading performance
Compares bot intentions vs actual executions and provides actionable insights
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import subprocess
import logging
from collections import defaultdict
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OANDATransaction:
    """OANDA transaction record."""
    transaction_id: str
    time: datetime
    instrument: str
    units: float
    price: float
    pl: float
    transaction_type: str
    reason: str
    account_balance: float

@dataclass
class BotTradeIntention:
    """Bot trade intention from logs."""
    timestamp: datetime
    pair: str
    signal_type: str
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    expected_units: int
    expected_profit: float
    expected_loss: float
    risk_reward_ratio: float
    rejection_reason: Optional[str] = None
    executed: bool = False

@dataclass
class PerformanceMetrics:
    """Performance analysis metrics."""
    total_bot_signals: int
    total_oanda_trades: int
    matched_trades: int
    missed_opportunities: int
    unexpected_trades: int
    execution_accuracy: float
    avg_confidence_winners: float
    avg_confidence_losers: float
    bot_win_rate: float
    actual_win_rate: float
    predicted_profit: float
    actual_profit: float
    avg_execution_delay: float

class LiveTradingPerformanceAnalyzer:
    """Analyze live trading performance by connecting to Railway and OANDA."""
    
    def __init__(self):
        """Initialize the analyzer with API connections."""
        # OANDA API setup
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.oanda_base_url = "https://api-fxpractice.oanda.com"  # Change to live URL for production
        
        if not self.oanda_api_key or not self.oanda_account_id:
            raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID environment variables required")
        
        # Railway setup
        self.railway_token = os.getenv('RAILWAY_TOKEN')
        self.railway_project_id = os.getenv('RAILWAY_PROJECT_ID')
        self.railway_service_id = os.getenv('RAILWAY_SERVICE_ID')
        
        # Data storage
        self.oanda_transactions: List[OANDATransaction] = []
        self.bot_intentions: List[BotTradeIntention] = []
        self.matched_trades: List[Tuple[BotTradeIntention, OANDATransaction]] = []
        
        logger.info("🚀 Live Trading Performance Analyzer initialized")
    
    def fetch_oanda_transactions(self, days_back: int = 7) -> List[OANDATransaction]:
        """Fetch transaction history from OANDA API."""
        try:
            # Calculate date range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days_back)
            
            # OANDA API headers
            headers = {
                'Authorization': f'Bearer {self.oanda_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Fetch transactions
            url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/transactions"
            params = {
                'from': start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'to': end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'type': 'ORDER_FILL,MARKET_ORDER,LIMIT_ORDER,STOP_ORDER'
            }
            
            logger.info(f"📡 Fetching OANDA transactions from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            transactions = []
            
            for tx in data.get('transactions', []):
                if tx.get('type') in ['ORDER_FILL', 'MARKET_ORDER']:
                    transaction = OANDATransaction(
                        transaction_id=tx.get('id', ''),
                        time=datetime.fromisoformat(tx.get('time', '').replace('Z', '+00:00')),
                        instrument=tx.get('instrument', ''),
                        units=float(tx.get('units', 0)),
                        price=float(tx.get('price', 0)),
                        pl=float(tx.get('pl', 0)),
                        transaction_type=tx.get('type', ''),
                        reason=tx.get('reason', ''),
                        account_balance=float(tx.get('accountBalance', 0))
                    )
                    transactions.append(transaction)
            
            self.oanda_transactions = transactions
            logger.info(f"✅ Fetched {len(transactions)} OANDA transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error fetching OANDA transactions: {e}")
            return []
    
    def fetch_railway_logs(self, hours_back: int = 24) -> str:
        """Fetch Railway deployment logs."""
        try:
            if not self.railway_token:
                logger.warning("⚠️ Railway token not provided, trying Railway CLI...")
                return self._fetch_logs_via_cli(hours_back)
            
            # Use Railway API
            headers = {
                'Authorization': f'Bearer {self.railway_token}',
                'Content-Type': 'application/json'
            }
            
            # Railway GraphQL API
            url = "https://backboard.railway.app/graphql/v2"
            
            # GraphQL query to get logs
            query = """
            query GetLogs($projectId: String!, $serviceId: String!, $startTime: DateTime!, $endTime: DateTime!) {
                logs(
                    projectId: $projectId
                    serviceId: $serviceId
                    startTime: $startTime
                    endTime: $endTime
                ) {
                    edges {
                        node {
                            timestamp
                            message
                            severity
                        }
                    }
                }
            }
            """
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
            
            variables = {
                'projectId': self.railway_project_id,
                'serviceId': self.railway_service_id,
                'startTime': start_time.isoformat(),
                'endTime': end_time.isoformat()
            }
            
            response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logs = []
                for edge in data.get('data', {}).get('logs', {}).get('edges', []):
                    node = edge.get('node', {})
                    logs.append(f"{node.get('timestamp', '')} - {node.get('message', '')}")
                
                log_content = '\n'.join(logs)
                logger.info(f"✅ Fetched {len(logs)} Railway log entries")
                return log_content
            else:
                logger.warning(f"⚠️ Railway API returned status {response.status_code}, trying CLI...")
                return self._fetch_logs_via_cli(hours_back)
                
        except Exception as e:
            logger.error(f"❌ Error fetching Railway logs via API: {e}")
            return self._fetch_logs_via_cli(hours_back)
    
    def _fetch_logs_via_cli(self, hours_back: int = 24) -> str:
        """Fetch logs using Railway CLI as fallback."""
        try:
            # Check if Railway CLI is installed
            result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("⚠️ Railway CLI not found. Install with: npm install -g @railway/cli")
                return ""
            
            # Fetch logs
            logger.info("🔄 Fetching logs via Railway CLI...")
            result = subprocess.run([
                'railway', 'logs', '--json', '--lines', '1000'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ Fetched logs via Railway CLI")
                return result.stdout
            else:
                logger.error(f"❌ Railway CLI error: {result.stderr}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Error fetching logs via CLI: {e}")
            return ""
    
    def parse_bot_intentions(self, log_content: str) -> List[BotTradeIntention]:
        """Parse bot trading intentions from Railway logs."""
        intentions = []
        
        if not log_content:
            logger.warning("⚠️ No log content to parse")
            return intentions
        
        lines = log_content.split('\n')
        
        for line in lines:
            try:
                # Parse different types of bot intentions
                
                # 1. Successful trade executions
                if "✅ ULTRA-REFINED TRADE EXECUTED:" in line:
                    intention = self._parse_executed_trade(line, lines)
                    if intention:
                        intention.executed = True
                        intentions.append(intention)
                
                # 2. Rejected signals
                elif "❌ Signal rejected:" in line:
                    intention = self._parse_rejected_signal(line, lines)
                    if intention:
                        intention.executed = False
                        intentions.append(intention)
                
                # 3. Trade closures
                elif "🎯 TRADE CLOSED:" in line:
                    self._update_trade_outcome(line, intentions)
                
            except Exception as e:
                logger.debug(f"Error parsing line: {str(e)[:100]}...")
                continue
        
        self.bot_intentions = intentions
        logger.info(f"✅ Parsed {len(intentions)} bot trading intentions")
        return intentions
    
    def _parse_executed_trade(self, line: str, all_lines: List[str]) -> Optional[BotTradeIntention]:
        """Parse executed trade from log line."""
        try:
            # Extract basic info from the line
            # Look for patterns like: "EUR/USD BUY | Order ID: 12345"
            import re
            
            # Find the line with trade details
            trade_details = {}
            line_idx = all_lines.index(line) if line in all_lines else -1
            
            # Look at subsequent lines for trade details
            for i in range(max(0, line_idx - 5), min(len(all_lines), line_idx + 10)):
                detail_line = all_lines[i]
                
                # Extract various details
                if "Entry:" in detail_line:
                    match = re.search(r'Entry: ([\d.]+)', detail_line)
                    if match:
                        trade_details['entry_price'] = float(match.group(1))
                
                if "Stop Loss:" in detail_line:
                    match = re.search(r'Stop Loss: ([\d.]+)', detail_line)
                    if match:
                        trade_details['stop_loss'] = float(match.group(1))
                
                if "Take Profit:" in detail_line:
                    match = re.search(r'Take Profit: ([\d.]+)', detail_line)
                    if match:
                        trade_details['target_price'] = float(match.group(1))
                
                if "Position Size:" in detail_line:
                    match = re.search(r'Position Size: ([\d,]+)', detail_line)
                    if match:
                        trade_details['units'] = int(match.group(1).replace(',', ''))
                
                if "Risk/Reward:" in detail_line:
                    match = re.search(r'Risk/Reward: ([\d.]+)', detail_line)
                    if match:
                        trade_details['risk_reward_ratio'] = float(match.group(1))
            
            # Extract timestamp
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S') if timestamp_match else datetime.now()
            
            # Extract pair and signal type
            pair_match = re.search(r'(\w+/\w+) (\w+)', line)
            if not pair_match:
                return None
            
            pair, signal_type = pair_match.groups()
            
            return BotTradeIntention(
                timestamp=timestamp,
                pair=pair,
                signal_type=signal_type,
                confidence=0.65,  # Default, would need to extract from logs
                entry_price=trade_details.get('entry_price', 0),
                target_price=trade_details.get('target_price', 0),
                stop_loss=trade_details.get('stop_loss', 0),
                expected_units=trade_details.get('units', 0),
                expected_profit=0,  # Calculate from other fields
                expected_loss=0,    # Calculate from other fields
                risk_reward_ratio=trade_details.get('risk_reward_ratio', 0),
                executed=True
            )
            
        except Exception as e:
            logger.debug(f"Error parsing executed trade: {e}")
            return None
    
    def _parse_rejected_signal(self, line: str, all_lines: List[str]) -> Optional[BotTradeIntention]:
        """Parse rejected signal from log line."""
        try:
            import re
            
            # Extract rejection reason
            reason_match = re.search(r'Signal rejected: (.+)', line)
            rejection_reason = reason_match.group(1) if reason_match else "Unknown"
            
            # Extract timestamp
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S') if timestamp_match else datetime.now()
            
            # Look for signal details in nearby lines
            line_idx = all_lines.index(line) if line in all_lines else -1
            
            # Default values - would need more sophisticated parsing
            return BotTradeIntention(
                timestamp=timestamp,
                pair="UNKNOWN",
                signal_type="UNKNOWN",
                confidence=0.0,
                entry_price=0,
                target_price=0,
                stop_loss=0,
                expected_units=0,
                expected_profit=0,
                expected_loss=0,
                risk_reward_ratio=0,
                rejection_reason=rejection_reason,
                executed=False
            )
            
        except Exception as e:
            logger.debug(f"Error parsing rejected signal: {e}")
            return None
    
    def _update_trade_outcome(self, line: str, intentions: List[BotTradeIntention]):
        """Update trade outcome from closure log."""
        # This would match closed trades with their original intentions
        # Implementation would depend on log format
        pass
    
    def match_trades(self) -> List[Tuple[BotTradeIntention, OANDATransaction]]:
        """Match bot intentions with actual OANDA transactions."""
        matches = []
        
        for intention in self.bot_intentions:
            if not intention.executed:
                continue
                
            # Find matching OANDA transaction within time window
            for transaction in self.oanda_transactions:
                if self._trades_match(intention, transaction):
                    matches.append((intention, transaction))
                    break
        
        self.matched_trades = matches
        logger.info(f"✅ Matched {len(matches)} trades between bot intentions and OANDA transactions")
        return matches
    
    def _trades_match(self, intention: BotTradeIntention, transaction: OANDATransaction) -> bool:
        """Check if bot intention matches OANDA transaction."""
        # Check instrument
        if intention.pair.replace('/', '_') != transaction.instrument:
            return False
        
        # Check direction
        if intention.signal_type == 'BUY' and transaction.units <= 0:
            return False
        if intention.signal_type == 'SELL' and transaction.units >= 0:
            return False
        
        # Check time window (within 5 minutes)
        time_diff = abs((intention.timestamp - transaction.time).total_seconds())
        if time_diff > 300:  # 5 minutes
            return False
        
        # Check price similarity (within 0.1%)
        if abs(intention.entry_price - transaction.price) / transaction.price > 0.001:
            return False
        
        return True
    
    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        total_bot_signals = len(self.bot_intentions)
        executed_intentions = [i for i in self.bot_intentions if i.executed]
        total_oanda_trades = len(self.oanda_transactions)
        matched_trades = len(self.matched_trades)
        
        # Calculate execution accuracy
        execution_accuracy = (matched_trades / len(executed_intentions)) if executed_intentions else 0
        
        # Missed opportunities (bot wanted to trade but didn't)
        missed_opportunities = len([i for i in self.bot_intentions if not i.executed])
        
        # Unexpected trades (OANDA trades without bot intention)
        unexpected_trades = total_oanda_trades - matched_trades
        
        # Confidence analysis
        winning_trades = [m for m in self.matched_trades if m[1].pl > 0]
        losing_trades = [m for m in self.matched_trades if m[1].pl < 0]
        
        avg_confidence_winners = statistics.mean([m[0].confidence for m in winning_trades]) if winning_trades else 0
        avg_confidence_losers = statistics.mean([m[0].confidence for m in losing_trades]) if losing_trades else 0
        
        # Win rates
        bot_win_rate = len(winning_trades) / len(self.matched_trades) if self.matched_trades else 0
        actual_win_rate = len([t for t in self.oanda_transactions if t.pl > 0]) / len(self.oanda_transactions) if self.oanda_transactions else 0
        
        # Profit analysis
        predicted_profit = sum([i.expected_profit for i in executed_intentions if i.expected_profit])
        actual_profit = sum([t.pl for t in self.oanda_transactions])
        
        # Execution delay
        execution_delays = []
        for intention, transaction in self.matched_trades:
            delay = (transaction.time - intention.timestamp).total_seconds()
            execution_delays.append(delay)
        
        avg_execution_delay = statistics.mean(execution_delays) if execution_delays else 0
        
        return PerformanceMetrics(
            total_bot_signals=total_bot_signals,
            total_oanda_trades=total_oanda_trades,
            matched_trades=matched_trades,
            missed_opportunities=missed_opportunities,
            unexpected_trades=unexpected_trades,
            execution_accuracy=execution_accuracy,
            avg_confidence_winners=avg_confidence_winners,
            avg_confidence_losers=avg_confidence_losers,
            bot_win_rate=bot_win_rate,
            actual_win_rate=actual_win_rate,
            predicted_profit=predicted_profit,
            actual_profit=actual_profit,
            avg_execution_delay=avg_execution_delay
        )
    
    def generate_improvement_suggestions(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []
        
        # Execution accuracy
        if metrics.execution_accuracy < 0.8:
            suggestions.append(f"🔧 Low execution accuracy ({metrics.execution_accuracy:.1%}). Check API connectivity and order placement logic.")
        
        # Confidence thresholds
        if metrics.avg_confidence_winners < metrics.avg_confidence_losers:
            suggestions.append("🎯 Consider raising confidence threshold - winning trades have lower average confidence than losing trades.")
        
        # Execution delays
        if metrics.avg_execution_delay > 30:
            suggestions.append(f"⚡ High execution delay ({metrics.avg_execution_delay:.1f}s). Optimize order placement speed.")
        
        # Missed opportunities
        if metrics.missed_opportunities > metrics.matched_trades:
            suggestions.append("📈 Many signals rejected. Review filtering criteria - may be too restrictive.")
        
        # Unexpected trades
        if metrics.unexpected_trades > 0:
            suggestions.append(f"❓ {metrics.unexpected_trades} unexpected trades detected. Check for manual interventions or external signals.")
        
        # Profit prediction accuracy
        if abs(metrics.predicted_profit - metrics.actual_profit) > abs(metrics.predicted_profit * 0.2):
            suggestions.append("🎯 Large difference between predicted and actual profit. Review risk/reward calculations.")
        
        # Win rate comparison
        if metrics.bot_win_rate < 0.5 and metrics.actual_win_rate > 0.5:
            suggestions.append("🔄 Bot win rate lower than overall performance. Review signal quality.")
        
        return suggestions
    
    def generate_comprehensive_report(self) -> str:
        """Generate a comprehensive performance analysis report."""
        metrics = self.calculate_performance_metrics()
        suggestions = self.generate_improvement_suggestions(metrics)
        
        report = f"""
# 🚀 Live Trading Performance Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 Executive Summary
- **Total Bot Signals**: {metrics.total_bot_signals}
- **Total OANDA Trades**: {metrics.total_oanda_trades}
- **Matched Trades**: {metrics.matched_trades}
- **Execution Accuracy**: {metrics.execution_accuracy:.1%}
- **Bot Win Rate**: {metrics.bot_win_rate:.1%}
- **Actual Win Rate**: {metrics.actual_win_rate:.1%}
- **Actual Profit**: ${metrics.actual_profit:.2f}

## 🎯 Trade Matching Analysis
- **Successfully Matched**: {metrics.matched_trades} trades
- **Missed Opportunities**: {metrics.missed_opportunities} (signals not executed)
- **Unexpected Trades**: {metrics.unexpected_trades} (trades without bot signals)
- **Average Execution Delay**: {metrics.avg_execution_delay:.1f} seconds

## 🧠 Confidence Analysis
- **Average Confidence (Winners)**: {metrics.avg_confidence_winners:.1%}
- **Average Confidence (Losers)**: {metrics.avg_confidence_losers:.1%}
- **Confidence Effectiveness**: {"✅ Good" if metrics.avg_confidence_winners > metrics.avg_confidence_losers else "❌ Needs Improvement"}

## 💰 Profit Analysis
- **Predicted Profit**: ${metrics.predicted_profit:.2f}
- **Actual Profit**: ${metrics.actual_profit:.2f}
- **Prediction Accuracy**: {100 - abs(metrics.predicted_profit - metrics.actual_profit) / max(abs(metrics.predicted_profit), 1) * 100:.1f}%

## 🔧 Improvement Suggestions
"""
        
        for i, suggestion in enumerate(suggestions, 1):
            report += f"\n{i}. {suggestion}"
        
        if not suggestions:
            report += "\n✅ No major issues detected. Performance looks good!"
        
        report += f"""

## 📈 Key Performance Indicators
- **Signal-to-Execution Ratio**: {metrics.matched_trades / max(metrics.total_bot_signals, 1) * 100:.1f}%
- **Trade Efficiency Score**: {metrics.execution_accuracy * metrics.bot_win_rate * 100:.1f}%
- **Profit Prediction Score**: {100 - abs(metrics.predicted_profit - metrics.actual_profit) / max(abs(metrics.predicted_profit), 1) * 100:.1f}%

## 🎯 Recommendations Priority
1. **High Priority**: Execution accuracy and unexpected trades
2. **Medium Priority**: Confidence threshold optimization
3. **Low Priority**: Minor timing improvements

---
*Analysis based on recent trading data from OANDA API and Railway logs*
        """
        
        return report
    
    def run_complete_analysis(self, days_back: int = 7, hours_back: int = 24) -> str:
        """Run complete analysis pipeline."""
        logger.info("🚀 Starting comprehensive trading performance analysis...")
        
        # Step 1: Fetch OANDA data
        logger.info("📡 Fetching OANDA transaction data...")
        self.fetch_oanda_transactions(days_back)
        
        # Step 2: Fetch Railway logs
        logger.info("📋 Fetching Railway bot logs...")
        log_content = self.fetch_railway_logs(hours_back)
        
        # Step 3: Parse bot intentions
        logger.info("🔍 Parsing bot trading intentions...")
        self.parse_bot_intentions(log_content)
        
        # Step 4: Match trades
        logger.info("🔗 Matching bot intentions with OANDA trades...")
        self.match_trades()
        
        # Step 5: Generate report
        logger.info("📊 Generating comprehensive report...")
        report = self.generate_comprehensive_report()
        
        logger.info("✅ Analysis complete!")
        return report


def main():
    """Run the live trading performance analysis."""
    try:
        analyzer = LiveTradingPerformanceAnalyzer()
        
        # Run analysis for past week
        report = analyzer.run_complete_analysis(days_back=7, hours_back=48)
        
        # Print report
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"trading_performance_report_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {filename}")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main() 