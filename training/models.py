import re
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils.text import slugify
from django.template import engines, Template, Context, loader
from django.utils.html import mark_safe
from django.utils import timezone
import uuid
import json

# =======================
# Step model
# =======================
class Step(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey('Scenario', on_delete=models.CASCADE, related_name='new_steps')

    title = models.CharField(max_length=200)
    content = models.TextField()

    order = models.PositiveIntegerField(default=1)
    timer_seconds = models.PositiveIntegerField(null=True, blank=True)
    score_value = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.scenario.title} - Step {self.order}: {self.title}"


# =======================
# Category model
# =======================
class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True, null=True)
    description = models.TextField(default="No description provided")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name or "", allow_unicode=True) or "category"
            cand = base
            i = 2
            while Category.objects.filter(slug=cand).exclude(pk=self.pk).exists():
                cand = f"{base}-{i}"
                i += 1
            self.slug = cand
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =======================
# Scenario model
# =======================
class Scenario(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', _('Beginner')
        INTERMEDIATE = 'intermediate', _('Intermediate')
        ADVANCED = 'advanced', _('Advanced')

    # 🔹 العلاقة مع جدول التصنيفات (Category)
    category = models.ForeignKey(
        "Category",                    # استخدم اسم الموديل كـ string
        on_delete=models.CASCADE,
        related_name="scenarios",
        null=True,
        blank=True
    )

    # 🔹 المعلومات الأساسية للسيناريو
    title = models.CharField(max_length=200)
    message = models.TextField()
    content = models.TextField(blank=True, null=True)
    is_phishing = models.BooleanField(default=True)

    # 🔹 مستوى الصعوبة
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER
    )

    # 🔹 عمق الخطوات داخل السيناريو
    depth = models.PositiveIntegerField(default=5)

    # 🔹 معلومات الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔹 تمثيل النص عند الطباعة أو العرض
    def __str__(self):
        category_name = getattr(self.category, "name", "Uncategorized")
        return f"{self.title} ({category_name})"

# =======================
# ScenarioStep model
# =======================
class ScenarioStep(models.Model):
    class StepType(models.TextChoices):
        EMAIL = 'email', 'Email'
        FAKE_LOGIN = 'fake_login', 'Fake Login'
        NOTICE = 'notice', 'Security Notice'
        CALL = 'call', 'Voice Call'
        FORM = 'form', 'Data Form'
        REWARD = 'reward', 'Reward Offer'
        SUMMARY = 'summary', 'Summary/Reflection'

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField()
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, default="")
    link_slug = models.SlugField(max_length=140, blank=True, default="")
    form_schema = models.JSONField(blank=True, null=True)
    timer_seconds = models.PositiveIntegerField(null=True, blank=True)
    risk_type = models.CharField(max_length=250, blank=True, null=True)
    risk_message = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("Scenario step")
        verbose_name_plural = _("Scenarios step")
        ordering = ['order']
        indexes = [
            models.Index(fields=['scenario']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['scenario', 'order'], name='uniq_scenario_order')
        ]

    def __str__(self):
        return self.title


class ScenarioLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey('Scenario', on_delete=models.CASCADE)
    run_uuid = models.CharField(max_length=64)  # ← NEW!
    step = models.IntegerField(default=0)
    action = models.CharField(max_length=20)  # next / back / finish
    score = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.scenario.title} - {self.action}"





# =======================
# UserScenarioRun model
# =======================
class UserScenarioRun(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    run_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    next_remaining = models.IntegerField(default=0)
    back_count = models.IntegerField(default=0)
    next_count = models.IntegerField(default=0)
    depth_max = models.IntegerField(default=0)
    step_index = models.IntegerField(default=1)
    score = models.IntegerField(default=0)
    context = models.JSONField(default=dict)
    last_risk_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.scenario}"


# =======================
# UserAction model
# =======================
class UserAction(models.Model):
    class Action(models.TextChoices):
        NEXT = 'next', 'Next'
        BACK = 'back', 'Back'
        CLICK = 'click', 'Clicked Link'
        SUBMIT = 'submit', 'Submit Form'
        REPORT = 'report', 'Report Phish'
        TIMEOUT = 'timeout', 'Timer Exceeded'

    run = models.ForeignKey(UserScenarioRun, on_delete=models.CASCADE, related_name='actions')
    step = models.ForeignKey(ScenarioStep, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    delta = models.IntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def apply_scoring(action: str, step_type: str, payload: dict) -> int:
        if action == 'report':
            return +5
        if action == 'click':
            return -2 if step_type in ('email', 'notice', 'reward') else -1
        if action == 'submit':
            return -5 if step_type in ('fake_login', 'form') else -1
        if action == 'next':
            return 0
        if action == 'back':
            return +1
        if action == 'timeout':
            return -2
        return 0


# =======================
# Render Step Body
# =======================
TRACK_TAG_RE = re.compile(r"{%\s*url\s+'training:track_link'\s+[^%]*%}")
SLUG_RE = re.compile(r"link_slug\s*=\s*'([^']+)'|link_slug\s*=\s*\"([^\"]+)\"")

def render_step_body(step, run, request) -> str:
    html = step.body or ""

    # 1) حاول render عادي (لو زبط ممتاز)
    try:
        ctx = (run.context or {}).copy()
        ctx.update({"run": run, "step": step})

        tpl = engines["django"].from_string(html)
        html = tpl.render(ctx, request=request)
    except Exception as e:
        print(f"[render_step_body] Template render failed for step {step.id}: {e}")

    # 2) ضمان: استبدال {% url training:track_link ... %} برابط فعلي حتى لو فشل الرندر
    def _replace_track_tag(match):
        tag = match.group(0)
        m = SLUG_RE.search(tag)
        slug = None
        if m:
            slug = m.group(1) or m.group(2)

        if not slug:
            slug = step.link_slug or "track-link"

        return reverse(
            "training:track_link",
            kwargs={"run_uuid": run.run_uuid, "step_id": step.id, "link_slug": slug},
        )

    html = TRACK_TAG_RE.sub(_replace_track_tag, html)
    return mark_safe(html)

class UserResponse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    scenario = models.ForeignKey(
        'training.Scenario', 
        on_delete=models.CASCADE
    )
    clicked = models.BooleanField(default=False)
    reported = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.scenario.title}"
