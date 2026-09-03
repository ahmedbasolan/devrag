"""
Database Migration Manager

Handles schema migrations for the e-commerce database.
Supports both forward and rollback migrations.
"""

import os
import json
from datetime import datetime
from pathlib import Path


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL', 'sqlite:///store.db')
        self.migrations_dir = Path(__file__).parent / 'migrations'
        self.migrations_dir.mkdir(exist_ok=True)
        self.applied = self._load_applied()

    def _load_applied(self):
        """Load list of applied migrations."""
        state_file = self.migrations_dir / '.applied.json'
        if state_file.exists():
            return json.loads(state_file.read_text())
        return []

    def _save_applied(self):
        """Persist applied migrations list."""
        state_file = self.migrations_dir / '.applied.json'
        state_file.write_text(json.dumps(self.applied, indent=2))

    def create_migration(self, name, up_sql, down_sql):
        """Create a new migration file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f'{timestamp}_{name}.json'
        migration = {
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'up': up_sql,
            'down': down_sql
        }
        filepath = self.migrations_dir / filename
        filepath.write_text(json.dumps(migration, indent=2))
        print(f'Created migration: {filename}')
        return filepath

    def migrate_up(self, steps=None):
        """Apply pending migrations."""
        pending = self._get_pending()
        if steps:
            pending = pending[:steps]

        for migration_file in pending:
            migration = json.loads(migration_file.read_text())
            print(f'Applying: {migration["name"]}')
            self._execute_sql(migration['up'])
            self.applied.append(migration_file.name)
            self._save_applied()

        print(f'Applied {len(pending)} migration(s)')

    def migrate_down(self, steps=1):
        """Rollback the last N migrations."""
        to_rollback = self.applied[-steps:] if steps else self.applied[:]

        for filename in reversed(to_rollback):
            migration_file = self.migrations_dir / filename
            if migration_file.exists():
                migration = json.loads(migration_file.read_text())
                print(f'Rolling back: {migration["name"]}')
                self._execute_sql(migration['down'])
                self.applied.remove(filename)

        self._save_applied()
        print(f'Rolled back {len(to_rollback)} migration(s)')

    def _get_pending(self):
        """Get list of unapplied migrations in order."""
        all_migrations = sorted(self.migrations_dir.glob('*.json'))
        return [m for m in all_migrations if m.name not in self.applied]

    def _execute_sql(self, sql):
        """Execute SQL statement against the database."""
        # In production, this would use the actual DB connection
        print(f'  SQL: {sql[:80]}...')

    def status(self):
        """Show migration status."""
        pending = self._get_pending()
        print(f'Applied: {len(self.applied)}')
        print(f'Pending: {len(pending)}')
        for m in pending:
            print(f'  - {m.name}')


# Pre-defined migrations for the e-commerce schema

MIGRATIONS = {
    '001_create_users': {
        'up': '''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                role VARCHAR(20) DEFAULT 'customer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''',
        'down': 'DROP TABLE IF EXISTS user;'
    },
    '002_create_products': {
        'up': '''
            CREATE TABLE IF NOT EXISTS product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price FLOAT NOT NULL,
                stock INTEGER DEFAULT 0,
                category VARCHAR(100),
                vendor_id INTEGER REFERENCES user(id),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''',
        'down': 'DROP TABLE IF EXISTS product;'
    },
    '003_create_orders': {
        'up': '''
            CREATE TABLE IF NOT EXISTS "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES user(id) NOT NULL,
                total FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER REFERENCES "order"(id) NOT NULL,
                product_id INTEGER REFERENCES product(id) NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price FLOAT NOT NULL
            );
        ''',
        'down': 'DROP TABLE IF EXISTS order_item; DROP TABLE IF EXISTS "order";'
    },
    '004_add_indexes': {
        'up': '''
            CREATE INDEX idx_products_category ON product(category);
            CREATE INDEX idx_products_vendor ON product(vendor_id);
            CREATE INDEX idx_orders_user ON "order"(user_id);
            CREATE INDEX idx_orders_status ON "order"(status);
        ''',
        'down': '''
            DROP INDEX IF EXISTS idx_products_category;
            DROP INDEX IF EXISTS idx_products_vendor;
            DROP INDEX IF EXISTS idx_orders_user;
            DROP INDEX IF EXISTS idx_orders_status;
        '''
    }
}


if __name__ == '__main__':
    import sys

    manager = MigrationManager()

    if len(sys.argv) < 2:
        print('Usage: python db_migration.py [status|up|down|create NAME]')
        sys.exit(1)

    command = sys.argv[1]

    if command == 'status':
        manager.status()
    elif command == 'up':
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else None
        manager.migrate_up(steps)
    elif command == 'down':
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        manager.migrate_down(steps)
    elif command == 'create' and len(sys.argv) > 2:
        name = sys.argv[2]
        if name in MIGRATIONS:
            m = MIGRATIONS[name]
            manager.create_migration(name, m['up'], m['down'])
        else:
            print(f'Unknown migration: {name}')
    else:
        print(f'Unknown command: {command}')
