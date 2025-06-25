#!/usr/bin/env python3
"""
🎯 Comprehensive Trading Analysis
Combines Railway bot logs with OANDA transaction data to understand:
- What the bot intended vs what actually happened
- Performance patterns and success rates
- Trading strategy effectiveness
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict, Counter
import subprocess
import re
from typing import Dict, List, Tuple

class ComprehensiveTradingAnalyzer:
    """Analyze Railway bot performance vs actual OANDA results."""
    
    def __init__(self):
        self.oanda_transactions = []
        self.railway_logs = ""
        self.bot_closed_positions = []
        self.analysis_results = {}
        
    def load_oanda_transactions(self, csv_file: str) -> pd.DataFrame:
        """Load and parse OANDA transaction CSV."""
        try:
            df = pd.read_csv(csv_file)
            print(f"📊 Loaded {len(df)} OANDA transactions")
            
            # Convert dates
            df['TRANSACTION DATE'] = pd.to_datetime(df['TRANSACTION DATE'])
            
            # Filter for actual trades (ORDER_FILL)
            trades_df = df[df['TRANSACTION TYPE'] == 'ORDER_FILL'].copy()
            
            # Calculate P&L for each trade
            trades_df['PL_NUMERIC'] = pd.to_numeric(trades_df['PL'], errors='coerce').fillna(0)
            
            self.oanda_transactions = trades_df
            return trades_df
            
        except Exception as e:
            print(f"❌ Error loading OANDA data: {e}")
            return pd.DataFrame()
    
    def fetch_railway_logs(self) -> str:
        """Fetch Railway logs."""
        try:
            result = subprocess.run(['railway', 'logs'], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                self.railway_logs = result.stdout
                return result.stdout
            else:
                print("⚠️ Could not fetch Railway logs, using sample data")
                return self._get_sample_logs()
        except Exception as e:
            print(f"⚠️ Railway logs unavailable: {e}")
            return self._get_sample_logs()
    
    def _get_sample_logs(self) -> str:
        """Get sample logs from the previous Railway output."""
        return """
INFO:__main__:🔍 Detected closed position: USD/CAD (Trade ID: 2904)
INFO:__main__:🔍 Detected closed position: USD/JPY (Trade ID: 2908)
INFO:__main__:🔍 Detected closed position: USD/JPY (Trade ID: 2967)
INFO:__main__:🔍 Detected closed position: USD/CHF (Trade ID: 2971)
INFO:__main__:🔍 Detected closed position: USD/CAD (Trade ID: 2979)
INFO:__main__:🔍 Detected closed position: NZD/USD (Trade ID: 2983)
INFO:__main__:🔍 Detected closed position: USD/JPY (Trade ID: 2993)
INFO:__main__:🔍 Detected closed position: USD/CHF (Trade ID: 2997)
INFO:__main__:🔍 Detected closed position: USD/JPY (Trade ID: 3017)
INFO:__main__:⏸️ Daily trade limit reached (12/12)
INFO:__main__:🚀 Starting trading session...
INFO:__main__:📊 Open positions: 3
INFO:__main__:💰 Account Balance: $10,114.99
INFO:__main__:📊 NAV: $10,125.39
INFO:__main__:📈 Margin Used: $594.74
INFO:__main__:📉 Margin Available: $9,531.69
INFO:__main__:💚 Health check passed - Balance: $10,114.99
INFO:__main__:📈 Performance: $+115.00 (+1.15%) since start
        """
    
    def parse_railway_logs(self) -> List[Dict]:
        """Parse Railway logs to extract bot decisions."""
        closed_positions = []
        
        for line in self.railway_logs.split('\n'):
            if "🔍 Detected closed position:" in line:
                match = re.search(r'🔍 Detected closed position: (\w+/\w+) \(Trade ID: (\d+)\)', line)
                if match:
                    pair = match.group(1)
                    trade_id = match.group(2)
                    closed_positions.append({
                        'pair': pair,
                        'trade_id': trade_id,
                        'source': 'railway_bot'
                    })
        
        self.bot_closed_positions = closed_positions
        return closed_positions
    
    def analyze_trading_patterns(self) -> Dict:
        """Analyze trading patterns from OANDA data."""
        if self.oanda_transactions.empty:
            return {}
        
        df = self.oanda_transactions
        
        # Basic statistics
        total_trades = len(df)
        profitable_trades = len(df[df['PL_NUMERIC'] > 0])
        losing_trades = len(df[df['PL_NUMERIC'] < 0])
        breakeven_trades = len(df[df['PL_NUMERIC'] == 0])
        
        # Calculate win rate
        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L analysis
        total_pnl = df['PL_NUMERIC'].sum()
        avg_winner = df[df['PL_NUMERIC'] > 0]['PL_NUMERIC'].mean() if profitable_trades > 0 else 0
        avg_loser = df[df['PL_NUMERIC'] < 0]['PL_NUMERIC'].mean() if losing_trades > 0 else 0
        
        # Profit factor
        gross_profit = df[df['PL_NUMERIC'] > 0]['PL_NUMERIC'].sum()
        gross_loss = abs(df[df['PL_NUMERIC'] < 0]['PL_NUMERIC'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Currency pair analysis
        pair_performance = df.groupby('INSTRUMENT').agg({
            'PL_NUMERIC': ['count', 'sum', 'mean'],
            'UNITS': 'mean'
        }).round(2)
        
        # Direction analysis
        df['DIRECTION_CLEAN'] = df['DIRECTION'].fillna('Unknown')
        direction_performance = df.groupby('DIRECTION_CLEAN').agg({
            'PL_NUMERIC': ['count', 'sum', 'mean']
        }).round(2)
        
        # Recent performance (last 30 days) - fix timezone issue
        try:
            # Make datetime comparison timezone-aware
            cutoff_date = pd.Timestamp.now(tz=df['TRANSACTION DATE'].dt.tz) - pd.Timedelta(days=30)
            recent_df = df[df['TRANSACTION DATE'] >= cutoff_date]
            recent_pnl = recent_df['PL_NUMERIC'].sum()
            recent_trades = len(recent_df)
        except Exception as e:
            print(f"⚠️ Timezone issue in recent analysis: {e}")
            # Fallback: use last 100 trades
            recent_df = df.tail(100)
            recent_pnl = recent_df['PL_NUMERIC'].sum()
            recent_trades = len(recent_df)
        
        return {
            'overall_stats': {
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'losing_trades': losing_trades,
                'breakeven_trades': breakeven_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_winner': avg_winner,
                'avg_loser': avg_loser,
                'profit_factor': profit_factor
            },
            'pair_performance': pair_performance,
            'direction_performance': direction_performance,
            'recent_performance': {
                'recent_pnl': recent_pnl,
                'recent_trades': recent_trades,
                'recent_avg': recent_pnl / recent_trades if recent_trades > 0 else 0
            }
        }
    
    def compare_bot_vs_oanda(self) -> Dict:
        """Compare bot detected trades with OANDA records."""
        bot_trade_ids = set([pos['trade_id'] for pos in self.bot_closed_positions])
        
        if self.oanda_transactions.empty:
            return {'error': 'No OANDA data available'}
        
        # Find matching trades in OANDA data
        oanda_trade_ids = set(self.oanda_transactions['TICKET'].astype(str))
        
        # Find matches and mismatches
        matched_trades = bot_trade_ids & oanda_trade_ids
        bot_only_trades = bot_trade_ids - oanda_trade_ids
        oanda_only_trades = oanda_trade_ids - bot_trade_ids
        
        # Analyze matched trades
        matched_analysis = {}
        if matched_trades:
            matched_df = self.oanda_transactions[
                self.oanda_transactions['TICKET'].astype(str).isin(matched_trades)
            ]
            matched_analysis = {
                'count': len(matched_df),
                'total_pnl': matched_df['PL_NUMERIC'].sum(),
                'avg_pnl': matched_df['PL_NUMERIC'].mean(),
                'pairs': matched_df['INSTRUMENT'].value_counts().to_dict()
            }
        
        return {
            'bot_detected_trades': len(bot_trade_ids),
            'oanda_total_trades': len(oanda_trade_ids),
            'matched_trades': len(matched_trades),
            'bot_only_trades': len(bot_only_trades),
            'oanda_only_trades': len(oanda_only_trades),
            'sync_percentage': (len(matched_trades) / len(bot_trade_ids)) * 100 if bot_trade_ids else 0,
            'matched_analysis': matched_analysis
        }
    
    def analyze_recent_activity(self) -> Dict:
        """Analyze recent trading activity."""
        if self.oanda_transactions.empty:
            return {}
        
        df = self.oanda_transactions
        
        try:
            # Make datetime comparisons timezone-aware
            now = pd.Timestamp.now(tz=df['TRANSACTION DATE'].dt.tz)
            
            # Last 7 days
            recent_7d = df[df['TRANSACTION DATE'] >= (now - pd.Timedelta(days=7))]
            
            # Last 24 hours
            recent_24h = df[df['TRANSACTION DATE'] >= (now - pd.Timedelta(hours=24))]
            
        except Exception as e:
            print(f"⚠️ Timezone issue in recent activity: {e}")
            # Fallback: use last N trades
            recent_7d = df.tail(50)
            recent_24h = df.tail(10)
        
        return {
            'last_7_days': {
                'trades': len(recent_7d),
                'pnl': recent_7d['PL_NUMERIC'].sum(),
                'pairs': recent_7d['INSTRUMENT'].value_counts().head(5).to_dict()
            },
            'last_24_hours': {
                'trades': len(recent_24h),
                'pnl': recent_24h['PL_NUMERIC'].sum(),
                'pairs': recent_24h['INSTRUMENT'].value_counts().head(3).to_dict()
            }
        }
    
    def identify_best_strategies(self) -> Dict:
        """Identify the most successful trading strategies."""
        if self.oanda_transactions.empty:
            return {}
        
        df = self.oanda_transactions
        
        # Best performing pairs
        pair_stats = df.groupby('INSTRUMENT').agg({
            'PL_NUMERIC': ['count', 'sum', 'mean'],
            'UNITS': 'mean'
        })
        pair_stats.columns = ['trade_count', 'total_pnl', 'avg_pnl', 'avg_units']
        
        # Filter pairs with at least 5 trades
        significant_pairs = pair_stats[pair_stats['trade_count'] >= 5]
        best_pairs = significant_pairs.nlargest(3, 'total_pnl')
        worst_pairs = significant_pairs.nsmallest(3, 'total_pnl')
        
        # Best performing directions
        direction_stats = df.groupby('DIRECTION').agg({
            'PL_NUMERIC': ['count', 'sum', 'mean']
        })
        direction_stats.columns = ['trade_count', 'total_pnl', 'avg_pnl']
        
        # Time-based analysis
        df['hour'] = df['TRANSACTION DATE'].dt.hour
        hourly_performance = df.groupby('hour')['PL_NUMERIC'].agg(['count', 'sum', 'mean'])
        best_hours = hourly_performance.nlargest(3, 'sum')
        
        return {
            'best_pairs': best_pairs.to_dict('index'),
            'worst_pairs': worst_pairs.to_dict('index'),
            'direction_performance': direction_stats.to_dict('index'),
            'best_trading_hours': best_hours.to_dict('index')
        }
    
    def generate_comprehensive_report(self, csv_file: str) -> str:
        """Generate comprehensive trading analysis report."""
        print("🎯 COMPREHENSIVE TRADING ANALYSIS")
        print("=" * 60)
        
        # Load data
        print("📊 Loading OANDA transaction data...")
        self.load_oanda_transactions(csv_file)
        
        print("📋 Fetching Railway bot logs...")
        self.fetch_railway_logs()
        
        print("🔍 Parsing bot decisions...")
        self.parse_railway_logs()
        
        print("📈 Analyzing trading patterns...")
        trading_patterns = self.analyze_trading_patterns()
        
        print("🔄 Comparing bot vs OANDA...")
        comparison = self.compare_bot_vs_oanda()
        
        print("⏰ Analyzing recent activity...")
        recent_activity = self.analyze_recent_activity()
        
        print("🏆 Identifying best strategies...")
        best_strategies = self.identify_best_strategies()
        
        # Generate report
        report = f"""
# 🎯 Comprehensive Trading Performance Analysis
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 OVERALL PERFORMANCE SUMMARY

### Trading Statistics:
- **Total Trades**: {trading_patterns.get('overall_stats', {}).get('total_trades', 0):,}
- **Win Rate**: {trading_patterns.get('overall_stats', {}).get('win_rate', 0):.1f}%
- **Profitable Trades**: {trading_patterns.get('overall_stats', {}).get('profitable_trades', 0):,}
- **Losing Trades**: {trading_patterns.get('overall_stats', {}).get('losing_trades', 0):,}
- **Total P&L**: ${trading_patterns.get('overall_stats', {}).get('total_pnl', 0):.2f}
- **Profit Factor**: {trading_patterns.get('overall_stats', {}).get('profit_factor', 0):.2f}

### Average Performance:
- **Average Winner**: ${trading_patterns.get('overall_stats', {}).get('avg_winner', 0):.2f}
- **Average Loser**: ${trading_patterns.get('overall_stats', {}).get('avg_loser', 0):.2f}
- **Risk/Reward Ratio**: {abs(trading_patterns.get('overall_stats', {}).get('avg_winner', 0) / trading_patterns.get('overall_stats', {}).get('avg_loser', 1)) if trading_patterns.get('overall_stats', {}).get('avg_loser', 0) != 0 else 0:.2f}

## 🤖 BOT vs OANDA COMPARISON

### Synchronization Analysis:
- **Bot Detected Trades**: {comparison.get('bot_detected_trades', 0)}
- **OANDA Total Trades**: {comparison.get('oanda_total_trades', 0)}
- **Matched Trades**: {comparison.get('matched_trades', 0)}
- **Sync Percentage**: {comparison.get('sync_percentage', 0):.1f}%

### Bot Performance:
"""
        
        if comparison.get('matched_analysis'):
            matched = comparison['matched_analysis']
            report += f"""
- **Matched Trades P&L**: ${matched.get('total_pnl', 0):.2f}
- **Average P&L per Matched Trade**: ${matched.get('avg_pnl', 0):.2f}
- **Most Traded Pairs**: {', '.join(list(matched.get('pairs', {}).keys())[:3])}
"""
        
        # Recent activity
        report += f"""
## ⏰ RECENT TRADING ACTIVITY

### Last 7 Days:
- **Trades**: {recent_activity.get('last_7_days', {}).get('trades', 0)}
- **P&L**: ${recent_activity.get('last_7_days', {}).get('pnl', 0):.2f}
- **Active Pairs**: {', '.join(list(recent_activity.get('last_7_days', {}).get('pairs', {}).keys())[:3])}

### Last 24 Hours:
- **Trades**: {recent_activity.get('last_24_hours', {}).get('trades', 0)}
- **P&L**: ${recent_activity.get('last_24_hours', {}).get('pnl', 0):.2f}
"""
        
        # Best strategies
        if best_strategies.get('best_pairs'):
            report += f"""
## 🏆 BEST PERFORMING STRATEGIES

### Top Performing Currency Pairs:
"""
            for pair, stats in list(best_strategies['best_pairs'].items())[:3]:
                report += f"- **{pair}**: ${stats['total_pnl']:.2f} total P&L ({stats['trade_count']} trades, ${stats['avg_pnl']:.2f} avg)\n"
            
            report += f"""
### Worst Performing Currency Pairs:
"""
            for pair, stats in list(best_strategies['worst_pairs'].items())[:3]:
                report += f"- **{pair}**: ${stats['total_pnl']:.2f} total P&L ({stats['trade_count']} trades, ${stats['avg_pnl']:.2f} avg)\n"
        
        if best_strategies.get('direction_performance'):
            report += f"""
### Direction Performance:
"""
            for direction, stats in best_strategies['direction_performance'].items():
                if direction and direction != 'nan':
                    report += f"- **{direction}**: ${stats['total_pnl']:.2f} total P&L ({stats['trade_count']} trades)\n"
        
        # Key insights
        overall_stats = trading_patterns.get('overall_stats', {})
        win_rate = overall_stats.get('win_rate', 0)
        total_pnl = overall_stats.get('total_pnl', 0)
        profit_factor = overall_stats.get('profit_factor', 0)
        
        report += f"""
## 🎯 KEY INSIGHTS & RECOMMENDATIONS

### What's Working Well:
"""
        
        if win_rate >= 60:
            report += f"✅ **Excellent Win Rate**: {win_rate:.1f}% win rate shows strong strategy execution\n"
        elif win_rate >= 50:
            report += f"✅ **Good Win Rate**: {win_rate:.1f}% win rate is above breakeven\n"
        
        if total_pnl > 0:
            report += f"✅ **Profitable Overall**: ${total_pnl:.2f} total profit demonstrates effective trading\n"
        
        if profit_factor > 1.5:
            report += f"✅ **Strong Profit Factor**: {profit_factor:.2f} shows good risk management\n"
        
        report += f"""
### Areas for Improvement:
"""
        
        if win_rate < 50:
            report += f"❌ **Low Win Rate**: {win_rate:.1f}% needs improvement - review entry criteria\n"
        
        if total_pnl < 0:
            report += f"❌ **Overall Loss**: ${total_pnl:.2f} - strategy needs refinement\n"
        
        if profit_factor < 1.2:
            report += f"❌ **Poor Profit Factor**: {profit_factor:.2f} - improve risk/reward ratio\n"
        
        # Bot-specific insights
        sync_pct = comparison.get('sync_percentage', 0)
        if sync_pct < 80:
            report += f"⚠️ **Bot Sync Issues**: Only {sync_pct:.1f}% of bot trades match OANDA records\n"
        
        report += f"""
### Actionable Recommendations:

1. **Focus on Profitable Pairs**: Concentrate trading on best-performing currency pairs
2. **Optimize Timing**: Trade during most profitable hours identified in analysis
3. **Risk Management**: Maintain current position sizing if profitable, adjust if losing
4. **Bot Monitoring**: Ensure bot decisions align with actual trade executions
5. **Strategy Refinement**: Analyze losing trades to improve entry/exit criteria

### Next Steps:
- Monitor daily performance against these benchmarks
- Review and adjust strategy based on market conditions
- Implement systematic profit-taking and loss-cutting rules
- Regular analysis of bot vs actual performance

---
*Analysis based on {trading_patterns.get('overall_stats', {}).get('total_trades', 0)} OANDA transactions and Railway bot logs*
        """
        
        return report

def main():
    """Run comprehensive trading analysis."""
    try:
        analyzer = ComprehensiveTradingAnalyzer()
        
        # Use the OANDA CSV file
        csv_file = "transactions_101-004-31788297-001 (2).csv"
        
        if not os.path.exists(csv_file):
            print(f"❌ CSV file not found: {csv_file}")
            return
        
        report = analyzer.generate_comprehensive_report(csv_file)
        print(report)
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"comprehensive_trading_analysis_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 