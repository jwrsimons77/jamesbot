#!/usr/bin/env python3
"""
🚂 Railway Bot Log Analyzer
Analyzes Railway bot logs to understand trading decisions and performance
Compares bot actions with actual OANDA trade outcomes
"""

import os
import requests
import re
from datetime import datetime, timezone
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
import json

class RailwayBotLogAnalyzer:
    """Analyze Railway bot logs and compare with OANDA performance."""
    
    def __init__(self):
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID')
        self.oanda_base_url = "https://api-fxpractice.oanda.com"
        
        # Bot log data
        self.closed_positions = []
        self.trading_sessions = []
        self.daily_limits = []
        self.account_summaries = []
        
        # OANDA comparison data
        self.oanda_trades = []
        
    def fetch_railway_logs(self) -> str:
        """Fetch Railway logs using CLI."""
        import subprocess
        try:
            result = subprocess.run(['railway', 'logs'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"❌ Railway logs error: {result.stderr}")
                return ""
        except Exception as e:
            print(f"❌ Error fetching Railway logs: {e}")
            return ""
    
    def parse_railway_logs(self, log_content: str) -> Dict:
        """Parse Railway logs to extract trading information."""
        if not log_content:
            return {}
        
        lines = log_content.split('\n')
        
        # Parse closed positions
        closed_positions = []
        trading_sessions = []
        daily_limits = []
        account_summaries = []
        
        for line in lines:
            try:
                # Parse closed positions
                if "🔍 Detected closed position:" in line:
                    match = re.search(r'🔍 Detected closed position: (\w+/\w+) \(Trade ID: (\d+)\)', line)
                    if match:
                        pair = match.group(1)
                        trade_id = match.group(2)
                        closed_positions.append({
                            'pair': pair,
                            'trade_id': trade_id,
                            'timestamp': self._extract_timestamp(line)
                        })
                
                # Parse trading sessions
                elif "🚀 Starting trading session..." in line:
                    trading_sessions.append({
                        'timestamp': self._extract_timestamp(line),
                        'action': 'session_start'
                    })
                
                # Parse daily limits
                elif "⏸️ Daily trade limit reached" in line:
                    match = re.search(r'Daily trade limit reached \((\d+)/(\d+)\)', line)
                    if match:
                        current_trades = int(match.group(1))
                        max_trades = int(match.group(2))
                        daily_limits.append({
                            'timestamp': self._extract_timestamp(line),
                            'current_trades': current_trades,
                            'max_trades': max_trades
                        })
                
                # Parse account summaries
                elif "💰 Account Balance:" in line:
                    balance_match = re.search(r'💰 Account Balance: \$([0-9,]+\.?\d*)', line)
                    if balance_match:
                        balance = float(balance_match.group(1).replace(',', ''))
                        account_summaries.append({
                            'timestamp': self._extract_timestamp(line),
                            'balance': balance,
                            'type': 'balance'
                        })
                
                elif "📊 NAV:" in line:
                    nav_match = re.search(r'📊 NAV: \$([0-9,]+\.?\d*)', line)
                    if nav_match and account_summaries:
                        nav = float(nav_match.group(1).replace(',', ''))
                        account_summaries[-1]['nav'] = nav
                
                elif "📈 Margin Used:" in line:
                    margin_match = re.search(r'📈 Margin Used: \$([0-9,]+\.?\d*)', line)
                    if margin_match and account_summaries:
                        margin_used = float(margin_match.group(1).replace(',', ''))
                        account_summaries[-1]['margin_used'] = margin_used
                
                elif "💚 Health check passed" in line:
                    balance_match = re.search(r'Balance: \$([0-9,]+\.?\d*)', line)
                    if balance_match:
                        balance = float(balance_match.group(1).replace(',', ''))
                        account_summaries.append({
                            'timestamp': self._extract_timestamp(line),
                            'balance': balance,
                            'type': 'health_check'
                        })
                
                elif "📈 Performance:" in line:
                    perf_match = re.search(r'📈 Performance: \$([+-]?[0-9,]+\.?\d*) \(([+-]?\d+\.?\d*)%\)', line)
                    if perf_match and account_summaries:
                        performance = float(perf_match.group(1).replace(',', ''))
                        percentage = float(perf_match.group(2))
                        account_summaries[-1]['performance'] = performance
                        account_summaries[-1]['performance_pct'] = percentage
                
            except Exception as e:
                continue
        
        self.closed_positions = closed_positions
        self.trading_sessions = trading_sessions
        self.daily_limits = daily_limits
        self.account_summaries = account_summaries
        
        return {
            'closed_positions': len(closed_positions),
            'trading_sessions': len(trading_sessions),
            'daily_limits': len(daily_limits),
            'account_summaries': len(account_summaries)
        }
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        # Railway logs don't always have timestamps, so we'll use current time
        return datetime.now()
    
    def fetch_oanda_trades(self) -> List[Dict]:
        """Fetch OANDA trades for comparison."""
        try:
            headers = {
                'Authorization': f'Bearer {self.oanda_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Get current open trades
            trades_url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/openTrades"
            response = requests.get(trades_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                trades = data.get('trades', [])
                
                formatted_trades = []
                for trade in trades:
                    formatted_trades.append({
                        'id': trade.get('id'),
                        'instrument': trade.get('instrument', '').replace('_', '/'),
                        'units': float(trade.get('currentUnits', 0)),
                        'open_price': float(trade.get('price', 0)),
                        'unrealized_pl': float(trade.get('unrealizedPL', 0)),
                        'open_time': trade.get('openTime', ''),
                        'status': 'OPEN'
                    })
                
                self.oanda_trades = formatted_trades
                return formatted_trades
            
        except Exception as e:
            print(f"❌ Error fetching OANDA trades: {e}")
            return []
    
    def analyze_bot_performance(self) -> Dict:
        """Analyze bot performance from logs."""
        if not self.closed_positions:
            return {'error': 'No closed positions found in logs'}
        
        # Count pairs traded
        pair_counts = Counter([pos['pair'] for pos in self.closed_positions])
        
        # Analyze trading frequency
        total_closed = len(self.closed_positions)
        unique_pairs = len(pair_counts)
        
        # Daily trading patterns
        daily_limits_hit = len(self.daily_limits)
        avg_trades_per_limit = sum([dl['current_trades'] for dl in self.daily_limits]) / len(self.daily_limits) if self.daily_limits else 0
        
        # Account progression
        account_progression = []
        for summary in self.account_summaries:
            if 'balance' in summary:
                account_progression.append({
                    'balance': summary['balance'],
                    'performance': summary.get('performance', 0),
                    'performance_pct': summary.get('performance_pct', 0),
                    'type': summary.get('type', 'unknown')
                })
        
        return {
            'trading_activity': {
                'total_closed_positions': total_closed,
                'unique_pairs_traded': unique_pairs,
                'most_traded_pairs': dict(pair_counts.most_common(5)),
                'daily_limits_hit': daily_limits_hit,
                'avg_trades_per_session': avg_trades_per_limit
            },
            'account_progression': account_progression,
            'trading_sessions': len(self.trading_sessions),
            'bot_activity_level': 'HIGH' if total_closed > 50 else 'MODERATE' if total_closed > 20 else 'LOW'
        }
    
    def compare_bot_vs_oanda(self) -> Dict:
        """Compare bot log data with actual OANDA positions."""
        bot_pairs = set([pos['pair'] for pos in self.closed_positions])
        oanda_pairs = set([trade['instrument'] for trade in self.oanda_trades])
        
        # Find trade IDs mentioned in bot logs
        bot_trade_ids = set([pos['trade_id'] for pos in self.closed_positions])
        oanda_trade_ids = set([trade['id'] for trade in self.oanda_trades])
        
        # Pair analysis
        bot_only_pairs = bot_pairs - oanda_pairs
        oanda_only_pairs = oanda_pairs - bot_pairs
        common_pairs = bot_pairs & oanda_pairs
        
        # Current OANDA positions analysis
        current_positions = []
        total_unrealized_pl = 0
        
        for trade in self.oanda_trades:
            direction = 'LONG' if trade['units'] > 0 else 'SHORT'
            current_positions.append({
                'pair': trade['instrument'],
                'direction': direction,
                'units': abs(trade['units']),
                'unrealized_pl': trade['unrealized_pl'],
                'open_price': trade['open_price']
            })
            total_unrealized_pl += trade['unrealized_pl']
        
        return {
            'pair_comparison': {
                'bot_tracked_pairs': list(bot_pairs),
                'oanda_current_pairs': list(oanda_pairs),
                'common_pairs': list(common_pairs),
                'bot_only_pairs': list(bot_only_pairs),
                'oanda_only_pairs': list(oanda_only_pairs)
            },
            'current_oanda_positions': current_positions,
            'total_unrealized_pl': total_unrealized_pl,
            'position_count': len(current_positions),
            'bot_closed_positions': len(self.closed_positions),
            'sync_status': 'PARTIAL' if bot_only_pairs or oanda_only_pairs else 'SYNCHRONIZED'
        }
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive analysis report."""
        print("🚂 RAILWAY BOT LOG ANALYSIS")
        print("=" * 60)
        
        # Fetch and parse logs
        print("📋 Fetching Railway logs...")
        log_content = self.fetch_railway_logs()
        
        if not log_content:
            return "❌ No Railway logs found"
        
        print("🔍 Parsing bot logs...")
        parse_results = self.parse_railway_logs(log_content)
        
        print("📡 Fetching OANDA data...")
        self.fetch_oanda_trades()
        
        print("📊 Analyzing bot performance...")
        bot_analysis = self.analyze_bot_performance()
        
        print("🔄 Comparing bot vs OANDA...")
        comparison = self.compare_bot_vs_oanda()
        
        # Generate report
        report = f"""
# 🚂 Railway Bot Trading Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 LOG PARSING SUMMARY
- **Closed Positions Detected**: {parse_results.get('closed_positions', 0)}
- **Trading Sessions**: {parse_results.get('trading_sessions', 0)}
- **Daily Limits Hit**: {parse_results.get('daily_limits', 0)}
- **Account Summaries**: {parse_results.get('account_summaries', 0)}

## 🤖 BOT PERFORMANCE ANALYSIS
"""
        
        if 'error' not in bot_analysis:
            activity = bot_analysis.get('trading_activity', {})
            report += f"""
### Trading Activity:
- **Total Closed Positions**: {activity.get('total_closed_positions', 0)}
- **Unique Pairs Traded**: {activity.get('unique_pairs_traded', 0)}
- **Bot Activity Level**: {bot_analysis.get('bot_activity_level', 'UNKNOWN')}
- **Trading Sessions**: {bot_analysis.get('trading_sessions', 0)}
- **Daily Limits Hit**: {activity.get('daily_limits_hit', 0)}

### Most Traded Pairs:
"""
            
            for pair, count in activity.get('most_traded_pairs', {}).items():
                report += f"- **{pair}**: {count} trades\n"
            
            # Account progression
            progression = bot_analysis.get('account_progression', [])
            if progression:
                latest = progression[-1]
                report += f"""
### Account Progression:
- **Latest Balance**: ${latest.get('balance', 0):,.2f}
- **Performance**: ${latest.get('performance', 0):,.2f} ({latest.get('performance_pct', 0):+.2f}%)
- **Health Checks**: {len([p for p in progression if p.get('type') == 'health_check'])}
"""
        
        # Comparison analysis
        report += f"""
## 🔄 BOT vs OANDA COMPARISON

### Current Status:
- **OANDA Open Positions**: {comparison.get('position_count', 0)}
- **Bot Closed Positions**: {comparison.get('bot_closed_positions', 0)}
- **Total Unrealized P&L**: ${comparison.get('total_unrealized_pl', 0):.2f}
- **Sync Status**: {comparison.get('sync_status', 'UNKNOWN')}

### Currency Pairs Analysis:
- **Bot Tracked Pairs**: {', '.join(comparison.get('pair_comparison', {}).get('bot_tracked_pairs', []))}
- **OANDA Current Pairs**: {', '.join(comparison.get('pair_comparison', {}).get('oanda_current_pairs', []))}
- **Common Pairs**: {', '.join(comparison.get('pair_comparison', {}).get('common_pairs', []))}
"""
        
        # Current positions
        current_positions = comparison.get('current_oanda_positions', [])
        if current_positions:
            report += f"\n### Current OANDA Positions:\n"
            for i, pos in enumerate(current_positions, 1):
                status = "🟢" if pos['unrealized_pl'] > 0 else "🔴" if pos['unrealized_pl'] < 0 else "⚪"
                report += f"{i}. {status} **{pos['pair']} {pos['direction']}**: {pos['units']:,.0f} units, ${pos['unrealized_pl']:.2f} P&L\n"
        
        # Key insights
        report += f"""
## 🎯 KEY INSIGHTS

### Bot Activity Patterns:
"""
        
        if bot_analysis.get('bot_activity_level') == 'HIGH':
            report += "- **Very Active Bot**: High trading frequency indicates aggressive strategy\n"
        elif bot_analysis.get('bot_activity_level') == 'MODERATE':
            report += "- **Moderate Activity**: Balanced trading approach\n"
        else:
            report += "- **Low Activity**: Conservative or selective trading\n"
        
        # Pair focus analysis
        most_traded = bot_analysis.get('trading_activity', {}).get('most_traded_pairs', {})
        if most_traded:
            top_pair = list(most_traded.keys())[0]
            top_count = most_traded[top_pair]
            report += f"- **Pair Focus**: {top_pair} is most actively traded ({top_count} positions)\n"
        
        # Performance insights
        if comparison.get('total_unrealized_pl', 0) > 0:
            report += f"- **Currently Profitable**: ${comparison.get('total_unrealized_pl', 0):.2f} unrealized gains\n"
        elif comparison.get('total_unrealized_pl', 0) < 0:
            report += f"- **Currently At Loss**: ${comparison.get('total_unrealized_pl', 0):.2f} unrealized losses\n"
        
        report += f"""
### Recommendations:
1. **Monitor daily limits** - Bot hitting {bot_analysis.get('trading_activity', {}).get('daily_limits_hit', 0)} daily limits
2. **Focus on profitable pairs** - Continue with successful strategies
3. **Risk management** - Current portfolio shows {comparison.get('position_count', 0)} open positions
4. **Regular monitoring** - Bot shows {bot_analysis.get('bot_activity_level', 'UNKNOWN')} activity level

---
*Analysis based on Railway bot logs and live OANDA data*
        """
        
        return report

def main():
    """Run the Railway bot log analysis."""
    try:
        analyzer = RailwayBotLogAnalyzer()
        report = analyzer.generate_comprehensive_report()
        print(report)
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"railway_bot_analysis_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise

if __name__ == "__main__":
    main() 