all: dict/database.sqlite
dict/database.sqlite: db/schema.sql db/cards.xml
	touch db/expansion.whitelist
	python database.py
clean:
	rm db/database.sqlite
