import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas_ta")

import requests
import time
import yfinance as yf
import patched_pandas_ta as ta  # ✅ Patched version
import pandas as pd

TOKEN = '8398180383:AAF3unmB3KQ_FIJFMDLdFIJqR_az1r8b2uE'

# ✅ Float data and ticker universe
float_data = {
    'AAPL': 15.8,
    'XENE': 18.2,
    'CELU': 22.5,
    'CRBP': 21.1
}
ticker_list = list(float_data.keys())

def get_updates(offset=None):
    url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
    if offset:
        url += f'?offset={offset}'
    return requests.get(url).json()

def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, data=payload)

def score_ticker(rsi, macd, roc):
    score = 0
    breakdown = []
    if rsi < 30:
        score += 30
        breakdown.append("RSI < 30 (+30)")
    if macd > 0:
        score += 40
        breakdown.append("MACD > 0 (+40)")
    if roc > 5:
        score += 30
        breakdown.append("ROC > 5 (+30)")
    return score, breakdown

def get_trend_bias(macd, roc):
    if macd > 0 and roc > 0:
        return "Bullish"
    elif macd > 0 or roc > 0:
        return "Neutral"
    else:
        return "Bearish"

def get_earnings_date(ticker):
    try:
        cal = yf.Ticker(ticker).calendar
        if not cal.empty:
            return str(cal.loc['Earnings Date'][0].date())
    except:
        pass
    return "N/A"

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period='6mo', interval='1d', auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.ta = ta  # ✅ Attach patched TA module to DataFrame

        if df.empty or 'Close' not in df.columns or df.dropna().shape[0] < 30:
            return None

        df.ta.rsi(close='Close', append=True)
        df.ta.macd(close='Close', append=True)
        df.ta.roc(close='Close', append=True)

        required_cols = ['RSI_14', 'MACD_12_26_9', 'ROC_10']
        if not all(col in df.columns for col in required_cols):
            return None

        df = df.dropna(subset=required_cols)
        if df.empty:
            return None

        latest = df.iloc[-1]

        rsi = latest['RSI_14']
        macd = latest['MACD_12_26_9']
        roc = latest['ROC_10']
        float_value = float_data.get(ticker.upper(), 'N/A')
        score, breakdown = score_ticker(rsi, macd, roc)
        trend = get_trend_bias(macd, roc)
        earnings = get_earnings_date(ticker)

        return {
            'RSI': round(rsi, 2),
            'MACD': round(macd, 2),
            'ROC': round(roc, 2),
            'Float': float_value,
            'Score': score,
            'Breakdown': breakdown,
            'Trend': trend,
            'Earnings': earnings,
            'Raw': {'RSI': rsi, 'MACD': macd, 'ROC': roc}
        }
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def format_ticker_analysis(ticker, data):
    if data is None:
        return f"⚠️ Unable to analyze ${ticker}. Data not available or ticker invalid."

    breakdown_text = "\n".join([f"   - {b}" for b in data['Breakdown']]) if data['Breakdown'] else "   - No triggers met"

    return (
        f"📊 ${ticker} Tactical Snapshot:\n"
        f"• RSI: {data['RSI']}\n"
        f"• MACD: {data['MACD']}\n"
        f"• ROC: {data['ROC']}%\n"
        f"• Float: {data['Float']}M\n"
        f"• Score: {data['Score']}\n"
        f"• Trend Bias: {data['Trend']}\n"
        f"• Earnings Date: {data['Earnings']}\n"
        f"• Scoring Breakdown:\n{breakdown_text}"
    )

def format_debug(ticker, data):
    if data is None:
        return f"⚠️ Unable to debug ${ticker}. No data available."
    raw = data['Raw']
    return (
        f"🛠️ Debug for ${ticker}:\n"
        f"• Raw RSI_14: {raw['RSI']}\n"
        f"• Raw MACD_12_26_9: {raw['MACD']}\n"
        f"• Raw ROC_10: {raw['ROC']}"
    )

def handle_top_command(chat_id):
    results = []
    for t in ticker_list:
        data = analyze_ticker(t)
        if data:
            results.append((t, data['Score']))
    if not results:
        send_message(chat_id, "⚠️ No valid tickers found.")
        return
    top = sorted(results, key=lambda x: x[1], reverse=True)[:3]
    reply = "🏆 Top Scoring Tickers:\n" + "\n".join([f"• ${t}: {s}" for t, s in top])
    send_message(chat_id, reply)

def handle_float_command(chat_id, max_float):
    filtered = [t for t in ticker_list if float_data.get(t, 999) <= max_float]
    if not filtered:
        send_message(chat_id, f"⚠️ No tickers with float ≤ {max_float}M.")
        return
    reply = f"📉 Tickers with float ≤ {max_float}M:\n" + "\n".join([f"• ${t}: {float_data[t]}M" for t in filtered])
    send_message(chat_id, reply)

def handle_ping_command(chat_id):
    send_message(chat_id, "✅ Bot is alive and listening.")

# ✅ Listener loop with command parsing
last_update_id = None

while True:
    updates = get_updates(last_update_id)
    if updates['result']:
        for update in updates['result']:
            last_update_id = update['update_id'] + 1

            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            message_text = message.get('text', '').strip().upper()

            print(f"📩 Received: {message_text} from chat {chat_id}")

            if message_text.startswith('$'):
                ticker = message_text[1:]
                indicators = analyze_ticker(ticker)
                reply = format_ticker_analysis(ticker, indicators)
                send_message(chat_id, reply)

            elif message_text.startswith('/DEBUG'):
                parts = message_text.split()
                if len(parts) == 2 and parts[1].startswith('$'):
                    ticker = parts[1][1:]
                    indicators = analyze_ticker(ticker)
                    reply = format_debug(ticker, indicators)
                    send_message(chat_id, reply)

            elif message_text.startswith('/TOP'):
                handle_top_command(chat_id)

            elif message_text.startswith('/FLOAT'):
                parts = message_text.split()
                if len(parts) == 2 and parts[1].isdigit():
                    max_float = float(parts[1])
                    handle_float_command(chat_id, max_float)

            elif message_text.startswith('/PING'):
                handle_ping_command(chat_id)

    time.sleep(2)
