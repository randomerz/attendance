import os
import sqlite3
import subprocess
import sys
import threading

import cv2
import db_manager
import process_video
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.properties import (BooleanProperty, NumericProperty, ObjectProperty,
							 ReferenceListProperty, StringProperty)
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.uix.video import Video
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.widget import Widget

#
# Python
#

color_blue = '00ddff'

db_cons, db_curs, db_names = [], [], []
try:
	# finding db files
	db_paths = []
	for root, dirs, files in os.walk('records'):
		for file in files:
			if '.db' in file: # TO DO: check if .db is at the end of file name, not just part of file
				db_paths.append(os.path.join(root, file))
				db_names.append(file[:-3])
	# connect to dbs
	for i in range(len(db_paths)):
		db_cons.append(sqlite3.connect(db_paths[i]))
		db_curs.append(db_cons[i].cursor())
		# for i in db_curs[i].execute('select * from users'):
		# 	print(i)
except Exception as e:
	print('Error!')
	print(e)

#
# Kivy
#

#
# Content and Sidebars
#

class MainContainer(BoxLayout):
	player = ObjectProperty(None)


class SideContainer(BoxLayout):
	side_content = ObjectProperty(None)


class StudentSidebar(BoxLayout):
	pass


class StudentMain(TabbedPanel):
	class_tabs = []

	def __init__(self, **kwargs):
		super(StudentMain, self).__init__(**kwargs)

		self.default_tab_text = 'Welcome!'
		self.default_tab.content = Label(text='Welcome to CATsys!')
		
		for i in range(len(db_curs)):
			tab = TabbedPanelHeader(text=db_names[i])#(text='Class %i' % (i + 1))
			tab.content = StudentList(i)
			self.class_tabs.append(tab)
			self.add_widget(tab)


class VideoSidebar(BoxLayout):
	recorded_layout = ObjectProperty(None)
	live_layout = ObjectProperty(None)
	video_main = None

	cur_mode = 'recorded'
	toggle_string = StringProperty('Use recorded video\n(Click to toggle)')
	toggle_source_string = StringProperty('Toggle Source (0)')

	def __init__(self, **kwargs):
		super(VideoSidebar, self).__init__(**kwargs)
		self.live_layout.size_hint_y = 0
		self.live_layout.height = '0dp'
		self.live_layout.opacity = 0
		self.recorded_layout.size_hint_y = 1
		self.recorded_layout.opacity = 1

		dropdown = DropDown()
		for i in range(8):
			btn = Button(text='Source %d' % i, size_hint_y=None, height=44)
			btn.bind(on_release=lambda btn: dropdown.select(btn.text))
			dropdown.add_widget(btn)
			
		main_button = Button(text='Source 0', size_hint=(None, None))
		main_button.bind(on_release=dropdown.open)
		dropdown.bind(on_select=lambda instance, x: setattr(main_button, 'text', x))
		#self.live_layout.clear_widgets()
		#self.live_layout.add_widget(dropdown)
	
	def toggle_video_mode(self):
		self.video_main.toggle_video_mode()

		if self.cur_mode == 'recorded':
			self.toggle_string = 'Use live video\n(Click to toggle)'
			self.cur_mode = 'live'
			self.recorded_layout.size_hint_y = 0
			self.recorded_layout.height = '0dp'
			self.recorded_layout.opacity = 0
			self.live_layout.size_hint_y = 1
			self.live_layout.opacity = 1

		elif self.cur_mode == 'live':
			self.toggle_string = 'Use recorded video\n(Click to toggle)'
			self.cur_mode = 'recorded'
			self.live_layout.size_hint_y = 0
			self.live_layout.height = '0dp'
			self.live_layout.opacity = 0
			self.recorded_layout.size_hint_y = 1
			self.recorded_layout.opacity = 1

	def toggle_source(self):
		self.video_main.toggle_camera_source()
		self.toggle_source_string = 'Toggle Source (%s)' % self.video_main.cur_source

	def pause_live(self):
		self.video_main.player.play = not self.video_main.player.play


class VideoMain(BoxLayout):
	player = ObjectProperty(None)

	cur_source = 0
	cam0 = None
	cam1 = None
	cur_mode = 'recorded'
	
	def toggle_video_mode(self):
		if self.cur_mode == 'recorded':
			self.cur_mode = 'live'
			if self.cur_source == 0:
				if not self.cam0:
					self.cam0 = Camera(index=0, resolution=(640,480))
				self.player = self.cam0
			elif self.cur_source == 1:
				if not self.cam1:
					self.cam1 = Camera(index=1, resolution=(640,480))
				self.player = self.cam1

		elif self.cur_mode == 'live':
			self.cur_mode = 'recorded'
			self.player = VideoPlayer()

		self.clear_widgets()
		self.add_widget(self.player)

	def toggle_camera_source(self):
		self.cur_source = (self.cur_source + 1) % 2
		if self.cur_source == 0:
			if not self.cam0:
				self.cam0 = Camera(index=0, resolution=(640,480))
			self.player = self.cam0
		elif self.cur_source == 1:
			if not self.cam1:
				self.cam1 = Camera(index=1, resolution=(640,480))
			self.player = self.cam1
		self.clear_widgets()
		self.add_widget(self.player)



class TrainSidebar(BoxLayout):
	pass


class TrainMain(BoxLayout):
	pass


#
# Sidebar Widgets
#

class StudentList(ScrollView):
	student_widgets = []
	selected_index = -1
	layout = None

	def __init__(self, db_index, **kwargs):
		super(StudentList, self).__init__(**kwargs)

		self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=10)
		# in case of no elements
		self.layout.bind(minimum_height=self.layout.setter('height'))

		for i in db_curs[db_index].execute('select * from users'):
			s = CreateClassStudentWidget(size_hint_y=None, height=40)
			s.index = len(self.student_widgets)
			s.parent_list = self
			s.name = str(i[0]) + '. ' + i[1].strip()
			self.student_widgets.append(s)
			self.layout.add_widget(s)

		self.clear_widgets()
		# add gridlayout with all the elements to scroll view (SV can only have 1 widget)
		self.add_widget(self.layout)
		

	def select(self, index):
		for i in self.student_widgets:
			i.selected = False

		# already selected the same label
		if self.selected_index == index:
			self.selected_index = -1
		else:
			self.selected_index = index
			for i in self.student_widgets:
				i.selected = False
			self.student_widgets[index].selected = True
		return True


#
# Content Support Widgets
#

class StudentElement(BoxLayout):
	student_label = StringProperty('TEMP')


class ConsoleDisplayWidget(BoxLayout):
	img = Image()
	label = Label(height=40, size_hint_y=None)

	def __init__(self, **kwargs):
		super(ConsoleDisplayWidget, self).__init__(**kwargs)

		self.add_widget(self.img)
		self.add_widget(self.label)
		self.label.text = 'Started!'


	def update_texture(self, frame):
		# updates image with a cv2 image
		buf1 = cv2.flip(frame, 0)
		buf = buf1.tostring()
		texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr') 
		texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
		self.img.texture = texture1


#
# Dialogue
#

class ConfirmDialog(FloatLayout):
	message = StringProperty('Are you sure you want to do this?')
	ok = ObjectProperty(None)
	cancel = ObjectProperty(None)


class LoadFileDialog(FloatLayout):
	load = ObjectProperty(None)
	cancel = ObjectProperty(None)


class LoadDetectDialog(FloatLayout):
	submit = ObjectProperty(None)
	cancel = ObjectProperty(None)


class CreateClassDialog(FloatLayout):
	create = ObjectProperty(None)
	cancel = ObjectProperty(None)
	list_widget = ObjectProperty(None)
	text_student_name = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(CreateClassDialog, self).__init__(**kwargs)

		# allow for enter key to submit forms
		self.list_widget.text_student_name = self.text_student_name


#
# Other Widgets
#

class CreateClassListWidget(ScrollView):
	student_widgets = []
	selected_index = -1
	layout = None

	text_student_name = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(CreateClassListWidget, self).__init__(**kwargs)

		self.layout = GridLayout(cols=1, spacing=5, size_hint_y=None, padding=5)
		self.layout.bind(minimum_height=self.layout.setter('height'))

		self.clear_widgets()
		self.add_widget(self.layout)

		# if enter is pressed
		Window.bind(on_key_down=self._on_keyboard_down)
		Window.bind(on_key_up=self._on_keyboard_up)

	def _on_keyboard_down(self, instance, keyboard, keycode, text, modifiers):
		if self.text_student_name.focus and keycode == 40:  # 40 - Enter key pressed
			self.add_student(self.text_student_name.text)
			self.text_student_name.text = ''

	def _on_keyboard_up(self, instance, keyboard, keycode):
		if self.text_student_name.focus and keycode == 40:  # 40 - Enter key pressed
			self.text_student_name.text = ''

	def add_student(self, name):
		if name.strip() != '':
			s = CreateClassStudentWidget(size_hint_y=None, height=40)
			s.index = len(self.student_widgets)
			s.parent_list = self
			s.name = name.strip()
			self.student_widgets.append(s)
			self.layout.add_widget(s)

	def remove_student(self):
		if 0 <= self.selected_index < len(self.student_widgets):
			print('removing', self.selected_index)
			for i in range(self.selected_index, len(self.student_widgets)):
				self.student_widgets[i].index = self.selected_index + i - 2
			self.layout.remove_widget(self.student_widgets.pop(self.selected_index))
			self.selected_index = -1


	def select(self, index):
		for i in self.student_widgets:
			i.selected = False

		# already selected the same label
		if self.selected_index == index:
			self.selected_index = -1
		else:
			self.selected_index = index
			for i in self.student_widgets:
				i.selected = False
			self.student_widgets[index].selected = True
		return True


class CreateClassStudentWidget(BoxLayout):
	index = None
	selected = BooleanProperty(False)
	selectable = BooleanProperty(True)
	parent_list = None

	name = StringProperty('TEMP')

	def on_touch_down(self, touch):
		if self.collide_point(*touch.pos) and self.selectable:
			return self.parent_list.select(self.index)

#
# Main App
#

class AttendanceApp(App):
	main_cont = None
	side_cont = None
	
	tab = 0
	student_main = None
	student_side = None
	video_main = None
	video_side = None
	train_main = None
	train_side = None

	side_student_string = StringProperty('[color=%s]Student[color=%s]' % (color_blue, color_blue))
	side_attendence_string = StringProperty('Attendence')
	side_train_string = StringProperty('Train')

	video_file_path = ''
	confirmation_func = None

	detect_faces_thread = None


	def build(self):
		Window.bind(on_dropfile=self._on_file_drop) # makes thing really slow i think in windows
		self.student_main = StudentMain()
		self.student_side = StudentSidebar()
		self.video_main = VideoMain()
		self.video_side = VideoSidebar()
		self.train_main = TrainMain()
		self.train_side = TrainSidebar()

		self.video_side.video_main = self.video_main

		self.main_cont = MainContainer(size_hint_x=.75)
		self.main_cont.add_widget(self.student_main)

		side_container = SideContainer(size_hint_x=.25)
		self.side_cont = side_container.side_content
		self.side_cont.add_widget(self.student_side)

		layout = BoxLayout(orientation='horizontal', spacing=5)
		layout.add_widget(side_container)
		layout.add_widget(self.main_cont)

		return layout

	def _on_file_drop(self, window, file_path):
		self.switch_video_file(file_path.decode())

	# Navigation buttons

	def switch_to_student(self):
		self.tab = 0
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.student_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.student_side)
		self.side_student_string = '[color=%s]Student[color=%s]' % (color_blue, color_blue)
		self.side_attendence_string = 'Attendence'
		self.side_train_string = 'Train'

	def switch_to_video(self):
		self.tab = 1
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.video_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.video_side)
		self.side_student_string = 'Student'
		self.side_attendence_string = '[color=%s]Attendence[color=%s]' % (color_blue, color_blue)
		self.side_train_string = 'Train'

		self.main_cont.clear_widgets()
		t = ConsoleDisplayWidget()
		self.main_cont.add_widget(t)
		capture = cv2.VideoCapture(0)
		ret, frame = capture.read()
		t.update_texture(frame)

	def switch_to_train(self):
		self.tab = 2
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.train_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.train_side)
		self.side_student_string = 'Student'
		self.side_attendence_string = 'Attendence'
		self.side_train_string = '[color=%s]Train[color=%s]' % (color_blue, color_blue)

	# Sidebar


	# Dialogue

	def dismiss_confirmation(self):
		self._confirmation_popup.dismiss()

	def show_confirmation(self, next_func, message='Are you sure you want to do this?'):
		content = ConfirmDialog(cancel=self.dismiss_file_popup)
		content.message = message
		self._confirmation_popup = Popup(title="Confirm Option", content=content, size_hint=(0.6, 0.4))
		self.confirmation_func = next_func
		self._confirmation_popup.open()

	def dismiss_file_popup(self):
		self._file_popup.dismiss()

	def show_file(self):
		content = LoadFileDialog(load=self.load, cancel=self.dismiss_file_popup)
		self._file_popup = Popup(title="Load file", content=content, size_hint=(0.9, 0.9))
		self._file_popup.open()

	def dismiss_create_class_popup(self):
		self._create_class_popup.dismiss()

	def show_create_class(self):
		content = CreateClassDialog(create=self.create_new_class, cancel=self.dismiss_create_class_popup)
		self._create_class_popup = Popup(title="Create New Class", content=content, size_hint=(0.9, 0.9))
		self._create_class_popup.open()

	def dismiss_detect_popup(self):
		self._detect_popup.dismiss()

	def show_detect(self):
		content = LoadDetectDialog(submit=self.detect_faces, cancel=self.dismiss_detect_popup)
		self._detect_popup = Popup(title="Detection parameters", content=content, size_hint=(0.6, 0.9))
		self._detect_popup.open()

	# Content

	def confirm_confirmation(self):
		self.confirmation_func()
		self.dismiss_confirmation()

	def switch_video_file(self, file_path):
		# TODO: check if file is valid video file via 'if' statement or 'try except'
		self.video_file_path = file_path
		if self.tab == 1:# or self.tab == 2:
			self.video_main.clear_widgets()
			self.video_main.player = VideoPlayer(source=file_path, state='play')
			self.video_main.add_widget(self.video_main.player)

	def load(self, path, filename):
		self.switch_video_file(os.path.join(path, filename[0]))
		self.dismiss_file_popup()

	def create_new_class(self, create_class_list_widget, class_name):
		# TO DO: creating class and then immediately removing class doesn't work
		if not len(create_class_list_widget.student_widgets):
			print('Class is empty!')
			return

		path = os.path.join('records', class_name.strip().replace(' ', '_') + '.db')
		if os.path.exists(path):
			print('Error! Class already exists!')
			return

		print('Creating New Class:', path)			

		db = open(path, 'w')
		conn = sqlite3.connect(path)
		curs = conn.cursor()
		db_cons.append(conn)
		db_curs.append(curs)
		db_manager.reset(curs, True)

		for i, w in enumerate(create_class_list_widget.student_widgets):
			print(w.name)
			db_manager.add_user(curs, i, w.name)

		tab = TabbedPanelHeader(text=class_name)
		tab.content = StudentList(len(self.student_main.class_tabs))
		self.student_main.class_tabs.append(tab)
		self.student_main.add_widget(tab)

		db_manager.close(conn)

		self.dismiss_create_class_popup()

	def remove_class_query(self):
		if self.student_main.current_tab == self.student_main.default_tab:
			return
		self.show_confirmation(self.remove_class, message='Are you sure you want to remove class: %s' % self.student_main.current_tab.text)

	def remove_class(self):
		# TODO: test this out more lmao
		print('removing a class!')
		rem_tab = self.student_main.current_tab
		ind = db_names.index(rem_tab.text)
		db_manager.close(db_cons.pop(ind))
		db_curs.pop(ind)
		db_names.pop(ind)
		os.remove('records/%s.db' % rem_tab.text)
		# TODO: remove model for class
		# TODO: remove student images
		self.student_main.switch_to(self.student_main.default_tab)
		self.student_main.remove_widget(rem_tab)

	def detect_faces(self, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames):
		self.dismiss_detect_popup()
		c = ['python3', 'detection.py', '--video', file_path, '--database', db_path, '--location', location, '--imagedir', image_dir, '--save-video', save_vid_path, '--save-boxes', save_boxes_path]
		if track_faces:
			c += ['--track']
		if int(num_frames) > 0:
			c += ['-n', num_frames]
		print(' '.join(c))
		self.detect_faces_thread = threading.Thread(target=self.run_detect_faces, args=(file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames, ))
		self.detect_faces_thread.daemon = True # kill thread when main program ends
		self.detect_faces_thread.start()
		#Clock.schedule_once(self.run_detect_faces(c))
		# subprocess.run(c)
		#python3 detection.py --video vids/me.mp4 --track --save-boxes boxes/test.pkl --save-video vids/me_out.mp4 --imagedir imdata --database records.db --location "TJ202"


	def run_detect_faces(self, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames):
		try:
			print('Running!')
			process_video.detect_faces_video(file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames)
			#subprocess.run(command)
		except Exception as e:
			print('error: ')
			print(e)

if __name__ == '__main__':
	AttendanceApp().run()
