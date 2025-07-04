import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get bot token and admin ID from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID") # A nan za a yi amfani da shi nan gaba

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Define states for our FSM (Finite State Machine)
class AccountSubmission(StatesGroup):
    waiting_for_phone_number = State()
    waiting_for_otp = State()

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    """
    Wannan handler ne don umarnin /start.
    Zai gaishe da mai amfani kuma ya umarce shi ya tura lambar waya.
    """
    welcome_message = (
        "Barka da zuwa cibiyar karbar Telegram accounts! "
        "Don farawa, turo lambar wayar account din da kake son sayarwa "
        "(misali: +2348167757987). "
        "Tabbatar ka cire Two-Factor Authentication (2FA) kafin ka tura."
    )
    sent_message = await message.answer(welcome_message)
    # Pin the welcome message
    [span_0](start_span)await bot.pin_chat_message(chat_id=message.chat.id, message_id=sent_message.message_id)[span_0](end_span)

    [span_1](start_span)await message.answer("Bot zai tambayi lambar waya.")[span_1](end_span)
    await state.set_state(AccountSubmission.waiting_for_phone_number)

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    """
    Wannan handler ne don umarnin /cancel.
    Zai soke kowane aiki da mai amfani yake yi a halin yanzu.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Babu wani aiki da za a soke.")
        return

    await state.clear()
    [span_2](start_span)await message.answer("An soke aikin cikin nasara.")[span_2](end_span)

@dp.message(AccountSubmission.waiting_for_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext) -> None:
    """
    Wannan handler ne don karbar lambar waya daga mai amfani.
    """
    phone_number = message.text.strip()

    # Basic validation for phone number (can be enhanced later)
    if not phone_number.startswith('+') or not phone_number[1:].isdigit():
        await message.answer("Don Allah ka turo lambar waya mai inganci, wacce take farawa da '+' (misali: +2348167757987).")
        return

    # Store the phone number in FSM context
    await state.update_data(phone_number=phone_number)

    [span_3](start_span)await message.answer("Ana sarrafawa... Don Allah a jira.")[span_3](end_span)

    # Here, you would typically initiate the login process using Telethon
    # For now, we'll just simulate it and ask for OTP

    [span_4](start_span)await message.answer(f"An tura lambar sirri (OTP) zuwa lambar: {phone_number}. Don Allah ka tura lambar sirrin a nan.")[span_4](end_span)
    await state.set_state(AccountSubmission.waiting_for_otp)

@dp.message(AccountSubmission.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext) -> None:
    """
    Wannan handler ne don karbar OTP daga mai amfani.
    """
    otp_code = message.text.strip()
    data = await state.get_data()
    phone_number = data.get('phone_number')

    # Basic validation for OTP (can be enhanced later)
    if not otp_code.isdigit() or len(otp_code) < 4: # OTPs are usually 4-6 digits
        await message.answer("Don Allah ka tura lambar sirri (OTP) mai inganci.")
        return

    # Here, you would typically use Telethon to complete the login with OTP
    # For now, we'll just acknowledge and clear state
    await message.answer(f"An karbi OTP: {otp_code} don lambar: {phone_number}. Ana sarrafawa...")

    # Simulating successful login message
    await message.answer(
        "An shiga account din ku cikin nasara ku cire shi daga na'urar ku. "
        "Za a biya ku bisa ga adadin account din da kuka kawo. "
        "Ana biyan kudi daga karfe 8:00 na dare (WAT) zuwa gaba. "
        "Don Allah ka shirya tura bukatar biya."
    [span_5](start_span))

    # Clear the state after successful processing
    await state.clear()
    logging.info(f"Account for {phone_number} successfully processed (simulated).")


async def main() -> None:
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

