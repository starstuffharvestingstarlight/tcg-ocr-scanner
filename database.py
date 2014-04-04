import os
import sys
import re
import xml.etree.ElementTree as ET
import sqlite3

# basic card
class Card(object):
	(slug, name, expansion, vendor_id, detected_in) = ('', '', '', '', 1000)
	def __init__(self, properties = {}):
		for p in properties:
			setattr(self, p, properties[p])
	def __str__(self):
		return "%s from %s (%s/%s)" % (self.name, self.expansion, self.slug, self.vendor_id)

# card collection
class CardDb(object):
	db_path = './db/database.sqlite'
	db_schema = './db/schema.sql'
	source_xml = './db/cards.xml'
	source_whitelist = './db/expansion.whitelist'
	target_dict_prefix = './db/tcg'
	card_db = {}

	def __init__(self, options, logger=None):
		if not os.path.exists(self.db_path) and options.rebuild_db:
			if logger:
				logger.log('Creating DB')
			self.build()
		
		if options.expansions:
			expansions = options.expansions
		elif os.path.exists(self.source_whitelist):
			with open(self.source_whitelist, 'rt') as whitelist:
				expansions = whitelist.read().strip().split('\n')
		else:
			expansions = []
		if logger:
			logger.log('Limiting DB to %s' % expansions)
		self.update_db(expansions, options.rebuild_db, True)

	def build(self):
		with sqlite3.connect(self.db_path) as connection:
			with open(self.db_schema, 'rt') as schema_file:
				schema = schema_file.read()
				connection.executescript(schema)

			root = ET.parse(self.source_xml).getroot()
			if root is not None:
				vendor_id_re = re.compile(r'.*multiverseid=(\d+)&.*')

				for n in root.findall('./cards/card'):
					try:
						(card_name, set_name, vendor_id) = (n.find('name').text, '', '')

						ocr_slug = re.sub(r'[^a-zA-Z]+', '', card_name)

						match = vendor_id_re.match(n.find('set').attrib['picURL'])
						if match is not None:
							vendor_id = match.group(1)

						for sn in n.findall('./set'):
							self.add(Card({
								'slug':ocr_slug,
								'name':card_name,
								'expansion':sn.text,
								'vendor_id':vendor_id
							}))

					except Exception:
						pass

	def update_db(self, expansions, dictionary=False, card_db=False):
		if dictionary or card_db:
			with sqlite3.connect(self.db_path) as connection:
				c = connection.cursor()
				sql = (
					# eventually, maybe multiple dicts per lang too?
					'select ocr_slug, c.name, e.name, c.vendor_id '
					'from card c '
					'inner join card_expansion ce on c.id = ce.card_id '
					'inner join expansion e on ce.expansion_id = e.id '
					'where c.frame_id = 1 ' # TODO
						'and c.product_id = 1 ' # TODO
						'and e.name in (%s) '
					'group by ocr_slug '
					'order by ocr_slug asc'
				) % (','.join(['?'] * len(expansions)))
				c.execute(sql, expansions)
				card_data = c.fetchall()

				if dictionary:
					with open('%s.dic' % self.target_dict_prefix, 'wt') as dictfile:
						dictfile.write(
							'%d\n%s\n' % (len(card_data), '\n'.join([card[0] for card in card_data]))
						)
					with open('%s.aff' % self.target_dict_prefix, 'wt') as afffile:
						afffile.write('')

				if card_db:
					for card in card_data:
						self.card_db[card[0]] = card

	def add(self, card):
		with sqlite3.connect(self.db_path) as c:
			try:
				sql = 'insert or ignore into expansion (name, product_id) values (?, ?)'
				c.execute(sql, [card.expansion, 1]) # TODO

				sql = (
					'insert or ignore into card '
					'(name, ocr_slug, ocr_language, vendor_id, product_id, frame_id) '
					'values '
					'(?, ?, ?, ?, ?, ?)'
				)
				c.execute(sql, [card.name, card.slug, 'eng', card.vendor_id, 1, 1]) # TODO

				sql = (
					'insert or ignore into card_expansion (card_id, expansion_id) '
					'select card.id, expansion.id '
					'from card, expansion '
					'where card.name = ? '
						'and ocr_language = ? '
						'and card.product_id = ? '
						'and frame_id = ? '
						'and expansion.name = ?'
				)
				c.execute(sql, [card.name, 'eng', 1, 1, card.expansion]) # TODO

				c.commit()
			except Exception as e:
				print 'Exception: %s' % e
				c.rollback()

	def exists(self, slug):
		return slug in self.card_db

	def get(self, slug):
		# TODO: return self.card_db[slug]
		data = self.card_db[slug]
		return Card({
			'slug':data[0],
			'name':data[1],
			'expansion': data[2],
			'vendor_id': data[3]
		})

class Options(object):
	def __init__(self):
		self.expansions = []
		self.logger = self
		self.rebuild_db = True
	def log(self, msg):
		print msg

if __name__ == '__main__':
	print 'Loading db. This might take a while.'
	db = CardDb(Options())
	print 'Fetching test card'
	print db.get('GitaxianProbe')
