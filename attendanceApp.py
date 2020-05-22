import os
import sqlite3
import subprocess
import sys
import threading
import time

import cv2
import db_manager
import process_video
import training_manager
from functools import partial
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
			# release camera (Kivy can't do that right now)
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
	train_main = None
	tracking_string = StringProperty('Group Tracking IDs')

	def toggle_tracking(self):
		self.train_main.toggle_tracking()

		if self.tracking_string == 'Group Tracking IDs':
			self.tracking_string = 'Don\'t Group Tracking IDs'
		elif self.tracking_string == 'Don\'t Group Tracking IDs':
			self.tracking_string = 'Group Tracking IDs'


class TrainMain(TabbedPanel):
	# basically same as student main
	locations = []
	should_group_tracking_id = True

	def __init__(self, **kwargs):
		super(TrainMain, self).__init__(**kwargs)

		self.default_tab_text = 'Training'
		self.default_tab.content = Label(text='Use these tools to help train the model.')
		
		for i in range(len(db_curs)):
			tab = TabbedPanelHeader(text=db_names[i])#(text='Class %i' % (i + 1))
			tab.content = ImageDateList(i, self)
			self.locations.append(tab)
			self.add_widget(tab)

	def toggle_tracking(self):
		self.should_group_tracking_id = not self.should_group_tracking_id


#
# Sidebar Widgets
#


#
# Content Support Widgets
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


class StudentElement(BoxLayout):
	student_label = StringProperty('TEMP')


class ConsoleDisplayWidget(BoxLayout):
	img = Image(source='frame.jpg')
	label = Label(height=40, size_hint_y=None)

	def __init__(self, **kwargs):
		super(ConsoleDisplayWidget, self).__init__(**kwargs)

		self.add_widget(self.img)
		self.add_widget(self.label)
		self.label.text = 'Started!'


	def update_texture(self, frame):
		# updates image with a cv2 image
		print('updated frame')
		buf1 = cv2.flip(frame, 0)
		buf = buf1.tostring()
		texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr') 
		texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
		self.img.texture = texture1
		print('updated frame')


class ImageDateList(ScrollView):
	db_cur = None
	image_date_widget = []
	dates = []
	last_selected_index = -1
	layout = None
	train_main = None

	def __init__(self, db_index, main, **kwargs):
		super(ImageDateList, self).__init__(**kwargs)
		self.dates, self.image_date_widget = [], [] # lists bleed over to next class for some reason, need this to reset
		self.train_main = main

		self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=10)
		# in case of no elements
		self.layout.bind(minimum_height=self.layout.setter('height'))

		self.db_cur = db_curs[db_index]
		info = db_curs[db_index].execute('select * from records')
		for src, datetime, loc, res, compid, userid, w, h, hwratio, x, y, frame, testid, confidence in info:
			if datetime.split(' ')[0] not in self.dates:
				self.dates.append(datetime.split(' ')[0])

		for i in self.dates:
			s = ImageDateElement(size_hint_y=None, height=40)
			s.index = len(self.image_date_widget)
			s.parent_list = self
			s.date_label = i
			self.image_date_widget.append(s)
			self.layout.add_widget(s)

		self.clear_widgets()
		self.add_widget(self.layout)
		

	def select(self, index):
		self.last_selected_index = index
		self.image_date_widget[index].selected = not self.image_date_widget[index].selected
		return True

	def dismiss_image_view_popup(self):
		self._image_view_popup.dismiss()

	def show_image_view(self, index):
		self.last_selected_index = index
		info = list(self.db_cur.execute('select * from records where datetime like \'%s%%\'' % self.dates[index]))
		users = dict(self.db_cur.execute('select * from users'))
		content = ImageViewerDialogue(cancel=self.dismiss_image_view_popup)
		content.viewer.init(info, users, self.show_name_select, self.train_main.should_group_tracking_id)
		self._image_view_popup = Popup(title="Viewing Images - %s" % self.dates[index], content=content, size_hint=(0.9, 0.9))
		self._image_view_popup.open()

	def refresh_image_view(self):
		info = list(self.db_cur.execute('select * from records where datetime like \'%s%%\'' % self.dates[self.last_selected_index]))
		users = dict(self.db_cur.execute('select * from users'))
		self._image_view_popup.content.viewer.init(info, users, self.show_name_select)

	def dismiss_name_select_popup(self):
		self._image_name_select_popup.dismiss()

	def show_name_select(self, compid, _): # button is passed here for some reason
		users = dict(self.db_cur.execute('select * from users'))
		content = NameSelectionDialogue(cancel=self.dismiss_name_select_popup)
		content.name_list.init(users, self, compid)
		self._image_name_select_popup = Popup(title="Assigning Student", content=content, size_hint=(0.6, 0.8))
		self._image_name_select_popup.open()


class ImageDateElement(BoxLayout):
	index = None
	selected = BooleanProperty(False)
	selectable = BooleanProperty(True)
	parent_list = None

	date_label = StringProperty('TEMP')

	def on_touch_down(self, touch):
		if self.collide_point(*touch.pos) and self.selectable:
			if touch.button == 'right':
				return self.parent_list.select(self.index)
			else:
				self.parent_list.show_image_view(self.index)

#
# Dialogue
#

class ConfirmDialogue(FloatLayout):
	message = StringProperty('Are you sure you want to do this?')
	ok = ObjectProperty(None)
	cancel = ObjectProperty(None)


class LoadFileDialogue(FloatLayout):
	load = ObjectProperty(None)
	cancel = ObjectProperty(None)


class LoadDetectDialogue(FloatLayout):
	submit = ObjectProperty(None)
	cancel = ObjectProperty(None)

class LoadTrainDialogue(FloatLayout):
	submit = ObjectProperty(None)
	cancel = ObjectProperty(None)

class LoadTestDialogue(FloatLayout):
	submit = ObjectProperty(None)
	cancel = ObjectProperty(None)


class CreateClassDialogue(FloatLayout):
	create = ObjectProperty(None)
	cancel = ObjectProperty(None)
	list_widget = ObjectProperty(None)
	text_student_name = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(CreateClassDialogue, self).__init__(**kwargs)

		# allow for enter key to submit forms
		self.list_widget.text_student_name = self.text_student_name


class ImageViewerDialogue(FloatLayout):
	cancel = ObjectProperty(None)
	viewer = ObjectProperty(None)


class NameSelectionList(ScrollView):
	student_widgets = []
	selected_index = -1
	ids = []
	layout = None
	im_date_list = None
	compid = -1

	def init(self, names, parent, comp):
		self.im_date_list = parent
		self.compid = comp

		self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=10)
		# in case of no elements
		self.layout.bind(minimum_height=self.layout.setter('height'))

		for i in names:
			s = CreateClassStudentWidget(size_hint_y=None, height=40) # reuse selectable name
			s.index = len(self.student_widgets)
			s.parent_list = self
			s.name = ' %i. %s' % (i, names[i])
			self.ids.append(i)
			self.student_widgets.append(s)
			self.layout.add_widget(s)

		self.clear_widgets()
		# add gridlayout with all the elements to scroll view (SV can only have 1 widget)
		self.add_widget(self.layout)
		

	def select(self, index):
		# for i in self.student_widgets:
		# 	i.selected = False

		# # already selected the same label
		# if self.selected_index == index:
		# 	self.selected_index = -1
		# else:
		# 	self.selected_index = index
		# 	for i in self.student_widgets:
		# 		i.selected = False
		self.student_widgets[index].selected = True
		userid = self.ids[index]
		# print(userid, self.compid, self.im_date_list.dates[self.im_date_list.last_selected_index])
		# print(list(self.im_date_list.db_cur.execute("select * from records where compid=%s and datetime like '%s%%'" % \
		# 	(self.compid, self.im_date_list.dates[self.im_date_list.last_selected_index]))))
		self.im_date_list.db_cur.execute("update records set userid=%s where compid=%s and datetime like '%s%%'" % \
			(userid, self.compid, self.im_date_list.dates[self.im_date_list.last_selected_index]))
		self.im_date_list.refresh_image_view()
		self.im_date_list.dismiss_name_select_popup()

		return True


class NameSelectionDialogue(FloatLayout):
	cancel = ObjectProperty(None)
	name_list = ObjectProperty(None)


class ImageViewerWidget(ScrollView):

	def init(self, info, users, open_dialogue, should_group_tracking_id):
		# layout = GridLayout(cols=4, row_force_default=True, row_default_height=150, height=9999)

		if should_group_tracking_id:
			compids = []
			for src, datetime, loc, res, compid, userid, w, h, hwratio, x, y, frame, testid, confidence in info:
				if compid not in compids:
					compids.append(compid)
			layout = ScrollGridLayout((len(compids) // 4 + 2) * 150)
			compids = []
			for src, datetime, loc, res, compid, userid, w, h, hwratio, x, y, frame, testid, confidence in info:
				if compid not in compids:
					compids.append(compid)
					src = src[3:] # remove the ../ at start of path
					if userid in users:
						name = ' %i. %s' % (userid, users[userid])
					else:
						name = ' Unidentified'
					img = ImageViewerElement(src, name, str(round(confidence, 2)), compid, open_dialogue)
					layout.add_widget(img)
		else:
			layout = ScrollGridLayout((len(info) // 4 + 2) * 150)
			for src, datetime, loc, res, compid, userid, w, h, hwratio, x, y, frame, testid, confidence in info:
				src = src[3:] # remove the ../ at start of path
				if userid in users:
					name = ' %i. %s' % (userid, users[userid])
				else:
					name = ' Unidentified'
				img = ImageViewerElement(src, name, str(round(confidence, 2)), compid, open_dialogue)
				layout.add_widget(img)

		print(len(layout.children) % 4)
		for i in range(4 - (len(layout.children) % 4)):
			layout.add_widget(Widget())

		self.clear_widgets()
		self.add_widget(layout)


class ScrollGridLayout(GridLayout):
    def __init__(self, h, **kwargs):
        super(ScrollGridLayout, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = h#self.minimum_height
        self.row_force_default = True
        self.row_default_height = 150
        self.cols = 4
        self.spacing = 10


class ImageViewerElement(BoxLayout):
	src = StringProperty()
	button_text = StringProperty()
	label_text = StringProperty()
	button = ObjectProperty()

	def __init__(self, src, name, conf, compid, open_dialogue, **kwargs):
		super(ImageViewerElement, self).__init__(**kwargs)
		self.src = src
		self.button_text = name
		self.label_text = conf
		self.button.bind(on_release=partial(open_dialogue, compid)) # I think this is wrong

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
	console_display_widget = None

	side_student_string = StringProperty('[color=%s]Student[color=%s]' % (color_blue, color_blue))
	side_attendance_string = StringProperty('Attendance')
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
		self.train_side.train_main = self.train_main

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
		self.side_attendance_string = 'Attendance'
		self.side_train_string = 'Train'

	def switch_to_video(self):
		self.tab = 1
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.video_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.video_side)
		self.side_student_string = 'Student'
		self.side_attendance_string = '[color=%s]Attendance[color=%s]' % (color_blue, color_blue)
		self.side_train_string = 'Train'

	def switch_to_train(self):
		self.tab = 2
		self.main_cont.clear_widgets()
		self.main_cont.add_widget(self.train_main)
		self.side_cont.clear_widgets()
		self.side_cont.add_widget(self.train_side)
		self.side_student_string = 'Student'
		self.side_attendance_string = 'Attendance'
		self.side_train_string = '[color=%s]Train[color=%s]' % (color_blue, color_blue)

	# Sidebar


	# Dialogue

	def dismiss_confirmation(self):
		self._confirmation_popup.dismiss()

	def show_confirmation(self, next_func, message='Are you sure you want to do this?'):
		content = ConfirmDialogue(cancel=self.dismiss_file_popup)
		content.message = message
		self._confirmation_popup = Popup(title="Confirm Option", content=content, size_hint=(0.6, 0.4))
		self.confirmation_func = next_func
		self._confirmation_popup.open()

	def dismiss_file_popup(self):
		self._file_popup.dismiss()

	def show_file(self):
		content = LoadFileDialogue(load=self.load, cancel=self.dismiss_file_popup)
		self._file_popup = Popup(title="Load file", content=content, size_hint=(0.9, 0.9))
		self._file_popup.open()

	def dismiss_create_class_popup(self):
		self._create_class_popup.dismiss()

	def show_create_class(self):
		content = CreateClassDialogue(create=self.create_new_class, cancel=self.dismiss_create_class_popup)
		self._create_class_popup = Popup(title="Create New Class", content=content, size_hint=(0.9, 0.9))
		self._create_class_popup.open()

	def dismiss_detect_popup(self):
		self._detect_popup.dismiss()

	def show_detect(self):
		content = LoadDetectDialogue(submit=self.detect_faces, cancel=self.dismiss_detect_popup)
		self._detect_popup = Popup(title="Detection parameters", content=content, size_hint=(0.6, 0.9))
		self._detect_popup.open()

	def dismiss_train_popup(self):
		self._train_popup.dismiss()

	def show_train(self):
		content = LoadTrainDialogue(submit=self.train_model, cancel=self.dismiss_train_popup)
		self._train_popup = Popup(title="Training parameters", content=content, size_hint=(0.6, 0.4))
		self._train_popup.open()

	def dismiss_test_popup(self):
		self._test_popup.dismiss()

	def show_test(self):
		content = LoadTestDialogue(submit=self.test_model, cancel=self.dismiss_test_popup)
		self._test_popup = Popup(title="Testing parameters", content=content, size_hint=(0.6, 0.3))
		self._test_popup.open()


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

		# db_manager.close(conn)

		self.dismiss_create_class_popup()

	def remove_class_query(self):
		if self.student_main.current_tab == self.student_main.default_tab:
			return
		self.show_confirmation(self.remove_class, message='Are you sure you want to remove class: %s' % self.student_main.current_tab.text)

	def remove_class(self):
		# TODO: test this out more
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
		# c = ['python3', 'detection.py', '--video', file_path, '--database', db_path, '--location', location, '--imagedir', image_dir, '--save-video', save_vid_path, '--save-boxes', save_boxes_path]
		# if track_faces:
		# 	c += ['--track']
		# if int(num_frames) > 0:
		# 	c += ['-n', num_frames]
		# print(' '.join(c))

		self.main_cont.clear_widgets()
		self.console_display_widget = ConsoleDisplayWidget()
		self.main_cont.add_widget(self.console_display_widget)
		process_video.app = self
		process_video.app_img = self.console_display_widget.img

		capture = cv2.VideoCapture(0)
		ret, frame = capture.read()
		capture.release()
		self.console_display_widget.update_texture(frame)

		self.detect_faces_thread = threading.Thread(target=self.run_detect_faces, args=(file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames, ))
		self.detect_faces_thread.daemon = True # kill thread when main program ends
		self.detect_faces_thread.start()

		# Clock.schedule_once(partial(self.run_detect_faces, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames))
		# subprocess.run(c)
		#python3 detection.py --video vids/me.mp4 --track --save-boxes boxes/test.pkl --save-video vids/me_out.mp4 --imagedir imdata --database records.db --location "TJ202"


	def run_detect_faces(self, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames, *args):
		print('args r ', args)
		try:
			print('Running!')
			process_video.detect_faces_video(file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames, self)
			#subprocess.run(command)
			print('Done!')
		except Exception as e:
			print('error: ')
			print(e)


	def train_model(self, curs_index, epochs, epoch_size, batch_size):
		self.dismiss_train_popup()

		curs_index, epochs, epoch_size, batch_size = int(curs_index), int(epochs), int(epoch_size), int(batch_size)
		db_name = db_names[curs_index]
		model_path = 'models/%s.h5' % db_name
		# model_path = 'models/class.h5'

		# self.main_cont.clear_widgets()
		# self.console_display_widget = ConsoleDisplayWidget()
		# self.main_cont.add_widget(self.console_display_widget)

		# process_video.app = self
		# process_video.app_img = self.console_display_widget.img
		# self.console_display_widget.update_texture(frame)

		self.train_model_thread = threading.Thread(target=self.run_train_model, args=(db_name, model_path, epochs, epoch_size, batch_size, ))
		self.train_model_thread.daemon = True # kill thread when main program ends
		self.train_model_thread.start()

	def run_train_model(self, db_name, model_path, epochs, epoch_size=64, batch_size=64, *args):
		print('args r ', args)
		try:
			print('Running!')
			cursor = ''
			conn = sqlite3.connect('records/%s.db' % db_name)
			curs = conn.cursor()
			training_manager.train(curs, model_path, epochs, epoch_size, batch_size)
			#subprocess.run(command)
			print('Done!')
		except Exception as e:
			print('error: ')
			print(e)


	def test_model(self, curs_index, datetime):
		self.dismiss_test_popup()

		curs_index = int(curs_index)
		db_name = db_names[curs_index]
		model_path = 'models/%s.h5' % db_name

		# self.main_cont.clear_widgets()
		# self.console_display_widget = ConsoleDisplayWidget()
		# self.main_cont.add_widget(self.console_display_widget)

		# process_video.app = self
		# process_video.app_img = self.console_display_widget.img
		# self.console_display_widget.update_texture(frame)

		self.test_model_thread = threading.Thread(target=self.run_test_model, args=(db_name, model_path, datetime, ))
		self.test_model_thread.daemon = True # kill thread when main program ends
		self.test_model_thread.start()

	def run_test_model(self, db_name, model_path, datetime, *args):
		print('args r ', args)
		try:
			print('Running!')
			cursor = ''
			conn = sqlite3.connect('records/%s.db' % db_name)
			curs = conn.cursor()
			training_manager.test(conn, curs, model_path, datetime)
			print('Done!')
			#subprocess.run(command)
		except Exception as e:
			print('error: ')
			print(e)


if __name__ == '__main__':
	AttendanceApp().run()
	for c in db_cons:
		db_manager.close(c)