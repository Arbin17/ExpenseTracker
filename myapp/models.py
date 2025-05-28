# expenses/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class RoommateGroup(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def get_all_members(self):
        """Get all members including the creator"""
        members = [self.created_by]
        members.extend([member.user for member in self.members.all()])
        return members

class RoommateGroupMember(models.Model):
    group = models.ForeignKey(RoommateGroup, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('group', 'user')
    
    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('utilities', 'Utilities'),
        ('rent', 'Rent'),
        ('groceries', 'Groceries'),
        ('transport', 'Transport'),
        ('entertainment', 'Entertainment'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(RoommateGroup, on_delete=models.CASCADE, related_name='expenses')
    date_added = models.DateTimeField(default=timezone.now)
    
    # New field for excluded members
    excluded_members = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='excluded_expenses',
        help_text="Members who should not be included in this expense split"
    )
    
    def __str__(self):
        return f"{self.title} - ${self.amount} by {self.paid_by.username}"
    
    def get_participating_members(self):
        """Get list of members who should split this expense"""
        all_members = self.group.get_all_members()
        excluded_members_list = list(self.excluded_members.all())
        participating_members = [member for member in all_members if member not in excluded_members_list]
        return participating_members
    
    def get_individual_share(self):
        """Calculate how much each participating member should pay"""
        participating_members = self.get_participating_members()
        if not participating_members:
            return 0
        return self.amount / len(participating_members)
    
    class Meta:
        ordering = ['-date_added']