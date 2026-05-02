import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import Bot
import asyncio
from datetime import datetime, time
import pytz

TELEGRAM_TOKEN = '8488480027:AAFyTg91j9bqgHcRfEvBD9BQh5VifGYdNBI'
CHAT_ID = '7973906409'

SYMBOLS = ['BTC/USDT','ETH/USDT','SOL/USDT']
RISK_REWARD = 3.0
bot = Bot(token=TELEGRAM_TOKEN)
exchange = ccxt.binance()
utc = pytz.UTC
LONDON_OPEN, LONDON_CLOSE = time(13,0), time(16,0)
NY_OPEN, NY_CLOSE = time(17,0), time(20,0)

def is_kill_zone():
    now = datetime.now(utc).time()
    return (LONDON_OPEN <= now <= LONDON_CLOSE) or (NY_OPEN <= now <= NY_CLOSE)

def get_ohlcv(symbol, timeframe):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    return df

def check_4h_bos(df):
    df['hh'] = df['high'] > df['high'].shift(1)
    df['bos_bull'] = df['hh'] & (df['close'] > df['high'].shift(1))
    df['ll'] = df['low'] < df['low'].shift(1)
    df['bos_bear'] = df['ll'] & (df['close'] < df['low'].shift(1))
    if df['bos_bull'].iloc[-3:].any(): return 'Bullish'
    if df['bos_bear'].iloc[-3:].any(): return 'Bearish'
    return None

def find_fvg(df, bias):
    for i in range(len(df)-3, len(df)-1):
        if bias == 'Bullish' and df['low'].iloc[i] > df['high'].iloc[i-2]:
            return {'high': df['low'].iloc[i], 'low': df['high'].iloc[i-2]}
        if bias == 'Bearish' and df['high'].iloc[i] < df['low'].iloc[i-2]:
            return {'high': df['low'].iloc[i-2], 'low': df['high'].iloc[i]}
    return None

async def main():
    await bot.send_message(chat_id=CHAT_ID, text='🎯 **Sniper Bot Online**\n24/7 Free Version')
    last_signal = {}
    while True:
        if not is_kill_zone():
            await asyncio.sleep(60); continue
        for symbol in SYMBOLS:
            try:
                bias = check_4h_bos(get_ohlcv(symbol, '4h'))
                if not bias: continue
                fvg = find_fvg(get_ohlcv(symbol, '1h'), bias)
                if not fvg: continue
                df15m = get_ohlcv(symbol, '15m')
                in_fvg = (df15m['low'].iloc[-1] <= fvg['high']) and (df15m['high'].iloc[-1] >= fvg['low'])
                if in_fvg and last_signal.get(symbol)!= datetime.now(utc).date():
                    entry = df15m['close'].iloc[-1]
                    atr = ta.atr(df15m['high'], df15m['low'], df15m['close'], 14).iloc[-1]
                    if bias == 'Bullish':
                        sl = fvg['low'] - atr * 0.5
                        tp = entry + (entry - sl) * RISK_REWARD
                        signal = 'LONG 🟢'
                    else:
                        sl = fvg['high'] + atr * 0.5
                        tp = entry - (sl - entry) * RISK_REWARD
                        signal = 'SHORT 🔴'
                    msg = f"🎯 **{symbol} {signal}**\n\n**Entry**: `${entry:.2f}`\n**SL**: `${sl:.2f}`\n**TP**: `${tp:.2f}`\n**R:R**: 1:{RISK_REWARD}"
                    await bot.send_message(chat_id=CHAT_ID, text=msg)
                    last_signal[symbol] = datetime.now(utc).date()
            except Exception as e: print(f"Error {symbol}: {e}")
        await asyncio.sleep(60)

if __name__ == '__main__': asyncio.run(main())
