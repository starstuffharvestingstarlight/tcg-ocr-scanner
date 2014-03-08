all: mtg.dic mtg.aff cards.pickle
mtg.dic: cards_joined.wordlist
	wc -l cards_joined.wordlist > mtg.dic
	sort cards_joined.wordlist | uniq >> mtg.dic 
mtg.aff:
	touch mtg.aff
cards_joined.wordlist: cards.xml
	./cardsxml2wordlist.py > cards_joined.wordlist
cards.pickle: cards.xml
	./cardsxml2dictpickle.py
