import threading
import time

def func(a):
	for i in range(10):
		time.sleep(10)
		print('a', a)
		time.sleep(1)
		print('b', a)
		time.sleep(1)

print('p')
t1 = threading.Thread(target=func, args=('123', ))
t1.daemon = True
t1.start()
time.sleep(5)