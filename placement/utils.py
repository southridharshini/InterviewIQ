import os
import re
import math
import random
import time
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings

# ----------------------------------------------------
# 1. Spam Detection Function
# ----------------------------------------------------
def is_spam_experience(text):
    if not text:
        return True, "No content provided."
        
    text_trimmed = text.strip()
    
    # Check 1: Too short
    if len(text_trimmed) < 25:
        return True, "Experience text is too short to be genuine."

    # Check 2: Repetitive word spam (e.g., "good good good good")
    words = text_trimmed.lower().split()
    if words and (words.count(words[0]) / len(words)) > 0.4:
        return True, "Repetitive word spam detected."

    # Check 3: Gibberish key-smash (e.g., "asdfghjjjjjjkkk")
    if re.search(r'(.)\1{4,}', text_trimmed):
        return True, "Gibberish or invalid characters detected."

    return False, "Valid"


# ----------------------------------------------------
# Helper Functions for Image Generation
# ----------------------------------------------------
def draw_star(draw, cx, cy, r_outer=10, r_inner=4, fill_color="#F59E0B"):
    """Draws a crisp 5-point vector star without depending on font glyphs."""
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill_color)


def draw_scalloped_seal(draw, center, r_outer, r_inner, num_points, fill_color, outline_color):
    """Draws a circular scalloped seal ring."""
    cx, cy = center
    points = []
    total_points = num_points * 2
    for i in range(total_points):
        angle = i * (2 * math.pi / total_points) - (math.pi / 2)
        r = r_outer if i % 2 == 0 else r_inner
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill_color, outline=outline_color)


def draw_qr_placeholder(draw, top_left, size=80):
    """Draws a vector QR code graphic placeholder."""
    x, y = top_left
    draw.rectangle([x, y, x + size, y + size], fill="#FFFFFF", outline="#000000", width=2)
    
    # Outer corners (position detection patterns)
    for cx, cy in [(x + 6, y + 6), (x + size - 26, y + 6), (x + 6, y + size - 26)]:
        draw.rectangle([cx, cy, cx + 20, cy + 20], fill="#000000")
        draw.rectangle([cx + 4, cy + 4, cx + 16, cy + 16], fill="#FFFFFF")
        draw.rectangle([cx + 7, cy + 7, cx + 13, cy + 13], fill="#000000")
    
    # Matrix pixels
    random.seed(42)
    for row in range(4, 12):
        for col in range(4, 12):
            if random.choice([True, False]):
                px = x + (col * 6)
                py = y + (row * 6)
                if not ((px < x + 30 and py < y + 30) or (px > x + size - 35 and py < y + 30) or (px < x + 30 and py > y + size - 35)):
                    draw.rectangle([px, py, px + 5, py + 5], fill="#000000")


# ----------------------------------------------------
# 2. LinkedIn Badge Image Generator
# ----------------------------------------------------
def create_linkedin_badge(student_name, company_name):
    """
    Generates a 1200x675 px LinkedIn Shareable Certificate & Badge Image.
    """
    width, height = 1200, 675
    
    # Canvas with Light Slate Background
    img = Image.new('RGB', (width, height), color='#F1F5F9')
    draw = ImageDraw.Draw(img)

    # Central Certificate Card Frame
    draw.rounded_rectangle([50, 40, 1150, 635], radius=20, fill='#FFFFFF', outline='#CBD5E1', width=2)

    # Right Bottom Geometric Accent
    draw.polygon([(820, 635), (1150, 430), (1150, 635)], fill='#2563EB')

    # Font Setup with safe fallbacks
    try:
        font_cert = ImageFont.truetype("arialbd.ttf", 32)
        font_name = ImageFont.truetype("arialbd.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_badge_head = ImageFont.truetype("arialbd.ttf", 15)
        font_badge_main = ImageFont.truetype("arialbd.ttf", 18)
    except IOError:
        try:
            font_cert = ImageFont.truetype("arial.ttf", 32)
            font_name = ImageFont.truetype("arial.ttf", 36)
            font_sub = ImageFont.truetype("arial.ttf", 22)
            font_badge_head = ImageFont.truetype("arial.ttf", 15)
            font_badge_main = ImageFont.truetype("arial.ttf", 18)
        except IOError:
            font_cert = font_name = font_sub = font_badge_head = font_badge_main = ImageFont.load_default()

    # ----------------------------------------------------
    # LEFT SECTION: CANDIDATE & CERTIFICATE DETAILS
    # ----------------------------------------------------
    # Profile Icon Frame
    avatar_cx, avatar_cy, avatar_r = 130, 125, 40
    draw.ellipse([avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r], fill='#DBEAFE', outline='#2563EB', width=2)
    draw.ellipse([avatar_cx - 14, avatar_cy - 24, avatar_cx + 14, avatar_cy + 4], fill='#2563EB')
    draw.ellipse([avatar_cx - 26, avatar_cy + 10, avatar_cx + 26, avatar_cy + 40], fill='#2563EB')

    # Certificate Header
    draw.text((190, 108), "CERTIFICATE OF CONTRIBUTION", fill='#1E293B', font=font_cert)

    # Student Name Display (Truncated if excessively long)
    display_name = str(student_name).upper() if student_name else "CANDIDATE NAME"
    if len(display_name) > 28:
        display_name = display_name[:25] + "..."
    draw.text((90, 215), display_name, fill='#0F172A', font=font_name)

    # Decorative Underlines
    draw.rectangle([90, 265, 520, 268], fill='#2563EB')
    draw.rectangle([90, 276, 440, 278], fill='#93C5FD')

    # Experience Info
    draw.text((90, 305), "Verified Interview Experience Contributor", fill='#475569', font=font_sub)
    draw.text((90, 340), f"Target Company: {str(company_name).upper()}", fill='#2563EB', font=font_sub)

    # QR Code Placeholder
    draw_qr_placeholder(draw, (90, 440), size=90)

    # Verification Badge Pill
    verif_x, verif_y = 210, 460
    draw.rounded_rectangle([verif_x, verif_y, verif_x + 290, verif_y + 50], radius=10, fill='#F0FDF4', outline='#16A34A', width=2)
    
    # Vector Checkmark inside green circle (avoids font box errors)
    draw.ellipse([verif_x + 12, verif_y + 12, verif_x + 38, verif_y + 38], fill='#16A34A')
    draw.line([(verif_x + 19, verif_y + 25), (verif_x + 24, verif_y + 30), (verif_x + 32, verif_y + 19)], fill='#FFFFFF', width=3)
    draw.text((verif_x + 48, verif_y + 13), "OFFICIALLY VERIFIED", fill='#15803D', font=font_sub)

    # ----------------------------------------------------
    # RIGHT SECTION: SCALLOPED BADGE & RIBBON
    # ----------------------------------------------------
    seal_cx, seal_cy = 930, 275

    # Background Ribbon
    ribbon_y1, ribbon_y2 = seal_cy - 25, seal_cy + 25
    draw.polygon([(740, ribbon_y1), (830, ribbon_y1), (830, ribbon_y2), (740, ribbon_y2), (760, seal_cy)], fill='#93C5FD')
    draw.polygon([(1030, ribbon_y1), (1120, ribbon_y1), (1100, seal_cy), (1120, ribbon_y2), (1030, ribbon_y2)], fill='#93C5FD')

    # Scalloped Outer Seal
    draw_scalloped_seal(draw, (seal_cx, seal_cy), r_outer=130, r_inner=120, num_points=26, fill_color='#1E3A8A', outline_color='#1E40AF')

    # White Inner Circle
    draw.ellipse([seal_cx - 105, seal_cy - 105, seal_cx + 105, seal_cy + 105], fill='#FFFFFF', outline='#1E3A8A', width=3)

    # Dotted Border Line inside Seal
    for a in range(0, 360, 12):
        rad = math.radians(a)
        px = seal_cx + 94 * math.cos(rad)
        py = seal_cy + 94 * math.sin(rad)
        draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill='#1E3A8A')

    # Seal Typography
    draw.text((seal_cx, seal_cy - 50), "INTERVIEW IQ", fill='#1E3A8A', font=font_badge_head, anchor="mm")
    
    # Middle Badge Tag
    draw.rectangle([seal_cx - 90, seal_cy - 18, seal_cx + 90, seal_cy + 18], fill='#1E3A8A')
    draw.text((seal_cx, seal_cy), "ALUMNI CONTRIBUTOR", fill='#FFFFFF', font=font_badge_main, anchor="mm")

    draw.text((seal_cx, seal_cy + 48), "VERIFIED EXPERIENCE", fill='#1E3A8A', font=font_badge_head, anchor="mm")

    # Vector 5-Star Rating (Gold vector stars)
    star_y = seal_cy + 150
    start_x = seal_cx - 50
    for i in range(5):
        draw_star(draw, cx=start_x + (i * 25), cy=star_y, r_outer=10, r_inner=4, fill_color='#F59E0B')

    # ----------------------------------------------------
    # SAVE IMAGE FILE
    # ----------------------------------------------------
    media_dir = os.path.join(settings.MEDIA_ROOT, 'badges')
    os.makedirs(media_dir, exist_ok=True)

    # Clean filename sanitization
    clean_student = re.sub(r'[^\w\-_]', '', str(student_name).replace(" ", "_").lower())
    clean_company = re.sub(r'[^\w\-_]', '', str(company_name).replace(" ", "_").lower())
    timestamp = int(time.time())
    
    filename = f"{clean_student}_{clean_company}_{timestamp}_badge.png"
    file_path = os.path.join(media_dir, filename)
    
    img.save(file_path, format='PNG', quality=95)

    return f"badges/{filename}"