import logging
import asyncio
import random
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.token import TokenValidationError
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# ====== CONFIG ======
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
POST_INTERVAL_HOURS = 4

PAIRS = ['DOGE/USDT', 'BCH/USDT', 'ETH/USDT', 'ARB/USDT', 'OP/USDT']
LEVERAGE_OPTIONS = [10, 15, 20]

# ====== BOT SETUP ======
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# ====== SEND SIGNAL ======
async def send_trade_signal():
    pair = random.choice(PAIRS)
    direction = random.choice(['LONG', 'SHORT'])
    leverage = random.choice(LEVERAGE_OPTIONS)

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
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)

# ====== TASK LOOP ======
async def signal_loop():
    while True:
        await send_trade_signal()
        await asyncio.sleep(POST_INTERVAL_HOURS * 3600)

# ====== /start handler ======
@dp.message(commands=["start"])
async def start_handler(message: Message):
    await message.answer("🤖 BashTrading Bot is active and ready to send signals!")

# ====== MAIN ======
async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, polling_timeout=60, handle_signals=True, close_bot_session=True, shutdown_polling=True, on_startup=signal_loop())
    except TokenValidationError:
        print("❌ BOT_TOKEN is invalid. Please check your .env file.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
