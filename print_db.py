"""
Usage: 
    print_db.py [--limit=<int>]
"""

from sqlite3 import connect
import pandas as pd
from settings import DB_NAME
from docopt import docopt

if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        limit = int(args['--limit'])
    except:
        limit = 10
        
    con = connect(DB_NAME)
    df = pd.read_sql(f"SELECT * FROM playlists ORDER BY timestamp DESC LIMIT {limit}", con)
    print(df[['playlist_id', 'name', 'description', 'timestamp']])
    con.close()
    exit()