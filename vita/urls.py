from django.urls import path,include
from . import views
from ckeditor_uploader import views as ckeditor_views
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


]

