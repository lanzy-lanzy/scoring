from django.urls import path
from . import views


urlpatterns = [
      path('dashboard/', views.dashboard, name='dashboard'),

      path('', views.landing_page, name='landing_page'),
      path('login/', views.login_view, name='login'),
      path('register/', views.register_view, name='register'),

      path('logout/', views.logout_view, name='logout'),
      path('profile/edit/', views.edit_profile, name='edit_profile'),
      path('settings/', views.settings_view, name='settings'),
      path('participants/', views.participant_list, name='participant_list'),
      path('participants/<int:participant_id>/', views.participant_detail, name='participant_detail'),
      path('participants/<int:participant_id>/delete/', views.delete_participant, name='delete_participant'),
      path('competitions/create/', views.create_competition, name='create_competition'),
      path('competitions/', views.competition_list, name='competition_list'),
      path('competitions/<int:competition_id>/', views.competition_detail, name='competition_detail'),
      path('competitions/<int:competition_id>/edit/', views.edit_competition, name='edit_competition'),
      path('competitions/<int:competition_id>/delete/', views.delete_competition, name='delete_competition'),
      path('participants/create/', views.create_participant, name='create_participant'),

      # Results URLs
      path('results/', views.results_list, name='results_list'),
      path('competitions/<int:competition_id>/results/', 
           views.competition_results_detail, name='competition_results_detail'),
      path('competitions/<int:competition_id>/results/reveal/', 
           views.results_reveal, name='results_reveal'),
      path('competitions/<int:competition_id>/results/toggle/', 
           views.toggle_results_visibility, name='toggle_results_visibility'),

      # Round Results URL
      path('competitions/<int:competition_id>/rounds/<int:round_id>/results/', views.round_results, name='round_results'),
      path('competition/<int:competition_id>/pdf-results/', views.generate_results_pdf, name='generate_pdf_results'),
      path('competition/<int:competition_id>/judges-breakdown-pdf/', views.generate_judges_breakdown_pdf, name='generate_judges_breakdown_pdf'),

      # Participant Assignment URLs
      path('participant-management/', views.participant_management, name='participant_management'),
      path('competitions/<int:competition_id>/participants/', views.manage_participants, name='manage_participants'),
      path('competitions/<int:competition_id>/participants/assign/', views.assign_participants, name='assign_participants'),
      path('competitions/<int:competition_id>/participants/<int:participant_id>/remove/', 
           views.remove_participant_from_competition, name='remove_participant_from_competition'),

      # Search URL
      path('search/', views.search, name='search'),

      # Judge Assignment URLs
      path('judge-management/', views.judge_management, name='judge_management'),  
      path('judges/all/', views.view_all_judges, name='view_all_judges'),
      path('judges/add/', views.add_judge, name='add_judge'),
      path('judges/<int:judge_id>/delete/', views.delete_judge, name='delete_judge'),
      path('competitions/<int:competition_id>/judges/', views.manage_judges, name='manage_judges'),
      path('competitions/<int:competition_id>/judges/assign/', views.assign_judges, name='assign_judges'),
      path('competitions/<int:competition_id>/judges/<int:assignment_id>/edit/', 
           views.edit_judge_assignment, name='edit_judge_assignment'),
      path('competitions/<int:competition_id>/judges/<int:assignment_id>/delete/', 
           views.delete_judge_assignment, name='delete_judge_assignment'),

      path('judge/dashboard/', views.judge_dashboard, name='judge_dashboard'),
      path('judge/scoring-panel/<int:round_id>/', views.scoring_panel, name='scoring_panel'),
      path('judge/results_list/', views.results_list, name='results_list'),

      # Round Management URLs
      path('competitions/<int:competition_id>/rounds/', views.manage_rounds, name='manage_rounds'),
      path('competitions/<int:competition_id>/rounds/create/', views.create_round, name='create_round'),
      path('competitions/<int:competition_id>/rounds/<int:round_id>/edit/', views.edit_round, name='edit_round'),
      path('competitions/<int:competition_id>/rounds/<int:round_id>/delete/', views.delete_round, name='delete_round'),
      path('competitions/<int:competition_id>/rounds/<int:round_id>/toggle-status/', views.toggle_round_status, name='toggle_round_status'),
      path('competitions/<int:competition_id>/rounds/<int:round_id>/start/', views.start_round, name='start_round'),
      path('competitions/<int:competition_id>/rounds/<int:round_id>/complete/', views.complete_round, name='complete_round'),

      # Score Management URLs 
      path('competition/<int:competition_id>/toggle-status/', views.toggle_competition_status, name='toggle_competition_status'),
      path('round/<int:round_id>/scoring/', views.scoring_panel, name='scoring_panel'),
      path('round/<int:round_id>/submit-batch-scores/', views.submit_batch_scores, name='submit_batch_scores'),
      path('round/<int:round_id>/submit-scores/', views.submit_scores, name='submit_scores'),
]
