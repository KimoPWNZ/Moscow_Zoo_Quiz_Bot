import asyncio
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BufferedInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Необходимо указать токен Telegram бота в переменной окружения BOT_TOKEN.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

with open("quiz_data.json", "r", encoding="utf-8") as f:
    quiz_data = json.load(f)

user_answers = {}

def get_social_media_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Instagram", url="https://instagram.com/moscowzoo"),
        InlineKeyboardButton(text="ВКонтакте", url="https://vk.com/moscowzoo")
    )
    builder.row(
        InlineKeyboardButton(text="Facebook", url="https://facebook.com/moscowzoo"),
        InlineKeyboardButton(text="YouTube", url="https://youtube.com/moscowzoo")
    )
    return builder.as_markup()

def get_share_keyboard(result_animal: str):
    share_text = f"Моё тотемное животное Московского зоопарка — {result_animal}!\nПройди викторину и узнай своё тотемное животное!"
    encoded_text = quote(share_text)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Поделиться результатом",
            url=f"https://t.me/share/url?url={encoded_text}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Наши соцсети",
            callback_data="social_media"
        )
    )
    return builder.as_markup()

def get_restart_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Перезапустить викторину",
            callback_data="restart_quiz"
        )
    )
    return builder.as_markup()

def get_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Оставить отзыв")],
            [KeyboardButton(text="Связаться с поддержкой")],
            [KeyboardButton(text="Наши соцсети")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

@dp.callback_query(lambda c: c.data == "restart_quiz")
async def process_restart(callback_query: CallbackQuery):
    await callback_query.answer()
    await start_quiz(callback_query.message)

@dp.callback_query(lambda c: c.data == "social_media")
async def process_social_media(callback_query: CallbackQuery):
    await callback_query.answer()
    await show_social_media(callback_query.message)

@dp.message(Command("social"))
async def show_social_media(message: Message):
    await message.answer(
        "Подпишитесь на наши социальные сети:",
        reply_markup=get_social_media_keyboard()
    )

@dp.message(Command("start"))
async def start_quiz(message: Message):
    user_answers[message.chat.id] = []
    await message.answer(
        "Привет! Добро пожаловать в викторину Московского зоопарка. Давайте начнём!",
        reply_markup=ReplyKeyboardRemove()
    )
    await send_question(message.chat.id, 0)

async def send_question(chat_id, question_index):
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
    if message.text in ["Оставить отзыв", "Связаться с поддержкой", "Наши соцсети"]:
        if message.text == "Наши соцсети":
            await show_social_media(message)
        else:
            await handle_contact_request(message)
        return

    if chat_id in user_answers:
        user_answers[chat_id].append(message.text)
        question_index = len(user_answers[chat_id])
        await send_question(chat_id, question_index)

async def handle_contact_request(message: Message):
    if message.text == "Оставить отзыв":
        await message.answer(
            "Пожалуйста, напишите ваш отзыв о викторине. Мы ценим ваше мнение!",
            reply_markup=ReplyKeyboardRemove()
        )
    elif message.text == "Связаться с поддержкой":
        await message.answer(
            "По всем вопросам вы можете написать на почту support@moscowzoo.ru или позвонить по телефону +7 (XXX) XXX-XX-XX",
            reply_markup=ReplyKeyboardRemove()
        )

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
        image_extensions = ['.jpg', '.jpeg', '.png']
        image_sent = False

        for ext in image_extensions:
            image_path = f"images/{result_animal}{ext}"
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as file:
                        photo_data = file.read()

                    photo = BufferedInputFile(
                        file=photo_data,
                        filename=f"{result_animal}{ext}"
                    )

                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=f"Ваше тотемное животное — {result_animal}!\n\n{quiz_data['animals'][result_animal]['description']}",
                        reply_markup=get_share_keyboard(result_animal)
                    )
                    image_sent = True
                    break
                except Exception as e:
                    print(f"Ошибка при отправке изображения {image_path}: {str(e)}")

        if not image_sent:
            print(f"Изображение для {result_animal} не найдено или не может быть отправлено")
            await bot.send_message(
                chat_id,
                f"Ваше тотемное животное — {result_animal}!\n\n{quiz_data['animals'][result_animal]['description']}",
                reply_markup=get_share_keyboard(result_animal)
            )

        await bot.send_message(
            chat_id,
            "Если хотите оставить отзыв напишите в чат:\nОставить отзыв\n"
            "\n"
            "Для связи с поддержкой напишите в чат:\nСвязаться с поддержкой",
            reply_markup=get_restart_inline_keyboard()
        )
    else:
        await bot.send_message(
            chat_id,
            "Не удалось определить животное. Попробуйте ещё раз!",
            reply_markup=get_restart_inline_keyboard()
        )

@dp.message(Command("help"))
async def help_info(message: Message):
    await message.answer(
        "Программа опеки Московского зоопарка позволяет вам помочь животным, взяв их под опеку. "
        "Узнайте больше на официальном сайте Зоопарка!\n\n"
        "Сайт: https://www.moscowzoo.ru\n"
        "Программа опеки: https://www.moscowzoo.ru/my-zoo/become-a-guardian/\n\n"
        "Наши социальные сети: /social",
        reply_markup=get_restart_inline_keyboard()
    )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())