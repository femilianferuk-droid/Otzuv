import logging
import json
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
BOT_TOKEN = "8397723969:AAGV-qBJ8GWLYaeY_QCdRlJGZbGJhsGNLJU"

# Простая загрузка данных
def load_data():
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def load_settings():
    try:
        with open('bot_settings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "required_channels": ["@v3estnikov"],
            "admin_ids": [7973988177],
            "owner_id": 7973988177,
            "referral_bonus_inviter": 5,
            "referral_bonus_invited": 2,
            "min_withdraw_amount": 10,
            "min_referrals_for_withdraw": 1
        }

# Инициализация данных
user_data = load_data()
bot_settings = load_settings()

def save_data():
    try:
        with open('user_data.json', 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

def save_settings():
    try:
        with open('bot_settings.json', 'w', encoding='utf-8') as f:
            json.dump(bot_settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")

# Состояния
STATES = {
    'WAITING_USERNAME': 0,
    'WAITING_GIFTS_COUNT': 1,
    'WAITING_NFT_GIFTS_COUNT': 2,
    'WAITING_REVIEW': 3,
    'WAITING_WITHDRAW_AMOUNT': 4,
    'WAITING_WITHDRAW_DETAILS': 5,
    'WAITING_BROADCAST': 6,
    'WAITING_CHANNEL_ADD': 7,
    'WAITING_ADMIN_ADD': 8
}

# Проверка прав
def is_owner(user_id):
    return user_id == bot_settings["owner_id"]

def is_admin(user_id):
    return user_id in bot_settings["admin_ids"]

# Клавиатуры
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Оставить отзыв", callback_data="leave_review")],
        [InlineKeyboardButton("💰 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton("🛟 Поддержка", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])

def get_withdraw_methods_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 СБП", callback_data="withdraw_sbp")],
        [InlineKeyboardButton("💳 Банковская карта", callback_data="withdraw_card")],
        [InlineKeyboardButton("₿ Crypto Bot", callback_data="withdraw_crypto")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
    ]
    
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton("📢 Управление каналами", callback_data="admin_channels")])
        keyboard.append([InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        
        # Инициализация пользователя
        if str(user_id) not in user_data:
            user_data[str(user_id)] = {
                'balance': 0,
                'reviews_count': 0,
                'referrals': [],
                'referral_code': str(user_id),
                'invited_by': None,
                'total_earned': 0,
                'registered_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            save_data()
        else:
            user_data[str(user_id)]['last_activity'] = datetime.now().isoformat()
            save_data()
        
        # Реферальная ссылка
        if context.args:
            referrer_id = context.args[0]
            if referrer_id != str(user_id) and referrer_id in user_data:
                user_data[str(user_id)]['invited_by'] = referrer_id
                save_data()
        
        # Главное меню
        user_info = user_data[str(user_id)]
        balance = user_info.get('balance', 0)
        referrals_count = len(user_info.get('referrals', []))
        reviews_count = user_info.get('reviews_count', 0)
        
        min_amount = bot_settings.get('min_withdraw_amount', 10)
        min_refs = bot_settings.get('min_referrals_for_withdraw', 1)
        
        can_withdraw = balance >= min_amount and referrals_count >= min_refs
        
        welcome_text = f"""
🎉 *Добро пожаловать в бот оплаты за отзывы!* 🎉

💎 *Ваш баланс:* {balance}₽
👥 *Рефералов:* {referrals_count}
📝 *Отзывов:* {reviews_count}

📋 *Условия вывода:*
• {'✅' if balance >= min_amount else '❌'} Баланс: {balance}₽/{min_amount}₽
• {'✅' if referrals_count >= min_refs else '❌'} Рефералов: {referrals_count}/{min_refs}

{'✅ *Вывод доступен!*' if can_withdraw else '❌ *Вывод пока недоступен*'}
        """
        
        keyboard = get_main_keyboard()
        if is_admin(user_id):
            keyboard.inline_keyboard.append([InlineKeyboardButton("👑 Админ Панель", callback_data="admin_panel")])
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Ошибка в start: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "leave_review":
            user_data[str(user_id)] = {
                'state': STATES['WAITING_USERNAME'],
                'total_amount': 10,
                'username': '',
                'gifts_bonus': 0,
                'nft_bonus': 0,
                **user_data.get(str(user_id), {})
            }
            save_data()
            
            text = "📝 *Напишите ваш юзернейм в Telegram:*"
            await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode='Markdown')
        
        elif data == "withdraw":
            user_info = user_data.get(str(user_id), {})
            balance = user_info.get('balance', 0)
            referrals_count = len(user_info.get('referrals', []))
            
            min_amount = bot_settings.get('min_withdraw_amount', 10)
            min_refs = bot_settings.get('min_referrals_for_withdraw', 1)
            
            if balance < min_amount or referrals_count < min_refs:
                text = f"""
❌ *Вывод временно недоступен*

📋 *Требования для вывода:*
• {'✅' if balance >= min_amount else '❌'} Баланс: {balance}₽/{min_amount}₽
• {'✅' if referrals_count >= min_refs else '❌'} Рефералов: {referrals_count}/{min_refs}

💡 *Как выполнить условия:*
• 📝 Оставляйте отзывы чтобы увеличить баланс
• 👥 Приглашайте друзей по реферальной ссылке
                """
                await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
            else:
                text = f"""
✅ *Все условия выполнены!*

💰 *Ваш баланс:* {balance}₽
👥 *Ваши рефералы:* {referrals_count}

👇 *Выберите способ вывода:*
                """
                await query.edit_message_text(text, reply_markup=get_withdraw_methods_keyboard(), parse_mode='Markdown')
        
        elif data == "referral":
            user_info = user_data.get(str(user_id), {})
            ref_code = user_info.get('referral_code', str(user_id))
            bot_username = (await context.bot.get_me()).username
            ref_link = f"https://t.me/{bot_username}?start={ref_code}"
            ref_count = len(user_info.get('referrals', []))
            
            min_refs = bot_settings.get('min_referrals_for_withdraw', 1)
            
            text = f"""
👥 *Ваши рефералы:* {ref_count}/{min_refs}
💰 *Заработано с рефералов:* {ref_count * 5}₽

🎁 *Бонусы:*
• Вам за каждого реферала: 5₽
• Рефералу при первом отзыве: 2₽

📎 *Ваша реферальная ссылка:*
`{ref_link}`
            """
            
            keyboard = [
                [InlineKeyboardButton("📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}&text=Получай+деньги+за+отзывы!")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == "support":
            text = "🛟 *Поддержка:* @support_username"
            await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        
        elif data == "admin_panel":
            if not is_admin(user_id):
                await query.edit_message_text("❌ Доступ запрещен!")
                return
            
            role = "👑 *Владелец*" if is_owner(user_id) else "⚡ *Администратор*"
            text = f"{role}\n\n👇 *Выберите действие:*"
            
            await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id), parse_mode='Markdown')
        
        elif data == "admin_stats":
            if not is_admin(user_id):
                return
            
            total_users = len(user_data)
            total_reviews = sum(user.get('reviews_count', 0) for user in user_data.values())
            total_balance = sum(user.get('balance', 0) for user in user_data.values())
            
            text = f"""
👥 *Всего пользователей:* {total_users}
📝 *Всего отзывов:* {total_reviews}
💰 *Общий баланс:* {total_balance}₽
            """
            
            await query.edit_message_text(text, reply_markup=get_admin_keyboard(user_id), parse_mode='Markdown')
        
        elif data == "admin_broadcast":
            if not is_admin(user_id):
                return
            
            user_data[str(user_id)]['state'] = STATES['WAITING_BROADCAST']
            save_data()
            
            await query.edit_message_text("📢 *Введите сообщение для рассылки:*", reply_markup=get_back_keyboard(), parse_mode='Markdown')
        
        elif data in ["withdraw_sbp", "withdraw_card", "withdraw_crypto"]:
            user_info = user_data.get(str(user_id), {})
            balance = user_info.get('balance', 0)
            
            min_amount = bot_settings.get('min_withdraw_amount', 10)
            min_refs = bot_settings.get('min_referrals_for_withdraw', 1)
            referrals_count = len(user_info.get('referrals', []))
            
            if balance < min_amount or referrals_count < min_refs:
                await query.edit_message_text("❌ Не выполнены условия вывода!", reply_markup=get_main_keyboard())
                return
            
            method_map = {
                "withdraw_sbp": "СБП",
                "withdraw_card": "Банковская карта", 
                "withdraw_crypto": "Crypto Bot"
            }
            
            user_data[str(user_id)]['withdraw_method'] = method_map[data]
            user_data[str(user_id)]['state'] = STATES['WAITING_WITHDRAW_AMOUNT']
            save_data()
            
            text = f"""
💎 *Способ вывода:* {method_map[data]}
💰 *Доступный баланс:* {balance}₽

👇 *Напишите сумму для вывода:*
            """
            
            await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode='Markdown')
        
        elif data == "back_to_main":
            user_info = user_data.get(str(user_id), {})
            balance = user_info.get('balance', 0)
            referrals_count = len(user_info.get('referrals', []))
            reviews_count = user_info.get('reviews_count', 0)
            
            text = f"""
💎 *Баланс:* {balance}₽
👥 *Рефералов:* {referrals_count}
📝 *Отзывов:* {reviews_count}
            """
            
            keyboard = get_main_keyboard()
            if is_admin(user_id):
                keyboard.inline_keyboard.append([InlineKeyboardButton("👑 Админ Панель", callback_data="admin_panel")])
            
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
    except Exception as e:
        print(f"Ошибка в button_handler: {e}")
        try:
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
        except:
            pass

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        message_text = update.message.text
        
        if str(user_id) not in user_data:
            await start(update, context)
            return
        
        # Обновляем активность
        user_data[str(user_id)]['last_activity'] = datetime.now().isoformat()
        save_data()
        
        current_state = user_data[str(user_id)].get('state')
        
        # Рассылка
        if current_state == STATES['WAITING_BROADCAST'] and is_admin(user_id):
            await update.message.reply_text("📢 *Начинаю рассылку...*", parse_mode='Markdown')
            
            success = 0
            failed = 0
            
            for uid in list(user_data.keys())[:50]:  # Ограничим для теста
                try:
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=message_text,
                        parse_mode='Markdown'
                    )
                    success += 1
                    await asyncio.sleep(0.1)
                except:
                    failed += 1
            
            user_data[str(user_id)]['state'] = None
            save_data()
            
            await update.message.reply_text(
                f"✅ *Рассылка завершена!*\nУспешно: {success}\nНе удалось: {failed}",
                reply_markup=get_admin_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
        
        # Процесс отзыва
        if current_state == STATES['WAITING_USERNAME']:
            user_data[str(user_id)]['username'] = message_text
            user_data[str(user_id)]['state'] = STATES['WAITING_GIFTS_COUNT']
            save_data()
            
            await update.message.reply_text(
                "🎁 *Сколько обычных подарков?*\n0 = +0₽, 1+ = +3₽",
                reply_markup=get_back_keyboard(),
                parse_mode='Markdown'
            )
        
        elif current_state == STATES['WAITING_GIFTS_COUNT']:
            try:
                count = int(message_text)
                bonus = 3 if count > 0 else 0
                user_data[str(user_id)]['gifts_bonus'] = bonus
                user_data[str(user_id)]['gifts_count'] = count
                user_data[str(user_id)]['state'] = STATES['WAITING_NFT_GIFTS_COUNT']
                save_data()
                
                await update.message.reply_text(
                    "🖼️ *Сколько NFT подарков?*\n0 = +0₽, 1+ = +8₽",
                    reply_markup=get_back_keyboard(),
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text("❌ Введите число!")
        
        elif current_state == STATES['WAITING_NFT_GIFTS_COUNT']:
            try:
                count = int(message_text)
                bonus = 8 if count > 0 else 0
                user_data[str(user_id)]['nft_bonus'] = bonus
                
                total = 10 + user_data[str(user_id)]['gifts_bonus'] + bonus
                user_data[str(user_id)]['total_amount'] = total
                user_data[str(user_id)]['state'] = STATES['WAITING_REVIEW']
                save_data()
                
                await update.message.reply_text(
                    f"✍️ *Напишите отзыв:*\n💎 Сумма: {total}₽\n✅ Обязательно: @v3estnikov\n❌ Запрещено: скам",
                    reply_markup=get_back_keyboard(),
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text("❌ Введите число!")
        
        elif current_state == STATES['WAITING_REVIEW']:
            if "@v3estnikov" not in message_text:
                await update.message.reply_text("❌ Обязательно укажите @v3estnikov!", reply_markup=get_main_keyboard())
            elif "скам" in message_text.lower():
                await update.message.reply_text("❌ Запрещено слово 'скам'!", reply_markup=get_main_keyboard())
            else:
                # Начисляем деньги
                total = user_data[str(user_id)]['total_amount']
                user_data[str(user_id)]['balance'] = user_data[str(user_id)].get('balance', 0) + total
                user_data[str(user_id)]['reviews_count'] = user_data[str(user_id)].get('reviews_count', 0) + 1
                user_data[str(user_id)]['state'] = None
                
                # Реферальные бонусы
                inviter_id = user_data[str(user_id)].get('invited_by')
                if inviter_id and inviter_id in user_data:
                    user_data[inviter_id]['balance'] += 5
                    if str(user_id) not in user_data[inviter_id].get('referrals', []):
                        user_data[inviter_id].setdefault('referrals', []).append(str(user_id))
                
                save_data()
                
                await update.message.reply_text(
                    f"✅ *Отзыв принят!*\n💎 Начислено: {total}₽\n💰 Баланс: {user_data[str(user_id)]['balance']}₽",
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
        
        elif current_state == STATES['WAITING_WITHDRAW_AMOUNT']:
            try:
                amount = int(message_text)
                balance = user_data[str(user_id)].get('balance', 0)
                min_amount = bot_settings.get('min_withdraw_amount', 10)
                
                if amount < min_amount:
                    await update.message.reply_text(f"❌ Мин. сумма: {min_amount}₽!")
                elif amount > balance:
                    await update.message.reply_text(f"❌ Недостаточно средств! Доступно: {balance}₽")
                else:
                    user_data[str(user_id)]['withdraw_amount'] = amount
                    user_data[str(user_id)]['state'] = STATES['WAITING_WITHDRAW_DETAILS']
                    save_data()
                    
                    method = user_data[str(user_id)]['withdraw_method']
                    text = f"📋 *Введите реквизиты для {method}:*"
                    await update.message.reply_text(text, reply_markup=get_back_keyboard(), parse_mode='Markdown')
            except:
                await update.message.reply_text("❌ Введите число!")
        
        elif current_state == STATES['WAITING_WITHDRAW_DETAILS']:
            # Создаем заявку
            amount = user_data[str(user_id)]['withdraw_amount']
            user_data[str(user_id)]['balance'] -= amount
            user_data[str(user_id)]['state'] = None
            save_data()
            
            await update.message.reply_text(
                f"✅ *Заявка создана!*\n💎 Сумма: {amount}₽\n⏰ Обработка: до 24 часов",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        print(f"Ошибка в handle_message: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

# Запуск бота
def main():
    try:
        # Создаем приложение с настройками для стабильности
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🤖 Бот запускается...")
        print(f"👑 Владелец: {bot_settings['owner_id']}")
        print("💰 Условия вывода: 10₽ + 1 реферал")
        
        # Запускаем бота с обработкой ошибок
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        print("Перезапуск через 10 секунд...")
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
