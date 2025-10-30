import re, urllib.parse, random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count, Sum
from django.utils.html import mark_safe
from .models import Category, Scenario, ScenarioStep, UserScenarioRun, UserAction, render_step_body
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.views.decorators.http import require_POST
import random, string, csv



URL_RE = re.compile(r'https?://[^\s]+')

@login_required
def home(request):
    categories = Category.objects.all().prefetch_related("scenarios")
    return render(request, "training/home.html", {"categories": categories})


def run_start(request, scenario_id):
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    run = UserScenarioRun.objects.create(
        user=request.user,
        scenario=scenario,
        next_remaining=scenario.depth,
        step_index=1,
        context={
            "bank_name": random.choice(["National Bank","SecurePay","Trust Bank"]),
            "last4": "".join(random.choices(string.digits, k=4)),
            "otp": "".join(random.choices(string.digits, k=6)),
            "student_portal": "https://portal.univ.example",
            "api_token": "tok_" + "".join(random.choices(string.ascii_lowercase+string.digits, k=12)),
        }
    )
    return redirect("training:run_step", run_uuid=run.run_uuid, index=1)


@login_required
def run_step(request, run_uuid, index):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    steps = list(run.scenario.steps.all())
    if index < 1 or index > len(steps): raise Http404()

    step = steps[index-1]
    # Deepest Depth Update
    run.depth_max = max(run.depth_max, index)
    run.save(update_fields=["depth_max"])

    context = run.context
    rendered_body = render_step_body(step, context)

    # Temporary (for IT/professional)
    deadline = None
    if step.timer_seconds:
        deadline = (timezone.now() + timezone.timedelta(seconds=step.timer_seconds)).timestamp()

    return render(request, "training/run_step.html", {
        "run": run,
        "step": step,
        "index": index,
        "total": len(steps),
        "deadline": deadline,
        "rendered_body": rendered_body,
    })


@require_POST
@login_required
def run_action(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    action = request.POST.get("action")  # next/back/click/submit/report/timeout
    step_id = int(request.POST.get("step_id"))
    step = get_object_or_404(ScenarioStep, pk=step_id)

    payload = {}
    if action == "submit":
        # Save any form fields
        for key, val in request.POST.items():
            if key.startswith("f_"):
                payload[key] = val

        # Example: If you enter the MFA/OTP form incorrectly → "Verification failed"
        if step.step_type in ("fake_login","form"):
            payload["verification"] = "failed"

    # points
    delta = UserAction.apply_scoring(action, step.step_type, payload)
    UserAction.objects.create(run=run, step=step, action=action, delta=delta, payload=payload)
    run.score += delta

    # Pointer movement + counters
    if action == "next":
        run.next_count += 1
        run.next_remaining = max(0, run.next_remaining - 1)
        run.step_index = min(run.step_index + 1, run.scenario.steps.count())
    elif action == "back":
        run.back_count += 1
        run.step_index = max(1, run.step_index - 1)
        # back does not increase next_remaining, it only reverses one step
    elif action in ("click","submit","report","timeout"):
        # Remains at the same step, only points/recording
        pass

    run.save()

    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)


@login_required
def track_link(request, run_uuid, step_id, link_slug):
    run  = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    step = get_object_or_404(ScenarioStep, pk=step_id, scenario=run.scenario)
    # register “click”
    delta = UserAction.apply_scoring('click', step.step_type, {})
    UserAction.objects.create(run=run, step=step, action='click', delta=delta)
    run.score += delta
    run.save(update_fields=['score'])
    # Redirect the user to a “fake” page if one exists, or return them to the same step.
    if step.step_type == 'email' and step.link_slug:
        return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index+1)  # Example: This takes it to the fake_login step.
    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)



def reports(request):
    runs = UserScenarioRun.objects.select_related("scenario","user").order_by("-started_at")
    return render(request, "training/reports.html", {"runs": runs})


def reports_csv(request):
    # CSV: session/user/scenario/points/depth/number next/back
    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="scenario_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["User","Scenario","Score","Depth Max","Next Count","Back Count","Started","Finished"])
    for r in UserScenarioRun.objects.select_related("user","scenario"):
        writer.writerow([r.user.username, r.scenario.title, r.score, r.depth_max, r.next_count, r.back_count, r.started_at, r.finished_at])
    return response


def category_detail(request, slug):
    category = get_object_or_404(Category.objects.prefetch_related("scenarios"), slug=slug)
    scenarios = category.scenarios.all()
    return render(request, "training/category_detail.html", {"category": category, "scenarios": scenarios})



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
