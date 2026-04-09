import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('trade_memory/portfolio.db')
cur = conn.cursor()

# Get current ETH price for notional calculation
eth_price_usd = 2260.0  # Approximate based on 0.001 ETH = ~$2.26

# New position: 0.001 ETH
positions = {
    "ETH": {
        "quantity": 0.001,
        "avg_entry_price": eth_price_usd,
        "entry_time": datetime.utcnow().isoformat(),
        "notional_usd": 0.001 * eth_price_usd
    }
}

# Update portfolio state: 0 cash, 0.001 ETH
cash_usd = 0.0
position_usd = 0.001 * eth_price_usd
unrealized_pnl = 0.0
realized_pnl = 0.0
total_assets = cash_usd + position_usd + unrealized_pnl
timestamp = datetime.utcnow().isoformat()

cur.execute('''
    INSERT INTO portfolio_state (timestamp, cash_usd, positions, unrealized_pnl, realized_pnl, total_assets)
    VALUES (?, ?, ?, ?, ?, ?)
''', (timestamp, cash_usd, json.dumps(positions), unrealized_pnl, realized_pnl, total_assets))

conn.commit()
print(f"Inserted new portfolio record")

# Verify
row = cur.execute('SELECT id, timestamp, cash_usd, positions FROM portfolio_state ORDER BY id DESC LIMIT 1').fetchone()
if row:
    id_, ts, cash, pos_json = row
    positions_dict = json.loads(pos_json)
    position_usd_calc = sum(p.get('notional_usd', 0) for p in positions_dict.values())
    print(f'\nUpdated portfolio (ID {id_}):')
    print(f'  Timestamp: {ts}')
    print(f'  Cash USD: ${cash:.2f}')
    print(f'  Positions: {json.dumps(positions_dict, indent=2)}')
    print(f'  Total Position USD (calculated): ${position_usd_calc:.2f}')
    print(f'  Total Assets: ${cash + position_usd_calc:.2f}')

conn.close()
