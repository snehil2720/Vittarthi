import requests,re,traceback
import json
import feedparser
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from vita.models import MarketSummary  
from vita.views import _fetch_fii_dii
# ─── 1. News Fetcher (New Addition) ──────────────────────────────────────────

def _fetch_news(market):
    """
    Fetch latest verified Google News for the given market.

    Returns clean text that can be passed directly to Gemini.
    """
    IGNORE_KEYWORDS = [
        "live",
        "live updates",
        "watch live",
        "share price",
        "stock price",
        "today live",
        "photos",
        "video",
        "opinion",
        "explained",
        "horoscope",
    ]

    queries = {
        "india": '"Indian Stock Market" OR Nifty OR Sensex',
        "us": '"US Stock Market" OR "S&P 500" OR Nasdaq OR "Dow Jones"',
        "crypto": 'Bitcoin OR Ethereum OR Cryptocurrency',
        "commodities": '"Gold Price" OR "Crude Oil" OR Commodities'
    }

    query = queries.get(market, "Financial Markets")

    if market in ("india", "commodities"):
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={query}+when:1d"
            "&hl=en-IN&gl=IN&ceid=IN:en"
        )
    else:
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={query}+when:1d"
            "&hl=en-US&gl=US&ceid=US:en"
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(
            rss_url,
            headers=headers,
            timeout=10,
            verify=False
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if not feed.entries:
            return "No major verified market news was available today."
        seen = set()
        news_items = []
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            # Remove source name from title
            title = re.sub(r"\s*[-|]\s*[^-|]+$", "", title)
            title = re.sub(r"\s+", " ", title).strip()
            if len(title) < 20:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            title_lower = title.lower()
            if any(word in title_lower for word in IGNORE_KEYWORDS):
                continue
            source = ""
            if hasattr(entry, "source"):
                source = entry.source.get("title", "")
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            link = entry.get("link", "")
            block = f"""Headline: {title}
Source: {source}
Published: {published}
Link: {link}
"""
            news_items.append(block)
            if len(news_items) >= 6:
                break
        if not news_items:
            return "No major verified market news was available today."
        return "\n------------------------------\n".join(news_items)
    except Exception as e:
        traceback.print_exc()
        return f"ERROR: {str(e)}"
        #return "No verified market news could be retrieved today."

# ─── Yahoo Finance fetcher (same jo tumhare views.py mein hai) ────────────────
def _yahoo_fetch(symbol, interval="1d", range_="5d"):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval={interval}&range={range_}&includePrePost=false"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        return r.json().get("chart", {}).get("result", [None])[0]
    except Exception:
        return None

def _get_price_change(symbol):
    data = _yahoo_fetch(symbol, interval="1d", range_="5d")
    if not data:
        return None, None, None
    
    meta = data.get("meta", {})
    price = meta.get("regularMarketPrice")
    
    closes = data.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    closes = [c for c in closes if c is not None]
    
    if len(closes) >= 2:
        prev_close = closes[-2]
        change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
    else:
        change_pct = 0
    
    return price, round(change_pct, 2), meta.get("shortName", symbol)

def _get_top_movers(symbols_dict, top_n=3):
    results = []
    for name, symbol in symbols_dict.items():
        price, change, _ = _get_price_change(symbol)
        if price is not None:
            results.append({"name": name, "symbol": symbol, "price": price, "change": change})
    
    results.sort(key=lambda x: x["change"], reverse=True)
    gainers = results[:top_n]
    losers  = sorted(results, key=lambda x: x["change"])[:top_n]
    return gainers, losers

# ─── Market-specific data collectors ─────────────────────────────────────────
def collect_india_data():
    indices = {
        "NIFTY 50":   ("^NSEI",    None),
        "SENSEX":     ("^BSESN",   None),
        "NIFTY BANK": ("^NSEBANK", None),
        "INDIA VIX":  ("^INDIAVIX", None),  # <-- VIX Added (Fear Gauge)
    }
    idx_data = {}
    for name, (sym, _) in indices.items():
        price, chg, _ = _get_price_change(sym)
        idx_data[name] = {"price": price, "change": chg}

    stocks = {
        "Reliance": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC Bank": "HDFCBANK.NS",
        "Infosys": "INFY.NS", "ICICI Bank": "ICICIBANK.NS", "ITC": "ITC.NS",
        "SBI": "SBIN.NS", "Bharti Airtel": "BHARTIARTL.NS", "HUL": "HINDUNILVR.NS",
        "L&T": "LT.NS", "Wipro": "WIPRO.NS", "Axis Bank": "AXISBANK.NS",
    }
    gainers, losers = _get_top_movers(stocks)
    
    # FII/DII Data Fetch
    fii_dii_raw = _fetch_fii_dii()
    fii_dii_text = "\n".join([f"{item['label']}: ₹{item['value']} Cr" if item['value'] is not None else f"{item['label']}: Not published yet" for item in fii_dii_raw])
    
    return idx_data, gainers, losers, fii_dii_text

def collect_us_data():
    indices = {
        "S&P 500":  "^GSPC",
        "Dow Jones": "^DJI",
        "Nasdaq":   "^IXIC",
        "US VIX (Fear Gauge)": "^VIX",         # New Additions for Prediction
        "10-Yr Bond Yield": "^TNX",
        "US Dollar Index": "DX-Y.NYB",
    }
    idx_data = {}
    for name, sym in indices.items():
        price, chg, _ = _get_price_change(sym)
        idx_data[name] = {"price": price, "change": chg}

    stocks = {
        "Apple": "AAPL", "Microsoft": "MSFT", "Amazon": "AMZN",
        "Nvidia": "NVDA", "Alphabet": "GOOGL", "Meta": "META",
        "Tesla": "TSLA", "Berkshire": "BRK-B", "JPMorgan": "JPM",
    }
    gainers, losers = _get_top_movers(stocks)
    
    # Returning 4 values to match India function signature
    return idx_data, gainers, losers, None

def collect_crypto_data():
    key_coins = {
        "Bitcoin (BTC)": "BTC-USD", 
        "Ethereum (ETH)": "ETH-USD",
    }
    idx_data = {}
    for name, sym in key_coins.items():
        price, chg, _ = _get_price_change(sym)
        idx_data[name] = {"price": price, "change": chg}

    altcoins = {
        "Solana": "SOL-USD", "BNB": "BNB-USD", "XRP": "XRP-USD", 
        "Cardano": "ADA-USD", "Dogecoin": "DOGE-USD", "Avalanche": "AVAX-USD",
        "Chainlink": "LINK-USD"
    }
    gainers, losers = _get_top_movers(altcoins)

    # Macro Indicators for Crypto (Liquidity & Tech Correlation)
    macros = {
        "Nasdaq Index (Tech Correlation)": "^IXIC",
        "US Dollar Index": "DX-Y.NYB",
    }
    macro_data = {}
    for name, sym in macros.items():
        price, chg, _ = _get_price_change(sym)
        macro_data[name] = {"price": price, "change": chg}

    macro_lines = []
    for n, d in macro_data.items():
        if d['price'] is not None:
            arrow = "▲" if (d['change'] or 0) >= 0 else "▼"
            macro_lines.append(f"{n}: {d['price']:,.2f} ({arrow}{abs(d['change'] or 0):.2f}%)")
    
    extra_text = "\n".join(macro_lines) if macro_lines else "Macro data unavailable"
    
    return idx_data, gainers, losers, extra_text

def collect_commodities_data():
    commodities = {
        "Gold (Comex)":       "GC=F",
        "Silver (Comex)":     "SI=F",
        "Crude Oil (WTI)":    "CL=F",
        "Natural Gas":        "NG=F",
        "Copper":             "HG=F",
    }
    comm_data = {}
    for name, sym in commodities.items():
        price, chg, _ = _get_price_change(sym)
        comm_data[name] = {"price": price, "change": chg}

    # Macro Indicators for Commodities
    macros = {
        "US Dollar Index": "DX-Y.NYB",
        "10-Yr Bond Yield": "^TNX",
    }
    macro_data = {}
    for name, sym in macros.items():
        price, chg, _ = _get_price_change(sym)
        macro_data[name] = {"price": price, "change": chg}

    # Format macro data as text for the prompt
    macro_lines = []
    for n, d in macro_data.items():
        if d['price'] is not None:
            arrow = "▲" if (d['change'] or 0) >= 0 else "▼"
            macro_lines.append(f"{n}: {d['price']:,.2f} ({arrow}{abs(d['change'] or 0):.2f}%)")
    
    extra_text = "\n".join(macro_lines) if macro_lines else "Macro data unavailable"
    
    # Returning 4 items to keep the signature uniform across all markets
    return comm_data, [], [], extra_text

# ─── Prompt builder ──────────────────────────────────────────────────────────
def build_prompt(market, idx_data=None, gainers=None, losers=None, raw_data=None, news_data=None, extra_text=None):
    today = datetime.now().strftime("%d %B %Y")

    def fmt_mover(m):
        arrow = "▲" if m['change'] >= 0 else "▼"
        return f"{m['name']} ({arrow}{abs(m['change'])}%)"

    def fmt_idx(name, d):
        if d['price'] is None:
            return f"{name}: N/A"
        arrow = "▲" if (d['change'] or 0) >= 0 else "▼"
        return f"{name}: {d['price']:,.2f} ({arrow}{abs(d['change'] or 0):.2f}%)"

    # ==========================================
    # 1. MARKET SPECIFIC CONTEXT & INSTRUCTIONS
    # ==========================================
    if market == "india":
        idx_lines = "\n".join([fmt_idx(n, d) for n, d in idx_data.items()])
        g_line = ", ".join([fmt_mover(g) for g in gainers])
        l_line = ", ".join([fmt_mover(l) for l in losers])
        
        # Context includes FII/DII which we passed as extra_text
        context = f"Date: {today}\nIndian Market Indices & VIX:\n{idx_lines}\nTop Gainers Today: {g_line}\nTop Losers Today:  {l_line}\n\nInstitutional Activity (Net Flows):\n{extra_text or 'Not available'}"
        
        market_analysis_rule = """
   - India VIX (e.g., "A rising VIX indicates fear...").
   - FII/DII flows (e.g., "Heavy FII selling suggests caution...").
   - Impact of the news headlines.
"""

    elif market == "us":
        idx_lines = "\n".join([fmt_idx(n, d) for n, d in idx_data.items()])
        g_line = ", ".join([fmt_mover(g) for g in gainers])
        l_line = ", ".join([fmt_mover(l) for l in losers])
        
        context = f"Date: {today}\nUS Market Indices & Macro Data:\n{idx_lines}\nTop Gainers Today: {g_line}\nTop Losers Today:  {l_line}"
        
        market_analysis_rule = """
   - US VIX and 10-Yr Bond Yields.
   - US Dollar Index strength/weakness.
   - Impact of the news headlines.
"""

    elif market == "crypto":
        idx_lines = "\n".join([fmt_idx(n, d) for n, d in idx_data.items()])
        g_line = ", ".join([fmt_mover(g) for g in gainers])
        l_line = ", ".join([fmt_mover(l) for l in losers])
        
        context = f"Date: {today}\nKey Crypto Prices:\n{idx_lines}\nTop Gainers (Altcoins): {g_line}\nTop Losers (Altcoins):  {l_line}\n\nGlobal Macro Data (Liquidity Indicators):\n{extra_text}"

        market_analysis_rule = """
   - Bitcoin and Ethereum price action and dominance.
   - The impact of US Dollar strength and Nasdaq (Tech correlation) on crypto liquidity.
   - Overall crypto market fear/greed sentiment.
   - Impact of the news headlines.
"""

    elif market == "commodities":
        lines = "\n".join([fmt_idx(n, d) for n, d in idx_data.items()])
        context = f"Date: {today}\nCommodity Prices:\n{lines}\n\nGlobal Macro Data:\n{extra_text}"
        
        market_analysis_rule = """
   - Gold and Crude Oil price movements.
   - The impact of US Dollar Index strength/weakness and Bond Yields on commodity prices.
   - Safe-haven demand vs industrial demand.
   - Impact of the news headlines.
"""

    # ==========================================
    # 2. COMMON PROMPT TEMPLATE
    # ==========================================
    return f"""
You are a professional financial journalist writing for a leading financial news website.

Your task is to write an accurate, natural, and engaging daily market summary using ONLY the information provided below.

==================================================
MARKET DATA
==================================================
{context}

==================================================
LATEST VERIFIED NEWS
==================================================
{news_data}

IMPORTANT RULES

1. Use ONLY the supplied market data and news.
2. Never invent reasons for market movements.
3. If the news does not clearly explain today's market movement, DO NOT repeatedly say "No major news" or "Information vacuum".
4. Focus on how indices/assets performed and overall sentiment.
5. Never guess or create explanations.
6. Do not predict exact prices or directional targets.

OUTPUT FORMAT

Return exactly TWO sections.

<h3>📊 Market Wrap-Up</h3>

Requirements:
• Start with a short paragraph (2–3 sentences) summarizing today's market.
• Then use a bullet list (<ul><li>) including Major indices/assets, Top gainers, Top losers.
• Mention only information present in MARKET DATA.

<h3>🔮 Market Pulse & Outlook</h3>

Requirements:
• You MUST start this section with exactly ONE of the following sentiment badges based on the news and macro data:
  <div class="ai-sentiment up">📈 Bullish Trend Expected</div>
  OR
  <div class="ai-sentiment down">📉 Bearish Trend Expected</div>
  OR
  <div class="ai-sentiment neutral">↔️ Sideways Movement Expected</div>

• After the badge, write a 2-3 sentence analysis. Explain WHY you chose that sentiment by referencing:
{market_analysis_rule}

• If the supplied news does NOT contain a clear catalyst, write something similar to:
"Markets remained largely range-bound during the session as investors stayed cautious. Attention is now shifting to upcoming economic data and global market developments."

• End with ONE sentence mentioning what investors may watch next.

WRITING STYLE
• Write like Moneycontrol, CNBC TV18 or Reuters.
• Use clear and simple business English. Keep sentences short.
• Avoid difficult words (like: confluence of factors, underpinned by, notable void).
• Length: 180–220 words.

Return ONLY valid HTML. Allowed tags: <h3> <p> <strong> <ul> <li> <div>
Do NOT return Markdown or code blocks.
"""

class Command(BaseCommand):
    help = 'Fetches real market data and generates AI summary via Gemini API'

    def add_arguments(self, parser):
        parser.add_argument('market', type=str,
                            help='Market type: india, us, crypto, commodities')

    def handle(self, *args, **kwargs):
        market = kwargs['market']
        if market not in ['india', 'us', 'crypto', 'commodities']:
            self.stdout.write(self.style.ERROR('Invalid market! Use: india, us, crypto, commodities'))
            return

        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR('GEMINI_API_KEY missing in settings.py!'))
            return

        # Step 1: Real data fetch karo (Numbers)
        self.stdout.write(f"📊 Fetching real-time {market} numbers from Yahoo Finance...")
        idx_data, gainers, losers, raw_data = None, None, None, None

        try:
            if market == "india":
                idx_data, gainers, losers,fii_dii  = collect_india_data()
            elif market == "us":
                idx_data, gainers, losers, extra_text = collect_us_data()
            elif market == "crypto":
                idx_data, gainers, losers, extra_text = collect_crypto_data()
            elif market == "commodities":
                idx_data, gainers, losers, extra_text = collect_commodities_data()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Data fetch failed: {e}'))
            return

        # Step 2: Real News fetch karo (Sentiment)
        self.stdout.write(f"📰 Fetching latest {market} news headlines...")
        news_data = _fetch_news(market)
        self.stdout.write(self.style.SUCCESS("✅ Real numbers and news fetched!"))
        print("getting mewssssssss data")
        print(news_data)
        # Step 3: Prompt banao real data ke saath
        prompt = build_prompt(market, idx_data, gainers, losers, raw_data, news_data)

        # Step 4: Gemini ko single request bhejo
        model_name = "gemini-3.1-flash-lite"
        api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        self.stdout.write(f"🤖 Sending data & news to Gemini for prediction...")
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"API Error ({response.status_code}): {response.text}"))
                return

            data = response.json()
            summary_html = data['candidates'][0]['content']['parts'][0]['text'].strip()

            # Clean backticks agar AI ne diye
            if summary_html.startswith("```"):
                summary_html = summary_html.split("```")[-2].replace("html", "").strip()

            today = timezone.localdate()  
            
            existing_summary = MarketSummary.objects.filter(
                market_type=market,
                date_created__date=today
            ).first()
            if existing_summary:
                # Agar aaj ki summary hai, toh usko UPDATE kar do
                existing_summary.summary_html = summary_html
                existing_summary.date_created = timezone.now()  # Time ko latest kar do
                existing_summary.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Summary updated for today ({market})!'))
            else:
                # Agar aaj ki koi summary nahi hai (din ka pehla run), toh CREATE karo
                MarketSummary.objects.create(market_type=market, summary_html=summary_html)
                self.stdout.write(self.style.SUCCESS(f'✅ New summary created for today ({market})!'))
            # Step 6: 7 din purane delete karo (Ye waisa hi rahega)
            seven_days_ago = timezone.now() - timedelta(days=7)
            deleted, _ = MarketSummary.objects.filter(
                market_type=market,
                date_created__lt=seven_days_ago
            ).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f'🗑 Deleted {deleted} old summaries.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Request Failed: {str(e)}'))