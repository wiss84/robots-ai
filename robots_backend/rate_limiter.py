import asyncio
import time
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os
from datetime import datetime as dt

logger = logging.getLogger(__name__)

@dataclass
class RequestRecord:
    """Record of a single request with timestamp and token count."""
    timestamp: float
    tokens: int

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
    requests_today: int = 0
    last_day_reset: float = field(default_factory=time.time)
    request_records: List[RequestRecord] = field(default_factory=list)
    
    @property
    def requests_this_minute(self) -> int:
        """Calculate requests in the last 60 seconds."""
        current_time = time.time()
        cutoff_time = current_time - 60
        return sum(1 for record in self.request_records if record.timestamp > cutoff_time)
    
    @property
    def tokens_this_minute(self) -> int:
        """Calculate tokens in the last 60 seconds."""
        current_time = time.time()
        cutoff_time = current_time - 60
        return sum(record.tokens for record in self.request_records if record.timestamp > cutoff_time)

class GeminiRateLimiter:
    """
    Advanced rate limiter for Gemini API with model switching and delay management.
    """
    
    def __init__(self):
        # Define model limits based on the task requirements
        self.model_limits = {
            "gemini-2.5-flash-lite-preview-06-17": ModelLimits(
                requests_per_minute=15,
                tokens_per_minute=250_000,
                requests_per_day=1000,
                model_name="gemini-2.5-flash-lite-preview-06-17"
            ),
            "gemini-2.5-flash-lite-preview-09-2025": ModelLimits(
                requests_per_minute=15,
                tokens_per_minute=250_000,
                requests_per_day=1000,
                model_name="gemini-2.5-flash-lite-preview-09-2025"
            ),
            "gemini-2.0-flash-lite": ModelLimits(
                requests_per_minute=30,
                tokens_per_minute=1_000_000,
                requests_per_day=200,
                model_name="gemini-2.0-flash-lite"
            ),
            "gemini-2.0-flash-lite-001": ModelLimits(
                requests_per_minute=30,
                tokens_per_minute=1_000_000,
                requests_per_day=200,
                model_name="gemini-2.0-flash-lite"
            ),
            "gemini-2.5-flash-lite": ModelLimits(
                requests_per_minute=10,
                tokens_per_minute=250_000,
                requests_per_day=1000,
                model_name="gemini-2.5-flash-lite"
            ),
            "gemini-2.5-flash": ModelLimits(
                requests_per_minute=10,
                tokens_per_minute=250_000,
                requests_per_day=250,
                model_name="gemini-2.5-flash"
            )
        }
        
        # Model priority order (primary -> secondary -> tertiary)
        self.model_priority = [
            "gemini-2.5-flash-lite-preview-06-17",
            "gemini-2.5-flash-lite-preview-09-2025",            
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash-lite-001", 
            "gemini-2.5-flash-lite",
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
                        # Handle timestamp conversion with backward compatibility
                        last_day_reset = self._parse_timestamp(usage_data.get('last_day_reset', time.time()))

                        # Reset daily counters if it's a new day
                        last_day = dt.fromtimestamp(last_day_reset)
                        if dt.now().date() > last_day.date():
                            usage_data['requests_today'] = 0
                            last_day_reset = time.time()

                        # Load request records from stored timestamps
                        request_records = []
                        stored_records = usage_data.get('request_records', [])
                        current_time = time.time()
                        cutoff_time = current_time - 60  # Only keep records from last 60 seconds
                        
                        for record_data in stored_records:
                            timestamp = self._parse_timestamp(record_data.get('timestamp', 0))
                            tokens = record_data.get('tokens', 0)
                            # Only keep recent records
                            if timestamp > cutoff_time:
                                request_records.append(RequestRecord(timestamp=timestamp, tokens=tokens))

                        # Update usage data
                        self.usage[model_name] = ModelUsage(
                            requests_today=usage_data.get('requests_today', 0),
                            last_day_reset=last_day_reset,
                            request_records=request_records
                        )

                # Force save to update format
                self._save_usage_data()

        except Exception as e:
            logger.warning(f"Could not load usage data: {e}")

    def _parse_timestamp(self, timestamp_value):
        """Parse timestamp value, handling both Unix float and ISO string formats."""
        if isinstance(timestamp_value, (int, float)):
            # Unix timestamp (backward compatibility)
            return float(timestamp_value)
        elif isinstance(timestamp_value, str):
            # ISO format string
            try:
                dt_obj = dt.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                return dt_obj.timestamp()
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp_value}")
                return time.time()
        else:
            # Fallback to current time
            return time.time()
    
    def _save_usage_data(self):
        """Save usage data to persistent storage."""
        try:
            usage_file = "rate_limiter_usage.json"
            data = {}
            for model_name, usage in self.usage.items():
                # Only save the last 20 request records to keep file size manageable
                recent_records = usage.request_records[-20:]
                
                data[model_name] = {
                    'requests_today': usage.requests_today,
                    'last_day_reset': dt.fromtimestamp(usage.last_day_reset).isoformat(),
                    'request_records': [
                        {
                            'timestamp': dt.fromtimestamp(record.timestamp).isoformat(),
                            'tokens': record.tokens
                        }
                        for record in recent_records
                    ]
                }

            with open(usage_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Could not save usage data: {e}")
    
    def _cleanup_old_records(self, model_name: str):
        """Remove request records older than 60 seconds."""
        usage = self.usage[model_name]
        current_time = time.time()
        cutoff_time = current_time - 60
        
        # Filter out old records
        usage.request_records = [
            record for record in usage.request_records 
            if record.timestamp > cutoff_time
        ]
    
    def _reset_daily_counter_if_needed(self, model_name: str):
        """Reset daily counter if a new day has started."""
        usage = self.usage[model_name]
        current_time = time.time()

        # Reset day counters
        last_day = dt.fromtimestamp(usage.last_day_reset)
        if dt.now().date() > last_day.date():
            print(f"🔄 Resetting daily counters for {model_name} - new day")
            usage.requests_today = 0
            usage.last_day_reset = current_time
    
    def _is_approaching_limit(self, model_name: str, estimated_tokens: int = 0) -> Tuple[bool, str]:
        """Check if we're approaching any rate limits."""
        self._cleanup_old_records(model_name)
        self._reset_daily_counter_if_needed(model_name)
        
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

    def _is_approaching_limit_no_reset(self, model_name: str, estimated_tokens: int = 0) -> Tuple[bool, str]:
        """Check if we're approaching any rate limits without cleaning up records."""
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
        self._reset_daily_counter_if_needed(model_name)
        limits = self.model_limits[model_name]
        usage = self.usage[model_name]
        return usage.requests_today >= limits.requests_per_day

    def _has_exceeded_daily_limit_no_reset(self, model_name: str) -> bool:
        """Check if daily limit has been exceeded without resetting counters."""
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
        # Check if current model has exceeded daily limit (don't reset counters here)
        if self._has_exceeded_daily_limit_no_reset(self.current_model):
            next_model = self._get_next_available_model()
            if next_model:
                old_model = self.current_model
                self.current_model = next_model
                logger.info(f"Switched from {old_model} to {self.current_model} due to daily limit")
                return self.current_model, f"Switched to {self.current_model} model due to daily usage limits on {old_model}. This conversation will be summarized to maintain context."
            else:
                # All models exhausted
                return self.current_model, "All models have reached their daily limits. Please try again tomorrow."

        # Check if we're approaching limits and need to delay (don't reset counters here)
        approaching, reason = self._is_approaching_limit_no_reset(self.current_model, estimated_tokens)

        if approaching:
            delay_message = f"Approaching rate limits ({reason}). Waiting {self.delay_when_approaching_limit} seconds to avoid exceeding limits..."
            logger.info(f"Delaying request: {reason}")
            await asyncio.sleep(self.delay_when_approaching_limit)
            return self.current_model, delay_message

        return self.current_model, None
    
    def record_request(self, model_name: str, tokens_used: int = 0):
        """Record a completed request and token usage."""
        self._cleanup_old_records(model_name)
        self._reset_daily_counter_if_needed(model_name)
        
        usage = self.usage[model_name]
        current_time = time.time()
        
        # Add new request record
        usage.request_records.append(RequestRecord(timestamp=current_time, tokens=tokens_used))
        usage.requests_today += 1
        
        # Keep only recent records (last 20)
        usage.request_records = usage.request_records[-20:]
        
        self._save_usage_data()
        
        logger.debug(f"Recorded request for {model_name}: {tokens_used} tokens. "
                    f"Usage: {usage.requests_this_minute}/min, {usage.requests_today}/day, {usage.tokens_this_minute} tokens/min")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics for all models."""
        stats = {}
        for model_name in self.model_limits.keys():
            # Clean up old records before getting stats
            self._cleanup_old_records(model_name)
            
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
            'last_updated': dt.now().isoformat()
        }
    
    def _is_quota_exceeded_error(self, error_response: str) -> bool:
        """Check if the API error indicates quota exceeded."""
        if not error_response:
            return False

        quota_indicators = [
            "ResourceExhausted: 429",
            "You exceeded your current quota",
            "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "limit: 200"
        ]
        return any(indicator.lower() in error_response.lower() for indicator in quota_indicators)

    def _are_all_models_exhausted(self) -> bool:
        """Check if all models have reached their daily limits."""
        for model_name, limits in self.model_limits.items():
            if not self._has_exceeded_daily_limit(model_name):
                return False
        return True

    def _get_conversation_history(self, agent_id: str, conversation_id: str) -> List[dict]:
        """Get conversation history from the specified agent's graph memory."""
        try:
            # Import here to avoid circular imports
            if agent_id == "coding":
                from agent_coding import graph
            elif agent_id == "finance":
                from agent_finance import graph
            elif agent_id == "news":
                from agent_news import graph
            elif agent_id == "coding-ask":
                from agent_coding_ask import graph
            elif agent_id == "realestate":
                from agent_realestate import graph
            elif agent_id == "travel":
                from agent_travel import graph
            elif agent_id == "image":
                from agent_image_generator import graph
            elif agent_id == "shopping":
                from agent_shopping import graph
            elif agent_id == "games":
                from agent_games import graph
            else:
                return []

            # Get conversation history from the graph's memory
            config = {"configurable": {"thread_id": conversation_id}}
            try:
                # Try to get the current state to extract messages
                state = graph.get_state(config)
                if state and hasattr(state, 'values') and 'messages' in state.values:
                    messages = state.values['messages']
                    # Convert messages to dict format for summarization
                    formatted_messages = []
                    for msg in messages:
                        if hasattr(msg, 'type') and msg.type == 'human':
                            formatted_messages.append({
                                'role': 'user',
                                'content': msg.content if hasattr(msg, 'content') else str(msg)
                            })
                        elif hasattr(msg, 'type') and msg.type == 'ai':
                            formatted_messages.append({
                                'role': 'assistant',
                                'content': msg.content if hasattr(msg, 'content') else str(msg)
                            })
                    return formatted_messages
            except Exception as e:
                logger.warning(f"Could not get conversation history for {agent_id}/{conversation_id}: {e}")
                return []

        except ImportError as e:
            logger.warning(f"Could not import graph for {agent_id}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error getting conversation history: {e}")
            return []

    def _summarize_conversation(self, messages: List[dict], previous_summary: str = "") -> str:
        """Summarize conversation using the summarization service."""
        try:
            import requests

            # Prepare the request for the summarization service
            summarize_request = {
                "previous_summary": previous_summary,
                "new_messages": messages[-10:]  # Only summarize last 10 messages to avoid token limits
            }

            # Call the summarization endpoint
            response = requests.post(
                "http://localhost:8000/summarize/rolling",
                json=summarize_request,
                timeout=30
            )

            if response.status_code == 200:
                summary_data = response.json()
                return summary_data.get('summary', '')
            else:
                logger.warning(f"Summarization service returned status {response.status_code}")
                return previous_summary

        except Exception as e:
            logger.warning(f"Could not summarize conversation: {e}")
            return previous_summary

    def record_request_with_error_handling(self, model_name: str, tokens_used: int = 0, api_error: str = None, agent_id: str = "", conversation_id: str = "") -> Tuple[str, Optional[str]]:
        """
        Record request with API error handling and potential model switching.

        Args:
            model_name: The model that was attempted
            tokens_used: Tokens used (0 if request failed)
            api_error: API error response string if request failed
            agent_id: Agent ID for conversation context
            conversation_id: Conversation ID for history retrieval

        Returns:
            Tuple of (actual_model_to_use, switch_message_or_none)
        """
        # Check if this is a quota exceeded error that should trigger model switching
        if api_error and self._is_quota_exceeded_error(api_error):
            logger.warning(f"Quota exceeded error detected for {model_name}: {api_error}")

            # CRITICAL: Check exhaustion status BEFORE marking current model as exhausted
            # This preserves the original state to distinguish between real exhaustion vs API issues
            all_models_were_exhausted_before = self._are_all_models_exhausted()

            # Mark this model as having reached its daily limit to trigger switching
            usage = self.usage[model_name]
            limits = self.model_limits[model_name]
            usage.requests_today = limits.requests_per_day  # Force daily limit reached

            # Force save the updated usage data
            self._save_usage_data()

            # Trigger model switch to next available model
            next_model = self._get_next_available_model()
            if next_model and next_model != self.current_model:
                old_model = self.current_model
                self.current_model = next_model

                # Get conversation context for summarization
                conversation_summary = ""
                if agent_id and conversation_id:
                    try:
                        # Get conversation history from the old model
                        messages = self._get_conversation_history(agent_id, conversation_id)
                        if messages:
                            # Summarize the conversation for context
                            conversation_summary = self._summarize_conversation(messages)
                            logger.info(f"Generated conversation summary for model switch ({len(messages)} messages)")
                        else:
                            logger.warning(f"No conversation history found for {agent_id}/{conversation_id}")
                    except Exception as e:
                        logger.warning(f"Could not summarize conversation for model switch: {e}")

                logger.info(f"API quota exceeded - switched from {old_model} to {next_model}")
                summary_info = f" Conversation summarized ({len(conversation_summary)} chars)." if conversation_summary else ""
                return next_model, f"API quota exceeded for {old_model}. Automatically switched to {next_model} for continued service.{summary_info}"

            # Now determine the real scenario based on the state BEFORE we started marking models
            if all_models_were_exhausted_before:
                # All models were already exhausted before this error - real quota exhaustion
                return self.current_model, "ALL_MODELS_EXHAUSTED"
            else:
                # Models weren't exhausted before - this is likely a temporary API issue
                return self.current_model, f"TEMPORARY_API_ISSUE:{model_name}"

        # For non-quota errors or successful requests, use standard recording
        self.record_request(model_name, tokens_used)
        return self.current_model, None

    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of tokens in text (4 characters ≈ 1 token)."""
        return max(len(text) // 4, 100)  # Minimum 100 tokens

# Global rate limiter instance
rate_limiter = GeminiRateLimiter()