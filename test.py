from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.base import runTouchApp


dropdown = DropDown()
for i in range(8):
	btn = Button(text='Source %d' % i, size_hint_y=None, height=44)
	btn.bind(on_release=lambda btn: dropdown.select(btn.text))
	dropdown.add_widget(btn)
	
main_button = Button(text='Video Source', size_hint=(None, None))
main_button.bind(on_release=dropdown.open)
dropdown.bind(on_select=lambda instance, x: setattr(main_button, 'text', x))
runTouchApp(main_button)