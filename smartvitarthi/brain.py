def financial_brain(salary, expenses=0):

    if salary <= 10000:
        return {
            "category": "low_income",
            "needs": int(0.7 * salary),
            "savings": int(0.2 * salary),
            "personal": int(0.1 * salary),
            "advice": [
                "Emergency fund pe focus karo",
                "Expenses track karo",
                "Risky investments avoid karo"
            ]
        }

    elif salary <= 30000:
        return {
            "category": "mid_income",
            "needs": int(0.6 * salary),
            "savings": int(0.25 * salary),
            "investment": int(0.15 * salary),
            "advice": [
                "SIP start karo",
                "Insurance lo",
                "Savings increase karo"
            ]
        }

    else:
        return {
            "category": "high_income",
            "needs": int(0.5 * salary),
            "investment": int(0.3 * salary),
            "wealth": int(0.2 * salary),
            "advice": [
                "Diversify portfolio",
                "Tax planning karo",
                "Long term investment karo"
            ]
        }
def financial_brain_v2(data):

    salary = data.get("salary", 0)
    expenses = data.get("expenses", 0)
    goal = data.get("goal", "saving")
    risk = data.get("risk", "low")

    savings = salary - expenses

    response = {}

    # Basic survival check
    if savings <= 0:
        response["status"] = "critical"
        response["advice"] = [
            "Aapka expense salary se zyada hai",
            "Immediate expense control karo",
            "Savings possible nahi hai abhi"
        ]
        return response

    # Emergency fund logic
    if savings < 0.2 * salary:
        response["priority"] = "emergency_fund"

    # Goal based planning
    if goal == "saving":
        response["plan"] = "Save 20% income monthly"

    elif goal == "investment":
        if risk == "low":
            response["plan"] = "FD / Safe SIP"
        elif risk == "medium":
            response["plan"] = "Balanced SIP"
        else:
            response["plan"] = "Equity SIP"

    elif goal == "loan":
        response["plan"] = "Minimize EMI < 30% salary"

    response["savings"] = savings

    return response