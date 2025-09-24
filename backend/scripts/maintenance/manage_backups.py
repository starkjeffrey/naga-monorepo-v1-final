#!/usr/bin/env python
"""
Backup management script for Naga SIS.
Lists, creates, and manages database backups.
"""

import json
import subprocess
from datetime import datetime


def get_backup_info():
    """Get information about existing backups."""
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.local.yml", "exec", "postgres", "backups"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Error getting backup list: {result.stderr}")
        return []

    # Parse the backup list
    backups = []
    lines = result.stdout.strip().split("\n")

    for line in lines:
        if line and not line.startswith("listing") and ".sql.gz" in line:
            # Extract backup filename and info
            parts = line.split()
            if len(parts) >= 9:  # Standard ls -la format
                size = parts[4]
                date = " ".join(parts[5:8])
                filename = parts[8]
                backups.append({"filename": filename, "size": size, "date": date})

    return backups


def create_backup(description=None):
    """Create a new database backup."""
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    if description:
        # Sanitize description for filename
        safe_desc = description.replace(" ", "_").replace("/", "_")[:50]
        backup_name = f"backup_{timestamp}_{safe_desc}"
    else:
        backup_name = f"backup_{timestamp}"

    print(f"🔄 Creating backup: {backup_name}.sql.gz")

    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.local.yml", "exec", "postgres", "backup"],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ Backup created successfully!")
        print(result.stdout)
        return True
    else:
        print(f"❌ Backup failed: {result.stderr}")
        return False


def list_backups():
    """List all available backups."""
    backups = get_backup_info()

    if not backups:
        print("📭 No backups found.")
        return

    print("\n📋 Available Backups:")
    print("-" * 80)
    print(f"{'Filename':<50} {'Size':>10} {'Date':<20}")
    print("-" * 80)

    total_size = 0
    for backup in backups:
        print(f"{backup['filename']:<50} {backup['size']:>10} {backup['date']:<20}")
        try:
            # Convert size to bytes for total
            size_value = backup["size"]
            if size_value.endswith("K"):
                total_size += int(float(size_value[:-1]) * 1024)
            elif size_value.endswith("M"):
                total_size += int(float(size_value[:-1]) * 1024 * 1024)
            elif size_value.endswith("G"):
                total_size += int(float(size_value[:-1]) * 1024 * 1024 * 1024)
            else:
                total_size += int(float(size_value))
        except (ValueError, TypeError):
            pass

    print("-" * 80)
    print(f"Total: {len(backups)} backups, ~{total_size / (1024 * 1024):.2f} MB")


def create_backup_metadata():
    """Create metadata file for the latest backup."""
    backups = get_backup_info()
    if not backups:
        print("❌ No backups to create metadata for.")
        return

    latest_backup = backups[-1]  # Assuming last one is the latest

    metadata = {
        "filename": latest_backup["filename"],
        "created_at": datetime.now().isoformat(),
        "size": latest_backup["size"],
        "database": "naga_local",
        "fixtures_generated": True,
        "description": "Regular backup with fixtures",
    }

    metadata_file = f"backup_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"📄 Metadata saved to: {metadata_file}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage database backups")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    subparsers.add_parser("list", help="List all backups")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument("-d", "--description", help="Backup description")
    create_parser.add_argument("-m", "--metadata", action="store_true", help="Create metadata file")

    # Info command
    subparsers.add_parser("info", help="Show backup statistics")

    args = parser.parse_args()

    if args.command == "list":
        list_backups()
    elif args.command == "create":
        if create_backup(args.description):
            if args.metadata:
                create_backup_metadata()
    elif args.command == "info":
        backups = get_backup_info()
        print("\n📊 Backup Statistics:")
        print(f"   Total backups: {len(backups)}")
        if backups:
            print(f"   Latest backup: {backups[-1]['filename']}")
            print(f"   Latest size: {backups[-1]['size']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
