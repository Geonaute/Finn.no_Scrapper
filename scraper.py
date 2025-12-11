#!/usr/bin/env python3
"""
FINN.no Web Scraper Module
Handles all web scraping operations for FINN.no
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from typing import List, Dict, Any, Callable, Optional
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class FinnScraper:
    """Web scraper for FINN.no marketplace"""
    
    BASE_URL = "https://www.finn.no"
    
    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        
    def _get_headers(self) -> dict:
        """Get randomized headers"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,nn;q=0.7,en-US;q=0.6,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Cache-Control": "max-age=0",
        }
        
    def stop(self):
        """Stop the scraping process"""
        self._stop_flag.set()
        
    def _should_stop(self) -> bool:
        """Check if scraping should stop"""
        return self._stop_flag.is_set()
        
    def _reset_stop_flag(self):
        """Reset the stop flag"""
        self._stop_flag.clear()
        
    def _build_search_url(self, params: dict) -> str:
        """Build the search URL from parameters"""
        url_base = params.get('url_base', 'https://www.finn.no/bap/forsale/search.html')
        
        query_params = []
        
        # Add keyword search
        keyword = params.get('keyword', '').strip()
        if keyword:
            query_params.append(f"q={requests.utils.quote(keyword)}")
        
        # Add subcategory
        subcategory = params.get('subcategory', '')
        if subcategory:
            query_params.append(subcategory)
        
        # Add location
        location = params.get('location', '')
        if location:
            query_params.append(location)
        
        # Add condition
        condition = params.get('condition', '')
        if condition:
            query_params.append(condition)
        
        # Add price range
        price_min = params.get('price_min', '').strip()
        if price_min and price_min.isdigit():
            query_params.append(f"price_from={price_min}")
            
        price_max = params.get('price_max', '').strip()
        if price_max and price_max.isdigit():
            query_params.append(f"price_to={price_max}")
        
        # Add sorting
        sort = params.get('sort', '')
        if sort:
            query_params.append(sort)
        
        # Build URL
        if query_params:
            url = f"{url_base}?{'&'.join(query_params)}"
        else:
            url = url_base
            
        return url
        
    def search(
        self,
        params: dict,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Search FINN.no with the given parameters
        
        Args:
            params: Search parameters
            progress_callback: Callback function for progress updates
            
        Returns:
            dict with items and statistics
        """
        self._reset_stop_flag()
        
        results = {
            'items': [],
            'stats': {},
            'comparisons': {},
            'search_url': '',
            'search_time': datetime.now().isoformat()
        }
        
        try:
            # Build search URL
            search_url = self._build_search_url(params)
            results['search_url'] = search_url
            
            max_results = params.get('max_results', 50)
            items = []
            page = 1
            
            while len(items) < max_results and not self._should_stop():
                # Add page parameter
                page_url = search_url
                if page > 1:
                    separator = '&' if '?' in search_url else '?'
                    page_url = f"{search_url}{separator}page={page}"
                
                if progress_callback:
                    progress_callback(
                        len(items),
                        max_results,
                        f"(Page {page})"
                    )
                
                # Fetch search results page
                page_items = self._scrape_search_page(page_url)
                
                if not page_items:
                    break  # No more results
                
                items.extend(page_items)
                page += 1
                
                # Rate limiting - random delay
                time.sleep(random.uniform(0.5, 1.5))
            
            # Trim to max results
            items = items[:max_results]
            
            if progress_callback:
                progress_callback(len(items), max_results, "Fetching details...")
            
            # Fetch additional details for each item (with threading)
            if items and not self._should_stop():
                items = self._fetch_item_details(items, progress_callback)
            
            results['items'] = items
            
            # Calculate statistics
            results['stats'] = self._calculate_stats(items)
            
            # Find similar items for comparison
            results['comparisons'] = self._find_comparisons(items)
            
        except Exception as e:
            print(f"Search error: {e}")
            raise
            
        return results
        
    def _scrape_search_page(self, url: str) -> List[Dict]:
        """Scrape a single search results page"""
        items = []
        
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all ad cards - FINN uses various class patterns
            ad_containers = soup.find_all('article', class_=re.compile(r'(sf-search-ad|ads__unit)'))
            
            if not ad_containers:
                # Try alternative selectors
                ad_containers = soup.find_all('a', class_=re.compile(r'(sf-search-ad-link|ads__unit__link)'))
            
            if not ad_containers:
                # Try finding by data attributes
                ad_containers = soup.find_all(attrs={'data-testid': re.compile(r'(ad-|listing-)')})
            
            for container in ad_containers:
                if self._should_stop():
                    break
                    
                try:
                    item = self._parse_search_item(container)
                    if item:
                        items.append(item)
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
                    
        except requests.RequestException as e:
            print(f"Request error for {url}: {e}")
            
        return items
        
    def _parse_search_item(self, container) -> Optional[Dict]:
        """Parse a single search result item"""
        item = {
            'id': '',
            'title': '',
            'price': 0,
            'price_text': '',
            'location': '',
            'condition': '',
            'posted': '',
            'image_url': '',
            'url': '',
            'seller_type': '',
            'description': ''
        }
        
        # Extract URL and ID
        link = container.find('a', href=True)
        if not link and container.name == 'a':
            link = container
            
        if link:
            href = link.get('href', '')
            if href:
                item['url'] = urljoin(self.BASE_URL, href)
                # Extract finnkode from URL
                if 'finnkode=' in href:
                    match = re.search(r'finnkode=(\d+)', href)
                    if match:
                        item['id'] = match.group(1)
                elif '/ad.html' in href:
                    match = re.search(r'/ad\.html\?finnkode=(\d+)', href)
                    if match:
                        item['id'] = match.group(1)
                else:
                    # Extract from path
                    parts = href.rstrip('/').split('/')
                    if parts:
                        item['id'] = parts[-1]
        
        # Extract title
        title_elem = container.find(['h2', 'h3'], class_=re.compile(r'(title|heading)'))
        if not title_elem:
            title_elem = container.find(class_=re.compile(r'(ad-title|item-title|heading)'))
        if not title_elem:
            title_elem = container.find('a', class_=re.compile(r'link'))
            
        if title_elem:
            item['title'] = title_elem.get_text(strip=True)
        
        # Extract price
        price_elem = container.find(class_=re.compile(r'(price|amount)'))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            item['price_text'] = price_text
            # Parse price number
            price_match = re.search(r'[\d\s]+', price_text.replace('\xa0', ' '))
            if price_match:
                try:
                    item['price'] = int(price_match.group().replace(' ', '').strip())
                except ValueError:
                    pass
        
        # Extract location
        location_elem = container.find(class_=re.compile(r'(location|place|geo)'))
        if location_elem:
            item['location'] = location_elem.get_text(strip=True)
        
        # Extract image
        img = container.find('img')
        if img:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                item['image_url'] = src
        
        # Extract posted time
        time_elem = container.find(class_=re.compile(r'(time|date|published)'))
        if time_elem:
            item['posted'] = time_elem.get_text(strip=True)
        
        # Only return if we have minimum required data
        if item['title'] and (item['url'] or item['id']):
            return item
            
        return None
        
    def _fetch_item_details(
        self,
        items: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """Fetch detailed information for each item"""
        detailed_items = []
        total = len(items)
        completed = 0
        
        def fetch_single(item):
            nonlocal completed
            if self._should_stop():
                return item
                
            try:
                url = item.get('url', '')
                if url:
                    details = self._scrape_item_details(url)
                    item.update(details)
                    
                    # Small random delay for rate limiting
                    time.sleep(random.uniform(0.2, 0.5))
                    
            except Exception as e:
                print(f"Error fetching details for {item.get('id')}: {e}")
            
            with self._lock:
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, "")
                    
            return item
        
        # Use thread pool for concurrent fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_single, item): item for item in items}
            
            for future in as_completed(futures):
                if self._should_stop():
                    break
                try:
                    result = future.result()
                    detailed_items.append(result)
                except Exception as e:
                    print(f"Thread error: {e}")
                    detailed_items.append(futures[future])
        
        return detailed_items
        
    def _scrape_item_details(self, url: str) -> Dict:
        """Scrape detailed information from an item page"""
        details = {
            'condition': '',
            'description': '',
            'seller_name': '',
            'seller_type': '',
            'attributes': {},
            'images': []
        }
        
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract description
            desc_elem = soup.find(class_=re.compile(r'(description|body|content)'))
            if desc_elem:
                details['description'] = desc_elem.get_text(strip=True)[:500]
            
            # Extract condition
            condition_elem = soup.find(string=re.compile(r'Tilstand|Condition', re.I))
            if condition_elem:
                parent = condition_elem.find_parent()
                if parent:
                    sibling = parent.find_next_sibling()
                    if sibling:
                        details['condition'] = sibling.get_text(strip=True)
            
            # Extract all attribute key-value pairs
            attribute_rows = soup.find_all(class_=re.compile(r'(attribute|property|detail)'))
            for row in attribute_rows:
                label = row.find(class_=re.compile(r'(label|key|name)'))
                value = row.find(class_=re.compile(r'(value|data)'))
                if label and value:
                    key = label.get_text(strip=True)
                    val = value.get_text(strip=True)
                    details['attributes'][key] = val
            
            # Extract seller info
            seller_elem = soup.find(class_=re.compile(r'(seller|contact|author)'))
            if seller_elem:
                details['seller_name'] = seller_elem.get_text(strip=True)
                
                # Check if private or business
                if soup.find(string=re.compile(r'Privat|Private', re.I)):
                    details['seller_type'] = 'Private'
                elif soup.find(string=re.compile(r'Bedrift|Business|Forhandler', re.I)):
                    details['seller_type'] = 'Business'
            
            # Extract all images
            image_container = soup.find(class_=re.compile(r'(gallery|images|photos)'))
            if image_container:
                images = image_container.find_all('img')
                for img in images[:10]:  # Limit to 10 images
                    src = img.get('src') or img.get('data-src')
                    if src:
                        details['images'].append(src)
                        
        except requests.RequestException as e:
            print(f"Error fetching details from {url}: {e}")
            
        return details
        
    def _calculate_stats(self, items: List[Dict]) -> Dict:
        """Calculate statistics from the items"""
        stats = {
            'total_items': len(items),
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0,
            'median_price': 0,
            'best_deal_score': 0,
            'potential_savings': 0,
            'price_distribution': {}
        }
        
        if not items:
            return stats
        
        # Filter items with valid prices
        priced_items = [item for item in items if item.get('price', 0) > 0]
        
        if not priced_items:
            return stats
        
        prices = [item['price'] for item in priced_items]
        
        stats['avg_price'] = sum(prices) / len(prices)
        stats['min_price'] = min(prices)
        stats['max_price'] = max(prices)
        
        # Calculate median
        sorted_prices = sorted(prices)
        mid = len(sorted_prices) // 2
        if len(sorted_prices) % 2 == 0:
            stats['median_price'] = (sorted_prices[mid - 1] + sorted_prices[mid]) / 2
        else:
            stats['median_price'] = sorted_prices[mid]
        
        # Calculate price distribution
        ranges = [
            (0, 100),
            (100, 500),
            (500, 1000),
            (1000, 5000),
            (5000, 10000),
            (10000, 50000),
            (50000, 100000),
            (100000, float('inf'))
        ]
        
        for low, high in ranges:
            label = f"{low}-{high}" if high != float('inf') else f"{low}+"
            count = len([p for p in prices if low <= p < high])
            stats['price_distribution'][label] = count
        
        # Find best deal score
        deal_scores = [item.get('deal_score', 0) for item in items]
        if deal_scores:
            stats['best_deal_score'] = max(deal_scores)
        
        # Calculate potential savings (sum of savings from deals)
        total_savings = 0
        for item in items:
            if item.get('deal_score', 0) >= 70:
                avg_price = item.get('avg_price', 0)
                price = item.get('price', 0)
                if avg_price > price > 0:
                    total_savings += (avg_price - price)
        
        stats['potential_savings'] = total_savings
        
        return stats
        
    def _find_comparisons(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Find similar items for comparison"""
        comparisons = {}
        
        # Group items by normalized title keywords
        title_groups = {}
        
        for item in items:
            title = item.get('title', '').lower()
            
            # Extract key product identifiers
            # Common patterns: brand + model, product type, etc.
            words = re.findall(r'\b[\w]+\b', title)
            
            # Create a simplified key from significant words
            significant_words = []
            for word in words:
                # Skip common non-descriptive words
                if word not in ['til', 'for', 'med', 'og', 'i', 'på', 'selges', 'salg', 'pent', 'brukt', 'ny']:
                    if len(word) > 2:
                        significant_words.append(word)
            
            if len(significant_words) >= 2:
                # Use first 2-3 significant words as grouping key
                key = ' '.join(significant_words[:3])
                
                if key not in title_groups:
                    title_groups[key] = []
                title_groups[key].append(item)
        
        # Filter to only groups with multiple items
        for key, group_items in title_groups.items():
            if len(group_items) >= 2:
                # Capitalize key for display
                display_key = key.title()
                comparisons[display_key] = group_items[:5]  # Limit to 5 items per group
        
        return comparisons


class DemoScraper(FinnScraper):
    """Demo scraper that returns mock data for testing"""
    
    def search(
        self,
        params: dict,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """Return demo data"""
        import random
        
        demo_items = []
        max_results = params.get('max_results', 50)
        
        products = [
            "iPhone 15 Pro Max 256GB",
            "iPhone 14 Pro 128GB",
            "iPhone 13 64GB",
            "Samsung Galaxy S24 Ultra",
            "MacBook Pro M3 14\"",
            "MacBook Air M2",
            "iPad Pro 12.9\" 2024",
            "PlayStation 5",
            "Xbox Series X",
            "Nintendo Switch OLED",
            "Sony WH-1000XM5",
            "AirPods Pro 2",
            "DJI Mini 4 Pro",
            "GoPro Hero 12",
            "Canon EOS R6 II",
            "IKEA Kallax Shelf",
            "Herman Miller Aeron",
            "Gaming PC RTX 4080",
            "LG C3 OLED 65\"",
            "Dyson V15 Detect",
        ]
        
        locations = ["Oslo", "Bergen", "Trondheim", "Stavanger", "Kristiansand", 
                    "Tromsø", "Drammen", "Fredrikstad", "Sandnes", "Bærum"]
        
        conditions = ["Som ny", "Pent brukt", "Brukt", "Ny"]
        
        for i in range(min(max_results, 50)):
            if progress_callback:
                progress_callback(i + 1, max_results, "")
                time.sleep(0.05)  # Simulate loading
            
            product = random.choice(products)
            base_price = random.randint(500, 25000)
            
            # Some items are deals (30% cheaper)
            is_deal = random.random() < 0.3
            if is_deal:
                price = int(base_price * 0.7)
                avg_price = base_price
            else:
                price = base_price
                avg_price = int(base_price * 1.1)
            
            deal_score = random.randint(50, 95) if is_deal else random.randint(20, 65)
            
            demo_items.append({
                'id': str(random.randint(100000000, 999999999)),
                'title': product,
                'price': price,
                'price_text': f"{price:,} kr".replace(',', ' '),
                'location': random.choice(locations),
                'condition': random.choice(conditions),
                'posted': f"{random.randint(1, 30)} dager siden",
                'image_url': f"https://picsum.photos/seed/{i}/400/300",
                'url': f"https://www.finn.no/bap/forsale/ad.html?finnkode={random.randint(100000000, 999999999)}",
                'seller_type': random.choice(['Private', 'Business']),
                'description': f"Selger {product}. Fungerer perfekt, ingen riper eller skader.",
                'deal_score': deal_score,
                'avg_price': avg_price,
            })
        
        # Calculate stats
        prices = [item['price'] for item in demo_items if item['price'] > 0]
        avg_price = sum(prices) / len(prices) if prices else 0
        best_score = max([item['deal_score'] for item in demo_items]) if demo_items else 0
        hot_deals = [item for item in demo_items if item['deal_score'] >= 70]
        savings = sum(item.get('avg_price', 0) - item.get('price', 0) for item in hot_deals if item.get('avg_price', 0) > item.get('price', 0))
        
        return {
            'items': demo_items,
            'stats': {
                'total_items': len(demo_items),
                'avg_price': avg_price,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'best_deal_score': best_score,
                'potential_savings': savings,
            },
            'comparisons': self._find_comparisons(demo_items),
            'search_url': 'https://www.finn.no/bap/forsale/search.html?demo=true',
            'search_time': datetime.now().isoformat()
        }
