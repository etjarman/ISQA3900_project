from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponseForbidden
from .models import Item, Match
from .forms import ItemForm, ProfileForm
from .matching import find_matches_for
from .forms_auth import SignupForm
import logging

logger = logging.getLogger(__name__)

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
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    item = form.save(commit=False)
                    item.owner = request.user
                    # New posts start unapproved
                    item.save()
                    try:
                        # Only compare against approved items
                        for other, score in find_matches_for(item, include_unapproved=False):
                            if item.status == "LOST":
                                Match.objects.get_or_create(lost_item=item, found_item=other, defaults={"score": score})
                            else:
                                Match.objects.get_or_create(lost_item=other, found_item=item, defaults={"score": score})
                    except Exception as e:
                        logger.exception("Match generation failed for item %s: %s", item.pk, e)
                        messages.warning(request, "Item posted, but match generation will run later.")

                messages.success(request, "Item posted successfully and awaiting approval.")
                return redirect("items:item_detail", pk=item.pk)

            except Exception as e:
                logger.exception("Create item failed: %s", e)
                messages.error(request, f"Could not save item: {e}")
        # invalid form OR exception
        return render(request, "items/item_form.html", {"form": form})
    else:
        form = ItemForm()
    return render(request, "items/item_form.html", {"form": form})

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

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import login
            login(request, user)
            return redirect("items:home")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})

@login_required
def my_account(request):
    """Account dashboard: update profile + see/manage your own items."""
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account updated.")
            return redirect("items:account")
    else:
        form = ProfileForm(instance=request.user)

    my_items = Item.objects.filter(owner=request.user).order_by("-date_reported")
    return render(request, "account/dashboard.html", {"form": form, "my_items": my_items})

@login_required
def item_update(request, pk):
    """Owner-only edit."""
    item = get_object_or_404(Item, pk=pk)
    if not (request.user.is_staff or item.owner_id == request.user.id):
        return HttpResponseForbidden("You can only edit your own items.")
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated.")
            return redirect("items:item_detail", pk=item.pk)
    else:
        form = ItemForm(instance=item)
    return render(request, "items/item_form.html", {"form": form, "item": item, "is_edit": True})

@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if not (request.user.is_staff or item.owner_id == request.user.id):
        return HttpResponseForbidden("You can only delete your own items.")
    item.delete()
    messages.success(request, "Item deleted.")
    return redirect("items:account")
