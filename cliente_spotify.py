#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import datetime
import base64
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qsl
from math import ceil


# In[2]:


client_id = 'e9a3d54e253d4efc91ada2f4cdd67cfc'
client_secret = '74d8228a44694380a45feafaa516ac7d'


# In[3]:


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_s = urlparse(self.path).query
        form = dict(parse_qsl(query_s))

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        if "code" in form:
            self.server.auth_code = form["code"]
            self.server.error = None
            status = "successful"
        elif "error" in form:
            self.server.error = form["error"]
            self.server.auth_code = None
            status = "failed ({})".format(form["error"])
        else:
            self._write("<html><body><h1>Invalid request</h1></body></html>")
            return

        self._write("""
        <html>
        <script>
        window.close()
        </script>
        <body>
        <h1>Authentication status: {}</h1>
        This window can be closed.
        </body>
        </html>
        """.format(status))

    def _write(self, text):
        return self.wfile.write(text.encode("utf-8"))

    def log_message(self, format, *args):
        return


def start_local_http_server(port, handler=RequestHandler):
    server = HTTPServer(("localhost", port), handler)
    server.allow_reuse_address = True
    server.auth_code = None
    server.error = None
    return server


# In[8]:


class SpotifyAPI(object):
    auth_code = None
    access_token = None
    refresh_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    #client_id = None
    #client_secret = None
    client_id = 'e9a3d54e253d4efc91ada2f4cdd67cfc'
    client_secret = '74d8228a44694380a45feafaa516ac7d'
    auth_url = "https://accounts.spotify.com/authorize"
    local_uri = "http://localhost:8000"
    token_url = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    def get_authorize_url(self):
        endpoint = self.auth_url
        scopes = ["playlist-read-collaborative", "playlist-modify-public", "playlist-read-private", "user-library-read"]
        auth_data = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.local_uri,
            "scope": ' '.join(scopes)
        }
        data = urlencode(auth_data)
        auth_url = f"{endpoint}?{data}"
        return auth_url

    def open_auth_url(self):
        auth_url = self.get_authorize_url()
        try:
            webbrowser.open(auth_url)
            print(f"Opened {auth_url} in your browser")
        except webbrowser.Error:
            print(f"Please navigate here: {auth_url}")

    def get_auth_response_local_server(self, port):
        server = start_local_http_server(port)
        self.open_auth_url()
        server.handle_request()

        if server.auth_code is not None:
            return server.auth_code
        elif server.error is not None:
            raise Exception(f"Received error from OAuth server: {server.error}")
        else:
            raise Exception("Server listening on localhost has not been accessed")

    def get_auth_code(self):
        auth_code = self.get_auth_response_local_server(port=8000)
        self.auth_code = auth_code
        return auth_code

    def get_client_credentials(self):
        # Returns a base64 encoded string
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_id == None:
            raise Exception("Se debe setear el client_id y client_secret")
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {
            "Authorization": f"Basic {client_creds_b64}"
        }

    def get_token_data(self):
        return {
            "grant_type": "authorization_code",
            "code": self.get_auth_code(),
            "redirect_uri": self.local_uri
        }

    def retrieve_tokens(self):
        token_url = self.token_url
        token_data = self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            raise Exception("No se pudo autenticar.")
        data = r.json()
        now = datetime.datetime.now()
        access_token = data['access_token']
        refresh_token = data['refresh_token']
        expires_in = data['expires_in'] # seconds
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True

    def renew_tokens(self, refresh_token):
        token_url = self.token_url
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            raise Exception("No se pudo autenticar.")
        data = r.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']

    def get_access_token(self):
        token = self.access_token
        refresh_token = self.refresh_token
        expires = self.access_token_expires
        now = datetime.datetime.now()
        if expires < now or token == None:
            self.renew_tokens(refresh_token)
            return self.get_access_token()
        return token

    def get_resource_header(self):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return headers

    def get_resource(self, lookup_id, resource_type='albums', version='v1'):
        endpoint = f"https://api.spotify.com/{version}/{resource_type}/{lookup_id}"
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers=headers)
        if r.status_code not in range(200,299):
            return {}
        return r.json()

    def get_album(self, _id):
        return self.get_resource(_id, resource_type='albums')

    def get_artist(self, _id):
        return self.get_resource(_id, resource_type='artists')

    def base_search(self, query_params):
        headers = self.get_resource_header()
        endpoint = "https://api.spotify.com/v1/search"
        lookup_url = f"{endpoint}?{query_params}"
        r = requests.get(lookup_url, headers=headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()

    def search(self, query=None, search_type='artist'):
        if query == None:
            raise Exception("Se necesita un parametro de busqueda")
        if isinstance(query, dict):
            query = " ".join([f"{k}:{v}" for k,v in query.items()])
        query_params = urlencode({"q": query, "type": search_type.lower()})
        return self.base_search(query_params)

    def get_user_liked_songs(self, limit=20, offset=0):
        endpoint = "https://api.spotify.com/v1/me/tracks"
        headers = self.get_resource_header()
        payload = {
            "limit": limit,
            "offset": offset
        }
        r = requests.get(endpoint, headers=headers, params=payload)
        if r.status_code not in range(200,299):
            return {}
        return r.json()

    def get_all_user_liked_songs_uri(self, limit=50, offset=0, id_list=[]):
        data = self.get_user_liked_songs(limit=limit, offset=offset)
        liked_songs = data['items']
        total = data['total']
        if offset < total:
            offset = offset + limit
            id_list = self.extract_song_uri(lista=liked_songs, ids=id_list)
            self.get_all_user_liked_songs_uri(offset=offset, id_list=id_list)
        return total, id_list

    def extract_song_uri(self, lista=[], ids=[]):
        for i in lista:
            ids.append(i['track']['uri'])
        return ids

    def get_user_id(self):
        endpoint = "https://api.spotify.com/v1/me"
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers=headers)
        if r.status_code not in range(200,299):
            return {}
        r = r.json()
        return r['id']

    def create_playlist(self, name=''):
        user_id = self.get_user_id()
        endpoint = f"https://api.spotify.com/v1/users/{user_id}/playlists"
        headers = self.get_resource_header()
        headers['Content-Type'] = 'application/json'
        r = requests.post(endpoint, json={'name': name}, headers=headers)
        if r.status_code not in range(200,299):
            return {}
        r = r.json()
        return r['id'] # Returns the playlist id

    def uri_splitter(self, offset=0, limit=100):
        total, uri_list = self.get_all_user_liked_songs_uri()
        shorter_list = []
        for i in range(limit):
            if (i+offset) < total:
                shorter_list.append(uri_list[i+offset])
        return shorter_list

    def create_liked_playlist(self, name='Musica Wenota', offset=0):
        playlist_id, total = self.check_playlist(name=name)
        endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = self.get_resource_header()
        headers['Content-Type'] = 'application/json'
        data = self.get_user_liked_songs(limit=1, offset=0)
        total = data['total'] - total
        cant = ceil(total/100)
        if cant == 1:
            uri_list = self.uri_splitter(limit=total)
            r = requests.post(endpoint, json={'uris': uri_list, 'position': 0}, headers=headers)
            if r.status_code not in range(200,299):
                return {}
            return True
        for i in range(cant):
            uri_list = self.uri_splitter(offset=offset)
            r = requests.post(endpoint, json={'uris': uri_list, 'position': 0}, headers=headers)
            if r.status_code not in range(200,299):
                return {}
            offset = offset + 100
        return True

    def get_playlist_id(self, name=''):
        endpoint = "https://api.spotify.com/v1/me/playlists"
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers=headers, params={'limit': 50})
        if r.status_code not in range(200,299):
            return {}
        data = r.json()
        if data['total'] > data['limit']:
            for i in range(len(data['items'])):
                if data['items'][i]['name'] == name:
                    return data['items'][i]['id']
            r = requests.get(endpoint, headers=headers, params={'limit': 50, 'offset': 50})
            data = r.json()
        for i in range(len(data['items'])):
            if data['items'][i]['name'] == name:
                return data['items'][i]['id']

    def check_playlist(self, name=''):
        playlist_id = self.get_playlist_id(name=name)
        if playlist_id == None:
            playlist_id = self.create_playlist(name=name)
        endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers=headers)
        return playlist_id, r.json()['total']
