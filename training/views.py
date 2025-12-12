from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count, Sum, Q
from django.views.decorators.http import require_POST
import random, string, csv
from .models import ScenarioLog

# Models / helpers
from .models import (
    Category,
    Scenario,
    ScenarioStep,
    UserScenarioRun,
    UserAction,
    UserResponse,
    render_step_body,
)


# -----------------------------
# Home & Profile & Signup
# -----------------------------
def home(request):
    categories = Category.objects.all().prefetch_related("scenarios")
    return render(request, "training/home.html", {"categories": categories})


def profile(request):
    return render(request, "training/profile.html")


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("training:home")
    else:
        form = UserCreationForm()

    return render(request, "training/signup.html", {"form": form})


# -----------------------------
# Scenario Run (Start)
# -----------------------------
@login_required
def run_start(request, scenario_id):
    scenario = get_object_or_404(Scenario, pk=scenario_id)

    first_step = scenario.steps.order_by("order").first()
    if not first_step:
        return HttpResponse("No steps available for this scenario.")

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

    return redirect("training:run_step", run_uuid=run.run_uuid, index=first_step.order)


@csrf_exempt
def log_action(request):
    if request.method == "POST":
        data = json.loads(request.body)

        user = request.user
        scenario_id = data.get("scenario_id")
        step = data.get("step")
        action = data.get("action")
        score = data.get("score")
        run_uuid = data.get("run_uuid")


        scenario = Scenario.objects.get(id=scenario_id)

        ScenarioLog.objects.create(
            user=user,
            scenario=scenario,
            run_uuid=run_uuid,
            action=action,
            step=step,
            score=score
        )

        return JsonResponse({"status": "saved"}, status=200)

    return JsonResponse({"error": "Invalid method"}, status=400)





# -----------------------------
# Scenario Step View
# -----------------------------
@login_required
def run_step(request, run_uuid, index):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    steps = list(run.scenario.steps.order_by("order").all())
    total = len(steps)

    if index < 1 or index > total:
        return redirect("training:run_summary", run_uuid=run_uuid)

    step = steps[index - 1]

    # update depth
    if index > (run.depth_max or 0):
        run.depth_max = index
        run.save(update_fields=["depth_max"])

    rendered_body = render_step_body(step, run, request)

    # timer
    deadline = None
    if getattr(step, "timer_seconds", None):
        deadline = (timezone.now() + timezone.timedelta(seconds=step.timer_seconds)).timestamp()

    return render(
        request,
        "training/run_step.html",
        {
            "run": run,
            "step": step,
            "step_index": index,
            "total_steps": total,
            "prev_step": index - 1 if index > 1 else None,
            "next_step": index + 1 if index < total else None,
            "deadline": deadline,
            "rendered_body": rendered_body,
            "run_uuid": run.run_uuid,
            "scenario_id": run.scenario.id,
            "run": run,
        },
    )


# -----------------------------
# Scenario Action Handler
# -----------------------------
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

    # Collect form fields (if submit)
    if action == "submit":
        for key, val in request.POST.items():
            if key.startswith("f_"):
                payload[key] = val

    # Apply scoring
    delta = UserAction.apply_scoring(action, step.step_type, payload)
    UserAction.objects.create(run=run, step=step, action=action, delta=delta, payload=payload)
    run.score = (run.score or 0) + (delta or 0)


    # 🟥 BACK ACTION → Show custom Security Risk Page
    if action == "back":
        run.back_count = (run.back_count or 0) + 1
        if not run.finished_at:
            run.finished_at = timezone.now()
        current_step = step.order or 1
        scenario_title = run.scenario.title.lower()
        max_score = run.scenario.depth or 5
        # 🔹 Detailed risks for each scenario (6 total)
        detailed_risks = {
            "scholarship delay": {
                1: ("Phishing Link", "You clicked a fake scholarship link leading to a malicious site.", "Attackers could harvest your academic and personal information."),
                2: ("Fake Form", "A fraudulent scholarship form requested personal and financial details.", "Submitting it could expose your identity and student account."),
                3: ("Attachment Risk", "The document was malicious and designed to infect your system.", "Opening it could install spyware stealing stored passwords."),
                4: ("Payment Fraud", "A fake scholarship fee page appeared.", "Proceeding could leak your banking credentials."),
                5: ("Full Compromise", "You nearly handed full access to attackers.", "They could change your passwords and impersonate you."),
            },
            "account security verification": {
                1: ("Login Spoof", "You interacted with a fake login page mimicking your organization's system.", "Entering your credentials would give attackers direct access."),
                2: ("OTP Theft", "A phishing form requested a one-time code.", "Attackers could hijack your MFA session."),
                3: ("Security Update", "The step faked a security update.", "Proceeding could have installed spyware."),
                4: ("Policy Confirmation", "Fake policy acceptance prompt detected.", "Accepting would redirect your data to malicious servers."),
                5: ("Full Breach", "You nearly enabled attackers to control your account fully.", "They could lock you out permanently."),
            },
            "payment confirmation": {
                1: ("Invoice Scam", "You opened a fake invoice attachment.", "It could install malware on your device."),
                2: ("Fake Gateway", "A cloned payment portal was presented.", "Entering card info would send data to attackers."),
                3: ("Receipt Phish", "A forged payment receipt was simulated.", "Responding could reveal company billing info."),
                4: ("Wire Transfer", "You were prompted for a bank transfer confirmation.", "Proceeding could initiate unauthorized transfers."),
                5: ("Financial Breach", "Completing this would let attackers steal company funds.", "They could drain corporate accounts."),
            },
            "service update": {
                1: ("Fake Update Notice", "A fraudulent update alert appeared.", "Clicking would download malware."),
                2: ("Credential Prompt", "A login verification popup was fake.", "Entering data would expose your credentials."),
                3: ("Data Harvesting", "A fake update form collected private info.", "Submitting it would leak sensitive data."),
                4: ("Script Injection", "A malicious download link was shown.", "It could give hackers remote control."),
                5: ("System Compromise", "Completing this would install spyware.", "Hackers could monitor your activities."),
            },
            "password reset": {
                1: ("Fake Reset Notice", "The email claimed you needed to reset your password.", "Clicking would expose your credentials."),
                2: ("Reset Form Phish", "A fake password reset form was displayed.", "Submitting it would send both old and new passwords to attackers."),
                3: ("Session Hijack", "A fake token page was loaded.", "Attackers could take over your session."),
                4: ("Keylogger Attack", "Malicious script attempted to record your keystrokes.", "It could steal login data."),
                5: ("Identity Theft", "Completing would compromise your identity.", "Attackers could impersonate you on internal systems."),
            },
            "cloud reauthentication": {
                1: ("API Token Request", "Fake API re-login email received.", "Entering your data would expose access keys."),
                2: ("Fake Cloud Login", "A cloned cloud login page appeared.", "Attackers could steal organization credentials."),
                3: ("Session Replay", "Phishing script attempted to capture live session cookies.", "Attackers could hijack active admin accounts."),
                4: ("Service Exploit", "Fake service reauthorization prompt detected.", "Granting access would allow full system manipulation."),
                5: ("System Breach", "You nearly allowed attackers administrative control.", "They could alter or delete company data."),
            },
        }

        # Match scenario
        matched_scenario = next((s for s in detailed_risks if s in scenario_title), "account security verification")
        step_data = detailed_risks.get(matched_scenario, {}).get(current_step)

        if step_data:
            risk_type, risk_message, awareness_tip = step_data
        else:
            risk_type, risk_message, awareness_tip = (
                "Phishing Attempt",
                "Unusual activity detected. You avoided a phishing trap.",
                "Always verify sender identity and avoid clicking suspicious links."
            )
        total_steps = run.scenario.steps.count()
        progress_ratio = (total_steps - current_step + 1) / total_steps
        score_gain = int(progress_ratio * max_score)  # 5 points max → 0 min
        run.score = score_gain
        # Feedback message
        if score_gain >= (max_score * 0.8):
            feedback = f"✅ Great awareness! You avoided a major risk early (+{score_gain} points)."
        elif score_gain >= (max_score * 0.4):
            feedback = f"⚠ Decent reaction. You avoided the threat, but later than ideal (+{score_gain} points)."
        else:
            feedback = f"❌ You reacted too late (+{score_gain} points only). Be more cautious next time."
        run.save(update_fields=["finished_at", "score", "back_count"])
        run.last_risk_type = risk_type
        run.save(update_fields=["finished_at", "score", "back_count", "last_risk_type"])
        return render(request, "training/back_risk.html", {
            "scenario_name": run.scenario.title,
            "risk_type": risk_type,
            "risk_message": risk_message,
            "awareness_tip": awareness_tip,
            "score": run.score,
            "run_uuid": run.run_uuid,
            "score_feedback": feedback,
        })

    # 🟩 NEXT ACTION
    elif action == "next":
        run.next_count = (run.next_count or 0) + 1
        run.next_remaining = max(0, (run.next_remaining or 0) - 1)
        run.step_index = min((run.step_index or 1) + 1, run.scenario.steps.count())

    # 🟨 OTHER ACTIONS
    elif action in ("click", "submit", "report", "timeout"):
        pass

    run.save()
    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)



# -----------------------------
# Track Email / Link Click
# -----------------------------
@login_required
def track_link(request, run_uuid, step_id, link_slug):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    step = get_object_or_404(ScenarioStep, pk=step_id, scenario=run.scenario)

    delta = UserAction.apply_scoring("click", getattr(step, "step_type", None), {})
    UserAction.objects.create(run=run, step=step, action="click", delta=delta)
    run.score = (run.score or 0) + (delta or 0)
    run.save(update_fields=['score'])
    
    if step.step_type == "email" and getattr(step, "link_slug", None):
        return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index + 1)
    run.step_index += 1
    run.save(update_fields=['step_index'])
    return redirect("training:run_step", run_uuid=run.run_uuid, index=run.step_index)


# -----------------------------
# Summary Page
# -----------------------------
@login_required
def run_summary(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    user_actions = UserAction.objects.filter(run=run)
    steps_done = run.scenario.steps.count()
    scenario_title = run.scenario.title.lower()

    risk_messages = {
     "credential": (
        "Credential Theft 🛑",
        "You interacted with a fake login page designed to steal your credentials.",
        "🔐 Always verify login pages and password reset links before entering your information."
     ),
     "password": (
        "Credential Theft 🛑",
        "This scenario simulated a password phishing attack.",
        "🟡 Always confirm password reset requests via your official IT system."
     ),
     "payment": (
        "Financial Fraud 💸",
        "You approved or interacted with a fake payment request intended to steal funds.",
        "🟠 Verify every payment request directly with your finance team before proceeding."
     ),
     "invoice": (
        "Financial Fraud 💸",
        "A fraudulent invoice attempt was simulated in this exercise.",
        "🟠 Always confirm invoice legitimacy through your organization’s billing portal."
     ),
     "update": (
        "Malware Infection 🧬",
        "This attack simulated a fake update designed to install malicious software.",
        "🔴 Only download updates from verified or internal IT sources."
     ),
     "security": (
        "System Breach ⚠️",
        "You engaged with a fake security alert that could compromise your account.",
        "🔴 Always report suspicious system alerts to IT before clicking anything."
     ),
     "verification": (
        "Data Theft 🔓",
        "You entered information on a fake verification page designed to collect private data.",
        "🟣 Only verify accounts through official company or service portals."
     ),
     "form": (
        "Privacy Breach 📄",
        "The form you submitted attempted to collect sensitive personal or company information.",
        "🟣 Never submit personal details through unverified web forms."
     ),
    "api": (
        "Cloud / API Compromise ☁️",
        "You authenticated through a fake API or cloud login portal.",
        "🟢 Always access cloud services via official links only."
    ),
    "default": (
        "Simulated Phishing Awareness ⚪",
        "You completed this scenario successfully — it represented a general phishing threat.",
        "💡 Stay alert and verify all links and sender addresses before taking action."
    ),
}

    matched_key = next((key for key in risk_messages if key in scenario_title), "default")
    attack_title, attack_message, awareness_tip = risk_messages[matched_key]

    icon_map = {
        "Financial Fraud": "🟠",
        "Credential Theft": "🔴",
        "Data Theft / Privacy Breach": "🟣",
        "Cloud / API Compromise": "🟢",
        "Malware / System Breach": "⚫",
        "General Awareness": "⚪",
    }
    attack_icon = icon_map.get(attack_title, "⚪")

    return render(request, "training/run_summary.html", {
        "run": run,
        "steps_done": steps_done,
        "user_actions": user_actions,
        "attack_title": attack_title,
        "attack_message": attack_message,
        "awareness_tip": awareness_tip,
        "attack_icon": attack_icon,
    })

# -----------------------------
# Reports (HTML)
# -----------------------------
@login_required
def report(request):
    runs = UserScenarioRun.objects.select_related("scenario", "user").order_by("-started_at")
    return render(request, "training/report.html", {"runs": runs})


# -----------------------------
# Reports (CSV)
# -----------------------------
@login_required
def reports_csv(request):
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


# -----------------------------
# Full Analytics Report
# -----------------------------
@login_required
def report_view(request):
    user = request.user
    START_DATE = timezone.now()
    # 🔹 نحضر فقط الـ Runs المكتملة (finished_at ليس NULL) ونرتبها زمنياً
    runs = (
        UserScenarioRun.objects
        .filter(user=user) # <--- 💡 فلترة Runs المكتملة
        .select_related("scenario__category")
        .prefetch_related("actions") 
        .order_by("scenario__category__name", "started_at")
    )

    # 🔹 نجمع السيناريوهات حسب الكاتيجوري
    from collections import defaultdict
    grouped = defaultdict(list)
    for run in runs:
        cat_name = run.scenario.category.name if run.scenario and run.scenario.category else "Uncategorized"
        grouped[cat_name].append(run)

    # 🔹 دالة مساعدة لتحليل البيانات
    def extract_data(run_list):
        data = []
        for run in run_list:
            actions = run.actions.all()
            back_count = actions.filter(action="back").count()
            next_count = actions.filter(action="next").count()
            
            # 💡 استخدام الـ score المخزن عند الانتهاء (أو 0 إذا لم يُخزن)
            score = run.score or 0

            data.append({
                "category": run.scenario.category.name if run.scenario and run.scenario.category else "Uncategorized",
                "scenario": run.scenario.title,
                "score": score,
                "backs": back_count,
                "nexts": next_count,
                "date": run.finished_at.strftime("%Y-%m-%d %H:%M") if run.finished_at else "—"
            })
        return data

    # 🔹 نحصل على أول 3 runs (الجولة الأولى) وثاني 3 runs (الجولة الثانية) لكل كاتيجوري
    first_set_runs, second_set_runs = [], []
    
    for cat, runs_list in grouped.items():
        # Runs 0, 1, 2 = الجولة الأولى
        first_set_runs.extend(runs_list[0:3]) 
        
        # Runs 3, 4, 5 = الجولة الثانية
        second_set_runs.extend(runs_list[3:6]) 
    
    first_data = extract_data(first_set_runs)
    second_data = extract_data(second_set_runs)


    # 🔹 تجهيز البيانات الأساسية للـ Chart (استعادة المنطق المفقود)
    
    categories = list(set([d["category"] for d in first_data] + [d["category"] for d in second_data]))
    first_scores = [d["score"] for d in first_data]
    second_scores = [d["score"] for d in second_data]

    # 🔹 حساب متوسط الوعي العام (كما كان في الكود الأصلي)
    # نفترض أن الحد الأقصى للـ Score هو 5 كما في الكود الأصلي: min(..., 5)
    max_score_per_run = 5 
    
    first_awareness = round(
        (sum(first_scores) / (len(first_scores) * max_score_per_run)) * 100, 1
    ) if first_scores else 0

    second_awareness = round(
        (sum(second_scores) / (len(second_scores) * max_score_per_run)) * 100, 1
    ) if second_scores else 0


    # 🔹 حساب متوسط الوعي لكل كاتيجوري (للشارت التفصيلي)
    category_scores_first = defaultdict(list)
    category_scores_second = defaultdict(list)

    for d in first_data:
        category_scores_first[d["category"]].append(d["score"])
    for d in second_data:
        category_scores_second[d["category"]].append(d["score"])

    avg_first_per_cat = {cat: round(sum(v)/len(v), 2) for cat, v in category_scores_first.items()}
    avg_second_per_cat = {cat: round(sum(v)/len(v), 2) for cat, v in category_scores_second.items()}

    chart_categories = categories # استخدام الكاتيجوريز التي فيها بيانات مكتملة
    chart_first_awareness = [avg_first_per_cat.get(cat, 0) for cat in chart_categories]
    chart_second_awareness = [avg_second_per_cat.get(cat, 0) for cat in chart_categories]

    # 🔹 تمرير البيانات إلى الصفحة
    context = {
        "first_data": first_data,
        "second_data": second_data,
        "categories": categories,
        "first_scores": first_scores,
        "second_scores": second_scores,
        
        # 💡 المتغيرات التي كانت مفقودة وتسبب الخطأ:
        "first_awareness": first_awareness,
        "second_awareness": second_awareness,
        
        "chart_categories": chart_categories,
        "chart_first_awareness": chart_first_awareness,
        "chart_second_awareness": chart_second_awareness,
    }

    return render(request, "training/report.html", context)
@login_required
def view_risk_details(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    scenario_title = run.scenario.title.lower()

    risk_messages = {
        "credential": (
            "Credential Theft",
            "Attackers attempt to steal your credentials through fake login pages or password reset requests.",
            "🟡 Always verify password reset or login pages before entering your details."
        ),
        "password": (
            "Credential Theft",
            "Fake password reset emails may attempt to capture your login details.",
            "🟡 Check sender domains carefully before resetting your password."
        ),
        "payment": (
            "Financial Fraud",
            "Fake payment portals or invoices aim to steal your money or banking details.",
            "🟠 Always confirm transactions with your finance department directly."
        ),
        "invoice": (
            "Financial Fraud",
            "Phishing invoices can trick employees into making unauthorized transfers.",
            "🟠 Verify payment requests through official communication channels."
        ),
        "update": (
            "Malware / System Breach",
            "Fake update alerts can install malware or steal internal credentials.",
            "🔴 Only download updates from official IT systems or admins."
        ),
        "security": (
            "Malware / System Breach",
            "Fake security warnings may install malicious code or capture access tokens.",
            "🔴 Report suspicious popups to your IT department immediately."
        ),
        "form": (
            "Data Theft / Privacy Breach",
            "Phishing forms collect personal or confidential information.",
            "🟣 Never submit sensitive data through unverified forms."
        ),
        "verification": (
            "Data Theft / Privacy Breach",
            "Fake verification requests mimic trusted institutions to steal private info.",
            "🟣 Ensure verification links match your organization’s real domain."
        ),
        "cloud": (
            "Cloud / API Compromise",
            "Fake cloud re-authentication requests can compromise internal accounts.",
            "🟢 Log in to cloud services only via the official dashboard."
        ),
        "api": (
            "Cloud / API Compromise",
            "Phishing emails targeting API tokens can expose system data.",
            "🟢 Never share authentication tokens via email."
        ),
        "default": (
            "General Awareness",
            "Stay alert to phishing attempts in all forms.",
            "⚪ Always verify senders and avoid clicking unfamiliar links."
        ),
    }

    matched_key = next((key for key in risk_messages if key in scenario_title), "default")
    risk_type, risk_message, awareness_tip = risk_messages[matched_key]

    last_action = run.actions.order_by("-created_at").first()
    delta = last_action.delta if last_action else 0

    if delta < 0:
        feedback = f"⚠ You lost {abs(delta)} awareness points for missing this threat."
    elif delta == 0:
        feedback = "⚪ No change in your awareness score this round."
    else:
        feedback = f"✅ Great job! You gained {delta} awareness points for identifying this risk."

    return render(request, "training/risk_details.html", {
        "scenario_name": run.scenario.title,
        "risk_type": risk_type,
        "risk_message": risk_message,
        "awareness_tip": awareness_tip,
        "score_feedback": feedback,
        "score": run.score,
        "scenario_id": run.scenario.id,
    })

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
