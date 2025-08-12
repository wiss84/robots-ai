import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class ModelLimits:
    """Rate limits for a specific model."""
    requests_per_minute: int
    tokens_per_minute: int
    requests_per_day: int
    model_name: str

@dataclass
class ModelUsage:
    """Current usage tracking for a model."""
    requests_this_minute: int = 0
    tokens_this_minute: int = 0
    requests_today: int = 0
    last_minute_reset: float = field(default_factory=time.time)
    last_day_reset: float = field(default_factory=time.time)
    request_timestamps: list = field(default_factory=list)

class GeminiRateLimiter:
    """
    Advanced rate limiter for Gemini API with model switching and delay management.
    """
    
    def __init__(self):
        # Define model limits based on the task requirements
        self.model_limits = {
            "gemini-2.0-flash-lite": ModelLimits(
                requests_per_minute=30,
                tokens_per_minute=1_000_000,
                requests_per_day=200,
                model_name="gemini-2.0-flash-lite"
            ),
            "gemini-2.5-flash-lite-preview-06-17": ModelLimits(
                requests_per_minute=15,
                tokens_per_minute=200_000,
                requests_per_day=1000,
                model_name="gemini-2.5-flash-lite-preview-06-17"
            ),
            "gemini-2.5-flash": ModelLimits(
                requests_per_minute=10,
                tokens_per_minute=250_000,
                requests_per_day=200,
                model_name="gemini-2.5-flash"
            )
        }
        
        # Model priority order (primary -> secondary -> tertiary)
        self.model_priority = [
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash-lite-preview-06-17", 
            "gemini-2.5-flash"
        ]
        
        # Current usage tracking
        self.usage: Dict[str, ModelUsage] = {
            model: ModelUsage() for model in self.model_limits.keys()
        }
        
        # Current active model
        self.current_model = self.model_priority[0]
        
        # Load persisted usage data
        self._load_usage_data()
        
        # Delay configuration
        self.delay_when_approaching_limit = 35  # seconds
        self.approach_threshold = 0.9  # 90% of limit
        
    def _load_usage_data(self):
        """Load usage data from persistent storage."""
        try:
            usage_file = "rate_limiter_usage.json"
            if os.path.exists(usage_file):
                with open(usage_file, 'r') as f:
                    data = json.load(f)
                    
                for model_name, usage_data in data.items():
                    if model_name in self.usage:
                        # Reset daily counters if it's a new day
                        last_day = datetime.fromtimestamp(usage_data.get('last_day_reset', 0))
                        if datetime.now().date() > last_day.date():
                            usage_data['requests_today'] = 0
                            usage_data['last_day_reset'] = time.time()
                        
                        # Reset minute counters if it's a new minute
                        if time.time() - usage_data.get('last_minute_reset', 0) >= 60:
                            usage_data['requests_this_minute'] = 0
                            usage_data['tokens_this_minute'] = 0
                            usage_data['last_minute_reset'] = time.time()
                            usage_data['request_timestamps'] = []
                        
                        self.usage[model_name] = ModelUsage(**usage_data)
                        
        except Exception as e:
            logger.warning(f"Could not load usage data: {e}")
    
    def _save_usage_data(self):
        """Save usage data to persistent storage."""
        try:
            usage_file = "rate_limiter_usage.json"
            data = {}
            for model_name, usage in self.usage.items():
                data[model_name] = {
                    'requests_this_minute': usage.requests_this_minute,
                    'tokens_this_minute': usage.tokens_this_minute,
                    'requests_today': usage.requests_today,
                    'last_minute_reset': usage.last_minute_reset,
                    'last_day_reset': usage.last_day_reset,
                    'request_timestamps': usage.request_timestamps[-10:]  # Keep last 10 timestamps
                }
            
            with open(usage_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save usage data: {e}")
    
    def _reset_counters_if_needed(self, model_name: str):
        """Reset minute and day counters if time periods have elapsed."""
        usage = self.usage[model_name]
        current_time = time.time()
        
        # Reset minute counters
        if current_time - usage.last_minute_reset >= 60:
            usage.requests_this_minute = 0
            usage.tokens_this_minute = 0
            usage.last_minute_reset = current_time
            usage.request_timestamps = []
        
        # Reset day counters
        last_day = datetime.fromtimestamp(usage.last_day_reset)
        if datetime.now().date() > last_day.date():
            usage.requests_today = 0
            usage.last_day_reset = current_time
    
    def _is_approaching_limit(self, model_name: str, estimated_tokens: int = 0) -> Tuple[bool, str]:
        """Check if we're approaching any rate limits."""
        self._reset_counters_if_needed(model_name)
        
        limits = self.model_limits[model_name]
        usage = self.usage[model_name]
        
        # Check requests per minute
        if usage.requests_this_minute >= limits.requests_per_minute * self.approach_threshold:
            return True, f"Approaching requests per minute limit ({usage.requests_this_minute}/{limits.requests_per_minute})"
        
        # Check tokens per minute
        if usage.tokens_this_minute + estimated_tokens >= limits.tokens_per_minute * self.approach_threshold:
            return True, f"Approaching tokens per minute limit ({usage.tokens_this_minute + estimated_tokens}/{limits.tokens_per_minute})"
        
        # Check requests per day
        if usage.requests_today >= limits.requests_per_day * self.approach_threshold:
            return True, f"Approaching requests per day limit ({usage.requests_today}/{limits.requests_per_day})"
        
        return False, ""
    
    def _has_exceeded_daily_limit(self, model_name: str) -> bool:
        """Check if daily limit has been exceeded."""
        self._reset_counters_if_needed(model_name)
        limits = self.model_limits[model_name]
        usage = self.usage[model_name]
        return usage.requests_today >= limits.requests_per_day
    
    def _get_next_available_model(self) -> Optional[str]:
        """Get the next available model that hasn't exceeded daily limits."""
        current_index = self.model_priority.index(self.current_model)
        
        for i in range(current_index + 1, len(self.model_priority)):
            model = self.model_priority[i]
            if not self._has_exceeded_daily_limit(model):
                return model
        
        return None
    
    async def check_and_wait_if_needed(self, estimated_tokens: int = 1000) -> Tuple[str, Optional[str]]:
        """
        Check rate limits and wait if needed. Returns (model_to_use, delay_message).
        
        Args:
            estimated_tokens: Estimated tokens for the upcoming request
            
        Returns:
            Tuple of (model_name, delay_message_or_none)
        """
        # Check if current model has exceeded daily limit
        if self._has_exceeded_daily_limit(self.current_model):
            next_model = self._get_next_available_model()
            if next_model:
                old_model = self.current_model
                self.current_model = next_model
                logger.info(f"Switched from {old_model} to {self.current_model} due to daily limit")
                return self.current_model, f"Switched to {self.current_model} model due to daily usage limits on {old_model}. This conversation will be summarized to maintain context."
            else:
                # All models exhausted
                return self.current_model, "All models have reached their daily limits. Please try again tomorrow."
        
        # Check if we're approaching limits and need to delay
        approaching, reason = self._is_approaching_limit(self.current_model, estimated_tokens)
        
        if approaching:
            delay_message = f"Approaching rate limits ({reason}). Waiting {self.delay_when_approaching_limit} seconds to avoid exceeding limits..."
            logger.info(f"Delaying request: {reason}")
            await asyncio.sleep(self.delay_when_approaching_limit)
            return self.current_model, delay_message
        
        return self.current_model, None
    
    def record_request(self, model_name: str, tokens_used: int = 0):
        """Record a completed request and token usage."""
        self._reset_counters_if_needed(model_name)
        
        usage = self.usage[model_name]
        usage.requests_this_minute += 1
        usage.requests_today += 1
        usage.tokens_this_minute += tokens_used
        usage.request_timestamps.append(time.time())
        
        # Keep only recent timestamps
        usage.request_timestamps = usage.request_timestamps[-20:]
        
        self._save_usage_data()
        
        logger.debug(f"Recorded request for {model_name}: {tokens_used} tokens. "
                    f"Usage: {usage.requests_this_minute}/min, {usage.requests_today}/day, {usage.tokens_this_minute} tokens/min")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics for all models."""
        stats = {}
        for model_name in self.model_limits.keys():
            self._reset_counters_if_needed(model_name)
            limits = self.model_limits[model_name]
            usage = self.usage[model_name]
            
            stats[model_name] = {
                'requests_per_minute': f"{usage.requests_this_minute}/{limits.requests_per_minute}",
                'tokens_per_minute': f"{usage.tokens_this_minute}/{limits.tokens_per_minute}",
                'requests_per_day': f"{usage.requests_today}/{limits.requests_per_day}",
                'is_current_model': model_name == self.current_model,
                'daily_limit_exceeded': self._has_exceeded_daily_limit(model_name)
            }
        
        return {
            'current_model': self.current_model,
            'models': stats,
            'last_updated': datetime.now().isoformat()
        }
    
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of tokens in text (4 characters ≈ 1 token)."""
        return max(len(text) // 4, 100)  # Minimum 100 tokens

# Global rate limiter instance
rate_limiter = GeminiRateLimiter()