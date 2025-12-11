#!/usr/bin/env python3
"""
Deal Analyzer Module
Analyzes scraped items to identify deals and calculate deal scores
"""

from typing import List, Dict, Any, Optional
import re
from collections import defaultdict
import statistics


class DealAnalyzer:
    """Analyzes items to identify deals and calculate scores"""
    
    # Known brands and their typical price ranges (for reference)
    BRAND_PATTERNS = {
        'apple': r'\b(iphone|ipad|macbook|mac|apple|airpods|watch)\b',
        'samsung': r'\b(samsung|galaxy)\b',
        'sony': r'\b(sony|playstation|ps[45])\b',
        'microsoft': r'\b(xbox|microsoft|surface)\b',
        'nintendo': r'\b(nintendo|switch)\b',
        'dyson': r'\b(dyson)\b',
        'lg': r'\b(lg|oled)\b',
        'dji': r'\b(dji|mavic|mini|phantom)\b',
        'canon': r'\b(canon|eos)\b',
        'nikon': r'\b(nikon)\b',
        'nvidia': r'\b(nvidia|geforce|rtx|gtx)\b',
        'amd': r'\b(amd|ryzen|radeon)\b',
    }
    
    # Condition weights for deal scoring
    CONDITION_WEIGHTS = {
        'ny': 1.0,
        'new': 1.0,
        'som ny': 0.95,
        'like new': 0.95,
        'pent brukt': 0.85,
        'lightly used': 0.85,
        'brukt': 0.70,
        'used': 0.70,
        'til reparasjon': 0.40,
        'for repair': 0.40,
    }
    
    def __init__(self):
        self.price_history = defaultdict(list)
        
    def analyze(
        self,
        items: List[Dict],
        threshold: int = 70
    ) -> dict:
        """
        Analyze items and calculate deal scores
        
        Args:
            items: List of scraped items
            threshold: Minimum deal score to highlight
            
        Returns:
            dict with analyzed items and statistics
        """
        if not items:
            return {
                'items': [],
                'stats': {},
                'comparisons': {}
            }
        
        # Group similar items to calculate average prices
        price_groups = self._group_by_similarity(items)
        
        # Calculate average prices for each group
        group_averages = {}
        for group_key, group_items in price_groups.items():
            prices = [item.get('price', 0) for item in group_items if item.get('price', 0) > 0]
            if prices:
                group_averages[group_key] = {
                    'avg': statistics.mean(prices),
                    'median': statistics.median(prices),
                    'min': min(prices),
                    'max': max(prices),
                    'count': len(prices)
                }
        
        # Calculate deal score for each item
        analyzed_items = []
        for item in items:
            analyzed_item = item.copy()
            
            # Find the group this item belongs to
            group_key = self._get_group_key(item)
            group_stats = group_averages.get(group_key, {})
            
            # Calculate deal score
            deal_score, factors = self._calculate_deal_score(item, group_stats)
            
            analyzed_item['deal_score'] = deal_score
            analyzed_item['deal_factors'] = factors
            analyzed_item['avg_price'] = group_stats.get('avg', 0)
            analyzed_item['price_comparison'] = {
                'group_avg': group_stats.get('avg', 0),
                'group_median': group_stats.get('median', 0),
                'group_min': group_stats.get('min', 0),
                'group_max': group_stats.get('max', 0),
                'similar_items_count': group_stats.get('count', 0)
            }
            
            # Add deal recommendation
            if deal_score >= 90:
                analyzed_item['recommendation'] = '🔥 EXCELLENT DEAL - Buy Now!'
                analyzed_item['recommendation_level'] = 'excellent'
            elif deal_score >= 80:
                analyzed_item['recommendation'] = '⭐ Great Deal - Highly Recommended'
                analyzed_item['recommendation_level'] = 'great'
            elif deal_score >= 70:
                analyzed_item['recommendation'] = '👍 Good Deal - Worth Considering'
                analyzed_item['recommendation_level'] = 'good'
            elif deal_score >= 50:
                analyzed_item['recommendation'] = '📊 Fair Price - Compare Before Buying'
                analyzed_item['recommendation_level'] = 'fair'
            else:
                analyzed_item['recommendation'] = '⚠️ Above Average Price'
                analyzed_item['recommendation_level'] = 'overpriced'
            
            analyzed_items.append(analyzed_item)
        
        # Calculate overall statistics
        stats = self._calculate_overall_stats(analyzed_items, threshold)
        
        # Find comparison groups
        comparisons = self._find_comparison_groups(analyzed_items)
        
        return {
            'items': analyzed_items,
            'stats': stats,
            'comparisons': comparisons
        }
        
    def _group_by_similarity(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by similarity for price comparison"""
        groups = defaultdict(list)
        
        for item in items:
            key = self._get_group_key(item)
            groups[key].append(item)
        
        return dict(groups)
        
    def _get_group_key(self, item: Dict) -> str:
        """Generate a grouping key for an item"""
        title = item.get('title', '').lower()
        
        # Extract brand
        brand = 'unknown'
        for brand_name, pattern in self.BRAND_PATTERNS.items():
            if re.search(pattern, title, re.IGNORECASE):
                brand = brand_name
                break
        
        # Extract product type/model keywords
        # Remove common words and keep significant terms
        words = re.findall(r'\b[\w]+\b', title)
        significant_words = []
        
        stop_words = {'til', 'for', 'med', 'og', 'i', 'på', 'selges', 'salg', 
                     'pent', 'brukt', 'ny', 'som', 'god', 'fin', 'veldig',
                     'the', 'a', 'an', 'for', 'sale', 'selling'}
        
        for word in words:
            if word not in stop_words and len(word) > 2:
                significant_words.append(word)
        
        # Create key from brand + first 2 significant words
        key_parts = [brand]
        key_parts.extend(significant_words[:2])
        
        return '_'.join(key_parts)
        
    def _calculate_deal_score(
        self,
        item: Dict,
        group_stats: Dict
    ) -> tuple[int, Dict]:
        """
        Calculate deal score for an item
        
        Returns:
            tuple of (score, factors_dict)
        """
        factors = {
            'price_factor': 0,
            'condition_factor': 0,
            'seller_factor': 0,
            'listing_age_factor': 0,
            'details': {}
        }
        
        price = item.get('price', 0)
        
        if price <= 0:
            return 0, factors
        
        # 1. Price Factor (60% of score)
        # Compare to group average
        avg_price = group_stats.get('avg', 0)
        median_price = group_stats.get('median', 0)
        
        if avg_price > 0:
            # Calculate percentage difference from average
            price_diff_pct = (avg_price - price) / avg_price * 100
            
            # Score: Higher score for lower prices
            # +30% below avg = 100 points
            # At avg = 50 points
            # -30% above avg = 0 points
            price_factor = min(100, max(0, 50 + (price_diff_pct * 1.67)))
            
            factors['price_factor'] = price_factor
            factors['details']['price_vs_avg'] = f"{price_diff_pct:+.1f}%"
            factors['details']['avg_price'] = avg_price
        else:
            # No comparison data, give neutral score
            factors['price_factor'] = 50
        
        # 2. Condition Factor (20% of score)
        condition = item.get('condition', '').lower().strip()
        condition_weight = 0.7  # Default
        
        for cond_key, weight in self.CONDITION_WEIGHTS.items():
            if cond_key in condition:
                condition_weight = weight
                break
        
        condition_factor = condition_weight * 100
        factors['condition_factor'] = condition_factor
        factors['details']['condition'] = condition or 'Not specified'
        
        # 3. Seller Factor (10% of score)
        seller_type = item.get('seller_type', '').lower()
        
        # Private sellers often have better deals
        if 'private' in seller_type or 'privat' in seller_type:
            seller_factor = 70  # Slightly favorable
        elif 'business' in seller_type or 'bedrift' in seller_type:
            seller_factor = 60  # Neutral - may be more reliable but higher prices
        else:
            seller_factor = 65  # Unknown
        
        factors['seller_factor'] = seller_factor
        factors['details']['seller_type'] = seller_type or 'Unknown'
        
        # 4. Listing Age Factor (10% of score)
        posted = item.get('posted', '').lower()
        listing_age_factor = 70  # Default
        
        if 'i dag' in posted or 'today' in posted or 'time' in posted or 'minut' in posted:
            listing_age_factor = 90  # Very new listing - might be a fresh deal
        elif 'i går' in posted or 'yesterday' in posted:
            listing_age_factor = 85
        elif any(str(i) in posted for i in range(1, 4)) and 'dag' in posted:
            listing_age_factor = 75  # Few days old
        elif any(str(i) in posted for i in range(4, 8)) and 'dag' in posted:
            listing_age_factor = 65  # About a week
        elif 'uke' in posted or 'week' in posted:
            listing_age_factor = 55  # Weeks old - might be overpriced
        elif 'måned' in posted or 'month' in posted:
            listing_age_factor = 40  # Old listing
        
        factors['listing_age_factor'] = listing_age_factor
        factors['details']['posted'] = posted or 'Unknown'
        
        # Calculate weighted final score
        final_score = (
            factors['price_factor'] * 0.60 +
            factors['condition_factor'] * 0.20 +
            factors['seller_factor'] * 0.10 +
            factors['listing_age_factor'] * 0.10
        )
        
        return int(final_score), factors
        
    def _calculate_overall_stats(
        self,
        items: List[Dict],
        threshold: int
    ) -> Dict:
        """Calculate overall statistics for all analyzed items"""
        stats = {
            'total_items': len(items),
            'avg_price': 0,
            'median_price': 0,
            'min_price': 0,
            'max_price': 0,
            'avg_deal_score': 0,
            'best_deal_score': 0,
            'deals_count': 0,
            'potential_savings': 0,
            'score_distribution': {
                'excellent': 0,  # 90+
                'great': 0,      # 80-89
                'good': 0,       # 70-79
                'fair': 0,       # 50-69
                'poor': 0        # <50
            }
        }
        
        if not items:
            return stats
        
        # Price statistics
        prices = [item.get('price', 0) for item in items if item.get('price', 0) > 0]
        if prices:
            stats['avg_price'] = statistics.mean(prices)
            stats['median_price'] = statistics.median(prices)
            stats['min_price'] = min(prices)
            stats['max_price'] = max(prices)
        
        # Deal score statistics
        scores = [item.get('deal_score', 0) for item in items]
        if scores:
            stats['avg_deal_score'] = statistics.mean(scores)
            stats['best_deal_score'] = max(scores)
        
        # Count deals by threshold
        stats['deals_count'] = len([item for item in items if item.get('deal_score', 0) >= threshold])
        
        # Calculate potential savings
        total_savings = 0
        for item in items:
            score = item.get('deal_score', 0)
            if score >= threshold:
                avg_price = item.get('avg_price', 0)
                price = item.get('price', 0)
                if avg_price > price > 0:
                    total_savings += (avg_price - price)
        
        stats['potential_savings'] = total_savings
        
        # Score distribution
        for item in items:
            score = item.get('deal_score', 0)
            if score >= 90:
                stats['score_distribution']['excellent'] += 1
            elif score >= 80:
                stats['score_distribution']['great'] += 1
            elif score >= 70:
                stats['score_distribution']['good'] += 1
            elif score >= 50:
                stats['score_distribution']['fair'] += 1
            else:
                stats['score_distribution']['poor'] += 1
        
        return stats
        
    def _find_comparison_groups(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Find groups of similar items for comparison"""
        comparisons = {}
        
        # Group by similarity
        groups = defaultdict(list)
        
        for item in items:
            # Create a normalized title key
            title = item.get('title', '').lower()
            
            # Extract key terms
            words = re.findall(r'\b[\w]+\b', title)
            significant_words = []
            
            for word in words:
                if len(word) > 3:
                    significant_words.append(word)
            
            if len(significant_words) >= 2:
                # Use first 3 significant words as key
                key = ' '.join(significant_words[:3])
                groups[key].append(item)
        
        # Keep only groups with 2+ items
        for key, group_items in groups.items():
            if len(group_items) >= 2:
                # Sort by price and limit
                sorted_items = sorted(
                    group_items,
                    key=lambda x: x.get('price', float('inf'))
                )
                display_key = key.title()
                comparisons[display_key] = sorted_items[:5]
        
        return comparisons
        
    def get_deal_summary(self, item: Dict) -> str:
        """Get a human-readable deal summary for an item"""
        score = item.get('deal_score', 0)
        price = item.get('price', 0)
        avg_price = item.get('avg_price', 0)
        factors = item.get('deal_factors', {})
        
        lines = []
        
        # Overall verdict
        if score >= 90:
            lines.append("🔥 EXCELLENT DEAL!")
        elif score >= 80:
            lines.append("⭐ Great Deal")
        elif score >= 70:
            lines.append("👍 Good Deal")
        elif score >= 50:
            lines.append("📊 Fair Price")
        else:
            lines.append("⚠️ Above Average")
        
        lines.append(f"Deal Score: {score}/100")
        
        # Price comparison
        if avg_price > 0 and price > 0:
            diff = avg_price - price
            if diff > 0:
                lines.append(f"💰 {diff:,.0f} kr below average!")
            else:
                lines.append(f"💸 {abs(diff):,.0f} kr above average")
        
        # Key factors
        details = factors.get('details', {})
        
        if details.get('condition'):
            lines.append(f"✨ Condition: {details['condition']}")
        
        if details.get('seller_type'):
            lines.append(f"👤 Seller: {details['seller_type']}")
        
        if details.get('posted'):
            lines.append(f"📅 Listed: {details['posted']}")
        
        return '\n'.join(lines)


def analyze_price_trend(prices: List[float]) -> Dict:
    """Analyze price trend from historical data"""
    if len(prices) < 2:
        return {'trend': 'insufficient_data', 'change': 0}
    
    # Calculate trend
    first_half = prices[:len(prices)//2]
    second_half = prices[len(prices)//2:]
    
    avg_first = sum(first_half) / len(first_half) if first_half else 0
    avg_second = sum(second_half) / len(second_half) if second_half else 0
    
    if avg_first > 0:
        change_pct = ((avg_second - avg_first) / avg_first) * 100
    else:
        change_pct = 0
    
    if change_pct < -5:
        trend = 'decreasing'
    elif change_pct > 5:
        trend = 'increasing'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'change_percent': change_pct,
        'avg_first_period': avg_first,
        'avg_second_period': avg_second,
        'min': min(prices),
        'max': max(prices),
        'current': prices[-1] if prices else 0
    }
