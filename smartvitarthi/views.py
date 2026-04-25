from django.shortcuts import render
from django.http import JsonResponse
from .brain import financial_brain,financial_brain_v2


def advisor_api(request):
    salary = int(request.GET.get('salary', 0))
    expenses = int(request.GET.get('expenses', 0))

    result = financial_brain(salary, expenses)

    return JsonResponse(result)

def advisor_page(request):
    session = request.session
    if "step" not in session:
        session["step"] = "ask_salary"
    return render(request, 'smartvitarthi/chat.html')

def handle_conversation(user_input, session):

    step = session.get("step", "ask_salary")

    if step == "ask_salary":
        salary = safe_int(user_input)

        if salary is None:
            return "Please valid salary number enter karo (jaise 10000)"
        
        session["salary"] = int(user_input)
        session["step"] = "ask_expenses"
        return "Aapke monthly expenses kitne hai?"

    elif step == "ask_expenses":
        session["expenses"] = int(user_input)
        session["step"] = "ask_goal"
        return "Aapka goal kya hai? (saving / investment / loan)"

    elif step == "ask_goal":
        session["goal"] = user_input
        session["step"] = "done"

        result = financial_brain_v2(session)
        return f"Result: {result}"
    
def chat_api(request):

    user_input = request.GET.get("message", "")
    session = request.session
    if not user_input:
        return JsonResponse({"reply": "Please kuch input do 😅"})
    # Initialize step
    if "step" not in session:
        session["step"] = "ask_salary"
        return JsonResponse({"reply": "Aapki monthly salary kya hai?"})

    # Continue conversation
    reply = handle_conversation(user_input, session)

    return JsonResponse({"reply": reply})
def safe_int(value):
    try:
        return int(value)
    except:
        return None