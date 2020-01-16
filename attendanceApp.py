from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
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
from kivy.core.window import Window

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



class AttendanceApp(App):
	main_cont = None
	side_cont = None
	player = ObjectProperty(None)
	tab = 0


	def build(self):
		Window.bind(on_dropfile=self._on_file_drop) # makes thing really slow i think
		self.main_cont = MainContainer(size_hint_x=.75)
		self.main_cont.remove_widget(self.main_cont.player)
		self.main_cont.add_widget(StudentMain())

		self.side_cont = SideContainer(size_hint_x=.25, orientation='vertical')
		self.side_cont.remove_widget(self.side_cont.side_content)
		self.side_cont.side_content = StudentSidebar()
		self.side_cont.add_widget(self.side_cont.side_content)
		#self.side_cont.add_widget(StudentSidebar)

		layout = BoxLayout(orientation='horizontal')
		layout.add_widget(self.side_cont)
		layout.add_widget(self.main_cont)

		return layout


	def _on_file_drop(self, window, file_path):
		self.main_cont.remove_widget(self.main_cont.player)
		self.main_cont.player = VideoPlayer(source=file_path.decode(), state='play')
		self.main_cont.add_widget(self.main_cont.player)
		return


if __name__ == '__main__':
	AttendanceApp().run()