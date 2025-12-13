from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count, Q, Sum, Avg
from django.views.decorators.http import require_POST
from .models import UserScenarioRun, ScenarioStep, UserAction
import random, string, csv, json
from collections import defaultdict

from django.contrib.auth import get_user_model

# Models / helpers
from .models import (
    Category,
    Scenario,
    ScenarioStep,
    UserScenarioRun,
    UserAction,
    UserResponse,
    ScenarioLog,
    render_step_body,
)

User = get_user_model()


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

    # ✅ step_id من الفورم (ScenarioStep PK)
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

    # ✅ Redact passwords if any
    if action == "submit":
        for k in ("f_pass", "f_password", "f_new_password", "f_confirm_password"):
            if k in payload:
                payload[k] = "[REDACTED]"

    # ✅ OTP validation (only for FORM submit)
    if action == "submit" and step.step_type == "form":
        entered = (payload.get("f_otp") or "").strip()
        real = (run.context or {}).get("otp")

        ctx = run.context or {}
        ctx["otp_verified"] = bool(real and entered == real)
        ctx["otp_entered"] = entered
        run.context = ctx
        run.save(update_fields=["context"])

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
        total_steps = run.scenario.steps.count()
        run.step_index = min((run.step_index or 1) + 1, total_steps)

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

    # تسجيل الضغط (بدون ما نغيّر step_index ولا ننهي السيناريو)
    UserAction.objects.create(
        run=run,
        step=step,
        action="link_click",
        delta=0,
        payload={"link_slug": link_slug, },
        created_at=timezone.now(),)

    return redirect("training:link_preview", run_uuid=run.run_uuid, step_id=step.id, link_slug=link_slug)


# -----------------------------
# Summary Page
# -----------------------------
@login_required
def run_summary(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)

    # ✅ مهم: اعتبر المحاولة "منتهية" بمجرد الوصول للـ Summary
    # عشان تنحسب بالتقرير (سواء كانت المحاولة نهاية طبيعية أو مبكرة)
    if not run.finished_at:
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])

    user_actions = UserAction.objects.filter(run=run)
    steps_done = run.scenario.steps.count()
    scenario_title = (run.scenario.title or "").lower()

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
            "System Breach ⚠",
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
            "Cloud / API Compromise ☁",
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

    return render(request, "training/run_summary.html", {
        "run": run,
        "steps_done": steps_done,
        "user_actions": user_actions,
        "attack_title": attack_title,
        "attack_message": attack_message,
        "awareness_tip": awareness_tip,
        "attack_icon": "⚪",
    })


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
# Full Analytics Report (NEW)  ✅ الجدولين + شارتين
# -----------------------------
User = get_user_model()

@login_required
def report_view(request):
    MAX_SCORE = 5  # score عندك فعليًا من 0..5

    runs_qs = (
        UserScenarioRun.objects
        .select_related("scenario", "scenario__category", "user")
        .filter(finished_at__isnull=False)  # بس المكتملة
    )

    # غير الأدمن يشوف تقريره فقط
    if not request.user.is_staff:
        runs_qs = runs_qs.filter(user=request.user)

    # 1) كل السيناريوهات مرتبة داخل كل كاتيجوري
    scenarios = (
        Scenario.objects
        .select_related("category")
        .filter(category__isnull=False)
        .order_by("category_id", "phase", "id")
    )

    scenarios_by_cat = {}
    for s in scenarios:
        scenarios_by_cat.setdefault(s.category_id, []).append(s)

    # helper: اختار first/second لكل category
    def pick_first_second(cat_id: int):
        lst = scenarios_by_cat.get(cat_id, [])
        if not lst:
            return (None, None)

        # First: أول واحد phase=1 إذا موجود، وإلا أول واحد
        first = next((x for x in lst if getattr(x, "phase", 1) == 1), lst[0])

        # Second: أول واحد phase=2 إذا موجود، وإلا ثاني عنصر (حسب الترتيب)
        second = next((x for x in lst if getattr(x, "phase", 1) == 2), None)
        if second is None:
            # خذي ثاني سيناريو “مختلف” عن الأول
            second = next((x for x in lst if x.id != first.id), None)

        return (first, second)

    # 2) إحصائيات كل المحاولات (ما بنحذف شيء)
    stats = (
        runs_qs.values(
            "scenario_id",
            "scenario__title",
            "scenario__category_id",
            "scenario__category__name",
        )
        .annotate(
            participants=Count("user", distinct=True),
            runs=Count("id"),
            avg_score=Avg("score"),
        )
    )

    stats_by_scenario = {row["scenario_id"]: row for row in stats}

    # 3) تجهيز صفوف الجدولين
    phase1_rows = []
    phase2_rows = []

    # كل الكاتيجوريز اللي عندها سيناريوهات
    category_ids = sorted(scenarios_by_cat.keys())

    def build_row(scn):
        if not scn:
            return None
        row = stats_by_scenario.get(scn.id, {})
        avg_score = float(row.get("avg_score") or 0.0)
        awareness_pct = round((avg_score / MAX_SCORE) * 100, 1) if MAX_SCORE else 0

        return {
            "category": scn.category.name if scn.category else "-",
            "scenario": scn.title,
            "participants": int(row.get("participants") or 0),
            "runs": int(row.get("runs") or 0),
            "avg_score": round(avg_score, 2),
            "awareness_pct": awareness_pct,
        }

    for cat_id in category_ids:
        first, second = pick_first_second(cat_id)
        r1 = build_row(first)
        r2 = build_row(second)

        if r1:
            phase1_rows.append(r1)
        if r2:
            phase2_rows.append(r2)

    # 4) Overall awareness (اختياري) — متوسط موزون حسب عدد الـ runs
    def overall_awareness(rows):
        total_runs = sum(r["runs"] for r in rows) or 0
        if total_runs == 0:
            return 0
        weighted_avg_score = sum((r["avg_score"] * r["runs"]) for r in rows) / total_runs
        return round((weighted_avg_score / MAX_SCORE) * 100, 1)

    first_awareness = overall_awareness(phase1_rows)
    second_awareness = overall_awareness(phase2_rows)

    # 5) بيانات الشارتات (٪ من 100 لكل Category)
    chart1_labels = [r["category"] for r in phase1_rows]
    chart1_values = [r["awareness_pct"] for r in phase1_rows]

    chart2_labels = [r["category"] for r in phase2_rows]
    chart2_values = [r["awareness_pct"] for r in phase2_rows]

    return render(request, "training/report.html", {
        "phase1_rows": phase1_rows,
        "phase2_rows": phase2_rows,
        "first_awareness": first_awareness,
        "second_awareness": second_awareness,
        "chart1_labels": json.dumps(chart1_labels),
        "chart1_values": json.dumps(chart1_values),
        "chart2_labels": json.dumps(chart2_labels),
        "chart2_values": json.dumps(chart2_values),
    })


# -----------------------------
# Risk Details
# -----------------------------
@login_required
def view_risk_details(request, run_uuid):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    scenario_title = (run.scenario.title or "").lower()

    risk_messages = {
        "credential": ("Credential Theft", "Attackers attempt to steal your credentials through fake login pages or password reset requests.", "🟡 Always verify password reset or login pages before entering your details."),
        "password": ("Credential Theft", "Fake password reset emails may attempt to capture your login details.", "🟡 Check sender domains carefully before resetting your password."),
        "payment": ("Financial Fraud", "Fake payment portals or invoices aim to steal your money or banking details.", "🟠 Always confirm transactions with your finance department directly."),
        "invoice": ("Financial Fraud", "Phishing invoices can trick employees into making unauthorized transfers.", "🟠 Verify payment requests through official communication channels."),
        "update": ("Malware / System Breach", "Fake update alerts can install malware or steal internal credentials.", "🔴 Only download updates from official IT systems or admins."),
        "security": ("Malware / System Breach", "Fake security warnings may install malicious code or capture access tokens.", "🔴 Report suspicious popups to your IT department immediately."),
        "form": ("Data Theft / Privacy Breach", "Phishing forms collect personal or confidential information.", "🟣 Never submit sensitive data through unverified forms."),
        "verification": ("Data Theft / Privacy Breach", "Fake verification requests mimic trusted institutions to steal private info.", "🟣 Ensure verification links match your organization’s real domain."),
        "cloud": ("Cloud / API Compromise", "Fake cloud re-authentication requests can compromise internal accounts.", "🟢 Log in to cloud services only via the official dashboard."),
        "api": ("Cloud / API Compromise", "Phishing emails targeting API tokens can expose system data.", "🟢 Never share authentication tokens via email."),
        "default": ("General Awareness", "Stay alert to phishing attempts in all forms.", "⚪ Always verify senders and avoid clicking unfamiliar links."),
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
def link_preview(request, run_uuid, step_id, link_slug):
    run = get_object_or_404(UserScenarioRun, run_uuid=run_uuid, user=request.user)
    step = get_object_or_404(ScenarioStep, pk=step_id, scenario=run.scenario)

    if link_slug == "revoke-session":
        context = {
            "title": "Security Activity Center",
            "subtitle": "Review recent account activity and manage sessions.",
            "displayed_url": "security-auth.company-safe.net",
            "card_title": "New API session detected",
            "items": [
                ("App", "Cloud API Gateway"),
                ("IP", "185.73.22.14"),
                ("Approx. location", "Istanbul, TR"),
                ("Device", "Linux (Firefox)"),
                ("Time", "Just now"),
            ],
            "hint": "For account changes, you may also open the Security Portal from your saved bookmark.",
        }

    elif link_slug == "open-verification-email":
        context = {
            "title": "Account Verification",
            "subtitle": "Verify your identity to restore access and review recent sign-in activity.",
            "displayed_url": "mail.company-safe.net/verify",
            "card_title": "Verification request",
            "items": [
                ("Request type", "Identity verification"),
                ("Delivery method", "Email link"),
                ("Reference ID", "VRF-20491"),
                ("Requested by", "Security System"),
                ("Time", "Just now"),
                ("Support", "security@company.com"),
            ],
            "hint": "Tip: If you didn’t initiate this request, confirm using your official security portal or help desk.",
        }

    elif link_slug == "cloud-access-console":
        context = {
            "title": "Cloud Access Console",
            "subtitle": "Sign in required to confirm IAM access identity.",
            "displayed_url": "cloud-auth-console-secure.company-safe.net",
            "card_title": "Access Identity Check",
            "items": [
                ("Sign-in method", "Corporate SSO + MFA"),
                ("Account", "Corporate Cloud"),
                ("Service", "AWS IAM"),
                ("Source IP", "203.0.113.58"),
                ("Region", "ap-southeast-1"),
                ("Time", "Just now"),
            ],
            "hint": "Tip: Many teams open cloud consoles from an internal dashboard or a saved bookmark to avoid mistyped domains.",
        }
    elif link_slug == "password-reset-preview":
        context = {
            "title": "Password Reset Portal",
            "subtitle": "Complete the password update to keep your account access uninterrupted.",
            "displayed_url": "it-helpdesk-reset.com/password/reset",
            "card_title": "Reset request details",
            "items": [
                ("Request type", "Password update"),
                ("Account", "Corporate SSO"),
                ("Delivery method", "Email link"),
                ("Ticket reference", "HD-PR-48219"),
                ("Requested by", "IT Support Automation"),
                ("Time", "Just now"),
            ],
            # تلميح لطيف بدون ما يقول “Phishing”
            "hint": "Tip: Many employees start password updates from the internal Helpdesk portal or saved bookmarks for faster access.",
        }
    elif link_slug == "security-verify-access":
       context = {
           "title": "Account Security Verification",
           "subtitle": "Verify recent sign-in activity to restore access to your account.",
           "displayed_url": "security-verify-access.com",
           "card_title": "Verification summary",
           "items": [
              ("Verification type", "Sign-in confirmation"),
              ("Account", "Corporate SSO"),
              ("Method", "Secure verification page"),
              ("Session status", "Temporarily locked"),
              ("Reference ID", "ASV-19340"),
              ("Time", "Just now"),
           ],
           "hint": "Tip: Many organizations provide account recovery from the official security portal or internal helpdesk dashboard.",
     }
    elif link_slug == "security-verify-access":
        context = {
            "title": "Account Security Verification",
            "subtitle": "Sign in to verify recent activity and restore access.",
            "displayed_url": "security-verify-access.com",
            "card_title": "Verification status",
            "items": [
                ("Request", "Account activity confirmation"),
                ("Method", "SSO + MFA"),
                ("Status", "Pending verification"),
                ("Time", "Just now"),
            ],
            # تلميح لطيف (بدون كلمة phishing)
            "hint": "Tip: If you didn’t initiate this check, open your official security portal directly from a saved bookmark or internal dashboard.",
            "show_login": True,
            # هذا اللي رح يطلع جوّا بلوك اللوجين اللي تحت
            "display_url": "security-verify-access.com",
        }
    elif link_slug == "tuition-payment-portal":
       context = {
           "title": "Student Financial Portal",
           "subtitle": "Sign in to review your tuition payment status and account balance.",
           "displayed_url": "student-finance-portal.company-safe.net",
           "card_title": "Payment Overview",
           "items": [
               ("Term", "Fall 2025"),
               ("Payment status", "Processing"),
               ("Amount due", "JOD 0.00"),
               ("Last activity", "Today"),
               ("Method", "Card / Bank transfer"),
           ],
           "hint": "Tip: Students usually access financial services from the university’s main website or student dashboard.",
           "show_login": True,
           "display_url": "student-finance-portal.company-safe.net",
       }
    elif link_slug == "scholarship-portal":
       context = {
           "title": "University Scholarship Portal",
           "subtitle": "Sign in to review scholarship updates and payment status.",
           "displayed_url": "portal-scholarships.univ.example",
           "card_title": "Scholarship Payment Status",
           "items": [
               ("Program", "Merit Scholarship"),
               ("Status", "Under review"),
               ("Next update", "Within 3–5 business days"),
               ("Reference", "SCH-12058"),
               ("Support", "scholarships@univ.example"),
           ],
           "hint": "Tip: Most students access scholarship updates from the official student portal or the university website.",
           "show_login": True,
           "display_url": "portal-scholarships.univ.example",
       }

    else:
        context = {
            "title": "External Link Preview",
            "subtitle": "This is a simulated external page for the training.",
            "displayed_url": "unknown-link.example",
            "card_title": "Preview",
            "items": [],
            "hint": "If something feels off, verify via official channels.",
        }

    # زر الرجعة لازم يرجع لستيب نفسه
    back_to_step_index = getattr(step, "order", None) or 1

    return render(request, "training/link_preview.html", {
        "run": run,
        "step": step,
        "step_index": back_to_step_index,
        "link_slug": link_slug,
        **context
    })



@login_required
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    scenarios = Scenario.objects.filter(category=category)
    return render(
        request,
        "training/category_detail.html",
        {"category": category, "scenarios": scenarios},
    )
report = report_view
