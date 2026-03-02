#!/usr/bin/env python3
"""Generate database schema diagram as PNG using PIL"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call(["pip3", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

# Colors
CORE_TABLE_BG = '#E8F4F8'
CORE_TABLE_BORDER = '#0F3460'
JUNCTION_YELLOW_BG = '#FFF3CD'
JUNCTION_YELLOW_BORDER = '#856404'
JUNCTION_RED_BG = '#FFE5E5'
JUNCTION_RED_BORDER = '#C33333'
JUNCTION_GREEN_BG = '#E5FFE5'
JUNCTION_GREEN_BORDER = '#2D862D'
JUNCTION_PURPLE_BG = '#F0E5FF'
JUNCTION_PURPLE_BORDER = '#6B2D86'
TEXT_COLOR = '#1a1a2e'
LINE_COLOR = '#555555'

# Create image
WIDTH = 2800
HEIGHT = 1600
img = Image.new('RGB', (WIDTH, HEIGHT), 'white')
draw = ImageDraw.Draw(img)

# Try to load a font
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    font_field = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
except:
    font_title = ImageFont.load_default()
    font_field = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_label = ImageFont.load_default()

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_table(x, y, width, height, title, fields, bg_color, border_color):
    """Draw a database table box"""
    bg = hex_to_rgb(bg_color)
    border = hex_to_rgb(border_color)

    # Draw table background
    draw.rectangle([x, y, x + width, y + height], fill=bg, outline=border, width=3)

    # Draw title background
    draw.rectangle([x, y, x + width, y + 30], fill=border, outline=border, width=2)

    # Draw title text
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = bbox[2] - bbox[0]
    draw.text((x + (width - title_width) // 2, y + 7), title, fill='white', font=font_title)

    # Draw fields
    field_y = y + 40
    for field in fields:
        draw.text((x + 10, field_y), field, fill=TEXT_COLOR, font=font_field)
        field_y += 20

def draw_arrow(x1, y1, x2, y2, color='#555555', style='solid', label='', label_pos='mid'):
    """Draw an arrow between two points"""
    rgb = hex_to_rgb(color)

    if style == 'dashed':
        # Draw dashed line
        dash_length = 10
        gap_length = 5
        total_length = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
        if total_length > 0:
            num_dashes = int(total_length / (dash_length + gap_length))
            for i in range(num_dashes):
                t1 = i * (dash_length + gap_length) / total_length
                t2 = (i * (dash_length + gap_length) + dash_length) / total_length
                dx1, dy1 = x1 + t1 * (x2 - x1), y1 + t1 * (y2 - y1)
                dx2, dy2 = x1 + t2 * (x2 - x1), y1 + t2 * (y2 - y1)
                draw.line([dx1, dy1, dx2, dy2], fill=rgb, width=2)
    else:
        draw.line([x1, y1, x2, y2], fill=rgb, width=2)

    # Draw arrowhead at end
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_length = 10
    arrow_angle = math.pi / 6

    p1_x = x2 - arrow_length * math.cos(angle - arrow_angle)
    p1_y = y2 - arrow_length * math.sin(angle - arrow_angle)
    p2_x = x2 - arrow_length * math.cos(angle + arrow_angle)
    p2_y = y2 - arrow_length * math.sin(angle + arrow_angle)

    draw.polygon([x2, y2, p1_x, p1_y, p2_x, p2_y], fill=rgb)

    # Draw label
    if label:
        if label_pos == 'mid':
            label_x, label_y = (x1 + x2) // 2, (y1 + y2) // 2
        elif label_pos == 'start':
            label_x, label_y = x1 + (x2 - x1) // 4, y1 + (y2 - y1) // 4
        else:  # 'end'
            label_x, label_y = x1 + 3 * (x2 - x1) // 4, y1 + 3 * (y2 - y1) // 4

        bbox = draw.textbbox((0, 0), label, font=font_label)
        label_width = bbox[2] - bbox[0]
        label_height = bbox[3] - bbox[1]

        # Draw white background for label
        padding = 3
        draw.rectangle([
            label_x - label_width//2 - padding,
            label_y - label_height//2 - padding,
            label_x + label_width//2 + padding,
            label_y + label_height//2 + padding
        ], fill='white', outline=rgb, width=1)

        draw.text((label_x - label_width//2, label_y - label_height//2), label, fill=rgb, font=font_label)

def draw_section_label(x, y, text):
    """Draw a section label"""
    bbox = draw.textbbox((0, 0), text, font=font_title)
    text_width = bbox[2] - bbox[0]
    draw.text((x - text_width // 2, y), text, fill=CORE_TABLE_BORDER, font=font_title)

# Layout with clear sections - IMPROVED to reduce arrow crossing
# Section 1: Core tables (left column) - MOVED roles next to users
CORE_X = 80
users_pos = (CORE_X, 100, 320, 170)
roles_pos = (CORE_X, 300, 320, 110)  # Moved directly below users
companies_pos = (CORE_X, 450, 320, 130)
permissions_pos = (CORE_X, 620, 320, 90)

# Section 2: User-Company junction tables (middle-left)
USER_COMPANY_X = 550
user_companies_pos = (USER_COMPANY_X, 100, 350, 90)
user_blocked_pos = (USER_COMPANY_X, 220, 350, 110)
user_granular_pos = (USER_COMPANY_X, 360, 350, 110)

# Section 3: User-Permission junction tables (middle-right)
USER_PERM_X = 1050
user_add_pos = (USER_PERM_X, 100, 350, 90)
user_minus_pos = (USER_PERM_X, 220, 350, 90)

# Section 4: Company-Role-Permission junction tables (right)
COMPANY_X = 1550
role_perm_pos = (COMPANY_X, 300, 350, 90)
company_roles_pos = (COMPANY_X, 450, 350, 90)
company_perm_pos = (COMPANY_X, 620, 350, 90)

# Draw section labels
draw_section_label(CORE_X + 160, 50, "CORE TABLES")
draw_section_label(USER_COMPANY_X + 175, 50, "USER ↔ COMPANY LINKS")
draw_section_label(USER_PERM_X + 175, 50, "USER ↔ PERMISSION LINKS")
draw_section_label(COMPANY_X + 175, 50, "COMPANY/ROLE ↔ PERMISSION")

# Draw core tables
draw_table(users_pos[0], users_pos[1], users_pos[2], users_pos[3],
    "users",
    ["• PK id: SERIAL", "• role_id: FK → roles", "• notes: TEXT",
     "• authentik_sub: VARCHAR(200)", "• username: VARCHAR(200)", "• name: VARCHAR(200)"],
    CORE_TABLE_BG, CORE_TABLE_BORDER)

draw_table(roles_pos[0], roles_pos[1], roles_pos[2], roles_pos[3],
    "roles",
    ["• PK id: SERIAL", "• name: VARCHAR(120)", "• description: TEXT"],
    CORE_TABLE_BG, CORE_TABLE_BORDER)

draw_table(companies_pos[0], companies_pos[1], companies_pos[2], companies_pos[3],
    "companies",
    ["• PK id: SERIAL", "• name: VARCHAR(200)", "• parent_id: FK → companies", "• is_hierarchical: BOOLEAN"],
    CORE_TABLE_BG, CORE_TABLE_BORDER)

draw_table(permissions_pos[0], permissions_pos[1], permissions_pos[2], permissions_pos[3],
    "permissions",
    ["• PK id: SERIAL", "• name: VARCHAR(120)"],
    CORE_TABLE_BG, CORE_TABLE_BORDER)

# Draw User-Company junction tables
draw_table(user_companies_pos[0], user_companies_pos[1], user_companies_pos[2], user_companies_pos[3],
    "user_companies",
    ["• PK user_id: FK → users", "• PK company_id: FK → companies"],
    JUNCTION_YELLOW_BG, JUNCTION_YELLOW_BORDER)

draw_table(user_blocked_pos[0], user_blocked_pos[1], user_blocked_pos[2], user_blocked_pos[3],
    "user_blocked_companies",
    ["(blocks with descendants)", "• PK user_id: FK → users", "• PK company_id: FK → companies"],
    JUNCTION_RED_BG, JUNCTION_RED_BORDER)

draw_table(user_granular_pos[0], user_granular_pos[1], user_granular_pos[2], user_granular_pos[3],
    "user_granular_blocked_companies",
    ["(blocks without descendants)", "• PK user_id: FK → users", "• PK company_id: FK → companies"],
    JUNCTION_RED_BG, JUNCTION_RED_BORDER)

# Draw User-Permission junction tables
draw_table(user_add_pos[0], user_add_pos[1], user_add_pos[2], user_add_pos[3],
    "user_add_rights",
    ["• PK user_id: FK → users", "• PK permission_id: FK → permissions"],
    JUNCTION_GREEN_BG, JUNCTION_GREEN_BORDER)

draw_table(user_minus_pos[0], user_minus_pos[1], user_minus_pos[2], user_minus_pos[3],
    "user_minus_rights",
    ["• PK user_id: FK → users", "• PK permission_id: FK → permissions"],
    JUNCTION_GREEN_BG, JUNCTION_GREEN_BORDER)

# Draw Company/Role-Permission junction tables
draw_table(role_perm_pos[0], role_perm_pos[1], role_perm_pos[2], role_perm_pos[3],
    "role_permissions",
    ["• PK role_id: FK → roles", "• PK permission_id: FK → permissions"],
    JUNCTION_PURPLE_BG, JUNCTION_PURPLE_BORDER)

draw_table(company_roles_pos[0], company_roles_pos[1], company_roles_pos[2], company_roles_pos[3],
    "company_roles",
    ["• PK company_id: FK → companies", "• PK role_id: FK → roles"],
    JUNCTION_PURPLE_BG, JUNCTION_PURPLE_BORDER)

draw_table(company_perm_pos[0], company_perm_pos[1], company_perm_pos[2], company_perm_pos[3],
    "company_permissions",
    ["• PK company_id: FK → companies", "• PK permission_id: FK → permissions"],
    JUNCTION_PURPLE_BG, JUNCTION_PURPLE_BORDER)

# Draw relationships with clear arrows and labels - COMMENTED OUT (lines removed as requested)
# # users -> roles (direct FK) - NOW VERTICAL AND CLEAR!
# draw_arrow(CORE_X + 160, 270, CORE_X + 160, 300, CORE_TABLE_BORDER, label='N:1\nDirect FK', label_pos='mid')
#
# # users -> user_companies -> companies
# draw_arrow(CORE_X + 320, 150, USER_COMPANY_X, 140, JUNCTION_YELLOW_BORDER, label='1:N')
# draw_arrow(USER_COMPANY_X + 350, 150, CORE_X + 320, 500, JUNCTION_YELLOW_BORDER, label='N:1')
#
# # users -> user_blocked_companies -> companies
# draw_arrow(CORE_X + 320, 190, USER_COMPANY_X, 260, JUNCTION_RED_BORDER, 'dashed', label='1:N')
# draw_arrow(USER_COMPANY_X + 350, 265, CORE_X + 320, 515, JUNCTION_RED_BORDER, 'dashed', label='N:1')
#
# # users -> user_granular_blocked_companies -> companies
# draw_arrow(CORE_X + 320, 230, USER_COMPANY_X, 400, JUNCTION_RED_BORDER, 'dashed', label='1:N')
# draw_arrow(USER_COMPANY_X + 350, 410, CORE_X + 320, 530, JUNCTION_RED_BORDER, 'dashed', label='N:1')
#
# # users -> user_add_rights -> permissions
# draw_arrow(CORE_X + 320, 130, USER_PERM_X, 140, JUNCTION_GREEN_BORDER, label='1:N')
# draw_arrow(USER_PERM_X + 350, 150, CORE_X + 320, 670, JUNCTION_GREEN_BORDER, label='N:1')
#
# # users -> user_minus_rights -> permissions
# draw_arrow(CORE_X + 320, 170, USER_PERM_X, 260, JUNCTION_GREEN_BORDER, 'dashed', label='1:N')
# draw_arrow(USER_PERM_X + 350, 270, CORE_X + 320, 690, JUNCTION_GREEN_BORDER, 'dashed', label='N:1')
#
# # companies -> company_roles -> roles
# draw_arrow(CORE_X + 320, 480, COMPANY_X, 490, JUNCTION_PURPLE_BORDER, label='1:N')
# draw_arrow(COMPANY_X + 350, 340, CORE_X + 320, 350, JUNCTION_PURPLE_BORDER, label='N:1')
#
# # companies -> company_permissions -> permissions
# draw_arrow(CORE_X + 320, 560, COMPANY_X, 670, JUNCTION_PURPLE_BORDER, label='1:N')
# draw_arrow(COMPANY_X + 350, 670, CORE_X + 320, 670, JUNCTION_PURPLE_BORDER, label='N:1')
#
# # roles -> role_permissions -> permissions
# draw_arrow(CORE_X + 320, 350, COMPANY_X, 340, JUNCTION_PURPLE_BORDER, label='1:N')
# draw_arrow(COMPANY_X + 350, 350, CORE_X + 320, 660, JUNCTION_PURPLE_BORDER, label='N:1')
#
# # companies self-reference (parent_id)
# draw_arrow(CORE_X + 160, 580, CORE_X + 160, 450, CORE_TABLE_BORDER, 'dashed', label='parent_id')

# Add legend with better formatting
legend_x = 100
legend_y = 900
legend_box_width = 600
legend_box_height = 320

# Draw legend box
draw.rectangle([legend_x - 20, legend_y - 20, legend_x + legend_box_width, legend_y + legend_box_height],
               outline=hex_to_rgb(CORE_TABLE_BORDER), width=2)

draw.text((legend_x, legend_y), "LEGEND", fill=hex_to_rgb(CORE_TABLE_BORDER), font=font_title)

y_offset = legend_y + 35

# Color coding
draw.rectangle([legend_x, y_offset, legend_x + 20, y_offset + 20],
               fill=hex_to_rgb(CORE_TABLE_BG), outline=hex_to_rgb(CORE_TABLE_BORDER), width=2)
draw.text((legend_x + 30, y_offset + 2), "Core Tables (users, companies, roles, permissions)",
          fill=TEXT_COLOR, font=font_field)

y_offset += 35
draw.rectangle([legend_x, y_offset, legend_x + 20, y_offset + 20],
               fill=hex_to_rgb(JUNCTION_YELLOW_BG), outline=hex_to_rgb(JUNCTION_YELLOW_BORDER), width=2)
draw.text((legend_x + 30, y_offset + 2), "User ↔ Company: Regular assignments",
          fill=TEXT_COLOR, font=font_field)

y_offset += 35
draw.rectangle([legend_x, y_offset, legend_x + 20, y_offset + 20],
               fill=hex_to_rgb(JUNCTION_RED_BG), outline=hex_to_rgb(JUNCTION_RED_BORDER), width=2)
draw.text((legend_x + 30, y_offset + 2), "User ↔ Company: Blocks (with/without descendants)",
          fill=TEXT_COLOR, font=font_field)

y_offset += 35
draw.rectangle([legend_x, y_offset, legend_x + 20, y_offset + 20],
               fill=hex_to_rgb(JUNCTION_GREEN_BG), outline=hex_to_rgb(JUNCTION_GREEN_BORDER), width=2)
draw.text((legend_x + 30, y_offset + 2), "User ↔ Permission: Add/Minus rights",
          fill=TEXT_COLOR, font=font_field)

y_offset += 35
draw.rectangle([legend_x, y_offset, legend_x + 20, y_offset + 20],
               fill=hex_to_rgb(JUNCTION_PURPLE_BG), outline=hex_to_rgb(JUNCTION_PURPLE_BORDER), width=2)
draw.text((legend_x + 30, y_offset + 2), "Company/Role ↔ Permission: Default permissions",
          fill=TEXT_COLOR, font=font_field)

y_offset += 40
draw.line([legend_x, y_offset, legend_x + 40, y_offset], fill=hex_to_rgb(LINE_COLOR), width=2)
draw.text((legend_x + 50, y_offset - 8), "Solid line: Regular relationship",
          fill=TEXT_COLOR, font=font_field)

y_offset += 25
# Draw dashed line
for i in range(0, 40, 10):
    draw.line([legend_x + i, y_offset, legend_x + i + 5, y_offset],
              fill=hex_to_rgb(LINE_COLOR), width=2)
draw.text((legend_x + 50, y_offset - 8), "Dashed line: Special/blocking relationship",
          fill=TEXT_COLOR, font=font_field)

y_offset += 35
draw.text((legend_x, y_offset), "Cardinality:", fill=TEXT_COLOR, font=font_field)
y_offset += 20
draw.text((legend_x + 10, y_offset), "• N:1 = Many-to-One (many records → one record)",
          fill=TEXT_COLOR, font=font_small)
y_offset += 18
draw.text((legend_x + 10, y_offset), "• 1:N = One-to-Many (one record → many records)",
          fill=TEXT_COLOR, font=font_small)

# Add key information box
info_x = 800
info_y = 900
info_box_width = 1000
info_box_height = 320

draw.rectangle([info_x - 20, info_y - 20, info_x + info_box_width, info_y + info_box_height],
               outline=hex_to_rgb(CORE_TABLE_BORDER), width=2)

draw.text((info_x, info_y), "KEY RELATIONSHIPS EXPLAINED", fill=hex_to_rgb(CORE_TABLE_BORDER), font=font_title)

info_offset = info_y + 35
draw.text((info_x, info_offset), "1. USERS → ROLES (Direct FK, N:1):",
          fill=TEXT_COLOR, font=font_field)
info_offset += 22
draw.text((info_x + 20, info_offset), "• Each user has ONE role (or no role) via role_id column",
          fill=TEXT_COLOR, font=font_field)
info_offset += 18
draw.text((info_x + 20, info_offset), "• Many users can share the same role (e.g., 10 users with 'admin' role)",
          fill=TEXT_COLOR, font=font_field)

info_offset += 30
draw.text((info_x, info_offset), "2. USERS ↔ COMPANIES: Three types of relationships:",
          fill=TEXT_COLOR, font=font_field)
info_offset += 22
draw.text((info_x + 20, info_offset), "• user_companies: Regular assignments (user can access these companies)",
          fill=TEXT_COLOR, font=font_field)
info_offset += 18
draw.text((info_x + 20, info_offset), "• user_blocked_companies: Blocked WITH descendants",
          fill=TEXT_COLOR, font=font_field)
info_offset += 18
draw.text((info_x + 20, info_offset), "• user_granular_blocked_companies: Blocked WITHOUT descendants",
          fill=TEXT_COLOR, font=font_field)

info_offset += 30
draw.text((info_x, info_offset), "3. USERS ↔ PERMISSIONS: Permission overrides:",
          fill=TEXT_COLOR, font=font_field)
info_offset += 22
draw.text((info_x + 20, info_offset), "• user_add_rights: Grants additional permissions to specific users",
          fill=TEXT_COLOR, font=font_field)
info_offset += 18
draw.text((info_x + 20, info_offset), "• user_minus_rights: Removes permissions from specific users",
          fill=TEXT_COLOR, font=font_field)

info_offset += 30
draw.text((info_x, info_offset), "4. COMPANIES: Self-referencing FK (parent_id) creates hierarchy tree",
          fill=TEXT_COLOR, font=font_field)

# Add title
title_text = "Database Schema - Company & User Management System"
bbox = draw.textbbox((0, 0), title_text, font=font_title)
title_width = bbox[2] - bbox[0]
draw.text((WIDTH // 2 - title_width // 2, 10), title_text, fill=hex_to_rgb(CORE_TABLE_BORDER), font=font_title)

# Save image
output_path = 'docs/database-schema.png'
img.save(output_path, 'PNG')
print(f"Schema diagram generated: {output_path}")
