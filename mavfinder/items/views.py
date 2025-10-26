from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Q
from .models import Item, Match
from .forms import ItemForm
from .matching import find_matches_for

def home(request):
    items = Item.objects.filter(approved=True)[:12]
    return render(request, 'items/home.html', {'items': items})

def item_list(request):
    q = request.GET.get('q',''); status = request.GET.get('status','')
    qs = Item.objects.filter(approved=True)
    if q: qs = qs.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(brand__icontains=q))
    if status in ('LOST','FOUND','CLAIMED'): qs = qs.filter(status=status)
    return render(request, 'items/item_list.html', {'items': qs, 'q': q, 'status': status})

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False); item.owner = request.user; item.save()
            for other, score in find_matches_for(item):
                if item.status == 'LOST':
                    Match.objects.get_or_create(lost_item=item, found_item=other, defaults={'score': score})
                else:
                    Match.objects.get_or_create(lost_item=other, found_item=item, defaults={'score': score})
            messages.success(request, 'Item posted successfully.')
            return redirect('items:item_detail', pk=item.pk)
    else:
        form = ItemForm()
    return render(request, 'items/item_form.html', {'form': form})

def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    matches = []
    if request.user.is_authenticated and request.user == item.owner:
        if item.status == 'LOST':
            matches = Match.objects.filter(lost_item=item).select_related('found_item')
        elif item.status == 'FOUND':
            matches = Match.objects.filter(found_item=item).select_related('lost_item')
    return render(request, 'items/item_detail.html', {'item': item, 'matches': matches})

@user_passes_test(lambda u: u.is_staff)
def match_review(request):
    pending = Match.objects.filter(status__in=['PENDING','NOTIFIED']).select_related('lost_item','found_item')
    return render(request, 'items/match_review.html', {'matches': pending})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(); login(request, user)
            return redirect('items:home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})