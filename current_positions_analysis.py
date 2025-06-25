#!/usr/bin/env python3
"""
🎯 Current Positions Analysis
Quick analysis of current OANDA positions with actionable insights
"""

import os
import requests
from datetime import datetime, timezone
import json
from collections import defaultdict

def analyze_current_positions():
    """Analyze current trading positions and provide insights."""
    
    # OANDA API setup
    api_key = os.getenv('OANDA_API_KEY')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    base_url = "https://api-fxpractice.oanda.com"
    
    if not api_key or not account_id:
        print("❌ OANDA credentials not found")
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("🎯 CURRENT TRADING POSITIONS ANALYSIS")
    print("=" * 60)
    
    try:
        # 1. Get account summary
        account_url = f"{base_url}/v3/accounts/{account_id}"
        response = requests.get(account_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error fetching account: {response.status_code}")
            return
        
        account_data = response.json()
        account = account_data.get('account', {})
        
        balance = float(account.get('balance', 0))
        unrealized_pl = float(account.get('unrealizedPL', 0))
        open_trade_count = account.get('openTradeCount', 0)
        margin_used = float(account.get('marginUsed', 0))
        margin_available = float(account.get('marginAvailable', 0))
        currency = account.get('currency', 'USD')
        
        print(f"💰 ACCOUNT SUMMARY:")
        print(f"   Account Balance: {currency} {balance:,.2f}")
        print(f"   Current P&L: {currency} {unrealized_pl:,.2f}")
        print(f"   Open Positions: {open_trade_count}")
        print(f"   Margin Used: {currency} {margin_used:,.2f}")
        print(f"   Margin Available: {currency} {margin_available:,.2f}")
        print(f"   Margin Utilization: {(margin_used / (margin_used + margin_available)) * 100:.1f}%")
        
        # 2. Analyze current open trades
        trades_url = f"{base_url}/v3/accounts/{account_id}/openTrades"
        response = requests.get(trades_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            trades = data.get('trades', [])
            
            if not trades:
                print("\n📊 No open trades found")
                return
            
            print(f"\n📊 OPEN POSITIONS BREAKDOWN:")
            print(f"   Total Open Trades: {len(trades)}")
            
            # Track performance metrics
            total_profit = 0
            profitable_trades = 0
            losing_trades = 0
            pair_performance = defaultdict(lambda: {'count': 0, 'profit': 0, 'directions': []})
            
            # Analyze each trade
            for i, trade in enumerate(trades, 1):
                try:
                    trade_id = trade.get('id', 'Unknown')
                    instrument = trade.get('instrument', '')
                    pair = instrument.replace('_', '/')
                    units = float(trade.get('currentUnits', 0))
                    open_price = float(trade.get('price', 0))
                    unrealized_pl = float(trade.get('unrealizedPL', 0))
                    open_time_str = trade.get('openTime', '')
                    
                    # Calculate position details
                    direction = 'LONG' if units > 0 else 'SHORT'
                    position_size = abs(units)
                    
                    # Parse open time safely
                    days_open = "Unknown"
                    if open_time_str:
                        try:
                            # Handle different timestamp formats
                            clean_time = open_time_str.split('.')[0] + 'Z'
                            open_dt = datetime.fromisoformat(clean_time.replace('Z', '+00:00'))
                            duration = datetime.now(timezone.utc) - open_dt
                            days_open = duration.days
                        except:
                            days_open = "Unknown"
                    
                    # Status indicators
                    if unrealized_pl > 0:
                        status = "🟢 PROFITABLE"
                        profitable_trades += 1
                    elif unrealized_pl < 0:
                        status = "🔴 LOSING"
                        losing_trades += 1
                    else:
                        status = "⚪ BREAKEVEN"
                    
                    print(f"\n   Position {i}: {status}")
                    print(f"      Pair: {pair} ({direction})")
                    print(f"      Size: {position_size:,.0f} units")
                    print(f"      Entry: {open_price:.5f}")
                    print(f"      Current P&L: {currency} {unrealized_pl:.2f}")
                    print(f"      Days Open: {days_open}")
                    print(f"      Trade ID: {trade_id}")
                    
                    # Track totals
                    total_profit += unrealized_pl
                    pair_performance[pair]['count'] += 1
                    pair_performance[pair]['profit'] += unrealized_pl
                    pair_performance[pair]['directions'].append(direction)
                    
                except Exception as e:
                    print(f"   Error analyzing trade {i}: {e}")
                    continue
            
            # 3. Performance Analysis
            print(f"\n📈 PERFORMANCE ANALYSIS:")
            total_trades = len(trades)
            win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
            
            print(f"   Current Win Rate: {win_rate:.1f}% ({profitable_trades}/{total_trades})")
            print(f"   Total Unrealized P&L: {currency} {total_profit:.2f}")
            print(f"   Average P&L per Trade: {currency} {total_profit / total_trades:.2f}")
            
            # ROI calculation
            roi = (total_profit / balance) * 100 if balance > 0 else 0
            print(f"   Current ROI: {roi:.2f}%")
            
            # 4. Currency Pair Performance
            print(f"\n💱 PAIR PERFORMANCE BREAKDOWN:")
            
            for pair, stats in pair_performance.items():
                avg_profit = stats['profit'] / stats['count']
                directions = ', '.join(set(stats['directions']))
                status_emoji = "✅" if stats['profit'] > 0 else "❌" if stats['profit'] < 0 else "⚪"
                
                print(f"   {status_emoji} {pair}:")
                print(f"      Total P&L: {currency} {stats['profit']:.2f}")
                print(f"      Positions: {stats['count']} ({directions})")
                print(f"      Avg per position: {currency} {avg_profit:.2f}")
            
            # 5. Risk Assessment
            print(f"\n⚖️ RISK ASSESSMENT:")
            
            portfolio_risk = (margin_used / balance) * 100 if balance > 0 else 0
            risk_per_trade = portfolio_risk / total_trades if total_trades > 0 else 0
            
            print(f"   Portfolio Risk: {portfolio_risk:.1f}% of account")
            print(f"   Risk per Trade: {risk_per_trade:.1f}%")
            
            # Risk level assessment
            if portfolio_risk > 20:
                risk_level = "🔴 HIGH RISK"
                risk_advice = "Consider reducing position sizes"
            elif portfolio_risk > 10:
                risk_level = "🟡 MODERATE RISK"
                risk_advice = "Monitor closely"
            elif portfolio_risk < 2:
                risk_level = "🟢 CONSERVATIVE"
                risk_advice = "Could potentially increase position sizes"
            else:
                risk_level = "🟢 APPROPRIATE"
                risk_advice = "Risk level looks good"
            
            print(f"   Risk Level: {risk_level}")
            print(f"   Recommendation: {risk_advice}")
            
            # 6. Actionable Insights
            print(f"\n🎯 KEY INSIGHTS & RECOMMENDATIONS:")
            
            # Find best and worst performing pairs
            if pair_performance:
                best_pair = max(pair_performance.items(), key=lambda x: x[1]['profit'])
                worst_pair = min(pair_performance.items(), key=lambda x: x[1]['profit'])
                
                print(f"\n✅ WHAT'S WORKING WELL:")
                if best_pair[1]['profit'] > 0:
                    print(f"   • {best_pair[0]} is your top performer ({currency} {best_pair[1]['profit']:.2f})")
                    print(f"   • Strategy appears effective for {best_pair[0]}")
                
                if win_rate >= 50:
                    print(f"   • Solid win rate of {win_rate:.0f}% indicates good strategy execution")
                
                if total_profit > 0:
                    print(f"   • Currently profitable overall ({currency} {total_profit:.2f})")
                
                print(f"\n❌ AREAS FOR IMPROVEMENT:")
                if worst_pair[1]['profit'] < -5:
                    print(f"   • {worst_pair[0]} is underperforming ({currency} {worst_pair[1]['profit']:.2f})")
                    print(f"   • Consider reviewing {worst_pair[0]} strategy")
                
                if win_rate < 50:
                    print(f"   • Win rate below 50% - review entry criteria")
                
                if total_profit < -20:
                    print(f"   • Significant unrealized losses - consider risk management review")
                
                # Immediate action items
                print(f"\n🔧 IMMEDIATE ACTION ITEMS:")
                
                if total_profit > 20:
                    print(f"   1. Consider taking partial profits on winning positions")
                    print(f"   2. Implement trailing stops to protect gains")
                
                if worst_pair[1]['profit'] < -10:
                    print(f"   3. Review or consider closing {worst_pair[0]} position")
                
                print(f"   4. Continue monitoring {best_pair[0]} for additional opportunities")
                print(f"   5. Set clear profit targets and stop-loss levels")
                
                # Strategy recommendations
                print(f"\n📊 STRATEGY RECOMMENDATIONS:")
                print(f"   • Focus on pairs showing consistent profitability")
                print(f"   • Review entry timing for underperforming pairs")
                print(f"   • Consider position sizing based on pair performance")
                print(f"   • Implement systematic profit-taking rules")
                
        print(f"\n" + "=" * 60)
        print(f"📊 Analysis Complete!")
        print(f"💡 Focus on scaling what works and fixing what doesn't!")
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")

if __name__ == "__main__":
    analyze_current_positions() 