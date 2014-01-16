import sublime
import sublime_plugin
import threading
import urllib.request

from xml.etree import ElementTree as etree

always_online_url = "http://google.com"
feed_url = "http://www.forocoches.com/foro/external.php?type=RSS2&forumids=2"
timeout = 2

class FeedNewsReaderCommand(sublime_plugin.WindowCommand):

    def run(self):
        sublime.status_message('Loading News Feed...')
        statusThread = CheckStatus(
            self.onInternetThreadResult,
            always_online_url,
            feed_url,
            timeout
        )
        statusThread.start()
        newsThread = FeedRSSNewsLoad(
            self.onNewsThreadResult,
            feed_url
        )
        newsThread.start()

    def onNewsThreadResult(self, data):
        self.feed_data = data
        sublime.set_timeout(self.displayItems, 0)

    def displayItems(self):
        self.feed_text = []
        for item in self.feed_data:
            print()
            first_line = "%s - %s" % (item['title'], item['date'])
            second_line = item['link']
            self.feed_text.append([first_line, second_line])
        self.window.show_quick_panel(self.feed_text, self.onItemSelection)

    def onItemSelection(self, index):
        if (index != -1):
            self.selected_item_index = index
            item = self.feed_data[index]
            # self.window.show_quick_panel(item['date'], self.onArticleSelection)
            # han = self.window.new_file()
            # print(han)
            self.openURL(item['link'])

    def onArticleSelection(self, index):
        print("go to site")

    def openURL(self, url):
        import webbrowser
        webbrowser.open(url)

    def onInternetThreadResult(self, status, service_status):
        self.internetStatus = status
        self.service_status = service_status
        sublime.set_timeout(self.displayError, 0)

    def displayError(self):
        if (not self.internetStatus):
            sublime.status_message('Your Internet connection seems to be down')
        elif (not self.service_status):
            sublime.status_message('Feed cannot be reached')


class FeedRSSNewsLoad(threading.Thread):

    def __init__(self, callback, feed_url):
        self.result = None
        self.feed_url = feed_url
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        feedApi = FeedNewsAPI()
        self.result = feedApi.get(self.feed_url)
        self.callback(self.result)
        return


class FeedNewsAPI:

    def get(self, url):
        feed = urllib.request.urlopen(url)
        feed_data = feed.read()
        feed.close()
        return self.parse_feed(feed_data)

    def parse_feed(self, data):
        root = etree.fromstring(data)
        item = root.findall('channel/item')
        print(item)

        stories=[]
        for entry in item:
            stories.append({
                'title': entry.findtext('title'),
                'link': entry.findtext('link'),
                'date': entry.findtext('pubDate')
            })
        return stories

class CheckStatus(threading.Thread):

    def __init__(self, callback, check_url, service_url, timeout):
        self.timeout = timeout
        self.check_url = check_url
        self.service_url = service_url
        threading.Thread.__init__(self)
        self.callback = callback

    def run(self):
        try:
            urllib.request.urlopen(self.check_url, timeout=self.timeout)
            try:
                urllib.request.urlopen(self.service_url, timeout=self.timeout)
                self.callback(True, True) # Both Up
            except:
                self.callback(True, False) # Feed Down
        except:
            self.callback(False, None) # No need to check Feed if no connection.
        return
