#!/usr/bin/python3

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import sys
import sqlite3
import re
import pprint
from feedgen.feed import FeedGenerator
import datetime
import pyrss2gen11
import json
import sys



# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
try:
	with open('.apikey','r') as f:
		DEVELOPER_KEY = f.read()
except:
	print("File open failed")
	sys.exit(1)
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"



def initSQL():
	conn = sqlite3.connect('viewsync.sqlite3')
	c = conn.cursor()
	c.execute("""
		CREATE TABLE IF NOT EXISTS episode(
			episodeNum 	INTEGER PRIMARY KEY,
			episodeDate Timestamp NOT NULL,
			description	TEXT NOT NULL,
			viewsync 	TEXT NOT NULL			
		);
		""")
def getPart():
	conn = sqlite3.connect('viewsync.sqlite3')
	c = conn.cursor()
	c.execute("""
		select count(*)+1 
		from episode;
		""")
	return(c.fetchone()[0])

def youtube_search(part, channelId, titleString):
	youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,developerKey=DEVELOPER_KEY)
	results = youtube.search().list(
		q=titleString % (part),
		order="relevance",
		part="id,snippet",
		maxResults=1,
		channelId=channelId).execute()

	#print(results['items'][0]['id'])


	
	if re.match(re.escape(titleString%(part))+".*" , results['items'][0]['snippet']['title']):
		#print("Matched:%s -- %s "%(titleString,results['items'][0]['snippet']['title']))
		link = "<a href='https://www.youtube.com/watch?v=%s'><h1>%s</h1><h2>by %s</h2><p>%s</p><img src='%s'/></a>" % (results['items'][0]['id']['videoId'], results['items'][0]['snippet']['title'], results['items'][0]['snippet']['channelTitle'], results['items'][0]['snippet']['description'], results['items'][0]['snippet']['thumbnails']['high']['url'])

		return((results['items'][0]['id']['videoId'],link,results['items'][0]['snippet']['publishedAt'] ))
	else:
		#print("Not Matched:%s -- %s "%(titleString,results['items'][0]['snippet']['title']))
		return((None, None, None))


def makeViewsync(part):
	#print("Making %s" % (part))
	steejoID, steejo, publishedAt = youtube_search(part, "UCeuyjX6ayprafiDlRxxrzNQ", "MASA FACTORIO - Let's Play Multiplayer Factorio Part %s")
	arumbaID, arumba,publishedAt = youtube_search(part, "UCISPcad-6svNxgViVr_syvA", "Factorio MASA %s")
	aavakID, aavak,publishedAt  = youtube_search(part, "UCqvU9Uxf_8YJOq67S6qcrFw", "Factorio MASA [Multiplayer] - %s.")
	benthamID, bentham,publishedAt = youtube_search(part, "UCwTLrdvrscYPXBZ3Z0kzX0g", "Factorio MASA Ep#%s")
	conn = sqlite3.connect('viewsync.sqlite3')
	c = conn.cursor()

	try:
		viewsync="http://viewsync.net/watch?v=%s&t=0&v=%s&t=0&v=%s&t=0&v=%s&t=0&autoplay=true" % (steejoID, arumbaID, aavakID, benthamID)
		c.execute("""
			REPLACE INTO episode VALUES(?,?,?,?)
			""", [part, publishedAt, "<h1><a href='%s'>Viewsync link for Episode %s</a></h1>"%(viewsync, part)+steejo+arumba+aavak+bentham, viewsync ])
		conn.commit()
		c.execute("select * from episode where episodeNum = ?", [part])
		#print(c.fetchone())
	except Exception as e:
		pass
		#print("Match error")
		#print(e)

def makeRSS():
	conn = sqlite3.connect('viewsync.sqlite3')
	c = conn.cursor()
	c.execute("""select * from episode order by episodeNum desc;""")



	items = []


	for row in c:
		item =  pyrss2gen11.RSSItem(
			title = "Episode %s" % (row[0]),
			link = "<![CDATA[%s]]>" % (row[3]),
			description = "<![CDATA[%s]]>" % (row[2]),
			pubDate = row[1],
			guid = pyrss2gen11.Guid("http://factoriony.drbbs.org/MASA/%s" % (row[0])))		
		items.append(item)


	
	rss = pyrss2gen11.RSS2(
	    title = "Viewsync MASA Feed",
	    link = "http://factoriony.drbbs.org/MASA.xml",
	    description = "Automatically compiled MASA feed",
	    lastBuildDate = datetime.datetime.now(),
	    items = items)

	
	rss.write_xml(open("masa.xml", "w"))

	cleanfile = ""
	with open("masa.xml", "r") as masa:
		from xml.sax import saxutils
		for line in masa:
			cleanfile=cleanfile+saxutils.unescape(line, {"&amp;":"&"})
			#print(line)
			#print(saxutils.unescape(line, {"&amp;":"&"}))
	
	with open("/var/www/html/masa.xml", "w") as masa:
		masa.write(cleanfile)


	

		
if __name__ == "__main__":
	try:
		initSQL()
		makeViewsync(getPart())
		makeRSS()
	except HttpError as e:
		print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
