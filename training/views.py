import re, urllib.parse, random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count, Sum
from django.utils.html import mark_safe
from .models import Scenario, UserResponse

URL_RE = re.compile(r'https?://[^\s]+')

@login_required
def home(request):
    scenarios = Scenario.objects.all()
    return render(request, 'training/home.html', {'scenarios': scenarios})


def _mutate_url(original_url):
    try:
        parsed = urllib.parse.urlsplit(original_url)
        host = parsed.hostname or ""
        parts = host.split(".")
        if len(parts) >= 2:
            parts[-2] = parts[-2] + "-v" + str(random.randint(2,99))
            new_host = ".".join(parts)
        else:
            new_host = host + "-v" + str(random.randint(2,99))
        netloc = new_host
        if parsed.port:
            netloc = f"{new_host}:{parsed.port}"
        new_url = urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        return new_url
    except Exception:
        return original_url + "?v=" + str(random.randint(2,9999))


def _mutate_url_harder(original_url):
        parsed = urllib.parse.urlsplit(original_url)
        host = (parsed.hostname or "")
        parts = host.split(".")
        if len(parts) >= 2:
        # Add a short word before the TLD segment (e.g. bank-login-security-update -> bank-login-security-update-sec)
            parts[-2] = parts[-2] + "-sec"   # Minor change to the part before the TLD
            new_host = ".".join(parts)
        else:
            new_host = host + "-sec"
        # We keep the scheme (https) but we will keep it text only
        new_path = (parsed.path.rstrip("/") or "") + "/secure-login"
        return urllib.parse.urlunsplit((parsed.scheme or "https", new_host, new_path, parsed.query, parsed.fragment))


def _inject_local_landing_harder(request, scenario):

    from .views import URL_RE
    lang = getattr(request, "LANGUAGE_CODE", "") or request.LANGUAGE_CODE
    msg = scenario.message_ar if (lang == "ar" and getattr(scenario, "message_ar", None)) else scenario.message or ""
    if not msg:
        return ""

    m = URL_RE.search(msg)
    if not m:
        return msg

    raw_url = m.group(0)
    mutated = _mutate_url_harder(raw_url)

    landing = request.build_absolute_uri(reverse("track_landing", args=[scenario.id]))
    tracked = f"{landing}?u={urllib.parse.quote(mutated, safe='')}"
    html = msg.replace(raw_url, f'<a href="{tracked}">{mutated}</a>')
    return mark_safe(html)




def _inject_local_landing_with_mutation(request, scenario):
    lang = getattr(request, "LANGUAGE_CODE", "") or request.LANGUAGE_CODE
    msg = scenario.message_ar if (lang == "ar" and getattr(scenario, "message_ar", None)) else scenario.message or ""
    if not msg:
        return ""

    m = URL_RE.search(msg)
    if not m:
        return msg

    raw_url = m.group(0)
    mutated = _mutate_url(raw_url)
    landing = request.build_absolute_uri(reverse("track_landing", args=[scenario.id]))
    tracked = f"{landing}?u={urllib.parse.quote(mutated, safe='')}"
    html = msg.replace(raw_url, f'<a href="{tracked}">{mutated}</a>')
    return mark_safe(html)



@login_required
def retake_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    # ======= for the new retake =======
    display_title = "Finance Team: Payment Pending"
    base_message  = (
        "Dear colleague,\n"
        "A pending payment is awaiting approval for your department. "
        "To avoid delays, please review the invoice using the link below:\n"
        "https://internal-invoice-company.com/payment-view"
    )
    # ==============================================
    ctx = "payment_retake"
    rendered_message = _render_with_tracking(request, scenario.id, base_message, ctx=ctx)


    return render(request, "training/scenario.html", {
        "scenario": scenario,
        "display_title": display_title,  #alternative title
        "rendered_message": rendered_message,  #New text with tracking
        "retake_mode": True,
        "retake_level": "hard",
        "display_title": "Finance Team: Payment Pending",
        "ctx": ctx,
    })


def _save_user_response(user, scenario, action):

    """
    The response is saved in a way that matches the model's structure:
    - If the UserResponse has clicked/reported fields, it stores them as two columns.
    - Otherwise, it uses a text action field.
    """
    field_names = {f.name for f in UserResponse._meta.get_fields()}
    if {"clicked", "reported"}.issubset(field_names):
        UserResponse.objects.create(
            user=user,
            scenario=scenario,
            clicked=(action == "click"),
            reported=(action == "report"),
        )
    else:
        # Assume there is a text field 'action'
        UserResponse.objects.create(
            user=user,
            scenario=scenario,
            action=action,
        )


@login_required
def scenario_view(request, pk):
    scenario = get_object_or_404(Scenario, pk=pk)
    rendered_message = _inject_local_landing_harder(request, scenario)

    if request.method == "POST":
        action = request.POST.get("action")
        ctx = request.POST.get("ctx")

        if action in {"report", "click"}:

            UserResponse.objects.create(
                user=request.user, scenario=scenario,
                clicked=(action == "click"),
                reported=(action == "report"),
            )

        #Thank you message for payments context
        if action == "report" and ctx == "payment_retake":
            return render(request, "training/feedback.html", {
                "title": "Thank you for reporting this suspicious payment notice.",
                "body": (
                    "You have successfully identified a possible phishing attempt—attackers often impersonate finance "
                    "teams to lure employees into clicking on fake invoice links. Your vigilance helps keep your department "
                    "and company safe. Always be cautious with urgent payment requests or unfamiliar links."
                ),
                "back_url": reverse("scenario", args=[scenario.id]),
            })

        # Default: Return to same page or general thanks page
        return render(request, "training/thanks.html", {
            "clicked": action == "click",
            "reported": action == "report",
        })

    return render(request, "training/scenario.html", {
        "scenario": scenario,
        "rendered_message": rendered_message,
    })




@login_required
def phishing_scenario(request, scenario_id):
    # Reuses the same logic with a different parameter name.
    return scenario_view(request, pk=scenario_id)



def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'training/signup.html', {'form': form})


def _inject_local_landing(request, scenario):

    lang = getattr(request, "LANGUAGE_CODE", "") or request.LANGUAGE_CODE
    msg = scenario.message_ar if (lang == "ar" and getattr(scenario, "message_ar", None)) else scenario.message
    if not msg:
        return msg or ""

    m = URL_RE.search(msg)
    if not m:
        return msg

    raw_url = m.group(0)
    landing = request.build_absolute_uri(reverse("track_landing", args=[scenario.id]))
    tracked = f"{landing}?u={urllib.parse.quote(raw_url, safe='')}"
    html = msg.replace(raw_url, f'<a href="{tracked}">{raw_url}</a>')
    return mark_safe(html)

@login_required
def track_landing(request, scenario_id):
    from django.shortcuts import get_object_or_404
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    original_url = request.GET.get("u", "")
    ctx = request.GET.get("ctx")

    # stpre as it is "click"
    UserResponse.objects.create(
        user=request.user,
        scenario=scenario,
        clicked=True,
        reported=False,
    )

    if ctx == "payment_retake":
        title = "You clicked on a link in a payment message that could be a phishing attempt."
        body = (
            "Fraudsters frequently use fake invoice notifications to steal sensitive information or compromise company "
            "accounts. Always verify unexpected payment requests and look closely at the sender and link addresses "
            "before taking any action."
        )
    else:
        title = "You clicked the link"
        body = ""

    # Show landing page
    return render(request, "training/track_landing.html", {
        "title": title,
        "body": body,
        "original_url": original_url,
        "scenario": scenario,
        "ctx": request.GET.get("ctx", ""),
    })

def _render_with_tracking(request, scenario_id, raw_text, ctx=None):
    """It takes a raw text with a URL in it, extracts the first URL, distorts it, and links it to the track_landing page to record the click."""
    m = URL_RE.search(raw_text or "")
    if not m:
        return mark_safe(raw_text or "")
    raw_url = m.group(0)
    mutated = _mutate_url_harder(raw_url)
    landing = request.build_absolute_uri(reverse("track_landing", args=[scenario_id]))

    params = {"u": mutated}
    if ctx:
        params["ctx"] = ctx

    tracked = f"{landing}?{urllib.parse.urlencode(params)}"
    html = (raw_text or "").replace(raw_url, f'<a href="{tracked}">{mutated}</a>')
    return mark_safe(html)




@login_required
def report(request):
    mine = (UserResponse.objects
            .filter(user=request.user)
            .aggregate(
                total=Count('id'),
                clicks=Sum('clicked'),
                reports=Sum('reported')))
    per_scenario = (UserResponse.objects
                    .values('scenario__title')
                    .annotate(
                        total=Count('id'),
                        clicks=Sum('clicked'),
                        reports=Sum('reported'))
                    .order_by('-total'))
    return render(request, 'training/report.html',
                  {'mine': mine, 'per_scenario': per_scenario})
#total = mine.get("total") or 0
#correct = mine.get("reports") or 0
#accuracy_pct = round((correct / total) * 100, 2) if total else 0.0

#context = {
#    "mine": mine,
#    "per_scenario": per_scenario,
#    "accuracy_pct": accuracy_pct,
#}



def scenario_list(request):
   first = Scenario.objects.order_by('id').first()
   return redirect('phishing_scenario', scenario_id=first.id) if first else redirect('home')
