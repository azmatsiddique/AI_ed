# src/utils/tracers.py
"""Trace logging processor using non-blocking async log writing."""

import asyncio
import uuid
from agents import TracingProcessor, Trace, Span
from ..core.database import async_write_log


def make_trace_id(tag: str) -> str:
    """Return a trace ID incorporating UUIDv4: 'trace_<tag>_<uuid4_hex>'."""
    clean_tag = tag.lower().strip()
    return f"trace_{clean_tag}_{uuid.uuid4().hex}"


def _log_async(name: str, log_type: str, message: str) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_write_log(name, log_type, message))
    except RuntimeError:
        pass


class LogTracer(TracingProcessor):
    def get_name(self, trace_or_span: Trace | Span) -> str | None:
        trace_id = trace_or_span.trace_id
        parts = trace_id.split("_")
        if len(parts) >= 2:
            return parts[1]
        return None

    def on_trace_start(self, trace) -> None:
        name = self.get_name(trace)
        if name:
            _log_async(name, "trace", f"Started: {trace.name}")

    def on_trace_end(self, trace) -> None:
        name = self.get_name(trace)
        if name:
            _log_async(name, "trace", f"Ended: {trace.name}")

    def on_span_start(self, span) -> None:
        name = self.get_name(span)
        typ = span.span_data.type if span.span_data else "span"
        if name:
            message = "Started"
            if span.span_data:
                if span.span_data.type:
                    message += f" {span.span_data.type}"
                if hasattr(span.span_data, "name") and span.span_data.name:
                    message += f" {span.span_data.name}"
                if hasattr(span.span_data, "server") and span.span_data.server:
                    message += f" {span.span_data.server}"
            if span.error:
                message += f" {span.error}"
            _log_async(name, typ, message)

    def on_span_end(self, span) -> None:
        name = self.get_name(span)
        typ = span.span_data.type if span.span_data else "span"
        if name:
            message = "Ended"
            if span.span_data:
                if span.span_data.type:
                    message += f" {span.span_data.type}"
                if hasattr(span.span_data, "name") and span.span_data.name:
                    message += f" {span.span_data.name}"
                if hasattr(span.span_data, "server") and span.span_data.server:
                    message += f" {span.span_data.server}"
            if span.error:
                message += f" {span.error}"
            _log_async(name, typ, message)

    def force_flush(self) -> None:
        pass

    def shutdown(self) -> None:
        pass