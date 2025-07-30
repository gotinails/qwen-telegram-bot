import logging
import requests
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === Настройки ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
MODEL_NAME = "gpt2"  # Быстрая и всегда доступная модель
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

# Заголовки для запроса
headers = {"Authorization": f"Bearer {HF_API_KEY}"}

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция для получения ответа от модели
async def get_hf_response(prompt: str) -> str:
    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 256,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

        logger.info(f"HF Status: {response.status_code}, Response: {response.text[:200]}...")

        if response.status_code == 200:
            try:
                output = response.json()
                if isinstance(output, list):
                    return output[0]['generated_text'].strip()
                elif isinstance(output, dict):
                    if 'generated_text' in output:
                        return output['generated_text'].strip()
                    elif 'error' in output:
                        return f"❌ {output['error']}"
                    else:
                        return "Не удалось получить ответ."
                else:
                    return "Ошибка: неожиданный формат данных."
            except Exception:
                return "Ошибка: не удалось обработать ответ."
        elif response.status_code == 503:
            return "⏳ Модель загружается, попробуй позже."
        elif response.status_code == 429:
            return "🚫 Слишком много запросов. Попробуй позже."
        elif response.status_code == 401:
            return "🔑 Ошибка авторизации. Проверьте HF_API_KEY."
        else:
            return f"❌ Ошибка {response.status_code}: {response.text}"
    except Exception as e:
        return f"🌐 Ошибка подключения: {str(e)}"

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    username = update.message.from_user.username or update.message.from_user.first_name
    logger.info(f"Сообщение от @{username} ({chat_id}): {user_message}")

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Простой промпт
    full_prompt = (
        "Ты — дружелюбный помощник. Отвечай кратко и по делу.\n\n"
        f"Пользователь: {user_message}\nТы:"
    )
    response = await get_hf_response(full_prompt)

    # Убираем промпт из ответа
    if response.startswith(full_prompt):
        response = response[len(full_prompt):].strip()

    await update.message.reply_text(response)

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

# Запуск бота
def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ Не задан TELEGRAM_BOT_TOKEN")
        return
    if not HF_API_KEY:
        logger.error("❌ Не задан HF_API_KEY")
        return

    logger.info("🤖 Бот запускается...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # Запуск в режиме polling — идеально для Fly.io
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
