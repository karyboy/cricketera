import signal,sys

def handleInt(sign,no):
	print "interrupted"

signal.signal(signal.SIGINT,handleInt)

try:
	sys.stdin.read(1)
except IOError:
	print "io interrupt"
else:
	print "yoyo"






