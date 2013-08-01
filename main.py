import requests
from bs4 import BeautifulSoup
import threading 
from gi.repository import Gtk,Notify,GObject
import re,os
import sys,signal
from xml.etree.ElementTree import XML as xmla

url_extend='?view=live;wrappertype=live'
checkid=0

class Match:
	def __init__(self,ele):
		self.ele=ele
		self.status={"t1head":"","t2head":"","over-ball":"","runs":"","wickets":"","curbatting":"","curbowling":"","batfirst":"","batsecond":"","batthird":"","batfourth":"","inngs":"","booted":False}
		self.inaction={"currentbats":{"runs":"","balls":"","name":""},"currentbowl":""}

	def pollUrl(self):
		self.scrape=BeautifulSoup(requests.get(self.url+url_extend).text)
	
	def setId(self):
		pattern=re.compile(r"([0-9]*)\.html")
		self.id=re.search(pattern,self.ele.find('./guid').text).group(1)

	def extractUrl(self):
		if isinstance(self.ele,str):
			self.url=self.ele
		else:
			self.url=self.ele.find('./guid').text
			if self.url.find('/companion')>-1:		# replace link to companion url 
				self.url=self.url.replace('/companion','')

	def extractTeams(self):
		tmp=self.scrape.find_all("meta",{"property":"og:title"})
		for kk in tmp:
			val=kk.attrs['content']
		tmp=val.split(",")
		tmp=tmp[0].split(' v ')

		self.team1=tmp[0]
		self.team2=tmp[1]
		#print self.team2     #this algorithm is not correct ... not required to change now
		#print self.team1

	def matchStatus(self):   # who is batting first and all
		tmp=self.scrape.find("p",{"class":"statusText"})
		if tmp.string.find("bat")>-1:
			cur="bat"
		else:
			cur="field"
		if tmp.string.find(self.team1)>-1:
			if cur=="bat":
				self.status["batfirst"]=self.team1
				self.status["batsecond"]=self.team2
			else:
				self.status["batfirst"]=self.team2
				self.status["batsecond"]=self.team1
		if tmp.string.find(self.team2)>-1:
			if cur=="bat":
				self.status["batfirst"]=self.team2
				self.status["batsecond"]=self.team1
			else:
				self.status["batfirst"]=self.team1
				self.status["batsecond"]=self.team2

	def currentBatting(self):
		tmp=self.scrape.find_all("p",{"class":"teamText"})
		try:
			if tmp[1].string.find("/")>-1:
				self.status["inngs"]="second"
				self.status["curbatting"]=self.team2
				self.status["curbowling"]=self.team1
			else:
				self.status["inngs"]="first"
				self.status["curbatting"]=self.team1
				self.status["curbowling"]=self.team2
		except IndexError:
			print "index error in currentBatting"
		#print tmp[0].string
		#print tmp[1].string

	def getScore(self):
		tmp=self.scrape.find_all("p",{"class":"teamText"})
		pattern=re.compile(r"[0-9]*\/[0-9][0-9]?")
		if self.status["inngs"]=="first":
			scr=re.search(pattern,tmp[0].string)
		if self.status["inngs"]=="second":
			scr=re.search(pattern,tmp[1].string)
		if scr!=None:
			tmp1=scr.group(0).split("/")
			self.status["wickets"]=int(tmp1[1])
			self.status["runs"]=int(tmp1[0])

	def getHeadScore(self):
		tmp=self.scrape.find_all("p",{"class":"teamText"})
		if self.status["inngs"]=="second":
			self.status["statustext"]=self.scrape.find("p",{"class":"statusText"}).string
		else:
			self.status["statustext"]=""
		self.status["t1head"]=tmp[0].string
		self.status["t2head"]=tmp[1].string

	def getActionPlayers(self):
		tmp=self.scrape.find_all("a",{"class":"livePlayerCurrent"})
		try:
			self.inaction["currentbats"]["name"]=tmp[0].string.replace('*','')
			self.inaction["currentbats"]["runs"]=tmp[0].parent.next_sibling.next_sibling.b.string
			self.inaction["currentbats"]["balls"]=tmp[0].parent.next_sibling.next_sibling.next_sibling.next_sibling.string
			self.inaction["currentbowl"]=tmp[1].string.replace('*','')
		except IndexError:
			print "index error"
		except AttributeError:
			print "att error"

	def stopSignal(self):
		print str(checkid)+"--"+str(self.id)
		if checkid==self.id:
			print "its this" 
			self.status["over-ball"]="matchover"
			GObject.source_remove(self.timer)

	def poll(self):
		self.pollUrl()
		self.currentBatting()
		self.getScore()
		self.getHeadScore()
		self.getActionPlayers()
		self.getComms()
		if self.status["over-ball"]!="matchover":
			self.timer=GObject.timeout_add(20000,self.poll)
		else:
			print "going"
		
	def getComms(self):
		tmp=self.scrape.find("table",{"class":"commsTable"})
		#print "polling"+"---"+self.status["t1head"]
		try:
			over=tmp.tr.td.p
			tmp1=tmp.tr.find("span",{"class":"commsImportant"})
			if self.status["statustext"].find("won")>-1:			# if match over
				if(self.status["over-ball"]!="matchover"):
					sendmessage(self.status["t1head"]+" vs "+self.status["t2head"],"<br>"+self.status["statustext"]+"<br>"+"match over")
					self.status["over-ball"]="matchover"


			else:
				if tmp.tr.find("td",{"class":"endofover"})!=None:       # pop-up if end of over 
					if(self.status["over-ball"]!="endofover"):
						sendmessage(self.status["t1head"]+" vs "+self.status["t2head"],"<br>"+"end of over"+"<br>"+self.status["statustext"])
						self.status["over-ball"]="endofover"
			
				if tmp1!=None:											# pop-up if important event
					if(self.status["over-ball"]!=over.string):
						self.status["over-ball"]=over.string
						if tmp1.string=="OUT":
							tmp2=tmp1.parent.parent.parent.next_sibling.next_sibling.find("p",{"class":"commsText"}).b.string
							sendmessage(self.status["t1head"]+" vs "+self.status["t2head"],"<br>"+tmp1.string+" ( %s ) " % (tmp2)+"<br>"+self.status["statustext"])
						else:
							sendmessage(self.status["t1head"]+" vs "+self.status["t2head"],"<br>"+tmp1.string+" ( %s(%s,%s) - %s )" % (self.inaction["currentbats"]["name"],self.inaction["currentbats"]["runs"],self.inaction["currentbats"]["balls"],self.inaction["currentbowl"])+"<br>"+self.status["statustext"])
			
			
				if over!=None:
					if(self.status["over-ball"]!=over.string):
						self.status["over-ball"]=over.string
						print over.parent.string+"---"+self.status["t1head"]
				else:
					print "end of over"+"---"+self.status["t1head"]
		except AttributeError:
			print "Attribute error"

	def boot(self):
		if(self.status["booted"]==False):	# first time boot
			self.extractUrl()
			self.setId()
			self.pollUrl()
			self.extractTeams()
			self.matchStatus()
			self.currentBatting()
			self.getHeadScore()
			self.getActionPlayers()
			self.getComms()
			print self.status
			self.status["booted"]=True
			self.timer=GObject.timeout_add(20000,self.poll)
			
		#print self.status

class Windowing:
	def __init__(self):
		self.build=Gtk.Builder()
		self.matches=[]
		self.build.add_from_file('test.glade')
		self.window=self.build.get_object("boxy")
		self.box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.window.add(self.box)
		self.build.connect_signals({"destroyit":self.destroy})
		self.window.show_all()

	def handleCheck(self,cb,obj):
		global checkid
		if cb.get_active()==True:
			self.bootNewMatch(obj)
		if cb.get_active()==False:
			checkid=self.getId(obj)
			print str(checkid)+"gya signal"
			for mat in self.matches:
				if mat.id==checkid:
					mat.stopSignal()
					break
		#print "checked"

	def getId(self,ele):
		pattern=re.compile(r"([0-9]*)\.html")
		id=re.search(pattern,ele.find('./guid').text)
		return id.group(1)
		

	def newCheckBox(self,ele):
		tmp=Gtk.CheckButton(ele.find('./title').text)
		tmp.connect("toggled",self.handleCheck,ele)
		tmp.show()
		self.box.pack_start(tmp,True,True,0)
	
	def bootNewMatch(self,ele):
		match=Match(ele)
		match.boot()
		self.matches.append(match)
	
	def destroy(self,k):
		print "destroyed"
		sys.exit()


r=requests.get('http://static.espncricinfo.com/rss/livescores.xml')

def exitOnInt(signal,frame):
	print "exiting "
	sys.exit(0)

def lister(ele):
	win=Windowing()
	el=ele.findall('.//item')
	for b in el:
		win.newCheckBox(b)
	from guppy import hpy
	hp=hpy()
	print hp.heap()
	Gtk.main()

def sendmessage(title, message):
	Notify.init("cricketera")
	notice = Notify.Notification.new(title, message,os.path.dirname(os.path.realpath(__file__))+"/cricketera.jpg")
   	notice.show()
   	return

try:
	#cam=Match('http://localhost/test.html')
	#cam.boot()
	lister(xmla(r.text))
	
	signal.signal(signal.SIGINT,exitOnInt)
except KeyboardInterrupt:
	sys.exit(0)


