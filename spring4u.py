# -*- coding:utf-8 -*-
import re, os
import urllib, urllib2
import time, cookielib
from bs4 import BeautifulSoup
from threading import Thread, Lock
from Queue import Queue
from zhtools.langconv import *
from threading import stack_size
stack_size(32768*32)

class RemoveTool(object):
    def __init__(self):
        self.remove_enter = re.compile(r"\n")
        self.replace_brbr = re.compile(r"<br/><br/>")
        self.replace_br = re.compile(r"<br/>")
        self.replace_nbsp = re.compile(r"&nbsp;")
        self.remove_tag = re.compile(r"<.*?>")
        self.remove_end = re.compile(r"[.*?]")
    def replace(self, str):
        str = re.sub(self.remove_enter, "", str)
        str = re.sub(self.replace_brbr, "\n", str)
        str = re.sub(self.replace_br, "", str)
        str = re.sub(self.replace_nbsp, " ", str)
        str = re.sub(self.remove_tag, "", str)
        str = re.sub(self.remove_end, "", str)
        return str.strip()

class Crawler(object):

    def __init__(self, threads):
        self.count = 0
        self.lock = Lock()
        self.q_req_url = Queue()
        self.s_req_url = set()
        self.threads = threads
        user_agent = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/48.0.2564.109 Safari/537.36'
        self.headers = {'User-Agent': user_agent}
        self.tool = RemoveTool()

    def __del__(self):
        time.sleep(0.5)
        self.q_req_url.join()

    def __login(self, login_url, post_data):
        cookie_support = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
        opener = urllib2.build_opener(cookie_support)
        urllib2.install_opener(opener)
        request = urllib2.Request(url=login_url, data=post_data, headers=self.headers)
        result = urllib2.urlopen(request)

    def __makedir(self, path):
        is_exists = os.path.exists(path)
        if not is_exists:
            os.makedirs(path)

    def delblankline(self, filename):
        infp = open(filename, "r")
        outfp = open(filename[1:], "w")
        lines = infp.readlines()
        for line in lines:
            line = Converter('zh-hans').convert(line.decode('utf-8'))
            line = line.encode('utf-8')
            if len(line) == 1 or len(line) == 0:
                continue
            if line != r'\r\n' and line[:-1].split():
                outfp.writelines(line)
        infp.close()
        outfp.close()

    def __get_new_urls_and_datas(self, url, articles=False):
        request = urllib2.Request(url=url, headers=self.headers)
        response = urllib2.urlopen(request, timeout=30)
        html_cont = response.read().decode('big5', 'ignore').encode('utf-8')
        soup = BeautifulSoup(html_cont, 'html.parser', from_encoding='utf-8')

        # <a href="http://spring4u.info/viewthread.php?tid=32459" target="_blank">
        links = soup.find_all('a', href=re.compile(r"^http://spring4u\.info/viewthread\.php\?tid=\d+"))

        if articles is True:
            # author_name = soup.find('td', width='65%').string
            # author_name = author_name[4:]
            # # print author_name
            # author_name = author_name.strip()
            # self.__makedir(author_name)
            author_name = "_novel"
            for link in links:
                file_name = author_name + "/" + link.string + ".txt"
                f = open(file_name, "w+")
                new_request = urllib2.Request(url=link['href'], headers=self.headers)
                new_response = urllib2.urlopen(new_request, timeout=30)
                str_ = new_response.read().decode('big5', 'replace').encode('utf-8')
                p = re.compile(r"<span style=.*?>(.*?)</span>", re.S)
                items = re.findall(p, str_)
                soup = BeautifulSoup(str_, 'html.parser', from_encoding='utf-8')
                link_authors = soup.find_all('a', href=re.compile(r"viewpro\.php\?uid=\d+"), target="_blank", class_="bold")
                link_author = soup.find('a', href=re.compile("viewpro\.php\?uid=\d+"), target="_blank", class_="bold")
                # print len(link_authors), len(items)
                Q = []
                for author in link_authors:
                    if author.string == link_author.string:
                        Q.append(True)
                    else:
                        Q.append(False)
                cnt = 0
                for item in items:
                    if cnt >= len(link_authors):
                        break
                    if Q[cnt] is True:
                        string = self.tool.replace(item)
                        # print string
                        f.write(string)
                    cnt += 1
                if( f ):
                    f.close()
                self.delblankline(file_name)
        else:
            for link in links:
                if link not in self.s_req_url:
                    self.q_req_url.put(link['href'])
                    self.s_req_url.add(link['href'])

    def start(self, root_url, login_url=None, post_data=None):
        if login_url is not None:
            self.__login(login_url, post_data)
        self.__get_new_urls_and_datas(root_url)
        for i in range(self.threads):
            t = Thread(target=self.craw)
            t.start()
            time.sleep(2)

    def craw(self):
        while True:
            req = self.q_req_url.get()
            with self.lock:
                self.count += 1
            print 'Craw %d: %s' % (self.count, req)
            try:
                self.__get_new_urls_and_datas(req, True)
            except urllib2.URLError, e:
                if hasattr(e, "reason"):
                    print 'Craw failed...', e.reason
            except Exception, e:
                print 'Craw failed...', e
            self.q_req_url.task_done()
            time.sleep(0.1)


if __name__ == '__main__':

    root_url = 'http://spring4u.info/viewthread.php?tid=48616'
    login_url = 'http://spring4u.info/logging.php?action=login'
    post_data = urllib.urlencode({
        'formhash': '95d3049b',
        'referer': '',
        'cookietime': '2592000',
        'loginfield': 'username',
        'username': 'mengt2012',
        'password': '******',
        'questionid': '0',
        'answer': '',
        'loginsubmit': '會員登錄'
    })
    new_craw = Crawler(threads=8)
    new_craw.start(root_url=root_url, login_url=login_url, post_data=post_data)
