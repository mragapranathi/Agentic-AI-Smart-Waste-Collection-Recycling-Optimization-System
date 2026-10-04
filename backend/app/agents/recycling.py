from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.agents.base import BaseAgent
from backend.app.services.recycling_service import RecyclingService
from backend.app.models.entities import Bin, Collection, SensorReading, RecyclingRecord
from backend.app.core.logging import logger


class RecyclingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Recycling & Segregation Agent",
            role="Guarantees circularity compliance, prevents cross-contamination, and tracks diversion rates"
        )

    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        analytics = RecyclingService.get_recycling_analytics(db, days=30)
        routes = state.get("routes", [])

        # ──────────────────────────────────────────────
        # A. SEGREGATION COMPLIANCE CHECK on proposed routes
        # ──────────────────────────────────────────────
        segregation_compliant = True
        segregation_warnings: List[str] = []
        for r in routes:
            route_waste_type = r.get("waste_type")
            for s in r.get("stops", []):
                stop_waste = s.get("waste_type")
                if stop_waste and route_waste_type and stop_waste != route_waste_type:
                    segregation_compliant = False
                    segregation_warnings.append(
                        f"Cross-stream violation: Bin {s['bin_id']} ({stop_waste}) "
                        f"on route {r['route_id']} ({route_waste_type})."
                    )

        # ──────────────────────────────────────────────
        # B. WASTE GENERATION ANALYSIS BY LOCATION / ZONE / TYPE / TIME
        # Tracks: high-generation, recurring overflow, underutilised, frequency patterns
        # ──────────────────────────────────────────────
        bins = db.query(Bin).filter(Bin.operational_status == "OPERATIONAL").all()

        by_waste_type: Dict[str, Dict] = {}
        high_generation_locations: List[Dict] = []
        overflow_locations: List[Dict] = []
        underutilized_bins: List[Dict] = []

        for b in bins:
            fill = b.current_fill_percent or 0.0
            wt = b.waste_type or "General"

            # Accumulate by waste type
            if wt not in by_waste_type:
                by_waste_type[wt] = {"count": 0, "avg_fill": 0.0, "total_fill": 0.0, "bins": []}
            by_waste_type[wt]["count"] += 1
            by_waste_type[wt]["total_fill"] += fill
            by_waste_type[wt]["bins"].append(b.bin_id)

            # High-generation locations: bins consistently near full
            if fill >= 80.0:
                high_generation_locations.append({
                    "bin_id": b.bin_id,
                    "location_name": b.location_name,
                    "waste_type": wt,
                    "current_fill_percent": round(fill, 1),
                    "capacity_liters": b.capacity_liters,
                    "insight": f"High-demand location at {fill:.1f}% fill; may need increased collection frequency."
                })

            # Recurring overflow locations: bins at or above threshold
            if fill >= (b.collection_threshold_percent or 85.0):
                overflow_locations.append({
                    "bin_id": b.bin_id,
                    "location_name": b.location_name,
                    "waste_type": wt,
                    "current_fill_percent": round(fill, 1),
                    "threshold": b.collection_threshold_percent,
                    "insight": f"Threshold exceeded at {fill:.1f}% (threshold {b.collection_threshold_percent:.0f}%)."
                })

            # Underutilised bins: bins with very low fill levels
            if fill <= 20.0:
                underutilized_bins.append({
                    "bin_id": b.bin_id,
                    "location_name": b.location_name,
                    "waste_type": wt,
                    "current_fill_percent": round(fill, 1),
                    "insight": "Low utilisation — consider relocating or reducing collection frequency."
                })

        # Average fill per waste type
        for wt, d in by_waste_type.items():
            d["avg_fill"] = round(d["total_fill"] / d["count"], 1) if d["count"] else 0.0
            del d["bins"]  # remove raw list for cleaner output

        # ──────────────────────────────────────────────
        # C. COLLECTION FREQUENCY PATTERNS
        # From completed collections in DB
        # ──────────────────────────────────────────────
        completed = db.query(Collection).filter(
            Collection.status.in_(["COLLECTED", "VERIFIED"])
        ).all()

        # Count collections per bin
        collections_per_bin: Dict[str, int] = {}
        for c in completed:
            collections_per_bin[c.bin_id] = collections_per_bin.get(c.bin_id, 0) + 1

        # Identify bins that are collected most frequently (top 5)
        freq_sorted = sorted(collections_per_bin.items(), key=lambda x: x[1], reverse=True)
        high_frequency_bins = [
            {"bin_id": bid, "collections": cnt, "insight": "High-frequency bin — review sizing or placement."}
            for bid, cnt in freq_sorted[:5]
        ]

        # ──────────────────────────────────────────────
        # D. IDENTIFY POOR SEGREGATION LOCATIONS from recycling records
        # ──────────────────────────────────────────────
        records = db.query(RecyclingRecord).all()
        poor_segregation_locations: List[Dict] = []
        if records:
            # Flag bins whose contamination rate exceeds 20%
            for rec in records:
                if rec.weight_kg > 0:
                    contamination_pct = (rec.contamination_weight_kg / rec.weight_kg) * 100.0
                    if contamination_pct > 20.0:
                        poor_segregation_locations.append({
                            "bin_id": rec.bin_id,
                            "waste_type": rec.waste_type,
                            "contamination_percent": round(contamination_pct, 1),
                            "insight": f"Contamination at {contamination_pct:.1f}% — segregation education needed."
                        })

        # ──────────────────────────────────────────────
        # Build reasoning summary
        # ──────────────────────────────────────────────
        reasoning = (
            f"Municipal recycling rate: {analytics['recycling_rate_percent']}%. "
            f"Segregation compliance on {len(routes)} proposed routes: "
            f"{'100% COMPLIANT' if segregation_compliant else f'VIOLATIONS ({len(segregation_warnings)})'}. "
            f"Identified {len(high_generation_locations)} high-generation locations, "
            f"{len(overflow_locations)} recurring overflow locations, "
            f"{len(underutilized_bins)} underutilised bins, "
            f"{len(poor_segregation_locations)} poor-segregation sites. "
            f"Waste-type breakdown: { {k: v['avg_fill'] for k, v in by_waste_type.items()} }."
        )

        logger.info(f"[RecyclingAgent] {reasoning}")

        return {
            "recycling_analytics": analytics,
            "segregation_compliant": segregation_compliant,
            "segregation_warnings": segregation_warnings,
            "waste_by_type_analysis": by_waste_type,
            "high_generation_locations": high_generation_locations[:20],
            "overflow_locations": overflow_locations[:20],
            "underutilized_bins": underutilized_bins[:20],
            "poor_segregation_locations": poor_segregation_locations[:10],
            "high_frequency_bins": high_frequency_bins,
        }, reasoning
