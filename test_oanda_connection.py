#!/usr/bin/env python3
"""
🔍 Test OANDA Connection and Account Details
Quick test of OANDA API connectivity and account status
"""

import os
import requests
from datetime import datetime, timedelta, timezone
import json

def test_oanda_connection():
    """Test OANDA API connection and get account details."""
    
    # Get credentials from environment
    api_key = os.getenv('OANDA_API_KEY')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    
    if not api_key or not account_id:
        print("❌ OANDA credentials not found in environment variables")
        return
    
    print(f"🔗 Testing OANDA connection...")
    print(f"   Account ID: {account_id}")
    print(f"   API Key: {api_key[:20]}...")
    
    # OANDA API setup
    base_url = "https://api-fxpractice.oanda.com"  # Practice API
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # 1. Test account details
        print("\n📊 Fetching account details...")
        account_url = f"{base_url}/v3/accounts/{account_id}"
        response = requests.get(account_url, headers=headers)
        
        if response.status_code == 200:
            account_data = response.json()
            account = account_data.get('account', {})
            
            print("✅ Account Details:")
            print(f"   Balance: ${float(account.get('balance', 0)):,.2f}")
            print(f"   NAV: ${float(account.get('nav', 0)):,.2f}")
            print(f"   Unrealized P&L: ${float(account.get('unrealizedPL', 0)):,.2f}")
            print(f"   Open Trade Count: {account.get('openTradeCount', 0)}")
            print(f"   Open Position Count: {account.get('openPositionCount', 0)}")
            print(f"   Currency: {account.get('currency', 'USD')}")
            print(f"   Margin Used: ${float(account.get('marginUsed', 0)):,.2f}")
            print(f"   Margin Available: ${float(account.get('marginAvailable', 0)):,.2f}")
        else:
            print(f"❌ Account details error: {response.status_code} - {response.text}")
            return
        
        # 2. Test historical transactions (extend timeframe)
        print("\n📈 Fetching transaction history (past 30 days)...")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)  # Extend to 30 days
        
        transactions_url = f"{base_url}/v3/accounts/{account_id}/transactions"
        params = {
            'from': start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'to': end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'pageSize': 100
        }
        
        response = requests.get(transactions_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transactions', [])
            
            print(f"✅ Found {len(transactions)} transactions")
            
            # Categorize transactions
            transaction_types = {}
            for tx in transactions:
                tx_type = tx.get('type', 'UNKNOWN')
                transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
            
            print("📋 Transaction Types:")
            for tx_type, count in transaction_types.items():
                print(f"   {tx_type}: {count}")
            
            # Show recent trades
            trade_transactions = [tx for tx in transactions if tx.get('type') in ['MARKET_ORDER', 'ORDER_FILL', 'TRADE_OPEN', 'TRADE_CLOSE']]
            
            if trade_transactions:
                print(f"\n🔥 Recent Trading Activity ({len(trade_transactions)} trades):")
                for i, trade in enumerate(trade_transactions[-5:]):  # Show last 5 trades
                    print(f"   {i+1}. {trade.get('time', '')[:16]} | {trade.get('type', '')} | {trade.get('instrument', '')} | ${trade.get('pl', 0)}")
            else:
                print("\n💤 No trading activity found")
                
        else:
            print(f"❌ Transaction history error: {response.status_code} - {response.text}")
        
        # 3. Test current positions
        print("\n📍 Checking current positions...")
        positions_url = f"{base_url}/v3/accounts/{account_id}/positions"
        
        response = requests.get(positions_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            positions = data.get('positions', [])
            open_positions = [pos for pos in positions if float(pos.get('long', {}).get('units', 0)) != 0 or float(pos.get('short', {}).get('units', 0)) != 0]
            
            print(f"✅ Found {len(open_positions)} open positions")
            
            for pos in open_positions:
                instrument = pos.get('instrument', '')
                long_units = float(pos.get('long', {}).get('units', 0))
                short_units = float(pos.get('short', {}).get('units', 0))
                unrealized_pl = float(pos.get('unrealizedPL', 0))
                
                if long_units > 0:
                    print(f"   📈 {instrument}: LONG {long_units:,.0f} units | P&L: ${unrealized_pl:.2f}")
                elif short_units < 0:
                    print(f"   📉 {instrument}: SHORT {abs(short_units):,.0f} units | P&L: ${unrealized_pl:.2f}")
        else:
            print(f"❌ Positions error: {response.status_code} - {response.text}")
        
        # 4. Test current prices for major pairs
        print("\n💱 Current market prices:")
        major_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD']
        
        for pair in major_pairs:
            pricing_url = f"{base_url}/v3/accounts/{account_id}/pricing"
            params = {'instruments': pair}
            
            response = requests.get(pricing_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                
                if prices:
                    price_data = prices[0]
                    bid = float(price_data.get('bids', [{}])[0].get('price', 0))
                    ask = float(price_data.get('asks', [{}])[0].get('price', 0))
                    spread = (ask - bid) * (10000 if 'JPY' not in pair else 100)
                    
                    print(f"   {pair.replace('_', '/')}: {bid:.5f} / {ask:.5f} (Spread: {spread:.1f} pips)")
        
        print(f"\n✅ OANDA Connection Test Complete!")
        print(f"🎯 Your account is {'ACTIVE' if len(transactions) > 0 else 'INACTIVE'}")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")

if __name__ == "__main__":
    test_oanda_connection() 