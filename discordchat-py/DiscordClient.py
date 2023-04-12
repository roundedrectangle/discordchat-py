from zenora import APIClient, OauthResponse # for getting access token
from typing import Optional
from threading import Thread
import requests

class DiscordClient:
    API_VERSION = 10
    API_ENDPOINT = f'https://discord.com/api/v{API_VERSION}/'
    #self.USERAGENT|{'other':'params'} # python 3.9+
    #{**self.USERAGENT, **{'other':'params'}}
    USERAGENT = {"User-Agent": f"DiscordClient ({API_ENDPOINT}, {API_VERSION})"}
    AUTH_HEADER_START = "Authorization: Bearer "
    GATEWAY_PARAMS = {'v': str(API_VERSION), 'encoding': 'json'}

    def __init__(self, token: str, secret: str, redirect_url: str, cached_token: Optional[OauthResponse] = None):
        """Token is a bot token
        Secret is the client secret
        cached_token is token from client.access_token from previous session, available after authentication via opening the link, then handling it with redirect_page; optional; expires in 7 days
        
        if there is no cached_token, you need to ask user to visit the access page and either ask him for the code (works only one time!) or somehow setup the redirecting (maybe to a local server?)
        then you need to call client.set_access_code(code)
        
        redirect_url is the redirect url that you set in the discord"""

        self.client = APIClient(token, client_secret=secret)

        self._access_code, self.access_token, self.heartbeat_interval = [None]*3

        if cached_token != None:
            self.access_token = cached_token
            self.auth_header = self.AUTH_HEADER_START+self.access_token

        self.redirect_url = redirect_url

        self.update_gateway_get_url()

    def set_access_code(self, code):
        self._access_code = code
        self.update_access_token()
    
    def update_access_token(self):
        self.access_token = self.client.oauth.get_access_token(self._auth_code, self.redirect_url)
        self.auth_header = self.AUTH_HEADER_START+self.access_token

    def update_gateway_get_url(self):
        from urllib.parse import urlparse, urlencode, parse_qsl
        gateway_base_url = requests.get(self.API_ENDPOINT+"gateway", headers=self.USERAGENT).json().get('url')
        gateway_base_url += ('' if gateway_base_url.endswith('/') else '/')
        parsed = urlparse(gateway_base_url)
        parsed = parsed._replace(query=urlencode({**self.GATEWAY_PARAMS, **dict(parse_qsl(parsed.query))}))
        self.gateway_get_url = parsed.geturl()

    def set_heartbeat(self, heartbeat_interval):
        was_set = self.heartbeat_interval != None
        self.heartbeat_interval = heartbeat_interval
        if not was_set:
            self.start_heartbeating()

    def start_heartbeating(self):
        pass