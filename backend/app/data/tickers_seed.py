"""Curated NSE ticker universe for autocomplete.

~250 NSE-listed equities covering Nifty 50, Nifty Next 50, broad Nifty 500
representation by sector, plus a few BSE-only tickers. This is good enough
for a showcase autocomplete; real-world deployment would back this with a
NSE/BSE security master refreshed nightly.

The list is curated by hand from public NSE indices. Free-text input still
works in the UI — yfinance validates the symbol when the orchestrator
runs, so users can type anything.
"""

from __future__ import annotations

from typing import TypedDict


class _Row(TypedDict):
    ticker: str
    name: str
    sector: str


_RAW: list[_Row] = [
    # ── Energy / Oil & Gas ───────────────────────────────────────────────
    {"ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
    {"ticker": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy"},
    {"ticker": "BPCL", "name": "Bharat Petroleum", "sector": "Energy"},
    {"ticker": "IOC", "name": "Indian Oil Corp", "sector": "Energy"},
    {"ticker": "GAIL", "name": "GAIL India", "sector": "Energy"},
    {"ticker": "HINDPETRO", "name": "Hindustan Petroleum", "sector": "Energy"},
    {"ticker": "PETRONET", "name": "Petronet LNG", "sector": "Energy"},
    {"ticker": "OIL", "name": "Oil India", "sector": "Energy"},
    {"ticker": "IGL", "name": "Indraprastha Gas", "sector": "Energy"},
    {"ticker": "MGL", "name": "Mahanagar Gas", "sector": "Energy"},
    {"ticker": "GUJGASLTD", "name": "Gujarat Gas", "sector": "Energy"},
    {"ticker": "ATGL", "name": "Adani Total Gas", "sector": "Energy"},

    # ── IT services & products ───────────────────────────────────────────
    {"ticker": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"ticker": "INFY", "name": "Infosys", "sector": "IT"},
    {"ticker": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
    {"ticker": "WIPRO", "name": "Wipro", "sector": "IT"},
    {"ticker": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
    {"ticker": "LTIM", "name": "LTIMindtree", "sector": "IT"},
    {"ticker": "PERSISTENT", "name": "Persistent Systems", "sector": "IT"},
    {"ticker": "COFORGE", "name": "Coforge", "sector": "IT"},
    {"ticker": "MPHASIS", "name": "Mphasis", "sector": "IT"},
    {"ticker": "OFSS", "name": "Oracle Financial Services", "sector": "IT"},
    {"ticker": "TATAELXSI", "name": "Tata Elxsi", "sector": "IT"},
    {"ticker": "KPITTECH", "name": "KPIT Technologies", "sector": "IT"},
    {"ticker": "LTTS", "name": "L&T Technology Services", "sector": "IT"},
    {"ticker": "BSOFT", "name": "Birlasoft", "sector": "IT"},
    {"ticker": "HEXT", "name": "Hexaware Technologies", "sector": "IT"},
    {"ticker": "NEWGEN", "name": "Newgen Software", "sector": "IT"},

    # ── Banks (private) ──────────────────────────────────────────────────
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "sector": "Financials"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Financials"},
    {"ticker": "AXISBANK", "name": "Axis Bank", "sector": "Financials"},
    {"ticker": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Financials"},
    {"ticker": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Financials"},
    {"ticker": "IDFCFIRSTB", "name": "IDFC First Bank", "sector": "Financials"},
    {"ticker": "FEDERALBNK", "name": "Federal Bank", "sector": "Financials"},
    {"ticker": "BANDHANBNK", "name": "Bandhan Bank", "sector": "Financials"},
    {"ticker": "RBLBANK", "name": "RBL Bank", "sector": "Financials"},
    {"ticker": "AUBANK", "name": "AU Small Finance Bank", "sector": "Financials"},
    {"ticker": "YESBANK", "name": "Yes Bank", "sector": "Financials"},
    {"ticker": "CSBBANK", "name": "CSB Bank", "sector": "Financials"},
    {"ticker": "DCBBANK", "name": "DCB Bank", "sector": "Financials"},

    # ── Banks (PSU) ──────────────────────────────────────────────────────
    {"ticker": "SBIN", "name": "State Bank of India", "sector": "Financials"},
    {"ticker": "BANKBARODA", "name": "Bank of Baroda", "sector": "Financials"},
    {"ticker": "PNB", "name": "Punjab National Bank", "sector": "Financials"},
    {"ticker": "CANBK", "name": "Canara Bank", "sector": "Financials"},
    {"ticker": "UNIONBANK", "name": "Union Bank of India", "sector": "Financials"},
    {"ticker": "INDIANB", "name": "Indian Bank", "sector": "Financials"},
    {"ticker": "IOB", "name": "Indian Overseas Bank", "sector": "Financials"},
    {"ticker": "BANKINDIA", "name": "Bank of India", "sector": "Financials"},
    {"ticker": "MAHABANK", "name": "Bank of Maharashtra", "sector": "Financials"},
    {"ticker": "CENTRALBK", "name": "Central Bank of India", "sector": "Financials"},
    {"ticker": "UCOBANK", "name": "UCO Bank", "sector": "Financials"},

    # ── NBFCs / Financial Services ──────────────────────────────────────
    {"ticker": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Financials"},
    {"ticker": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Financials"},
    {"ticker": "CHOLAFIN", "name": "Cholamandalam Investment", "sector": "Financials"},
    {"ticker": "SHRIRAMFIN", "name": "Shriram Finance", "sector": "Financials"},
    {"ticker": "SBICARD", "name": "SBI Cards & Payment Services", "sector": "Financials"},
    {"ticker": "MUTHOOTFIN", "name": "Muthoot Finance", "sector": "Financials"},
    {"ticker": "MANAPPURAM", "name": "Manappuram Finance", "sector": "Financials"},
    {"ticker": "LICHSGFIN", "name": "LIC Housing Finance", "sector": "Financials"},
    {"ticker": "PFC", "name": "Power Finance Corp", "sector": "Financials"},
    {"ticker": "RECLTD", "name": "REC Limited", "sector": "Financials"},
    {"ticker": "IRFC", "name": "Indian Railway Finance Corp", "sector": "Financials"},
    {"ticker": "HUDCO", "name": "Housing & Urban Development Corp", "sector": "Financials"},
    {"ticker": "POONAWALLA", "name": "Poonawalla Fincorp", "sector": "Financials"},
    {"ticker": "M&MFIN", "name": "Mahindra & Mahindra Financial", "sector": "Financials"},
    {"ticker": "HDFCAMC", "name": "HDFC Asset Management", "sector": "Financials"},
    {"ticker": "NAM-INDIA", "name": "Nippon Life India AMC", "sector": "Financials"},

    # ── Insurance ────────────────────────────────────────────────────────
    {"ticker": "LICI", "name": "Life Insurance Corp of India", "sector": "Financials"},
    {"ticker": "SBILIFE", "name": "SBI Life Insurance", "sector": "Financials"},
    {"ticker": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Financials"},
    {"ticker": "ICICIPRULI", "name": "ICICI Prudential Life", "sector": "Financials"},
    {"ticker": "ICICIGI", "name": "ICICI Lombard General Insurance", "sector": "Financials"},
    {"ticker": "MAXFIN", "name": "Max Financial Services", "sector": "Financials"},
    {"ticker": "STARHEALTH", "name": "Star Health & Allied Insurance", "sector": "Financials"},
    {"ticker": "NIACL", "name": "New India Assurance", "sector": "Financials"},
    {"ticker": "GICRE", "name": "General Insurance Corp", "sector": "Financials"},

    # ── FMCG ─────────────────────────────────────────────────────────────
    {"ticker": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
    {"ticker": "ITC", "name": "ITC", "sector": "FMCG"},
    {"ticker": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
    {"ticker": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
    {"ticker": "DABUR", "name": "Dabur India", "sector": "FMCG"},
    {"ticker": "MARICO", "name": "Marico", "sector": "FMCG"},
    {"ticker": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG"},
    {"ticker": "COLPAL", "name": "Colgate-Palmolive India", "sector": "FMCG"},
    {"ticker": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
    {"ticker": "VBL", "name": "Varun Beverages", "sector": "FMCG"},
    {"ticker": "EMAMILTD", "name": "Emami", "sector": "FMCG"},
    {"ticker": "PGHH", "name": "P&G Hygiene & Health Care", "sector": "FMCG"},
    {"ticker": "GILLETTE", "name": "Gillette India", "sector": "FMCG"},
    {"ticker": "JYOTHYLAB", "name": "Jyothy Labs", "sector": "FMCG"},
    {"ticker": "MCDOWELL-N", "name": "United Spirits", "sector": "FMCG"},
    {"ticker": "RADICO", "name": "Radico Khaitan", "sector": "FMCG"},
    {"ticker": "UBL", "name": "United Breweries", "sector": "FMCG"},
    {"ticker": "TATATEA", "name": "Tata Tea", "sector": "FMCG"},

    # ── Auto OEMs ────────────────────────────────────────────────────────
    {"ticker": "MARUTI", "name": "Maruti Suzuki India", "sector": "Auto"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
    {"ticker": "M&M", "name": "Mahindra & Mahindra", "sector": "Auto"},
    {"ticker": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Auto"},
    {"ticker": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto"},
    {"ticker": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Auto"},
    {"ticker": "TVSMOTOR", "name": "TVS Motor", "sector": "Auto"},
    {"ticker": "ASHOKLEY", "name": "Ashok Leyland", "sector": "Auto"},
    {"ticker": "ESCORTS", "name": "Escorts Kubota", "sector": "Auto"},
    {"ticker": "FORCEMOT", "name": "Force Motors", "sector": "Auto"},
    {"ticker": "OLAELEC", "name": "Ola Electric Mobility", "sector": "Auto"},

    # ── Auto ancillaries ─────────────────────────────────────────────────
    {"ticker": "BOSCHLTD", "name": "Bosch", "sector": "Auto"},
    {"ticker": "MOTHERSON", "name": "Samvardhana Motherson Intl", "sector": "Auto"},
    {"ticker": "BHARATFORG", "name": "Bharat Forge", "sector": "Auto"},
    {"ticker": "MRF", "name": "MRF", "sector": "Auto"},
    {"ticker": "BALKRISIND", "name": "Balkrishna Industries", "sector": "Auto"},
    {"ticker": "APOLLOTYRE", "name": "Apollo Tyres", "sector": "Auto"},
    {"ticker": "CEATLTD", "name": "CEAT", "sector": "Auto"},
    {"ticker": "TIINDIA", "name": "Tube Investments of India", "sector": "Auto"},
    {"ticker": "EXIDEIND", "name": "Exide Industries", "sector": "Auto"},
    {"ticker": "AMARARAJA", "name": "Amara Raja Energy", "sector": "Auto"},
    {"ticker": "SUNDRMFAST", "name": "Sundram Fasteners", "sector": "Auto"},
    {"ticker": "ENDURANCE", "name": "Endurance Technologies", "sector": "Auto"},
    {"ticker": "MINDA", "name": "Uno Minda", "sector": "Auto"},
    {"ticker": "SCHAEFFLER", "name": "Schaeffler India", "sector": "Auto"},

    # ── Pharma & Healthcare ──────────────────────────────────────────────
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"ticker": "DRREDDY", "name": "Dr. Reddy's Laboratories", "sector": "Pharma"},
    {"ticker": "CIPLA", "name": "Cipla", "sector": "Pharma"},
    {"ticker": "DIVISLAB", "name": "Divi's Laboratories", "sector": "Pharma"},
    {"ticker": "LUPIN", "name": "Lupin", "sector": "Pharma"},
    {"ticker": "AUROPHARMA", "name": "Aurobindo Pharma", "sector": "Pharma"},
    {"ticker": "TORNTPHARM", "name": "Torrent Pharmaceuticals", "sector": "Pharma"},
    {"ticker": "ZYDUSLIFE", "name": "Zydus Lifesciences", "sector": "Pharma"},
    {"ticker": "ALKEM", "name": "Alkem Laboratories", "sector": "Pharma"},
    {"ticker": "ABBOTINDIA", "name": "Abbott India", "sector": "Pharma"},
    {"ticker": "GLAND", "name": "Gland Pharma", "sector": "Pharma"},
    {"ticker": "BIOCON", "name": "Biocon", "sector": "Pharma"},
    {"ticker": "GLENMARK", "name": "Glenmark Pharmaceuticals", "sector": "Pharma"},
    {"ticker": "IPCALAB", "name": "Ipca Laboratories", "sector": "Pharma"},
    {"ticker": "AJANTPHARM", "name": "Ajanta Pharma", "sector": "Pharma"},
    {"ticker": "SANOFI", "name": "Sanofi India", "sector": "Pharma"},
    {"ticker": "GSPL", "name": "Gujarat State Petronet", "sector": "Pharma"},
    {"ticker": "NATCOPHARM", "name": "Natco Pharma", "sector": "Pharma"},
    {"ticker": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
    {"ticker": "FORTIS", "name": "Fortis Healthcare", "sector": "Healthcare"},
    {"ticker": "MAXHEALTH", "name": "Max Healthcare Institute", "sector": "Healthcare"},
    {"ticker": "NH", "name": "Narayana Hrudayalaya", "sector": "Healthcare"},
    {"ticker": "SYNGENE", "name": "Syngene International", "sector": "Healthcare"},

    # ── Cement & Building Materials ─────────────────────────────────────
    {"ticker": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Materials"},
    {"ticker": "GRASIM", "name": "Grasim Industries", "sector": "Materials"},
    {"ticker": "SHREECEM", "name": "Shree Cement", "sector": "Materials"},
    {"ticker": "AMBUJACEM", "name": "Ambuja Cements", "sector": "Materials"},
    {"ticker": "ACC", "name": "ACC", "sector": "Materials"},
    {"ticker": "DALBHARAT", "name": "Dalmia Bharat", "sector": "Materials"},
    {"ticker": "RAMCOCEM", "name": "Ramco Cements", "sector": "Materials"},
    {"ticker": "JKCEMENT", "name": "JK Cement", "sector": "Materials"},
    {"ticker": "BIRLACORPN", "name": "Birla Corporation", "sector": "Materials"},
    {"ticker": "PIDILITIND", "name": "Pidilite Industries", "sector": "Materials"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "sector": "Materials"},
    {"ticker": "BERGEPAINT", "name": "Berger Paints India", "sector": "Materials"},
    {"ticker": "KANSAINER", "name": "Kansai Nerolac Paints", "sector": "Materials"},
    {"ticker": "INDIGOPNTS", "name": "Indigo Paints", "sector": "Materials"},

    # ── Metals & Mining ──────────────────────────────────────────────────
    {"ticker": "TATASTEEL", "name": "Tata Steel", "sector": "Metals"},
    {"ticker": "JSWSTEEL", "name": "JSW Steel", "sector": "Metals"},
    {"ticker": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
    {"ticker": "VEDL", "name": "Vedanta", "sector": "Metals"},
    {"ticker": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Metals"},
    {"ticker": "SAIL", "name": "Steel Authority of India", "sector": "Metals"},
    {"ticker": "NMDC", "name": "NMDC", "sector": "Metals"},
    {"ticker": "COALINDIA", "name": "Coal India", "sector": "Energy"},
    {"ticker": "NATIONALUM", "name": "National Aluminium", "sector": "Metals"},
    {"ticker": "HINDZINC", "name": "Hindustan Zinc", "sector": "Metals"},
    {"ticker": "APLAPOLLO", "name": "APL Apollo Tubes", "sector": "Metals"},
    {"ticker": "JSWENERGY", "name": "JSW Energy", "sector": "Power"},
    {"ticker": "RATNAMANI", "name": "Ratnamani Metals & Tubes", "sector": "Metals"},
    {"ticker": "WELCORP", "name": "Welspun Corp", "sector": "Metals"},

    # ── Power, Utilities ─────────────────────────────────────────────────
    {"ticker": "NTPC", "name": "NTPC", "sector": "Power"},
    {"ticker": "POWERGRID", "name": "Power Grid Corp", "sector": "Power"},
    {"ticker": "TATAPOWER", "name": "Tata Power", "sector": "Power"},
    {"ticker": "ADANIPOWER", "name": "Adani Power", "sector": "Power"},
    {"ticker": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Power"},
    {"ticker": "ADANIENSOL", "name": "Adani Energy Solutions", "sector": "Power"},
    {"ticker": "TORNTPOWER", "name": "Torrent Power", "sector": "Power"},
    {"ticker": "CESC", "name": "CESC", "sector": "Power"},
    {"ticker": "NHPC", "name": "NHPC", "sector": "Power"},
    {"ticker": "SJVN", "name": "SJVN", "sector": "Power"},
    {"ticker": "NLCINDIA", "name": "NLC India", "sector": "Power"},
    {"ticker": "IEX", "name": "Indian Energy Exchange", "sector": "Power"},
    {"ticker": "RPOWER", "name": "Reliance Power", "sector": "Power"},
    {"ticker": "INOXWIND", "name": "Inox Wind", "sector": "Power"},
    {"ticker": "SUZLON", "name": "Suzlon Energy", "sector": "Power"},

    # ── Telecom ──────────────────────────────────────────────────────────
    {"ticker": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
    {"ticker": "IDEA", "name": "Vodafone Idea", "sector": "Telecom"},
    {"ticker": "TATACOMM", "name": "Tata Communications", "sector": "Telecom"},
    {"ticker": "INDUSTOWER", "name": "Indus Towers", "sector": "Telecom"},
    {"ticker": "RAILTEL", "name": "RailTel Corp of India", "sector": "Telecom"},
    {"ticker": "HFCL", "name": "HFCL", "sector": "Telecom"},

    # ── Industrials, Engineering, Capital Goods ─────────────────────────
    {"ticker": "LT", "name": "Larsen & Toubro", "sector": "Industrials"},
    {"ticker": "SIEMENS", "name": "Siemens", "sector": "Industrials"},
    {"ticker": "ABB", "name": "ABB India", "sector": "Industrials"},
    {"ticker": "BEL", "name": "Bharat Electronics", "sector": "Industrials"},
    {"ticker": "BHEL", "name": "Bharat Heavy Electricals", "sector": "Industrials"},
    {"ticker": "HAL", "name": "Hindustan Aeronautics", "sector": "Industrials"},
    {"ticker": "CUMMINSIND", "name": "Cummins India", "sector": "Industrials"},
    {"ticker": "THERMAX", "name": "Thermax", "sector": "Industrials"},
    {"ticker": "VOLTAS", "name": "Voltas", "sector": "Industrials"},
    {"ticker": "ABFRL", "name": "Aditya Birla Fashion & Retail", "sector": "Retail"},
    {"ticker": "POLYCAB", "name": "Polycab India", "sector": "Industrials"},
    {"ticker": "HAVELLS", "name": "Havells India", "sector": "Industrials"},
    {"ticker": "CGPOWER", "name": "CG Power & Industrial Solutions", "sector": "Industrials"},
    {"ticker": "KEC", "name": "KEC International", "sector": "Industrials"},
    {"ticker": "KALPATPOWR", "name": "Kalpataru Projects International", "sector": "Industrials"},
    {"ticker": "AIAENG", "name": "AIA Engineering", "sector": "Industrials"},
    {"ticker": "CARBORUNIV", "name": "Carborundum Universal", "sector": "Industrials"},
    {"ticker": "GRINDWELL", "name": "Grindwell Norton", "sector": "Industrials"},
    {"ticker": "TIMKEN", "name": "Timken India", "sector": "Industrials"},
    {"ticker": "ELGIEQUIP", "name": "Elgi Equipments", "sector": "Industrials"},
    {"ticker": "HONAUT", "name": "Honeywell Automation India", "sector": "Industrials"},
    {"ticker": "TRITURBINE", "name": "Triveni Turbine", "sector": "Industrials"},

    # ── Defence ──────────────────────────────────────────────────────────
    {"ticker": "MAZDOCK", "name": "Mazagon Dock Shipbuilders", "sector": "Defence"},
    {"ticker": "BDL", "name": "Bharat Dynamics", "sector": "Defence"},
    {"ticker": "COCHINSHIP", "name": "Cochin Shipyard", "sector": "Defence"},
    {"ticker": "GRSE", "name": "Garden Reach Shipbuilders", "sector": "Defence"},
    {"ticker": "DATAPATTNS", "name": "Data Patterns India", "sector": "Defence"},
    {"ticker": "MTARTECH", "name": "MTAR Technologies", "sector": "Defence"},

    # ── Infrastructure / Construction ───────────────────────────────────
    {"ticker": "ADANIENT", "name": "Adani Enterprises", "sector": "Diversified"},
    {"ticker": "ADANIPORTS", "name": "Adani Ports & SEZ", "sector": "Infrastructure"},
    {"ticker": "GMRINFRA", "name": "GMR Airports Infrastructure", "sector": "Infrastructure"},
    {"ticker": "IRCTC", "name": "Indian Railway Catering & Tourism", "sector": "Infrastructure"},
    {"ticker": "NCC", "name": "NCC", "sector": "Infrastructure"},
    {"ticker": "GPPL", "name": "Gujarat Pipavav Port", "sector": "Infrastructure"},
    {"ticker": "JKIL", "name": "J Kumar Infraprojects", "sector": "Infrastructure"},
    {"ticker": "IRB", "name": "IRB Infrastructure Developers", "sector": "Infrastructure"},

    # ── Real Estate ──────────────────────────────────────────────────────
    {"ticker": "DLF", "name": "DLF", "sector": "Real Estate"},
    {"ticker": "GODREJPROP", "name": "Godrej Properties", "sector": "Real Estate"},
    {"ticker": "OBEROIRLTY", "name": "Oberoi Realty", "sector": "Real Estate"},
    {"ticker": "PRESTIGE", "name": "Prestige Estates Projects", "sector": "Real Estate"},
    {"ticker": "BRIGADE", "name": "Brigade Enterprises", "sector": "Real Estate"},
    {"ticker": "PHOENIXLTD", "name": "Phoenix Mills", "sector": "Real Estate"},
    {"ticker": "MAHLIFE", "name": "Mahindra Lifespaces", "sector": "Real Estate"},
    {"ticker": "SOBHA", "name": "Sobha", "sector": "Real Estate"},
    {"ticker": "LODHA", "name": "Macrotech Developers (Lodha)", "sector": "Real Estate"},

    # ── Retail / E-commerce / Consumer Durables ─────────────────────────
    {"ticker": "TITAN", "name": "Titan Company", "sector": "Consumer Durables"},
    {"ticker": "DMART", "name": "Avenue Supermarts (DMart)", "sector": "Retail"},
    {"ticker": "TRENT", "name": "Trent", "sector": "Retail"},
    {"ticker": "VMART", "name": "V-Mart Retail", "sector": "Retail"},
    {"ticker": "ABFRL", "name": "Aditya Birla Fashion & Retail", "sector": "Retail"},
    {"ticker": "SHOPERSTOP", "name": "Shoppers Stop", "sector": "Retail"},
    {"ticker": "ZOMATO", "name": "Zomato (Eternal)", "sector": "Internet"},
    {"ticker": "NYKAA", "name": "FSN E-Commerce (Nykaa)", "sector": "Internet"},
    {"ticker": "PAYTM", "name": "One 97 Communications (Paytm)", "sector": "Internet"},
    {"ticker": "POLICYBZR", "name": "PB Fintech (Policybazaar)", "sector": "Internet"},
    {"ticker": "DELHIVERY", "name": "Delhivery", "sector": "Internet"},
    {"ticker": "NAUKRI", "name": "Info Edge (Naukri)", "sector": "Internet"},
    {"ticker": "ASIANTILES", "name": "Asian Granito India", "sector": "Consumer Durables"},
    {"ticker": "WHIRLPOOL", "name": "Whirlpool of India", "sector": "Consumer Durables"},
    {"ticker": "BAJAJELEC", "name": "Bajaj Electricals", "sector": "Consumer Durables"},
    {"ticker": "CROMPTON", "name": "Crompton Greaves Consumer Electrical", "sector": "Consumer Durables"},
    {"ticker": "SYMPHONY", "name": "Symphony", "sector": "Consumer Durables"},
    {"ticker": "DIXON", "name": "Dixon Technologies", "sector": "Consumer Durables"},
    {"ticker": "AMBER", "name": "Amber Enterprises India", "sector": "Consumer Durables"},
    {"ticker": "VGUARD", "name": "V-Guard Industries", "sector": "Consumer Durables"},
    {"ticker": "KAJARIACER", "name": "Kajaria Ceramics", "sector": "Consumer Durables"},
    {"ticker": "SUPREMEIND", "name": "Supreme Industries", "sector": "Consumer Durables"},
    {"ticker": "ASTRAL", "name": "Astral", "sector": "Consumer Durables"},
    {"ticker": "RELAXO", "name": "Relaxo Footwears", "sector": "Consumer Durables"},
    {"ticker": "BATAINDIA", "name": "Bata India", "sector": "Consumer Durables"},
    {"ticker": "PAGEIND", "name": "Page Industries", "sector": "Consumer Durables"},
    {"ticker": "ADITYABIRLA", "name": "Aditya Birla Capital", "sector": "Financials"},
    {"ticker": "RAYMOND", "name": "Raymond", "sector": "Consumer Durables"},

    # ── Chemicals & Specialty ───────────────────────────────────────────
    {"ticker": "UPL", "name": "UPL", "sector": "Chemicals"},
    {"ticker": "PIIND", "name": "PI Industries", "sector": "Chemicals"},
    {"ticker": "SRF", "name": "SRF", "sector": "Chemicals"},
    {"ticker": "AARTI", "name": "Aarti Industries", "sector": "Chemicals"},
    {"ticker": "DEEPAKNTR", "name": "Deepak Nitrite", "sector": "Chemicals"},
    {"ticker": "TATACHEM", "name": "Tata Chemicals", "sector": "Chemicals"},
    {"ticker": "GNFC", "name": "Gujarat Narmada Valley Fertilizers", "sector": "Chemicals"},
    {"ticker": "GSFC", "name": "Gujarat State Fertilizers", "sector": "Chemicals"},
    {"ticker": "NAVINFLUOR", "name": "Navin Fluorine International", "sector": "Chemicals"},
    {"ticker": "ATUL", "name": "Atul", "sector": "Chemicals"},
    {"ticker": "FINEORG", "name": "Fine Organic Industries", "sector": "Chemicals"},
    {"ticker": "GUJALKALI", "name": "Gujarat Alkalies & Chemicals", "sector": "Chemicals"},
    {"ticker": "CLEAN", "name": "Clean Science & Technology", "sector": "Chemicals"},
    {"ticker": "VINATIORGA", "name": "Vinati Organics", "sector": "Chemicals"},
    {"ticker": "CHAMBLFERT", "name": "Chambal Fertilisers", "sector": "Chemicals"},
    {"ticker": "COROMANDEL", "name": "Coromandel International", "sector": "Chemicals"},
    {"ticker": "RALLIS", "name": "Rallis India", "sector": "Chemicals"},
    {"ticker": "SOLARINDS", "name": "Solar Industries India", "sector": "Chemicals"},

    # ── Media & Entertainment ───────────────────────────────────────────
    {"ticker": "SUNTV", "name": "Sun TV Network", "sector": "Media"},
    {"ticker": "ZEEL", "name": "Zee Entertainment Enterprises", "sector": "Media"},
    {"ticker": "PVRINOX", "name": "PVR Inox", "sector": "Media"},
    {"ticker": "SAREGAMA", "name": "Saregama India", "sector": "Media"},
    {"ticker": "TIPSINDLTD", "name": "Tips Industries", "sector": "Media"},
    {"ticker": "NETWORK18", "name": "Network 18 Media & Investments", "sector": "Media"},

    # ── Logistics & Transportation ──────────────────────────────────────
    {"ticker": "BLUEDART", "name": "Blue Dart Express", "sector": "Logistics"},
    {"ticker": "CONCOR", "name": "Container Corporation of India", "sector": "Logistics"},
    {"ticker": "GATI", "name": "Gati", "sector": "Logistics"},
    {"ticker": "TCI", "name": "Transport Corporation of India", "sector": "Logistics"},
    {"ticker": "MAHLOG", "name": "Mahindra Logistics", "sector": "Logistics"},

    # ── Aviation ────────────────────────────────────────────────────────
    {"ticker": "INDIGO", "name": "InterGlobe Aviation (IndiGo)", "sector": "Aviation"},
    {"ticker": "SPICEJET", "name": "SpiceJet", "sector": "Aviation"},

    # ── Hospitality & Tourism ───────────────────────────────────────────
    {"ticker": "INDHOTEL", "name": "Indian Hotels Company (Taj)", "sector": "Hospitality"},
    {"ticker": "EIHOTEL", "name": "EIH (Oberoi Hotels)", "sector": "Hospitality"},
    {"ticker": "LEMONTREE", "name": "Lemon Tree Hotels", "sector": "Hospitality"},
    {"ticker": "CHALET", "name": "Chalet Hotels", "sector": "Hospitality"},

    # ── Misc / Diversified ──────────────────────────────────────────────
    {"ticker": "BSE", "name": "BSE Ltd", "sector": "Financials"},
    {"ticker": "MCX", "name": "Multi Commodity Exchange of India", "sector": "Financials"},
    {"ticker": "CDSL", "name": "Central Depository Services", "sector": "Financials"},
    {"ticker": "KFINTECH", "name": "KFin Technologies", "sector": "Financials"},
    {"ticker": "CAMS", "name": "Computer Age Management Services", "sector": "Financials"},
    {"ticker": "ICICIGI", "name": "ICICI Lombard General Insurance", "sector": "Financials"},
    {"ticker": "PEL", "name": "Piramal Enterprises", "sector": "Diversified"},
    {"ticker": "ABCAPITAL", "name": "Aditya Birla Capital", "sector": "Financials"},
    {"ticker": "JIOFIN", "name": "Jio Financial Services", "sector": "Financials"},
    {"ticker": "JUBLFOOD", "name": "Jubilant FoodWorks", "sector": "FMCG"},
    {"ticker": "JUBLINGREA", "name": "Jubilant Ingrevia", "sector": "Chemicals"},
    {"ticker": "AAVAS", "name": "Aavas Financiers", "sector": "Financials"},
    {"ticker": "HOMEFIRST", "name": "Home First Finance", "sector": "Financials"},
    {"ticker": "REPCOHOME", "name": "Repco Home Finance", "sector": "Financials"},
    {"ticker": "PNBHOUSING", "name": "PNB Housing Finance", "sector": "Financials"},
    {"ticker": "CHOLAHLDNG", "name": "Cholamandalam Financial Holdings", "sector": "Financials"},
    {"ticker": "BAJAJHLDNG", "name": "Bajaj Holdings & Investment", "sector": "Financials"},
    {"ticker": "GICRE", "name": "General Insurance Corporation of India", "sector": "Financials"},
    {"ticker": "INDIAMART", "name": "IndiaMART InterMESH", "sector": "Internet"},
    {"ticker": "JUSTDIAL", "name": "Just Dial", "sector": "Internet"},
    {"ticker": "RVNL", "name": "Rail Vikas Nigam", "sector": "Infrastructure"},
    {"ticker": "IRCON", "name": "Ircon International", "sector": "Infrastructure"},
    {"ticker": "ENGINERSIN", "name": "Engineers India", "sector": "Industrials"},
    {"ticker": "HUDCO", "name": "Housing & Urban Development Corp", "sector": "Financials"},
]


# Deduplicate by ticker (defensive — easy to accidentally type-twice in a hand-written list).
_seen: set[str] = set()
KNOWN_TICKERS_SEED: list[_Row] = []
for _row in _RAW:
    if _row["ticker"] not in _seen:
        _seen.add(_row["ticker"])
        KNOWN_TICKERS_SEED.append(_row)
