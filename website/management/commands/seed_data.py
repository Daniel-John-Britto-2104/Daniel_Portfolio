from django.core.management.base import BaseCommand
from website.portfolio_defaults import seed_database_tables


class Command(BaseCommand):
    help = "Seed database with Daniel John Britto's updated portfolio and resume data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            default=True,
            help="Wipe and recreate all portfolio records with canonical data (default True)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding portfolio data..."))
        force = options.get("force", True)
        seed_database_tables(force=force)
        self.stdout.write(self.style.SUCCESS("Successfully seeded all portfolio database tables!"))
