from google.appengine.ext import ndb
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import datetime
import binascii
import os

'''
This file contains the methods required for building and verifying the Blockchain
'''

global current_mining_difficulty
current_mining_difficulty = int(os.environ['BLOCK_GEN_INTERVAL']) * int(os.environ['DIFFICULTY_ADJ_INTERVAL'])

class Block(ndb.Model):
	index = ndb.IntegerProperty()
	block_hash = ndb.StringProperty()
	prev_block_hash = ndb.StringProperty()
	timestamp = ndb.DateTimeProperty()
	data = ndb.StringProperty()
	difficulty = ndb.IntegerProperty()
	nonce = ndb.IntegerProperty()

class Blockchain(ndb.Model):
	blocks = ndb.StructuredProperty(Block, repeated=True)

# def is_timestamp_valid(new_block, prev_block):
# 	return ((prev_block.timestamp - new_block.timestamp).total_seconds() < 60) and (new_block.timestamp - datetime.datetime.now() < 60)

def get_adjusted_difficulty(the_latest_block, the_blockchain):
	prev_adj_block = the_blockchain[len(the_blockchain) - int(os.environ['DIFFICULTY_ADJ_INTERVAL'])]
	expected_time = int(os.environ['BLOCK_GEN_INTERVAL']) * int(os.environ['DIFFICULTY_ADJ_INTERVAL'])
	time_taken = the_latest_block.timestamp - prev_adj_block.timestamp

	if (time_taken < (expected_time / 2)):
		return prev_adj_block.difficulty + 1
	elif (time_taken > (expected_time * 2)):
		return prev_adj_block.difficulty - 1
	else:
		return prev_adj_block.difficulty

def get_mining_difficulty():
	# Retrieve the latest Block from the Blockchain
	the_blockchain = (Blockchain.query().fetch())[0].blocks
	latest_block = the_blockchain[len(the_blockchain) - 1]

	if ((latest_block.index % int(os.environ['DIFFICULTY_ADJ_INTERVAL']) == 0) and (latest_block.index != 0)):
		return get_adjusted_difficulty(latest_block, the_blockchain)
	else:
		return latest_block.difficulty

def calculate_block_hash(block_index, previous_block_hash, block_timestamp, block_data, block_difficulty, block_nonce):
	return SHA256.new(str(block_index) + str(previous_block_hash) + str(block_timestamp) + str(block_data) + str(block_difficulty) + str(block_nonce)).hexdigest()

def generate_genesis_block():
	genesis_block = Block(
		index=0, 
		block_hash='2A7137BBB6D1C20EBF160C4715965CBE335082895BD46A088FC16512F203CB9C',
		prev_block_hash=None,
		timestamp=datetime.datetime(1992, 9, 9),
		data='The Genesis Block of the CGCoin',
		difficulty=current_mining_difficulty,
		nonce=0
	)

	return genesis_block

def check_genesis_block_valid(block_to_check):
	genesis_block = Block(
		index=0, 
		block_hash='2A7137BBB6D1C20EBF160C4715965CBE335082895BD46A088FC16512F203CB9C',
		prev_block_hash=None,
		timestamp=datetime.datetime(1992, 9, 9),
		data='The Genesis Block of the CGCoin',
		difficulty=current_mining_difficulty,
		nonce=0
	)

	if (genesis_block.index != block_to_check.index):
		return False

	if (genesis_block.block_hash != block_to_check.block_hash):
		return False

	if (genesis_block.prev_block_hash != block_to_check.prev_block_hash):
		return False

	if (genesis_block.timestamp != block_to_check.timestamp):
		return False

	if (genesis_block.data != block_to_check.data):
		return False

	if (genesis_block.difficulty != block_to_check.difficulty):
		return False

	if (genesis_block.nonce != block_to_check.nonce):
		return False

	if (not(check_block_structure_valid(genesis_block))):
		return False

	return True

def check_block_valid(new_block, prev_block):
	# Check if the previous block's index is exactly 1 less than the new block's
	if (prev_block.index + 1 != new_block.index):
		return False

	# Check if the previous block's hash matches the new block's previous hash
	if (prev_block.block_hash != new_block.prev_block_hash):
		return False

	# Check if the new block's hash is valid
	if (calculate_block_hash(new_block) != new_block.hash):
		return False

	# Check if the new block's difficulty is valid
	if (new_block.difficulty != current_mining_difficulty):
		return False

	# Check if the new block's structure is valid
	if (not(check_block_structure_valid(new_block))):
		return False

	return True

def check_block_structure_valid(the_block):
	# Check if all types of the Block's attributes are valid types
	return (type(the_block.index) == int) and (type(the_block.block_hash) == str) and (type(the_block.prev_block_hash) == str) and (type(the_block.timestamp) == datetime.datetime) and (type(the_block.data) == str) and (type(the_block.difficulty) == int) and (type(the_block.nonce) == int)

def check_blockchain_valid():
	# Retrieve the Blockchain
	the_blockchain = (Blockchain.query().fetch())[0].blocks

	# Check to see if the Genesis Block is valid
	if (not(check_genesis_block_valid(the_blockchain[0]))):
		return False

	# Check the validity of every Block in the chain, apart from the Genesis Block
	for i in range(1, len(the_blockchain)):
		if (not(check_block_valid(the_blockchain[i], the_blockchain[i - 1]))):
			return False

	return True

# the_hash: str
# difficulty: int
def hash_matches_difficulty(the_hash, difficulty):
	hash_in_binary = binascii.unhexlify(the_hash)
	# Ensure that difficulty is an integer
	if (type(difficulty) == int):
		req_prefix = binascii.unhexlify('0' * difficulty)

		if (hash_in_binary[:len(req_prefix)] == req_prefix):
			return True

	return False

def generate_next_block(block_data):
	current_mining_difficulty = get_mining_difficulty()

	# Retrieve the latest Block
	the_blockchain = (Blockchain.query().fetch())[0].blocks
	latest_block = the_blockchain[len(all_blocks) - 1]

	next_index = latest_block.index + 1
	next_timestamp = datetime.datetime.now()

	_curr_nonce = 0

	while True:
		next_hash = calculate_block_hash(next_index, latest_block.block_hash, next_timestamp, block_data, current_mining_difficulty, _curr_nonce)

		if (hash_matches_difficulty(next_hash, current_mining_difficulty)):
			new_block = Block(
				index=next_index,
				block_hash=next_hash,
				prev_block_hash=latest_block.block_hash,
				timestamp=next_timestamp,
				data=block_data,
				difficulty=current_mining_difficulty,
				nonce=_curr_nonce
			)

			# Update the Blockchain
			the_blockchain = (Blockchain.query().fetch())[0].blocks
			the_blockchain.append(new_block)
			the_blockchain.put()

			return True

		_curr_nonce += 1