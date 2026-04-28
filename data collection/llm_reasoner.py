import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class LLMReasoner:
    def __init__(self, model_name="gpt-4o-mini"):
        """
        Initializes the LLM client. Kept standard to easily swap models/providers later.
        """
        self.model_name = model_name
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_reasoning(self, role: str, name: str, html_snippet: str, is_accessible: bool, wcag_violations: str, wcag_passes: str) -> str:
        """
        Generates Chain-of-Thought reasoning explaining the WCAG compliance of an element.
        """
        prompt = f"""
You are an expert accessibility auditor. Analyze the provided HTML element and screen reader output.
Your task is to write out the logical reasoning for WHY this element passes or fails accessibility standards.

Element Role: {role}
Element Name: {name}
HTML Snippet: {html_snippet}

Heuristic Analysis Result:
Accessible: {is_accessible}
Violations: {wcag_violations}
Passes: {wcag_passes}

Instructions:
1. Write a step-by-step reasoning explaining the accessibility state of this element.
2. Explicitly mention the relevant WCAG guideline (what the guideline is).
3. Explain exactly how this specific HTML snippet is either violating the guideline or correctly following it.
4. Keep the reasoning concise but thorough. Do not use markdown formatting, just plain text.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional web accessibility auditor evaluating WCAG guidelines."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating reasoning: {str(e)}"
