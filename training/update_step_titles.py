from training.models import ScenarioStep

def update_step_titles():
    updates = {
        "email": [
            "Important Account Notification",
            "Payment Confirmation Required",
            "Action Needed: Verify Your Access",
            "Your Account Needs Attention",
        ],
        "fake login": [
            "Access Portal",
            "Login Verification",
            "Account Access Form",
            "User Authentication",
        ],
        "security notice": [
            "System Message",
            "Session Timeout",
            "Account Notice",
            "Service Update",
        ],
        "summary/reflection": [
            "Case Summary",
            "Incident Report",
            "Verification Outcome",
            "User Feedback Summary",
        ],
        "notice": [
            "System Message",
            "Session Timeout",
            "Account Notice",
            "Service Update",
        ],
        "form": [
            "Information Request",
            "Verification Form",
            "Account Input Page",
            "Form Submission",
        ],
    }

    all_steps = ScenarioStep.objects.all()
    count = 0

    for step in all_steps:
        step_type = step.step_type.lower().strip()
        matched = None

        # نحاول نطابق أقرب مفتاح في القاموس حتى لو الاسم فيه اختلاف بسيط
        for key in updates.keys():
            if key in step_type:
                matched = key
                break

        if matched:
            titles = updates[matched]
            new_title = titles[count % len(titles)]
            step.title = new_title
            step.save(update_fields=["title"])
            count += 1
            print(f"✅ Updated: {step.scenario.title} → {new_title}")

    print(f"\n🎯 Done! Updated {count} step titles successfully.")

if __name__ == "__main__":
    update_step_titles()
