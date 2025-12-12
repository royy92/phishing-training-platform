from training.models import Category, Scenario, ScenarioStep
from django.contrib.auth.models import User

def seed():
    # 1️⃣ إنشاء التصنيفات
    cat_anyone, _ = Category.objects.get_or_create(name="Anyone", slug="anyone")
    cat_it, _ = Category.objects.get_or_create(name="IT / Professionals", slug="it-professionals")
    cat_students, _ = Category.objects.get_or_create(name="Students", slug="students")
    cat_cloud, _ = Category.objects.get_or_create(name="Cloud Access Breach Simulation", slug="cloud-access")

    # 2️⃣ سيناريو 1 - Scholarship Delay Verification
    s1 = Scenario.objects.create(title="Scholarship Delay Verification", category=cat_anyone)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s1, order=1, step_type="Email", title="Scholarship Notification Email",
            body="<p>📧 A fake scholarship notification asking to verify your credentials.</p>",
            timer_seconds=45,
            risk_type="Credential Theft",
            risk_message="Fake scholarship emails are designed to steal login credentials or personal data."
        ),
        ScenarioStep(
            scenario=s1, order=2, step_type="Fake Login", title="University Login Page",
            body="<p>🔒 You are redirected to a fake login portal mimicking your university website.</p>",
            timer_seconds=40,
            risk_type="Phishing Website",
            risk_message="Fake university login pages collect your username and password."
        ),
    ])

    # 3️⃣ سيناريو 2 - Account Security Verification
    s2 = Scenario.objects.create(title="Account Security Verification", category=cat_anyone)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s2, order=1, step_type="Email", title="Unusual Login Attempt",
            body="<p>⚠️ Alert: Unusual login detected! Verify your account now.</p>",
            timer_seconds=45,
            risk_type="Phishing Email",
            risk_message="Attackers impersonate support to trick you into sharing your password."
        ),
    ])

    # 4️⃣ سيناريو 3 - Cloud Access Breach Simulation
    s3 = Scenario.objects.create(title="Cloud Access Breach Simulation", category=cat_it)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s3, order=1, step_type="Email", title="Cloud Security Alert: Suspicious Key Use",
            body="<p>🚨 SOC alert: Unauthorized access detected using your AWS IAM key.</p>",
            timer_seconds=50,
            risk_type="Credential Leakage",
            risk_message="Leaked IAM keys can be exploited to access critical infrastructure."
        ),
    ])

    # 5️⃣ سيناريو 4 - Tuition Payment Verification Scam
    s4 = Scenario.objects.create(title="Tuition Payment Verification Scam", category=cat_students)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s4, order=1, step_type="Email", title="University Finance Office: Tuition Payment Issue",
            body="<p>💳 The finance office detected a payment issue. Please verify your details.</p>",
            timer_seconds=50,
            risk_type="Financial Fraud",
            risk_message="Fake tuition notifications aim to collect credit card or bank information."
        ),
    ])

    # 6️⃣ سيناريو 5 - Suspicious API Session
    s5 = Scenario.objects.create(title="Suspicious API Session / CSP Token Alert", category=cat_it)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s5, order=1, step_type="Email", title="API Session Alert",
            body="<p>🔐 Your API token was used from an unusual location. Check activity.</p>",
            timer_seconds=40,
            risk_type="Token Hijacking",
            risk_message="Attackers might use stolen API tokens to impersonate legitimate services."
        ),
    ])

    # 7️⃣ سيناريو 6 - Unusual Sign-In Activity
    s6 = Scenario.objects.create(title="Unusual Sign-in Activity", category=cat_anyone)
    ScenarioStep.objects.bulk_create([
        ScenarioStep(
            scenario=s6, order=1, step_type="Email", title="Password Expiry Notification",
            body="<p>🔔 Your password is expiring soon. Click below to reset it now.</p>",
            timer_seconds=45,
            risk_type="Password Harvesting",
            risk_message="Fake password expiry alerts capture your credentials for later misuse."
        ),
    ])

    print("✅ All scenarios and steps added successfully!")


if __name__ == "__main__":
    seed()
