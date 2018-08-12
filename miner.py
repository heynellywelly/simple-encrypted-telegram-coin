from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors
from blockchain import generate_genesis_block, check_genesis_block_valid, generate_next_block, check_blockchain_valid
import webapp2
import logging
import ast

class Wallet(ndb.Model):
	pvt_key = ndb.StringProperty()
	pub_key = ndb.StringProperty()
	wallet_addr = ndb.StringProperty()
	wallet_val = ndb.IntegerProperty()

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

class MinerWorker(webapp2.RequestHandler):
	# task_payload: str
	def verify_transaction(task_payload):
		# Check that the payload is a valid JSON
		try:
			xtn_dict = ast.literal_eval(task_payload)

			# Retrieve all the existing Wallets
			all_wallets = Wallet.query().fetch()

			for each_wallet in all_wallets:
				# If this is the Transferrer for this Transaction
				if (each_wallet.wallet_addr == xtn_dict['transferrer_wallet_addr']):
					# Check if the Transferrer has the amount that they wish to transfer
					xfer_amt = int(xtn_dict['transfer_amt'])

					# If the amount they wish to transfer is greater than the existing Wallet value
					# Reject this Transaction
					if (xfer_amt > each_wallet.wallet_val):
						return False
					# Else, proceed to create the necessary Block and update the Blockchain
					else:
						return generate_next_block(xtn_dict['transferrer_wallet_addr'] + " has transferred " + xtn_dict['transfer_amt'] + " CGCoin(s) to " + xtn_dict['transferee_wallet_addr'] + ".")

		except:
			return False

	def get(self):
		# Retrieve the queue that contains the Transaction tasks
		xtn_queue = taskqueue.Queue('xtn-pull-queue')
		xtn_tasks = None

		try:
			xtn_tasks = xtn_queue.lease_tasks_by_tag(3600, 1000, deadline=300, 'cgcoin')
		except (taskqueue.TransientError, apiproxy_errors.DeadlineExceededError) as e:
			logging.exception(e)
			return

		if (xtn_tasks is not None):
			# Retrieve all Blocks in the Blockchain
			all_blocks = (Blockchain.query().fetch())[0].blocks
			# Check to see if the Blockchain is empty
			# If it is NOT empty
			if (len(all_blocks) != 0):
				# Check that the first block in the chain is a Genesis block
				is_genesis_block = check_genesis_block_valid(all_blocks[0])

				# If the Genesis Block is legitimate, we then proceed to verify the rest of the Blockchain
				if (is_genesis_block):
					is_blockchain_valid = check_blockchain_valid()

					# If the Blockchain is valid, proceed with the creation of the new Block
					if (is_blockchain_valid):
						for each_task in xtn_tasks:
							@ndb.transactional
							is_xtn_valid = verify_transaction(each_task.payload)

							if (is_xtn_valid):
								# Delete the Task
								xtn_tasks.delete_tasks(each_task)
							else:
								# Notify the user (later)
								xtn_tasks.delete_tasks(each_task)

			# Else, this means that the Blockchain is empty
			else:
				# Create a Genesis Block
				genesis_block = generate_genesis_block()
				genesis_block.put()

				# Create the new Block(s) from the Transaction tasks
				for each_task in xtn_tasks:
					@ndb.transactional
					is_xtn_valid = verify_transaction(each_task.payload)

					if (is_xtn_valid):
						# Delete the Task
						xtn_tasks.delete_tasks(each_task)
					else:
						# Notify the user (later)
						xtn_tasks.delete_tasks(each_task)

app = webapp2.WSGIApplication(
	[
		('/blockchain_miner', MinerWorker)
	],
	debug=True
)