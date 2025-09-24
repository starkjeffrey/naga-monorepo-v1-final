#!/usr/bin/env python3
"""
Database Backup Tool for NAGA Local PostgreSQL
===============================================
8-word summary: Backup and restore local PostgreSQL database safely
Services/apps involved: PostgreSQL, Docker
Date created: 2025-09-23
Date last modified: 2025-09-23
Status: COMPLETE

This script provides backup and restore functionality for the local PostgreSQL database.
"""

import argparse
import gzip
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class DatabaseBackupTool:
    """Manage PostgreSQL database backups for the NAGA system."""

    def __init__(self):
        # Docker configuration
        self.docker_compose_file = Path(__file__).parent.parent.parent.parent / "docker-compose.local.yml"
        self.container_name = "django-postgres"  # Default container name
        self.db_name = "naga_local"
        self.db_user = "debug"
        self.db_password = "debug"
        self.db_host = "postgres"  # Service name in docker-compose

        # Backup configuration
        self.backup_dir = Path(__file__).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def get_timestamp(self):
        """Generate a timestamp for backup files."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def run_docker_command(self, command, capture_output=False):
        """Run a command in the postgres docker container."""
        docker_cmd = ["docker", "compose", "-f", str(self.docker_compose_file), "exec", "-T", "postgres", *command]

        try:
            if capture_output:
                result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
                return result.stdout
            else:
                subprocess.run(docker_cmd, check=True)
                return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running command: {e}")
            if capture_output and e.stderr:
                print(f"Error output: {e.stderr}")
            return None

    def check_docker_running(self):
        """Check if the PostgreSQL container is running."""
        try:
            cmd = [
                "docker",
                "compose",
                "-f",
                str(self.docker_compose_file),
                "ps",
                "--services",
                "--filter",
                "status=running",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return "postgres" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def get_database_size(self):
        """Get the current database size."""
        query = f"SELECT pg_size_pretty(pg_database_size('{self.db_name}'));"
        result = self.run_docker_command(
            ["psql", "-U", self.db_user, "-d", self.db_name, "-t", "-c", query], capture_output=True
        )

        if result:
            return result.strip()
        return "Unknown"

    def backup_database(self, custom_name=None, compressed=True):
        """Create a backup of the database."""
        if not self.check_docker_running():
            print("❌ PostgreSQL container is not running!")
            print("Start it with: docker compose -f backend/docker-compose.local.yml up -d postgres")
            return False

        timestamp = self.get_timestamp()

        # Determine backup filename
        if custom_name:
            base_name = f"{custom_name}_{timestamp}"
        else:
            base_name = f"naga_backup_{timestamp}"

        backup_file = self.backup_dir / f"{base_name}.sql"

        print(f"🔍 Database size: {self.get_database_size()}")
        print(f"📦 Starting backup to: {backup_file.name}")

        # Create pg_dump command
        dump_cmd = [
            "pg_dump",
            "-U",
            self.db_user,
            "-d",
            self.db_name,
            "--verbose",
            "--no-owner",
            "--no-acl",
            "--if-exists",
            "--clean",
        ]

        # Run pg_dump and save output
        try:
            docker_cmd = [
                "docker",
                "compose",
                "-f",
                str(self.docker_compose_file),
                "exec",
                "-T",
                "postgres",
                *dump_cmd,
            ]

            with open(backup_file, "w") as f:
                subprocess.run(docker_cmd, stdout=f, check=True)

            # Compress if requested
            if compressed:
                print("🗜️  Compressing backup...")
                compressed_file = backup_file.with_suffix(".sql.gz")
                with open(backup_file, "rb") as f_in:
                    with gzip.open(compressed_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove uncompressed file
                backup_file.unlink()
                backup_file = compressed_file

            # Calculate final size
            size_mb = backup_file.stat().st_size / (1024 * 1024)

            # Create metadata file
            metadata = {
                "timestamp": timestamp,
                "database": self.db_name,
                "compressed": compressed,
                "size_mb": round(size_mb, 2),
                "file": backup_file.name,
            }

            metadata_file = self.backup_dir / f"{base_name}_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            print("✅ Backup completed successfully!")
            print(f"📁 Backup file: {backup_file}")
            print(f"📊 Size: {size_mb:.2f} MB")

            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Backup failed: {e}")
            # Clean up partial backup
            if backup_file.exists():
                backup_file.unlink()
            return False

    def list_backups(self):
        """List all available backups."""
        backups = []

        # Find all SQL and compressed SQL files
        for file in self.backup_dir.glob("*.sql*"):
            # Skip if it's a metadata file
            if file.suffix == ".json":
                continue

            # Check for metadata file
            metadata_file = file.with_suffix("") if file.suffix == ".gz" else file
            metadata_file = metadata_file.with_suffix(".json").with_name(metadata_file.stem + "_metadata.json")

            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                    backups.append(
                        {
                            "file": file.name,
                            "size_mb": metadata.get("size_mb", 0),
                            "timestamp": metadata.get("timestamp", "unknown"),
                            "compressed": metadata.get("compressed", False),
                        }
                    )
            else:
                # No metadata, get basic info
                size_mb = file.stat().st_size / (1024 * 1024)
                backups.append(
                    {
                        "file": file.name,
                        "size_mb": round(size_mb, 2),
                        "timestamp": "unknown",
                        "compressed": file.suffix == ".gz",
                    }
                )

        # Sort by filename (which includes timestamp)
        backups.sort(key=lambda x: x["file"], reverse=True)

        return backups

    def restore_database(self, backup_file, force=False):
        """Restore database from a backup file."""
        if not self.check_docker_running():
            print("❌ PostgreSQL container is not running!")
            print("Start it with: docker compose -f backend/docker-compose.local.yml up -d postgres")
            return False

        backup_path = self.backup_dir / backup_file

        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False

        # Safety check
        if not force:
            print(f"⚠️  WARNING: This will REPLACE the entire {self.db_name} database!")
            print(f"Current database size: {self.get_database_size()}")
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if response != "yes":
                print("Restore cancelled.")
                return False

        print(f"🔄 Restoring from: {backup_file}")

        try:
            # Handle compressed files
            if backup_path.suffix == ".gz":
                print("🗜️  Decompressing backup...")
                docker_cmd = [
                    "docker",
                    "compose",
                    "-f",
                    str(self.docker_compose_file),
                    "exec",
                    "-T",
                    "postgres",
                    "psql",
                    "-U",
                    self.db_user,
                    "-d",
                    self.db_name,
                ]

                with gzip.open(backup_path, "rb") as f:
                    subprocess.run(docker_cmd, stdin=f, check=True)
            else:
                # Regular SQL file
                docker_cmd = [
                    "docker",
                    "compose",
                    "-f",
                    str(self.docker_compose_file),
                    "exec",
                    "-T",
                    "postgres",
                    "psql",
                    "-U",
                    self.db_user,
                    "-d",
                    self.db_name,
                ]

                with open(backup_path) as f:
                    subprocess.run(docker_cmd, stdin=f, check=True)

            print("✅ Database restored successfully!")
            print(f"📊 New database size: {self.get_database_size()}")

            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Restore failed: {e}")
            return False

    def clean_old_backups(self, keep_count=10):
        """Remove old backups, keeping only the most recent ones."""
        backups = self.list_backups()

        if len(backups) <= keep_count:
            print(f"✅ Only {len(backups)} backups exist, no cleanup needed.")
            return

        # Delete oldest backups
        to_delete = backups[keep_count:]

        for backup in to_delete:
            file_path = self.backup_dir / backup["file"]
            metadata_path = (
                file_path.with_suffix("")
                .with_suffix(".json")
                .with_name(file_path.stem.replace(".sql", "") + "_metadata.json")
            )

            print(f"🗑️  Deleting: {backup['file']}")
            if file_path.exists():
                file_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

        print(f"✅ Cleaned up {len(to_delete)} old backups.")


def main():
    parser = argparse.ArgumentParser(
        description="PostgreSQL Database Backup Tool for NAGA System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a backup
  python db_backup.py backup

  # Create a named backup
  python db_backup.py backup --name pre_migration

  # List all backups
  python db_backup.py list

  # Restore from a specific backup
  python db_backup.py restore naga_backup_20250923_143022.sql.gz

  # Clean old backups (keep last 10)
  python db_backup.py clean --keep 10
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a database backup")
    backup_parser.add_argument("--name", help="Custom name for the backup (timestamp will be appended)")
    backup_parser.add_argument("--no-compress", action="store_true", help="Save backup without compression")

    # List command
    subparsers.add_parser("list", help="List available backups")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("backup_file", help="Name of the backup file to restore")
    restore_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean old backups")
    clean_parser.add_argument("--keep", type=int, default=10, help="Number of recent backups to keep (default: 10)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    tool = DatabaseBackupTool()

    if args.command == "backup":
        success = tool.backup_database(custom_name=args.name, compressed=not args.no_compress)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        backups = tool.list_backups()
        if not backups:
            print("No backups found.")
        else:
            print(f"\n{'=' * 80}")
            print(f"{'Backup File':<50} {'Size (MB)':<15} {'Timestamp':<20}")
            print(f"{'=' * 80}")
            for backup in backups:
                compressed = " [GZ]" if backup["compressed"] else ""
                print(f"{backup['file']:<50} {backup['size_mb']:<15.2f} {backup['timestamp']:<20}{compressed}")
            print(f"{'=' * 80}")
            print(f"Total: {len(backups)} backups")

    elif args.command == "restore":
        success = tool.restore_database(args.backup_file, force=args.force)
        sys.exit(0 if success else 1)

    elif args.command == "clean":
        tool.clean_old_backups(keep_count=args.keep)


if __name__ == "__main__":
    main()
