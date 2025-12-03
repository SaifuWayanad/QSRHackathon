"""
Kitchen Management Model
Handles order assignment logic and kitchen mapping
"""

from datetime import datetime
from typing import Dict, List, Optional
import sqlite3

class KitchenManager:
    """Manages kitchen assignments and order routing"""
    
    # Kitchen mapping based on food categories
    KITCHEN_MAPPING = {
        'Burgers': 'main_kitchen',
        'Steaks': 'main_kitchen',
        'Grilled Items': 'grill',
        'Salads': 'prep_kitchen',
        'Appetizers': 'main_kitchen',
        'Main Course': 'main_kitchen',
        'Pasta': 'main_kitchen',
        'Pizza': 'pizza_kitchen',
        'Sandwiches': 'main_kitchen',
        'Soups': 'prep_kitchen',
        'Desserts': 'pastry_kitchen',
        'Beverages': 'bar',
        'Coffee': 'bar',
        'Juices': 'bar',
        'Smoothies': 'bar',
        'Other': 'general_kitchen'
    }
    
    # Kitchen details
    KITCHENS = {
        'main_kitchen': {
            'id': 'main_kitchen',
            'name': 'Main Kitchen',
            'icon': '👨‍🍳',
            'capacity': 15,
            'specialties': ['Burgers', 'Steaks', 'Appetizers', 'Main Course', 'Pasta', 'Sandwiches']
        },
        'grill': {
            'id': 'grill',
            'name': 'Grill Station',
            'icon': '🔥',
            'capacity': 8,
            'specialties': ['Grilled Items', 'Steaks']
        },
        'prep_kitchen': {
            'id': 'prep_kitchen',
            'name': 'Prep Kitchen',
            'icon': '🥗',
            'capacity': 10,
            'specialties': ['Salads', 'Soups', 'Fresh Items']
        },
        'pizza_kitchen': {
            'id': 'pizza_kitchen',
            'name': 'Pizza Station',
            'icon': '🍕',
            'capacity': 6,
            'specialties': ['Pizza']
        },
        'pastry_kitchen': {
            'id': 'pastry_kitchen',
            'name': 'Pastry Kitchen',
            'icon': '🧁',
            'capacity': 8,
            'specialties': ['Desserts', 'Pastries']
        },
        'bar': {
            'id': 'bar',
            'name': 'Bar',
            'icon': '🍹',
            'capacity': 12,
            'specialties': ['Beverages', 'Coffee', 'Juices', 'Smoothies']
        },
        'general_kitchen': {
            'id': 'general_kitchen',
            'name': 'General Kitchen',
            'icon': '🍴',
            'capacity': 20,
            'specialties': ['Other']
        }
    }
    
    # Status workflow
    STATUS_FLOW = [
        'pending',
        'preparing',
        'ready',
        'served',
        'completed'
    ]
    
    STATUS_LABELS = {
        'pending': '⏳ Pending',
        'preparing': '👨‍🍳 Preparing',
        'ready': '✓ Ready',
        'served': '🍽️ Served',
        'completed': '✅ Completed'
    }
    
    STATUS_COLORS = {
        'pending': '#FFA500',      # Orange
        'preparing': '#3498DB',    # Blue
        'ready': '#2ECC71',        # Green
        'served': '#9B59B6',       # Purple
        'completed': '#27AE60'     # Dark Green
    }
    
    @staticmethod
    def get_kitchen_for_item(category: str) -> str:
        """Get appropriate kitchen for a food category"""
        return KitchenManager.KITCHEN_MAPPING.get(category, 'general_kitchen')
    
    @staticmethod
    def get_kitchen_details(kitchen_id: str) -> Dict:
        """Get kitchen information"""
        return KitchenManager.KITCHENS.get(kitchen_id, KitchenManager.KITCHENS['general_kitchen'])
    
    @staticmethod
    def assign_order_items(order_data: Dict) -> Dict[str, List]:
        """
        Assign order items to appropriate kitchens
        Returns dict with kitchen_id as key and items as value
        """
        items_by_kitchen = {}
        
        for item in order_data.get('items', []):
            category = item.get('category_name', 'Other')
            kitchen_id = KitchenManager.get_kitchen_for_item(category)
            
            if kitchen_id not in items_by_kitchen:
                items_by_kitchen[kitchen_id] = []
            
            items_by_kitchen[kitchen_id].append({
                'id': item.get('id'),
                'name': item.get('food_name'),
                'category': category,
                'quantity': item.get('quantity'),
                'price': item.get('price'),
                'notes': item.get('notes', ''),
                'status': 'pending'
            })
        
        return items_by_kitchen
    
    @staticmethod
    def get_next_status(current_status: str) -> Optional[str]:
        """Get next status in workflow"""
        if current_status in KitchenManager.STATUS_FLOW:
            idx = KitchenManager.STATUS_FLOW.index(current_status)
            if idx + 1 < len(KitchenManager.STATUS_FLOW):
                return KitchenManager.STATUS_FLOW[idx + 1]
        return None
    
    @staticmethod
    def get_all_kitchens() -> List[Dict]:
        """Get all kitchen information"""
        return list(KitchenManager.KITCHENS.values())
