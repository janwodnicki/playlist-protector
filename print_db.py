"""
Usage: 
    print_db.py <username> [--limit=<int>]
"""

from sqlite3 import Connection
import pandas as pd
from config import DB_NAME, USERS_DB
from docopt import docopt
import json

if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        limit = int(args['--limit'])
    except:
        limit = 10
    users = json.load(open(USERS_DB, 'r'))

    try:
        uri = users[args['<username>']]['spotify_uri']
    except:
        print(f"user: {args['<username>']} not found")
        exit()
        
    con = Connection(DB_NAME)
    df = pd.read_sql(f"SELECT * FROM playlists", con)
    print(df[df.owner == uri].head(limit))
    con.close()
    exit()