from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.video import Video
from kivy.properties import (ReferenceListProperty, ObjectProperty, BooleanProperty)
from kivy.uix.popup import Popup
from kivy.core.window import Window

import os 

#
# Content and Sidebars
#

class MainContainer(BoxLayout):
	player = ObjectProperty(None)


class SideContainer(BoxLayout):
	side_content = ObjectProperty(None)


class StudentSidebar(BoxLayout):
	pass


class StudentMain(RecycleView):
	def __init__(self, **kwargs):
		super(StudentMain, self).__init__(**kwargs)
		self.data = [{'text': 'student ' + str(x)} for x in range(10)]


class VideoSidebar(BoxLayout):
	pass


class VideoMain(RecycleView):
	player = ObjectProperty(None)


class TrainSidebar(BoxLayout):
	pass


class TrainMain(RecycleView):
	pass


#
# Sidebar Widgets
#


class LoadFileDialog(FloatLayout):
	load = ObjectProperty(None)
	cancel = ObjectProperty(None)

#
# Content Widgets
#

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
								 RecycleBoxLayout):
	''' Adds selection and focus behaviour to the view. '''


class SelectableLabel(RecycleDataViewBehavior, Label):
	''' Add selection support to the Label '''
	index = None
	selected = BooleanProperty(False)
	selectable = BooleanProperty(True)

	def refresh_view_attrs(self, rv, index, data):
		''' Catch and handle the view changes '''
		self.index = index
		return super(SelectableLabel, self).refresh_view_attrs(
			rv, index, data)

	def on_touch_down(self, touch):
		''' Add selection on touch down '''
		if super(SelectableLabel, self).on_touch_down(touch):
			return True
		if self.collide_point(*touch.pos) and self.selectable:
			return self.parent.select_with_touch(self.index, touch)

	def apply_selection(self, rv, index, is_selected):
		''' Respond to the selection of items in the view. '''
		self.selected = is_selected
		if is_selected:
			print("selection changed to {0}".format(rv.data[index]))
		else:
			print("selection removed for {0}".format(rv.data[index]))


class LoadDetectDialog(FloatLayout):
	submit = ObjectProperty(None)
	cancel = ObjectProperty(None)

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

	def dismiss_file_popup(self):
		self._file_popup.dismiss()

	def show_file(self):
		content = LoadFileDialog(load=self.load, cancel=self.dismiss_file_popup)
		self._file_popup = Popup(title="Load file", content=content, size_hint=(0.9, 0.9))
		self._file_popup.open()

	def dismiss_detect_popup(self):
		self._detect_popup.dismiss()

	def show_detect(self):
		content = LoadDetectDialog(submit=self.detect_faces, cancel=self.dismiss_detect_popup)
		self._detect_popup = Popup(title="Detection parameters", content=content, size_hint=(0.6, 0.9))
		self._detect_popup.open()

	# def show_save(self):
	# 	content = SaveDialog(save=self.save, cancel=self.dismiss_popup)
	# 	self._popup = Popup(title="Save file", content=content,
	# 						size_hint=(0.9, 0.9))
	# 	self._popup.open()

	def load(self, path, filename):
		self.switch_video_file(os.path.join(path, filename[0]))
		self.dismiss_file_popup()

	# Content

	def switch_video_file(self, file_path):
		# TODO: check if file is valid video file via 'if' statement or 'try except'
		self.video_file_path = file_path
		if self.tab == 1:# or self.tab == 2:
			self.video_main.clear_widgets()
			self.video_main.player = VideoPlayer(source=file_path, state='play')
			self.video_main.add_widget(self.video_main.player)

	def detect_faces(self, file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames):
		print('request to start detection:', file_path, db_path, location, image_dir, save_vid_path, save_boxes_path, track_faces, num_frames)
		self.dismiss_detect_popup()


if __name__ == '__main__':
	AttendanceApp().run()
