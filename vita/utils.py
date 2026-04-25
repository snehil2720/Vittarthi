import openai

def generate_ai_summary(content):
    try:
        print("contentcontentcontent",content)
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize in 2 lines, engaging"},
                {"role": "user", "content": content[:2000]}
            ]
        )
        return response['choices'][0]['message']['content']

    except:
        print("excepttttt")
        words = content.split()
        return " ".join(words[:25]) + "..."