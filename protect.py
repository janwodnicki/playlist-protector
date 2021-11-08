"Usage: protect.py <username>"

from secret import CLIENT_ID, CLIENT_SECRET
from settings import REDIRECT_URI, DB_NAME, TABLE_NAME
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from sqlite3 import connect
from datetime import datetime
import requests
import base64
from docopt import docopt

def get_as_base64(url):
    return base64.b64encode(requests.get(url).content)

def table_exists(db_name, table_name):
    con = connect(db_name)
    cur = con.cursor()
    cur.execute(f"SELECT COUNT(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    exists = cur.fetchone()[0] != 0
    con.close()
    return exists

def get_playlists(sp):
    try:
        me = sp.me()['uri']
        results = sp.current_user_playlists()
        playlists = results['items']

        while results['next']:
            results = sp.next(results)
            playlists.extend(results['items'])
    except:
        print('Could not fetch playlists')
        return None
    
    owner_playlists = [p for p in playlists if p['owner']['uri'] == me]

    p_dicts = list()
    for p in owner_playlists:
        if len(p['images']) > 0:
            image_url = p['images'][0]['url']
        else: image_url = ""
        p_dict = dict()
        p_dict.update({
            'playlist_uri': p['uri'],
            'playlist_id': p['id'],
            'snapshot_id': p['snapshot_id'],
            'owner': p['owner']['uri'],
            'name': p['name'],
            'description': p['description'],
            'image_url': image_url,
            'timestamp': datetime.now()
        })
        p_dicts.append(p_dict)
    return pd.DataFrame(p_dicts)

def fix_reported(df, sp, db_name):
    updated = list()
    reported = df[df['name'] == ''].copy()
    if len(reported) == 0: return
    con = connect(db_name)
    for _, row in reported.iterrows():
        qry = f"""
        SELECT *
        FROM {TABLE_NAME}
        WHERE owner='{row.owner}'
        AND snapshot_id<>'{row.snapshot_id}'
        AND playlist_uri='{row.playlist_uri}'
        AND name<>''
        ORDER BY timestamp DESC
        LIMIT 1
        """
        match = pd.read_sql(qry, con)
        if len(match) > 0:
            match = match.iloc[0]
            playlist_id, name, description, image_url = match[['playlist_id', 'name', 'description', 'image_url']].to_list()
            if bool(description): sp.playlist_change_details(playlist_id=playlist_id, name=name, description=description)
            else: sp.playlist_change_details(playlist_id=playlist_id, name=name)
            sp.playlist_upload_cover_image(playlist_id=playlist_id, image_b64=get_as_base64(image_url))
            updated.append((match, row))
        else:
            print(f"No matches found for playlist: {row['name']} - {row.playlist_id}, user needs to upload details manually")
    con.close()
    print(updated)
    return

def update_database(df, db_name):
    con = connect(db_name)
    snapshots = set(pd.read_sql("SELECT DISTINCT snapshot_id FROM playlists", con).snapshot_id.to_list())
    df_append = df[(df['name'] != '') & (~df.snapshot_id.isin(snapshots))].copy()
    df_append.to_sql('playlists', con, if_exists='append', index=False)
    con.close()
    return

def fix_and_update(sp, db_name):
    playlists = get_playlists(sp)
    if type(playlists) != type(None):
        if not table_exists(db_name, 'playlists'):
            con = connect(db_name)
            playlists.to_sql('playlists', con, if_exists='append', index=False)
            con.close()
        fix_reported(playlists, sp, db_name)
        update_database(playlists, db_name)
    return

if __name__ == "__main__":
    args = docopt(__doc__)
    scope = 'playlist-read-private playlist-modify-private playlist-modify-public ugc-image-upload'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope,
        open_browser=False,
        username=args['<username>']
        )
    )
    fix_and_update(sp, DB_NAME)
    exit()