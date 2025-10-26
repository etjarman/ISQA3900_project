from django.core.management.base import BaseCommand
from items.models import Category
DEFAULTS = ['Backpack','Laptop','Phone','Keys','ID Card','Water Bottle','Clothing','Calculator','Headphones']
class Command(BaseCommand):
    help = 'Seed default categories'
    def handle(self, *args, **kwargs):
        n = 0
        for name in DEFAULTS:
            _, created = Category.objects.get_or_create(name=name)
            n += int(created)
        self.stdout.write(self.style.SUCCESS(f'Seeded categories. New: {n}'))