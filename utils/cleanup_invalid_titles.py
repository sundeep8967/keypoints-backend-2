#!/usr/bin/env python3
"""
Database Cleanup Script
Removes articles with invalid titles (metadata/schedule) from Supabase
"""

from db.supabase_integration import SupabaseNewsDB

def main():
    print("🧹 Starting database cleanup for invalid titles...")
    print("="*60)
    
    try:
        # Initialize database connection
        db = SupabaseNewsDB()
        
        # Run cleanup
        cleanup_stats = db.cleanup_invalid_titles()
        
        print("\n" + "="*60)
        print("📊 CLEANUP SUMMARY")
        print("="*60)
        print(f"📰 Total articles checked: {cleanup_stats['total_checked']}")
        print(f"❌ Invalid titles found: {cleanup_stats['invalid_titles_found']}")
        print(f"🗑️  Articles removed: {cleanup_stats['articles_removed']}")
        
        if cleanup_stats['articles_removed'] > 0:
            print(f"\n✅ Successfully cleaned {cleanup_stats['articles_removed']} invalid articles!")
            print("🎉 Your database now contains only valid news article titles.")
        else:
            print("\n✅ No invalid titles found - your database is clean!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()