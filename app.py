"""
Finn.no Deal Finder - Ultimate Norwegian Marketplace Scraper
A powerful tool to find the best deals on Norway's largest marketplace
"""

from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import hashlib
import re
from urllib.parse import urlencode, quote_plus
import time
import statistics
from io import BytesIO
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import threading

app = Flask(__name__)
CORS(app)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
SEARCHES_FILE = os.path.join(DATA_DIR, 'saved_searches.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'price_history.json')
FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Finn.no Categories and Subcategories
FINN_CATEGORIES = {
    "torget": {
        "name": "Torget (Marketplace)",
        "url": "https://www.finn.no/bap/forsale/search.html",
        "subcategories": {
            "all": "Alle kategorier",
            "electronics": "Elektronikk og hvitevarer",
            "furniture": "Møbler og interiør",
            "clothing": "Klær, kosmetikk og accessoirer",
            "sports": "Sport og friluftsliv",
            "vehicles": "Bil-, MC- og båtutstyr",
            "kids": "Barn og baby",
            "hobby": "Hobby og fritid",
            "garden": "Hage og utemiljø",
            "tools": "Verktøy og maskiner",
            "music": "Musikk og lydanlegg",
            "animals": "Dyr og tilbehør",
            "collectibles": "Samleobjekter og kunst",
            "books": "Bøker og blader",
            "food": "Mat og drikke"
        }
    },
    "car": {
        "name": "Bil (Cars)",
        "url": "https://www.finn.no/car/used/search.html",
        "subcategories": {
            "all": "Alle merker",
            "audi": "Audi",
            "bmw": "BMW",
            "ford": "Ford",
            "mercedes": "Mercedes-Benz",
            "nissan": "Nissan",
            "tesla": "Tesla",
            "toyota": "Toyota",
            "volkswagen": "Volkswagen",
            "volvo": "Volvo"
        }
    },
    "realestate": {
        "name": "Eiendom (Real Estate)",
        "url": "https://www.finn.no/realestate/homes/search.html",
        "subcategories": {
            "all": "Alle typer",
            "apartment": "Leilighet",
            "house": "Enebolig",
            "townhouse": "Rekkehus",
            "cabin": "Hytte",
            "plot": "Tomt"
        }
    },
    "mc": {
        "name": "MC (Motorcycles)",
        "url": "https://www.finn.no/mc/used/search.html",
        "subcategories": {
            "all": "Alle typer"
        }
    },
    "boat": {
        "name": "Båt (Boats)",
        "url": "https://www.finn.no/boat/forsale/search.html",
        "subcategories": {
            "all": "Alle typer",
            "motorboat": "Motorbåt",
            "sailboat": "Seilbåt",
            "jet_ski": "Vannscooter"
        }
    }
}

# Norwegian Locations (Fylker/Counties)
NORWEGIAN_LOCATIONS = {
    "all": "Hele Norge",
    "oslo": "Oslo",
    "viken": "Viken",
    "vestland": "Vestland",
    "rogaland": "Rogaland",
    "trondelag": "Trøndelag",
    "nordland": "Nordland",
    "vestfold_telemark": "Vestfold og Telemark",
    "agder": "Agder",
    "innlandet": "Innlandet",
    "more_romsdal": "Møre og Romsdal",
    "troms_finnmark": "Troms og Finnmark"
}

# Condition options
CONDITIONS = {
    "all": "Alle",
    "new": "Ny",
    "as_new": "Som ny",
    "used": "Brukt",
    "for_parts": "For deler"
}

# Sort options
SORT_OPTIONS = {
    "relevance": "Relevans",
    "price_asc": "Pris lav-høy",
    "price_desc": "Pris høy-lav",
    "date_desc": "Nyeste først",
    "date_asc": "Eldste først"
}


class FinnScraper:
    """Scraper for finn.no marketplace"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'nb-NO,nb;q=0.9,no;q=0.8,nn;q=0.7,en-US;q=0.6,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
    def build_search_url(self, params):
        """Build finn.no search URL from parameters"""
        category = params.get('category', 'torget')
        base_url = FINN_CATEGORIES.get(category, FINN_CATEGORIES['torget'])['url']
        
        query_params = {}
        
        # Search query
        if params.get('query'):
            query_params['q'] = params['query']
        
        # Price range
        if params.get('price_from'):
            query_params['price_from'] = params['price_from']
        if params.get('price_to'):
            query_params['price_to'] = params['price_to']
        
        # Condition
        condition = params.get('condition', 'all')
        if condition != 'all':
            condition_map = {
                'new': '1',
                'as_new': '2', 
                'used': '3',
                'for_parts': '4'
            }
            if condition in condition_map:
                query_params['condition'] = condition_map[condition]
        
        # Sort
        sort = params.get('sort', 'relevance')
        sort_map = {
            'price_asc': '2',
            'price_desc': '3',
            'date_desc': '1',
            'date_asc': '4'
        }
        if sort in sort_map:
            query_params['sort'] = sort_map[sort]
        
        # Published within (days)
        if params.get('published_within'):
            query_params['published'] = params['published_within']
        
        # Private sellers only
        if params.get('private_only'):
            query_params['dealer_segment'] = '1'
        
        # Has image
        if params.get('has_image'):
            query_params['image'] = '1'
        
        # Shipping available (Fiks Ferdig)
        if params.get('shipping'):
            query_params['fiks_ferdig'] = '1'
        
        url = base_url
        if query_params:
            url += '?' + urlencode(query_params, quote_via=quote_plus)
        
        return url
    
    def scrape_listings(self, params, max_pages=3):
        """Scrape listings from finn.no"""
        all_listings = []
        url = self.build_search_url(params)
        
        for page in range(1, max_pages + 1):
            page_url = url
            if page > 1:
                separator = '&' if '?' in url else '?'
                page_url = f"{url}{separator}page={page}"
            
            try:
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                listings = self._parse_listings(soup, params.get('category', 'torget'))
                
                if not listings:
                    break
                    
                all_listings.extend(listings)
                
                # Be respectful with rate limiting
                time.sleep(0.5)
                
            except requests.RequestException as e:
                print(f"Error scraping page {page}: {e}")
                break
        
        return all_listings
    
    def _parse_listings(self, soup, category):
        """Parse listings from BeautifulSoup object"""
        listings = []
        
        # Find all article elements (finn.no listing cards)
        articles = soup.find_all('article', class_=lambda x: x and ('ads__unit' in x or 'sf-search-ad' in x or 'a-card' in x))
        
        # Alternative selectors
        if not articles:
            articles = soup.find_all('a', class_=lambda x: x and 'sf-search-ad' in str(x))
        
        if not articles:
            # Try finding by data attributes or other patterns
            articles = soup.select('[data-testid*="ad-card"], .ads__unit, .result-card, article')
        
        for article in articles:
            try:
                listing = self._parse_single_listing(article, category)
                if listing and listing.get('title'):
                    listings.append(listing)
            except Exception as e:
                print(f"Error parsing listing: {e}")
                continue
        
        return listings
    
    def _parse_single_listing(self, article, category):
        """Parse a single listing element"""
        listing = {
            'id': None,
            'title': None,
            'price': None,
            'price_numeric': None,
            'location': None,
            'description': None,
            'image_url': None,
            'listing_url': None,
            'published': None,
            'condition': None,
            'shipping_available': False,
            'category': category,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Extract link and ID
        link = article.find('a', href=True)
        if link:
            href = link.get('href', '')
            if href:
                if href.startswith('/'):
                    listing['listing_url'] = f"https://www.finn.no{href}"
                elif href.startswith('http'):
                    listing['listing_url'] = href
                
                # Extract ID from URL
                id_match = re.search(r'/(\d+)(?:\?|$|#)', href)
                if id_match:
                    listing['id'] = id_match.group(1)
        
        # Extract title
        title_elem = article.find(['h2', 'h3', 'span'], class_=lambda x: x and ('heading' in str(x).lower() or 'title' in str(x).lower()))
        if not title_elem:
            title_elem = article.find('a', class_=lambda x: x and 'sf-search-ad-link' in str(x))
        if title_elem:
            listing['title'] = title_elem.get_text(strip=True)
        
        # Extract price
        price_selectors = [
            ('span', {'class': lambda x: x and 'price' in str(x).lower()}),
            ('span', {'data-testid': 'price'}),
            ('div', {'class': lambda x: x and 'price' in str(x).lower()})
        ]
        
        for tag, attrs in price_selectors:
            price_elem = article.find(tag, attrs)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                listing['price'] = price_text
                # Extract numeric price
                price_match = re.search(r'([\d\s]+)', price_text.replace(' ', '').replace('\xa0', ''))
                if price_match:
                    try:
                        listing['price_numeric'] = int(price_match.group(1).replace(' ', ''))
                    except ValueError:
                        pass
                break
        
        # Extract location
        location_elem = article.find(['span', 'div'], class_=lambda x: x and ('location' in str(x).lower() or 'address' in str(x).lower()))
        if location_elem:
            listing['location'] = location_elem.get_text(strip=True)
        
        # Extract image
        img = article.find('img')
        if img:
            listing['image_url'] = img.get('src') or img.get('data-src') or img.get('srcset', '').split()[0]
        
        # Extract description/subtitle
        desc_elem = article.find(['p', 'span'], class_=lambda x: x and ('description' in str(x).lower() or 'subtitle' in str(x).lower()))
        if desc_elem:
            listing['description'] = desc_elem.get_text(strip=True)
        
        # Check for shipping badge (Fiks Ferdig)
        shipping_badge = article.find(['span', 'div'], class_=lambda x: x and 'fiks' in str(x).lower())
        if shipping_badge:
            listing['shipping_available'] = True
        
        # Extract published time
        time_elem = article.find('time')
        if time_elem:
            listing['published'] = time_elem.get('datetime') or time_elem.get_text(strip=True)
        
        return listing
    
    def get_listing_details(self, listing_url):
        """Get detailed information for a single listing"""
        try:
            response = self.session.get(listing_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {
                'full_description': None,
                'seller_info': None,
                'all_images': [],
                'specifications': {},
                'views': None
            }
            
            # Get full description
            desc_elem = soup.find(['div', 'p'], class_=lambda x: x and 'description' in str(x).lower())
            if desc_elem:
                details['full_description'] = desc_elem.get_text(strip=True)
            
            # Get all images
            gallery = soup.find_all('img', src=lambda x: x and 'images.finncdn.no' in str(x))
            for img in gallery:
                src = img.get('src')
                if src:
                    details['all_images'].append(src)
            
            # Get seller info
            seller_elem = soup.find(['div', 'span'], class_=lambda x: x and 'seller' in str(x).lower())
            if seller_elem:
                details['seller_info'] = seller_elem.get_text(strip=True)
            
            return details
            
        except Exception as e:
            print(f"Error getting listing details: {e}")
            return None


class DealAnalyzer:
    """Analyze deals and find the best prices"""
    
    @staticmethod
    def calculate_deal_score(listing, similar_listings):
        """Calculate a deal score from 0-100 based on price compared to similar items"""
        if not listing.get('price_numeric') or not similar_listings:
            return None
        
        prices = [l['price_numeric'] for l in similar_listings if l.get('price_numeric')]
        if len(prices) < 2:
            return None
        
        avg_price = statistics.mean(prices)
        min_price = min(prices)
        max_price = max(prices)
        current_price = listing['price_numeric']
        
        # Calculate percentile (lower is better)
        below_count = sum(1 for p in prices if p > current_price)
        percentile = (below_count / len(prices)) * 100
        
        # Calculate savings percentage
        savings_pct = ((avg_price - current_price) / avg_price) * 100 if avg_price > 0 else 0
        
        # Deal score: combination of percentile and savings
        deal_score = min(100, max(0, (percentile * 0.6) + (savings_pct * 0.4)))
        
        return {
            'score': round(deal_score, 1),
            'avg_price': round(avg_price, 0),
            'min_price': min_price,
            'max_price': max_price,
            'savings_amount': round(avg_price - current_price, 0),
            'savings_percent': round(savings_pct, 1),
            'price_rank': f"{below_count + 1}/{len(prices)}",
            'is_great_deal': deal_score >= 70,
            'is_good_deal': 50 <= deal_score < 70
        }
    
    @staticmethod
    def find_similar_listings(listing, all_listings):
        """Find similar listings based on title keywords"""
        if not listing.get('title'):
            return []
        
        keywords = set(listing['title'].lower().split())
        # Remove common words
        stopwords = {'og', 'i', 'på', 'til', 'for', 'med', 'av', 'en', 'et', 'den', 'det', 'de', 'som', 'er', 'var', 'har', 'kan', 'vil', 'skal'}
        keywords = keywords - stopwords
        
        similar = []
        for other in all_listings:
            if other.get('id') == listing.get('id'):
                continue
            
            other_keywords = set(other.get('title', '').lower().split())
            overlap = len(keywords & other_keywords)
            
            if overlap >= 2:  # At least 2 common keywords
                similar.append(other)
        
        return similar
    
    @staticmethod
    def rank_deals(listings):
        """Rank all listings by deal quality"""
        ranked = []
        
        for listing in listings:
            similar = DealAnalyzer.find_similar_listings(listing, listings)
            analysis = DealAnalyzer.calculate_deal_score(listing, similar)
            
            listing_copy = listing.copy()
            listing_copy['deal_analysis'] = analysis
            ranked.append(listing_copy)
        
        # Sort by deal score (highest first)
        ranked.sort(key=lambda x: (x.get('deal_analysis', {}) or {}).get('score', 0), reverse=True)
        
        return ranked


# Initialize scraper
scraper = FinnScraper()
analyzer = DealAnalyzer()


# Utility functions for data persistence
def load_json_file(filepath, default=None):
    """Load JSON file with default fallback"""
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """Save data to JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False


# Flask Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html',
                         categories=FINN_CATEGORIES,
                         locations=NORWEGIAN_LOCATIONS,
                         conditions=CONDITIONS,
                         sort_options=SORT_OPTIONS)


@app.route('/api/categories')
def get_categories():
    """Get all categories and subcategories"""
    return jsonify(FINN_CATEGORIES)


@app.route('/api/search', methods=['POST'])
def search():
    """Search finn.no and analyze deals"""
    params = request.json
    
    # Scrape listings
    listings = scraper.scrape_listings(params, max_pages=params.get('max_pages', 3))
    
    # Analyze deals
    ranked_listings = analyzer.rank_deals(listings)
    
    # Calculate summary statistics
    prices = [l['price_numeric'] for l in listings if l.get('price_numeric')]
    
    summary = {
        'total_found': len(listings),
        'with_price': len(prices),
        'avg_price': round(statistics.mean(prices), 0) if prices else 0,
        'min_price': min(prices) if prices else 0,
        'max_price': max(prices) if prices else 0,
        'great_deals': sum(1 for l in ranked_listings if (l.get('deal_analysis') or {}).get('is_great_deal')),
        'good_deals': sum(1 for l in ranked_listings if (l.get('deal_analysis') or {}).get('is_good_deal'))
    }
    
    return jsonify({
        'success': True,
        'listings': ranked_listings,
        'summary': summary,
        'search_url': scraper.build_search_url(params)
    })


@app.route('/api/saved-searches', methods=['GET'])
def get_saved_searches():
    """Get all saved searches"""
    searches = load_json_file(SEARCHES_FILE, [])
    return jsonify(searches)


@app.route('/api/saved-searches', methods=['POST'])
def save_search():
    """Save a new search"""
    search_data = request.json
    search_data['id'] = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
    search_data['created_at'] = datetime.now().isoformat()
    
    searches = load_json_file(SEARCHES_FILE, [])
    searches.append(search_data)
    save_json_file(SEARCHES_FILE, searches)
    
    return jsonify({'success': True, 'search': search_data})


@app.route('/api/saved-searches/<search_id>', methods=['DELETE'])
def delete_search(search_id):
    """Delete a saved search"""
    searches = load_json_file(SEARCHES_FILE, [])
    searches = [s for s in searches if s.get('id') != search_id]
    save_json_file(SEARCHES_FILE, searches)
    
    return jsonify({'success': True})


@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    """Get all favorited listings"""
    favorites = load_json_file(FAVORITES_FILE, [])
    return jsonify(favorites)


@app.route('/api/favorites', methods=['POST'])
def add_favorite():
    """Add a listing to favorites"""
    listing = request.json
    
    favorites = load_json_file(FAVORITES_FILE, [])
    
    # Check if already favorited
    if not any(f.get('id') == listing.get('id') for f in favorites):
        listing['favorited_at'] = datetime.now().isoformat()
        favorites.append(listing)
        save_json_file(FAVORITES_FILE, favorites)
    
    return jsonify({'success': True})


@app.route('/api/favorites/<listing_id>', methods=['DELETE'])
def remove_favorite(listing_id):
    """Remove a listing from favorites"""
    favorites = load_json_file(FAVORITES_FILE, [])
    favorites = [f for f in favorites if f.get('id') != listing_id]
    save_json_file(FAVORITES_FILE, favorites)
    
    return jsonify({'success': True})


@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export listings to CSV"""
    listings = request.json.get('listings', [])
    
    output = BytesIO()
    output.write('\ufeff'.encode('utf-8'))  # BOM for Excel
    
    fieldnames = ['title', 'price', 'location', 'condition', 'listing_url', 'deal_score', 'avg_price', 'savings']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    
    output.write(','.join(fieldnames).encode('utf-8') + b'\n')
    
    for listing in listings:
        row = {
            'title': listing.get('title', ''),
            'price': listing.get('price', ''),
            'location': listing.get('location', ''),
            'condition': listing.get('condition', ''),
            'listing_url': listing.get('listing_url', ''),
            'deal_score': (listing.get('deal_analysis') or {}).get('score', ''),
            'avg_price': (listing.get('deal_analysis') or {}).get('avg_price', ''),
            'savings': (listing.get('deal_analysis') or {}).get('savings_amount', '')
        }
        row_str = ','.join([f'"{str(v)}"' for v in row.values()])
        output.write(row_str.encode('utf-8') + b'\n')
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=finn_deals_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )


@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Export listings to PDF"""
    data = request.json
    listings = data.get('listings', [])
    search_params = data.get('search_params', {})
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1a1a2e')
    )
    elements.append(Paragraph("🔍 Finn.no Deal Finder Report", title_style))
    
    # Search info
    search_info = f"Search: {search_params.get('query', 'All items')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    elements.append(Paragraph(search_info, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Summary stats
    if listings:
        prices = [l['price_numeric'] for l in listings if l.get('price_numeric')]
        if prices:
            summary = f"Found {len(listings)} items | Avg price: {int(statistics.mean(prices)):,} kr | Price range: {min(prices):,} - {max(prices):,} kr"
            elements.append(Paragraph(summary, styles['Normal']))
            elements.append(Spacer(1, 20))
    
    # Table data
    table_data = [['#', 'Title', 'Price', 'Deal Score', 'Link']]
    
    for i, listing in enumerate(listings[:50], 1):  # Limit to 50 items
        deal_score = (listing.get('deal_analysis') or {}).get('score', '-')
        score_str = f"{deal_score}%" if isinstance(deal_score, (int, float)) else '-'
        
        title = listing.get('title', '')[:40] + ('...' if len(listing.get('title', '')) > 40 else '')
        
        table_data.append([
            str(i),
            title,
            listing.get('price', '-'),
            score_str,
            'Link' if listing.get('listing_url') else '-'
        ])
    
    table = Table(table_data, colWidths=[30, 200, 80, 70, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1a1a2e')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=finn_deals_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
    )


@app.route('/api/print', methods=['POST'])
def generate_print_view():
    """Generate print-friendly HTML"""
    data = request.json
    listings = data.get('listings', [])
    
    return render_template('print.html', listings=listings, generated=datetime.now().strftime('%Y-%m-%d %H:%M'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
