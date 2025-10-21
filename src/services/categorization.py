"""
Transaction Categorization and Pattern Learning Service

This service handles:
1. Pattern matching for auto-categorization
2. Learning new patterns from user edits
3. Suggesting improvements to transaction descriptions
"""

import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..db.models import TransactionPattern, Category


class CategorizationService:
    """Service for transaction categorization and pattern learning"""

    def __init__(self, db: Session):
        self.db = db

    def find_suggestions(self, original_description: str, reference: str = "") -> Dict:
        """
        Find suggestions for a transaction based on learned patterns.

        Args:
            original_description: Original transaction description
            reference: Transaction reference number

        Returns:
            Dict with suggested_description, category_id, confidence, pattern_matched
        """
        # Combine description and reference for pattern matching
        search_text = f"{original_description} {reference}".lower()

        # Find matching patterns ordered by confidence
        patterns = self.db.query(TransactionPattern).filter(
            TransactionPattern.confidence > 0.3  # Minimum confidence threshold
        ).order_by(TransactionPattern.confidence.desc()).all()

        best_match = None
        best_confidence = 0.0

        for pattern in patterns:
            matched = False

            if pattern.pattern_type == 'contains':
                if pattern.pattern_value.lower() in search_text:
                    matched = True

            elif pattern.pattern_type == 'starts_with':
                if search_text.startswith(pattern.pattern_value.lower()):
                    matched = True

            elif pattern.pattern_type == 'regex':
                try:
                    if re.search(pattern.pattern_value, search_text, re.IGNORECASE):
                        matched = True
                except re.error:
                    # Invalid regex, skip
                    continue

            elif pattern.pattern_type == 'reference_exact':
                if pattern.pattern_value.lower() == reference.lower():
                    matched = True

            if matched and pattern.confidence > best_confidence:
                best_match = pattern
                best_confidence = pattern.confidence

        if best_match:
            # Get category name if available
            category_name = None
            if best_match.category_id:
                category = self.db.query(Category).filter(
                    Category.id == best_match.category_id
                ).first()
                if category:
                    category_name = category.name

            return {
                'suggested_description': best_match.suggested_description,
                'suggested_category_id': best_match.category_id,
                'suggested_category_name': category_name,
                'confidence': best_match.confidence,
                'pattern_matched': best_match.pattern_value
            }

        return {
            'suggested_description': None,
            'suggested_category_id': None,
            'suggested_category_name': None,
            'confidence': 0.0,
            'pattern_matched': None
        }

    def learn_pattern(
        self,
        original_description: str,
        new_description: str,
        reference: str = "",
        category_id: Optional[int] = None
    ):
        """
        Learn a new pattern from user edit.

        This creates or updates patterns based on what changed.
        """
        # Determine what pattern to extract
        patterns_to_create = []

        # Strategy 1: If reference exists and changed description significantly, use reference
        if reference and len(reference) >= 6:
            patterns_to_create.append({
                'type': 'reference_exact',
                'value': reference,
                'description': new_description,
                'category_id': category_id
            })

        # Strategy 2: Extract key words from original that identify this type
        # Look for distinctive keywords (e.g., "MTN", "CHECKERS", merchant names)
        words = original_description.split()
        for word in words:
            word_clean = word.strip('*.,').upper()
            # If word is distinctive (5+ chars, alphanumeric, not common words)
            if (len(word_clean) >= 5 and
                any(c.isalpha() for c in word_clean) and
                word_clean not in ['PURCHASE', 'LOCAL', 'DEBIT', 'CREDIT']):

                patterns_to_create.append({
                    'type': 'contains',
                    'value': word_clean,
                    'description': new_description,
                    'category_id': category_id
                })
                break  # Only take first distinctive word

        # Create or update patterns
        for pattern_data in patterns_to_create:
            # Check if pattern already exists
            existing = self.db.query(TransactionPattern).filter(
                TransactionPattern.pattern_type == pattern_data['type'],
                TransactionPattern.pattern_value == pattern_data['value']
            ).first()

            if existing:
                # Update existing pattern
                existing.suggested_description = pattern_data['description']
                existing.category_id = pattern_data['category_id']
                existing.times_applied += 1
                existing.times_accepted += 1
                # Increase confidence (up to 1.0)
                existing.confidence = min(1.0, existing.confidence + 0.1)
            else:
                # Create new pattern
                new_pattern = TransactionPattern(
                    pattern_type=pattern_data['type'],
                    pattern_value=pattern_data['value'],
                    suggested_description=pattern_data['description'],
                    category_id=pattern_data['category_id'],
                    confidence=0.7,  # Start with medium confidence
                    times_applied=1,
                    times_accepted=1
                )
                self.db.add(new_pattern)

        self.db.commit()

    def apply_pattern_feedback(self, pattern_id: int, accepted: bool):
        """
        Update pattern confidence based on user accepting/rejecting suggestion.

        Args:
            pattern_id: ID of the pattern that was suggested
            accepted: Whether user accepted the suggestion
        """
        pattern = self.db.query(TransactionPattern).filter(
            TransactionPattern.id == pattern_id
        ).first()

        if pattern:
            pattern.times_applied += 1

            if accepted:
                pattern.times_accepted += 1
                # Increase confidence
                pattern.confidence = min(1.0, pattern.confidence + 0.05)
            else:
                # Decrease confidence
                pattern.confidence = max(0.0, pattern.confidence - 0.1)

            self.db.commit()

    def get_all_categories(self) -> List[Dict]:
        """Get all categories for display in UI"""
        categories = self.db.query(Category).order_by(Category.name).all()

        return [
            {
                'id': cat.id,
                'name': cat.name,
                'parent_id': cat.parent_id,
                'color': cat.color,
                'icon': cat.icon
            }
            for cat in categories
        ]

    def create_category(self, name: str, parent_id: Optional[int] = None,
                       color: Optional[str] = None, icon: Optional[str] = None) -> int:
        """Create a new category"""
        category = Category(
            name=name,
            parent_id=parent_id,
            color=color,
            icon=icon
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category.id

    def update_category(self, category_id: int, name: Optional[str] = None,
                       color: Optional[str] = None, icon: Optional[str] = None) -> bool:
        """Update an existing category"""
        category = self.db.query(Category).filter(Category.id == category_id).first()

        if not category:
            return False

        if name is not None:
            category.name = name
        if color is not None:
            category.color = color
        if icon is not None:
            category.icon = icon

        self.db.commit()
        return True

    def seed_default_categories(self):
        """Seed database with common transaction categories"""
        default_categories = [
            {"name": "Groceries", "color": "#4CAF50", "icon": "🛒"},
            {"name": "Fuel", "color": "#FF9800", "icon": "⛽"},
            {"name": "Utilities", "color": "#2196F3", "icon": "💡"},
            {"name": "Rent/Mortgage", "color": "#9C27B0", "icon": "🏠"},
            {"name": "Dining", "color": "#F44336", "icon": "🍽️"},
            {"name": "Entertainment", "color": "#E91E63", "icon": "🎬"},
            {"name": "Transport", "color": "#607D8B", "icon": "🚗"},
            {"name": "Healthcare", "color": "#009688", "icon": "🏥"},
            {"name": "Shopping", "color": "#FF5722", "icon": "🛍️"},
            {"name": "Salary/Income", "color": "#8BC34A", "icon": "💰"},
            {"name": "Business Expense", "color": "#795548", "icon": "💼"},
            {"name": "Bank Fees", "color": "#9E9E9E", "icon": "🏦"},
            {"name": "Other", "color": "#BDBDBD", "icon": "📋"},
        ]

        for cat_data in default_categories:
            existing = self.db.query(Category).filter(
                Category.name == cat_data["name"]
            ).first()

            if not existing:
                self.create_category(**cat_data)
