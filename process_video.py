import argparse
import datetime
import hashlib
import multiprocessing
import os
import sqlite3
import sys
from multiprocessing import pool
from random import random

import matlab.engine

import _pickle as cPickle
import cv2 as cv
import numpy as np
import progressbar  # pip3 install progressbar2
from munkres import Munkres
from progress.bar import Bar

from kivy.graphics.texture import Texture

try:
	from secrets import token_hex
except ImportError:
	from os import urandom
	def token_hex(nbytes=None):
		return urandom(nbytes).hex()

### CMD LINE ARGS ###

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--video',help='Path to Video file')
ap.add_argument('-w', '--webcam',help='Enable WebCam',action="store_true",default=False)
ap.add_argument('-n', '--number-of-frames',type=int,default=-1,help="Maximum Number of Frames To Capture")
ap.add_argument('-s', '--skip-rate',type=int,default=1,help="Skip Rate of Frames")
ap.add_argument('-b', '--boxes',help="Path To Bounding Boxes File")
ap.add_argument('-t', '--track',help="Enable Tracking",action="store_true",default=False)
ap.add_argument('--no-draw', help="Does Not Draw Boxes on Frames", action="store_true", default=False)
ap.add_argument('--no-display',help="Disables Display",action="store_true",default=False)
ap.add_argument('--save-boxes',help="Path To Save Bounding Boxes")
ap.add_argument('--save-video',help="Path To Save Video")
ap.add_argument('-i', '--imagedir', help='Path To Local Image Database')
ap.add_argument('-d', '--database', help='Path To Local SQLite Database')
ap.add_argument('-l', '--location', help="Unique Camera Location")
ap.add_argument('-f', '--fps', type=float, default=20.0, help="Frames Per Second")
args = vars(ap.parse_args())

init = False

widgets = [' [', progressbar.Timer(), '] ', progressbar.Bar(), ' (', progressbar.ETA(), ') ', ]

eng, m = None, None

app = None

#####################

class Box:	
	def __init__(self, vals, i_d=None):
		self.coord = vals
		self.id = i_d
		if vals != None: self.area = abs(vals[2] - vals[0]) * abs(vals[3] - vals[1])
		if self.id == None: self.color = (0, 255, 0)
		else: self.color = (int(255 * random()), int(255 * random()), int(255 * random()))

	def setId(self, i_d, coef=40, color=(0, 255, 0)):
		self.id = i_d
		self.color = color

	def IoU(self, other):
		if self.coord == None or other.coord == None: return .01
		boxA = self.coord
		boxB = other.coord
		xA = max(boxA[0], boxB[0])
		yA = max(boxA[1], boxB[1])
		xB = min(boxA[2], boxB[2])
		yB = min(boxA[3], boxB[3])
		interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
		boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
		boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
		iou = interArea / float(boxAArea + boxBArea - interArea)
		return iou

	def __repr__(self):
		return str(self.coord)

def getImageBoxes(frame):
	fname = 'temp_pics/' + token_hex(6) + '.jpg'
	cv.imwrite(fname, frame)
	cmd = "tiny_face_detector('"+fname+"','"+fname+"',.5,.1,0)"
	bboxes = eng.eval(cmd)
	os.system('rm ' + fname) 
	return bboxes

def showVideo(vid):
	i = 0
	while i < len(vid):
		cv.imshow('Detections',vid[i])
		if cv.waitKey(1) & 0xFF == ord('q'): break
		if i == len(vid) - 1 and int(input("1 To Replay ")) == 1: i = 0
		else: i += 1
	cv.destroyAllWindows()

def readVideo(fname, n=-1, s=1):
	print("Reading Video", fname)
	vid = []
	cap = cv.VideoCapture(fname)
	if not cap:
		print('Warning: video not opened')
	i = -1
	while cap.isOpened():
		if len(vid) == n: break
		ret, frame = cap.read()
		if frame is None or frame.shape[0] <= 0 or frame.shape[1] <= 1: break
		i += 1
		if i % s != 0: continue
		app.console_display_widget.update_texture(frame) # 
		vid.append(frame)
		if cv.waitKey(1) & 0xFF == ord('q'): break
	return vid

def getVideoBoxes(vid):
	print("Computing Video Boxes")
	bar = progressbar.ProgressBar(max_value=len(vid), widgets=widgets)
	boxes = []
	for j, frame in enumerate(vid): 
		bar.update(j)
		boxes.append([Box(i) for i in getImageBoxes(frame)])
	bar.update(len(vid))
	return boxes 

def drawBoxes(vid, boxes):
	for i in range(len(vid)):
		frame = vid[i]
		bboxes = boxes[i]
		for box in bboxes: 
			coords = box.coord
			if coords == None: continue
			frame = cv.rectangle(frame, (int(coords[0]), int(coords[1])), (int(coords[2]), int(coords[3])), box.color, 2)

def match(prev, curr, runid, frame=0):
	lc = len(curr)
	lp = len(prev)
	print('lp', lp, 'lc', lc)
	if lc < lp: 
		curr += [Box(None) for i in range(0,lp-lc)] # Old Faces Not Detected
	elif lp < lc: # New Faces Detected
		runid += lc - lp
		prev += [Box(None, runid - i) for i in range(0, lc - lp)]
	cmat = [[-1 * c.IoU(p) for p in prev] for c in curr]
	matches = m.compute(cmat)
	for c, p in matches: 
		curr[c].setId(prev[p].id, color=prev[p].color)
	curr = curr[0:lc]
	prev = prev[0:lp]
	return runid, curr, prev
	
def track(boxes, baseid=0):
	print("Tracking Faces")
	if len(boxes) == 0: return
	bboxes = boxes[0]
	maxid = len(boxes[0])
	for i in range(len(bboxes)):
		bboxes[i].setId(i + baseid, color=(int(255 * random()), int(255 * random()), int(255 * random())))
	runid = baseid + len(bboxes)
	for i in range(1, len(boxes)): 
		runid, boxes[i], boxes[i - 1] = match(prev=boxes[i - 1], curr=boxes[i], runid=runid, frame=i)
	print("Found", runid - baseid, "Unique Faces")
	return runid
	
def readWebCam(n=-1, s=1):
	DCS_IP = "198.38.18.121"#"192.168.1.29"
	userauth = ('admin', 'pass098')
	streamurl = "http://" + ':'.join(userauth) + '@' + DCS_IP + "/video/mjpg.cgi?type=.mjpg" 
	return readVideo(streamurl, n, s)

def readBoxes(filepath):
	print("Reading Boxes From", filepath)
	return cPickle.load(open(filepath, 'rb'))

def writeBoxes(boxes, filepath):
	print("Saving Boxes To", filepath)
	cPickle.dump(boxes, open(filepath,'wb'))

def writeVideo(vid, filepath):
	print("Saving Video To", filepath)
	if len(vid) == 0: return
	#fourcc = cv.VideoWriter_fourcc(*'DIV3') 
	fourcc = 0x7634706d
	print(vid[0].shape[0], vid[0].shape[1])
	out = cv.VideoWriter(filepath, fourcc, args["fps"], (vid[0].shape[1], vid[0].shape[0]))
	if not out.isOpened(): print("Video Writer Is Not Opened")
	for frame in vid: out.write(frame)
	out.release()

def cropImage(frame, bboxes, imagedir, camid, cursor, i):
	if camid not in os.listdir(imagedir): os.system('mkdir "' + os.path.join(imagedir,camid) + '"') #Fix Broken Path
	date = str(datetime.datetime.today()).split(' ')[0]	#Get Date
	if date not in os.listdir(os.path.join(imagedir,camid)): os.system('mkdir "' + os.path.join(imagedir,camid,date) + '"') #Fix Broken Path
	boxcount = 0
	for box in bboxes:
		if box.coord == None: continue
		print('a')
		if box.id == None: continue
		boxcount += 1
		crop_img = frame[int(box.coord[1]):int(box.coord[3]), int(box.coord[0]):int(box.coord[2])] 
		if str(box.id) not in os.listdir(os.path.join(imagedir, camid, date)): 
			os.system('mkdir "' + os.path.join(imagedir, camid, date, str(box.id)) + '"') #Fix Broken Path
		tod = datetime.datetime.today()
		impath = os.path.join(imagedir, camid, date, str(box.id), str(tod) + ".jpg")
		cv.imwrite(impath, crop_img)
		w = int(box.coord[2] - box.coord[0])
		h = int(box.coord[3] - box.coord[1])
		if cursor: 
			cursor.execute("insert into records values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(impath,str(tod),camid,crop_img.size,box.id,-1,w,h,int(h/w*100)/100,int(box.coord[0]),int(box.coord[1]),i,-1,-1))
	print('Added %i boxes to database' % boxcount)

def cropVideo(vid,bboxes,imagedir,camid,sql=None):
	print("Generating Raw Image Database")	
	bar = Bar('Cropping Frames', max=len(vid))
	print("Generating SQLite Database")
	conn = sqlite3.connect(sql)
	c = conn.cursor()
	for i in range(len(vid)): 
		cropImage(vid[i], bboxes[i], imagedir, camid, c, i)
		bar.next()
	bar.finish()
	conn.commit()
	conn.close()

def endProgram(msg = None):
	if msg: print(msg)
	sys.exit()

def debug(boxes):
	for i in range(len(boxes)): 
		print(len(boxes[i]), end=" ")
		stp = len(boxes[i])
		for j in range(len(boxes[i])):
			if boxes[i][j].coord == None:
				stp = j
				break
			print(j, end = " ")
		print("|", stp)
		boxes[i] = boxes[i][0:stp]

def detect_faces_video(file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames):
	global init, eng, m

	capture = cv.VideoCapture(0)
	ret, frame = capture.read()
	capture.release()

	buf1 = cv.flip(frame, 0)
	buf = buf1.tostring()
	texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr') 
	texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
	app.console_display_widget.img.texture = texture1
	return
	frame=None
	# app.console_display_widget.update_texture(frame)

	print(app, app.console_display_widget, app.console_display_widget.label, app.console_display_widget.label.text)
	app.console_display_widget.label.text = "temp"

	if not init:
		os.chdir("tiny")
		print("Changed Working Directory To Tiny")

		if not args['boxes']: 
			eng = matlab.engine.start_matlab()
			print("Matlab Engine Spun Up")
		m = Munkres()

		init = True
	
	app.console_display_widget.label.text = "spun up"


	vid = readVideo(os.path.join('..', file_path), num_frames) #, skip_rate)
	print("Read video of size", len(vid), "given maximum number of frames =", num_frames, "and skip rate =", '1', "frames")

	boxes = getVideoBoxes(vid)
	if track_faces:
		track(boxes)
	writeBoxes(boxes, os.path.join('..', save_boxes_path))

	cropVideo(vid, boxes, os.path.join('..', image_dir), location, os.path.join('..', db_path))

	writeVideo(vid, os.path.join('..', save_vid_path))

if __name__ == "__main__":
	# Init stuff #
	print('Imported External Libraries')

	os.chdir("tiny")
	print("Changed Working Directory To Tiny")
	if not args['boxes']: 
		eng = matlab.engine.start_matlab()
		print("Matlab Engine Spun Up")
	m = Munkres()


	if args['webcam']: vid = readWebCam(args["number_of_frames"], args["skip_rate"])
	elif args['video']: vid = readVideo(os.path.join('..',args["video"]),args["number_of_frames"], args["skip_rate"])
	else: endProgram("No Video Input Given. Use the --video or --webcam flags to provide video input.")
	print("Read video of size", len(vid), "given maximum number of frames =", args["number_of_frames"], "and skip rate =", args["skip_rate"], "frames")
	
	if args["boxes"]: boxes = readBoxes(os.path.join('..',args["boxes"]))
	else: boxes = getVideoBoxes(vid) 
	if args["track"]: track(boxes)
	else: print("Tracking Disabled")
	if args["save_boxes"]: writeBoxes(boxes,os.path.join('..',args["save_boxes"]))
	else: print("Saving Boxes Disabled")
	
	if not args["location"]: print("No location input Given. Use the --location flag to provide the location of the camera. Database generation disabled.")
	elif not args["imagedir"]: print("No Image Database Directory Given. Use the --imagedir flag to provide the location of the raw image database. Database generation disabled.")
	elif not args["database"]: print("No SQLite Database Given. Use the --database flag to provide the location of the SQLite Database. Database generation disabled.")
	else: cropVideo(vid, boxes, os.path.join('..',args["imagedir"]), args["location"], os.path.join('..',args["database"]))
	
	if not args["no_draw"]: drawBoxes(vid,boxes)
	else: print("Drawing Disabled")
	if args["save_video"]: writeVideo(vid,os.path.join('..',args["save_video"])) 
	else: print("Saving Video Disabled")
	if not args["no_display"]: showVideo(vid)
	else: print("Display Disabled")
