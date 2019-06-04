import keras
from keras.layers import Conv2D, MaxPooling2D, Input, Dense, Flatten
from keras.models import Model, load_model
import numpy as np
from math import ceil
import sqlite3
import argparse
import os
from PIL import Image
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument('-d', '--database', help="Path To SQLite Database", required=True)
ap.add_argument('-e', '--epochs', help="Number of Epochs To Run", type=int, default=10)
ap.add_argument('-t', '--datetime', help="Autofill Datetime")
ap.add_argument('-l', '--location', help="Autofill Location")
ap.add_argument('-s', '--save', help="Model Save Location", default="models/match.h5")
ap.add_argument('--load', help="Model Load Location", default="models/match.h5")
ap.add_argument('-p', '--progress', help="Training Figure Location", default="match_train_fig.png")
args = vars(ap.parse_args())

def connect():
	conn = sqlite3.connect(args['database'])
	curs = conn.cursor()	
	return conn, curs

def close(conn):
	if not conn: return
	conn.close()

fix_path = lambda p: os.path.join('tiny',p)

batch_size = 32
num_channels = 3
num_classes = 2
epoch_size = 64
s = 64

def get_model():
	face_img = Input(shape=(s,s,num_channels))
	conv_1 = Conv2D(64,(5,5),padding='same',activation='relu')(face_img)
	conv_1 = MaxPooling2D(pool_size=(2,2))(conv_1)
	conv_2 = Conv2D(128,(3,3),padding='same',activation='relu')(conv_1)
	conv_2 = MaxPooling2D(pool_size=(2,2))(conv_2)
	conv_3 = Conv2D(192,(3,3))(conv_2)
	conv_4 = Conv2D(192,(3,3))(conv_3)
	conv_5 = Conv2D(256,(3,3))(conv_4)
	conv_5 = MaxPooling2D(pool_size=(2,2))(conv_4)
	vision_model = Model(face_img, conv_5)

	face_a = Input(shape=(s,s,num_channels))
	face_b = Input(shape=(s,s,num_channels))
	vis_out_a = vision_model(face_a)
	vis_out_b = vision_model(face_b)

	flat_a = Flatten()(vis_out_a)
	flat_b = Flatten()(vis_out_b)
	conc = keras.layers.concatenate([flat_a, flat_b])
	full_1 = Dense(1000,activation='relu')(conc)
	full_2 = Dense(1000,activation='relu')(full_1)
	full_3 = Dense(1,activation='sigmoid')(full_2)
	return Model([face_a, face_b], full_3)

def pathToImg(path):
	img = Image.open(path)
	img.load()
	data = np.asarray(img.resize((s,s)), dtype="float64")/256	
	return data

def sel_data(n=batch_size):
	conn, curs = connect()
	if not curs: return
	rows = curs.execute("select image, userid from records where userid > 0 and frame < 45 order by random() limit ?",(n,)).fetchall()
	rows = [(pathToImg(fix_path(row[0])), row[1]) for row in rows]
	close(conn)
	return rows

def gen_data():
	while True:		
		rows_a = sel_data(batch_size)
		rows_b = sel_data(batch_size)
		pairs = [(rows_a[i][0], rows_b[i][0], 0) if rows_a[i][1] != rows_b[i][1] else (rows_a[i][0], rows_b[i][0], 1) for i in range(len(rows_a))] 
		data = [np.concatenate([[row[0]] for row in pairs],axis=0), np.concatenate([[row[1]] for row in pairs], axis=0)]
		labels = np.array([0 if rows_a[i][1] != rows_b[i][1] else 1 for i in range(len(rows_a))])  
		yield (data,labels)

def test(model):
	if args["datetime"]: datestr = args["datetime"] + "%"
	else: datestr = input("Date (yyyy-mm-dd): ")+"%"
	if args["location"]: loc = args["location"]
	else: loc = input("Location: ")
	conn, curs = connect()
	if not curs: return
	rows = curs.execute("select image, userid from records where loc=? and datetime like ? and userid > 0",(loc,datestr)).fetchall()
	data_rows = [(pathToImg(fix_path(row[0])), [row[1]-1]) for row in rows]
	data = np.concatenate([[row[0]] for row in data_rows],axis=0)
	labels = keras.utils.to_categorical(np.array([row[1] for row in data_rows]), num_classes)
	ret = model.predict(data,batch_size=batch_size)
	print(ret.shape)
	print(ret[0], np.argmax(ret[0]))
	for i, row in enumerate(rows):
		curs.execute("update records set testid=? where image=?", (int(np.argmax(ret[i])+1), row[0])).fetchall()
	conn.commit()
	close(conn)
	return ret
try:
	recog_model = load_model(args["load"])
	print("Loading Saved Model: " + args["load"])
except Exception as e:
	print("Creating New Model due to ", str(e))
	recog_model = get_model() 
	recog_model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

gendata = gen_data()
history = recog_model.fit_generator(gendata,use_multiprocessing=True,steps_per_epoch=ceil(epoch_size/batch_size),epochs=args["epochs"]*50)
#test(recog_model)

print("Saving Model To: " + args["save"])
recog_model.save(args["save"])
plt.plot(history.history['acc'])
plt.title('Model accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Train', 'Test'], loc='upper left')
plt.savefig(args["progress"])
