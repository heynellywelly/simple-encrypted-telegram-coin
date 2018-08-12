# -*- coding: utf-8 -*-

import telegram
import string
import random
import Crypto
import binascii
from collections import OrderedDict
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256

class User(ndb.Model):
	user_name = ndb.StringProperty()
	user_id = ndb.StringProperty()
	pvt_chat_id = ndb.StringProperty()
	wallet_addr = ndb.StringProperty()

class Wallet(ndb.Model):
	pvt_key = ndb.StringProperty()
	pub_key = ndb.StringProperty()
	wallet_addr = ndb.StringProperty()
	wallet_val = ndb.IntegerProperty()

class Blockchain(ndb.Model):
	blocks = ndb.StructuredProperty(Block, repeated=True)

# Takes in a user's (first) name, Telegram user ID, and chat ID between the user and the bot,
# and returns a response text indicating the user's successful registration, or a failed
# registration due to the user having already signed up
def register_new_user(user_name, user_id, user_pvt_chat_id):
	# The text to return to the user
	return_text = ""

	# Fetch all users in the database
	all_users = User.query().fetch()

	for each_user in all_users:
		if (each_user.user_id == str(user_id)):
			return_text = "Thank you but our records indicate that you have already registered with us!"

	# If at this point, return_text is still an empty string,
	# then register the user
	if (return_text == ""):
		user_wallet_addr = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
		# Create a new User entity
		new_user = User(user_name=user_name, user_id=str(user_id), pvt_chat_id=user_pvt_chat_id, wallet_addr=user_wallet_addr)
		new_user.put()
		# Generate the Wallet's private and public keys for this user
		pvt_key, pub_key = generate_wallet_keys()
		# Create a new Wallet entity for this user
		new_wallet = Wallet(pvt_key=pvt_key, pub_key=pub_key, wallet_addr=user_wallet_addr, wallet_val=100)
		new_wallet.put()
		return_text = "Thank you for registering with us, " + user_name + "." + " Your CGCoin Wallet has been created, with the wallet address: " + user_wallet_addr + "." + " 100 CGCoins have been deposited in your account as a welcome gift." + "\n\n Please use /wallet to view your CGCoin Wallet."
	
	return return_text

# Takes in no parameters, and generates a private and public key for a user's wallet
def generate_wallet_keys(): 
	random_gen = Crypto.Random.new().read
	pvt_key = RSA.generate(1024, random_gen)
	pub_key = pvt_key.publickey()

	return (binascii.hexlify(pvt_key.exportKey(format='DER')).decode('ascii'), binascii.hexlify(pub_key.exportKey(format='DER')).decode('ascii'))

# Takes in a user's Telegram user ID and returns the Wallet information from the Google NDB if it can be found,
# else it returns an error message indicating that the user does not have a registered wallet.
def get_wallet_info(user_id):
	# The text to return to the user
	return_text = ""

	# Fetch all users
	all_users = User.query().fetch()

	for each_user in all_users:
		# If we find a user ID that matches, retrieve its wallet address
		if (each_user.user_id == str(user_id)):
			all_wallets = Wallet.query().fetch()
			user_wallet_addr = each_user.wallet_addr
			for each_wallet in all_wallets:
				# If this is the wallet that belongs to the user
				if (each_wallet.wallet_addr == user_wallet_addr):
					user_wallet_val = each_wallet.wallet_val

					return_text = "Wallet address: " + str(user_wallet_addr) + "\n" + "Current wallet value: " + str(user_wallet_val) + " CGCoins." + "\n\n" + "Please note: Your wallet value updates approximately every 10 minutes. If your value does not reflect the correct amount, please check back later."

					return return_text

			# We should not reach this part of the code,
			# else that means that we have a user without a wallet
			return_text = "ERROR: This user does not have an associated wallet. Please contact the Capgemini Exchange administrator."

			return return_text

	# If we reach this point, then it means that this user has not registered for a wallet
	# Since we iterate through all users in the database, and cannot find one with a corresponding Telegram user ID
	return_text = "ERROR: You have not yet registered for a CGCoin wallet. Register now with /reg !"

	return return_text

# Takes in a user's Telegram user ID and returns a list of possible users to transfer to, 
# Returns a list of Telegram InlineKeyboardButtons, including a 'Cancel Transaction' button
def get_transferees(transferrer_id):
	# The list of transferees to return to the user
	transferees_list = []

	# Fetch all users
	all_users = User.query().fetch()

	for each_user in all_users:
		# If this is not the user trying to make the transfer
		if (each_user.user_id != str(transferrer_id)):
			# Retrieve the user's name
			transferees_list.append([telegram.InlineKeyboardButton(text=each_user.user_name, callback_data="?~`xfer_wa_add"+each_user.wallet_addr)])

	# # Add in a 'Cancel Transaction' button
	# transferees_list.append([telegram.InlineKeyboardButton(text='Cancel Transaction', callback_data="?~`xfer_wa_add_cancel")])
	
	return telegram.InlineKeyboardMarkup(transferees_list)

# Takes in a user's Telegram user ID and returns a tuple of (True, user's wallet address)
# if the user can be found. Else it returns (False, None).
def get_transferrer_wallet_addr(user_telegram_id):
	# Fetch all users
	all_users = User.query().fetch()

	for each_user in all_users:
		# If this is the user whose wallet address we are looking for
		if (each_user.user_id == str(user_telegram_id)):
			return (True, each_user.wallet_addr)

	return (False, None)

# Takes in a user's Telegram user ID or wallet address, and returns the private chat ID between the user and the bot
def get_user_pvt_chat_id(transferrer_id_or_wa_addr):
	# Fetch all users
	all_users = User.query().fetch()

	for each_user in all_users:
		# If this is the user that we are looking for
		if ((each_user.user_id == str(transferrer_id_or_wa_addr)) or (each_user.wallet_addr == str(transferrer_id_or_wa_addr))):
			return each_user.pvt_chat_id

def get_user_wa_pvt_key(transferrer_wa_addr):
	# Fetch all Wallets
	all_wallets = Wallet.query().fetch()

	for each_wallet in all_wallets:
		# If this is the wallet we are looking for
		if (each_wallet.wallet_addr == str(transferrer_wa_addr)):
			return each_wallet.pvt_key

def get_user_wa_pub_key(transferrer_wa_addr):
	# Fetch all Wallets
	all_wallets = Wallet.query().fetch()

	for each_wallet in all_wallets:
		# If this is the wallet we are looking for
		if (each_wallet.wallet_addr == str(transferrer_wa_addr)):
			return each_wallet.pub_key

def generate_transaction(transferrer_wallet_addr, transferee_wallet_addr, transfer_amt):
	try:
		# Create an OrderedDict of this transaction's details
		unencrypted_xtn = {
			'transferrer_wallet_addr': str(transferrer_wallet_addr),
			'transferee_wallet_addr': str(transferee_wallet_addr),
			'transfer_amt': str(transfer_amt)
		}
		# Create a stringy-fied version of the OrderedDict
		# This is the unencrypted version of the transaction
		unencrypted_xtn_str = str(unencrypted_xtn)

		# Retrieve the user's wallet private key
		transferrer_pvt_key = get_user_wa_pvt_key(transferrer_wallet_addr)	# transferrer_pvt_key is a str
		pvt_key = RSA.importKey(binascii.unhexlify(transferrer_pvt_key))
		# Create a RSA digital signature protocol (PKCS1) with the user's private key
		signer = PKCS1_v1_5.new(pvt_key)
		# Hash the Transaction details
		the_hash = SHA256.new(unencrypted_xtn_str.decode('utf-8'))

		# Retrieve the Task Queue
		xtn_task_queue = taskqueue.Queue('xtn-pull-queue')

		# Create a Transaction task that consists of
		# 1) An encrypted version of the Transaction, i.e. A signed, hash, in unicode
		# 2) An unencrypted version of the Transaction, stringyfied Python dictionary
		xtn_task_queue.add(taskqueue.Task(payload={'encrypted_xtn': str(binascii.hexlify(signer.sign(the_hash)).decode('ascii')), 'un_encrypted_xtn': unencrypted_xtn_str}, method='PULL', tag='cgcoin'))

		return True
	except Exception as e:
		print(e)
		return False

def retrieve_transactions():
	# Initialize a variable to hold the response string
	return_text = "These are the following unverified transactions that have been made:\n\n"

	# Retrieve all existing Transactions
	all_xtns = Transaction.query().fetch()

	for each_xtn in all_xtns:
		encrypted_xtn = each_xtn.encrypted_xtn 	# encrypted_xtn is a str
		un_encrypted_xtn = json.loads(each_xtn.un_encrypted_xtn)

		# Retrieve the unencrypted transaction details
		transferrer_wallet_addr = un_encrypted_xtn["transferrer_wallet_addr"]
		transferee_wallet_addr = un_encrypted_xtn["transferee_wallet_addr"]
		transfer_amt = un_encrypted_xtn["transfer_amt"]

		# Retrieve the transferrer's public key
		transferrer_pub_key = get_user_wa_pub_key(transferrer_wallet_addr)	# transferrer_pub_key is a str
		pub_key = RSA.importKey(binascii.unhexlify(transferrer_pub_key))
		# Create a RSA signature protocol with the public key
		verifier = PKCS1_v1_5.new(pub_key)
		# Hash the unencrypted Transaction
		_recreated_xtn = {
			'transferrer_wallet_addr': str(transferrer_wallet_addr),
			'transferee_wallet_addr': str(transferee_wallet_addr),
			'transfer_amt': str(transfer_amt)
		}
		the_hash = SHA256.new(str(_recreated_xtn).decode('utf-8'))
		# Compare the hash with the signed hash
		# If it is a legitimate Transaction (but not verified with the ledger yet)
		if (verifier.verify(the_hash, binascii.unhexlify(encrypted_xtn))):
			# Write it in the return_text
			return_text = return_text + transfer_amt + " CGCoin(s) was transferred from " + transferrer_wallet_addr + " to " + transferee_wallet_addr + ".\n\n"
		# Else if it is a tampered Transaction
		else:
			return_text = return_text + "The transaction of " + transfer_amt + " CGCoin(s) from " + transferrer_wallet_addr + " to " + transferee_wallet_addr + " was tampered with.\n\n"

	return return_text