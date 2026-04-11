"""
AI condition grading: Gemini 1.5 Flash preferred; Groq fallback; heuristic if no API key.
Output: condition category, sentiment 0–1, key_issues[].
"""
from __future__ import annotations


import json
import os
import re
from typing import Any


def _heuristic_grade(return_note: str, transcript: str) -> dict[str, Any]:
   text = f"{return_note or ''} {transcript or ''}".lower()
   issues: list[str] = []
   if re.search(r"\b(scratch|dent|chip)\b", text):
       issues.append("Surface damage")
   if re.search(r"\b(colour|color|mismatch|different tone)\b", text):
       issues.append("Color mismatch")
   if re.search(r"\b(broken|snapped|crack|shattered)\b", text):
       issues.append("Structural damage")
   if re.search(r"\b(wobbly|loose|won't tighten)\b", text):
       issues.append("Stability or assembly")


   if re.search(r"\b(broken|snapped|shattered|destroyed)\b", text):
       category = "Damaged"
   elif re.search(r"\b(defect|faulty|won't work|doesn't work|missing part)\b", text):
       category = "Faulty"
   elif re.search(r"\b(new in box|unopened|never assembled|like new)\b", text):
       category = "New"
   elif re.search(r"\b(opened|assembled once|minor)\b", text):
       category = "Open-Box"
   else:
       category = "Open-Box"


   # Sentiment 0–1 from simple polarity
   neg = len(re.findall(r"\b(terrible|awful|hate|broken|disappointed|worst)\b", text))
   pos = len(re.findall(r"\b(love|great|perfect|good|fine|thanks)\b", text))
   raw = 0.5 + 0.15 * pos - 0.2 * neg
   sentiment = max(0.0, min(1.0, raw))


   return {
       "condition_grade": category,
       "sentiment_score": round(sentiment, 3),
       "key_issues": issues[:8] or ["No specific issues detected in text"],
   }




def _parse_llm_json(text: str) -> dict[str, Any] | None:
   text = text.strip()
   m = re.search(r"\{[\s\S]*\}", text)
   if not m:
       return None
   try:
       return json.loads(m.group())
   except json.JSONDecodeError:
       return None




def grade_with_gemini(return_note: str, transcript: str) -> dict[str, Any] | None:
   key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
   if not key:
       return None
   try:
       import google.generativeai as genai
       from google.generativeai.generative_models import GenerativeModel
   except ImportError:
       return None
   genai.configure(api_key=key)
   model = GenerativeModel("gemini-1.5-flash")
   prompt = """You are a returns analyst for Williams Sonoma / West Elm furniture.
Given the customer return note and support transcript, respond with ONLY valid JSON:
{
 "condition_grade": one of ["New","Like-New","Open-Box","Faulty","Damaged","Scrap"],
 "sentiment_score": number 0 to 1 (0 angry, 1 very positive),
 "key_issues": array of short strings e.g. "Leg joint failure"
}
Return note: """ + repr(return_note[:4000]) + """
Transcript: """ + repr(transcript[:4000])
   try:
       resp = model.generate_content(prompt)
       raw = (resp.text or "").strip()
       parsed = _parse_llm_json(raw)
       if not parsed:
           return None
       cg = str(parsed.get("condition_grade", "Open-Box"))
       ss = float(parsed.get("sentiment_score", 0.5))
       ss = max(0.0, min(1.0, ss))
       ki = parsed.get("key_issues") or []
       if not isinstance(ki, list):
           ki = [str(ki)]
       return {"condition_grade": cg, "sentiment_score": round(ss, 3), "key_issues": [str(x) for x in ki][:12]}
   except Exception:
       return None




def grade_with_groq(return_note: str, transcript: str) -> dict[str, Any] | None:
   key = os.getenv("GROQ_API_KEY")
   if not key:
       return None
   try:
       from groq import Groq  # type: ignore
   except ImportError:
       return None
   try:
       client = Groq(api_key=key)
       prompt = """Return JSON only: {"condition_grade":"New|Like-New|Open-Box|Faulty|Damaged|Scrap","sentiment_score":0-1,"key_issues":["..."]}
Note: """ + (return_note or "")[:3000] + "\nTranscript: " + (transcript or "")[:3000]
       r = client.chat.completions.create(
           model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
           messages=[{"role": "user", "content": prompt}],
           temperature=0.2,
       )
       raw = (r.choices[0].message.content or "").strip()
       parsed = _parse_llm_json(raw)
       if not parsed:
           return None
       cg = str(parsed.get("condition_grade", "Open-Box"))
       ss = max(0.0, min(1.0, float(parsed.get("sentiment_score", 0.5))))
       ki = parsed.get("key_issues") or []
       if not isinstance(ki, list):
           ki = [str(ki)]
       return {"condition_grade": cg, "sentiment_score": round(ss, 3), "key_issues": [str(x) for x in ki][:12]}
   except Exception:
       return None




def heuristic_grade(return_note: str, transcript: str) -> dict[str, Any]:
   return _heuristic_grade(return_note, transcript)




def grade_condition(return_note: str, transcript: str) -> dict[str, Any]:
   """Prefer Gemini, then Groq, then heuristic."""
   out = grade_with_gemini(return_note, transcript)
   if out:
       return out
   out = grade_with_groq(return_note, transcript)
   if out:
       return out
   return _heuristic_grade(return_note, transcript)
try:
   from PIL import Image
except ImportError:
   Image = None
def grade_image_with_gemini(sku_id: str, catalog_path: str, user_path: str) -> dict[str, Any] | None:
   """
   Multimodal AI: Compares catalog perfection vs. customer reality.
   Used for the AI Visual Truth Auditor feature.
   """
   key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
   if not key or not Image:
       return None
      
   try:
       import google.generativeai as genai
       from google.generativeai.generative_models import GenerativeModel
       genai.configure(api_key=key)
       model = GenerativeModel("gemini-1.5-flash")
      
       # Load images
       cat_img = Image.open(catalog_path)
       usr_img = Image.open(user_path)
      
       prompt = f"""
       You are a visual quality auditor for Williams-Sonoma furniture.
       Compare these two images of SKU: {sku_id}.
       Image 1: Professional Studio Catalog Photo.
       Image 2: Customer's Home Return Photo.
      
       Identify 'Visual Drift': Does the product look significantly different in terms of
       color saturation, wood finish tone, or texture due to misleading photography?
      
       Respond ONLY with valid JSON:
       {{
         "drift_detected": boolean,
         "drift_score": number 0 to 1,
         "issue": "Brief description of mismatch (e.g., Color Saturation Delta)",
         "suggestion": "Specific advice for photography team"
       }}
       """
      
       # Call Gemini with both images and text
       response = model.generate_content([prompt, cat_img, usr_img])
       parsed = _parse_llm_json(response.text)
      
       if not parsed:
           return None
          
       return {
           "drift_detected": bool(parsed.get("drift_detected", False)),
           "drift_score": float(parsed.get("drift_score", 0.0)),
           "issue": str(parsed.get("issue", "Unknown mismatch")),
           "suggestion": str(parsed.get("suggestion", "No suggestion provided"))
       }
   except Exception as e:
       print(f"[AI Auditor Error]: {e}")
       return None
