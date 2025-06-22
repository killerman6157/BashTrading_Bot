import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from datetime import datetime

# ====== CONFIG ======
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Replace with @BashTrading_Bot token
GROUP_CHAT_ID = -1001234567890      # Replace with your signal group ID
POST_INTERVAL_HOURS = 4            # Every 4 hours (2x/day approx)

# Signal Template Settings
PAIRS = ['DOGE/USDT', 'BCH/USDT', 'ETH/USDT', 'ARB/USDT', 'OP/USDT']
LEVERAGE_OPTIONS = [10, 15, 20]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# ====== CORE FUNCTION ======
async def send_trade_signal():
    pair = random.choice(PAIRS)
    direction = random.choice(['LONG', 'SHORT'])
    leverage = random.choice(LEVERAGE_OPTIONS)

    # Fake signal numbers (replace with real API logic later)
    entry = round(random.uniform(0.1, 100), 3)
    tp = round(entry * (1.05 if direction == 'LONG' else 0.95), 3)
    sl = round(entry * (0.97 if direction == 'LONG' else 1.03), 3)

    message = f"""
📊 <b>Sabon Signal</b>

🔹 <b>Pair:</b> {pair}
📈 <b>Direction:</b> {direction}
🎯 <b>Entry:</b> ${entry}
🎯 <b>TP:</b> ${tp}
🛑 <b>SL:</b> ${sl}
💥 <b>Leverage:</b> {leverage}x (Isolated)
🕒 <i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>
    """

    await bot.send_message(GROUP_CHAT_ID, message, parse_mode=ParseMode.HTML)

# ====== AUTO POST LOOP ======
async def scheduler():
    while True:
        await send_trade_signal()
        await asyncio.sleep(POST_INTERVAL_HOURS * 3600)

@dp.message_handler(commands=['start'])
async def start_cmd(msg: types.Message):
    await msg.reply("🤖 BashTrading Bot ready! You will receive 2x signals daily.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())
    executor.start_polling(dp, skip_updates=True)
