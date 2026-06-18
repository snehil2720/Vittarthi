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
    emi = None
    total_payment = None
    total_interest = None

    labels = []
    balance_data = []
    interest_data = []

    table_data = []

    if request.method == "POST":
        P = float(request.POST.get("amount"))
        annual_rate = float(request.POST.get("rate"))
        years = float(request.POST.get("time"))

        r = annual_rate / 100 / 12
        n = int(years) * 12

        emi = P * r * ((1 + r)**n) / ((1 + r)**n - 1)
        emi = round(emi, 2)

        balance = P
        total_interest = 0

        for i in range(1, n + 1):
            interest = balance * r
            principal = emi - interest
            balance -= principal

            total_interest += interest

            # yearly graph
            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                balance_data.append(round(balance, 2))
                interest_data.append(round(total_interest, 2))

            table_data.append({
                "month": i,
                "emi": round(emi, 2),
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "balance": round(balance, 2)
            })

        total_payment = round(emi * n, 2)
        total_interest = round(total_interest, 2)
    CalcUsage.objects.create(name="EMI")
    return render(request, 'emi.html', {
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "labels": labels,
        "balance_data": balance_data,
        "interest_data": interest_data,
        "table_data": table_data
    })
def home_loan(request):
    emi = None
    total_payment = None
    total_interest = None
    labels, balance_data, interest_data, table_data = [], [], [], []

    if request.method == "POST":
        P = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate"))
        years = float(request.POST.get("time"))

        r = rate / 100 / 12
        n = int(years) * 12

        emi = P * r * ((1+r)**n) / ((1+r)**n - 1)
        balance = P
        total_interest = 0

        for i in range(1, n+1):
            interest = balance * r
            principal = emi - interest
            balance -= principal
            total_interest += interest

            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                balance_data.append(round(balance,2))
                interest_data.append(round(total_interest,2))

            table_data.append({
                "month": i,
                "emi": round(emi,2),
                "principal": round(principal,2),
                "interest": round(interest,2),
                "balance": round(balance,2)
            })

        total_payment = round(emi*n,2)
    CalcUsage.objects.create(name="HOME_LOAN")
    return render(request, 'loan/home_loan.html', locals())



def car_loan(request):
    emi = None
    total_payment = None
    total_interest = None
    labels, balance_data, interest_data, table_data = [], [], [], []

    if request.method == "POST":
        P = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate", 9.2))
        years = int(request.POST.get("time"))

        r = rate / 100 / 12
        n = years * 12

        emi = P * r * ((1+r)**n) / ((1+r)**n - 1)
        balance = P
        total_interest = 0

        for i in range(1, n+1):
            interest = balance * r
            principal = emi - interest
            balance -= principal
            total_interest += interest

            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                balance_data.append(round(balance,2))
                interest_data.append(round(total_interest,2))

            table_data.append({
                "month": i,
                "emi": round(emi,2),
                "principal": round(principal,2),
                "interest": round(interest,2),
                "balance": round(balance,2)
            })

        total_payment = round(emi*n,2)
    CalcUsage.objects.create(name="CAR_LOAN")
    return render(request, 'loan/car_loan.html', locals())

def personal_loan(request):
    emi = None
    total_payment = None
    total_interest = None
    labels, balance_data, interest_data, table_data = [], [], [], []

    if request.method == "POST":
        P = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate", 11))
        years = int(request.POST.get("time"))

        r = rate / 100 / 12
        n = years * 12

        emi = P * r * ((1+r)**n) / ((1+r)**n - 1)
        balance = P
        total_interest = 0

        for i in range(1, n+1):
            interest = balance * r
            principal = emi - interest
            balance -= principal
            total_interest += interest

            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                balance_data.append(round(balance,2))
                interest_data.append(round(total_interest,2))

            table_data.append({
                "month": i,
                "emi": round(emi,2),
                "principal": round(principal,2),
                "interest": round(interest,2),
                "balance": round(balance,2)
            })

        total_payment = round(emi*n,2)
    CalcUsage.objects.create(name="PERSONAL_LOAN")
    return render(request, 'loan/personal_loan.html', locals())

def ppf_calc(request):
    result = None
    labels, data, table_data = [], [], []

    if request.method == "POST":
        yearly = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate", 7.1))/100
        years = int(request.POST.get("time"))

        total = 0

        for i in range(1, years+1):
            total = (total + yearly) * (1+rate)

            labels.append(f"Year {i}")
            data.append(round(total,2))

            table_data.append({
                "year": i,
                "value": round(total,2)
            })

        result = round(total,2)
    CalcUsage.objects.create(name="PPF")
    return render(request, 'investment/ppf.html', locals())

def nps_calc(request):
    result = None
    labels, data, table_data = [], [], []

    if request.method == "POST":
        monthly = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate", 9))/100/12
        years = int(request.POST.get("time"))

        total = 0

        for i in range(1, years*12+1):
            total = (total + monthly)*(1+rate)

            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                data.append(round(total,2))

            table_data.append({"month": i, "value": round(total,2)})

        result = round(total,2)
    CalcUsage.objects.create(name="NPS")
    return render(request, 'investment/nps.html', locals())

def retirement_calc(request):
    result = None
    total_invested = None
    profit = None

    labels = []
    data = []
    table_data = []

    if request.method == "POST":
        monthly = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate")) / 100 / 12
        years = int(request.POST.get("time"))

        months = years * 12
        total = 0
        invested = 0

        for i in range(1, months + 1):
            invested += monthly
            total = (total + monthly) * (1 + rate)

            # yearly graph
            if i % 12 == 0:
                labels.append(f"Year {i//12}")
                data.append(round(total, 2))

            # monthly table
            table_data.append({
                "month": i,
                "invested": round(invested, 2),
                "value": round(total, 2)
            })

        result = round(total, 2)
        total_invested = round(invested, 2)
        profit = round(result - total_invested, 2)
    CalcUsage.objects.create(name="RETIREMENT")
    return render(request, 'investment/retirement.html', {
        "result": result,
        "total_invested": total_invested,
        "profit": profit,
        "labels": labels,
        "data": data,
        "table_data": table_data
    })

def salary_calc(request):
    inhand = None
    table_data = []

    if request.method == "POST":
        ctc = float(request.POST.get("ctc"))

        pf = ctc * 0.12
        tax = ctc * 0.1
        bonus = ctc * 0.05

        inhand = ctc - pf - tax + bonus

        table_data = [
            {"name": "CTC", "value": ctc},
            {"name": "PF", "value": pf},
            {"name": "Tax", "value": tax},
            {"name": "Bonus", "value": bonus},
            {"name": "In-hand", "value": inhand},
        ]
    CalcUsage.objects.create(name="SALARY")
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
    eligible = None

    if request.method == "POST":
        salary = float(request.POST.get("salary"))
        score = int(request.POST.get("score"))

        factor = 40
        if score > 750:
            factor = 60
        elif score < 600:
            factor = 20

        eligible = salary * factor
    CalcUsage.objects.create(name="LOAN_ELIGIBILITY")
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

> Vittarthi is a free platform offering practical financial calculators for SIP, EMI, and Retirement planning, alongside a comprehensive Knowledge Hub featuring the latest finance blogs, market news, and case studies.

## Calculators
These tools help users estimate investments, loans, EMIs, and retirement savings.
- [SIP Calculator](https://vittarthi.com/calculators/sip)
- [PPF Calculator](https://vittarthi.com/calculators/ppf)
- [NPS Calculator](https://vittarthi.com/calculators/nps)
- [EMI Calculator](https://vittarthi.com/calculators/emi)
- [Loan Eligibility](https://vittarthi.com/calculators/loan-eligibility)
- [Salary Calculator](https://vittarthi.com/calculators/salary)
- [PF Calculator](https://vittarthi.com/calculators/pf)
- [Retirement Calculator](https://vittarthi.com/calculators/retirement)
- [Car loan Calculator](https://vittarthi.com/calculators/car-loan)
- [Home Loan Calculator](https://vittarthi.com/calculators/home-loan)
- [Personal Loan Calculator](https://vittarthi.com/calculators/personal-loan)

## Knowledge Hub
Explore blogs, market news, and practical case studies to improve financial understanding.
- [Knowledge Hub Home](https://vittarthi.com/resources)

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
- [Contact](https://vittarthi.com/contact): Get in touch with us.
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