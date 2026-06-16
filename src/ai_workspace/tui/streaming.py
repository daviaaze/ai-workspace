"""
Streaming LLM wrapper — intercepts LiteLLM calls to capture token-level streaming.

The problem: crewAI uses litellm.completion() internally, which returns the full
response at once. We want real-time token streaming into the TUI's AgentLane.

Solution: Monkey-patch litellm.completion with a wrapper that:
1. Calls the real litellm.completion with stream=True
2. Pushes each token chunk to the TUI queue in real-time
3. Returns the complete text as if it were a non-streaming call

This gives us token-by-token output without modifying crewAI.

Usage:
    from ai_workspace.tui.streaming import enable_streaming, disable_streaming
    
    queue = asyncio.Queue()
    enable_streaming(queue)
    # ... crewAI kickoff runs, tokens appear in queue ...
    disable_streaming()
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("aiw.tui.streaming")

# Reference to the original litellm.completion
_original_completion = None
_stream_queue = None
_stream_lock = threading.Lock()


def enable_streaming(queue: Any) -> None:
    """Enable token-level streaming for all litellm completion calls.
    
    Args:
        queue: An asyncio.Queue where token chunks will be pushed.
               Each chunk is a string like "  💬 processing..."
    """
    global _original_completion, _stream_queue
    
    with _stream_lock:
        if _original_completion is not None:
            return  # Already enabled
        
        try:
            import litellm
            _original_completion = litellm.completion
        except ImportError:
            logger.warning("litellm not available, streaming disabled")
            return
        
        _stream_queue = queue
        
        def streaming_completion(*args: Any, **kwargs: Any) -> Any:
            """Wrapped litellm.completion with token streaming."""
            q = _stream_queue
            if q is None or kwargs.get("stream") is True:
                # Already streaming or no queue — pass through
                return _original_completion(*args, **kwargs)
            
            # Enable streaming for this call
            kwargs["stream"] = True
            
            try:
                response = _original_completion(*args, **kwargs)
            except Exception:
                # Fallback: try without streaming
                kwargs["stream"] = False
                return _original_completion(*args, **kwargs)
            
            # Collect chunks and push to queue
            full_content = ""
            chunk_count = 0
            
            try:
                for chunk in response:
                    chunk_count += 1
                    
                    # Extract content from chunk
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            token = delta.content
                            full_content += token
                            
                            # Push to queue (every ~4th chunk for performance)
                            if q and chunk_count % 4 == 0:
                                try:
                                    q.put_nowait(f"  💬 {full_content[-200:]}")
                                except Exception:
                                    pass
                    
                    # Check for reasoning/thinking content
                    if hasattr(chunk, 'choices') and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            reasoning = delta.reasoning_content
                            if q:
                                try:
                                    q.put_nowait(f"  💭 {reasoning[:200]}")
                                except Exception:
                                    pass
            
            except Exception as e:
                logger.debug("Streaming chunk error: %s", e)
            
            # Push final content summary
            if q and full_content:
                try:
                    # Push the complete response as one message
                    # (individual tokens were streamed above)
                    pass  # Already streamed chunks
                except Exception:
                    pass
            
            # Return a mock response that looks like a non-streaming completion
            # crewAI expects response.choices[0].message.content
            return _make_mock_response(full_content, args, kwargs, chunk_count)
        
        litellm.completion = streaming_completion
        logger.info("Token streaming enabled")


def disable_streaming() -> None:
    """Restore the original litellm.completion."""
    global _original_completion, _stream_queue
    
    with _stream_lock:
        if _original_completion is None:
            return
        
        try:
            import litellm
            litellm.completion = _original_completion
        except ImportError:
            pass
        
        _original_completion = None
        _stream_queue = None
        logger.info("Token streaming disabled")


def _make_mock_response(
    content: str,
    args: tuple,
    kwargs: dict,
    chunk_count: int,
) -> Any:
    """Create a mock response object that looks like a litellm completion."""
    class MockDelta:
        def __init__(self, c):
            self.content = c
            self.role = "assistant"
            self.function_call = None
            self.tool_calls = None
    
    class MockChoice:
        def __init__(self, c):
            self.message = MockDelta(c)
            self.finish_reason = "stop"
            self.index = 0
    
    class MockUsage:
        def __init__(self):
            self.prompt_tokens = 0
            self.completion_tokens = max(1, len(content) // 4)
            self.total_tokens = self.prompt_tokens + self.completion_tokens
    
    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice(content)]
            self.usage = MockUsage()
            self.model = kwargs.get("model", "unknown")
            self.object = "chat.completion"
    
    return MockResponse()
