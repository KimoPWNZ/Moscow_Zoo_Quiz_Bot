import asyncio
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Необходимо указать токен Telegram бота в переменной окружения BOT_TOKEN.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

with open("quiz_data.json", "r", encoding="utf-8") as f:
    quiz_data = json.load(f)

user_answers = {}


@dp.message(Command("start"))
async def start_quiz(message: Message):
    """Обработчик команды /start. Начинает викторину."""
    user_answers[message.chat.id] = []
    await message.answer("Привет! Добро пожаловать в викторину Московского зоопарка. Давайте начнём!")
    await send_question(message.chat.id, 0)


async def send_question(chat_id, question_index):
    """Отправляет вопрос пользователю."""
    if question_index < len(quiz_data["questions"]):
        question = quiz_data["questions"][question_index]
        answers_markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=answer)] for answer in question["answers"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await bot.send_message(chat_id, question["text"], reply_markup=answers_markup)
    else:
        await calculate_result(chat_id)


@dp.message()
async def handle_answer(message: Message):
    chat_id = message.chat.id
    if chat_id in user_answers:
        user_answers[chat_id].append(message.text)
        question_index = len(user_answers[chat_id])
        await send_question(chat_id, question_index)

async def calculate_result(chat_id):
    answers = user_answers.get(chat_id, [])
    max_match = 0
    result_animal = None

    for animal, data in quiz_data["animals"].items():
        match_count = sum(1 for answer in answers if answer in data["answers"])
        if match_count > max_match:
            max_match = match_count
            result_animal = animal

    if result_animal:
        image_path = f"images/{result_animal}.jpg"
        if os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                await bot.send_photo(chat_id, photo, caption=f"Ваше тотемное животное — {result_animal}!\n\n{quiz_data['animals'][result_animal]['description']}")
        else:
            await bot.send_message(chat_id, f"Ваше тотемное животное — {result_animal}!\n\n{quiz_data['animals'][result_animal]['description']}")
        await bot.send_message(chat_id, "Хотите узнать больше о программе опеки? Нажмите /help")
    else:
        await bot.send_message(chat_id, "Не удалось определить животное. Попробуйте ещё раз! /start")


@dp.message(Command("help"))
async def help_info(message: Message):
    await message.answer("Программа опеки Московского зоопарка позволяет вам помочь животным, взяв их под опеку. Узнайте больше на официальном сайте Зоопарка!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())