# -*- coding: utf-8 -*-

import sys
import requests
from config import BASE_URL, AUTH_ENDPOINT
from requests.auth import AuthBase
from requests.cookies import extract_cookies_to_jar

class User(AuthBase):
    """
        User object to be used as auth in requests
    """
    # need to fill Authoritazion with current token provide by api


    def __init__(self, username, password, session = None):
        self.username = username
        self.password = password
        self.session = session or requests.Session()
        self.token = self.get_token()

    def get_token(self):
        """
            Request auth endpoint and return user token  
        """
        url = BASE_URL+AUTH_ENDPOINT
        # use json paramenter because for any reason they send user and pass in plain text :'(
        r = self.session.post(
            url, json={'username': self.username, 'password': self.password})
        if r.status_code == 200:
            print("You are in!")
            return 'Bearer ' + r.json()['data']['access']

        print("Error login,  check user and password")
        print("Error {}".format(r.json()["message"]))
        sys.exit(2)

    def refresh_header(self):
        """
            Refresh jwt because it expired and returned
        """
        self.token = self.get_token()

        return self.header

    def __call__(self, r):
        r.headers["Authorization"] = self.token
        r.register_hook('response', self.handle_401)
        return r

    def handle_401(self, r: requests.Response, *args, **kwargs):
        if not r.status_code == 401:
            return r
        r.content
        r.close()

        #stolen from https://github.com/psf/requests/blob/main/requests/auth.py
        prep = r.request.copy()
        extract_cookies_to_jar(prep._cookies, r.request, r.raw) #type: ignore
        prep.headers['Authorization'] = self.token
        _r = r.connection.send(prep, **kwargs) #type: ignore
        _r.history.append(r)
        _r.request = prep

        return _r 