
# coding: utf-8

# # Donbot
# A simple module for automating interactions with mafiascum.net.
# Create an instance of the Donbot class with your username and password 
# (and potentially other parameters), and you'll be able to:
# - Collect a range of posts from a thread
# - Make posts in a specified thread with specified content
# - Send pms to a user with a specified subject and body
# - Collect the number of posts in a specified thread
# - Collect id matching a specified scummer's username
# 
# More functionality will be added in the future according to project demands.

# ## Setup

# ### Dependencies

# In[1]:


from datetime import datetime # to parse timestamps
from math import ceil         # to get page# from post
from lxml import html         # to help parse website content
import requests               # for interacting with website
import time                   # need delays before post requests


# ### Urls donbot will construct requests with

# In[2]:


# generic site url; will start other urls
siteurl = 'https://forum.mafiascum.net/'

# where bot logs into mafiascum.net
loginurl = siteurl + 'ucp.php?mode=login'

# format w/ username and get to obtain page w/ their userid on it
userurl = siteurl + 'search.php?keywords=&terms=all&author={}'

# make post request here w/ right format to make a post to thread
posturl = siteurl + 'posting.php?mode=reply&{}'

# post request here w/ form to send a pm
pmurl = siteurl + 'ucp.php?i=pm&mode=compose'


# ### Paths to elements donbot will grab info from

# In[3]:


# number of posts in thread assoc'd w/ page
postcountpath = "//div[@class='pagination']/text()"

# every post on current page
postspath = '//div[@class="post bg2" or @class="post bg1"]'

# post# of a post
numberpath = ".//p[@class='author']/a/strong/text()"

# username assoc'd w/ a post
userpath = ".//dl[@class='postprofile']/dt/a/text()"

# content of a post
contentpath = ".//div[@class='content']"

# timestamp of a post
datetimepath = ".//p[@class='author']/text()"

# path to value of all input elements on page with specified name
postformpath = "//input[@name='{}']/@value"

# at userurl, path to link that has their userid
userlinkpath = "//dt[@class='author']/a/@href"


# ### Other static variables used across instances

# In[4]:


# number of posts that appear on each thread page
postsperpage = 25 


# ## The Donbot Class

# In[5]:


class Donbot:
    
    def __init__(self, username=None, password=None,
                 thread=None, postdelay=1.5):
        self.postdelay = postdelay # seconds to wait before post requests
        self.thread = thread
        self.username = username
        self.session = requests.Session()
        
        if username and password:
            self.session.post(loginurl, 
                              {'username': username, 'password': password,
                               'redirect': 'index.php', 'login': 'Login'})
        
    def getUserID(self, username):
        # Search for posts by user; userID is in link in first result.
        username = username.replace(' ', '+')
        page = self.session.get(userurl.format(username)).content
        userposts = html.fromstring(page)
        userlink = userposts.xpath(userlinkpath)[0]
        return userlink[userlink.rfind('=')+1:]
    
    def getNumberOfPosts(self, thread=None):
        thread = thread if thread else self.thread
        if len(thread) == 0:
            raise ValueError('No thread specified!')
        page = self.session.get(thread).content
        numberOfPosts = html.fromstring(page).xpath(postcountpath)[0]
        return int(numberOfPosts[:numberOfPosts.find(' ')].strip())
        
    def getPosts(self, thread=None, start=0, end=float('infinity')):
        thread = self.thread if not thread else thread
        if len(thread) == 0:
            raise ValueError('No thread specified!')
            
        # check end or # of posts in thread to find pages we need to examine
        startpage = ceil(start/postsperpage)
        endpage = (ceil(end/postsperpage) if end != float('infinity')
                   else ceil(self.getNumberOfPosts(thread)/postsperpage))
        
        # collect on each page key content from posts after currentpost
        newposts = []
        for i in range(startpage*25, endpage*25, 25):
            page = self.session.get(thread+'&start='+str(i)).content
            for post in html.fromstring(page).xpath(postspath):
                p = {}
                p['number'] = int(post.xpath(numberpath)[0][1:])
                if p['number'] >= start and p['number'] <= end:
                    p['user'] = post.xpath(userpath)[0]
                    p['content'] = html.tostring(post.xpath(contentpath)[0])
                    p['content'] = p['content'].decode('UTF-8')

                    # requires some postprocessing to turn into a datetime
                    stamp = post.xpath(datetimepath)[-1]
                    p['datetime'] = stamp[stamp.find('» ')+2:].strip()
                    p['datetime'] = datetime.strptime(
                        p['datetime'], '%a %b %d, %Y %I:%M %p')
                    newposts.append(p)
        return newposts
        
    def makePost(self, content, thread=None, postdelay=None):
        postdelay = postdelay if postdelay else self.postdelay
        thread = thread if thread else self.thread
        if len(thread) == 0:
            raise ValueError('No thread specified!')
        
        # one request to get form info for post, and another to make it
        threadid = thread[thread.find('?')+1:]
        page = html.fromstring(self.session.get(
            posturl.format(thread[thread.find('?')+1:])).content)
        form = {'message': content, 'addbbcode20': 100,
                'post': 'Submit', 'disable_smilies': 'on',
                'attach_sig': 'on', 'icon': 0}
        for name in ['topic_cur_post_id', 'lastclick',
                     'creation_time','form_token']:
            form[name] = page.xpath(postformpath.format(name))[0]

        time.sleep(postdelay)
        self.session.post(posturl.format(
            thread[thread.find('?')+1:]), form)
        
    def sendPM(self, subject, body, sendto, postdelay=None):
        # one request to get form info for pm, and another to send it
        # a third request gets userid matching user
        postdelay = postdelay if postdelay else self.postdelay
        compose = html.fromstring(self.session.get(pmurl).content)
        form = {'username_list':'', 'subject':subject, 'addbbcode20':100,
                'message':body, 'status_switch':0, 'post':'Submit',
                'attach_sig':'on', 'disable_smilies':'on',
                'address_list[u][{}]'.format(self.getUserID(sendto)):'to'}
        for name in ['lastclick', 'creation_time', 'form_token']:
            form[name] = compose.xpath(postformpath.format(name))[0]

        time.sleep(postdelay)
        self.session.post(pmurl, form)
