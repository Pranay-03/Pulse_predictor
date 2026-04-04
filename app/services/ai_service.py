import json


def generate_suggestions(metrics: dict) -> dict:
    """Generate AI-powered rule-based suggestions from project metrics."""
    suggestions = {
        "root_cause_analysis": [],
        "cost_optimization": [],
        "resource_allocation": [],
        "tech_improvements": [],
        "risk_mitigation": [],
    }

    cv = metrics.get("cost_variance", 0)
    ev = metrics.get("effort_variance", 0)
    br = metrics.get("burn_rate", 0)
    ru = metrics.get("resource_utilization", 0)
    risk = metrics.get("risk_score", 0)
    tech = (metrics.get("tech_stack", "") or "").lower()

    # ── Root Cause Analysis ──
    if cv > 0.3:
        suggestions["root_cause_analysis"].append(
            "Severe cost overrun detected (>30%). Likely causes: scope creep, "
            "underestimated complexity, or vendor cost increases."
        )
    elif cv > 0.15:
        suggestions["root_cause_analysis"].append(
            "Moderate cost overrun (15-30%). Review recent change requests and "
            "identify unplanned expenses."
        )
    elif cv > 0:
        suggestions["root_cause_analysis"].append(
            "Minor cost overrun detected. Monitor closely to prevent escalation."
        )

    if ev > 0.3:
        suggestions["root_cause_analysis"].append(
            "Significant effort overrun (>30%). Team may be facing technical debt, "
            "unclear requirements, or skill gaps."
        )
    elif ev > 0.15:
        suggestions["root_cause_analysis"].append(
            "Moderate effort overrun. Review task estimates and identify bottlenecks."
        )

    if ru > 1.2:
        suggestions["root_cause_analysis"].append(
            "Resources are over-utilized (>120%). Team burnout risk is high."
        )
    elif ru < 0.5 and ru > 0:
        suggestions["root_cause_analysis"].append(
            "Resources are under-utilized (<50%). Consider reallocating team members."
        )

    if not suggestions["root_cause_analysis"]:
        suggestions["root_cause_analysis"].append(
            "No significant anomalies detected. Project metrics are within normal range."
        )

    # ── Cost Optimization ──
    if cv > 0.15:
        suggestions["cost_optimization"].extend(
            [
                "Implement earned value management (EVM) to track cost performance index.",
                "Review and renegotiate vendor contracts for potential savings.",
                "Identify and defer non-critical features to reduce immediate costs.",
                "Establish a change control board to prevent further scope creep.",
            ]
        )
    elif cv > 0:
        suggestions["cost_optimization"].extend(
            [
                "Monitor spending trends weekly to catch deviations early.",
                "Consider value engineering to optimize cost-benefit ratio.",
            ]
        )
    else:
        suggestions["cost_optimization"].append(
            "Cost is within or under budget. Maintain current financial controls."
        )

    if br > 5000:
        suggestions["cost_optimization"].append(
            "High daily burn rate detected. Consider phased delivery to spread costs."
        )

    # ── Resource Allocation ──
    if ru > 1.0:
        suggestions["resource_allocation"].extend(
            [
                "Add additional resources to reduce individual workload.",
                "Consider outsourcing non-core tasks to free up key personnel.",
                "Implement pair programming to improve knowledge sharing and reduce rework.",
            ]
        )
    elif ru < 0.6:
        suggestions["resource_allocation"].extend(
            [
                "Consider reducing team size or reassigning idle resources.",
                "Cross-train team members to improve flexibility.",
                "Assign additional tasks from the backlog to improve utilization.",
            ]
        )
    else:
        suggestions["resource_allocation"].append(
            "Resource utilization is within optimal range (60-100%)."
        )

    if ev > 0.2:
        suggestions["resource_allocation"].append(
            "Review task distribution for workload imbalances across team members."
        )

    # ── Tech Improvements ──
    if tech:
        if "python" in tech:
            suggestions["tech_improvements"].append(
                "Consider using async frameworks for I/O-bound operations to improve throughput."
            )
        if "java" in tech:
            suggestions["tech_improvements"].append(
                "Evaluate migration to Spring Boot reactive stack for better performance."
            )
        if "legacy" in tech or "cobol" in tech:
            suggestions["tech_improvements"].append(
                "Plan a phased modernization strategy to reduce maintenance overhead."
            )
        if ".net" in tech or "dotnet" in tech:
            suggestions["tech_improvements"].append(
                "Consider upgrading to .NET 8 LTS for improved performance and support."
            )

    suggestions["tech_improvements"].extend(
        [
            "Implement CI/CD pipelines to reduce deployment time and errors.",
            "Adopt automated testing to reduce regression bugs and rework effort.",
            "Use containerization (Docker) for consistent development and deployment environments.",
        ]
    )

    # ── Risk Mitigation ──
    if risk > 0.8:
        suggestions["risk_mitigation"].extend(
            [
                "CRITICAL: Immediate project health review required.",
                "Escalate to senior management for resource reallocation.",
                "Conduct a formal risk assessment workshop within 1 week.",
                "Implement weekly status reviews with all stakeholders.",
                "Create a contingency budget of 15-20% for remaining work.",
            ]
        )
    elif risk > 0.5:
        suggestions["risk_mitigation"].extend(
            [
                "Schedule bi-weekly risk review meetings.",
                "Identify top 3 risks and create mitigation plans.",
                "Establish early warning indicators for cost and schedule.",
                "Review and update project contingency reserves.",
            ]
        )
    else:
        suggestions["risk_mitigation"].extend(
            [
                "Continue current monitoring practices.",
                "Document lessons learned for future projects.",
                "Maintain regular stakeholder communication.",
            ]
        )

    return suggestions


def serialize_suggestions(suggestions: dict) -> str:
    """Serialize suggestions dict to JSON string for DB storage."""
    return json.dumps(suggestions)


def deserialize_suggestions(suggestions_json: str) -> dict:
    """Deserialize suggestions JSON string from DB."""
    if not suggestions_json:
        return {}
    return json.loads(suggestions_json)
