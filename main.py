import logging, json, ccxt, pandas as pd
from ta.momentum import RSIIndicator
from aiogram import Bot, Dispatcher, executor, types, F # Ƙara F idan har yanzu kana amfani da aiogram 3.x
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from datetime import datetime
from config import API_TOKEN, CHANNEL_ID

# Konfigaration na Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Da fatan za a zaɓi musayar da ta dace da kai. Binance, Bybit, KuCoin, da sauransu.
# Kuna iya buƙatar API key da secret idan zaku fara ciniki na gaske ko kuma download manyan data.
exchange = ccxt.binance({
    'enableRateLimit': True, # Yana taimakawa hana keta iyakar API requests
})
pairs_to_check = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
DB_FILE = "db.json" # Wannan baya amfani a code din yanzu, amma za'a iya amfani dashi
ALERTS_FILE = "alerts.json"

def load_json(file):
    try: return json.load(open(file, "r"))
    except FileNotFoundError: return {} # Gyara: Idan fayil babu, mayar da fanko {}
    except json.JSONDecodeError:
        logging.error(f"Kuskure yayin karanta JSON daga {file}. An mayar da fanko.")
        return {}


def save_json(data, file):
    with open(file, "w") as f: json.dump(data, f, indent=2)

def fetch_signal(pair):
    try:
        # Dauko Candles na awa 1 guda 100
        candles = exchange.fetch_ohlcv(pair, '1h', limit=100)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Lissafa RSI
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()

        # --- Aiwatar da dabarun gano Support da Resistance (mataki na farko) ---
        # Wannan shine wani saukin tsarin gano 'pivot points' a matsayin S&R.
        # Don cikakken aiwatar da littafin PDF din, zaka buƙaci algorithms masu rikitarwa
        # kamar su gano 'multiple rejections', 'obvious levels', da 'zones'.

        # Gano Swing High (pivot high)
        # Babban mataki ne idan ya fi na baya da na gaba (misali, 2 candles baya da 2 candles gaba)
        df['is_swing_high'] = (df['high'] > df['high'].shift(1)) & \
                              (df['high'] > df['high'].shift(2)) & \
                              (df['high'] > df['high'].shift(-1)) & \
                              (df['high'] > df['high'].shift(-2))

        # Gano Swing Low (pivot low)
        # Ƙasƙanci ne idan ya fi na baya da na gaba (misali, 2 candles baya da 2 candles gaba)
        df['is_swing_low'] = (df['low'] < df['low'].shift(1)) & \
                             (df['low'] < df['low'].shift(2)) & \
                             (df['low'] < df['low'].shift(-1)) & \
                             (df['low'] < df['low'].shift(-2))

        # Dauko sabbin bayanan
        current_close = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]

        # Neman sabbin swing high/low points
        recent_swing_high_points = df[df['is_swing_high']].tail(3)['high'].tolist()
        recent_swing_low_points = df[df['is_swing_low']].tail(3)['low'].tolist()

        # Idan ba a samu swing high/low ba, yi amfani da min/max na kwanan nan
        swing_high = max(recent_swing_high_points) if recent_swing_high_points else df['high'].iloc[-10:-1].max()
        swing_low = min(recent_swing_low_points) if recent_swing_low_points else df['low'].iloc[-10:-1].min()

        # --- Dabarun Sigina (wanda aka gyara kaɗan) ---
        # Wannan dabarar har yanzu tana da sauƙi kuma tana buƙatar ƙarin gwaji.
        # Zaka iya ƙara hadadden dokoki bisa ga Support, Resistance, da Trendlines daga littafin.
        # Misali: "BUY idan farashi ya dawo zuwa matakin tallafi bayan ya yi sama, kuma RSI ya nuna over-sold".

        # Yana duba ko farashin yanzu ya kusa da swing high/low don yanke shawara
        # Zaka iya gyara waɗannan sharuɗɗa gwargwadon dabarunka.
        if current_close > swing_high and current_rsi > 60: # Overbought, yana iya ci gaba da hawa
            entry = current_close
            # Misali lissafin TP/SL dangane da S&R da kasuwar yanzu
            tp = round(entry * 1.02, 2) # Misali 2% profit
            sl = round(swing_high * 0.99, 2) # Kasa da swing high kadan
            return {
                "type": "BUY", "pair": pair, "entry": round(entry, 2),
                "sl": sl, "tp": tp, "rsi": round(current_rsi, 2)
            }
        elif current_close < swing_low and current_rsi < 40: # Oversold, yana iya ci gaba da sauka
            entry = current_close
            tp = round(entry * 0.98, 2) # Misali 2% profit
            sl = round(swing_low * 1.01, 2) # Sama da swing low kadan
            return {
                "type": "SELL", "pair": pair, "entry": round(entry, 2),
                "sl": sl, "tp": tp, "rsi": round(current_rsi, 2)
            }
        return None
    except Exception as e:
        logging.error(f"⚠️ Error fetching signal for {pair}: {e}", exc_info=True)
        return None

async def send_best_signal():
    logging.info("Ana duba sigina...")
    alerts = load_json(ALERTS_FILE)
    all_signals = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    for pair in pairs_to_check:
        signal = fetch_signal(pair)
        if signal:
            text = (
                f"{'🟢' if signal['type']=='BUY' else '🔴'} *{signal['type']} Signal* ({signal['pair']})\n"
                f"🕒 {now}\n"
                f"💰 Entry: `${signal['entry']}`\n"
                f"🎯 TP: `${signal['tp']}`\n"
                f"🛡 SL: `${signal['sl']}`\n"
                f"📊 RSI: `{signal['rsi']}`"
            )
            all_signals.append(text)

            # store for /myalerts
            key = signal['pair']
            alerts.setdefault(key, []).append({
                "time": now,
                "type": signal['type'],
                "entry": signal['entry'],
                "tp": signal['tp'],
                "sl": signal['sl'],
                "rsi": signal['rsi']
            })
            # limit to last 5
            alerts[key] = alerts[key][-5:]

    if all_signals:
        final_msg = "📢 *Crypto Signal Alert*\n\n" + "\n\n".join(all_signals)
        try:
            await bot.send_message(CHANNEL_ID, final_msg, parse_mode="Markdown")
            logging.info(f"An aika sigina {len(all_signals)} zuwa channel {CHANNEL_ID}.")
        except Exception as e:
            logging.error(f"Kuskure yayin aika sako zuwa Telegram: {e}", exc_info=True)
    else:
        logging.info("Babu sabbin sigina da aka samu yanzu.")

    save_json(alerts, ALERTS_FILE)

# --- Sabon Aiki na Backtesting (Conceptual - Ba Cikakken Aiwatarwa Ba) ---
async def backtest_strategy(pair, timeframe='1h', start_date=None, end_date=None):
    logging.info(f"Ana fara backtesting na {pair}...")
    # Mataki 1: Dauko Bayanan Tarihi mai Yawa
    # Zaka buƙaci zaɓin yadda zaka dawo da manyan data na tarihi
    # exchange.fetch_ohlcv yana da iyakacin adadin data. Zaka iya amfani da looping ko wata hanyar.
    # Misali: candles = exchange.fetch_ohlcv(pair, timeframe, since=start_date_timestamp, limit=some_large_number)
    
    # Don gwaji, bari mu yi amfani da ƙananan data na ƙarshe
    try:
        # A nan za ka canza limit zuwa dubbai ko miliyoyi don cikakken backtesting
        candles = exchange.fetch_ohlcv(pair, timeframe, limit=500) 
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
    except Exception as e:
        logging.error(f"Kuskure yayin dauko bayanan tarihi don backtesting: {e}", exc_info=True)
        return

    # Mataki 2: Aiwatar da Dabarun a kan Bayanan Tarihi
    # Zaka buƙaci rubuta sigar dabarunka (kamar fetch_signal) wanda zai iya gudana akan kowane layi na DataFrame.
    # Wannan zai haɗa da:
    # - Lissafin RSI da gano S&R points ga kowane lokaci a cikin tarihin
    # - Shigar da ciniki idan sharuɗɗan sun cika
    # - Rufe ciniki idan SL/TP ya cika ko kuma wasu sharuɗɗan fita

    trades = [] # Zai adana cikakkun bayanai game da kowane ciniki

    # Wannan misali ne kawai na yadda zaka iya juyawa ta kowane bar
    for i in range(len(df)):
        current_slice = df.iloc[:i+1] # Yana simulating yadda bayanan ke zuwa a lokacin gaske
        if len(current_slice) < 100: # Tabbatar cewa akwai isasshen data don lissafin indicators
            continue
        
        # A nan za ka kira aikin dabarunka wanda aka tsara don backtesting.
        # Wannan zai zama ingantaccen sigar 'fetch_signal' amma yana aiki akan 'current_slice'
        # ba tare da kiran API ba a kowane lokaci.
        
        # Misali: signal = your_backtest_strategy_logic(current_slice)
        # Idan signal ta dawo, yi rijistar cinikin.
        
        # Wannan sashen yana buƙatar cikakken aiwatarwa don zama aiki.
        pass

    # Mataki 3: Nazarin Sakamakon Backtesting
    # Da zarar an gama juyawa ta duk bayanan, zaka lissafta:
    # - Jimlar riba/asara
    # - Adadin cinikai masu nasara/gazawa
    # - Win rate
    # - Mafi girman Drawdown
    # - Da sauran metrics masu muhimmanci

    logging.info(f"An gama backtesting na {pair}. Sakamakon zai bayyana a nan...")
    # A nan zaka iya buga sakamakon ko ajiye su zuwa fayil.

# --- Telegram Handlers ---
@dp.message_handler(commands=["myalerts"])
async def handle_alerts(message: types.Message):
    alerts = load_json(ALERTS_FILE)
    text = ""
    if not alerts:
        text = "🚫 Babu alerts tukuna."
    else:
        for pair, signals in alerts.items():
            text += f"*{pair} Alerts:*\n"
            for s in signals:
                text += (
                    f"{'🟢' if s['type']=='BUY' else '🔴'} *{s['type']}* @ `{s['time']}`\n"
                    f"💰 Entry: {s['entry']} | 🎯 TP: {s['tp']} | 🛡 SL: {s['sl']} | RSI: {s['rsi']}\n\n"
                )
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply("🤖 Bot ɗin crypto signal ya kunna!\nZa a dinga turawa sakonni kai tsaye a channel.\nZa ka iya amfani da /myalerts don duba sakonni na baya.")

# --- Scheduler ---
scheduler = AsyncIOScheduler(timezone="Africa/Lagos") # Tabbatar da Timezone dinka
scheduler.add_job(send_best_signal, 'cron', hour='9', minute='0') # Gyara hour da minute zuwa string
scheduler.add_job(send_best_signal, 'cron', hour='19', minute='0')
scheduler.start()

if __name__ == "__main__":
    logging.info("Bot yana farawa...")
    executor.start_polling(dp, skip_updates=True)

