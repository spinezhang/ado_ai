#!/usr/bin/env python3
"""Helper script to reset the ADO AI database."""

import os
import sys
from pathlib import Path

def reset_database():
    """Reset the database by removing it and recreating all tables."""
    db_path = Path("ado_ai.db")
    backup_path = Path("ado_ai.db.backup")

    print("🗑️  Database Reset Tool")
    print("=" * 50)

    if db_path.exists():
        # Create backup
        if backup_path.exists():
            backup_path.unlink()
        db_path.rename(backup_path)
        print(f"✓ Backup created: {backup_path}")
        print(f"✓ Removed old database: {db_path}")
    else:
        print("ℹ️  No existing database found")

    # Initialize new database
    try:
        from ado_ai_web.database.session import init_db, engine
        from sqlalchemy import inspect

        init_db()

        # Verify tables created
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n✓ Database initialized with {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        print("\n✅ Database reset complete!")
        print("\nNext steps:")
        print("  1. Start the web service: python -m ado_ai_web.main")
        print("  2. Navigate to: http://localhost:8000")
        print("  3. Complete the setup wizard")

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reset ADO AI database")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.no_confirm:
        response = input("\n⚠️  This will delete all data and reset the database. Continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Cancelled.")
            sys.exit(0)

    reset_database()
