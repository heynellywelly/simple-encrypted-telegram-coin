# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.abspath('.'), 'venv/Lib/site-packages'))

import telegram
from telegram.ext import (Updater, Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler,
                            ConversationHandler)

from flask import Flask, request

app = Flask(__name__)

global bot
bot = telegram.Bot(token=os.environ['BOT_TOKEN'])

global dispatcher
dispatcher = None

from handlers.handler import (start, register, wallet, transfer_list, inline_button_callback, user_transfer_amt,
                                cancel_transaction, transactions)

@app.route('/' + os.environ['BOT_TOKEN'], methods=['POST'])
def webhook_handler():
    if (request.method == 'POST'):
        # Retrieve the message in JSON, then transform it to a Telegram object
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        webhook_update(update)

    return 'ok'

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    # Setup the Google App Engine Dispatcher
    setup_gae_dispatcher()

    is_webhook_set = bot.setWebhook(os.environ['APP_URL'] + '/' + os.environ['BOT_TOKEN'])

    if (is_webhook_set):
        return "Webhook setup was a success!"
    else:
        return "Webhook setup didn't work out, it failed."

def webhook_update(update):
    global dispatcher

    if (dispatcher is None):
        setup_gae_dispatcher()
        
    dispatcher.process_update(update)

def setup_gae_dispatcher():
    global dispatcher

    dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0)

    # Create a conversation handler for transferring CGCoins
    SELECT_TRANSFEREE, SET_TRANSFER_AMT = range(2)

    transfer_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("transfer", transfer_list, pass_user_data=True)],
        states={
            SELECT_TRANSFEREE: [CallbackQueryHandler(inline_button_callback, pass_user_data=True)],
            SET_TRANSFER_AMT: [MessageHandler(Filters.text, user_transfer_amt, pass_user_data=True)]
        },
        fallbacks=[CommandHandler("cancel", cancel_transaction)]
    )

    # Register handlers here
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("reg", register))
    dispatcher.add_handler(CommandHandler("wallet", wallet))
    dispatcher.add_handler(CommandHandler("transactions", transactions))
    dispatcher.add_handler(transfer_conv_handler)

    return dispatcher

@app.route('/')
def index():
    return "."
