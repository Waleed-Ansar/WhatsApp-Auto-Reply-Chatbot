import sqlite3
from datetime import datetime, timedelta

class SQLiteSessionManager:
    def __init__(self, db_path='sessions.db', timeout_minutes=120):
        self.db_path = db_path
        self.timeout = timedelta(minutes=timeout_minutes)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT,
                last_activity TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def session(self, session_id: str):
        """Creates or retrieves a session. Deletes the session if expired."""
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute(
            'SELECT data, last_activity FROM sessions WHERE session_id = ?',
            (session_id,)
        )
        row = cursor.fetchone()
        
        if row:
            data, last_activity = row
            last_activity = datetime.fromisoformat(last_activity)
            print(datetime.now() - last_activity , self.timeout)

            if datetime.now() - last_activity > self.timeout:
                conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                conn.commit()
                conn.close()
                return "Expired"

            else:
                conn.execute(
                    'UPDATE sessions SET last_activity = ? WHERE session_id = ?',
                    (datetime.now(), session_id)
                )
                conn.commit()
                conn.close()
                return "Updated"
        
        else:
            session_data = f"Chat Data for ID: {session_id}"
            conn.execute(
                'INSERT INTO sessions (session_id, data, last_activity) VALUES (?, ?, ?)',
                (session_id, session_data, datetime.now())
            )
            conn.commit()
            conn.close()
            return "Created"

session_manager = SQLiteSessionManager()

