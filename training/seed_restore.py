from training.models import Category, Scenario, ScenarioStep

ScenarioStep.objects.all().delete()
Scenario.objects.all().delete()
Category.objects.all().delete()

anyone = Category.objects.create(name="Anyone", slug="anyone")
it = Category.objects.create(name="IT / Professionals", slug="it")
student = Category.objects.create(name="Student", slug="student")

# =========================
# 🧩 Scenario 1: Anyone
# =========================
s_anyone = Scenario.objects.create(
    title="Unusual Sign-in Activity",
    category=anyone
)

ScenarioStep.objects.bulk_create([
    ScenarioStep(order=1, scenario=s_anyone, title="Email alert", step_type="email",
                 body="You receive an email saying there was unusual sign-in activity on your account."),
    ScenarioStep(order=2, scenario=s_anyone, title="Review link", step_type="click",
                 body="The email provides a link claiming you can secure your account by signing in."),
    ScenarioStep(order=3, scenario=s_anyone, title="Fake login page", step_type="fake_login",
                 body="The link opens a fake login page asking for your username and password."),
    ScenarioStep(order=4, scenario=s_anyone, title="Report email", step_type="report",
                 body="You recognize signs of phishing and report the suspicious email."),
    ScenarioStep(order=5, scenario=s_anyone, title="Summary", step_type="summary",
                 body="Lesson: Always verify the sender and check the URL before entering credentials.")
])


# =========================
# 🧩 Scenario 3: Student
# =========================
s_student = Scenario.objects.create(
    title="Scholarship Delay Verification",
    category=student
)

ScenarioStep.objects.bulk_create([
    ScenarioStep(order=1, scenario=s_student, title="Scholarship email", step_type="email",
                 body="You receive an email claiming your scholarship payment has been delayed."),
    ScenarioStep(order=2, scenario=s_student, title="Verification link", step_type="click",
                 body="The email asks you to verify your student information via a provided link."),
    ScenarioStep(order=3, scenario=s_student, title="Fake portal", step_type="fake_login",
                 body="You are taken to a fake university login page that captures credentials."),
    ScenarioStep(order=4, scenario=s_student, title="Report phishing", step_type="report",
                 body="You report the suspicious email to the university’s IT department."),
    ScenarioStep(order=5, scenario=s_student, title="Reflection", step_type="summary",
                 body="Always verify university domains before clicking any link related to payments.")
])

# =========================
# 🧩 Scenario 4: Suspicious API Session / CSP Token Alert
# =========================
s_api = Scenario.objects.create(
    title="Suspicious API Session / CSP Token Alert",
    category=it
)

ScenarioStep.objects.bulk_create([
    ScenarioStep(order=1, scenario=s_api, title="Security alert", step_type="email",
                 body="You receive an alert about a suspicious API token used from an unknown IP."),
    ScenarioStep(order=2, scenario=s_api, title="Access dashboard", step_type="click",
                 body="The alert email includes a link to check your API session activity."),
    ScenarioStep(order=3, scenario=s_api, title="Fake developer login", step_type="fake_login",
                 body="The link redirects you to a fake developer portal requesting credentials."),
    ScenarioStep(order=4, scenario=s_api, title="Incident response", step_type="report",
                 body="You notice the fake URL and report the incident to the security team."),
    ScenarioStep(order=5, scenario=s_api, title="Summary & Best Practices", step_type="summary",
                 body="Always verify URLs and use token-based authentication from trusted dashboards only.")
])

print("✅ All categories, scenarios, and steps restored successfully!")
