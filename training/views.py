from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
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


from django.views.decorators.http import require_POST

import random, string, csv

# models / helpers
from .models import (
    Category,
    Scenario,
    ScenarioStep,
    UserScenarioRun,
    UserAction,
    render_step_body,
)


def home(request):
    """
    Home page: list of categories
    """
    categories = Category.objects.all().prefetch_related("scenarios")
    return render(request, "training/home.html", {"categories": categories})


def profile(request):
    return render(request, 'training/profile.html')



def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('training:home')
    else:
        form = UserCreationForm()
    return render(request, 'training/signup.html', {'form': form})





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


@login_required
def category_detail(request, slug):
    """
    Category page: shows scenarios that belong to this category
    """
    category = get_object_or_404(Category, slug=slug)
    scenarios = Scenario.objects.filter(category=category)
    return render(
        request,
        "training/category_detail.html",
        {"category": category, "scenarios": scenarios},
    )


@login_required
def run_start(request, scenario_id):
    """
    Start a new run for the user on a specific scenario:
    - Fill a random context (bank/last4/otp/token)
    - Create a UserScenarioRun
    - Redirect to the first step in the scenario
    """
    scenario = get_object_or_404(Scenario, pk=scenario_id)

    # Ensure that the scenario actually has steps
    first_step = scenario.steps.order_by("order").first()
    if not first_step:
        return HttpResponse("No steps available for this scenario.")

    # Create a new run for each user
    run = UserScenarioRun.objects.create(
        user=request.user,
        scenario=scenario,
        next_remaining=scenario.depth if getattr(scenario, "depth", None) else 0,
        step_index=1,
        depth_max=1,
        score=0,
        context={
            "bank_name": random.choice(["National Bank", "SecurePay", "Trust Bank"]),
            "last4": "".join(random.choices(string.digits, k=4)),
            "otp": "".join(random.choices(string.digits, k=6)),
            "student_portal": "https://portal.univ.example",
            "api_token": "tok_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12)),
        },
    )

    # Redirect to the first step (use run.run_uuid instead of scenario_id)
    return redirect("training:run_step", run_uuid=run.run_uuid, index=first_step.order)


@login_required
def run_step(request, run_uuid, index):
    """
    Display a specific step of the scenario for the current run:
    - Validate index
    - Update depth_max
    - Render step body using the run context
    - Calculate deadline if the step is timed
    """
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    steps_qs = list(run.scenario.steps.order_by("order").all())
    total = len(steps_qs)
    if index < 1 or index > total:
         return redirect("training:run_summary", run_uuid=run_uuid)

    step = steps_qs[index - 1]

    # Update the maximum depth reached
    if index > (run.depth_max or 0):
        run.depth_max = index
        run.save(update_fields=["depth_max"])

    # Replace variables in the step body using the stored run context
    context_data = run.context or {}
    rendered_body = render_step_body(step, context_data)

    # If the step is timed, calculate a deadline timestamp (in seconds)
    deadline = None
    if getattr(step, "timer_seconds", None):
        deadline = (timezone.now() + timezone.timedelta(seconds=step.timer_seconds)).timestamp()

    # Calculate previous/next indices for easier navigation
    prev_step = index - 1 if index > 1 else None
    next_step = index + 1 if index < len(steps_qs) else None

    return render(
        request,
        "training/run_step.html",
        {
            "run": run,
            "step": step,
            "step_index": index,
            "total_steps": len(steps_qs),
            "prev_step": prev_step,
            "next_step": next_step,
            "deadline": deadline,
            "rendered_body": rendered_body,
            "run_uuid": run.run_uuid,
        },
    )


@require_POST
@login_required
def run_action(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)

    action = request.POST.get("action")  # expected: next/back/click/submit/report/timeout
    try:
        step_id = int(request.POST.get("step_id"))
    except (TypeError, ValueError):
        return redirect("training:run_summary", run_uuid=run.run_uuid)

    step = get_object_or_404(ScenarioStep, pk=step_id, scenario=run.scenario)
    payload = {}

    # ⬇ Collect form fields (if submit)
    if action == "submit":
        for key, val in request.POST.items():
            if key.startswith("f_"):
                payload[key] = val

    # ⬇ Apply scoring
    delta = UserAction.apply_scoring(action, step.step_type, payload)
    UserAction.objects.create(run=run, step=step, action=action, delta=delta, payload=payload)
    run.score = (run.score or 0) + (delta or 0)

    # ⬇ Back button → go directly to summary
    if action == "back":
       run.back_count = (getattr(run, "back_count", 0) or 0) + 1
    # Set finished_at if not set
       if not run.finished_at:
           run.finished_at = timezone.now()
       run.save(update_fields=["finished_at", "score", "back_count"])
    # Always redirect to summary/score page for back action
       return redirect("training:run_summary", run_uuid=run.run_uuid)

    # ⬇ Next step
    elif action == "next":
        run.next_count = (run.next_count or 0) + 1
        run.next_remaining = max(0, (run.next_remaining or 0) - 1)
        run.step_index = min((run.step_index or 1) + 1, run.scenario.steps.count())

    # ⬇ Other actions
    elif action in ("click", "submit", "report", "timeout"):
        pass

    run.save()
    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)


@login_required
def track_link(request, run_uuid, step_id, link_slug):
    """
    Track link clicks (safe/transformed links) inside emails:
    - Log a click action
    - Redirect to a fake page or move to the next step
    """
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    step = get_object_or_404(ScenarioStep, pk=step_id, scenario=run.scenario)

    delta = UserAction.apply_scoring("click", getattr(step, "step_type", None), {})
    UserAction.objects.create(run=run, step=step, action="click", delta=delta)
    run.score = (run.score or 0) + (delta or 0)
    run.save(update_fields=["score"])

    if step.step_type == "email" and getattr(step, "link_slug", None):
        next_index = run.step_index + 1
        return redirect("training:run_step", run_uuid=run.run_uuid, index=next_index)

    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)


@login_required
def report(request):
    """
    HTML page showing reports/sessions
    """
    runs = UserScenarioRun.objects.select_related("scenario", "user").order_by("-started_at")
    return render(request, "training/report.html", {"runs": runs})


@login_required
def reports_csv(request):
    """
    Download CSV containing summaries of all runs
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="scenario_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["User", "Scenario", "Score", "Depth Max", "Next Count", "Back Count", "Started", "Finished"])

    for r in UserScenarioRun.objects.select_related("user", "scenario").all():
        writer.writerow([
            r.user.username,
            r.scenario.title,
            r.score,
            r.depth_max,
            r.next_count,
            r.back_count,
            r.started_at,
            r.finished_at,
        ])
    return response
@login_required
def run_summary(request, run_uuid):   

    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    steps_done = run.scenario.steps.count() 

    return render(request, "training/run_summary.html", {
        "run": run,
        "steps_done": steps_done,
    })
