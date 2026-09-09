import sqlite3,json,os
from .mission_manager import now
class Storage:
    def __init__(self):
        self.db=sqlite3.connect(os.getenv('DATABASE_PATH','neela_yaan.sqlite3'),check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY, timestamp TEXT, payload TEXT, sent INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,type TEXT,detail TEXT);')
    def event(self,kind,detail=''):
        self.db.execute('INSERT INTO events(timestamp,type,detail) VALUES(?,?,?)',(now(),kind,detail));self.db.commit()
    def save(self,d):
        cur=self.db.execute('INSERT INTO samples(timestamp,payload) VALUES(?,?)',(d['timestamp'],json.dumps(d))); self.db.commit();return cur.lastrowid
    def update(self,id,d):
        self.db.execute('UPDATE samples SET payload=? WHERE id=?',(json.dumps(d),id));self.db.commit()
    def history(self,limit=600,since=None):
        rows=self.db.execute('SELECT payload FROM samples WHERE (? IS NULL OR timestamp>=?) ORDER BY id DESC LIMIT ?',(since,since,limit)).fetchall()
        return [json.loads(x[0]) for x in reversed(rows)]
    def events(self):
        return [dict(zip(('id','timestamp','type','detail'),r)) for r in self.db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 200')]
    def counts(self):
        total,sent=self.db.execute('SELECT count(*),coalesce(sum(sent),0) FROM samples').fetchone();return {'packet_count':total,'transmitted':sent,'pending':total-sent}
