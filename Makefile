all: dict/cards.pickle
dict/cards.pickle:
	cd dict && $(MAKE)
