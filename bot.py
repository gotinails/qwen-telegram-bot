import logging
import requests
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === Настройки ===
HF_API_KEY = os.getenv("HF_API_KEY")
MODEL_NAME = "Qwen/Qwen2.5-1.5B"  # Лёгкая, но умная модель
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

# Заголовки для запроса
headers = {"Authorization": f"Bearer {HF_API_KEY}"}

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для получения ответа от модели
async def get_hf_response(prompt: str) -> str:
    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }
        }
        response = requests.post(API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()[0]['generated_text'].strip()
        else:
            error = response.json()
            return f"Ошибка: {response.status_code} — {error.get('error', 'Неизвестная ошибка')}"
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.message.chat_id
    username = update.message.from_user.username or update.message.from_user.first_name
    logger.info(f"Сообщение от @{username} ({chat_id}): {user_message}")

    # Показываем "печатает..."
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # Получаем ответ
    full_prompt = f"Ты — дружелюбный и умный помощник. Отвечай кратко и по делу.\n\nПользователь: {user_message}\nТы:"
    response = await get_hf_response(full_prompt)

    # Убираем промпт из ответа (если модель его повторила)
    if response.startswith(full_prompt):
        response = response[len(full_prompt):].strip()

    # Отправляем ответ
    await update.message.reply_text(response)

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

# Запуск бота
def main():
    if not HF_API_KEY:
        logger.error("❌ Не задан HF_API_KEY")
        return
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.error("❌ Не задан TELEGRAM_BOT_TOKEN")
        return

    logger.info("🤖 Бот запускается...")

    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # === Настройка вебхука ===
    port = int(os.getenv("PORT", 8000))
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}.onrender.com/webhook"

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url,
        secret_token="my-super-secret-token-12345"
    )
