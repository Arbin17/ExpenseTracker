from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from decimal import Decimal
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
        paid_by=request.user,  # ✅ Add this filter
        date_added__gte=current_month,
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
        form = ExpenseForm(request.POST, group=group)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.paid_by = request.user
            expense.group = group
            expense.save()
            
            # Save the excluded members (many-to-many field)
            form.save_m2m()
            
            # Show success message with participation details
            participating_count = len(expense.get_participating_members())
            total_members = len(group.get_all_members())
            excluded_count = total_members - participating_count
            
            success_msg = f"Expense added successfully! Split among {participating_count} members"
            if excluded_count > 0:
                success_msg += f" ({excluded_count} member{'s' if excluded_count > 1 else ''} excluded)"
            
            messages.success(request, success_msg)
            return redirect('dashboard')
    else:
        form = ExpenseForm(group=group)
    
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
    all_members = group.get_all_members()
    
    # Calculate individual contributions and what they should pay
    member_data = {}
    for member in all_members:
        # How much they actually paid
        paid_amount = expenses.filter(paid_by=member).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # How much they should pay (sum of their shares in all expenses they participate in)
        should_pay = Decimal('0.00')
        for expense in expenses:
            participating_members = expense.get_participating_members()
            if member in participating_members:
                should_pay += expense.get_individual_share()
        
        # Calculate balance (positive means they should receive money, negative means they owe)
        balance = paid_amount - should_pay
        
        member_data[member] = {
            'paid': paid_amount,
            'should_pay': should_pay,
            'balance': balance
        }
    
    # Prepare expenses with participation info
    expenses_with_info = []
    for expense in expenses:
        participating_members = expense.get_participating_members()
        excluded_members = list(expense.excluded_members.all())
        
        expenses_with_info.append({
            'expense': expense,
            'participating_members': participating_members,
            'excluded_members': excluded_members,
            'individual_share': expense.get_individual_share(),
            'participant_count': len(participating_members)
        })
    
    context = {
        'group': group,
        'expenses_with_info': expenses_with_info,
        'total_expenses': total_expenses,
        'all_members': all_members,
        'member_data': member_data,
    }
    return render(request, 'expenses/monthly_summary.html', context)

@login_required
def delete_group(request, group_id):
    """
    Delete a group - only the creator can delete the group.
    This will also delete all associated expenses and memberships.
    """
    group = get_object_or_404(RoommateGroup, id=group_id)
    
    # Check if the current user is the creator of the group
    if request.user != group.created_by:
        messages.error(request, "You don't have permission to delete this group.")
        return HttpResponseForbidden("You don't have permission to delete this group.")
    
    if request.method == 'POST':
        group_name = group.name
        
        # Django's CASCADE delete will automatically handle:
        # - GroupMember objects related to this group
        # - Expense objects related to this group
        # - Any other related objects with CASCADE foreign keys
        group.delete()
        
        messages.success(request, f'Group "{group_name}" has been deleted successfully.')
        return redirect('dashboard')  # or whatever your main page URL name is
    
    # If it's a GET request, redirect back to dashboard
    return redirect('dashboard')

@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    
    # Check if user can edit this expense (must be the person who paid or group creator)
    if not (expense.paid_by == request.user or expense.group.created_by == request.user):
        messages.error(request, "You can only edit expenses you created or if you're the group creator.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully!")
            return redirect('monthly_summary', group_id=expense.group.id)
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'expenses/edit_expense.html', {
        'form': form, 
        'expense': expense,
        'group': expense.group
    })

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    
    # Check if user can delete this expense (must be the person who paid or group creator)
    if not (expense.paid_by == request.user or expense.group.created_by == request.user):
        messages.error(request, "You can only delete expenses you created or if you're the group creator.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        group_id = expense.group.id
        expense_title = expense.title
        expense.delete()
        messages.success(request, f"Expense '{expense_title}' deleted successfully!")
        return redirect('monthly_summary', group_id=group_id)
    
    return render(request, 'expenses/confirm_delete.html', {
        'expense': expense,
        'group': expense.group
    })

@login_required
def expense_detail(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    
    # Check if user is member of the group
    if not (expense.group.created_by == request.user or 
            RoommateGroupMember.objects.filter(group=expense.group, user=request.user).exists()):
        messages.error(request, "You are not a member of this group.")
        return redirect('dashboard')
    
    # Check if user can edit this expense
    can_edit = (expense.paid_by == request.user or expense.group.created_by == request.user)
    
    return render(request, 'expenses/expense_detail.html', {
        'expense': expense,
        'group': expense.group,
        'can_edit': can_edit
    })