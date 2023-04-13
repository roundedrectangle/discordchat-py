from zenora import APIClient, OauthResponse # for getting access token
from typing import Union, Optional
from threading import Thread
import requests, json
from websocket import WebSocket
from time import sleep

class DiscordClient:
    API_VERSION = 10
    API_ENDPOINT = f'https://discord.com/api/v{API_VERSION}/'
    #self.USERAGENT|{'other':'params'} # python 3.9+
    #{**self.USERAGENT, **{'other':'params'}}
    USERAGENT = {"User-Agent": f"DiscordClient ({API_ENDPOINT}, {API_VERSION})"}
    USERAGENT_PLAIN = f"User-Agent: DiscordClient ({API_ENDPOINT}, {API_VERSION})"
    AUTH_HEADER_START = "Authorization: Bearer "
    GATEWAY_PARAMS = {'v': str(API_VERSION), 'encoding': 'json'}

    _access_code: Optional[str] = None
    access_token: Optional[OauthResponse] = None
    heartbeat_interval: Optional[float] = None # in seconds
    ws: Optional[WebSocket] = None
    redirect_url: str
    gateway_get_url: Optional[str] = None
    last_seq_num: Optional[int] = None

    def __init__(self, token: str, secret: str, redirect_url: str, cached_token: Optional[OauthResponse] = None):
        """Token is a bot token
        Secret is the client secret
        cached_token is token from client.access_token from previous session, available after authentication via opening the link, then handling it with redirect_page; optional; expires in 7 days
        
        if there is no cached_token, you need to ask user to visit the access page and either ask him for the code (works only one time!) or somehow setup the redirecting (maybe to a local server?)
        then you need to call client.set_access_code(code)
        
        redirect_url is the redirect url that you set in the discord"""

        self.client = APIClient(token, client_secret=secret)

        self.redirect_url = redirect_url

        self.update_gateway_get_url()

        if cached_token != None:
            self.update_access_token(cached_token)

        

    def set_access_code(self, code):
        self._access_code = code
        self.update_access_token()
    
    def update_access_token(self, cached: Optional[OauthResponse]=None):
        self.access_token = cached if cached != None else self.client.oauth.get_access_token(self._access_code, self.redirect_url)
        self.auth_header = self.AUTH_HEADER_START+self.access_token.access_token

    def update_gateway_get_url(self):
        from urllib.parse import urlparse, urlencode, parse_qsl
        gateway_base_url = requests.get(self.API_ENDPOINT+"gateway", headers=self.USERAGENT).json().get('url')
        gateway_base_url += ('' if gateway_base_url.endswith('/') else '/')
        parsed = urlparse(gateway_base_url)
        parsed = parsed._replace(query=urlencode({**self.GATEWAY_PARAMS, **dict(parse_qsl(parsed.query))}))
        self.gateway_get_url = parsed.geturl()

    def handle_messages(self):
        while True:
            _data = self.ws.recv()
            if _data in [None, '']: return
            data = json.loads(_data)
            op = data.get("op")
            d = data.get("d", {})
            s = data.get("s")

            if s != None:
                self.last_seq_num = s
            
            if op == 10: # Hello
                print('heartbeat interval:'+str(d.get('heartbeat_interval')))
                self.set_heartbeat(d.get('heartbeat_interval'))
                self.ws.send(str({"op":2,"d":{"token":self.access_token.access_token,"properties":{"os":"linux","browser":self.USERAGENT.values()[0],"device":self.USERAGENT.values()[0]},}}))
            elif op == 11:
                print('connection is not zombied')

    def run_forever(self):
        self.ws = WebSocket()
        self.ws.connect(self.gateway_get_url, header=[self.USERAGENT_PLAIN])
        Thread(target=self.handle_messages).start()

    def set_heartbeat(self, heartbeat_interval): # in milliseconds
        was_set = self.heartbeat_interval != None
        self.heartbeat_interval = heartbeat_interval/1000
        if not was_set:
            self.start_heartbeating()

    def do_heartbeating(self):
        print(11)
        self.ws.send(str({"op": 1, "d": self.last_seq_num}))
        print(self.ws.recv())
        print(12)
        while True:
            print(self.heartbeat_interval)
            sleep(self.heartbeat_interval-0.25) # in seconds
            print(14)
            self.ws.send(str({"op": 1, "d": self.last_seq_num}))
            print(15)

    def start_heartbeating(self):
        Thread(target=self.do_heartbeating).start()