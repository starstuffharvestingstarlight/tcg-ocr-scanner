#!/usr/bin/python
import sys
import re
import xml.etree.ElementTree as ET
import pickle

if len(sys.argv) > 1:
  src = sys.argv[1]
else:
  src = "cards.xml"

tree = ET.parse(src)
root = tree.getroot()

carddict = {}
set_name_re = re.compile(r"http://mtgimage.com/setname/([\w\s]+)/.*")
multiverse_id_re = re.compile(r".*multiverseid=(\d+)&.*")
for n in root.findall("./cards/card"):
  try:
    (card_name, set_name, multiverse_id) = (n.find("name").text, "", "")

    card_id = re.sub(r"[^a-zA-Z]+", "", card_name)

    set_node = n.find("set")

    match = set_name_re.match(n.find("set").attrib["picURLHq"])
    if not (match is None):
      set_name = match.group(1)
      #print "set name: %s" % setName

    match = multiverse_id_re.match(n.find("set").attrib["picURL"])
    if not (match is None):
      multiverse_id = match.group(1)
      #print "multiverse id: %s" % multiverse_id
    
    carddict[card_id] = (card_id, card_name, set_name, multiverse_id)
  except Exception: 
    pass

pickle.dump(carddict, open("cards.pickle", "wb"))
