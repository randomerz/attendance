import sqlite3
import argparse
from progress.bar import Bar
import cv2 as cv
import os
import json

#
# Python
#

#'''
print('zzzzzzzzzzzzzzzz')
ap = argparse.ArgumentParser()
ap.add_argument('-d', '--database', help="Path To SQLite Database", required=True) # temporary, search directory for databases instead
ap.add_argument('-v','--video', help="Input Video For Overlay")
args = vars(ap.parse_args())
conn = None
curs = None
print(args)

try:
	conn = sqlite3.connect(args['database'])
	curs = conn.cursor()
	for i in curs.execute('select * from users'):
		print(i)
except Exception as e:
	print('Error!')
	print(e)