"""
Create solution bulk packages in admin:
- Year solutions: All solution PDFs in one year = Rs 50
- Topic solutions: All solution PDFs in all subjects of one topic = Rs 150

Run: python manage.py create_solution_packages

Creates packages only for years/topics that have solution PDFs.
Skips if a matching package already exists.
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from pdf_app.models import PDFFile, PDFPackage, Topic


class Command(BaseCommand):
    help = 'Create Year (Rs 50) and Topic (Rs 150) solution packages for bulk buy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year-price',
            type=float,
            default=50,
            help='Price for Year solutions package (default: 50)',
        )
        parser.add_argument(
            '--topic-price',
            type=float,
            default=150,
            help='Price for Topic solutions package (default: 150)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving',
        )

    def handle(self, *args, **options):
        year_price = Decimal(str(options['year_price']))
        topic_price = Decimal(str(options['topic_price']))
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN – no changes will be saved'))

        created = 0

        # 1. Year solutions packages (Rs 50 each)
        years_with_solutions = PDFFile.objects.filter(
            pdf_type__in=['SOLUTION', 'BOTH']
        ).values_list('year', flat=True).distinct().order_by('-year')

        for year in years_with_solutions:
            existing = PDFPackage.objects.filter(
                package_type='YEAR',
                year=year,
                subject__isnull=True,
                topic__isnull=True,
                content_type='SOLUTIONS',
                is_active=True,
            ).first()

            if existing:
                self.stdout.write(f'  Skip: Year {year} solutions package already exists (id={existing.id})')
                continue

            name = f'Year {year} Solutions'
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f'  Would create: {name} – Rs {year_price}'))
                created += 1
                continue

            pkg = PDFPackage.objects.create(
                name=name,
                package_type='YEAR',
                year=year,
                subject=None,
                topic=None,
                content_type='SOLUTIONS',
                price=year_price,
                is_active=True,
            )
            # Trigger PDF auto-fill via admin save logic (or utils.get_pdfs_for_package)
            from pdf_app.utils import get_pdfs_for_package
            pdfs = list(get_pdfs_for_package(pkg).values_list('id', flat=True))
            pkg.pdfs.set(pdfs)
            self.stdout.write(self.style.SUCCESS(f'  Created: {name} – Rs {year_price} ({len(pdfs)} PDFs)'))
            created += 1

        # 2. Topic solutions packages (Rs 150 each)
        for topic in Topic.objects.all():
            has_solutions = PDFFile.objects.filter(
                subject__topic=topic,
                pdf_type__in=['SOLUTION', 'BOTH'],
            ).exists()

            if not has_solutions:
                self.stdout.write(f'  Skip: Topic "{topic.name}" has no solution PDFs')
                continue

            existing = PDFPackage.objects.filter(
                package_type='TOPIC',
                topic=topic,
                subject__isnull=True,
                year__isnull=True,
                content_type='SOLUTIONS',
                is_active=True,
            ).first()

            if existing:
                self.stdout.write(f'  Skip: Topic "{topic.name}" solutions package already exists (id={existing.id})')
                continue

            name = f'{topic.name} Solutions – All subjects'
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f'  Would create: {name} – Rs {topic_price}'))
                created += 1
                continue

            pkg = PDFPackage.objects.create(
                name=name,
                package_type='TOPIC',
                topic=topic,
                subject=None,
                year=None,
                content_type='SOLUTIONS',
                price=topic_price,
                is_active=True,
            )
            from pdf_app.utils import get_pdfs_for_package
            pdfs = list(get_pdfs_for_package(pkg).values_list('id', flat=True))
            pkg.pdfs.set(pdfs)
            self.stdout.write(self.style.SUCCESS(f'  Created: {name} – Rs {topic_price} ({len(pdfs)} PDFs)'))
            created += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nWould create {created} package(s). Run without --dry-run to save.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nCreated {created} solution package(s).'))
