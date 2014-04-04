create table product 
-- product that the cards belong to, added for future development
(
	id integer primary key autoincrement not null,
	name text -- e.g., MTG, Android Netrunner
);

insert into product
(id, name)
values
(1, 'MtG'),
(2, 'A:NR');

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

insert into frame
(id, name, ocr_rect, normalised_dimensions, product_id)
values
(1, 'New Frame', '', '', 1),
(2, 'Old Frame', '', '', 1);

create table processor 
-- image processing block, for example, whether we need to invert, greyscale, etc
-- includes the python class to instantiate. this allows us to manage which processing
-- blocks will be on when we set which cards we'll be loading
(
	id integer primary key autoincrement not null,
	class text, -- python class name to instantiate
	description text, -- description of the processor
	unique(class)
);
insert into processor
(id, class, description)
values
(1, 'CropProcessor', 'Crops to the frame rectangle'),
(2, 'GreyscaleProcessor', 'Converts image to greyscale'),
(3, 'InvertProcessor', 'Converts image to greyscale');

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

insert into frame_processor
(frame_id, processor_id, sequence_number)
values
(1, 1, 1),
(1, 2, 2);

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
	ocr_language text, -- used for tesseract (see man 1 tesseract)
	vendor_id text, -- used for the vendor code if card has one
	product_id integer references product(id),
	frame_id integer references frame(id),
	unique(ocr_slug, ocr_language, product_id, frame_id)
);

create table expansion
-- simple card groups
(
	id integer primary key autoincrement not null,
	name text,
	product_id integer references product(id),
	unique(name)
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

