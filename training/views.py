from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Scenario, UserResponse


# Create your views here.
@login_required
def home(request):
    return render(request, 'training/home.html')


def phishing_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        clicked = True if action == 'click' else False
        reported = True if action == 'report' else False

        # User response log
        UserResponse.objects.create(
            user=request.user,
            scenario=scenario,
            clicked=clicked,
            reported=reported
        )

        return render(request, 'training/thanks.html', {
            'clicked': clicked,
            'reported': reported
        })

    return render(request, 'training/scenario.html', {
        'scenario': scenario
    })

