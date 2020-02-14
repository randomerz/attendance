import sqlite3
import argparse
from progress.bar import Bar
import cv2 as cv
import os
import json
import sys
from random import randint

ap = argparse.ArgumentParser()
ap.add_argument('-d', '--database', help="Path To SQLite Database", required=False)
ap.add_argument('-t', '--datetime', help="Autofill Datetime")
ap.add_argument('-l', '--location', help="Autofill Location")
ap.add_argument('-n', '--names', help="Use Names", action="store_true", default=False)
ap.add_argument('-o', '--option', help="Override UI", type=int)
ap.add_argument('-f', '--fps', help="Frames Per Second", type=int)
ap.add_argument('-v','--video', help="Input Video For Overlay")
ap.add_argument('-s','--save-video',help="Output Video For Overlay")
args = vars(ap.parse_args())
conn = None
curs = None

def connect():
	global conn, curs
	try:
		conn = sqlite3.connect(args['database'])
		curs = conn.cursor()
		return True
	except:
		print('Error connecting to database! Did you provide one?')	
		return False

def tag(db_curs, datestr, location, compid, userid):
	if not db_curs: return
	curs.execute("update records set userid=? where compid=? and loc=? and datetime like ?", (userid, compid, location, datestr))

def useridToJSON(db_curs, datestr, location):
	if not db_curs: return
	rows = db_curs.execute("select distinct compid, userid from records where loc=? and datetime like ?", (location, datestr)).fetchall()
	return {row[0]: row[1] for row in rows}

def JSONToUserid(db_curs, datestr, location, dic):
	for k in dic: tag(db_curs, datestr, location, int(k), dic[k])

def vis(db_curs, datestr, location, compid):
	os.chdir("tiny")
	if not db_curs: return
	rows = db_curs.execute("select image from records where compid=? and loc=? and datetime like ?", (compid, location, datestr)).fetchall()
	if len(rows) > 10: rows = rows[0:10]
	for row in rows:
		img = cv.imread(row[0])
		cv.imshow("image", img)
		cv.waitKey(250)
	cv.destroyAllWindows()	
	os.chdir('..')

def close(db_cons):
	if not db_cons: return
	db_cons.commit()
	db_cons.close()

def tag_inp(db_curs):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	compid = int(input("Tracking ID: "))
	userid = int(input("User ID: "))
	tag(db_curs, datestr, loc, compid, userid)
	return True

def vis_inp(db_curs):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	compid = int(input("Tracking ID: "))
	vis(db_curs, datestr, loc, compid)
	return True

def reset(db_curs, user=False):
	if not db_curs: return
	try: db_curs.execute("drop table records")
	except: print("Records Table Not Found")
	db_curs.execute("CREATE TABLE records (image text primary key, datetime text, loc text, res int, compid int, userid int, width int, height int, hwratio double, x int, y int, frame int,testid int, confidence float)")	
	if (user): 
		try: db_curs.execute("drop table users")
		except: print("Users Table Not Found")
		db_curs.execute("CREATE TABLE users (userid int primary key, name text)")
	return True

def vis_user(db_curs):
	if not db_curs: return
	rows = db_curs.execute("select * from users")
	for i in rows: print(i)

def add_user(db_curs, userid, name):
	if not db_curs: return
	db_curs.execute("insert into users (userid, name) values (?,?)",(userid,name))

def upd_user(db_curs, userid, name):
	if not db_curs: return
	db_curs.execute("update users set name=? where userid=?",(name,userid))

def toJSON(db_curs):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	fn = input("Filename: ")
	json.dump(useridToJSON(db_curs, datestr, loc),open(fn, 'w'))

def loJSON():
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	fn = input("Filename: ")
	JSONToUserid(datestr, loc, json.load(open(fn, 'r')))
	
def readVideo(fname, n=-1, s=1):
	print("Reading Video", fname)
	vid = []
	cap = cv.VideoCapture(fname)
	i = -1
	while cap.isOpened():
		if len(vid) == n: break
		ret, frame = cap.read()
		if frame is None or frame.shape[0] <= 0 or frame.shape[1] <= 1: break
		i+=1
		if i%s != 0: continue
		vid.append(frame)
		if cv.waitKey(1) & 0xFF == ord('q'): break
	return vid

def getNames(db_curs):
	if not db_curs: return
	rows = db_curs.execute("SELECT userid, name FROM users").fetchall()
	return {i[0]:i[1] for i in rows}

#test_color = lambda c, u, t, b: c if not b else (0,255,0) if t == u else (0,0,255)
def drawBoxes(db_curs, vid, datetime, location, test=False):
	if not db_curs: return
	rows = db_curs.execute("SELECT frame,x,y,width,height,compid,userid,testid,confidence FROM records WHERE loc=? and datetime like ?",(location,datetime)).fetchall()
	colors = {}
	names = getNames()
	ove_color = False
	for f,x,y,w,h,c,u,t,conf in rows:
		if u == -1 and test: 
			ove_color = True
			u = t 
		if u not in colors: colors[u] = (randint(0,255),randint(0,255),randint(0,255))
		vid[f] = cv.rectangle(vid[f], (x, y), (x+w, y+h), test_color(colors[u],u,t,test and not ove_color), 2) 
		vid[f] = cv.putText(vid[f], "Tracking ID: " + str(c),(x,y),cv.FONT_HERSHEY_SIMPLEX,1.0,color=colors[u],thickness=2)
		if not args["names"]: vid[f] = cv.putText(vid[f], "User ID: " + str(u),(x,y+h),cv.FONT_HERSHEY_SIMPLEX,1.0,color=colors[u],thickness=2)
		else: vid[f] = cv.putText(vid[f], names[u],(x,y+h),cv.FONT_HERSHEY_SIMPLEX,1.0,color=colors[u],thickness=2)
		if test: vid[f] = cv.putText(vid[f], str(int(conf*1000)/10)+"%", (x,y+h+22),cv.FONT_HERSHEY_SIMPLEX,1.0,color=colors[u],thickness=2)
	for i in range(len(vid)):
		vid[i] = cv.putText(vid[i], "Frame " + str(i), (0,22),cv.FONT_HERSHEY_SIMPLEX,1.0,color=(0,255,0), thickness=2) 
	return vid

def writeVideo(vid,vfilepath, fps):
	print("Saving Video To", filepath)
	if len(vid) == 0: return
	fourcc = cv.VideoWriter_fourcc(*'DIV3') 
	#fourcc = 0x7634706d
	print(vid[0].shape[0], vid[0].shape[1])
	out = cv.VideoWriter(filepath,fourcc, fps, (vid[0].shape[1],vid[0].shape[0]))
	if not out.isOpened(): print("Video Writer Is Not Opened")
	for frame in vid: out.write(frame)
	out.release()

def dropDay(db_curs):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	if not db_curs: return
	db_curs.execute("DELETE FROM records WHERE loc=? and datetime like ?",(loc,datestr)).fetchall()
	
def overlay(test=False):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	if args["video"]: fname = args["video"]
	else: fname = input("Video To Overlay: ")
	if args["save_video"]: oname = args["save_video"]
	else: oname = input("Video To Output: ")
	if args["fps"]: fps = args["fps"]
	else: fps = int(input("Frames Per Second: "))
	vid = readVideo(fname)
	vid = drawBoxes(vid,datestr,loc,test)
	writeVideo(vid,oname,fps)		
	
if __name__ == "__main__":
	if not connect():
		sys.exit(0)
	print(conn, curs)
	while True:
		if args["option"]: inp = args["option"]  
		else: inp = int(input("0 To Tag\n1 To Visualize\n2 To Reset\n3 To See Registered Users\n4 To Add New User\n5 To Update Existing User\n6 To Save To JSON\n7 To Load JSON\n8 To Overlay Training Data\n9 To Overlay Test Data\n10 To Drop a Day\n11 To Hard Reset\n-1 To Save and Quit\n-2 To Save\nCommand: "))
		if(inp == -1): break 
		elif(inp == -2): conn.commit()
		elif(inp == 0): tag_inp(curs)
		elif(inp == 1): vis_inp(curs)
		elif(inp == 2): reset(curs)
		elif(inp == 3): vis_user(curs)	
		elif(inp == 4): add_user(curs, int(input("User ID: ")), input("User Name: "))	
		elif(inp == 5): upd_user(curs, int(input("User ID: ")), input("User Name: "))	
		elif(inp == 6): toJSON()
		elif(inp == 7): loJSON()
		elif(inp == 8): overlay() 	
		elif(inp == 9): overlay(True)
		elif(inp == 10): dropDay(curs)
		elif(inp == 11): reset(curs, True)
		if args["option"]: break
	close(conn)

