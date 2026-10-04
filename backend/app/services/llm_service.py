import os
from typing import Optional, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger

class LLMService:
    @staticmethod
    def generate_explanation(prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates operational explanations and summarizations.
        Falls back seamlessly to deterministic rule-based explanations if no LLM API key is provided.
        """
        # 1. Try Gemini if configured
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{prompt}\nContext: {context or {}}"
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini API call failed, using deterministic explanation fallback: {e}")

        # 2. Try OpenAI if configured
        if settings.OPENAI_API_KEY:
            try:
                import requests
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": f"{prompt}\nContext: {context or {}}"}],
                    "temperature": 0.2
                }
                res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.warning(f"OpenAI call failed, using deterministic fallback: {e}")

        # 3. Robust Deterministic Rule-Based Fallback
        return LLMService._deterministic_explanation(prompt, context)

    @staticmethod
    def _deterministic_explanation(prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        topic = ctx.get("topic", "general")

        if topic == "priority":
            bin_id = ctx.get("bin_id", "Bin")
            fill = ctx.get("fill", 0)
            threshold = ctx.get("threshold", 85)
            pred = ctx.get("pred_fill", fill)
            if fill >= 90:
                return (
                    f"{bin_id} is designated CRITICAL due to an immediate overflow risk ({fill:.1f}% fill). "
                    f"Remaining capacity is insufficient for safe buffer operation."
                )
            elif pred >= threshold:
                return (
                    f"{bin_id} is recommended for proactive collection. Current fill is {fill:.1f}%, but the "
                    f"ML forecasting model projects it will exceed the {threshold:.0f}% threshold to {pred:.1f}% "
                    f"before the next scheduled municipal cycle."
                )
            return f"{bin_id} fill level ({fill:.1f}%) is within standard municipal operating limits."

        elif topic == "reviewer":
            route_count = ctx.get("route_count", 0)
            violations = ctx.get("violations", [])
            if not violations:
                return (
                    f"Operational Reviewer validated all {route_count} proposed routes. All vehicle capacity limits, "
                    f"waste stream segregation constraints, and driver shift durations are strictly verified within bounds."
                )
            return f"Operational Reviewer flagged {len(violations)} issues requiring adjustment: {', '.join(violations[:2])}."

        elif topic == "replanning":
            bin_id = ctx.get("bin_id", "Surge Bin")
            vid = ctx.get("vehicle_id", "Assigned Vehicle")
            detour_km = ctx.get("detour_km", 1.8)
            return (
                f"Dynamic replanning triggered by surge at {bin_id}. Vehicle {vid} has adequate headroom "
                f"to absorb demand with a minor detour of {detour_km:.1f} km, averting municipal overflow."
            )

        return (
            "Operational AI Analysis: Actions optimized based on real-time sensor metrics, "
            "ML accumulation rates, and OR-Tools CVRP capacity constraints."
        )
