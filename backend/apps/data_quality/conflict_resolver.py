"""Conflict resolution engine for field-level data conflicts."""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .models import CanonicalFieldSource, DataConflictLog


class ConflictResolutionPolicy:
    """Per-field conflict resolution rules."""
    
    # Default policies
    POLICIES = {
        ('team', 'name'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['rapidapi_free', 'cricapi'],
        },
        ('team', 'country'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['rapidapi_free'],
        },
        ('team', 'short_name'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['cricbuzz2'],
        },
        ('team', 'logo_url'): {
            'strategy': 'most_recent',  # Use latest logo
            'priority_providers': ['rapidapi_free', 'cricbuzz2'],
        },
        
        ('player', 'name'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['rapidapi_free', 'cricapi'],
        },
        ('player', 'country'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['cricapi', 'rapidapi_free'],
        },
        ('player', 'role'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['cricbuzz2'],
        },
        ('player', 'image_url'): {
            'strategy': 'most_recent',
            'priority_providers': ['cricbuzz2'],
        },
        
        ('match', 'result_text'): {
            'strategy': 'most_recent',  # Use latest score update
            'priority_providers': ['cricbuzz2', 'rapidapi_free'],
        },
        ('match', 'winner'): {
            'strategy': 'highest_confidence',
            'priority_providers': ['cricbuzz2'],
        },
    }
    
    @classmethod
    def get_policy(cls, entity_type: str, field_name: str) -> Dict[str, Any]:
        """Get conflict resolution policy for entity/field pair."""
        key = (entity_type, field_name)
        return cls.POLICIES.get(key, {
            'strategy': 'highest_confidence',
            'priority_providers': [],
        })


class ConflictResolver:
    """Resolve field-level conflicts using configured policies."""
    
    @staticmethod
    def resolve(
        entity_type: str,
        entity_id: str,
        field_name: str,
        candidates: Dict[str, Tuple[Any, int, datetime]],
    ) -> Tuple[Any, str, Optional[int]]:
        """
        Resolve conflict between candidate values.
        
        Args:
            entity_type: 'team', 'player', 'match', 'venue'
            entity_id: ID of entity
            field_name: Field name
            candidates: {provider: (value, confidence_score, timestamp), ...}
        
        Returns:
            (resolved_value, resolution_strategy, winning_confidence_score)
        """
        policy = ConflictResolutionPolicy.get_policy(entity_type, field_name)
        strategy = policy.get('strategy', 'highest_confidence')
        priority_providers = policy.get('priority_providers', [])
        
        if not candidates:
            return None, strategy, None
        
        if len(candidates) == 1:
            provider, (value, confidence, _) = list(candidates.items())[0]
            return value, strategy, confidence
        
        # Route to strategy handler
        if strategy == 'highest_confidence':
            return ConflictResolver._resolve_by_confidence(
                candidates, priority_providers
            ), strategy, None
        elif strategy == 'most_recent':
            return ConflictResolver._resolve_by_timestamp(candidates), strategy, None
        elif strategy == 'majority_vote':
            return ConflictResolver._resolve_by_majority(candidates), strategy, None
        else:
            # Default: highest confidence
            return ConflictResolver._resolve_by_confidence(
                candidates, priority_providers
            ), strategy, None
    
    @staticmethod
    def _resolve_by_confidence(
        candidates: Dict[str, Tuple[Any, int, datetime]],
        priority_providers: List[str],
    ) -> Any:
        """Pick value from highest confidence source (with provider priority as tiebreaker)."""
        def sort_key(item):
            provider, (value, confidence, _) = item
            # Primary: highest confidence
            # Secondary: provider priority order (lower index = higher priority)
            priority_idx = (
                priority_providers.index(provider)
                if provider in priority_providers
                else len(priority_providers)
            )
            return (-confidence, priority_idx)
        
        winner_provider, (winner_value, _, _) = min(candidates.items(), key=sort_key)
        return winner_value
    
    @staticmethod
    def _resolve_by_timestamp(
        candidates: Dict[str, Tuple[Any, int, datetime]]
    ) -> Any:
        """Pick most recent value."""
        winner_provider, (winner_value, _, _) = max(
            candidates.items(),
            key=lambda item: item[1][2]  # timestamp
        )
        return winner_value
    
    @staticmethod
    def _resolve_by_majority(
        candidates: Dict[str, Tuple[Any, int, datetime]]
    ) -> Any:
        """Pick value that appears from most sources."""
        value_votes = {}
        for provider, (value, _, _) in candidates.items():
            value_str = str(value)
            value_votes[value_str] = value_votes.get(value_str, 0) + 1
        
        winner_value_str = max(value_votes.items(), key=lambda x: x[1])[0]
        # Find first candidate with this value
        for provider, (value, _, _) in candidates.items():
            if str(value) == winner_value_str:
                return value
        return None


class FieldSourceManager:
    """Manage canonical field sources with conflict detection."""
    
    @staticmethod
    def update_field_source(
        entity_type: str,
        entity_id: str,
        field_name: str,
        value: Any,
        provider: str,
        confidence_score: int,
        timestamp: datetime,
        raw_snapshot_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Update a field source, detecting conflicts if needed.
        
        Returns:
            (conflict_detected, conflicting_value)
        """
        obj, created = CanonicalFieldSource.objects.get_or_create(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            defaults={
                'source_provider': provider,
                'source_timestamp': timestamp,
                'confidence_score': confidence_score,
                'canonical_value': str(value) if value is not None else None,
                'raw_snapshot_id': raw_snapshot_id,
            }
        )
        
        if created:
            return False, None  # No conflict
        
        # Check for conflict
        existing_value = obj.canonical_value
        existing_provider = obj.source_provider
        
        if str(value) == existing_value and provider == existing_provider:
            # Same source, same value: no conflict
            obj.source_timestamp = timestamp
            obj.save()
            return False, None
        
        if str(value) != existing_value:
            # Different values: CONFLICT
            conflicting_values = obj.conflicting_values or {}
            conflicting_values[existing_value] = {
                'source_provider': existing_provider,
                'confidence': obj.confidence_score,
            }
            conflicting_values[str(value)] = {
                'source_provider': provider,
                'confidence': confidence_score,
            }
            obj.conflicting_values = conflicting_values
            
            # Auto-resolve using policy
            candidates = {
                existing_provider: (existing_value, obj.confidence_score, obj.source_timestamp),
                provider: (value, confidence_score, timestamp),
            }
            resolved_value, strategy, _ = ConflictResolver.resolve(
                entity_type, entity_id, field_name, candidates
            )
            
            obj.canonical_value = str(resolved_value) if resolved_value is not None else None
            obj.source_provider = provider if str(value) == str(resolved_value) else existing_provider
            obj.confidence_score = confidence_score if str(value) == str(resolved_value) else obj.confidence_score
            obj.source_timestamp = timestamp if str(value) == str(resolved_value) else obj.source_timestamp
            obj.save()
            
            # Log the conflict
            DataConflictLog.objects.create(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                conflicting_values=conflicting_values,
                resolution_strategy=strategy,
                resolved_value=str(resolved_value) if resolved_value is not None else None,
            )
            
            return True, existing_value
        
        # Same value, different provider: update source if higher confidence
        if confidence_score > obj.confidence_score:
            obj.source_provider = provider
            obj.confidence_score = confidence_score
            obj.source_timestamp = timestamp
            obj.raw_snapshot_id = raw_snapshot_id
            obj.save()
        
        return False, None
