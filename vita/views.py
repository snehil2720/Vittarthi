from django.shortcuts import render, redirect, get_object_or_404
from .models import Blog,CalcUsage,PrimaryCategory,SecondaryCategory,PrivacyPolicy,CustomUser,ContactMessage,LegalPage,Author
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.contrib.auth import login, authenticate,logout
from django.contrib import messages
from django.utils.text import slugify
import re
import math
from django.core.mail import send_mail
from django.conf import settings
from .utils import generate_ai_summary
import requests
import yfinance as yf
import certifi
from django.db.models import Count,Q
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils.html import strip_tags
from bs4 import BeautifulSoup
#from financial_advisor.views import dashboard
from vita.decorators import admin_required, writer_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
import urllib3
import traceback
from datetime import datetime
import os, certifi
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
os.environ['CURL_CA_BUNDLE']     = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE']      = certifi.where()

def auth_page(request):
    return render(request, "authentication/auth.html")

def forgot_password(request):
    return render(request, 'authentication/forgot_password.html')
# SIGNUP
def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email    = request.POST.get("email")
        password = request.POST.get("password")
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("auth")
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='user'
        )
        login(
            request,
            user,
            backend='django.contrib.auth.backends.ModelBackend'
        )
        messages.success(request, "Account created successfully 🎉")
        #return redirect("dashboard")
        #return redirect("http://app.vittarthi.local:8000/")
        #return redirect("https://app.vittarthi.com/")
        return redirect(settings.DASHBOARD_URL)
    return redirect("auth")


# SIGNIN
def signin(request):

    if request.method == "POST":

        identifier = request.POST.get("identifier")
        password   = request.POST.get("password")

        user_obj = None

        # Login via Email
        if "@" in identifier:

            try:
                user_obj = CustomUser.objects.get(email=identifier)
            except CustomUser.DoesNotExist:
                messages.error(request, "Email not registered")
                return redirect("auth")

        # Login via Username
        else:

            try:
                user_obj = CustomUser.objects.get(username=identifier)
            except CustomUser.DoesNotExist:
                messages.error(request, "Username not found")
                return redirect("auth")

        # Authenticate using actual username
        user = authenticate(
            request,
            username=user_obj.username,
            password=password
        )

        if user:
            login(
                request,
                user,
                backend='django.contrib.auth.backends.ModelBackend'
            )
            #return redirect("dashboard")
            #return redirect("https://app.vittarthi.com/") #production pe 
            #return redirect("http://app.vittarthi.local:8000/") #local pe 
            return redirect(settings.DASHBOARD_URL)

        else:
            messages.error(request, "Invalid password")

    return redirect("auth")

def signout(request):
    logout(request)
    return redirect("home")


from django.db.models import Q
def home(request):
    #blogs = Blog.objects.all().order_by('-id')
    blogs = Blog.objects.filter(
        Q(primary_category__slug='blogs') |
        Q(secondary_category__slug='blogs')
    ).distinct()[:3]

    news = Blog.objects.filter(
        Q(primary_category__slug='news') |
        Q(secondary_category__slug='news')
    ).distinct()[:3]

    case_studies = Blog.objects.filter(
        Q(primary_category__slug='case-study') |
        Q(secondary_category__slug='case-study')
    ).distinct()[:3]
    market = get_market_data()
    latestblogs = Blog.objects.order_by('-created_at')[:3]
    context = {
        "market": market,
        'latestblogs': latestblogs,
        'blogs_data': blogs,
        'news_data': news,
        'case_data': case_studies,
    }
    return render(request, 'home.html', context)

def calculators(request):
    return render(request, 'calculators.html')

def blogs(request):
    return render(request, 'blogs.html')

def products(request):
    return render(request, 'products.html')

def contact(request):
    return render(request, 'contact.html')

def is_writer(user):
    #return True
    #return 'snehil'
    return user.is_authenticated and (user.is_staff or user.username in ['user1', 'user2'])

# Function is under development ....
# def blog_list(request):
#     #blogs = Blog.objects.filter(status='published').order_by('-created_at')
#     categories = Category.objects.all()
#     top_blog = Blog.objects.filter(is_featured=True,status='published').order_by('-created_at').first()
#     if not top_blog:
#             top_blog = Blog.objects.filter(status='published').order_by('-created_at').first()
#     if top_blog:
#         regular_blogs = Blog.objects.exclude(id=top_blog.id).order_by('-created_at')
#     else:
#         regular_blogs = [] 
#     context = {
#         'top_blog': top_blog,
#         'blogs': blogs,
#         'categories': categories 
#     }
#     return render(request, 'blogs/list.html', context)

def blog_list(request, primary_slug):
    primary = get_object_or_404(PrimaryCategory, slug=primary_slug)

    blogs = Blog.objects.filter(
        status='published',
        primary_category=primary
    ).order_by('-created_at')
    secondary_slug = request.GET.get('secondary')

    if secondary_slug and secondary_slug != "all":
        blogs = blogs.filter(secondary_category__slug=secondary_slug)

    paginator = Paginator(blogs, 7)  # 7 blogs per page
    page_number = request.GET.get('page')
    blogs = paginator.get_page(page_number)

    secondary_categories = SecondaryCategory.objects.filter(primary=primary)
    category_counts = (
        Blog.objects
        .filter(status='published')
        .values('primary_category__slug')
        .annotate(total=Count('id'))
    )

    counts = {item['primary_category__slug']: item['total']
            for item in category_counts}

    blog_count = counts.get('blogs', 0)
    case_study_count = counts.get('case-study', 0)
    news_count = counts.get('news', 0)
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Resources', 'url': '/resources'},
        {'name': primary.name, 'url': ''}
    ]
    return render(request, 'blogs/list.html', {
        'blogs': blogs,
        'primary': primary,
        'secondary_categories': secondary_categories,
        'breadcrumbs': breadcrumbs,
        'blog_count': blog_count,
        'case_study_count': case_study_count,
        'news_count': news_count,
        'current_section': primary.slug,
    })
def get_secondary(request, primary_id):
    cats = SecondaryCategory.objects.filter(primary_id=primary_id)
    data = list(cats.values('id', 'name'))
    return JsonResponse(data, safe=False)

def blog_detail(request, primary_slug,slug):
    blog = get_object_or_404(
        Blog,
        slug=slug,
        status='published',
        primary_category__slug=primary_slug  
    )
    related_articles = Blog.objects.filter(
        status='published',
        primary_category=blog.primary_category
    ).exclude(
        id=blog.id
    ).order_by('-created_at')[:5]

    popular_articles = Blog.objects.filter(
        status='published',
        primary_category=blog.primary_category
    ).exclude(
        id=blog.id
    ).order_by('-likes')[:5]
    categories = type(blog.primary_category).objects.all()
    text = re.sub('<[^<]+?>', '', blog.content)
    words = len(text.split())
    read_time = math.ceil(words / 200)
    #return render(request, 'blogs/detail.html', {'blog': blog})
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {
            'name': blog.primary_category.name,
            'url': f'/resources/{blog.primary_category.slug}'
        },
        {
            'name': blog.title,
            'url': ''
        }
    ]
    return render(request, 'blogs/detail.html', {
        'blog': blog,
        'read_time': read_time,
        'breadcrumbs': breadcrumbs,
        'related_articles': related_articles,
        'popular_articles': popular_articles,
        'categories': categories,
    })
@admin_required
def delete_blog(request, slug):
    blog = Blog.objects.get(slug=slug)
    primary_slug = blog.primary_category.slug
    blog.delete()
    return redirect('resource_list', primary_slug=primary_slug)
def generate_unique_slug(title, slug_input=None, instance=None):
    base_slug = slugify(slug_input) if slug_input else slugify(title)
    slug = base_slug
    counter = 1

    while Blog.objects.filter(slug=slug).exclude(id=instance.id if instance else None).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug

@writer_required
def write_blog(request):

    primary_categories = PrimaryCategory.objects.all()
    secondary_categories = SecondaryCategory.objects.none()
    authors = Author.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        slug_input = request.POST.get("slug")
        content = request.POST.get('content')

        primary_id = request.POST.get('primary_category')
        secondary_id = request.POST.get('secondary_category')

        # ✅ SAFE CAST
        primary_id = int(primary_id) if primary_id else None
        secondary_id = int(secondary_id) if secondary_id else None

        meta_title = request.POST.get("meta_title")
        meta_description = request.POST.get("meta_description")

        slug = generate_unique_slug(title, slug_input)[:200]
        summary = generate_ai_summary(content)

        # ✅ SAFE SEO
        meta_title = (meta_title or f"{title} | Vittarthi")[:200]
        meta_description = (meta_description or summary[:160])[:160]

        Blog.objects.create(
            title=title,
            content=content,
            image=request.FILES.get('image'),
            author=request.user,
            author_profile_id=request.POST.get('author_profile') or None,
            reviewed_by_id=request.POST.get('reviewed_by') or None,
            edited_by_id=request.POST.get('edited_by') or None,
            status=request.POST.get('status'),

            primary_category_id=primary_id,
            secondary_category_id=secondary_id,

            slug=slug,
            summary=summary,

            focus_keyword=request.POST.get('focus_keyword'),
            meta_title=meta_title,
            meta_description=meta_description,
        )

        return redirect('resource_list', primary_slug='blogs')

    return render(request, 'blogs/write.html', {
        'primary_categories': primary_categories,
        'secondary_categories': secondary_categories,
        'authors': authors,
    })

@writer_required
def my_blogs(request):
    #blogs = Blog.objects.filter(author=request.user)
    blogs = Blog.objects.all().order_by('-id')
    paginator = Paginator(blogs, 10)  # 10 per page

    page_number = request.GET.get('page')
    blogs = paginator.get_page(page_number)
    return render(request, 'blogs/my_blogs.html', {'blogs': blogs})

@writer_required
def edit_blog(request, id):
    blog = get_object_or_404(Blog, id=id)

    # if blog.author != request.user:
    #     return redirect('blogs')

    primary_categories = PrimaryCategory.objects.all()
    secondary_categories = SecondaryCategory.objects.filter(
        primary=blog.primary_category
    ) if blog.primary_category else SecondaryCategory.objects.none()
    
    # ✅ Fetch authors for the dropdowns
    authors = Author.objects.all()

    if request.method == 'POST':
        new_content = request.POST.get("content")

        if blog.content != new_content:
            blog.summary = generate_ai_summary(new_content)

        blog.title = request.POST.get('title')
        blog.content = new_content
        blog.status = request.POST.get('status')

        # ✅ SLUG UPDATE FIX
        slug_input = request.POST.get("slug")
        blog.slug = generate_unique_slug(blog.title, slug_input, instance=blog)

        # ✅ SEO FIX
        blog.meta_title = request.POST.get("meta_title") or f"{blog.title} | Vita₹thi"
        blog.meta_description = request.POST.get("meta_description") or blog.summary[:160]

        # ✅ CATEGORY FIX
        blog.primary_category_id = request.POST.get('primary_category') or None
        blog.secondary_category_id = request.POST.get('secondary_category') or None
        
        # ✅ AUTHOR & REVIEWER FIX (New)
        blog.author_profile_id = request.POST.get('author_profile') or None
        blog.reviewed_by_id = request.POST.get('reviewed_by') or None
        blog.edited_by_id = request.POST.get('edited_by') or None

        if request.FILES.get('image'):
            blog.image = request.FILES.get('image')

        blog.save()
        return redirect('my_blogs')

    return render(request, 'blogs/edit.html', {
        'blog': blog,
        'primary_categories': primary_categories,
        'secondary_categories': secondary_categories,
        'authors': authors  # ✅ Pass authors to template context
    })


def sip_calculator(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = float(data.get("amount", 0))
            rate = float(data.get("rate", 0)) / 100 / 12  # Monthly rate
            years = float(data.get("time", 0))
            step_up = float(data.get("step_up", 0)) / 100 # Annual step up
            inflation = float(data.get("inflation", 0)) / 100 # Annual inflation

            months = int(years * 12)
            total = 0
            invested = 0
            current_amount = amount

            yearly_data = []
            monthly_data = []

            for i in range(1, months + 1):
                invested += current_amount
                total = (total + current_amount) * (1 + rate)

                monthly_data.append({
                    "month": i,
                    "invested": round(invested),
                    "profit": round(total - invested),
                    "total": round(total)
                })

                if i % 12 == 0:
                    year = i // 12
                    yearly_data.append({
                        "year": year,
                        "invested": round(invested),
                        "profit": round(total - invested),
                        "total": round(total)
                    })
                    current_amount = current_amount * (1 + step_up)

            profit = total - invested
            
            taxable_profit = max(0, profit - 125000)
            tax = taxable_profit * 0.125
            net_in_hand = total - tax
            real_value = total / ((1 + inflation) ** years) if inflation > 0 else total

            # Record usage (optional, since it will fire on every slider move, you might want to remove this or throttle it)
            # CalcUsage.objects.create(name="SIP")

            return JsonResponse({
                "success": True,
                "total": round(total),
                "invested": round(invested),
                "profit": round(profit),
                "tax": round(tax),
                "net_in_hand": round(net_in_hand),
                "real_value": round(real_value),
                "yearly_data": yearly_data,
                "monthly_data": monthly_data
            })
            
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    CalcUsage.objects.create(name="SIP") # You can record a page visit here!
    
    return render(request, 'investment/sip.html')


def emi_calculator(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            P = float(data.get("amount", 0))
            annual_rate = float(data.get("rate", 0))
            years = float(data.get("time", 0))
            
            # Advanced fields (will default to 0 if not sent yet)
            monthly_prepay = float(data.get("monthly_prepay", 0))
            yearly_prepay = float(data.get("yearly_prepay", 0))
            processing_fee_pct = float(data.get("processing_fee_pct", 0))
            r = annual_rate / 100 / 12
            n = int(years * 12)
            # Handle 0% interest edge case
            if r == 0:
                emi = P / n if n > 0 else 0
            else:
                emi = P * r * ((1 + r)**n) / (((1 + r)**n) - 1)
            base_emi = round(emi)
            processing_fee = round(P * (processing_fee_pct / 100))
            net_disbursed = P - processing_fee
            balance = P
            total_interest = 0
            months_taken = 0
            yearly_data = []
            monthly_data = []
            yearly_principal = 0
            yearly_interest = 0
            # Generate the Amortization Schedule
            for i in range(1, n + 1):
                if balance <= 0:
                    break
                    
                months_taken += 1
                interest = balance * r
                
                # Apply extra prepayments
                actual_payment = base_emi + monthly_prepay
                if i % 12 == 0:
                    actual_payment += yearly_prepay
                    
                # Don't overpay on the final month
                if actual_payment > balance + interest:
                    actual_payment = balance + interest
                    
                principal = actual_payment - interest
                balance -= principal
                total_interest += interest
                
                yearly_principal += principal
                yearly_interest += interest
                
                monthly_data.append({
                    "month": i,
                    "principal": round(principal),
                    "interest": round(interest),
                    "balance": round(max(0, balance))
                })
                
                # Save Yearly Rollup
                if i % 12 == 0 or balance <= 0:
                    if yearly_principal > 0 or yearly_interest > 0:
                        yearly_data.append({
                            "year": (i - 1) // 12 + 1,
                            "principal": round(yearly_principal),
                            "interest": round(yearly_interest),
                            "balance": round(max(0, balance)),
                            "total_paid": round(yearly_principal + yearly_interest)
                        })
                    yearly_principal = 0
                    yearly_interest = 0
            total_payment = P + total_interest
            # Calculate savings if prepayments were used
            if monthly_prepay > 0 or yearly_prepay > 0:
                base_total_interest = (base_emi * n) - P
                interest_saved = max(0, base_total_interest - total_interest)
                tenure_saved_months = n - months_taken
            else:
                interest_saved = 0
                tenure_saved_months = 0
            return JsonResponse({
                "success": True,
                "principal": round(P),
                "emi": base_emi,
                "total_interest": round(total_interest),
                "total_payment": round(total_payment),
                "processing_fee": processing_fee,
                "net_disbursed": net_disbursed,
                "months_taken": months_taken,
                "interest_saved": round(interest_saved),
                "tenure_saved_months": tenure_saved_months,
                "yearly_data": yearly_data,
                "monthly_data": monthly_data
            })
            
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    # GET Request: Render the page
    CalcUsage.objects.create(name="EMI")
    return render(request, 'emi.html')
def home_loan(request):
    # If it's a POST request, we treat it as an API call
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})
        # Get Inputs
        P = float(data.get("amount", 0))
        annual_rate = float(data.get("rate", 0))
        years = float(data.get("time", 0))
        m_prepay = float(data.get("monthly_prepay", 0))
        y_prepay = float(data.get("yearly_prepay", 0))
        pf_pct = float(data.get("processing_fee_pct", 0))
        if P <= 0 or annual_rate <= 0 or years <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})
        r = annual_rate / 100 / 12
        n = int(years) * 12
        # 1. Base EMI Calculation (Standard without prepayments)
        base_emi = P * r * ((1 + r)**n) / ((1 + r)**n - 1)
        base_emi = round(base_emi, 2)
        base_total_interest = (base_emi * n) - P
        # Processing Fee
        processing_fee_amount = round(P * (pf_pct / 100), 2)
        # 2. Actual Amortization with Prepayments
        balance = P
        total_interest = 0
        months_taken = 0
        monthly_data = []
        yearly_data = []
        
        year_principal = 0
        year_interest = 0
        year_total_paid = 0
        for i in range(1, n + 1):
            if balance <= 0:
                break
            
            interest = balance * r
            principal = base_emi - interest
            # Apply Monthly Prepayment
            principal += m_prepay
            
            # Apply Yearly Prepayment (every 12th month)
            if i % 12 == 0:
                principal += y_prepay
            # Final payment adjustment
            if principal > balance:
                principal = balance
            balance -= principal
            total_interest += interest
            months_taken += 1
            # Accumulate yearly stats
            year_principal += principal
            year_interest += interest
            year_total_paid += (principal + interest)
            monthly_data.append({
                "month": i,
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "balance": round(balance, 2)
            })
            if i % 12 == 0 or balance <= 0:
                yearly_data.append({
                    "year": (i + 11) // 12, # Group properly if ending mid-year
                    "principal": round(year_principal, 2),
                    "interest": round(year_interest, 2),
                    "balance": round(balance, 2),
                    "total_paid": round(year_total_paid, 2)
                })
                year_principal = 0
                year_interest = 0
                year_total_paid = 0
        total_payment = P + total_interest
        # Prepayment Savings
        interest_saved = round(base_total_interest - total_interest, 2)
        if interest_saved < 0: 
            interest_saved = 0
        tenure_saved_months = n - months_taken
        CalcUsage.objects.create(name="HOME_LOAN")
        return JsonResponse({
            "success": True,
            "emi": base_emi,
            "principal": P,
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_payment, 2),
            "months_taken": months_taken,
            "interest_saved": interest_saved,
            "tenure_saved_months": tenure_saved_months,
            "processing_fee": processing_fee_amount,
            "monthly_data": monthly_data,
            "yearly_data": yearly_data
        })
    # For initial GET request, just render the HTML
    return render(request, 'loan/home_loan.html', locals())



def car_loan(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})
        # Get Inputs
        P = float(data.get("amount", 0))
        annual_rate = float(data.get("rate", 0))
        years = float(data.get("time", 0))
        m_prepay = float(data.get("monthly_prepay", 0))
        y_prepay = float(data.get("yearly_prepay", 0))
        pf_pct = float(data.get("processing_fee_pct", 0))
        if P <= 0 or annual_rate <= 0 or years <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})
        r = annual_rate / 100 / 12
        n = int(years) * 12
        # 1. Base EMI Calculation
        base_emi = P * r * ((1 + r)**n) / ((1 + r)**n - 1)
        base_emi = round(base_emi, 2)
        base_total_interest = (base_emi * n) - P
        # Processing Fee
        processing_fee_amount = round(P * (pf_pct / 100), 2)
        # 2. Amortization with Prepayments
        balance = P
        total_interest = 0
        months_taken = 0
        monthly_data = []
        yearly_data = []
        
        year_principal = 0
        year_interest = 0
        year_total_paid = 0
        for i in range(1, n + 1):
            if balance <= 0:
                break
            
            interest = balance * r
            principal = base_emi - interest
            # Apply Prepayments
            principal += m_prepay
            if i % 12 == 0:
                principal += y_prepay
            if principal > balance:
                principal = balance
            balance -= principal
            total_interest += interest
            months_taken += 1
            year_principal += principal
            year_interest += interest
            year_total_paid += (principal + interest)
            monthly_data.append({
                "month": i,
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "balance": round(balance, 2)
            })
            if i % 12 == 0 or balance <= 0:
                yearly_data.append({
                    "year": (i + 11) // 12, 
                    "principal": round(year_principal, 2),
                    "interest": round(year_interest, 2),
                    "balance": round(balance, 2),
                    "total_paid": round(year_total_paid, 2)
                })
                year_principal = 0
                year_interest = 0
                year_total_paid = 0
        total_payment = P + total_interest
        interest_saved = round(base_total_interest - total_interest, 2)
        if interest_saved < 0: interest_saved = 0
        tenure_saved_months = n - months_taken
        CalcUsage.objects.create(name="CAR_LOAN")
        return JsonResponse({
            "success": True,
            "emi": base_emi,
            "principal": P,
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_payment, 2),
            "months_taken": months_taken,
            "interest_saved": interest_saved,
            "tenure_saved_months": tenure_saved_months,
            "processing_fee": processing_fee_amount,
            "monthly_data": monthly_data,
            "yearly_data": yearly_data
        })
    return render(request, 'loan/car_loan.html', locals())

def personal_loan(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        # Get Inputs
        P = float(data.get("amount", 0))
        annual_rate = float(data.get("rate", 0))
        years = float(data.get("time", 0))
        m_prepay = float(data.get("monthly_prepay", 0))
        y_prepay = float(data.get("yearly_prepay", 0))
        pf_pct = float(data.get("processing_fee_pct", 0))

        if P <= 0 or annual_rate <= 0 or years <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})

        r = annual_rate / 100 / 12
        n = int(years * 12)

        # Base EMI (Without Prepayment)
        base_emi = P * r * ((1 + r)**n) / (((1 + r)**n) - 1)
        base_total_payment = base_emi * n
        base_total_interest = base_total_payment - P

        # Prepayment Tracking Variables
        balance = P
        total_interest = 0
        monthly_data = []
        yearly_data = []

        year_prin = 0
        year_int = 0
        months_taken = 0

        for i in range(1, n + 1):
            if balance <= 0:
                break

            months_taken += 1
            interest_for_month = balance * r
            
            # The actual payment we make this month
            current_payment = base_emi + m_prepay
            
            # If it's the end of a year, add yearly prepayment
            if i % 12 == 0:
                current_payment += y_prepay
                
            # If balance + interest is less than the payment, we just pay it off
            if current_payment > (balance + interest_for_month):
                current_payment = balance + interest_for_month
                
            principal_for_month = current_payment - interest_for_month

            total_interest += interest_for_month
            balance -= principal_for_month
            if balance < 0: balance = 0

            year_int += interest_for_month
            year_prin += principal_for_month

            monthly_data.append({
                "month": i,
                "emi": round(base_emi, 2),
                "principal": round(principal_for_month, 2),
                "interest": round(interest_for_month, 2),
                "balance": round(balance, 2)
            })

            if i % 12 == 0 or balance == 0:
                yearly_data.append({
                    "year": (i + 11) // 12,  # 1-12 = Year 1, 13-24 = Year 2
                    "principal": round(year_prin, 2),
                    "interest": round(year_int, 2),
                    "balance": round(balance, 2),
                    "total_paid": round(year_prin + year_int, 2)
                })
                year_prin = 0
                year_int = 0

        total_payment = P + total_interest
        interest_saved = round(base_total_interest - total_interest, 2)
        if interest_saved < 0: interest_saved = 0
        tenure_saved_months = n - months_taken
        
        # Calculate Processing Fee (usually deducted from disbursed amount)
        processing_fee_amt = round(P * (pf_pct / 100), 2)
        disbursed_amt = round(P - processing_fee_amt, 2)

        CalcUsage.objects.create(name="PERSONAL_LOAN")

        return JsonResponse({
            "success": True,
            "emi": round(base_emi, 2),
            "principal": P,
            "total_interest": round(total_interest, 2),
            "total_payment": round(total_payment, 2),
            "months_taken": months_taken,
            "interest_saved": interest_saved,
            "tenure_saved_months": tenure_saved_months,
            "processing_fee_amt": processing_fee_amt,
            "disbursed_amt": disbursed_amt,
            "monthly_data": monthly_data,
            "yearly_data": yearly_data
        })

    return render(request, 'loan/personal_loan.html', locals())

def ppf_calc(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        yearly_amount = float(data.get("amount", 150000))
        rate = float(data.get("rate", 7.1))
        years = int(data.get("time", 15))
        frequency = data.get("frequency", "yearly")  # 'monthly' or 'yearly'
        tax_slab = float(data.get("tax_slab", 30))   # 0, 5, 10, 20, 30

        # Validate
        if yearly_amount <= 0 or years < 15 or rate <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})

        # PPF allows only 15 + 5-year blocks
        valid_years = [15, 20, 25, 30, 35, 40, 45, 50]
        if years not in valid_years:
            years = min(valid_years, key=lambda y: abs(y - years))

        annual_rate = rate / 100
        monthly_rate = annual_rate / 12

        # If monthly, deposit per month; else lump sum in April (start of FY)
        if frequency == "monthly":
            monthly_deposit = yearly_amount / 12
        else:
            monthly_deposit = None  # lump sum yearly

        total_invested = 0
        total_corpus = 0
        yearly_data = []

        for year in range(1, years + 1):
            opening_balance = total_corpus
            year_invested = 0
            annual_interest = 0

            if frequency == "monthly":
                # True month-by-month PPF simulation
                # Interest is calculated on min balance between 5th and EOM
                # Assuming deposit is before 5th, so full month counts
                balance_at_start = total_corpus
                for month in range(1, 13):
                    balance_at_start += monthly_deposit
                    year_invested += monthly_deposit
                    # Interest credited at end of FY, but calculated monthly
                    annual_interest += balance_at_start * monthly_rate
                total_corpus = opening_balance + year_invested + annual_interest
            else:
                # Yearly lump sum deposited on April 1st (before 5th - earns full year)
                year_invested = yearly_amount
                total_corpus = (opening_balance + year_invested) * (1 + annual_rate)
                annual_interest = total_corpus - opening_balance - year_invested

            total_invested += year_invested

            yearly_data.append({
                "year": year,
                "opening": round(opening_balance, 2),
                "deposited": round(year_invested, 2),
                "interest": round(annual_interest, 2),
                "closing": round(total_corpus, 2),
                "total_invested": round(total_invested, 2),
            })

        wealth_gained = total_corpus - total_invested

        # Section 80C Tax Saving calculation
        deductible_per_year = min(yearly_amount, 150000)
        tax_saved_per_year = deductible_per_year * (tax_slab / 100) * 1.04  # 4% cess
        total_tax_saved = tax_saved_per_year * years

        CalcUsage.objects.create(name="PPF")

        return JsonResponse({
            "success": True,
            "total_corpus": round(total_corpus, 2),
            "total_invested": round(total_invested, 2),
            "wealth_gained": round(wealth_gained, 2),
            "tax_saved_per_year": round(tax_saved_per_year, 2),
            "total_tax_saved": round(total_tax_saved, 2),
            "yearly_data": yearly_data
        })

    return render(request, 'investment/ppf.html', locals())

def nps_calc(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})
        # Get Inputs
        P = float(data.get("amount", 0))
        age = int(data.get("age", 30))
        annual_rate = float(data.get("rate", 10.0))
        annuity_pct = float(data.get("annuity_pct", 40))
        annuity_rate = float(data.get("annuity_rate", 6.0))
        if P <= 0 or age >= 60 or annual_rate <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})
        years = 60 - age
        n_months = years * 12
        r = annual_rate / 100 / 12
        total_invested = P * n_months
        
        # Calculate Corpus using SIP Future Value formula 
        # (Assuming investment at the start of each month)
        # FV = P * [ ((1+r)^n - 1) / r ] * (1+r)
        total_corpus = P * (((1 + r)**n_months - 1) / r) * (1 + r)
        
        # Maturity Breakdown at age 60
        annuity_amount = total_corpus * (annuity_pct / 100)
        lumpsum_amount = total_corpus - annuity_amount
        
        # Monthly Pension (Annuity amount * annual rate / 12)
        monthly_pension = annuity_amount * (annuity_rate / 100) / 12
        
        # Build Yearly Schedule
        yearly_data = []
        current_corpus = 0
        current_invested = 0
        
        for year in range(1, years + 1):
            for month in range(1, 13):
                current_invested += P
                current_corpus = (current_corpus + P) * (1 + r)
                
            yearly_data.append({
                "age": age + year,
                "invested": round(current_invested, 2),
                "returns": round(current_corpus - current_invested, 2),
                "corpus": round(current_corpus, 2)
            })
        CalcUsage.objects.create(name="NPS")
        return JsonResponse({
            "success": True,
            "total_invested": round(total_invested, 2),
            "total_corpus": round(total_corpus, 2),
            "lumpsum_amount": round(lumpsum_amount, 2),
            "annuity_amount": round(annuity_amount, 2),
            "monthly_pension": round(monthly_pension, 2),
            "wealth_gained": round(total_corpus - total_invested, 2),
            "yearly_data": yearly_data
        })
    return render(request, 'investment/nps.html', locals())
def retirement_calc(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        current_age    = int(float(data.get("current_age", 30)))
        ret_age        = int(float(data.get("ret_age", 60)))
        existing       = float(data.get("savings", 0))
        monthly_sip    = float(data.get("monthly_sip", 10000))
        annual_return  = float(data.get("rate", 12))
        step_up_pct    = float(data.get("step_up_pct", 0))       # % annual SIP increase
        monthly_exp    = float(data.get("monthly_expense", 50000))
        inflation      = float(data.get("inflation", 6))

        # Basic validation
        if ret_age <= current_age:
            return JsonResponse({"success": False, "error": "Retirement age must be greater than current age"})
        if monthly_sip < 0 or existing < 0 or annual_return <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})

        years       = ret_age - current_age
        monthly_r   = annual_return / 100 / 12
        inflation_r = inflation / 100

        # ── Stream 1: Existing corpus compounds for full duration ──
        stream1_corpus = existing * ((1 + monthly_r) ** (years * 12))

        # ── Stream 2: Step-Up SIP compounding year by year ──
        stream2_corpus = 0
        current_sip    = monthly_sip
        yearly_data    = []
        cumulative_invested = existing
        total_sip_invested  = 0

        for year in range(1, years + 1):
            for month in range(1, 13):
                stream2_corpus = (stream2_corpus + current_sip) * (1 + monthly_r)
                total_sip_invested += current_sip

            # Step up SIP at end of each year
            if step_up_pct > 0:
                current_sip = current_sip * (1 + step_up_pct / 100)

            cumulative_invested = existing + total_sip_invested
            total_corpus_now = (existing * ((1 + monthly_r) ** (year * 12))) + stream2_corpus

            yearly_data.append({
                "age": current_age + year,
                "invested": round(cumulative_invested, 2),
                "returns": round(total_corpus_now - cumulative_invested, 2),
                "corpus": round(total_corpus_now, 2),
            })

        total_corpus   = stream1_corpus + stream2_corpus
        total_invested = existing + total_sip_invested
        wealth_gained  = total_corpus - total_invested

        # ── Inflation-Adjusted Corpus Goal (4% Rule) ──
        # What will monthly_exp cost at retirement?
        inflation_factor         = (1 + inflation_r) ** years
        expense_at_retirement    = monthly_exp * inflation_factor        # monthly
        annual_exp_at_retirement = expense_at_retirement * 12
        required_corpus          = annual_exp_at_retirement * 25         # 4% Rule = 25x annual expenses
        corpus_gap               = required_corpus - total_corpus        # positive = short, negative = ahead

        # ── Post-Retirement Sustainability ──
        # How long does corpus last drawing expense_at_retirement/month at 7% post-ret return?
        post_ret_r      = 7 / 100 / 12
        balance         = total_corpus
        months_lasting  = 0
        monthly_draw    = expense_at_retirement
        while balance > 0 and months_lasting < 600:   # cap at 50 years
            balance = balance * (1 + post_ret_r) - monthly_draw
            months_lasting += 1

        years_lasting  = months_lasting // 12
        months_lasting_rem = months_lasting % 12

        CalcUsage.objects.create(name="RETIREMENT")

        return JsonResponse({
            "success": True,
            "total_corpus": round(total_corpus, 2),
            "total_invested": round(total_invested, 2),
            "wealth_gained": round(wealth_gained, 2),
            "required_corpus": round(required_corpus, 2),
            "corpus_gap": round(corpus_gap, 2),
            "expense_at_retirement": round(expense_at_retirement, 2),
            "years_lasting": years_lasting,
            "months_lasting_rem": months_lasting_rem,
            "yearly_data": yearly_data,
        })

    return render(request, 'investment/retirement.html', locals())

def salary_calc(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        ctc           = float(data.get("ctc", 1000000))
        basic_pct     = float(data.get("basic_pct", 40)) / 100
        annual_bonus  = float(data.get("bonus", 0))
        is_metro      = bool(data.get("is_metro", True))
        monthly_rent  = float(data.get("monthly_rent", 0))
        other_80c     = float(data.get("other_80c", 0))  # PPF, ELSS etc.

        if ctc <= 0:
            return JsonResponse({"success": False, "error": "Invalid CTC"})

        # ── CTC Breakdown ──
        basic_annual      = ctc * basic_pct
        employer_pf       = basic_annual * 0.12        # Part of CTC, not in-hand
        gratuity          = basic_annual * 0.0481      # 4.81% of Basic

        gross_annual      = ctc - employer_pf - gratuity
        hra_annual        = basic_annual * (0.50 if is_metro else 0.40)
        special_allowance = max(0, gross_annual - basic_annual - hra_annual)

        # ── Employee Deductions (from in-hand) ──
        employee_pf       = basic_annual * 0.12
        professional_tax  = 2400   # ₹200/month standard

        # ════════════════════════════════════
        #  NEW REGIME  (FY 2024-25)
        # ════════════════════════════════════
        std_new      = 75000
        taxable_new  = max(0, gross_annual + annual_bonus - std_new - employee_pf)

        def slab_new(inc):
            t = 0
            slabs = [(300000,0),(700000,0.05),(1000000,0.10),(1200000,0.15),(1500000,0.20)]
            prev = 0
            for limit, rate in slabs:
                if inc <= limit:
                    t += (inc - prev) * rate; break
                t += (limit - prev) * rate
                prev = limit
            else:
                t += (inc - 1500000) * 0.30
            return t

        tax_new_base = 0 if taxable_new <= 700000 else slab_new(taxable_new)
        tax_new      = round(tax_new_base * 1.04, 2)   # +4% cess

        # ════════════════════════════════════
        #  OLD REGIME  (FY 2024-25)
        # ════════════════════════════════════
        std_old      = 50000

        # HRA Exemption (least of 3 conditions)
        hra_exempt = 0
        if monthly_rent > 0:
            hra_exempt = min(
                hra_annual,
                basic_annual * (0.50 if is_metro else 0.40),
                max(0, monthly_rent * 12 - basic_annual * 0.10)
            )

        # 80C: EPF already counts, cap total at ₹1.5L
        epf_80c    = min(employee_pf, 150000)
        extra_80c  = min(other_80c, max(0, 150000 - epf_80c))
        total_80c  = epf_80c + extra_80c

        taxable_old = max(0, gross_annual + annual_bonus - std_old - hra_exempt - total_80c)

        def slab_old(inc):
            t = 0
            slabs = [(250000,0),(500000,0.05),(1000000,0.20)]
            prev = 0
            for limit, rate in slabs:
                if inc <= limit:
                    t += (inc - prev) * rate; break
                t += (limit - prev) * rate
                prev = limit
            else:
                t += (inc - 1000000) * 0.30
            return t

        tax_old_base = 0 if taxable_old <= 500000 else slab_old(taxable_old)
        tax_old      = round(tax_old_base * 1.04, 2)   # +4% cess

        # ── Regime Comparison ──
        better_regime = "new" if tax_new <= tax_old else "old"
        tax_saving    = abs(tax_old - tax_new)

        # ── Final In-Hand ──
        def inhand(tax):
            a = gross_annual + annual_bonus - employee_pf - professional_tax - tax
            return {"annual": round(a, 2), "monthly": round(a / 12, 2)}

        ih_new = inhand(tax_new)
        ih_old = inhand(tax_old)

        CalcUsage.objects.create(name="SALARY")

        return JsonResponse({
            "success": True,
            # CTC Components (Annual)
            "ctc":               round(ctc, 2),
            "basic_annual":      round(basic_annual, 2),
            "hra_annual":        round(hra_annual, 2),
            "special_allowance": round(special_allowance, 2),
            "employer_pf":       round(employer_pf, 2),
            "gratuity":          round(gratuity, 2),
            "annual_bonus":      round(annual_bonus, 2),
            "gross_annual":      round(gross_annual, 2),
            # Deductions
            "employee_pf":       round(employee_pf, 2),
            "professional_tax":  professional_tax,
            "hra_exempt":        round(hra_exempt, 2),
            "total_80c":         round(total_80c, 2),
            # Tax
            "taxable_new":       round(taxable_new, 2),
            "tax_new":           tax_new,
            "taxable_old":       round(taxable_old, 2),
            "tax_old":           tax_old,
            "better_regime":     better_regime,
            "tax_saving":        round(tax_saving, 2),
            # In-Hand
            "inhand_new_monthly": ih_new["monthly"],
            "inhand_new_annual":  ih_new["annual"],
            "inhand_old_monthly": ih_old["monthly"],
            "inhand_old_annual":  ih_old["annual"],
        })

    return render(request, 'salary/salary.html', locals())

# def pf_calc(request):
#     result = None
#     table_data = []

#     if request.method == "POST":
#         salary = float(request.POST.get("salary"))

#         pf = salary * 0.12

#         for i in range(1,13):
#             table_data.append({"month": i, "pf": pf*i})

#         result = pf*12
#     CalcUsage.objects.create(name="PF")
#     return render(request, 'salary/pf.html', locals())

def pf_calc(request):
    if request.method == "POST" and request.headers.get('Content-Type') == 'application/json':
        try:
            data = json.loads(request.body)
            initial_salary = float(data.get("basic", 0))
            years = int(data.get("time", 20))
            emp_pct = float(data.get("emp_pct", 12)) / 100
            interest_rate = float(data.get("rate", 8.25)) / 100
            salary_increment = float(data.get("hike", 5.0)) / 100
            inflation_rate = float(data.get("inflation", 6.0)) / 100

            corpus = 0.0
            total_invested = 0.0
            current_salary = initial_salary
            monthly_rate = interest_rate / 12
            pf_rate_total = emp_pct + 0.0367

            yearly_data = []
            monthly_data = []

            for year in range(1, years + 1):
                if year > 1:
                    current_salary *= (1 + salary_increment)

                monthly_contribution = current_salary * pf_rate_total
                year_deposit = 0
                year_interest = 0
                opening_bal = corpus

                for month in range(1, 13):
                    month_opening = corpus
                    corpus += monthly_contribution
                    year_deposit += monthly_contribution
                    interest_this_month = corpus * monthly_rate
                    year_interest += interest_this_month
                    corpus += interest_this_month

                    monthly_data.append({
                        "year": year,
                        "month": month,
                        "openingBal": round(month_opening),
                        "deposited": round(monthly_contribution),
                        "interest": round(interest_this_month),
                        "total": round(corpus)
                    })

                total_invested += year_deposit
                yearly_data.append({
                    "year": year,
                    "openingBal": round(opening_bal),
                    "deposited": round(year_deposit),
                    "interest": round(year_interest),
                    "investedTotal": round(total_invested),
                    "profitTotal": round(corpus - total_invested),
                    "total": round(corpus)
                })

            total_profit = corpus - total_invested
            real_value = corpus / ((1 + inflation_rate) ** years) if inflation_rate > 0 else corpus

            return JsonResponse({
                "status": "success",
                "total": round(corpus),
                "invested": round(total_invested),
                "profit": round(total_profit),
                "real_value": round(real_value),
                "yearlyData": yearly_data,
                "monthlyData": monthly_data
            })

        except (ValueError, TypeError, KeyError) as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return render(request, 'salary/pf.html', {})
def loan_eligibility(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

        salary   = float(data.get("salary", 0))
        existing = float(data.get("existing", 0))
        score    = int(data.get("score", 750))
        rate     = float(data.get("rate", 8.5))
        years    = int(data.get("years", 20))

        if salary <= 0 or rate <= 0 or years <= 0:
            return JsonResponse({"success": False, "error": "Invalid inputs"})

        # ── FOIR based on salary bracket (standard Indian bank rules) ──
        if salary > 200000:   foir = 0.65
        elif salary > 100000: foir = 0.60
        elif salary > 75000:  foir = 0.55
        elif salary > 25000:  foir = 0.50
        else:                 foir = 0.40

        # ── CIBIL Score Multiplier ──
        if score < 600:
            score_mult   = 0.0
            score_status = "Poor — Likely Rejected"
            score_color  = "rose"
        elif score < 650:
            score_mult   = 0.5
            score_status = "Fair — High Risk"
            score_color  = "gold"
        elif score < 700:
            score_mult   = 0.75
            score_status = "Average — Limited Options"
            score_color  = "gold"
        elif score < 750:
            score_mult   = 0.85
            score_status = "Good — Standard Terms"
            score_color  = "blue"
        else:
            score_mult   = 1.0
            score_status = "Excellent — Best Rates"
            score_color  = "green"

        max_total_emi = salary * foir
        available_emi = max(0, (max_total_emi - existing) * score_mult)
        take_home     = max(0, salary - existing - available_emi)

        # ── Loan Amount via PV Annuity Formula ──
        def calc_loan(emi, r_annual, y):
            mr = r_annual / 100 / 12
            n  = y * 12
            if mr <= 0 or n <= 0 or emi <= 0:
                return 0
            return round(emi * ((1 + mr)**n - 1) / (mr * (1 + mr)**n), 2)

        eligible_loan = calc_loan(available_emi, rate, years)

        # ── Tenure Comparison Table (backend computed) ──
        tenure_table = []
        for t in [5, 10, 15, 20, 25, 30]:
            loan_amt = calc_loan(available_emi, rate, t)
            tenure_table.append({
                "tenure": t,
                "rate":   rate,
                "emi":    round(available_emi, 2),
                "loan":   loan_amt
            })

        CalcUsage.objects.create(name="LOAN_ELIGIBILITY")

        return JsonResponse({
            "success":       True,
            "eligible_loan": round(eligible_loan, 2),
            "available_emi": round(available_emi, 2),
            "max_total_emi": round(max_total_emi, 2),
            "take_home":     round(take_home, 2),
            "existing_emi":  round(existing, 2),
            "foir_pct":      round(foir * 100),
            "score_status":  score_status,
            "score_color":   score_color,
            "tenure_table":  tenure_table,
        })

    return render(request, 'eligibility/eligibility.html', locals())
# def like_blog(request, id):
#     blog = Blog.objects.get(id=id)
#     blog.likes += 1
#     blog.save()

#     return JsonResponse({'likes': blog.likes})
def like_blog(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    
    liked_blogs = request.session.get('liked_blogs', [])

    if blog.id in liked_blogs:
        blog.likes -= 1
        liked_blogs.remove(blog.id)
        is_liked = False
    else:
        blog.likes += 1
        liked_blogs.append(blog.id)
        is_liked = True

    blog.save()
    request.session['liked_blogs'] = liked_blogs

    return JsonResponse({
        'likes': blog.likes,
        'liked': is_liked  
    })
def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required!'})

        user_subject = "Welcome to Vita₹thi! 🎉"
        user_message = f"""Hi there,

Thank you for subscribing to Vita₹thi! 

We're thrilled to have you on board. You'll now receive our latest financial guides, investment strategies, and calculators directly in your inbox. 

Stay tuned for our next update!

Cheers,
Team Vita₹thi
"""
        
        # ✉️ 2. EMAIL TO COMPANY/ADMINS (Notification Mail)
        company_subject = "🚀 New Newsletter Subscriber!"
        company_message = f"Great news!\n\nA new user has just subscribed to the Vita₹thi newsletter.\n\nSubscriber Email: {email}"
        
        # Send mail to company 
        company_emails = ['snehilsingh7800m@gmail.com', 'iamcjayesh519@gmail.com'] 

        try:
            send_mail(
                user_subject,
                user_message,
                settings.EMAIL_HOST_USER, 
                [email], 
                fail_silently=False,
            )
            
            send_mail(
                company_subject,
                company_message,
                settings.EMAIL_HOST_USER,
                company_emails,
                fail_silently=False,
            )
            
            return JsonResponse({'status': 'success', 'message': 'Subscribed successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


import requests

import requests

def get_market_data():
    try:
        # ---------- USD → INR ----------
        rate_res = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=INR").json()
        usd_inr = rate_res["rates"]["INR"]

        # ---------- GOLD (approx via XAU price proxy) ----------
        gold_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd").json()
        gold_usd = gold_res.get("gold", {}).get("usd", 0)

        # ---------- SILVER ----------
        silver_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=silver&vs_currencies=usd").json()
        silver_usd = silver_res.get("silver", {}).get("usd", 0)

        # ---------- BTC ----------
        btc_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").json()
        btc_usd = btc_res["bitcoin"]["usd"]

        return {
            "gold": round(gold_usd * usd_inr, 2),
            "silver": round(silver_usd * usd_inr, 2),
            "btc": round(btc_usd * usd_inr, 2),
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "gold": "N/A",
            "silver": "N/A",
            "btc": "N/A"
        }

def calc_count(request):
    count = CalcUsage.objects.count()
    return JsonResponse({'count': count})

def popular_calculators(request):
    data = (
        CalcUsage.objects
        .values('name')
        .annotate(total=Count('name'))
        .order_by('-total')
    )

    return JsonResponse(list(data), safe=False)

def add_secondary(request):
    data = json.loads(request.body)

    name = data.get("name")
    primary_id = data.get("primary_id")

    if not name or not primary_id:
        return JsonResponse({"status": "error", "message": "Name & Primary required"})

    try:
        primary = PrimaryCategory.objects.get(id=primary_id)
    except PrimaryCategory.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Invalid primary"})

    cat = SecondaryCategory.objects.create(
        name=name,
        primary=primary   
    )

    return JsonResponse({
        "status": "success",
        "id": cat.id,
        "name": cat.name
    })


def delete_secondary(request, id):
    SecondaryCategory.objects.filter(id=id).delete()
    return JsonResponse({"status": "success"})

def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    return render(request, 'errors/500.html', status=500)

def custom_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def custom_400(request, exception):
    return render(request, 'errors/400.html', status=400)

def sitemap_ui(request):

    sitemap_links = [
        {
            "title": "Posts Sitemap",
            "url": "/sitemap-posts.xml",
            "desc": "Blogs, news and case studies"
        },
        {
            "title": "Pages Sitemap",
            "url": "/sitemap-pages.xml",
            "desc": "Static pages"
        },
        {
            "title": "Categories Sitemap",
            "url": "/sitemap-categories.xml",
            "desc": "Secondary category archive pages"
        },
        {
            "title": "Calculators Sitemap",
            "url": "/sitemap-calculators.xml",
            "desc": "All calculator pages"
        }
    ]

    return render(request, 'sitemap.html', {
        'sitemaps': sitemap_links
    })


import os
def styled_sitemap(request, sitemap_response):

    sitemap_response.render()

    content = sitemap_response.content.decode()

    content = content.replace(
        '<?xml version="1.0" encoding="UTF-8"?>',
        '''<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="/static/sitemap.xsl"?>'''
    )

    return HttpResponse(
        content,
        content_type='application/xml'
    )

@require_POST
def contact_submit(request):
    print("CONTACT API HIT_before")
    try:
        print("CONTACT API HIT")
        data = json.loads(request.body)
        print(data)
        if data.get('website'):
            return JsonResponse({
                'status': 'error',
                'message': 'Spam detected'
            }, status=400)
        contact = ContactMessage.objects.create(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            category=data.get('categoryInput'),
            calculator=data.get('calculator'),
            subject=data.get('subject'),
            message=data.get('message'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        send_mail(
            subject='We received your message | Vittarthi',
            message=f'''
        Hi {contact.first_name},
        Your Ticket ID :
        {contact.ticket_id}
        Thank you for contacting Vittarthi.
        We’ve received your message regarding:
        "{contact.subject}"
        Our team will review it and get back to you soon.
        Typical response times:
        • General queries → 1–2 business days
        • Bug reports → within 24 hours
        • Privacy requests → within 5 business days
        Regards,
        Team Vittarthi
        https://vittarthi.com
        ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            fail_silently=True
        )   
        send_mail(
            subject=f'New Contact Form | {contact.category}',
            message=f'''
        New contact form submitted.
        Name:
        {contact.first_name} {contact.last_name}
        Ticket ID:
        {contact.ticket_id}
        Email:
        {contact.email}
        Category:
        {contact.category}
        Subject:
        {contact.subject}
        Message:
        {contact.message}
        ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['vittarthi2026@gmail.com'],
            fail_silently=True
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Message saved successfully',
            'ticket_id': contact.ticket_id
        })

    except Exception as e:

        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    
def contact_page(request):

    return render(
        request,
        'vita/contact.html'
    )


def privacy_policy(request):
    policy = PrivacyPolicy.objects.first()
    return render(request, "vita/privacy.html", {
        "policy": policy
    })

def legal_page(request, slug):

    page = get_object_or_404(
        LegalPage,
        slug=slug
    )

    return render(request, "vita/legal_page.html", {
        "page": page
    })

def aboutus(request):

    return render(
        request,
        'vita/aboutus.html'
    )

def authors(request):

    authors = Author.objects.filter(
        is_active=True
    )

    for author in authors:

        # WRITTEN
        author.total_written = Blog.objects.filter(
            author_profile=author,
            status='published'
        ).count()

        # REVIEWED
        author.total_reviewed = Blog.objects.filter(
            reviewed_by=author,
            status='published'
        ).count()

        # EDITED
        author.total_edited = Blog.objects.filter(
            edited_by=author,
            status='published'
        ).count()

        # TOTAL
        author.total_articles = (
            author.total_written +
            author.total_reviewed +
            author.total_edited
        )

    return render(
        request,
        'author/authors.html',
        {
            'authors': authors
        }
    )
def author_detail(request, slug):

    author = get_object_or_404(Author, slug=slug)

    written_articles_qs = Blog.objects.filter(
        author_profile=author,
        status='published'
    ).select_related(
        'primary_category',
        'secondary_category'
    ).order_by('-created_at')

    reviewed_articles_qs = Blog.objects.filter(
        reviewed_by=author,
        status='published'
    ).select_related(
        'primary_category',
        'secondary_category'
    ).order_by('-created_at')

    edited_articles_qs = Blog.objects.filter(
        edited_by=author,
        status='published'
    ).select_related(
        'primary_category',
        'secondary_category'
    ).order_by('-created_at')

    paginator = Paginator(written_articles_qs, 3)

    page_number = request.GET.get('page')

    written_articles = paginator.get_page(page_number)

    total_articles = written_articles_qs.count()
    total_reviewed = reviewed_articles_qs.count()
    total_edited = edited_articles_qs.count()

    # EXPERTISE
    expertise_categories = []
    seen = set()

    source_queryset = written_articles_qs

    if author.role.lower() == 'reviewer':
        source_queryset = reviewed_articles_qs

    elif author.role.lower() == 'editor':
        source_queryset = edited_articles_qs

    for blog in source_queryset:

        if blog.secondary_category:

            slug = blog.secondary_category.slug

            if slug not in seen:

                expertise_categories.append({
                    'name': blog.secondary_category.name,
                    'slug': slug,
                    'primary_slug': blog.primary_category.slug
                })

                seen.add(slug)
    breadcrumbs = [
        {'name': 'Home', 'url': '/'},
        {'name': 'Authors', 'url': '/authors'},
        {'name': author.name, 'url': ''}
    ]
    context = {
        'breadcrumbs': breadcrumbs,
        'author': author,

        'written_articles': written_articles_qs,
        'reviewed_articles': reviewed_articles_qs,
        'edited_articles': edited_articles_qs,

        'total_articles': total_articles,
        'total_reviewed': total_reviewed,
        'total_edited': total_edited,

        'expertise_categories': expertise_categories,

        'is_writer': author.role.lower() == 'writer',
        'is_reviewer': author.role.lower() == 'reviewer',
        'is_editor': author.role.lower() == 'editor',

        'written_articles_paginated': written_articles,
    }

    return render(request, 'author/author_detail.html', context)

def resources(request):

    blogs = Blog.objects.filter(
        status='published'
    ).filter(
        Q(primary_category__slug='blogs') |
        Q(secondary_category__slug='blogs')
    ).order_by('-created_at')[:3]

    news = Blog.objects.filter(
        status='published'
    ).filter(
        Q(primary_category__slug='news') |
        Q(secondary_category__slug='news')
    ).order_by('-created_at')[:3]

    case_studies = Blog.objects.filter(
        status='published'
    ).filter(
        Q(primary_category__slug='case-study') |
        Q(secondary_category__slug='case-study')
    ).order_by('-created_at')[:3]
    for section in [blogs, news, case_studies]:
        for item in section:

            soup = BeautifulSoup(item.content, "html.parser")

            # remove style & script tags completely
            for tag in soup(["style", "script"]):
                tag.decompose()

            clean_text = soup.get_text(separator=" ", strip=True)

            item.content = clean_text
    context = {
        'blogs': blogs,
        'news': news,
        'case_studies': case_studies,
    }

    return render(request, 'blogs/blog_home.html', context)

def resource_category(request, primary_slug):

    blogs = Blog.objects.filter(
        status='published'
    ).filter(
        Q(primary_category__slug=primary_slug) |
        Q(secondary_category__slug=primary_slug)
    ).distinct().order_by('-created_at')

    context = {
        'blogs': blogs,
        'primary_slug': primary_slug
    }

    return render(request, 'blogs/list.html', context)

@admin_required
def admin_dashboard(request):

    users = CustomUser.objects.all().order_by('id')

    return render(
        request,
        'vita/access.html',
        {
            'users': users
        }
    )

@admin_required
def change_role(request, user_id):
    if request.method == "POST":
        role = request.POST.get("role")
        user = CustomUser.objects.get(id=user_id)
        user.role = role
        user.save()
        messages.success(request, "Role updated successfully")
    return redirect('admin_dashboard')




def sip_fv(monthly, rate_annual, years):
    r = rate_annual / 100 / 12
    n = years * 12
    if r == 0:
        return monthly * n
    return monthly * (((math.pow(1 + r, n) - 1) / r) * (1 + r))

def fd_fv(monthly, rate_annual, years):
    rm = rate_annual / 100 / 12
    nm = years * 12
    if rm == 0:
        return monthly * nm
    return monthly * (((math.pow(1 + rm, nm) - 1) / rm))

@csrf_exempt
@require_http_methods(["POST", "GET"])
def api_sip_vs_fd(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
        else:
            data = request.GET
            
        monthly = float(data.get('monthly_amount', 5000))
        years = int(data.get('years', 10))
        sip_r = float(data.get('sip_rate', 12))
        fd_r = float(data.get('fd_rate', 6.5))
        
        invested = monthly * years * 12
        sip_val = sip_fv(monthly, sip_r, years)
        fd_val = fd_fv(monthly, fd_r, years)
        sip_gain = sip_val - invested
        fd_gain = fd_val - invested
        
        # Chart data
        labels = []
        sip_data = []
        fd_data = []
        
        for y in range(1, min(years, 30) + 1):
            labels.append(f'Yr {y}')
            sip_data.append(round(sip_fv(monthly, sip_r, y)))
            fd_data.append(round(fd_fv(monthly, fd_r, y)))
            
        return JsonResponse({
            'success': True,
            'summary': {
                'invested': round(invested),
                'sip_returns': round(sip_gain),
                'sip_total': round(sip_val),
                'sip_cagr': round(sip_r, 1),
                'fd_returns': round(fd_gain),
                'fd_total': round(fd_val),
            },
            'chart': {
                'labels': labels,
                'sip_data': sip_data,
                'fd_data': fd_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def ppf_fv(yearly, rate_annual, years):
    corpus = 0
    r = rate_annual / 100
    for _ in range(years):
        corpus = (corpus + yearly) * (1 + r)
    return corpus

def elss_fv(yearly, rate_annual, years):
    corpus = 0
    r = rate_annual / 100
    for _ in range(years):
        corpus = (corpus + yearly) * (1 + r)
    return corpus

def elss_post_tax(total, invested):
    gains = total - invested
    taxable_gains = max(0, gains - 100000)
    tax = taxable_gains * 0.10
    return total - tax

@csrf_exempt
@require_http_methods(["POST", "GET"])
def api_ppf_vs_elss(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
        else:
            data = request.GET
            
        yearly = float(data.get('yearly_amount', 150000))
        years = int(data.get('years', 15))
        ppf_r = 7.1  # Fixed by govt
        elss_r = float(data.get('elss_rate', 13))
        
        limited_yearly = min(yearly, 150000)
        invested = limited_yearly * years
        
        ppf_total = ppf_fv(limited_yearly, ppf_r, years)
        elss_pre = elss_fv(limited_yearly, elss_r, years)
        elss_post = elss_post_tax(elss_pre, invested)
        
        elss_gains = elss_pre - invested
        elss_ltcg = elss_pre - elss_post
        tax_saved = invested * 0.30
        
        # Chart milestones (every 5 years)
        labels = []
        ppf_data = []
        elss_data = []
        
        for y in range(5, min(years, 30) + 1, 5):
            labels.append(f'{y} Yrs')
            ppf_data.append(round(ppf_fv(limited_yearly, ppf_r, y)))
            ep = elss_fv(limited_yearly, elss_r, y)
            elss_data.append(round(elss_post_tax(ep, limited_yearly * y)))
            
        if years % 5 != 0:
            labels.append(f'{years} Yrs')
            ppf_data.append(round(ppf_total))
            elss_data.append(round(elss_post))
            
        return JsonResponse({
            'success': True,
            'summary': {
                'invested': round(invested),
                'ppf_interest': round(ppf_total - invested),
                'ppf_total': round(ppf_total),
                'ppf_tax_saved': round(tax_saved),
                'elss_gains': round(elss_gains),
                'elss_pretax': round(elss_pre),
                'elss_tax': round(elss_ltcg),
                'elss_total': round(elss_post),
            },
            'chart': {
                'labels': labels,
                'ppf_data': ppf_data,
                'elss_data': elss_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def calc_emi(p, r_annual, n):
    r = r_annual / 100 / 12
    if r == 0:
        return p / n
    return p * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)

def sip_lumpsum_fv(lumpsum, rate_annual, years):
    return lumpsum * math.pow(1 + rate_annual / 100, years)

@csrf_exempt
@require_http_methods(["POST", "GET"])
def api_home_loan_vs_rent(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
        else:
            data = request.GET
            
        prop = float(data.get('property_price', 8000000))
        dp_pct = float(data.get('down_payment_pct', 20))
        loan_r = float(data.get('loan_rate', 8.5))
        tenure = int(data.get('tenure_years', 20))
        app_r = float(data.get('appreciation_rate', 6))
        month_rent = float(data.get('monthly_rent', 20000))
        rent_inc = float(data.get('rent_increase', 8))
        sip_r = float(data.get('sip_rate', 12))
        
        dp = prop * dp_pct / 100
        loan_amt = prop - dp
        n = tenure * 12
        emi = calc_emi(loan_amt, loan_r, n)
        total_paid = emi * n
        total_int = total_paid - loan_amt
        prop_future = prop * math.pow(1 + app_r / 100, tenure)
        
        sip_corpus = sip_lumpsum_fv(dp, sip_r, tenure)
        
        total_rent = 0
        cur_rent = month_rent
        for _ in range(tenure):
            total_rent += cur_rent * 12
            cur_rent *= (1 + rent_inc / 100)
            
        buy_net_worth = prop_future
        rent_net_worth = max(0, sip_corpus - total_rent)
        
        # Break-even year calculation
        be_year = tenure + 1
        for y in range(1, tenure + 1):
            pv = prop * math.pow(1 + app_r / 100, y)
            buy_nw_y = max(0, pv)
            
            sc = sip_lumpsum_fv(dp, sip_r, y)
            tr = 0
            cr = month_rent
            for j in range(y):
                tr += cr * 12
                cr *= (1 + rent_inc / 100)
            rent_nw_y = max(0, sc - tr)
            
            if buy_nw_y >= rent_nw_y:
                be_year = y
                break
                
        # Chart Data
        labels = []
        buy_data = []
        rent_data = []
        
        for y in range(1, tenure + 1):
            labels.append(f'Yr {y}')
            buy_data.append(round(prop * math.pow(1 + app_r / 100, y)))
            
            sc = sip_lumpsum_fv(dp, sip_r, y)
            tr = 0
            cr = month_rent
            for j in range(y):
                tr += cr * 12
                cr *= (1 + rent_inc / 100)
            rent_data.append(round(max(0, sc - tr)))
            
        return JsonResponse({
            'success': True,
            'summary': {
                'loan_amt': round(loan_amt),
                'emi': round(emi),
                'total_int': round(total_int),
                'prop_future': round(prop_future),
                'buy_networth': round(buy_net_worth),
                'dp_invested': round(dp),
                'sip_corpus': round(sip_corpus),
                'total_rent': round(total_rent),
                'rent_networth': round(rent_net_worth),
                'breakeven_year': be_year,
                'tenure': tenure
            },
            'chart': {
                'labels': labels,
                'buy_data': buy_data,
                'rent_data': rent_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(['POST', 'GET'])
def api_sgb_vs_gold(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
        else:
            data = request.GET
            
        grams = float(data.get('grams', 10))
        price_per_gram = float(data.get('price_per_gram', 7500))
        app_r = float(data.get('appreciation_rate', 8))
        years = int(data.get('years', 8))
        
        import math
        raw_gold_value = grams * price_per_gram
        making_charges_pct = 10
        gst_pct = 3
        locker_cost_yearly = 1500
        
        physical_cost = raw_gold_value * (1 + (making_charges_pct + gst_pct) / 100)
        
        sgb_cost = raw_gold_value
        sgb_interest_rate = 2.5
        annual_sgb_interest = sgb_cost * (sgb_interest_rate / 100)
        
        labels = []
        phys_data = []
        sgb_data = []
        total_sgb_interest = 0
        total_locker_cost = 0
        
        for y in range(1, years + 1):
            labels.append(f'Yr {y}')
            current_raw_value = raw_gold_value * math.pow(1 + app_r / 100, y)
            total_locker_cost += locker_cost_yearly
            phys_data.append(round(current_raw_value - total_locker_cost))
            
            total_sgb_interest += annual_sgb_interest
            sgb_data.append(round(current_raw_value + total_sgb_interest))
            
        phys_final = phys_data[-1]
        sgb_final = sgb_data[-1]
        sgb_advantage = sgb_final - phys_final
        
        return JsonResponse({
            'success': True,
            'summary': {
                'raw_value': round(raw_gold_value),
                'physical_cost': round(physical_cost),
                'sgb_cost': round(sgb_cost),
                'total_sgb_interest': round(total_sgb_interest),
                'total_locker_cost': round(total_locker_cost),
                'phys_final': round(phys_final),
                'sgb_final': round(sgb_final),
                'sgb_advantage': round(sgb_advantage)
            },
            'chart': {
                'labels': labels,
                'phys_data': phys_data,
                'sgb_data': sgb_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(['POST', 'GET'])
def api_nps_vs_mf(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
        else:
            data = request.GET
            
        monthly = float(data.get('monthly_amount', 10000))
        current_age = int(data.get('current_age', 30))
        retire_age = 60
        years = retire_age - current_age
        mf_rate = float(data.get('mf_rate', 12))
        nps_rate = float(data.get('nps_rate', 10))
        tax_slab = float(data.get('tax_slab', 30))
        
        invested = monthly * years * 12
        
        mf_corpus = sip_fv(monthly, mf_rate, years)
        mf_gains = mf_corpus - invested
        mf_tax = max(0, mf_gains - 100000) * 0.10
        mf_post_tax = mf_corpus - mf_tax
        
        nps_corpus = sip_fv(monthly, nps_rate, years)
        nps_lumpsum = nps_corpus * 0.60
        nps_annuity_corpus = nps_corpus * 0.40
        
        yearly_nps_contrib = monthly * 12
        eligible_80ccd = min(50000, yearly_nps_contrib)
        total_tax_saved = (eligible_80ccd * (tax_slab / 100)) * years
        
        labels = []
        mf_data = []
        nps_data = []
        
        for y in range(5, min(years, 40) + 1, 5):
            labels.append(f'Age {current_age + y}')
            c = sip_fv(monthly, mf_rate, y)
            t = max(0, (c - (monthly*y*12)) - 100000) * 0.10
            mf_data.append(round(c - t))
            nps_data.append(round(sip_fv(monthly, nps_rate, y)))
            
        if years % 5 != 0:
            labels.append(f'Age 60')
            mf_data.append(round(mf_post_tax))
            nps_data.append(round(nps_corpus))
            
        return JsonResponse({
            'success': True,
            'summary': {
                'invested': round(invested),
                'mf_corpus': round(mf_corpus),
                'mf_tax': round(mf_tax),
                'mf_post_tax': round(mf_post_tax),
                'nps_corpus': round(nps_corpus),
                'nps_lumpsum': round(nps_lumpsum),
                'nps_annuity': round(nps_annuity_corpus),
                'tax_saved_80ccd': round(total_tax_saved)
            },
            'chart': {
                'labels': labels,
                'mf_data': mf_data,
                'nps_data': nps_data
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def compare_hub(request):
    return render(request, 'compare/compare_hub.html')

def page_sgb_vs_gold(request):
    return render(request, 'compare/sgb_vs_gold.html')

def page_nps_vs_mf(request):
    return render(request, 'compare/nps_vs_mf.html')

def page_sip_vs_fd(request):
    return render(request, 'compare/sip_vs_fd.html')

def page_ppf_vs_elss(request):
    return render(request, 'compare/ppf_vs_elss.html')

def page_homeloan_vs_rent(request):
    return render(request, 'compare/homeloan_vs_rent.html')


def generate_llms_content(is_full=False):
    # 1. Base Structure aur Calculators
    content = """# Vittarthi

> Vittarthi is a free platform offering practical financial calculators for SIP, EMI, and Retirement planning, alongside a Knowledge Hub of finance guides, market news, and investment case studies focused on Indian investors.

## Calculators
Free tools to estimate investments, loans, EMIs, and retirement savings.
- [SIP Calculator](https://vittarthi.com/calculators/sip): Project returns on a monthly systematic investment plan.
- [PPF Calculator](https://vittarthi.com/calculators/ppf): Estimate the maturity value of Public Provident Fund savings.
- [NPS Calculator](https://vittarthi.com/calculators/nps): Project National Pension System corpus and expected pension.
- [EMI Calculator](https://vittarthi.com/calculators/emi): Calculate monthly installments for any loan.
- [Loan Eligibility](https://vittarthi.com/calculators/loan-eligibility): Check the loan amount you qualify for based on income.
- [Salary Calculator](https://vittarthi.com/calculators/salary): Break down in-hand salary from CTC after deductions.
- [PF Calculator](https://vittarthi.com/calculators/pf): Estimate your Employee Provident Fund balance over time.
- [Retirement Calculator](https://vittarthi.com/calculators/retirement): Work out the corpus needed to retire comfortably.
- [Car Loan Calculator](https://vittarthi.com/calculators/car-loan): Compute EMIs and total interest on a car loan.
- [Home Loan Calculator](https://vittarthi.com/calculators/home-loan): Compute home loan EMIs, interest, and amortization.
- [Personal Loan Calculator](https://vittarthi.com/calculators/personal-loan): Calculate personal loan EMIs and repayment schedule.

## Knowledge Hub
Guides, market news, and case studies to improve financial understanding.
- [Knowledge Hub Home](https://vittarthi.com/resources): Central hub for all blogs, news, and case studies.
- [Blog Index](https://vittarthi.com/resources/blogs): Full archive of finance and investing guides.
- [Case Study Index](https://vittarthi.com/resources/case-study): Full archive of fund and wealth-creation case studies.

"""

    # 2. Database se Articles query karna (Descending order - newest first)
    base_qs = Blog.objects.select_related('primary_category').filter(status = 'published').order_by('-created_at')
    blogs_qs = base_qs.filter(primary_category__slug='blogs')
    news_qs = base_qs.filter(primary_category__slug='news')
    case_studies_qs = base_qs.filter(primary_category__slug='case-study')
    # Agar 'llms.txt' (short) hai, toh sirf top 100 fetch karein
    #print(blogs_qs)
    if not is_full:
        blogs_qs = blogs_qs[:100]
        news_qs = news_qs[:100]
        case_studies_qs = case_studies_qs[:100]

    # --- BLOGS ---
    content += "### Blogs\nDetailed articles and guides on financial planning and mutual funds.\n"
    for item in blogs_qs:
        url = f"https://vittarthi.com/resources/{item.primary_category.slug}/{item.slug}"
        content += f"- [{item.title}]({url})\n"
    
    # --- NEWS ---
    content += "\n### News\nLatest market updates and financial news.\n"
    for item in news_qs:
        url = f"https://vittarthi.com/resources/{item.primary_category.slug}/{item.slug}"
        content += f"- [{item.title}]({url})\n"
        
    # --- CASE STUDIES ---
    content += "\n### Case Studies\nReal-world scenarios and insights on financial tools and investments.\n"
    for item in case_studies_qs:
        url = f"https://vittarthi.com/resources/{item.primary_category.slug}/{item.slug}"
        content += f"- [{item.title}]({url})\n"

    # 3. Footer / Other Pages
    content += """
## Other Pages
- [About Us](https://vittarthi.com/about-us): Learn more about Vittarthi.
- [Contact](https://vittarthi.com/contact): Get in touch with the team.
"""
    return content

# View for llms.txt (Limited version)
def llms_txt_view(request):
    content = generate_llms_content(is_full=False)
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

# View for llms-full.txt (Unlimited version)
def llms_full_txt_view(request):
    content = generate_llms_content(is_full=True)
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

def indianstock(request):
    return render(request, 'market/indianstock.html')

def usstock(request):
    return render(request, 'market/usstock.html')

def commodities(request):
    return render(request, 'market/commodities.html')

def crypto(request):
    return render(request, 'market/crypto.html')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ── Global Yahoo Session (reused across requests) ──
_YF_SESSION = None
_YF_CRUMB   = None
_NSE_SESSION = None
def _init_yahoo_session():
    """Visit Yahoo Finance to get cookies + crumb token."""
    global _YF_SESSION, _YF_CRUMB
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    # Step 1: Visit homepage to set cookies
    try:
        s.get("https://finance.yahoo.com", timeout=10, verify=False)
    except Exception as e:
        print(f"Yahoo homepage visit failed: {e}")
    # Step 2: Fetch crumb
    try:
        cr = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10, verify=False)
        _YF_CRUMB = cr.text.strip()
    except Exception as e:
        print(f"Crumb fetch failed: {e}")
        _YF_CRUMB = None
    _YF_SESSION = s
    print(f"Yahoo session initialized. Crumb: {_YF_CRUMB}")
    return s
def _yahoo_fetch(symbol, period="5d"):
    """Fetch OHLCV data from Yahoo Finance chart API."""
    global _YF_SESSION, _YF_CRUMB
    if _YF_SESSION is None:
        _init_yahoo_session()

    url    = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": period}
    if _YF_CRUMB:
        params["crumb"] = _YF_CRUMB

    try:
        r = _YF_SESSION.get(url, params=params, timeout=10, verify=False)

        # If 401/404, reinitialize session and retry once
        if r.status_code in (401, 404):
            print(f"Session expired for {symbol}, reinitializing...")
            _init_yahoo_session()
            if _YF_CRUMB:
                params["crumb"] = _YF_CRUMB
            r = _YF_SESSION.get(url, params=params, timeout=10, verify=False)

        r.raise_for_status()
        data   = r.json()
        result = data["chart"]["result"]
        if not result:
            print(f"No result for {symbol}")
            return None

        meta   = result[0]["meta"]
        curr   = round(float(meta.get("regularMarketPrice") or 0), 2)

        # Extract historical closing prices
        raw_closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        clean_closes = [round(float(c), 2) for c in raw_closes if c is not None]
        
        # Proper 'Previous Close' calculation for 1-day accurate change
        if not clean_closes:
            prev = curr
        elif curr == clean_closes[-1] and len(clean_closes) > 1:
            # The array already includes today's close, so yesterday's is the 2nd to last
            prev = clean_closes[-2]
        elif curr != clean_closes[-1]:
            # The array doesn't have today's close yet, so the last element is yesterday's
            prev = clean_closes[-1]
        else:
            prev = curr

        change = round(curr - prev, 2)
        pct    = round((change / prev) * 100, 2) if prev else 0.0

        # Sparkline (last 7 points)
        spark = clean_closes[-7:]

        return {"price": curr, "change": change, "pct": pct, "spark": spark}

    except Exception as e:
        print(f"_yahoo_fetch failed for {symbol}: {e}")
        return None
def _init_nse_session():
    global _NSE_SESSION
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
    })
    try:
        s.get("https://www.nseindia.com", timeout=10, verify=False)
    except Exception as e:
        print(f"NSE homepage visit failed: {e}")
    _NSE_SESSION = s
    return s
def _fetch_fii_dii():
    """Fetch today's FII/DII net activity from NSE."""
    global _NSE_SESSION
    if _NSE_SESSION is None:
        _init_nse_session()
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    try:
        r = _NSE_SESSION.get(url, timeout=10, verify=False)
        # If blocked, reinit and retry
        if r.status_code in (401, 403):
            _init_nse_session()
            r = _NSE_SESSION.get(url, timeout=10, verify=False)
        r.raise_for_status()
        data = r.json()
        fii_net = None
        dii_net = None
        for row in data:
            cat = row.get("category", "").upper()
            try:
                net = round(float(row.get("netValue", "0").replace(",", "")), 2)
            except (ValueError, AttributeError):
                net = None
            if "FII" in cat or "FPI" in cat:
                fii_net = net
            elif "DII" in cat:
                dii_net = net
        return [
            {"label": "FII (net)", "value": fii_net},
            {"label": "DII (net)", "value": dii_net},
        ]
    except Exception as e:
        print(f"FII/DII fetch failed: {e}")
        return [
            {"label": "FII (net)", "value": None},
            {"label": "DII (net)", "value": None},
        ]

@cache_page(300)
def market_live_data(request):
    try:
        INDEX_SYMBOLS = {
            "NIFTY 50":         ("^NSEI",     "NSE"),
            "SENSEX":           ("^BSESN",    "BSE"),
            "NIFTY BANK":       ("^NSEBANK",  "NSE"),
            "NIFTY MIDCAP 100": ("^NSMIDCP",  "NSE"),
            "NIFTY IT":         ("^CNXIT",    "NSE"),
            "INDIA VIX":        ("^INDIAVIX", "Volatility"),
        }
        NIFTY50_STOCKS = [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
            "LT.NS","HCLTECH.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "SUNPHARMA.NS","BAJFINANCE.NS","TITAN.NS","WIPRO.NS","POWERGRID.NS",
            "NTPC.NS","TATAMOTORS.NS","ULTRACEMCO.NS","ONGC.NS","COALINDIA.NS",
            "JSWSTEEL.NS","TATASTEEL.NS","HINDALCO.NS","CIPLA.NS","DRREDDY.NS",
        ]
        SECTOR_SYMBOLS = {
            "IT":     "^CNXIT",     "Pharma": "^CNXPHARMA",
            "Auto":   "^CNXAUTO",   "FMCG":   "^CNXFMCG",
            "Bank":   "^NSEBANK",   "Realty": "^CNXREALTY",
            "Energy": "^CNXENERGY", "Metal":  "^CNXMETAL",
        }
        GLOBAL_SYMBOLS = {
            "Dow Jones":  "^DJI",  "Nasdaq":     "^IXIC",
            "S&P 500":    "^GSPC", "Nikkei 225": "^N225",
            "FTSE 100":   "^FTSE",
        }
        # ── Indices ──
        indices = []
        for name, (sym, sub) in INDEX_SYMBOLS.items():
            d = _yahoo_fetch(sym)
            if not d:
                continue
            indices.append({
                "name": name, "sub": sub,
                "value": d["price"], "change": d["change"],
                "pct": d["pct"], "spark": d["spark"],
            })
        # ── Gainers / Losers ──
        stock_moves = []
        for sym in NIFTY50_STOCKS:
            d = _yahoo_fetch(sym)
            if not d:
                continue
            name = sym.replace(".NS", "")
            stock_moves.append({"t": name, "s": name, "px": d["price"], "pct": d["pct"]})
        stock_moves.sort(key=lambda x: x["pct"], reverse=True)
        gainers = stock_moves[:5]
        losers  = list(reversed(stock_moves))[:5]
        # ── Sectors ──
        sectors = []
        for name, sym in SECTOR_SYMBOLS.items():
            d = _yahoo_fetch(sym)
            sectors.append({"name": name, "pct": d["pct"] if d else 0.0})
        # ── Global ──
        global_indices = []
        for name, sym in GLOBAL_SYMBOLS.items():
            d = _yahoo_fetch(sym)
            if d:
                global_indices.append({"name": name, "value": d["price"], "pct": d["pct"]})
        # ── Breadth ──
        advancing = len([s for s in stock_moves if s["pct"] > 0])
        declining = len([s for s in stock_moves if s["pct"] <= 0])
        breadth   = {"advances": int(advancing * 150), "declines": int(declining * 150)}
        # ── Auto Summary ──
        nifty        = next((i for i in indices if "NIFTY 50" in i["name"]), None)
        sensex       = next((i for i in indices if "SENSEX"   in i["name"]), None)
        best_sector  = max(sectors, key=lambda s: s["pct"], default=None)
        worst_sector = min(sectors, key=lambda s: s["pct"], default=None)
        summary = []
        if nifty:
            d = "gained" if nifty["pct"] >= 0 else "fell"
            summary.append(f"Nifty 50 {d} {abs(nifty['pct']):.2f}% to {nifty['value']:,.2f}")
        if sensex:
            d = "rose" if sensex["pct"] >= 0 else "slipped"
            summary.append(f"Sensex {d} {abs(sensex['pct']):.2f}% to {sensex['value']:,.2f}")
        if best_sector and best_sector["pct"] > 0:
            summary.append(f"{best_sector['name']} led the session (+{best_sector['pct']:.2f}%)")
        if worst_sector and worst_sector["pct"] < 0:
            summary.append(f"{worst_sector['name']} was under pressure ({worst_sector['pct']:.2f}%)")
        if gainers:
            summary.append(f"Top gainer: {gainers[0]['t']} (+{gainers[0]['pct']:.2f}%)")
        if losers:
            summary.append(f"Top loser: {losers[0]['t']} ({losers[0]['pct']:.2f}%)")
        if breadth["advances"] > breadth["declines"]:
            summary.append(f"Broad market positive — {breadth['advances']:,} stocks advanced")
        else:
            summary.append(f"Broad market weak — {breadth['declines']:,} stocks declined")
        CalcUsage.objects.create(name="MARKET_VIEW")
        return JsonResponse({
            "success": True,
            "asOf": 	datetime.now(tz=ZoneInfo("Asia/Kolkata")).isoformat(),
            "indices": indices,  "gainers": gainers,
            "losers":  losers,   "sectors": sectors,
            "breadth": breadth,
            "flows": _fetch_fii_dii(),
            "global":  global_indices,
            "summary": summary,
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@cache_page(300)
def us_market_live_data(request):
    """US Market live data — reuses _yahoo_fetch from Indian stocks."""
    try:
        # ── US Indices ──
        INDEX_SYMBOLS = {
            "S&P 500":       ("^GSPC",     "SPX"),
            "DOW JONES":     ("^DJI",      "DJIA"),
            "NASDAQ COMP":   ("^IXIC",     "IXIC"),
            "NASDAQ 100":    ("^NDX",      "NDX"),
            "RUSSELL 2000":  ("^RUT",      "RUT"),
            "CBOE VIX":      ("^VIX",      "Volatility"),
        }

        # ── Major US Stocks (S&P 500 heavyweights) ──
        US_STOCKS = {
            "AAPL":  "Apple",        "MSFT":  "Microsoft",
            "GOOGL": "Alphabet",     "AMZN":  "Amazon",
            "NVDA":  "NVIDIA",       "META":  "Meta",
            "TSLA":  "Tesla",        "BRK-B": "Berkshire",
            "LLY":   "Eli Lilly",    "UNH":   "UnitedHealth",
            "JPM":   "JPMorgan",     "V":     "Visa",
            "AVGO":  "Broadcom",     "MA":    "Mastercard",
            "JNJ":   "Johnson&J",    "PG":    "Procter&Gamble",
            "HD":    "Home Depot",   "MRK":   "Merck",
            "COST":  "Costco",       "ABBV":  "AbbVie",
            "CRM":   "Salesforce",   "WMT":   "Walmart",
            "BAC":   "Bank of America","KO":  "Coca-Cola",
            "NFLX":  "Netflix",      "MU":    "Micron",
            "CAT":   "Caterpillar",  "GS":    "Goldman Sachs",
            "CSCO":  "Cisco",        "IBM":   "IBM",
        }

        # ── Sector ETFs (GICS sectors via SPDR ETFs) ──
        SECTOR_ETFS = {
            "Technology":    "XLK",   "Health Care":   "XLV",
            "Financials":    "XLF",   "Industrials":   "XLI",
            "Staples":       "XLP",   "Real Estate":   "XLRE",
            "Utilities":     "XLU",   "Materials":     "XLB",
            "Energy":        "XLE",   "Discretionary": "XLY",
            "Comm Svcs":     "XLC",
        }

        # ── Macro (Treasury, Dollar, Oil, Gold) ──
        MACRO_SYMBOLS = {
            "US 10-Yr Treasury": {"sym": "^TNX",     "kind": "yield", "suffix": ""},
            "US Dollar Index":   {"sym": "DX-Y.NYB", "kind": "index", "suffix": ""},
            "WTI Crude Oil":     {"sym": "CL=F",     "kind": "usd",   "suffix": "/bbl"},
            "Gold (Spot)":       {"sym": "GC=F",     "kind": "usd",   "suffix": "/oz"},
        }

        # ── Global Indices (non-US) ──
        GLOBAL_SYMBOLS = {
            "Nifty 50 (India)": "^NSEI",
            "FTSE 100":         "^FTSE",
            "DAX":              "^GDAXI",
            "Nikkei 225":       "^N225",
            "Hang Seng":        "^HSI",
        }

        # ── Fetch Indices ──
        indices = []
        for name, (sym, sub) in INDEX_SYMBOLS.items():
            d = _yahoo_fetch(sym)
            if not d:
                continue
            indices.append({
                "name": name, "sub": sub,
                "value": d["price"], "change": d["change"],
                "pct": d["pct"], "spark": d["spark"],
            })

        # ── Fetch Stocks → Gainers/Losers ──
        stock_moves = []
        for sym, full_name in US_STOCKS.items():
            d = _yahoo_fetch(sym)
            if not d:
                continue
            stock_moves.append({"t": full_name, "s": sym, "px": d["price"], "pct": d["pct"]})

        stock_moves.sort(key=lambda x: x["pct"], reverse=True)
        gainers = stock_moves[:5]
        losers  = list(reversed(stock_moves))[:5]

        # ── Fetch Sectors ──
        sectors = []
        for name, sym in SECTOR_ETFS.items():
            d = _yahoo_fetch(sym)
            sectors.append({"name": name, "pct": d["pct"] if d else 0.0})
        sectors.sort(key=lambda x: x["pct"], reverse=True)

        # ── Fetch Macro ──
        macro = []
        for name, info in MACRO_SYMBOLS.items():
            d = _yahoo_fetch(info["sym"])
            if d:
                macro.append({
                    "name":   name,
                    "value":  d["price"],
                    "kind":   info["kind"],
                    "suffix": info["suffix"],
                    "chg":    d["pct"],
                })

        # ── Fetch Global ──
        global_indices = []
        for name, sym in GLOBAL_SYMBOLS.items():
            d = _yahoo_fetch(sym)
            if d:
                global_indices.append({"name": name, "value": d["price"], "pct": d["pct"]})

        # ── Market Breadth (estimated) ──
        advancing = len([s for s in stock_moves if s["pct"] > 0])
        declining = len([s for s in stock_moves if s["pct"] <= 0])
        breadth = {
            "advances": int(advancing * 110),
            "declines": int(declining * 110),
        }

        CalcUsage.objects.create(name="US_MARKET_VIEW")

        return JsonResponse({
            "success": True,
            "asOf":    datetime.now(tz=ZoneInfo("America/New_York")).isoformat(),
            "indices": indices,
            "gainers": gainers,
            "losers":  losers,
            "sectors": sectors,
            "breadth": breadth,
            "macro":   macro,
            "global":  global_indices,
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@cache_page(300)
def commodities_live_data(request):
    """Commodities live data — reuses _yahoo_fetch. All conversions server-side."""
    try:
        # ── Get USDINR first (needed for all INR conversions) ──
        usdinr_data = _yahoo_fetch("USDINR=X")
        usdinr = usdinr_data["price"] if usdinr_data else 94.38

        # ═══════════ METALS ═══════════
        gold_spot  = _yahoo_fetch("GC=F")
        silver_spot = _yahoo_fetch("SI=F")

        # India premium: ~15% import duty + 3% GST ≈ 18.45%
        INDIA_PREMIUM = 1.13
        # 1 troy oz = 31.1035 grams

        metals = []

        if gold_spot:
            # Gold USD/oz → INR/10g
            g_inr = round(gold_spot["price"] * usdinr / 31.1035 * 10 * INDIA_PREMIUM)
            g_pct = gold_spot["pct"]
            g_prev = g_inr / (1 + g_pct / 100) if g_pct != 0 else g_inr
            g_chg = round(g_inr - g_prev)
            g_spark = [round(p * usdinr / 31.1035 * 10 * INDIA_PREMIUM) for p in gold_spot["spark"]] if gold_spot["spark"] else []

            metals.append({"name": "Gold 24K", "sub": "per 10g · India", "cur": "INR", "val": g_inr, "unit": "", "dec": 0, "chg": g_chg, "pct": g_pct, "spark": g_spark})

            g22 = round(g_inr * 22 / 24)
            g22_chg = round(g_chg * 22 / 24)
            metals.append({"name": "Gold 22K", "sub": "per 10g · India", "cur": "INR", "val": g22, "unit": "", "dec": 0, "chg": g22_chg, "pct": g_pct, "spark": []})

            g18 = round(g_inr * 18 / 24 * 0.97)
            g18_chg = round(g_chg * 18 / 24)
            metals.append({"name": "Gold 18K", "sub": "per 10g · India", "cur": "INR", "val": g18, "unit": "", "dec": 0, "chg": g18_chg, "pct": g_pct, "spark": []})

        if silver_spot:
            # Silver USD/oz → INR/kg
            s_inr = round(silver_spot["price"] * usdinr / 31.1035 * 1000 * INDIA_PREMIUM)
            s_pct = silver_spot["pct"]
            s_prev = s_inr / (1 + s_pct / 100) if s_pct != 0 else s_inr
            s_chg = round(s_inr - s_prev)
            s_spark = [round(p * usdinr / 31.1035 * 1000 * INDIA_PREMIUM) for p in silver_spot["spark"]] if silver_spot["spark"] else []

            metals.append({"name": "Silver", "sub": "per kg · India", "cur": "INR", "val": s_inr, "unit": "", "dec": 0, "chg": s_chg, "pct": s_pct, "spark": s_spark})

        # International spot
        if gold_spot:
            metals.append({"name": "Gold Spot", "sub": "per oz · COMEX", "cur": "USD", "val": gold_spot["price"], "unit": "", "dec": 2, "chg": gold_spot["change"], "pct": gold_spot["pct"], "spark": gold_spot["spark"]})
        if silver_spot:
            metals.append({"name": "Silver Spot", "sub": "per oz · COMEX", "cur": "USD", "val": silver_spot["price"], "unit": "", "dec": 2, "chg": silver_spot["change"], "pct": silver_spot["pct"], "spark": silver_spot["spark"]})

        # ═══════════ ENERGY ═══════════
        energy = []
        energy_list = [
            ("Brent Crude", "BZ=F",  "per barrel"),
            ("WTI Crude",   "CL=F",  "per barrel"),
            ("Natural Gas", "NG=F",  "per MMBtu"),
        ]
        for name, sym, sub in energy_list:
            d = _yahoo_fetch(sym)
            if d:
                energy.append({"name": name, "sub": sub, "cur": "USD", "val": d["price"], "unit": "", "dec": 2, "chg": d["change"], "pct": d["pct"], "spark": d["spark"]})

        # ═══════════ BASE METALS ═══════════
        baseMetals = []

        # Copper: HG=F is USD per pound → INR/kg (1 lb = 0.453592 kg)
        copper = _yahoo_fetch("HG=F")
        if copper:
            cu_inr = round(copper["price"] * usdinr / 0.453592, 2)
            cu_chg = round(copper["change"] * usdinr / 0.453592, 2)
            baseMetals.append({"name": "Copper", "sub": "₹/kg", "cur": "INR", "val": cu_inr, "dec": 2, "chg": cu_chg, "pct": copper["pct"]})

        # Aluminium, Zinc, Lead, Nickel — approximate from LME USD/tonne via Yahoo
        lme_metals = [
            ("Aluminium", "ALI=F",  2450),   # fallback LME ~$2450/tonne
            ("Zinc",      "ZNC=F",  2700),   # fallback ~$2700/tonne
            ("Lead",      "LEAD.L", 1820),   # fallback ~$1820/tonne
            ("Nickel",    "NI=F",   15200),  # fallback ~$15200/tonne
        ]
        for name, sym, fallback_usd_tonne in lme_metals:
            d = _yahoo_fetch(sym)
            if d and d["price"] > 0:
                # Yahoo LME prices are USD per tonne → INR/kg
                val_inr = round(d["price"] * usdinr / 1000, 2)
                chg_inr = round(d["change"] * usdinr / 1000, 2)
                baseMetals.append({"name": name, "sub": "₹/kg", "cur": "INR", "val": val_inr, "dec": 2, "chg": chg_inr, "pct": d["pct"]})
            else:
                # Use fallback estimate
                val_inr = round(fallback_usd_tonne * usdinr / 1000, 2)
                baseMetals.append({"name": name, "sub": "₹/kg (est.)", "cur": "INR", "val": val_inr, "dec": 2, "chg": 0, "pct": 0.0})

        # ═══════════ CURRENCY ═══════════
        currency = []

        fx_pairs = [
            ("USD / INR", "USDINR=X"),
            ("EUR / INR", "EURINR=X"),
            ("GBP / INR", "GBPINR=X"),
        ]
        for name, sym in fx_pairs:
            d = _yahoo_fetch(sym)
            if d:
                currency.append({"name": name, "cur": "INR", "val": d["price"], "dec": 2, "chg": d["change"], "pct": d["pct"]})

        # 100 JPY / INR — compute from USDJPY + USDINR
        jpyusd = _yahoo_fetch("JPY=X")  # USD per 1 JPY
        if jpyusd and jpyusd["price"] > 0:
            # JPY=X gives USD per 1 JPY, so 100 JPY = 100 * JPY=X * USDINR... No wait
            # Actually JPY=X on Yahoo gives USDJPY (how many JPY per 1 USD)
            # Let me use JPYINR=X directly
            jpyinr = _yahoo_fetch("JPYINR=X")
            if jpyinr:
                val100 = round(jpyinr["price"] * 100, 2)
                chg100 = round(jpyinr["change"] * 100, 2)
                currency.append({"name": "100 JPY / INR", "cur": "INR", "val": val100, "dec": 2, "chg": chg100, "pct": jpyinr["pct"]})
            else:
                # Fallback: compute from USDJPY
                usdjpy = _yahoo_fetch("USDJPY=X")
                if usdjpy and usdjpy["price"] > 0:
                    val100 = round(100 * usdinr / usdjpy["price"], 2)
                    currency.append({"name": "100 JPY / INR", "cur": "INR", "val": val100, "dec": 2, "chg": 0, "pct": 0.0})

        # AED / INR
        aed = _yahoo_fetch("AEDINR=X")
        if aed:
            currency.append({"name": "AED / INR", "cur": "INR", "val": aed["price"], "dec": 2, "chg": aed["change"], "pct": aed["pct"]})
        else:
            # AED is pegged to USD: 1 USD = 3.6725 AED → 1 AED = USDINR / 3.6725
            aed_val = round(usdinr / 3.6725, 2)
            currency.append({"name": "AED / INR", "cur": "INR", "val": aed_val, "dec": 2, "chg": 0, "pct": 0.0})

        # Dollar Index
        dxy = _yahoo_fetch("DX-Y.NYB")
        if dxy:
            currency.append({"name": "Dollar Index", "sub": "DXY", "cur": "", "val": dxy["price"], "dec": 2, "chg": dxy["change"], "pct": dxy["pct"]})

        # ═══════════ FUEL (Govt-set, update manually) ═══════════
        fuel = [
            {"name": "Petrol",  "sub": "₹/litre",       "cur": "INR", "val": 111.21, "dec": 2},
            {"name": "Diesel",  "sub": "₹/litre",       "cur": "INR", "val": 97.83,  "dec": 2},
            {"name": "LPG",     "sub": "₹/14.2kg cyl",  "cur": "INR", "val": 941.50, "dec": 2},
            {"name": "CNG",     "sub": "₹/kg",          "cur": "INR", "val": 76.50,  "dec": 2},
        ]

        CalcUsage.objects.create(name="COMMODITIES_VIEW")

        return JsonResponse({
            "success": True,
            "asOf": datetime.now(tz=ZoneInfo("Asia/Kolkata")).isoformat(),
            "metals": metals,
            "energy": energy,
            "baseMetals": baseMetals,
            "currency": currency,
            "fuel": fuel,
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@cache_page(300)
def crypto_live_data(request):
    """Crypto live data — CoinGecko (free) + USDINR from Yahoo."""
    try:
        # ── USDINR for conversion ──
        usdinr_data = _yahoo_fetch("USDINR=X")
        usdinr = usdinr_data["price"] if usdinr_data else 94.38

        # ── CoinGecko — one call, all data ──
        COIN_IDS = "bitcoin,ethereum,tether,binancecoin,ripple,solana,dogecoin,cardano"
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency":              "usd",
            "ids":                      COIN_IDS,
            "order":                    "market_cap_desc",
            "sparkline":                "false",
            "price_change_percentage":  "24h",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept":     "application/json",
        }

        r = requests.get(url, params=params, headers=headers, verify=False, timeout=15)
        r.raise_for_status()
        data = r.json()

        SYMBOL_MAP = {
            "bitcoin": "BTC",  "ethereum": "ETH",  "tether":      "USDT",
            "binancecoin": "BNB", "ripple": "XRP", "solana":      "SOL",
            "dogecoin": "DOGE", "cardano": "ADA",
        }

        coins = []
        for coin in data:
            sym       = SYMBOL_MAP.get(coin["id"], coin.get("symbol", "?").upper())
            usd_price = float(coin.get("current_price", 0) or 0)
            pct       = round(float(coin.get("price_change_percentage_24h", 0) or 0), 2)
            mcap      = int(coin.get("market_cap", 0) or 0)
            inr_price = usd_price * usdinr

            # Smart decimal places
            if usd_price >= 1:
                usd_round = round(usd_price, 2)
            elif usd_price >= 0.01:
                usd_round = round(usd_price, 4)
            else:
                usd_round = round(usd_price, 6)

            if inr_price >= 100:
                inr_round = round(inr_price, 0)
            else:
                inr_round = round(inr_price, 2)

            coins.append({
                "name": coin.get("name", sym),
                "sub":  sym,
                "usd":  usd_round,
                "inr":  inr_round,
                "pct":  pct,
                "mcap": mcap,
            })

        CalcUsage.objects.create(name="CRYPTO_VIEW")

        return JsonResponse({
            "success": True,
            "asOf":    datetime.now(tz=ZoneInfo("Asia/Kolkata")).isoformat(),
            "coins":   coins,
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"success": False, "error": str(e)}, status=500)