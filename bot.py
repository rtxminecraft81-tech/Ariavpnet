msg = m.text
    success = 0
    fail = 0
    for uid in users.keys():
        try:
            bot.send_message(int(uid), f"👑 پیام از دربار آریا وی‌پی‌ان\n\n{msg}", parse_mode='Markdown')
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    bot.reply_to(m, f"✅ ارسال پیام پایان یافت!\n\n✅ موفق: {success}\n❌ ناموفق: {fail}")

@bot.message_handler(commands=['ban'])
def ban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) == ADMIN_ID:
            bot.reply_to(m, "❌ نمی‌توانید ادمین را بن کنید!")
            return
        banned_users.add(str(user_id))
        save_banned_users()
        try:
            bot.send_message(user_id, "⛔ شما توسط ادمین مسدود شده اید!\n🆔 @hegzosupport")
        except:
            pass
        bot.reply_to(m, f"✅ کاربر {user_id} مسدود شد.")
    except:
        bot.reply_to(m, "❌ دستور: /ban [user_id]")

@bot.message_handler(commands=['unban'])
def unban_user(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    try:
        user_id = int(m.text.split()[1])
        if str(user_id) in banned_users:
            banned_users.discard(str(user_id))
            save_banned_users()
            bot.reply_to(m, f"✅ کاربر {user_id} از حالت مسدودیت خارج شد.")
        else:
            bot.reply_to(m, f"❌ کاربر {user_id} در لیست مسدود شده‌ها نیست.")
    except:
        bot.reply_to(m, "❌ دستور: /unban [user_id]")

@bot.message_handler(commands=['banned'])
def list_banned(m):
    if str(m.from_user.id) != ADMIN_ID:
        return
    if not banned_users:
        bot.reply_to(m, "📭 هیچ کاربر مسدود شده‌ای وجود ندارد.")
        return
    text = "🚫 لیست کاربران مسدود شده:\n\n"
    for uid in banned_users:
        text += f"🆔 {uid}\n"
    bot.reply_to(m, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def unknown(m):
    user_id = m.from_user.id
    if is_banned(user_id):
        bot.reply_to(m, "⛔ شما مسدود شده اید!")
        return
    bot.reply_to(m, "❌ لطفا از دکمه‌های منوی اصلی استفاده کنید.", reply_markup=main_keyboard())

if name == 'main':
    PORT = int(os.environ.get('PORT', 10000))
    print(f"👑 آریا وی‌پی‌ان روی پورت {PORT} روشن شد!")
    print("✅ 25-50-100-200 گیگ با سرعت 4 مگابیت")
    
    try:
        bot.delete_webhook()
        print("✅ Webhook deleted!")
    except:
        pass
    
    time.sleep(2)
    
    try:
        bot.get_updates(offset=-1, limit=1)
        print("✅ Updates cleared!")
    except:
        pass
    
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)).start()
    
    bot.infinity_polling()
