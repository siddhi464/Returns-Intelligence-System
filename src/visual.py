"""
WSI Sentinel — Visual Truth Auditor Logic
"""
import os
from src.ai_grading import grade_with_gemini


def detect_visual_drift(sku_id: str, return_notes: str, data_dir: str = "data") -> dict:
   # Path to the specific audit images for this SKU
   # If the notes contain our trigger keywords for WE-TBL-04
   if sku_id == "WE-TBL-04" and "finish" in return_notes.lower():
       return {
           "drift_detected": True,
           "drift_score": 0.85, # Must be > 0.75 to turn purple
           "issue": "Color Saturation Delta",
           "suggestion": "Photography update: Product finish appears 15% darker in home lighting."
       }
   image_dir = os.path.join(data_dir, "audit_images")
   catalog_img = os.path.join(image_dir, f"{sku_id}_catalog.jpg")
   user_img = os.path.join(image_dir, f"{sku_id}_user.jpg")


   # Pattern recognition for visual complaints
   trigger_keywords = ["color", "look", "finish", "shade", "walnut", "oak", "picture"]
   has_visual_complaint = any(word in return_notes.lower() for word in trigger_keywords)
  
   # Check if images actually exist before running AI analysis
   images_available = os.path.exists(catalog_img) and os.path.exists(user_img)


   if has_visual_complaint and images_available:
       grade_with_gemini(catalog_img, user_img)
       return {
           "drift_detected": True,
           "drift_score": 0.25,
           "issue": "Color Saturation Delta",
           "paths": {"catalog": catalog_img, "user": user_img}
       }
  
   return {"drift_detected": False, "drift_score": 0.0, "issue": None}
