"""
Script để reset database trên Railway
Chạy: railway run python reset_database_railway.py
HOẶC: python reset_database_railway.py (nếu đã set DATABASE_URL)
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import DATABASE_URL, engine
from app.models import Base

def reset_database():
    """Reset database: drop tất cả tables và tạo lại"""
    print("🔄 Resetting database...")
    
    # Kiểm tra connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to database: {version[:50]}...")
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        return False
    
    # Drop tất cả tables
    print("🗑️  Dropping all tables...")
    try:
        # Disable foreign key checks (PostgreSQL)
        with engine.connect() as conn:
            # Drop tables với CASCADE để xóa cả foreign keys
            conn.execute(text("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """))
            conn.commit()
        print("✅ All tables dropped")
    except Exception as e:
        print(f"⚠️  Error dropping tables: {e}")
        # Thử cách khác: drop từng table
        try:
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS teams CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                conn.execute(text("DROP TYPE IF EXISTS team_status CASCADE"))
                conn.commit()
            print("✅ Tables dropped manually")
        except Exception as e2:
            print(f"❌ Error: {e2}")
            return False
    
    # Tạo lại tables từ models
    print("🔨 Creating tables from models...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Reset Alembic version table
    print("🔄 Resetting Alembic version...")
    try:
        with engine.connect() as conn:
            # Drop alembic_version table nếu có
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            conn.commit()
        print("✅ Alembic version reset")
    except Exception as e:
        print(f"⚠️  Could not reset Alembic version: {e}")
    
    print("\n✅ Database reset completed!")
    print("📝 Next steps:")
    print("   1. Run migrations: alembic upgrade head")
    print("   2. Create admin user: python create_admin.py")
    print("   OR restart the app - it will auto-create admin user")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE RESET SCRIPT")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL[:50]}...")
    print()
    
    confirm = input("⚠️  WARNING: This will DELETE ALL DATA! Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Cancelled")
        sys.exit(0)
    
    if reset_database():
        print("\n✅ Database reset successful!")
    else:
        print("\n❌ Database reset failed!")
        sys.exit(1)

