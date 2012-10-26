"Shelf connectors for persisting stashed template context variables."

import cPickle as pickle
import pickletools
from contextlib import closing
from cPickle import HIGHEST_PROTOCOL
from sqlite3 import Binary as blobify
from sqlite3 import dbapi2 as sqlite3
from sqlite3 import OperationalError


class BaseConnector(object):
    def __init__(self, app):
        self.app = app

    def get(self, site, rule):
        raise NotImplementedError('A shelf connector must implement get.')

    def put(self, site, rule, context, source_files=None):
        raise NotImplementedError('A shelf connector must implement put.')

    def drop(self, site, rule=None):
        raise NotImplementedError('A shelf connector must implement drop.')

    def list(self, site=None):
        """Return list of routes.  If a site is specified, only
        routes for that site will be returned.
        """
        raise NotImplementedError('A shelf connector must implement list.')

class SqliteConnector(BaseConnector):
    def initialize(self):
        """ -- schema:
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            rule TEXT NOT NULL,
            context BLOB NOT NULL
        );
        """
        with self.connect(initialize=False) as db:
            db.cursor().executescript(self.initialize.func_doc)

    def add_source_files_to_schema(self):
        with self.connect(initialize=False) as db:
            try:
                db.cursor().execute("SELECT source_files FROM contexts")
            except OperationalError:
                db.cursor().execute("ALTER TABLE contexts "
                                    "ADD COLUMN source_files "
                                    "NOT NULL "
                                    "DEFAULT ''")

    def connect(self, initialize=True):
        if initialize:
            self.initialize()
            self.add_source_files_to_schema()
        return sqlite3.connect(self.app.config['SHELF_SQLITE_FILEPATH'])

    def connection(self):
        return closing(self.connect())

    def get(self, site, rule):
        with self.connection() as db:
            cursor = db.execute('SELECT context FROM contexts '
                                'WHERE site = ? AND rule = ? '
                                'ORDER BY id DESC;', (site, rule))
            result = cursor.fetchone()
            if result is None:
                return {}
            return pickle.loads(str(result[0]))

    def source(self, site, rule):
        with self.connection() as db:
            cursor = db.execute('SELECT source_files FROM contexts '
                                'WHERE site = ? AND rule = ? '
                                'ORDER BY id DESC;', (site, rule))
            result = cursor.fetchone()
            if result is None:
                return []
            return pickle.loads(str(result[0]))

    def put(self, site, rule, context, source_files=None):
        if source_files is None:
            source_files = [None]

        with self.connection() as db:
            # Preserve existing source files
            cursor = db.execute('SELECT source_files '
                                'FROM contexts '
                                'WHERE site = ? AND rule = ?;',
                                (site, rule))
            existing_source_files = cursor.fetchone()
            if existing_source_files:
                existing_source_files = pickle.loads(str(existing_source_files[0]))
                source_files += existing_source_files
                source_files = sorted(list(set(source_files)))

            # Check to see if the context is already shelved.
            cursor = db.execute('SELECT id FROM contexts '
                                'WHERE site = ? AND rule = ?;', (site, rule))
            serialized_context = pickle.dumps(context, HIGHEST_PROTOCOL)
            serialized_source_files = pickle.dumps(source_files, HIGHEST_PROTOCOL)
            # Optimize pickle size, and conform it to sqlite's BLOB type.
            serialized_context = blobify(pickletools.optimize(serialized_context))
            serialized_source_files = blobify(pickletools.optimize(serialized_source_files))

            if cursor.fetchone() is None:
                db.execute('INSERT INTO contexts '
                           '(site, rule, context, source_files) VALUES (?, ?, ?, ?);',
                           (site, rule, serialized_context, serialized_source_files))
            else:
                db.execute('UPDATE contexts '
                           'SET context = ?, '
                           '    source_files = ? '
                           'WHERE site = ? AND rule = ?;',
                           (serialized_context, serialized_source_files, site, rule))
            db.commit()

    def drop(self, site, rule=None):
        if rule is None:
            rule = '%'
        with self.connection() as db:
            cursor = db.execute('SELECT id FROM contexts '
                                'WHERE site = ? '
                                'AND rule LIKE ?;', (site, rule))
            if cursor.fetchone() is not None:
                db.execute('DELETE FROM contexts '
                           'WHERE site = ? AND rule LIKE ?;', (site, rule))

                db.commit()

    def list(self, site=None, rule=None):
        if site is None:
            site = '%'
        if rule is None:
            rule = '%'
        with self.connection() as db:
            cursor = db.execute('SELECT site, rule FROM contexts '
                                'WHERE site LIKE ? AND rule LIKE ?;',
                                (site, rule))
            return cursor.fetchall()
