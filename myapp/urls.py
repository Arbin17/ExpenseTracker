from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_user, name='register'),
    path('login/',views.login_user,name='login'),
    path('logout/',views.logout_user,name='logout'),
    path('create-group/', views.create_group, name='create_group'),
    path('add-expense/<int:group_id>/', views.add_expense, name='add_expense'),
    path('add-roommate/<int:group_id>/', views.add_roommate, name='add_roommate'),
    path('monthly-summary/<int:group_id>/', views.monthly_summary, name='monthly_summary'),
    path('group/<int:group_id>/remove-roommate/<int:user_id>/', views.remove_roommate, name='remove_roommate'),
]
