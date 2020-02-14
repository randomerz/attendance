from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.scrollview import ScrollView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.tabbedpanel import TabbedPanelHeader
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.video import Video
from kivy.uix.popup import Popup
from kivy.properties import (ReferenceListProperty, ObjectProperty, BooleanProperty, NumericProperty, StringProperty)
from kivy.core.window import Window

import os
import subprocess
import sys
import sqlite3

import db_manager

#
# Python
#

db_cons, db_curs = [], []
try:
	# finding db files
	db_paths = []
	for root, dirs, files in os.walk('records'):
		for file in files:
			if '.db' in file:
				db_paths.append(os.path.join(root, file))
	# connect to dbs
	for i in range(len(db_paths)):
		db_cons.append(sqlite3.connect(db_paths[i]))
		db_curs.append(db_cons[i].cursor())
		for i in db_curs[i].execute('select * from users'):
			print(i)
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
			tab = TabbedPanelHeader(text='Class %i' % (i + 1))
			tab.content = StudentList(i)
			self.class_tabs.append(tab)
			self.add_widget(tab)



class VideoSidebar(BoxLayout):
	pass


class VideoMain(BoxLayout):
	player = ObjectProperty(None)


class TrainSidebar(BoxLayout):
	pass


class TrainMain(BoxLayout):
	pass


#
# Sidebar Widgets
#

class StudentList(ScrollView):
	def __init__(self, db_index, **kwargs):
		super(StudentList, self).__init__(**kwargs)

		layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=10)
		# in case of no elements
		layout.bind(minimum_height=layout.setter('height'))

		for i in db_curs[db_index].execute('select * from users'):
			btn = StudentElement(size_hint_y=None, height=40)
			btn.student_label = str(i[0]) + '. ' + i[1] # number. student name
			layout.add_widget(btn)
		'''
		for i in range(30):
			btn = StudentElement(size_hint_y=None, height=40)
			btn.student_label = str(i + 1) + '. Student Name'
			layout.add_widget(btn)
		'''

		self.clear_widgets()
		# add gridlayout with all the elements to scroll view (SV can only have 1 widget)
		self.add_widget(layout)


#
# Content Widgets
#

class StudentElement(BoxLayout):
	student_label = StringProperty('TEMP')


#
# Dialogue
#

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

	video_file_path = ''


	def build(self):
		Window.bind(on_dropfile=self._on_file_drop) # makes thing really slow i think
		self.student_main = StudentMain()
		self.student_side = StudentSidebar()
		self.video_main = VideoMain()
		self.video_side = VideoSidebar()
		self.train_main = TrainMain()
		self.train_side = TrainSidebar()

		self.main_cont = MainContainer(size_hint_x=.75)
		self.main_cont.add_widget(self.student_main)

		side_container = SideContainer(size_hint_x=.25)
		self.side_cont = side_container.side_content
		self.side_cont.add_widget(self.student_side)

		layout = BoxLayout(orientation='horizontal')
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

	def switch_to_video(self):
		self.tab = 1
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.video_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.video_side)

	def switch_to_train(self):
		self.tab = 2
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.train_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.train_side)

	# Sidebar


	# Dialogue

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
		if not len(create_class_list_widget.student_widgets):
			print('Class is empty!')
			return

		path = os.path.join('records', class_name.replace(' ', '_') + '.db')
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

		tab = TabbedPanelHeader(text='Class %i' % (len(self.student_main.class_tabs) + 1))
		tab.content = StudentList(len(self.student_main.class_tabs))
		self.student_main.class_tabs.append(tab)
		self.student_main.add_widget(tab)

		db_manager.close(conn)

		self.dismiss_create_class_popup()

	def detect_faces(self, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames):
		print('request to start detection:')#, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames)
		self.dismiss_detect_popup()
		try:
			c = ['python3', 'detection.py', '--video', file_path, '--database', db_path, '--location', location, '--imagedir', image_dir, '--save-video', save_vid_path, '--save-boxes', save_boxes_path]
			if track_faces:
				c += ['--track']
			if int(num_frames) > 0:
				c += ['-n', num_frames]
			print(' '.join(c))
			subprocess.run(c)
			#python3 detection.py --video vids/me.mp4 --track --save-boxes boxes/test.pkl --save-video vids/me_out.mp4 --imagedir imdata --database records.db --location "TJ202"
		except Exception as e:
			print('e-error!')
			print(e)

if __name__ == '__main__':
	AttendanceApp().run()
