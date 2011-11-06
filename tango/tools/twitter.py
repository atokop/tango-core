import re
import time
from urllib import urlencode

import simplejson
import oauth2 as oauth

class TwitterApiCallFailed(Exception): pass

def parse_link(text):
    """
    >>> parse_link('A link to http://battle.net')
    "A link to <a href='http://battle.net'>http://battle.net</a>"
    """
    return re.sub(
        r"(http(s)?://[\w./?=%&amp;\-]+)",
        lambda x: "<a href='%s'>%s</a>" % (x.group(), x.group()),
        text
    )
        
        # parse @tweeter
def parse_at(text):
    """
    >>> parse_at('A reference to @teebesz')
    "A reference to <a href='http://twitter.com/teebesz'>@teebesz</a>"
    """
    return re.sub(
        r'@(\w+)',
        lambda x: "<a href='http://twitter.com/%s'>%s</a>" \
            % (x.group()[1:], x.group()),
        text
    )

def parse_hashtag(text):
    """
    >>> parse_hashtag('A twitter #hashtag')
    "A twitter <a href='http://twitter.com/search?q=%23hashtag'>#hashtag</a>"
    """
    return re.sub(
        r'#(\w+)',
        lambda x: "<a href='http://twitter.com/search?q=%%23%s'>%s</a>" \
            % (x.group()[1:], x.group()),
        text
    )

class TwitterApi(object):
    BASE_URI = 'https://api.twitter.com/1'

    def __init__(self, **kwargs):
        self.consumer_secret    = kwargs.get('CONSUMER_SECRET', '')
        self.consumer_key       = kwargs.get('CONSUMER_KEY', '')
        self.oauth_token        = kwargs.get('OAUTH_TOKEN', '')
        self.oauth_token_secret = kwargs.get('OAUTH_TOKEN_SECRET', '')

    def __call__(self, url, method='GET', params=None):
        oauth_timestamp    = int(time.time())
        oauth_nonce        = oauth.generate_nonce

        token = oauth.Token(key=self.oauth_token, 
                            secret=self.oauth_token_secret)
        consumer = oauth.Consumer(key=self.consumer_key, 
                                  secret=self.consumer_secret)
        client = oauth.Client(consumer, token)

        if url[0] != '/': url = '/' + url
        url = "%s%s" % (self.BASE_URI, url)

        if params:
            if method == 'GET':
                url += "?" + urlencode(params)
                resp, content = client.request(url, method)
            elif method in ('POST', 'PUT'):
                resp, content = client.request(url, method, urlencode(params))
        else:
            resp, content = client.request(url, method)

        if int(resp.get('status', 0)) != 200:
            raise TwitterApiCallFailed(resp, content)

        return resp, content

if __name__ == "__main__":
    import doctest
    doctest.testmod()
