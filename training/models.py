from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils.text import slugify
from django.template import Template, Context
from django.utils import timezone
import uuid
import uuid, json

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


class Scenario(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', _('Beginner')
        INTERMEDIATE = 'intermediate', _('Intermediate')
        ADVANCED = 'advanced', _('Advanced')

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='scenarios',
        null=True,
        blank=True
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    content = models.TextField(blank=True, null=True)

    is_phishing = models.BooleanField(default=True)

    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER
    )
    depth = models.PositiveIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



# Each step within the scenario (Email, Fake Login, Notice, Call Script, Reward…)
class ScenarioStep(models.Model):
    class StepType(models.TextChoices):
        EMAIL    = 'email', 'Email'
        FAKE_LOGIN = 'fake_login', 'Fake Login'
        NOTICE   = 'notice', 'Security Notice'
        CALL     = 'call', 'Voice Call'
        FORM     = 'form', 'Data Form'
        REWARD   = 'reward', 'Reward Offer'
        SUMMARY  = 'summary', 'Summary/Reflection'

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='steps')
    order    = models.PositiveIntegerField()
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    title    = models.CharField(max_length=200, blank=True)
    body     = models.TextField(blank=True, default="")            # Supports {{variables}} templates
    link_slug = models.SlugField(max_length=140, blank=True, default="")  #Fake link track we are following
    form_schema = models.JSONField(blank=True, null=True)          # [{name,label,type,required},...]
    timer_seconds = models.PositiveIntegerField(null=True, blank=True)    # IT


    class Meta:
        verbose_name = _("Scenario")
        verbose_name_plural = _("Scenarios")
        ordering = ["order"]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scenario']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['scenario', 'order'], name='uniq_scenario_order')
        ]
        ordering = ['order']


    def __str__(self):
        return  self.title


# User session with one scenario (for account, counter, points…)
class UserScenarioRun(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scenario  = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    run_uuid  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    next_remaining = models.IntegerField(default=0)  # start with scenario.depth
    back_count  = models.IntegerField(default=0)
    next_count  = models.IntegerField(default=0)
    depth_max   = models.IntegerField(default=0)     # The deepest step he reached
    step_index  = models.IntegerField(default=1)     # 1..N
    score       = models.IntegerField(default=0)
    context     = models.JSONField(default=dict)     # Dynamic values (bank_name, last4, otp…)


# Every event the user performs
class UserAction(models.Model):
    class Action(models.TextChoices):
        NEXT    = 'next', 'Next'
        BACK    = 'back', 'Back'
        CLICK   = 'click', 'Clicked Link'
        SUBMIT  = 'submit', 'Submit Form'
        REPORT  = 'report', 'Report Phish'
        TIMEOUT = 'timeout', 'Timer Exceeded'

    run       = models.ForeignKey(UserScenarioRun, on_delete=models.CASCADE, related_name='actions')
    step      = models.ForeignKey(ScenarioStep, on_delete=models.SET_NULL, null=True, blank=True)
    action    = models.CharField(max_length=20, choices=Action.choices)
    delta     = models.IntegerField(default=0)   # Points effect amount
    payload   = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    @staticmethod
    def apply_scoring(action: str, step_type: str, payload: dict) -> int:
        # Simple points rule
        if action == 'report':            return +5
        if action == 'click':
            # If you click on a link in an email/Notice → negative
            return -2 if step_type in ('email','notice','reward') else -1
        if action == 'submit':
            # Entering sensitive data → Higher penalty
            return -5 if step_type in ('fake_login','form') else -1
        if action == 'next':              return 0
        if action == 'back':              return +1
        if action == 'timeout':           return -2
        return 0


def render_step_body(step: ScenarioStep, ctx: dict) -> str:
    tpl = Template(step.body or "")
    return tpl.render(Context(ctx))



class UserResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scenario = models.ForeignKey('training.Scenario', on_delete=models.CASCADE)
    clicked = models.BooleanField(default=False)
    reported = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.scenario}"
