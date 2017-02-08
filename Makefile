all: dict/database.sqlite
dict/database.sqlite: db/schema.sql db/cards.xml
	touch db/expansion.whitelist
	python database.py
train: train/AllSets.json
	python train/train-data-downloader.py
train/AllSets.json: train/AllSets.json.zip
	unzip train/AllSets.json.zip -d train
train/AllSets.json.zip:
	wget http://mtgjson.com/json/AllSets.json.zip -O train/AllSets.json.zip
clean:
	rm db/database.sqlite
