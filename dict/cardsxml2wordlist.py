#!/usr/bin/python
import sys
import re
import xml.etree.ElementTree as ET

if len(sys.argv) > 1:
  src = sys.argv[1]
else:
  src = "cards.xml"

tree = ET.parse(src)
root = tree.getroot()
for n in root.findall("./cards/card"):
  try:
    print re.sub(r"[^a-zA-Z]+", "", n.find("name").text)
  except Exception: 
    pass
