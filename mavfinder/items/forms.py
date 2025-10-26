from django import forms
from .models import Item
class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['status','title','description','category','color_primary','brand',
                  'model_or_markings','building','room_or_area','date_lost_or_found','photo']
        widgets = {
            'date_lost_or_found': forms.DateInput(attrs={'type':'date'}),
            'description': forms.Textarea(attrs={'rows':4})
        }