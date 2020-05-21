import keras
from keras.layers import Conv2D, MaxPooling2D, Input, Dense, Flatten
from keras.models import Model, load_model
from spp.SpatialPyramidPooling import SpatialPyramidPooling as SPP
import numpy as np
from math import ceil
###adapted from SPP Github###
batch_size = 64
num_channels = 1
num_classes = 1
epoch_size = 64*2

face_img = Input(shape=(None,None,num_channels))

conv_1 = Conv2D(32,(3,3),padding='same',activation='relu')(face_img)
conv_2 = Conv2D(32,(3,3),activation='relu')(conv_1)
conv_2 = MaxPooling2D(pool_size=(2,2))(conv_2)
conv_3 = Conv2D(64,(3,3),padding='same',activation='relu')(conv_2)
conv_4 = Conv2D(63,(3,3))(conv_3)
conv_4 = SPP([1,2,4])(conv_4)

vision_model = Model(face_img, conv_4)
face_a = Input(shape=(None,None,num_channels))
face_b = Input(shape=(None,None,num_channels))
out_a = vision_model(face_a)
out_b = vision_model(face_b)

conc = keras.layers.concatenate([out_a, out_b])
full_1 = Dense(num_classes,activation='sigmoid')(conc)

try:
	recog_model = load_model('match.h5', custom_objects={'SpatialPyramidPooling':SPP})
	print("Loading Saved Model")
except Exception as e:
	print("Creating New Model due to ", str(e))
	recog_model = Model([face_a, face_b], full_1)
	recog_model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

def gen_pair(s):
	pass	
def gen_data():
	s = 64
	while True:		
		data = [256*np.random.rand(epoch_size, s, s, num_channels) for i in range(2)]
		labels = np.zeros((epoch_size))#,num_classes))
		if s == 64: s = 32
		else: s = 64	
		yield (data,labels)

gendata = gen_data()
recog_model.fit_generator(gendata,use_multiprocessing=True,steps_per_epoch=ceil(epoch_size/batch_size),epochs=1)

recog_model.save('match.h5')

'''conv_1 = Conv2D(32,(3,3),padding='same',activation='relu')(face_img)
conv_1 = MaxPooling2D((2,2))(conv_1)
conv_2 = Conv2D(32,(3,3),padding='same',activation='relu')(conv_1)
conv_2 = MaxPooling2D((2,2))(conv_2)
conv_3 = Conv2D(64,(3,3),padding='same',activation='relu')(conv_2)
conv_4 = Conv2D(64,(3,3),padding='same',activation='relu')(conv_4)
conv_5 = Conv2D(64,(3,3),padding='same',activation='relu')(conv_5)
face_out = SPP([1,2,4])(conv_5)
vision_model = Model(face_img,face_out)
face_a = Input(shape=(None,None,1))
face_b = Input(shape=(None,None,1))
out_a = vision_model(face_a)
out_b = vision_model(face_b)
concatenated = keras.layers.concatenate([out_a, out_b])
out = Dense(1, activation='sigmoid')(concatenated)
classification_model = Model([face_a, face_b], out)
classification_model.compile(optimizer='rmsprop', loss='binary_crossentropy')
model.fit(data, labels)'''
