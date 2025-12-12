from training.models import Category, Scenario, ScenarioStep

def seed():
    # --- Create Categories ---
    anyone = Category.objects.get_or_create(name="Anyone")[0]
    it = Category.objects.get_or_create(name="IT / Professionals")[0]
    students = Category.objects.get_or_create(name="Students")[0]

    print("✅ Categories created.")

    def create_scenario(category, title, message, steps_data):
        scenario = Scenario.objects.create(category=category, title=title, message=message, is_phishing=True)
        for step in steps_data:
            ScenarioStep.objects.create(scenario=scenario, **step)
        print(f"🎯 Scenario added: {title}")
        return scenario

    # ---------------------------------------------------------------------
    # ANYONE SCENARIOS (no timer)
    # ---------------------------------------------------------------------
    create_scenario(
        anyone,
        "Password Expiry Scam",
        "Teach users to recognize fake password-expiry phishing emails.",
        [
            {"order": 1, "step_type": "Email", "title": "Password Expiry Notification", "body": " You received an email from “IT Support” ...", "risk_type": "Credential Theft", "risk_message": "Fake password reset portals steal user credentials."},
            {"order": 2, "step_type": "Fake Login", "title": "Fake Password Reset Portal", "body": " The link opens a webpage that looks identical...", "risk_type": "Credential Theft", "risk_message": "Attackers capture usernames and passwords from cloned login pages."},
            {"order": 3, "step_type": "Security Notice", "title": "Security Alert", "body": "⚠️ After you submit your credentials...", "risk_type": "Unauthorized Access", "risk_message": "Your data was transmitted to a malicious actor."},
            {"order": 4, "step_type": "Security Notice", "title": "Security Awareness Tip", "body": " Always check the sender’s email domain...", "risk_type": "Awareness", "risk_message": "Verifying email sources can prevent phishing success."},
            {"order": 5, "step_type": "Summary/Reflection", "title": "Scenario Summary", "body": "✅ You learned how phishing emails exploit urgency...", "risk_type": "Educational", "risk_message": "Stay cautious of urgent security-related emails."},
        ],
    )

    create_scenario(
        anyone,
        "Account Security Verification",
        "Simulated phishing disguised as security verification from IT.",
        [
            {"order": 1, "step_type": "Email", "title": "Unusual Login Attempt", "body": "🚨 Your account was accessed...", "risk_type": "Impersonation Attack", "risk_message": "Attackers imitate IT teams to gain trust."},
            {"order": 2, "step_type": "Fake Login", "title": "Security Verification Portal", "body": " The portal looks identical to your company’s login page...", "risk_type": "Credential Theft", "risk_message": "Fake portals harvest login data."},
            {"order": 3, "step_type": "Security Notice", "title": "Account Recovery Notice", "body": "⚠ After submitting, a message appears...", "risk_type": "Data Breach", "risk_message": "Stolen credentials can be used to access systems."},
            {"order": 4, "step_type": "Security Notice", "title": "Security Awareness Tip", "body": " Cybercriminals often imitate IT security departments...", "risk_type": "Awareness", "risk_message": "Always contact IT directly for verification."},
            {"order": 5, "step_type": "Summary/Reflection", "title": "Scenario Summary", "body": "✅ You just experienced a simulated security phishing attempt...", "risk_type": "Educational", "risk_message": "Recognizing patterns prevents real-world breaches."},
        ],
    )

    # ---------------------------------------------------------------------
    # IT / PROFESSIONALS (WITH TIMER)
    # ---------------------------------------------------------------------
    create_scenario(
        it,
        "Suspicious API Session / CSP Token Alert",
        "Teach IT users to detect suspicious API or token phishing emails.",
        [
            {"order": 1, "step_type": "Email", "timer_seconds": 45, "title": "API Session Alert", "body": "🚨 You received an automated email...", "risk_type": "Unauthorized Access", "risk_message": "Compromised API keys can allow system breaches."},
            {"order": 2, "step_type": "Fake Login", "timer_seconds": 60, "title": "Security Dashboard Login", "body": "🔐 The link takes you to a fake company portal...", "risk_type": "Credential Theft", "risk_message": "Stolen logins can expose entire networks."},
            {"order": 3, "step_type": "Security Notice", "timer_seconds": 40, "title": "System Warning", "body": "⚠️ After entering your credentials...", "risk_type": "Privilege Escalation", "risk_message": "Hackers can exploit admin access gained through phishing."},
            {"order": 4, "step_type": "Security Notice", "timer_seconds": 35, "title": "IT Awareness Tip", "body": " Always verify URLs before entering credentials...", "risk_type": "Awareness", "risk_message": "Suspicious URLs are a key red flag for phishing."},
            {"order": 5, "step_type": "Summary/Reflection", "timer_seconds": 50, "title": "Scenario Summary", "body": "✅ This exercise demonstrated how attackers mimic alerts...", "risk_type": "Educational", "risk_message": "Stay alert to domain spoofing and fake portals."},
        ],
    )

    create_scenario(
        it,
        "Cloud Access Breach Simulation",
        "Advanced phishing targeting IAM and Cloud portal users.",
        [
            {"order": 1, "step_type": "Email", "timer_seconds": 45, "title": "Cloud Security Alert", "body": "🚨 The SOC team detected unauthorized activity...", "risk_type": "Data Leak", "risk_message": "Cloud credentials leaks can expose critical data."},
            {"order": 2, "step_type": "Fake Login", "timer_seconds": 60, "title": "Cloud Access Console", "body": " Your session has expired...", "risk_type": "Credential Theft", "risk_message": "Fake IAM reauthentication forms steal identities."},
            {"order": 3, "step_type": "Security Notice", "timer_seconds": 50, "title": "Security Operations Follow-Up", "body": "Thank you for your quick response...", "risk_type": "Awareness", "risk_message": "SOC follow-up simulations reinforce readiness."},
            {"order": 4, "step_type": "Security Notice", "timer_seconds": 40, "title": "Professional Awareness Reminder", "body": " Always validate URLs when prompted for reauthentication...", "risk_type": "Awareness", "risk_message": "Always verify organizational domains."},
            {"order": 5, "step_type": "Summary/Reflection", "timer_seconds": 55, "title": "Scenario Summary", "body": "✅ Professionals who double-checked the domain...", "risk_type": "Educational", "risk_message": "Security training helps prevent IAM-related phishing."},
        ],
    )

    # ---------------------------------------------------------------------
    # STUDENTS (no timer)
    # ---------------------------------------------------------------------
    create_scenario(
        students,
        "Tuition Payment Verification Scam",
        "Phishing that imitates university finance office emails.",
        [
            {"order": 1, "step_type": "Email", "title": "University Finance Office", "body": " Dear Student, our records indicate...", "risk_type": "Financial Scam", "risk_message": "Attackers impersonate finance departments to steal money."},
            {"order": 2, "step_type": "Fake Login", "title": "Student Payment Portal", "body": "You are redirected to a fake portal...", "risk_type": "Credential Theft", "risk_message": "Login details stolen can be used for fraud."},
            {"order": 3, "step_type": "Form", "title": "Payment Verification Form", "body": "Please confirm your student ID and bank number...", "risk_type": "Data Exposure", "risk_message": "Sensitive personal and bank details can be exploited."},
            {"order": 4, "step_type": "Notice", "title": "Suspicious Payment Attempt", "body": "⚠️ Unusual verification attempt detected...", "risk_type": "Awareness", "risk_message": "Avoid entering details on unsolicited links."},
            {"order": 5, "step_type": "Summary/Reflection", "title": "Scenario Summary", "body": "✅ Legitimate universities never ask for your bank details...", "risk_type": "Educational", "risk_message": "Always verify payment issues with the university directly."},
        ],
    )

    create_scenario(
        students,
        "Scholarship Delay Verification",
        "Phishing disguised as scholarship or financial aid delay emails.",
        [
            {"order": 1, "step_type": "Email", "title": "Scholarship Notification Email", "body": " You received an email titled 'Delay in Your Scholarship Payment'...", "risk_type": "Financial Scam", "risk_message": "Fake scholarship updates lure students into phishing traps."},
            {"order": 2, "step_type": "Fake Login", "title": "Fake Login Page", "body": "The page looks identical to your university’s portal...", "risk_type": "Credential Theft", "risk_message": "Fake portals mimic real ones to steal access data."},
            {"order": 3, "step_type": "Security Notice", "title": "Security Warning", "body": "🚨 After entering your credentials, a fake alert appears...", "risk_type": "Unauthorized Access", "risk_message": "Phishers can access student systems once credentials are compromised."},
            {"order": 4, "step_type": "Security Notice", "title": "Security Awareness Tip", "body": " Legitimate organizations never ask you to log in via email links...", "risk_type": "Awareness", "risk_message": "Always check domains and use official university portals."},
            {"order": 5, "step_type": "Summary/Reflection", "title": "Scenario Summary", "body": " You learned to identify and avoid phishing emails related to scholarships.", "risk_type": "Educational", "risk_message": "Well done! You are now better protected from financial phishing."},
        ],
    )

    print("🎓 All scenarios, risks, and steps added successfully!")


if __name__ == "__main__":
    seed()
