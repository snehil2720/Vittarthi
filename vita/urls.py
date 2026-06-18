from django.urls import path,include
from . import views
from ckeditor_uploader import views as ckeditor_views
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', views.home, name='home'),
    path('calculators', views.calculators, name='calculators'),
    # path('blogs/', views.blogs, name='blogs'),
    #path('products/', views.products, name='products'),
    path('contact', views.contact_page, name='contact'),
    path('about-us', views.aboutus, name='aboutus'),
    
    path('calculators/sip', views.sip_calculator, name='sip'),

    path('calculators/emi', views.emi_calculator, name='emi'),
    path('calculators/home-loan', views.home_loan, name='home_loan'),
    path('calculators/car-loan', views.car_loan, name='car_loan'),
    path('calculators/personal-loan', views.personal_loan, name='personal_loan'),

    path('calculators/ppf', views.ppf_calc, name='ppf'),
    path('calculators/nps', views.nps_calc, name='nps'),
    path('calculators/retirement', views.retirement_calc, name='retirement'),

    path('calculators/salary', views.salary_calc, name='salary'),
    path('calculators/pf', views.pf_calc, name='pf'),

    path('calculators/loan-eligibility', views.loan_eligibility, name='eligibility'),

    #path('blogs/', views.blog_list, name='blogs'),
    #path('blogs/<int:id>/', views.blog_detail, name='blog_detail'),
    path('blogs/write', views.write_blog, name='write_blog'),
    path('blogs/my-blogs', views.my_blogs, name='my_blogs'),
    path('blogs/edit/<int:id>', views.edit_blog, name='edit_blog'),
    #path('blogs/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('resources/<slug:primary_slug>/<slug:slug>', views.blog_detail, name='blog_detail'),

    #path('ckeditor/', include('ckeditor_uploader.urls')),
    path('ckeditor/upload/', ckeditor_views.upload, name='ckeditor_upload'),
    path('ckeditor/browse/', ckeditor_views.browse, name='ckeditor_browse'),

    path('blogs/like/<slug:slug>', views.like_blog, name='like_blog'),
    path('blogs/delete/<slug:slug>', views.delete_blog, name='delete_blog'),
    
    path('signup', views.signup, name='signup'),
    path('signin', views.signin, name='signin'),
    path('logout', views.signout, name='logout'),
    path('login', views.auth_page, name='auth'),

    path('forgot-password',views.forgot_password,name='forgot_password'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),

    path('calc-count/', views.calc_count, name='calc_count'),
    path('popular-calculators/', views.popular_calculators, name='popular_calculators'),

    path('add-secondary/', views.add_secondary),
    path('delete-secondary/<int:id>/', views.delete_secondary),

    path('resources/<slug:primary_slug>', views.blog_list, name='resource_list'),
    path('resources', views.resources, name='resources'),
    path(
        'resources/<slug:primary_slug>',
        views.resource_category,
        name='resource_category'
    ),

    path('get-secondary/<int:primary_id>/', views.get_secondary),
    path('contact-submit',views.contact_submit, name='contact_submit'),
    #path('privacy/', views.privacy_policy, name='privacy'),

    path('legal/<slug:slug>', views.legal_page, name='legal_page'),

    path('authors',views.authors,name='authors'),
    path('authors/<slug:slug>',views.author_detail,name='author_detail'),
    path(
        'admin-dashboard',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'change-role/<int:user_id>',
        views.change_role,
        name='change_role'
    ),
    path(
    'forgot-password/',
        auth_views.PasswordResetView.as_view(
            template_name='authentication/forgot_password.html'
        ),
        name='password_reset'
    ),

    path(
        'forgot-password/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='authentication/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='authentication/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),

    path(
        'reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='authentication/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    path('compare', views.compare_hub, name='compare_hub'),
    
    path('compare/sip-vs-fd', views.page_sip_vs_fd, name='page_sip_vs_fd'),
    path('api/compare/sip-vs-fd', views.api_sip_vs_fd, name='api_sip_vs_fd'),

    path('compare/ppf-vs-elss', views.page_ppf_vs_elss, name='page_ppf_vs_elss'),
    path('api/compare/ppf-vs-elss', views.api_ppf_vs_elss, name='api_api_ppf_elss'),

    path('compare/home-loan-vs-rent', views.page_homeloan_vs_rent, name='page_homeloan_vs_rent'),
    path('api/compare/home-loan-vs-rent', views.api_home_loan_vs_rent, name='api_home_loan_rent'),

    path('compare/sgb-vs-gold', views.page_sgb_vs_gold, name='page_sgb_vs_gold'),
    path('api/compare/sgb-vs-gold', views.api_sgb_vs_gold, name='api_sgb_vs_gold'),

    path('compare/nps-vs-mf', views.page_nps_vs_mf, name='page_nps_vs_mf'),
    path('api/compare/nps-vs-mf', views.api_nps_vs_mf, name='api_nps_vs_mf'),

    path('llms.txt', views.llms_txt_view, name='llms_txt'),
    path('llms-full.txt', views.llms_full_txt_view, name='llms_full_txt'),
]

