from django.contrib.auth import get_user_model
from django import forms
from .models import Item

User = get_user_model()


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "status",
            "title",
            "description",
            "category",
            "color_primary",
            "brand",
            "model_or_markings",
            "building",
            "room_or_area",
            "date_lost_or_found",
            "photo",
        ]
        widgets = {
            "date_lost_or_found": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow LOST and FOUND in the post form
        allowed = {Item.LOST, Item.FOUND}
        self.fields["status"].choices = [
            (value, label)
            for value, label in Item.STATUS_CHOICES
            if value in allowed
        ]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

class NotifyMatchForm(forms.Form):
    title = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 7}))