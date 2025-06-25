#!/usr/bin/env python3
"""
🎯 Quick Trading Analysis
Focused analysis of current OANDA positions and trading patterns
Provides actionable insights on what's working vs what's not
"""

import os
import requests
from datetime import datetime, timedelta, timezone
import json
from collections import defaultdict

def analyze_current_trading_performance():
    """Quick analysis of current trading performance."""
    
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
    
    print("🎯 QUICK TRADING PERFORMANCE ANALYSIS")
    print("=" * 50)
    
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
        nav = float(account.get('nav', 0))
        unrealized_pl = float(account.get('unrealizedPL', 0))
        open_trade_count = account.get('openTradeCount', 0)
        margin_used = float(account.get('marginUsed', 0))
        margin_available = float(account.get('marginAvailable', 0))
        
        print(f"💰 ACCOUNT OVERVIEW:")
        print(f"   Balance: ${balance:,.2f}")
        print(f"   Current P&L: ${unrealized_pl:,.2f}")
        print(f"   Open Trades: {open_trade_count}")
        print(f"   Margin Utilization: {(margin_used / (margin_used + margin_available)) * 100:.1f}%")
        
        # 2. Analyze current positions
        print(f"\n📊 CURRENT POSITION ANALYSIS:")
        
        positions_url = f"{base_url}/v3/accounts/{account_id}/openTrades"
        response = requests.get(positions_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            trades = data.get('trades', [])
            
            if not trades:
                print("   No open trades found")
                return
            
            # Analyze each position
            total_profit = 0
            profitable_trades = 0
            losing_trades = 0
            pair_performance = defaultdict(lambda: {'count': 0, 'profit': 0, 'direction': []})
            
            print(f"\n🔍 INDIVIDUAL POSITION BREAKDOWN:")
            
            for i, trade in enumerate(trades, 1):
                instrument = trade.get('instrument', '')
                pair = instrument.replace('_', '/')
                units = float(trade.get('currentUnits', 0))
                open_price = float(trade.get('price', 0))
                unrealized_pl = float(trade.get('unrealizedPL', 0))
                open_time = trade.get('openTime', '')
                
                # Calculate position details
                direction = 'LONG' if units > 0 else 'SHORT'
                position_size = abs(units)
                
                # Calculate how long position has been open
                if open_time:
                    open_dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
                    duration = datetime.now(timezone.utc) - open_dt
                    days_open = duration.days
                    hours_open = duration.total_seconds() / 3600
                else:
                    days_open = 0
                    hours_open = 0
                
                # Status indicators
                status = "🟢 WINNING" if unrealized_pl > 0 else "🔴 LOSING" if unrealized_pl < 0 else "⚪ BREAKEVEN"
                
                print(f"\n   {i}. {status} - {pair} {direction}")
                print(f"      Position Size: {position_size:,.0f} units")
                print(f"      Entry Price: {open_price:.5f}")
                print(f"      Current P&L: ${unrealized_pl:.2f}")
                print(f"      Duration: {days_open} days ({hours_open:.1f} hours)")
                
                # Track performance metrics
                total_profit += unrealized_pl
                if unrealized_pl > 0:
                    profitable_trades += 1
                else:
                    losing_trades += 1
                
                # Track by pair
                pair_performance[pair]['count'] += 1
                pair_performance[pair]['profit'] += unrealized_pl
                pair_performance[pair]['direction'].append(direction)
            
            # 3. Performance Summary
            print(f"\n📈 PERFORMANCE SUMMARY:")
            win_rate = (profitable_trades / len(trades)) * 100 if trades else 0
            print(f"   Current Win Rate: {win_rate:.1f}% ({profitable_trades}/{len(trades)})")
            print(f"   Total Unrealized P&L: ${total_profit:.2f}")
            print(f"   Average P&L per Trade: ${total_profit / len(trades):.2f}")
            
            # 4. Pair Analysis
            print(f"\n💱 CURRENCY PAIR PERFORMANCE:")
            for pair, stats in pair_performance.items():
                avg_profit = stats['profit'] / stats['count']
                directions = ', '.join(set(stats['direction']))
                status = "✅" if stats['profit'] > 0 else "❌"
                
                print(f"   {status} {pair}: ${stats['profit']:.2f} ({stats['count']} trades, {directions})")
                print(f"      Average per trade: ${avg_profit:.2f}")
            
            # 5. Risk Analysis
            print(f"\n⚖️ RISK ANALYSIS:")
            total_risk = (margin_used / balance) * 100 if balance > 0 else 0
            print(f"   Portfolio Risk: {total_risk:.1f}% of account")
            
            risk_per_trade = total_risk / len(trades) if trades else 0
            print(f"   Average Risk per Trade: {risk_per_trade:.1f}%")
            
            if total_risk > 10:
                print(f"   ⚠️ HIGH RISK: Consider reducing position sizes")
            elif total_risk < 2:
                print(f"   ⚠️ LOW RISK: Consider increasing position sizes for better returns")
            else:
                print(f"   ✅ MODERATE RISK: Risk level appears appropriate")
            
            # 6. Actionable Insights
            print(f"\n🎯 ACTIONABLE INSIGHTS:")
            
            # Best performing pairs
            best_pair = max(pair_performance.items(), key=lambda x: x[1]['profit'])
            worst_pair = min(pair_performance.items(), key=lambda x: x[1]['profit'])
            
            print(f"\n✅ WHAT'S WORKING:")
            if best_pair[1]['profit'] > 0:
                print(f"   • {best_pair[0]} is your best performer (${best_pair[1]['profit']:.2f})")
                print(f"   • Continue monitoring {best_pair[0]} for similar setups")
            
            if profitable_trades > losing_trades:
                print(f"   • Current strategy has {win_rate:.0f}% win rate - above average!")
                print(f"   • Position sizing and risk management appear effective")
            
            print(f"\n❌ WHAT NEEDS ATTENTION:")
            if worst_pair[1]['profit'] < -5:
                print(f"   • {worst_pair[0]} is underperforming (${worst_pair[1]['profit']:.2f})")
                print(f"   • Consider reviewing {worst_pair[0]} strategy or cutting losses")
            
            if losing_trades > profitable_trades:
                print(f"   • More losing than winning trades currently")
                print(f"   • Review entry criteria and timing")
            
            # Duration analysis
            long_trades = [t for t in trades if (datetime.now(timezone.utc) - datetime.fromisoformat(t.get('openTime', '').replace('Z', '+00:00'))).days > 7]
            if long_trades:
                print(f"   • {len(long_trades)} trades open for >7 days - consider exit strategy")
            
            print(f"\n🔧 IMMEDIATE RECOMMENDATIONS:")
            
            if total_profit > 0:
                print(f"   1. Consider taking partial profits on winning trades")
                print(f"   2. Trail stop losses to protect gains")
            
            if total_profit < -50:
                print(f"   1. Review risk management - losses exceeding comfort zone")
                print(f"   2. Consider reducing position sizes")
            
            print(f"   3. Monitor {best_pair[0]} for additional opportunities")
            print(f"   4. Review and potentially close {worst_pair[0]} position")
            print(f"   5. Set daily/weekly P&L targets and stick to them")
            
            # 7. Market Context
            print(f"\n📊 CURRENT MARKET CONTEXT:")
            
            # Get current prices for context
            major_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
            print(f"   Current Market Prices:")
            
            for pair in major_pairs:
                pricing_url = f"{base_url}/v3/accounts/{account_id}/pricing"
                params = {'instruments': pair}
                
                try:
                    response = requests.get(pricing_url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        prices = data.get('prices', [])
                        
                        if prices:
                            price_data = prices[0]
                            bid = float(price_data.get('bids', [{}])[0].get('price', 0))
                            ask = float(price_data.get('asks', [{}])[0].get('price', 0))
                            mid = (bid + ask) / 2
                            spread = (ask - bid) * (10000 if 'JPY' not in pair else 100)
                            
                            print(f"      {pair.replace('_', '/')}: {mid:.5f} (Spread: {spread:.1f} pips)")
                except:
                    continue
        
        print(f"\n" + "=" * 50)
        print(f"📊 Analysis Complete - Review insights above")
        print(f"💡 Focus on what's working and minimize what's not!")
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")

if __name__ == "__main__":
    analyze_current_trading_performance() 