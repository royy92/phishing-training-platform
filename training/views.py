from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count, Sum

from .models import Scenario, UserResponse

@login_required
def home(request):
    scenarios = Scenario.objects.all()
    return render(request, 'training/home.html', {'scenarios': scenarios})

@login_required
def phishing_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        clicked  = (action == 'click')
        reported = (action == 'report')
        UserResponse.objects.create(
            user=request.user, scenario=scenario,
            clicked=clicked, reported=reported
        )
        return render(request, 'training/thanks.html',
                      {'clicked': clicked, 'reported': reported})
    return render(request, 'training/scenario.html', {'scenario': scenario})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'training/signup.html', {'form': form})

@login_required
def report(request):
    mine = (UserResponse.objects
            .filter(user=request.user)
            .aggregate(
                total=Count('id'),
                clicks=Sum('clicked'),
                reports=Sum('reported')))
    per_scenario = (UserResponse.objects
                    .values('scenario__title')
                    .annotate(
                        total=Count('id'),
                        clicks=Sum('clicked'),
                        reports=Sum('reported'))
                    .order_by('-total'))
    return render(request, 'training/report.html',
                  {'mine': mine, 'per_scenario': per_scenario})


def scenario_list(request):
   first = Scenario.objects.order_by('id').first()
   return redirect('phishing_scenario', scenario_id=first.id) if first else redirect('home')
