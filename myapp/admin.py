from django.contrib import admin
from .models import RoommateGroup, RoommateGroupMember, Expense

@admin.register(RoommateGroup)
class RoommateGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'created_by__username')

@admin.register(RoommateGroupMember)
class RoommateGroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'joined_at')
    list_filter = ('joined_at',)
    search_fields = ('group__name', 'user__username')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'category', 'paid_by', 'group', 'date_added')
    list_filter = ('category', 'date_added', 'group')
    search_fields = ('title', 'paid_by__username', 'group__name')
    ordering = ('-date_added',)
