#!/usr/bin/env python3
"""
بوت تيليجرام متطور - إصدار نهائي
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

# المكتبات الخاصة بـ python-telegram-bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler
)

# ========== إعدادات البوت ==========
# 🔴 غير هذه القيم حسب بياناتك!
BOT_TOKEN = "8184511868:AAGK4PiBW1F17XVkMA2a5LbpdG6JhSYgLkE"  # توكن البوت
ADMIN_ID = 5858582355  # أيدي الأدمن

# حالات المحادثة
WAITING_FOR_REPLY, WAITING_FOR_BROADCAST = range(2)

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# أسماء الملفات
DATA_FILE = "bot_users.json"

# ========== دوال إدارة البيانات ==========
def load_data() -> dict:
    """تحميل البيانات من ملف"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"خطأ في تحميل البيانات: {e}")
    return {"users": {}, "user_ids": [], "user_count": 0, "messages": []}

def save_data(data: dict) -> bool:
    """حفظ البيانات إلى ملف"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")
        return False

def add_user(user_id: int, username: str, first_name: str, is_admin: bool = False) -> bool:
    """إضافة مستخدم جديد"""
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "username": username or "",
            "first_name": first_name or "",
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": 0,
            "is_admin": is_admin
        }
        
        if user_id_str not in data["user_ids"]:
            data["user_ids"].append(user_id_str)
        
        data["user_count"] = len(data["users"])
        save_data(data)
        return True
    
    # تحديث بيانات المستخدم الموجود
    data["users"][user_id_str]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(data)
    return False

def update_user_message(user_id: int, message: str):
    """تحديث رسائل المستخدم"""
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str in data["users"]:
        data["users"][user_id_str]["message_count"] += 1
        data["users"][user_id_str]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # حفظ الرسالة في السجل
        message_data = {
            "user_id": user_id_str,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "replied": False
        }
        
        if "messages" not in data:
            data["messages"] = []
        
        data["messages"].append(message_data)
        
        # حفظ فقط آخر 100 رسالة
        if len(data["messages"]) > 100:
            data["messages"] = data["messages"][-100:]
        
        save_data(data)

def get_user_count() -> int:
    """عدد المستخدمين"""
    data = load_data()
    return data.get("user_count", 0)

def get_all_users() -> list:
    """جميع المستخدمين"""
    data = load_data()
    return data.get("user_ids", [])

def get_user_info(user_id: str) -> dict:
    """معلومات مستخدم"""
    data = load_data()
    return data.get("users", {}).get(str(user_id), {})

# ========== دوال الأدمن ==========
def is_admin(user_id: int) -> bool:
    """التحقق إذا كان المستخدم أدمن"""
    return user_id == ADMIN_ID

def get_admin_stats() -> dict:
    """إحصائيات للأدمن"""
    data = load_data()
    users = data.get("users", {})
    
    # مستخدمين اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = sum(1 for user in users.values() if user.get("join_date", "").startswith(today))
    
    # مجموع الرسائل
    total_messages = sum(user.get("message_count", 0) for user in users.values())
    
    # الرسائل اليوم
    today_messages = 0
    for msg in data.get("messages", []):
        if msg.get("timestamp", "").startswith(today):
            today_messages += 1
    
    return {
        "total_users": len(users),
        "today_users": today_users,
        "total_messages": total_messages,
        "today_messages": today_messages
    }

# ========== دوال إنشاء الكيبورد ==========
def create_admin_main_keyboard() -> InlineKeyboardMarkup:
    """لوحة الأدمن الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="stats_main")],
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="users_main")],
        [InlineKeyboardButton("📣 إرسال إشعار للكل", callback_data="broadcast_main")],
        [InlineKeyboardButton("📨 آخر الرسائل", callback_data="messages_main")],
        [InlineKeyboardButton("🔄 تحديث البيانات", callback_data="refresh_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_user_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة المستخدم الرئيسية"""
    if is_admin(user_id):
        return create_admin_main_keyboard()
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ معلومات عن البوت", callback_data="about_info")],
        [InlineKeyboardButton("📞 كيفية التواصل", callback_data="contact_info")],
        [InlineKeyboardButton("🔔 اشعارات البوت", callback_data="notifications_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_back_keyboard(target: str = "main") -> InlineKeyboardMarkup:
    """زر الرجوع"""
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=f"back_{target}")]]
    return InlineKeyboardMarkup(keyboard)

def create_reply_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """زر الرد على مستخدم"""
    keyboard = [[InlineKeyboardButton("↩️ الرد على الرسالة", callback_data=f"reply_{user_id}")]]
    return InlineKeyboardMarkup(keyboard)

def create_stats_keyboard() -> InlineKeyboardMarkup:
    """لوحة الإحصائيات"""
    keyboard = [
        [InlineKeyboardButton("📈 إحصائيات عامة", callback_data="stats_general")],
        [InlineKeyboardButton("📅 إحصائيات اليوم", callback_data="stats_today")],
        [InlineKeyboardButton("👤 أفضل المستخدمين", callback_data="stats_top")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_users_list_keyboard(page: int = 0) -> tuple:
    """لوحة قائمة المستخدمين مع ترقيم الصفحات"""
    users = get_all_users()
    data = load_data()
    
    # ترتيب المستخدمين حسب تاريخ الانضمام
    sorted_users = sorted(users, key=lambda x: data["users"].get(x, {}).get("join_date", ""), reverse=True)
    
    # تقسيم إلى صفحات (10 مستخدمين لكل صفحة)
    items_per_page = 10
    total_pages = (len(sorted_users) + items_per_page - 1) // items_per_page
    
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_users = sorted_users[start_idx:end_idx]
    
    # إنشاء لوحة المفاتيح
    keyboard = []
    
    for user_id in page_users:
        user_info = data["users"].get(user_id, {})
        name = user_info.get("first_name", "مستخدم")
        
        # تقصير الاسم إذا كان طويلاً
        if len(name) > 15:
            name = name[:15] + "..."
        
        button_text = f"👤 {name}"
        if user_info.get("message_count", 0) > 0:
            button_text += f" ({user_info['message_count']})"
        
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f"viewuser_{user_id}"
        )])
    
    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"users_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="none"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️ التالي", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    
    # نص الصفحة
    page_text = f"📋 قائمة المستخدمين (الصفحة {page+1} من {total_pages})\n"
    page_text += f"👥 الإجمالي: {len(sorted_users)} مستخدم\n\n"
    
    return page_text, InlineKeyboardMarkup(keyboard)

# ========== أوامر البوت ==========
async def start(update: Update, context: CallbackContext):
    """أمر /start"""
    user = update.effective_user
    
    # تحقق إذا كان أدمن
    user_is_admin = is_admin(user.id)
    
    # إضافة المستخدم
    is_new = add_user(user.id, user.username, user.first_name, user_is_admin)
    
    # رسالة ترحيبية مختلفة
    if user_is_admin:
        welcome = f"""
🎖️ *مرحباً أيها الأدمن {user.first_name}!*

🤖 *لوحة التحكم جاهزة لك*
🔸 اضغط على الأزرار أدناه للتحكم الكامل
🔸 يمكنك الرد على جميع الرسائل مباشرة

🆔 رقمك: `{user.id}`
🔐 صلاحيات: مدير البوت
        """
        reply_markup = create_admin_main_keyboard()
    else:
        welcome = f"""
🎊 *أهلاً وسهلاً {user.first_name}!*

🤖 *مرحباً بك في بوت التواصل*
🔸 يمكنك إرسال رسائلك مباشرة
🔸 سنرد عليك بأسرع وقت

📌 *ملاحظة:* هذا بوت تواصل مباشر مع الإدارة
🆔 رقمك: `{user.id}`
        """
        reply_markup = create_user_main_keyboard(user.id)
    
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)
    
    # إشعار للأدمن إذا كان مستخدم جديد وليس أدمن
    if is_new and not user_is_admin:
        try:
            admin_msg = f"""
👤 *مستخدم جديد دخل البوت*

🆔 الرقم: `{user.id}`
📛 الاسم: {user.first_name}
🔖 اليوزر: @{user.username or 'لا يوجد'}

📅 الوقت: {datetime.now().strftime('%H:%M:%S')}
            """
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار أدمن: {e}")

async def help_cmd(update: Update, context: CallbackContext):
    """أمر /help"""
    user = update.effective_user
    
    if is_admin(user.id):
        help_text = """
🆘 *مركز مساعدة الأدمن*

📌 *الأوامر المتاحة:*
/start - عرض لوحة التحكم
/admin - لوحة التحكم (متاحة في الأزرار)

📋 *الميزات:*
- عرض الإحصائيات
- إدارة المستخدمين
- إرسال إشعارات للكل
- الرد على الرسائل مباشرة

💡 *نصيحة:* استخدم الأزرار للتحكم السريع
        """
        reply_markup = create_admin_main_keyboard()
    else:
        help_text = """
🆘 *مركز المساعدة*

📌 *كيفية الاستخدام:*
1. أرسل رسالتك مباشرة في الدردشة
2. انتظر رد المشرف
3. يمكنك إرسال عدة رسائل

🔔 *ملاحظات:*
- الردود تكون في أقرب وقت
- يمكنك متابعة رسائلك

📞 *للتواصل السريع:* أرسل رسالتك مباشرة
        """
        reply_markup = create_user_main_keyboard(user.id)
    
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def about_cmd(update: Update, context: CallbackContext):
    """أمر /about"""
    stats = get_admin_stats()
    
    about_text = f"""
🤖 *معلومات عن البوت*

📛 *الاسم:* بوت التواصل المباشر
✨ *الوصف:* بوت للتواصل مع الإدارة
📊 *المستخدمين:* {stats['total_users']}
📨 *الرسائل:* {stats['total_messages']}

🔧 *المميزات:*
- تواصل مباشر مع الإدارة
- إشعارات فورية
- ردود سريعة
- واجهة سهلة

⚡ *الإصدار:* 3.0 نهائي
📅 {datetime.now().strftime('%Y-%m-%d')}
    """
    
    user = update.effective_user
    reply_markup = create_user_main_keyboard(user.id)
    
    await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)

async def admin_cmd(update: Update, context: CallbackContext):
    """أمر /admin - اختياري"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ *ليس لديك صلاحية!*", parse_mode='Markdown')
        return
    
    admin_text = f"""
👑 *لوحة تحكم الأدمن*

🎖️ *مرحباً {user.first_name}!*

📊 *الإحصائيات السريعة:*
👥 المستخدمين: {get_user_count()}
🆔 رقمك: `{user.id}`
🕐 {datetime.now().strftime('%H:%M:%S')}

📌 *اختر من القائمة أدناه:*
    """
    
    await update.message.reply_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=create_admin_main_keyboard()
    )

# ========== معالجة رسائل المستخدمين ==========
async def handle_user_message(update: Update, context: CallbackContext):
    """معالجة رسائل المستخدمين"""
    user = update.effective_user
    message_text = update.message.text
    
    # إذا كان المرسل هو الأدمن، تجاهل (ما عدا في وضع الرد)
    if is_admin(user.id) and context.user_data.get('replying_to') is None:
        # الأدمن يرسل رسالة عادية
        await update.message.reply_text(
            "👑 أنت الأدمن! استخدم الأزرار للتحكم في البوت.",
            parse_mode='Markdown',
            reply_markup=create_admin_main_keyboard()
        )
        return
    
    # تحديث رسالة المستخدم
    update_user_message(user.id, message_text)
    
    # إضافة المستخدم إذا كان جديداً
    add_user(user.id, user.username, user.first_name, is_admin(user.id))
    
    # رد تلقائي للمستخدم
    await update.message.reply_text(
        "✅ *تم استلام رسالتك بنجاح!*\n\n"
        "📨 المشرف سيرد عليك في أقرب وقت.\n"
        "⏳ الرجاء الانتظار...",
        parse_mode='Markdown'
    )
    
    # إرسال إشعار مختصر للأدمن
    admin_notification = f"""
📬 *رسالة جديدة*

👤 *المرسل:* {user.first_name}
🔖 @{user.username or 'لا يوجد يوزر'}
🆔 `{user.id}`

📝 *الرسالة:*
{message_text}
    """
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_notification,
            parse_mode='Markdown',
            reply_markup=create_reply_keyboard(str(user.id))
        )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار: {e}")

# ========== معالجة الأزرار الرئيسية ==========
async def button_handler(update: Update, context: CallbackContext):
    """معالجة جميع الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    logger.info(f"زر مضغوط: {data} من {user.id}")
    
    # زر الرجوع العام
    if data == "back_main":
        if is_admin(user.id):
            await query.edit_message_text(
                "👑 *لوحة تحكم الأدمن*\n\nاختر من القائمة:",
                parse_mode='Markdown',
                reply_markup=create_admin_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "🤖 *مرحباً بك في البوت*\n\nاختر من القائمة:",
                parse_mode='Markdown',
                reply_markup=create_user_main_keyboard(user.id)
            )
        return
    
    # زر الرجوع للإحصائيات
    elif data == "back_stats":
        stats_text = "📊 *قائمة الإحصائيات*\n\nاختر نوع الإحصائيات:"
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
        return
    
    # زر لا شيء (للأزرار غير النشطة)
    elif data == "none":
        await query.answer("هذا الزر للإعلام فقط")
        return
    
    # ========== معالجة أزرار الأدمن ==========
    if not is_admin(user.id):
        await query.answer("⛔ ليس لديك صلاحية!")
        return
    
    # الإحصائيات الرئيسية
    if data == "stats_main":
        stats = get_admin_stats()
        stats_text = f"""
📊 *الإحصائيات الرئيسية*

👥 *المستخدمين:*
✅ الإجمالي: {stats['total_users']}
🆕 اليوم: {stats['today_users']}

📨 *الرسائل:*
✍️ الإجمالي: {stats['total_messages']}
📅 اليوم: {stats['today_messages']}

📌 *اختر لمزيد من التفاصيل:*
        """
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
    
    # قائمة المستخدمين
    elif data == "users_main":
        page_text, reply_markup = create_users_list_keyboard()
        await query.edit_message_text(
            page_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    # إرسال إشعار للكل
    elif data == "broadcast_main":
        await query.edit_message_text(
            "📣 *إرسال إشعار للجميع*\n\n"
            "📝 أرسل الرسالة الآن:\n"
            "(أو /cancel للإلغاء)",
            parse_mode='Markdown',
            reply_markup=create_back_keyboard("main")
        )
        context.user_data['waiting_broadcast'] = True
        return WAITING_FOR_BROADCAST
    
    # آخر الرسائل
    elif data == "messages_main":
        data_obj = load_data()
        messages = data_obj.get("messages", [])
        
        if not messages:
            await query.edit_message_text(
                "📭 لا توجد رسائل بعد!",
                parse_mode='Markdown',
                reply_markup=create_back_keyboard("main")
            )
            return
        
        # عرض آخر 5 رسائل
        recent_messages = messages[-5:]
        messages_text = "📨 *آخر الرسائل الواردة:*\n\n"
        
        for i, msg in enumerate(recent_messages[::-1], 1):
            user_info = get_user_info(msg["user_id"])
            name = user_info.get("first_name", "مستخدم")
            username = user_info.get("username", "")
            
            messages_text += f"{i}. 👤 {name}"
            if username:
                messages_text += f" (@{username})"
            
            messages_text += f"\n   🆔 `{msg['user_id']}`\n"
            messages_text += f"   📝 {msg['message'][:50]}"
            if len(msg['message']) > 50:
                messages_text += "..."
            
            messages_text += f"\n   🕐 {msg['timestamp']}\n"
            
            # زر الرد السريع
            reply_btn = InlineKeyboardButton(
                f"↩️ الرد على {name}",
                callback_data=f"reply_{msg['user_id']}"
            )
            
            # إذا كانت هذه ليست الرسالة الأولى، أضف سطراً فارغاً
            if i < len(recent_messages):
                messages_text += "\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            messages_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # تحديث البيانات
    elif data == "refresh_main":
        count = get_user_count()
        await query.edit_message_text(
            f"🔄 *تم تحديث البيانات!*\n\n"
            f"✅ عدد المستخدمين: {count}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown',
            reply_markup=create_admin_main_keyboard()
        )
    
    # الإحصائيات العامة
    elif data == "stats_general":
        stats = get_admin_stats()
        data_obj = load_data()
        
        # حساب متوسط الرسائل
        avg_messages = 0
        if stats['total_users'] > 0:
            avg_messages = stats['total_messages'] / stats['total_users']
        
        stats_text = f"""
📈 *الإحصائيات العامة*

👥 *المستخدمين:*
✅ الإجمالي: {stats['total_users']}
💬 نشطين: {sum(1 for u in data_obj['users'].values() if u.get('message_count', 0) > 0)}

📨 *الرسائل:*
✍️ الإجمالي: {stats['total_messages']}
📊 المتوسط: {avg_messages:.1f} رسالة/مستخدم

📅 *الفترة:*
⏳ أول مستخدم: {min([u.get('join_date', '') for u in data_obj['users'].values()] + ['غير معروف'])}
🕐 آخر نشاط: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
    
    # إحصائيات اليوم
    elif data == "stats_today":
        stats = get_admin_stats()
        stats_text = f"""
📅 *إحصائيات اليوم*

👥 *المستخدمين:*
🆕 الجدد: {stats['today_users']}

📨 *الرسائل:*
📝 اليوم: {stats['today_messages']}

⏰ *التوقيت:*
🕒 من: 00:00:00
🕒 إلى: {datetime.now().strftime('%H:%M:%S')}

📊 *النسبة من الإجمالي:*
👥 {((stats['today_users']/max(stats['total_users'], 1))*100):.1f}% من المستخدمين
📨 {((stats['today_messages']/max(stats['total_messages'], 1))*100):.1f}% من الرسائل
        """
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
    
    # أفضل المستخدمين
    elif data == "stats_top":
        data_obj = load_data()
        users = data_obj.get("users", {})
        
        # ترتيب المستخدمين حسب عدد الرسائل
        sorted_users = sorted(
            [(uid, info) for uid, info in users.items() if int(uid) != ADMIN_ID],
            key=lambda x: x[1].get("message_count", 0),
            reverse=True
        )[:10]
        
        if not sorted_users:
            await query.edit_message_text(
                "📭 لا توجد بيانات كافية عن المستخدمين!",
                parse_mode='Markdown',
                reply_markup=create_stats_keyboard()
            )
            return
        
        top_text = "🏆 *أفضل 10 مستخدمين نشاطاً:*\n\n"
        
        for i, (uid, info) in enumerate(sorted_users, 1):
            top_text += f"{i}. 👤 {info.get('first_name', 'مستخدم')}"
            if info.get("username"):
                top_text += f" (@{info['username']})"
            
            top_text += f"\n   📨 {info.get('message_count', 0)} رسالة"
            top_text += f"\n   🆔 `{uid}`\n\n"
        
        await query.edit_message_text(
            top_text,
            parse_mode='Markdown',
            reply_markup=create_stats_keyboard()
        )
    
    # عرض صفحة معينة من المستخدمين
    elif data.startswith("users_page_"):
        page = int(data.replace("users_page_", ""))
        page_text, reply_markup = create_users_list_keyboard(page)
        await query.edit_message_text(
            page_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    # عرض مستخدم معين
    elif data.startswith("viewuser_"):
        user_id = data.replace("viewuser_", "")
        user_info = get_user_info(user_id)
        
        if not user_info:
            await query.edit_message_text(
                "❌ المستخدم غير موجود!",
                parse_mode='Markdown',
                reply_markup=create_back_keyboard("main")
            )
            return
        
        user_text = f"""
👤 *معلومات المستخدم*

📛 *الاسم:* {user_info.get('first_name', 'غير معروف')}
🔖 *اليوزر:* @{user_info.get('username', 'لا يوجد')}
🆔 *الرقم:* `{user_id}`

📅 *تاريخ الانضمام:* {user_info.get('join_date', 'غير معروف')}
🕐 *آخر نشاط:* {user_info.get('last_active', 'غير معروف')}
📨 *عدد الرسائل:* {user_info.get('message_count', 0)}

📌 *اختر الإجراء:*
        """
        
        keyboard = [
            [InlineKeyboardButton("↩️ الرد على هذا المستخدم", callback_data=f"reply_{user_id}")],
            [InlineKeyboardButton("📨 عرض رسائله", callback_data=f"usermsgs_{user_id}")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="users_main")]
        ]
        
        await query.edit_message_text(
            user_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # الرد على مستخدم
    elif data.startswith("reply_"):
        user_id = data.replace("reply_", "")
        user_info = get_user_info(user_id)
        
        if not user_info:
            await query.edit_message_text(
                "❌ المستخدم غير موجود!",
                parse_mode='Markdown',
                reply_markup=create_back_keyboard("main")
            )
            return
        
        # حفظ حالة الرد
        context.user_data['replying_to'] = user_id
        context.user_data['reply_message_id'] = query.message.message_id
        
        reply_text = f"""
↩️ *الرد على المستخدم*

👤 *إلى:* {user_info.get('first_name', 'المستخدم')}
🔖 @{user_info.get('username', 'لا يوجد يوزر')}
🆔 `{user_id}`

📝 *أرسل الآن رسالة الرد:*
(أرسل /cancel للإلغاء)
        """
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_reply")]]
        
        await query.edit_message_text(
            reply_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_FOR_REPLY
    
    # إلغاء الرد
    elif data == "cancel_reply":
        context.user_data.pop('replying_to', None)
        await query.edit_message_text(
            "❌ تم إلغاء الرد",
            parse_mode='Markdown',
            reply_markup=create_admin_main_keyboard()
        )
        return ConversationHandler.END
    
    # أزرار للمستخدمين العاديين
    elif data == "about_info":
        await about_cmd(update, context)
    
    elif data == "contact_info":
        contact_text = """
📞 *كيفية التواصل*

📌 *طريقة التواصل:*
1. أرسل رسالتك مباشرة
2. انتظر رد المشرف
3. يمكنك إرسال استفسارات متعددة

⏰ *أوقات الرد:*
- الردود في أقرب وقت ممكن
- 24/7 متاحة للرسائل

🔔 *ملاحظة:* هذا بوت تواصل مباشر
        """
        await query.edit_message_text(
            contact_text,
            parse_mode='Markdown',
            reply_markup=create_user_main_keyboard(user.id)
        )
    
    elif data == "notifications_info":
        notify_text = """
🔔 *إشعارات البوت*

📌 *ما تحصل عليه:*
- تأكيد استلام الرسالة
- رد من المشرف عند الرد
- إشعارات مهمة من الإدارة

🔕 *إيقاف الإشعارات:*
لا يمكن إيقاف الإشعارات الأساسية
لأنها مهمة للتواصل

📱 *لأي استفسار:* أرسل رسالة مباشرة
        """
        await query.edit_message_text(
            notify_text,
            parse_mode='Markdown',
            reply_markup=create_user_main_keyboard(user.id)
        )

# ========== معالجة رد الأدمن ==========
async def handle_admin_reply(update: Update, context: CallbackContext):
    """معالجة رد الأدمن على المستخدم"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return ConversationHandler.END
    
    # التحقق إذا كان في وضع الرد
    target_user_id = context.user_data.get('replying_to')
    
    if not target_user_id:
        return ConversationHandler.END
    
    reply_text = update.message.text
    
    # إلغاء إذا كان /cancel
    if reply_text.lower() == "/cancel":
        context.user_data.pop('replying_to', None)
        await update.message.reply_text(
            "❌ تم إلغاء الرد",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    try:
        # إرسال الرد للمستخدم
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=f"📨 *رد من الإدارة:*\n\n{reply_text}",
            parse_mode='Markdown'
        )
        
        # تأكيد للأدمن
        user_info = get_user_info(target_user_id)
        await update.message.reply_text(
            f"✅ *تم إرسال الرد بنجاح!*\n\n"
            f"👤 إلى: {user_info.get('first_name', 'المستخدم')}\n"
            f"🆔 الرقم: `{target_user_id}`",
            parse_mode='Markdown',
            reply_markup=create_admin_main_keyboard()
        )
        
        # تحديث الرسالة الأصلية
        reply_message_id = context.user_data.get('reply_message_id')
        if reply_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=ADMIN_ID,
                    message_id=reply_message_id,
                    text=f"✅ *تم الرد على هذا المستخدم*\n\n👤 بواسطة: {user.first_name}\n🕐 {datetime.now().strftime('%H:%M:%S')}",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # تنظيف البيانات
        context.user_data.pop('replying_to', None)
        context.user_data.pop('reply_message_id', None)
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الرد: {e}")
        await update.message.reply_text(
            f"❌ *فشل إرسال الرد!*\n\nالخطأ: {str(e)}",
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END

async def cancel_reply(update: Update, context: CallbackContext):
    """إلغاء الرد"""
    if is_admin(update.effective_user.id):
        context.user_data.pop('replying_to', None)
        await update.message.reply_text(
            "❌ تم إلغاء عملية الرد",
            reply_markup=create_admin_main_keyboard()
        )
    return ConversationHandler.END

# ========== معالجة البث ==========
async def handle_broadcast_message(update: Update, context: CallbackContext):
    """معالجة رسالة البث"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return ConversationHandler.END
    
    if context.user_data.get('waiting_broadcast'):
        broadcast_text = update.message.text
        
        if broadcast_text.lower() == "/cancel":
            context.user_data.pop('waiting_broadcast', None)
            await update.message.reply_text(
                "❌ تم إلغاء البث",
                reply_markup=create_admin_main_keyboard()
            )
            return ConversationHandler.END
        
        users = get_all_users()
        total = len(users)
        
        if total == 0:
            await update.message.reply_text(
                "📭 لا يوجد مستخدمين!",
                reply_markup=create_admin_main_keyboard()
            )
            context.user_data.pop('waiting_broadcast', None)
            return ConversationHandler.END
        
        # إرسال البث
        progress_msg = await update.message.reply_text(f"🚀 جاري الإرسال لـ {total} مستخدم...")
        
        success = 0
        for uid in users:
            try:
                if int(uid) != ADMIN_ID:  # لا ترسل للأدمن
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=broadcast_text,
                        parse_mode='Markdown'
                    )
                    success += 1
            except:
                pass
        
        await progress_msg.edit_text(
            f"📣 *تم الانتهاء من البث!*\n\n"
            f"✅ ناجح: {success}\n"
            f"📊 الإجمالي: {total}\n"
            f"📅 {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='Markdown'
        )
        
        context.user_data.pop('waiting_broadcast', None)
        return ConversationHandler.END

# ========== التشغيل الرئيسي ==========
def main():
    """الدالة الرئيسية لتشغيل البوت"""
    print("=" * 50)
    print("🤖 بوت تيليجرام - الإصدار النهائي")
    print("✨ مع واجهة أزرار متكاملة")
    print("=" * 50)
    
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة handler للمحادثة
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler),
        ],
        states={
            WAITING_FOR_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_reply),
                CommandHandler("cancel", cancel_reply),
            ],
            WAITING_FOR_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message),
                CommandHandler("cancel", cancel_reply),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_reply)],
    )
    
    # إضافة handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    
    # إضافة handler المحادثة
    app.add_handler(conv_handler)
    
    # إضافة handler لرسائل المستخدمين
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    
    # بدء البوت
    print("✅ البوت يعمل بنجاح!")
    print(f"👑 الأدمن: {ADMIN_ID}")
    print("📱 اذهب إلى تيليجرام وجرب:")
    print("   /start - لرؤية الأزرار مباشرة")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    # تحذير الأمان
    print("⚠️  تأكد من تغيير التوكن!")
    print("=" * 40)
    
    main()