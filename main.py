import requests
from bs4 import BeautifulSoup
import threading 
import pynotify
import re
import sys,signal
from xml.etree.ElementTree import XML as xmla

url_extend='?view=live;wrappertype=live'

class Match:
	def __init__(self,ele):
		self.ele=ele
		self.status={"t1head":"","t2head":"","over-ball":"","runs":"","wickets":"","curbatting":"","curbowling":"","batfirst":"","batsecond":"","batthird":"","batfourth":"","inngs":"","booted":False}
		self.inaction={"currentbats":{"runs":"","balls":"","name":""},"currentbowl":""}

	def pollUrl(self):
		self.scrape=BeautifulSoup(requests.get(self.url+url_extend).text)
		
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
		#print self.team2
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

		#sys.exit(0)

	def poll(self):
		self.pollUrl()
		self.currentBatting()
		self.getScore()
		self.getHeadScore()
		self.getActionPlayers()
		self.getComms()
		if self.status["over-ball"]!="matchover":
			t=threading.Timer(20,self.poll)
			t.start()
		else:
			sys.exit()

	def getComms(self):
		tmp=self.scrape.find("table",{"class":"commsTable"})
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
					print over.parent.string
			else:
				print "end of over"

	def boot(self):
		if(self.status["booted"]==False):	# first time boot
			self.extractUrl()
			self.pollUrl()
			self.extractTeams()
			self.matchStatus()
			self.currentBatting()
			self.getHeadScore()
			self.getActionPlayers()
			self.getComms()
			self.status["booted"]=True
			t=threading.Timer(20,self.poll)
			t.start()

		#print self.status



r=requests.get('http://static.espncricinfo.com/rss/livescores.xml')
def listMatches(ele,index):
	el=ele.findall('.//item')
	lis=[]
	for a in index:
		lis.append(el[a])
	return lis

def exitOnInt(signal,frame):
	print "exiting "
	sys.exit(0)


def sendmessage(title, message):
	pynotify.init("cricketera")
   	notice = pynotify.Notification(title, message,"/home/karnesh/Desktop/clock.png")
   	notice.show()
   	return

try:
#	sys.stdin.read(1)
	matches=listMatches(xmla(r.text),[7,8,9])
	for b in matches:
		mat=Match(b)
		mat.boot()
	#cam=Match('http://localhost/test.html')
	#cam.boot()
	signal.signal(signal.SIGINT,exitOnInt)
except KeyboardInterrupt:
	sys.exit(0)


