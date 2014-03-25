import pickle

# basic card
class Card(object):
	(slug, name, detected_in) = ('', '', 1000)
	def __init__(self, properties = {}):
		for p in properties:
			setattr(self, p, properties[p])

# card collection
class CardDb(object):
	def __init__(self, options):
		try:
			self.card_db = pickle.load(open('./dict/cards.pickle', 'rb'))
		except Exception:
			print 'No card database found. Try running "make dict" with a cards.xml file in ./dict/'
			exit()
	def exists(self, slug):
		return slug in self.card_db
	def get(self, slug):
		data = self.card_db[slug]
		return Card({'slug':data[0], 'name':data[1], 'expansion': data[2], 'multiverse_id': data[3]})

