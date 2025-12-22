"""
Script to reset database - delete and recreate from scratch
"""
import os
import sys

# Delete database file if exists
db_path = "tournament.db"
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"OK: Deleted {db_path}")
    except Exception as e:
        print(f"ERROR: Cannot delete {db_path}: {e}")
        print("Please make sure the server is stopped and no process is using the database")
        sys.exit(1)
else:
    print(f"OK: {db_path} does not exist, no need to delete")

# Run migration
print("\nCreating database...")
os.system("python -m alembic upgrade head")
print("\nOK: Database has been reset successfully!")
