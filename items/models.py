from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class Item(models.Model):
    LOST, FOUND, CLAIMED = 'LOST','FOUND','CLAIMED'
    STATUS_CHOICES = [(LOST,'Lost'),(FOUND,'Found'),(CLAIMED,'Claimed')]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='items')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=LOST)

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    color_primary = models.CharField(max_length=30, blank=True)
    brand = models.CharField(max_length=80, blank=True)
    model_or_markings = models.CharField(max_length=120, blank=True)

    building = models.CharField(max_length=120, blank=True)
    room_or_area = models.CharField(max_length=120, blank=True)

    date_lost_or_found = models.DateField(null=True, blank=True)
    date_reported = models.DateTimeField(auto_now_add=True)

    photo = models.ImageField(upload_to='items/', blank=True, null=True)

    approved = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta: ordering = ['-date_reported']
    def __str__(self): return f'{self.title} ({self.status})'

class Match(models.Model):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (REJECTED, "Rejected"),
    ]

    lost_item = models.ForeignKey(Item, related_name="lost_matches", on_delete=models.CASCADE)
    found_item = models.ForeignKey(Item, related_name="found_matches", on_delete=models.CASCADE)
    score = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lost_item} ↔ {self.found_item} ({self.score})"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    def __str__(self): return f'Msg {self.id} on {self.item_id}'