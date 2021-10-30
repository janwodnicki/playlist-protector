"""
Usage: 
    protect.py <username>
"""

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, DB_NAME
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from sqlite3 import Connection
from datetime import datetime
from pandas.io.sql import DatabaseError
import requests
import base64
from docopt import docopt

def get_as_base64(url):
    return base64.b64encode(requests.get(url).content)

def get_playlists(sp):
    try:
        me = sp.me()['uri']
        results = sp.current_user_playlists()
        playlists = results['items']

        while results['next']:
            results = sp.next(results)
            playlists.extend(results['items'])
    except Exception as e:
        print(e)
        return False
    
    owner_playlists = [p for p in playlists if p['owner']['uri'] == me]

    p_dicts = list()
    for p in owner_playlists:
        p_dict = dict()
        p_dict.update({
            'playlist_uri': p['uri'],
            'playlist_id': p['id'],
            'snapshot_id': p['snapshot_id'],
            'owner': p['owner']['uri'],
            'name': p['name'],
            'description': p['description'],
            'image_url': p['images'][0]['url'],
            'timestamp': datetime.now()
        })
        p_dicts.append(p_dict)
    return pd.DataFrame(p_dicts)

def update_playlists(con, sp):
    new = get_playlists(sp)
    updated = list()
    if type(new) == bool:
        if not new:
            return updated

    try:
        old = pd.read_sql('select * from playlists', con)
        old.sort_values('timestamp', ascending=False, inplace=True)
    except DatabaseError:
        new.to_sql('playlists', con, if_exists='fail', index=False)
        return updated
    
    for _, row in new.iterrows():
        old_snaps = old[old.snapshot_id != row.snapshot_id].copy()
        matches = old_snaps[old_snaps.playlist_uri == row.playlist_uri].head(1)

        # Don't do anything if playlist is new or there is no older snapshot to take from
        if len(matches) == 0: continue
        else: match = matches.iloc[0]

        # Send update request with old snapshot info if title is gone
        if (not row['name']) and match['name']:
            playlist_id, name, description, image_url = match[['playlist_id', 'name', 'description', 'image_url']].to_list()
            if bool(description):
                sp.playlist_change_details(playlist_id=playlist_id, name=name, description=description)
            else:
                sp.playlist_change_details(playlist_id=playlist_id, name=name)
            sp.playlist_upload_cover_image(playlist_id=playlist_id, image_b64=get_as_base64(image_url))
            updated.append((match, row))

        else: continue
    
    new = get_playlists(sp)
    new.to_sql('playlists', con, if_exists='append', index=False)
    return updated

if __name__ == "__main__":
    args = docopt(__doc__)
    scope = 'playlist-read-private playlist-modify-private playlist-modify-public ugc-image-upload'
    con = Connection(DB_NAME)
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        open_browser=False,
        username=args['<username>']
        )
    )
    print(update_playlists(con, sp))
    con.close()
    exit()