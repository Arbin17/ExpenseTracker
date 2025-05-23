from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import RoommateGroup, RoommateGroupMember, Expense
from .forms import CustomUserCreationForm, ExpenseForm, RoommateGroupForm, AddRoommateForm

def register_user(request):
    form= SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('login')
    else:
        messages.error(
                request,
                "",
            )
        return render(request,'expenses/register.html',{'form':form})

def login_user(request):
    if request.method=="POST":
        username = request.POST['username']
        password =request.POST['password']
        user =  authenticate(request,username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect('dashboard')
        else:
            messages.success(request,("Something went wrong...."))
            return redirect('login')
    else:
        return render(request,'expenses/login.html',{})


    return render(request,'expenses/login.html',{})

def logout_user(request):
    logout(request)

    return redirect('login')

@login_required
def dashboard(request):
    # Get user's groups
    user_groups = RoommateGroup.objects.filter(
        Q(created_by=request.user) | Q(members__user=request.user)
    ).distinct()
    
    # Get recent expenses
    recent_expenses = Expense.objects.filter(
        group__in=user_groups
    ).order_by('-date_added')[:10]
    
    # Calculate total expenses for current month
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_total = Expense.objects.filter(
        group__in=user_groups,
        date_added__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'user_groups': user_groups,
        'recent_expenses': recent_expenses,
        'monthly_total': monthly_total,
    }
    return render(request, 'expenses/dashboard.html', context)

@login_required
def add_expense(request, group_id):
    group = get_object_or_404(RoommateGroup, id=group_id)
    
    # Check if user is member of the group
    if not (group.created_by == request.user or 
            RoommateGroupMember.objects.filter(group=group, user=request.user).exists()):
        messages.error(request, "You are not a member of this group.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.group = group
            expense.save()
            messages.success(request, "Expense added successfully!")
            return redirect('dashboard')
    else:
        form = ExpenseForm()
    
    return render(request, 'expenses/add_expense.html', {'form': form, 'group': group})

@login_required
def create_group(request):
    if request.method == 'POST':
        form = RoommateGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            messages.success(request, f"Group '{group.name}' created successfully!")
            return redirect('dashboard')
    else:
        form = RoommateGroupForm()
    
    return render(request, 'expenses/create_group.html', {'form': form})

@login_required
def add_roommate(request, group_id):
    group = get_object_or_404(RoommateGroup, id=group_id)
    
    if group.created_by != request.user:
        messages.error(request, "Only group creator can add roommates.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AddRoommateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username=username)
                if RoommateGroupMember.objects.filter(group=group, user=user).exists():
                    messages.warning(request, f"{username} is already in this group.")
                else:
                    RoommateGroupMember.objects.create(group=group, user=user)
                    messages.success(request, f"{username} added to the group!")
                return redirect('dashboard')
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' not found.")
    else:
        form = AddRoommateForm()
    
    return render(request, 'expenses/add_roommate.html', {'form': form, 'group': group})
@login_required
def remove_roommate(request, group_id, user_id):
    group = get_object_or_404(RoommateGroup, id=group_id)

    if group.created_by != request.user:
        messages.error(request, "Only group creator can remove roommates.")
        return redirect('dashboard')

    try:
        user_to_remove = User.objects.get(id=user_id)
        membership = RoommateGroupMember.objects.get(group=group, user=user_to_remove)
        membership.delete()
        messages.success(request, f"{user_to_remove.username} has been removed from the group.")
    except User.DoesNotExist:
        messages.error(request, "User does not exist.")
    except RoommateGroupMember.DoesNotExist:
        messages.warning(request, "This user is not a member of the group.")

    return redirect('dashboard')

@login_required
def monthly_summary(request, group_id):
    group = get_object_or_404(RoommateGroup, id=group_id)
    
    # Check if user is member of the group
    if not (group.created_by == request.user or 
            RoommateGroupMember.objects.filter(group=group, user=request.user).exists()):
        messages.error(request, "You are not a member of this group.")
        return redirect('dashboard')
    
    # Get current month's expenses
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    expenses = Expense.objects.filter(
        group=group,
        date_added__gte=current_month
    ).order_by('-date_added')
    
    # Calculate totals
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get all group members
    all_members = [group.created_by]
    all_members.extend([member.user for member in group.members.all()])
    
    # Calculate individual contributions
    member_contributions = {}
    for member in all_members:
        contribution = expenses.filter(paid_by=member).aggregate(total=Sum('amount'))['total'] or 0
        member_contributions[member] = contribution
    
    # Calculate equal share
    equal_share = total_expenses / len(all_members) if all_members else 0
    
    # Calculate balances (who owes/is owed)
    balances = {}
    for member in all_members:
        balance = member_contributions[member] - equal_share
        balances[member] = balance
    
    context = {
        'group': group,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'equal_share': equal_share,
        'member_contributions': member_contributions,
        'balances': balances,
        'all_members': all_members,
        'members_data': [
            {
                'member': member,
                'contribution': member_contributions[member],
                'balance': balances[member]
            } for member in all_members
        ]
    }
    return render(request, 'expenses/monthly_summary.html', context)