create table product 
-- product that the cards belong to, added for future development
(
	id integer primary key autoincrement not null,
	name text -- e.g., MTG, Android Netrunner
);

create table frame 
-- base settings for the image recognition. this allows the system to 
-- prepare the image based on the cards we're after. at the moment
-- only MtG/new frames are supported but the idea is to have a frame 
-- setting for each frame. for example, a split card could use a different 
-- crop and rotation
(
	id integer primary key autoincrement not null,
	name text,
	ocr_rect text, -- [x, y, w, h]
	normalised_dimensions, -- [w, h]
	product_id integer references product(id),
	unique(name, product_id)
);

create table processor 
-- image processing block, for example, whether we need to invert, grayscale, etc
-- includes the python class to instantiate. this allows us to manage which processing
-- blocks will be on when we set which cards we'll be loading
(
	id integer primary key autoincrement not null,
	class text, -- python class name to instantiate
	description text, -- description of the processor
	unique(class)
);

create table frame_processor 
-- relationship between frames and processor blocks
-- with a sequence number for the order they'll be run
-- e.g.: 1:crop, 2:rgb2grey, ...
(
	id integer primary key autoincrement not null,
	frame_id integer references frame(id),
	processor_id integer references processor(id),
	sequence_number integer,
	unique(frame_id, processor_id, sequence_number)
);

create table card 
-- settings for the card. the ocr_slug is what the ocr will use
-- as a word for the custom dictionary. while it may not be unique, 
-- detecting the full identity of the card (set, name, etc) is not 
-- done yet but this setup allows that in the future. for example,
-- if there are several cards with the same ocr_slug, we can then use
-- some other AI module to decide which set it might be from
(
	id integer primary key autoincrement not null,
	name text,
	ocr_slug text, -- used for tesseract
	ocr_language text, -- used for tesseract
	product_id integer references product(id),
	frame_id integer references frame(id)
);

create table expansion
-- simple card groups
(
	id integer primary key autoincrement not null,
	name text
);

create table card_expansion
-- relationship between cards and groups. since a card isn't only identified
-- by the name, we can use the constraint. depending on how far the detector
-- goes, it would pick out different versions of a card based on the features
-- we're detecting (this happens, for example, with alt art for the same cards)
(
	id integer primary key autoincrement not null,
	card_id integer references card(id),
	expansion_id integer references expansion(id),
	unique(card_id, expansion_id) 
);

