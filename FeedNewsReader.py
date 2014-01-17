import sublime
import sublime_plugin
import threading
import urllib.request

from xml.etree import ElementTree as etree
from datetime import datetime

always_online_url = "http://google.com"
feed_url = "http://www.forocoches.com/foro/external.php?type=RSS2&forumids=2"
timeout = 2

class FeedNewsReaderCommand(sublime_plugin.WindowCommand):

    def run(self):
        sublime.status_message('Loading News Feed...')
        statusThread = CheckStatus(
            self.on_internet_thread_result,
            always_online_url,
            feed_url,
            timeout
        )
        statusThread.start()
        newsThread = FeedRSSNewsLoad(
            self.on_news_thread_result,
            feed_url
        )
        newsThread.start()

    def on_news_thread_result(self, data):
        self.feed_data = data
        sublime.set_timeout(self.display_items, 0)

    def display_items(self):
        self.feed_text = []
        for item in self.feed_data:
            self.feed_text.append([
                "%s - %s" % (item['date'].time(), item['title']),
                item['link']
            ])
        self.show_quick_panel(self.feed_text, self.on_item_selected)

    def on_item_selected(self, index):
        if (index != -1):
            self.selected_item_index = index
            item = self.feed_data[index]
            self.show_in_quick_panel(item)

    def show_in_quick_panel(self, item):
        self.selected_item = item
        self.show_quick_panel(
            ['Read here', 'Open in browser'],
            self.on_article_selected
        )

    def on_article_selected(self, index):
        """
        Display a selector to choose from either open a new view with feed_text
        or open the link in a browser tab.
        """
        if (index == 0):
            self.show_in_new_tab(self.selected_item)
        elif (index == 1):
            self.open_url(self.selected_item['link'])

    def show_in_new_tab(self, item):
        doc = self.window.new_file()
        doc.set_scratch(True)
        contents = []
        contents.append(item['title'])
        contents.append(item['link'])
        contents.append(item['description'])
        doc.run_command('append', {
            'characters': '\n\n'.join(contents),
        })

    def show_in_browser(self, item):
        self.open_url(item['link'])

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def on_internet_thread_result(self, status, service_status):
        self.internetStatus = status
        self.service_status = service_status
        sublime.set_timeout(self.displayError, 0)

    def displayError(self):
        if (not self.internetStatus):
            sublime.status_message('Your Internet connection seems to be down')
        elif (not self.service_status):
            sublime.status_message('Feed cannot be reached')

    def show_quick_panel(self, options, done):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 10)

class FeedRSSNewsLoad(threading.Thread):
    """
    Launch the RSS Loading on its own thread
    """
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
    """
    Perform the actual url loading and XML parsing.
    """
    def get(self, url):
        feed = urllib.request.urlopen(url)
        feed_data = feed.read()
        feed.close()
        return self.parse_feed(feed_data)

    def parse_feed(self, data):
        root = etree.fromstring(data)
        item = root.findall('channel/item')

        stories=[]
        for entry in item:
            pub_date = datetime.strptime(
                entry.findtext('pubDate'),
                '%a, %d %b %Y %X GMT'
            )
            story = {
                'title': entry.findtext('title'),
                'link': entry.findtext('link'),
                'date': pub_date,
                'description': entry.findtext('description'),
                'content': entry.findtext('encoded'),
            }
            stories.append(story)
        return stories


class CheckStatus(threading.Thread):
    """
    Pre-check of online/offline status and notify the configured
    callbacks to handle the request
    """
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
