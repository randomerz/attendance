from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.base import runTouchApp
from kivy.app import App
from kivy.clock import Clock

class Screen(FloatLayout):

	def __init__(self, **kwargs):
		super(Screen, self).__init__(**kwargs)
		dropdown = DropDown()
		for i in range(8):
			btn = Button(text='Source %d' % i, size_hint_y=None, height=44)
			btn.bind(on_release=lambda btn: dropdown.select(btn.text))
			dropdown.add_widget(btn)
			
		main_button = Button(text='Video Source', size_hint=(None, None), pos=(100, 100))
		main_button.bind(on_release=dropdown.open)
		#main_button.bind(on_release=Clock.schedule_once(lambda dt: print('hi')))
		dropdown.bind(on_select=lambda instance, x: setattr(main_button, 'text', x))
		self.add_widget(main_button)

class AttendanceApp(App):

	def build(self):
		return Screen()





if __name__ == '__main__':
	AttendanceApp().run()