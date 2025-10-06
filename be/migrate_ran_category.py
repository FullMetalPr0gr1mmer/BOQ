"""
One-time migration script to populate ran_category for existing RANLvl3 records.

This script updates all existing RANLvl3 records to set the ran_category field based on the category:
- If category contains "FTK" -> ran_category = "FTK Radio"
- Otherwise -> ran_category = "Radio"
"""

from Database.session import SessionLocal
from Models.RAN.RANLvl3 import RANLvl3


def migrate_ran_category():
    """Migrate ran_category for all existing RANLvl3 records."""
    db = SessionLocal()
    try:
        # Fetch all RANLvl3 records
        all_records = db.query(RANLvl3).all()

        updated_count = 0
        skipped_count = 0

        for record in all_records:
            # Skip if ran_category is already set
            if record.ran_category:
                skipped_count += 1
                continue

            # Determine ran_category based on category
            if record.category:
                if "FTK" in record.category:
                    record.ran_category = "FTK Radio"
                else:
                    record.ran_category = "Radio"
                updated_count += 1
            else:
                # If no category, set to None (or you could set a default)
                record.ran_category = None
                skipped_count += 1

        # Commit all changes
        db.commit()

        print(f"✅ Migration completed successfully!")
        print(f"   - Updated: {updated_count} records")
        print(f"   - Skipped: {skipped_count} records")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting ran_category migration...")
    migrate_ran_category()
