from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Item, Match, Notification, Profile
from .forms import ItemForm, ProfileForm, NotifyMatchForm, UserProfileForm
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
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = ProfileForm(request.POST, instance=request.user)
        prof_form = UserProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and prof_form.is_valid():
            user_form.save()
            prof_form.save()
            messages.success(request, "Account information updated.")
            return redirect("items:account")
    else:
        user_form = ProfileForm(instance=request.user)
        prof_form = UserProfileForm(instance=profile)

    my_items = Item.objects.filter(owner=request.user).order_by("-date_reported")

    return render(
        request,
        "account/dashboard.html",
        {
            "user_form": user_form,
            "profile_form": prof_form,
            "my_items": my_items,
        },
    )

@login_required
def item_update(request, pk):
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

@login_required
def notifications(request):
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    return render(request, "items/notifications.html", {"notifications": qs})

@login_required
def notification_mark_read(request, notif_id):
    n = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    if n.url:
        return redirect(n.url)
    return redirect("items:notifications")

@staff_member_required
def review_items(request):

    pending_items = Item.objects.filter(approved=False).order_by("-date_reported")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approve":
            ids = request.POST.getlist("item_ids")
            if not ids:
                messages.warning(request, "No items selected for approval.")
            else:
                qs = Item.objects.filter(id__in=ids)
                count = qs.update(approved=True)
                messages.success(request, f"Approved {count} item(s).")

        updated_matches = 0
        valid_statuses = {Match.PENDING, Match.CONFIRMED, Match.REJECTED}
        for key, value in request.POST.items():
            if not key.startswith("match_status_"):
                continue
            if not value:
                continue

            match_id = key.replace("match_status_", "", 1)
            try:
                match_obj = Match.objects.get(id=match_id)
            except Match.DoesNotExist:
                continue

            if value in valid_statuses and match_obj.status != value:
                match_obj.status = value
                match_obj.save(update_fields=["status"])
                updated_matches += 1

        if updated_matches:
            messages.success(request, f"Updated {updated_matches} match(es).")

        return redirect("items:review_items")

    # Pending items + potential matches
    items_with_matches = []
    for item in pending_items:
        raw_matches = find_matches_for(item, include_unapproved=True)
        items_with_matches.append({
            "item": item,
            "matches": [
                {"item": m[0], "score": m[1]}
                for m in raw_matches[:5]
            ],
        })

    # Approved items + existing matched items
    approved_items = Item.objects.filter(approved=True).order_by("-date_reported")
    approved_items_with_matches = []
    for item in approved_items:
        matches = Match.objects.filter(
            Q(lost_item=item) | Q(found_item=item)
        ).select_related("lost_item", "found_item").order_by("-score")
        approved_items_with_matches.append({
            "item": item,
            "matches": matches,
        })

    context = {
        "items_with_matches": items_with_matches,
        "approved_items_with_matches": approved_items_with_matches,
    }
    return render(request, "items/review_items.html", context)

@staff_member_required
def notify_match(request, match_id):
    match = get_object_or_404(
        Match.objects.select_related("lost_item__owner", "found_item__owner"),
        id=match_id
    )

    lost_owner = getattr(match.lost_item, "owner", None)
    found_owner = getattr(match.found_item, "owner", None)

    recipients = []
    if lost_owner:
        recipients.append(lost_owner)
    if found_owner and found_owner not in recipients:
        recipients.append(found_owner)

    if not recipients:
        messages.error(request, "This match has no associated users to notify.")
        return redirect("items:review_items")

    default_title = "Possible match found for your item"

    match_url = reverse("items:item_detail", args=[match.lost_item.id])

    default_message = (
        f"A potential match was found:\n"
        f"- Lost: {match.lost_item.title}\n"
        f"- Found: {match.found_item.title}\n"
        f"- Score: {match.score}\n\n"
        f"Open the item page to review details."
    )

    if request.method == "POST":
        form = NotifyMatchForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            message_text = form.cleaned_data["message"]

            for u in recipients:
                Notification.objects.create(
                    recipient=u,
                    match=match,
                    title=title,
                    message=message_text,
                    url=match_url,
                    created_by=request.user,
                )

            messages.success(request, f"In-app notification created for {len(recipients)} user(s).")
            return redirect("items:review_items")
    else:
        form = NotifyMatchForm(initial={"title": default_title, "message": default_message})

    return render(request, "items/notify_match.html", {"match": match, "form": form, "recipients": recipients})
