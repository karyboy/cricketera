from gi.repository import Gtk,GObject
import sys,threading,time

def destroy(k):
	print "destroyed"
	sys.exit()

def poll():
	print "called it "
	GObject.timeout_add(5000,poll)
	#t=threading.Timer(1,poll)
	#t.start()

start=time.time()	
build=Gtk.Builder()
build.add_from_file('test.glade')
window=build.get_object("boxy")
build.connect_signals({"destroyit":destroy})
window.show_all()
#t=threading.Timer(1,poll)
#t.start()
GObject.timeout_add(5000,poll)
Gtk.main()







