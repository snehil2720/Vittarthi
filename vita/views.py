from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from .models import Blog,CalcUsage,PrimaryCategory,SecondaryCategory
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.contrib.auth import login, authenticate,logout
from .models import CustomUser
from django.contrib import messages
from django.utils.text import slugify
import re
import math
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .utils import generate_ai_summary
import requests
import yfinance as yf
import certifi
from .models import CalcUsage
from django.db.models import Count

def auth_page(request):
    return render(request, "authentication/auth.html")

# SIGNUP
def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("auth")

        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            role='user'
        )

        login(request, user)

        messages.success(request, "Account created successfully 🎉")
        return redirect("auth")

    return redirect("auth")


# SIGNIN
def signin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # check user exists
        if not CustomUser.objects.filter(username=username).exists():
            messages.error(request, "User not found! Please signup first.")
            return redirect("auth")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid password")

    return redirect("auth")

def signout(request):
    logout(request)
    return redirect("home")



def home(request):
    blogs = Blog.objects.all().order_by('-id')
    market = get_market_data()
    latestblogs = Blog.objects.order_by('-created_at')[:3]
    return render(request, 'home.html', {'blogs': blogs,"market": market, "latestblogs":latestblogs})

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

    secondary_categories = SecondaryCategory.objects.filter(primary=primary)

    return render(request, 'blogs/list.html', {
        'blogs': blogs,
        'primary': primary,
        'secondary_categories': secondary_categories
    })
def get_secondary(request, primary_id):
    cats = SecondaryCategory.objects.filter(primary_id=primary_id)
    data = list(cats.values('id', 'name'))
    return JsonResponse(data, safe=False)

def blog_detail(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    text = re.sub('<[^<]+?>', '', blog.content)
    words = len(text.split())
    read_time = math.ceil(words / 200)
    #return render(request, 'blogs/detail.html', {'blog': blog})
    return render(request, 'blogs/detail.html', {
        'blog': blog,
        'read_time': read_time
    })

def delete_blog(request, slug):
    blog = Blog.objects.get(slug=slug)
    blog.delete()
    return redirect('/blogs/')
def generate_unique_slug(title, slug_input):
    base_slug = slugify(slug_input) if slug_input else slugify(title)
    slug = base_slug
    counter = 1

    while Blog.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
@login_required
def write_blog(request):
    if not is_writer(request.user):
        return redirect('blogs')

    primary_categories = PrimaryCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        slug_input = request.POST.get("slug")
        content = request.POST.get('content')

        primary_id = request.POST.get('primary_category')
        secondary_id = request.POST.get('secondary_category') or None

        slug = generate_unique_slug(title, slug_input)
        summary = generate_ai_summary(content)

        Blog.objects.create(
            title=title,
            content=content,
            image=request.FILES.get('image'),
            author=request.user,
            status=request.POST.get('status'),

            primary_category_id=primary_id,
            secondary_category_id=secondary_id,  # 🔥 optional

            slug=slug,
            summary=summary
        )

        return redirect('resource_list', primary_slug='blogs')

    return render(request, 'blogs/write.html', {
        'primary_categories': primary_categories
    })

@login_required
def my_blogs(request):
    blogs = Blog.objects.filter(author=request.user)
    return render(request, 'blogs/my_blogs.html', {'blogs': blogs})

@login_required
def edit_blog(request, id):
    blog = get_object_or_404(Blog, id=id)

    if blog.author != request.user:
        return redirect('blogs')

    primary_categories = PrimaryCategory.objects.all()
    secondary_categories = SecondaryCategory.objects.filter(
        primary=blog.primary_category
    ) if blog.primary_category else SecondaryCategory.objects.none()

    if request.method == 'POST':
        new_content = request.POST.get("content")

        if blog.content != new_content:
            blog.summary = generate_ai_summary(new_content)

        blog.title = request.POST.get('title')
        blog.content = new_content
        blog.status = request.POST.get('status')

        # 🔥 NEW CATEGORY UPDATE
        blog.primary_category_id = request.POST.get('primary_category')
        blog.secondary_category_id = request.POST.get('secondary_category')

        if request.FILES.get('image'):
            blog.image = request.FILES.get('image')

        blog.save()
        return redirect('my_blogs')

    return render(request, 'blogs/edit.html', {
        'blog': blog,
        'primary_categories': primary_categories,
        'secondary_categories': secondary_categories
    })

def sip_calculator(request):
    result = None
    chart_labels = []
    invested_data = []
    value_data = []
    table_data = []
    profit = ''
    invested_total = ''
    profit_percent = ''
    if request.method == "POST":
        amount = float(request.POST.get("amount"))
        rate = float(request.POST.get("rate")) / 100 / 12
        years = float(request.POST.get("time"))
        months = int(years) * 12

        total = 0
        invested = 0

        for i in range(1, months + 1):
            invested += amount
            total = (total + amount) * (1 + rate)

            # yearly data for graph
            if i % 12 == 0:
                year = i // 12
                chart_labels.append(f"Year {year}")
                invested_data.append(round(invested, 2))
                value_data.append(round(total, 2))

            # monthly table data
            table_data.append({
                "month": i,
                "invested": round(invested, 2),
                "value": round(total, 2)
            })

        result = round(total, 2)
        profit = round(total - invested, 2)
        invested_total = round(invested, 2)
        profit_percent = round((profit / invested_total) * 100, 2) if invested_total > 0 else 0
    CalcUsage.objects.create(name="SIP")
    return render(request, 'investment/sip.html', {
        "result": result,
        "profit": profit,
        "labels": chart_labels,
        "invested_data": invested_data,
        "value_data": value_data,
        "table_data": table_data,
        "invested_total":invested_total,
        "profit_percent": profit_percent
    })

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

def pf_calc(request):
    result = None
    table_data = []

    if request.method == "POST":
        salary = float(request.POST.get("salary"))

        pf = salary * 0.12

        for i in range(1,13):
            table_data.append({"month": i, "pf": pf*i})

        result = pf*12
    CalcUsage.objects.create(name="PF")
    return render(request, 'salary/pf.html', locals())

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