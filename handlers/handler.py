# -*- coding: utf-8 -*-

import telegram
from database.gaedb import (register_new_user, get_wallet_info, get_transferees, get_transferrer_wallet_addr, 
	get_user_pvt_chat_id, retrieve_transactions, generate_transaction)
from telegram.ext import ConversationHandler

SELECT_TRANSFEREE, SET_TRANSFER_AMT = range(2)

def start(bot, update):
    bot.sendMessage(update.message.chat.id, text="Hi there! Please register with us via /reg if you have not, else type /help for more information!")

def register(bot, update):
	response_text = register_new_user((update.message.from_user.first_name).decode('utf-8'), str(update.message.from_user.id), str(update.message.chat.id))
	bot.sendMessage(update.message.chat.id, text=response_text)

def wallet(bot, update):
	response_text = get_wallet_info(str(update.message.from_user.id))
	bot.sendMessage(update.message.chat.id, text=response_text, reply_markup=telegram.ReplyKeyboardMarkup([['/transfer']], one_time_keyboard=True))

def transfer_list(bot, update, user_data):
	response_text = "Who would you like to make a transfer to?"
	# Store the transferrer's wallet address
	is_user_found, transferrer_wallet_addr = get_transferrer_wallet_addr(str(update.message.from_user.id))
	if (is_user_found):
		user_data['transferrer_wallet_addr'] = transferrer_wallet_addr
		transferees_list = get_transferees(str(update.message.from_user.id))
		# Send a list of transferees that the user can transfer CGCoin to
		update.message.reply_text(text=response_text, reply_markup=transferees_list)
		# Send the user a 'Cancel' option
		bot.sendMessage(get_user_pvt_chat_id(str(update.message.from_user.id)), text="Or cancel your transaction any time.", reply_markup=telegram.ReplyKeyboardMarkup([['/cancel']], one_time_keyboard=True))
		return SELECT_TRANSFEREE
	# Else if the user cannot be found in the database
	else:
		bot.sendMessage(update.message.chat.id, text="ERROR: You don't seem to have been registered with us, would you like to register for a CGCoin Wallet? /reg")
		cancel_transaction(bot, update, user_data)

def inline_button_callback(bot, update, user_data):
	callback_data = update.callback_query.data
	# If this unique string exists in the callback data,
	# then this is the callback case for TRANSFERRING CGCoin
	if ("?~`xfer_wa_add" in callback_data):
		bot.answer_callback_query(update.callback_query.id)
		# Retrieve the transferee's wallet address
		transferee_wallet_addr = callback_data.split("?~`xfer_wa_add", 1)[1]
		# Store the transferee's wallet address
		user_data['transferee_wallet_addr'] = transferee_wallet_addr
		# Store the transferrer's wallet address 
		is_wa_addr_available, wallet_addr = get_transferrer_wallet_addr(update.callback_query.from_user.id)
		# If the user's wallet address can be found
		if (is_wa_addr_available):
			user_data['transferrer_wallet_addr'] = wallet_addr
			# Ask the user how much they would like to transfer
			bot.sendMessage(get_user_pvt_chat_id(str(update.callback_query.from_user.id)), text="Your recipient's wallet address is: " + wallet_addr + "\n\n" + "How much would you like to transfer?" + "\n\n" + "NOTE: The minimum transfer is 1 CGCoin.", reply_markup=telegram.ReplyKeyboardMarkup([['/cancel']], one_time_keyboard=True))
			return SET_TRANSFER_AMT

	cancel_transaction(bot, update, user_data)

def user_transfer_amt(bot, update, user_data):
	user_text_amt = update.message.text
	transferrer_wallet_addr = user_data['transferrer_wallet_addr']
	transferee_wallet_addr = user_data['transferee_wallet_addr']

	# Check if the user's input amount is:
	# 1) An integer, and
	# 2) it is a value greater than zero
	try:
		# 1)
		user_int_amt = int(user_text_amt)
		# 2)
		if (user_int_amt > 0):
			# Create a Transaction
			is_transaction_created = generate_transaction(transferrer_wallet_addr, transferee_wallet_addr, user_text_amt)
			if (is_transaction_created):
				# Let the user know that the transaction has been registered
				update.message.reply_text("Your transaction of " + str(user_int_amt) + " CGCoin(s) has been registered, and will be authenticated at the next available period.")
			else:
				# Let the user know that something went wrong with the transaction
				update.message.reply_text("Something went wrong with your transaction, please try again or contact the Capgemini Exchange Administrator.")
			# END the conversation
			return ConversationHandler.END
		# The user entered an integer which is less than or equal to zero 
		else:
			update.message.reply_text("Please transfer an amount that is greater than zero.")
			return SET_TRANSFER_AMT
	# The user entered a non-numerical value
	except ValueError:
		update.message.reply_text("Please enter a numerical value for your CGCoin transfer.")
		return SET_TRANSFER_AMT

def cancel_transaction(bot, update, user_data=None):
	update.message.reply_text("You have cancelled your CGCoin transaction.")

	if (user_data is not None):
		if ('transferrer_wallet_addr' in user_data):
			del user_data['transferrer_wallet_addr']
		if ('transferee_wallet_addr' in user_data):
			del user_data['transferee_wallet_addr']

		user_data.clear()

	return ConversationHandler.END

def transactions(bot, update):
	response_text = retrieve_transactions()
	bot.sendMessage(update.message.chat.id, text=response_text)


