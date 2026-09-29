import random
import math
import pygame
import os
from urllib.request import urlopen
from io import BytesIO

# ============================================
# CASA-212 COCKPIT SIMULATOR - WITH REAL COCKPIT IMAGE
# ============================================
pygame.init()

WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CASA-212 Cockpit Simulator - Real Cockpit")
clock = pygame.time.Clock()

# Fonts
font_giant = pygame.font.SysFont("courier", 72, bold=True)
font_big = pygame.font.SysFont("courier", 48, bold=True)
font_med = pygame.font.SysFont("courier", 32, bold=True)
font_small = pygame.font.SysFont("courier", 22, bold=True)
font_tiny = pygame.font.SysFont("courier", 16, bold=True)

# ============================================
# LAYOUT ZONES
# ============================================
# Buồn lái thực tế (bên phải)
COCKPIT_X, COCKPIT_Y = 1050, 50
COCKPIT_W, COCKPIT_H = 860, 1000

# Kính buồn lái (phía bên trên buồn lái thực tế)
WINDSHIELD_X, WINDSHIELD_Y = COCKPIT_X + 50, COCKPIT_Y + 80
WINDSHIELD_W, WINDSHIELD_H = 760, 280

# Radar PFD 120° sector (bên trái)
RADAR_X, RADAR_Y = 20, 50
RADAR_W, RADAR_H = 1000, 980

# ============================================
# THỜI TIẾT
# ============================================
weather_modes = {
    "clear": {
        "name": "CLEAR",
        "sky_top": (95, 170, 255),
        "sky_bottom": (200, 230, 255),
        "mountain": (58, 80, 90),
        "mountain2": (36, 52, 60),
        "cloud": (255, 255, 255),
        "fog_alpha": 0,
        "rain": False,
        "storm": False,
    },
    "rain": {
        "name": "RAIN",
        "sky_top": (58, 78, 110),
        "sky_bottom": (155, 175, 200),
        "mountain": (52, 62, 74),
        "mountain2": (30, 38, 48),
        "cloud": (200, 215, 230),
        "fog_alpha": 30,
        "rain": True,
        "storm": False,
    },
    "storm": {
        "name": "STORM",
        "sky_top": (18, 22, 32),
        "sky_bottom": (62, 70, 90),
        "mountain": (42, 45, 50),
        "mountain2": (22, 25, 28),
        "cloud": (120, 130, 145),
        "fog_alpha": 55,
        "rain": True,
        "storm": True,
    },
    "fog": {
        "name": "FOG",
        "sky_top": (155, 165, 170),
        "sky_bottom": (215, 220, 220),
        "mountain": (110, 118, 118),
        "mountain2": (88, 92, 94),
        "cloud": (245, 245, 245),
        "fog_alpha": 150,
        "rain": False,
        "storm": False,
    },
}

current_weather = "clear"

# Clouds / Raindrops
clouds = []
for i in range(18):
    clouds.append({
        "x": random.randint(0, WINDSHIELD_W),
        "y": random.randint(20, 200),
        "w": random.randint(80, 180),
        "h": random.randint(25, 45),
        "speed": random.uniform(6, 18),
    })

raindrops = []
for i in range(150):
    raindrops.append({
        "x": random.randint(50, WINDSHIELD_W - 50),
        "y": random.randint(0, WINDSHIELD_H),
        "len": random.randint(6, 12),
        "speed": random.uniform(10, 25),
    })

# ============================================
# RADAR 120° SECTOR
# ============================================
radar_center_x = RADAR_X + RADAR_W // 2
radar_center_y = RADAR_Y + RADAR_H // 2
radar_radius = 280

# Quét từ -60° đến +60° (120° total)
radar_scan_angle = -60
radar_scan_direction = 1
radar_scan_speed = 1.8

# Dữ liệu radar
radar_data = []
for i in range(40):
    angle = random.uniform(-60, 60)
    radar_data.append({
        "angle": angle,
        "distance": random.uniform(0.2, 0.95),
        "type": random.choice(["cloud", "turbulence", "heat"]),
        "intensity": random.uniform(0.3, 1.0),
    })

radar_colors = {
    "cloud": (100, 150, 255),
    "turbulence": (255, 200, 100),
    "heat": (255, 100, 100),
}

# ============================================
# FLIGHT DATA
# ============================================
air_speed = 210
altitude = 2400
heading = 136
climb = 180
throttle = 72
fuel = 65

pfd_temperature = 18.5
pfd_turbulence = 0.3

# ============================================
# BUTTON CLASS
# ============================================
class Button:
    def __init__(self, x, y, w, h, text, color, active_color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.active_color = active_color
        self.active = False

    def draw(self, surface):
        color = self.active_color if self.active else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=8)
        label = font_small.render(self.text, True, (255, 255, 255))
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

buttons = [
    Button(COCKPIT_X + 30, COCKPIT_Y + 400, 120, 40, "CLEAR", (70, 120, 180), (30, 170, 255)),
    Button(COCKPIT_X + 160, COCKPIT_Y + 400, 120, 40, "RAIN", (70, 140, 120), (40, 200, 150)),
    Button(COCKPIT_X + 290, COCKPIT_Y + 400, 120, 40, "STORM", (90, 70, 70), (190, 80, 80)),
    Button(COCKPIT_X + 420, COCKPIT_Y + 400, 120, 40, "FOG", (100, 110, 110), (160, 170, 170)),
]

for b in buttons:
    b.active = (b.text.lower() == current_weather)

# ============================================
# UTILITY FUNCTIONS
# ============================================
def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def color_lerp(c1, c2, t):
    r = int(lerp(c1[0], c2[0], t))
    g = int(lerp(c1[1], c2[1], t))
    b = int(lerp(c1[2], c2[2], t))
    return (r, g, b)

def deg_to_rad(deg):
    return deg * math.pi / 180

def angle_to_pos(angle, distance, center_x, center_y, max_radius):
    rad = deg_to_rad(angle - 90)
    x = center_x + distance * max_radius * math.cos(rad)
    y = center_y + distance * max_radius * math.sin(rad)
    return int(x), int(y)

# ============================================
# DRAW RADAR 120° SECTOR
# ============================================
def draw_radar_120():
    global radar_scan_angle, radar_scan_direction
    
    # Khung radar
    pygame.draw.rect(screen, (8, 8, 15), (RADAR_X, RADAR_Y, RADAR_W, RADAR_H), border_radius=20)
    pygame.draw.rect(screen, (80, 100, 130), (RADAR_X, RADAR_Y, RADAR_W, RADAR_H), 3, border_radius=20)
    
    # Vẽ background sector 120°
    points = [(radar_center_x, radar_center_y)]
    for angle in range(-60, 61, 2):
        rad = deg_to_rad(angle - 90)
        x = radar_center_x + radar_radius * math.cos(rad)
        y = radar_center_y + radar_radius * math.sin(rad)
        points.append((x, y))
    points.append((radar_center_x, radar_center_y))
    
    pygame.draw.polygon(screen, (15, 25, 40), points)
    pygame.draw.polygon(screen, (60, 90, 140), points, 2)
    
    # Vòng tròn khoảng cách
    for dist in [0.25, 0.5, 0.75, 1.0]:
        r = int(radar_radius * dist)
        pygame.draw.circle(screen, (40, 60, 90), (radar_center_x, radar_center_y), r, 1)
        
        label_text = f"{int(dist * 100)}%"
        label = font_tiny.render(label_text, True, (120, 150, 200))
        screen.blit(label, (radar_center_x + r - 10, radar_center_y - 15))
    
    # Đường trung tâm (0°)
    end_x, end_y = angle_to_pos(0, 1.0, radar_center_x, radar_center_y, radar_radius)
    pygame.draw.line(screen, (60, 90, 140), (radar_center_x, radar_center_y), (end_x, end_y), 1)
    
    # Đường biên -60° và +60°
    for edge_angle in [-60, 60]:
        end_x, end_y = angle_to_pos(edge_angle, 1.0, radar_center_x, radar_center_y, radar_radius)
        pygame.draw.line(screen, (60, 90, 140), (radar_center_x, radar_center_y), (end_x, end_y), 2)
    
    # Vẽ dữ liệu radar
    for data in radar_data:
        if -60 <= data["angle"] <= 60:
            x, y = angle_to_pos(data["angle"], data["distance"], radar_center_x, radar_center_y, radar_radius)
            radius = int(12 * data["intensity"])
            color = radar_colors.get(data["type"], (100, 100, 255))
            pygame.draw.circle(screen, color, (x, y), radius)
            pygame.draw.circle(screen, color, (x, y), radius, 1)
    
    # Quét radar (scan line) - 120° sector
    radar_scan_angle += radar_scan_direction * radar_scan_speed
    
    if radar_scan_angle >= 60:
        radar_scan_angle = 60
        radar_scan_direction = -1
    elif radar_scan_angle <= -60:
        radar_scan_angle = -60
        radar_scan_direction = 1
    
    # Vẽ scan line
    end_x, end_y = angle_to_pos(radar_scan_angle, 1.0, radar_center_x, radar_center_y, radar_radius)
    pygame.draw.line(screen, (0, 255, 100), (radar_center_x, radar_center_y), (end_x, end_y), 3)
    
    # Tiêu đề
    title = font_med.render("PFD RADAR (120° SECTOR)", True, (100, 180, 255))
    screen.blit(title, (RADAR_X + 30, RADAR_Y + 20))
    
    # Thông tin
    temp_text = f"TEMP: {pfd_temperature:.1f}°C"
    temp_label = font_small.render(temp_text, True, (200, 150, 100))
    screen.blit(temp_label, (RADAR_X + 30, RADAR_Y + RADAR_H - 120))
    
    turb_text = f"TURB: {pfd_turbulence:.2f}G"
    turb_label = font_small.render(turb_text, True, (200, 100, 100))
    screen.blit(turb_label, (RADAR_X + 30, RADAR_Y + RADAR_H - 80))
    
    # Chú thích
    legend_y = RADAR_Y + RADAR_H - 50
    pygame.draw.circle(screen, (100, 150, 255), (RADAR_X + 30, legend_y), 5)
    text = font_tiny.render("Clouds", True, (100, 150, 255))
    screen.blit(text, (RADAR_X + 50, legend_y - 6))
    
    pygame.draw.circle(screen, (255, 200, 100), (RADAR_X + 200, legend_y), 5)
    text = font_tiny.render("Turbulence", True, (255, 200, 100))
    screen.blit(text, (RADAR_X + 220, legend_y - 6))
    
    pygame.draw.circle(screen, (255, 100, 100), (RADAR_X + 420, legend_y), 5)
    text = font_tiny.render("Heat/Stress", True, (255, 100, 100))
    screen.blit(text, (RADAR_X + 440, legend_y - 6))

# ============================================
# DRAW OUTSIDE SCENE (WINDSHIELD VIEW)
# ============================================
def draw_outside_scene(mode_name):
    cfg = weather_modes[mode_name]
    sky_top = cfg["sky_top"]
    sky_bottom = cfg["sky_bottom"]
    
    # Gradient background
    for y in range(0, WINDSHIELD_H):
        t = y / WINDSHIELD_H
        color = color_lerp(sky_top, sky_bottom, t)
        pygame.draw.line(screen, color, (WINDSHIELD_X, WINDSHIELD_Y + y),
                         (WINDSHIELD_X + WINDSHIELD_W, WINDSHIELD_Y + y))
    
    # Núi
    mountain_base_y = 200
    if cfg["storm"]:
        mountain_base_y = 220
    elif cfg["fog_alpha"] > 100:
        mountain_base_y = 210
    
    pts1 = [
        (0, mountain_base_y), (80, 120), (160, 180), (240, 100), (320, 160),
        (400, 110), (480, 180), (WINDSHIELD_W, mountain_base_y)
    ]
    pygame.draw.polygon(screen, cfg["mountain"], [(WINDSHIELD_X + x, WINDSHIELD_Y + y) for x, y in pts1])
    
    pts2 = [
        (0, WINDSHIELD_H), (60, 200), (160, 240), (280, 180), (380, WINDSHIELD_H),
        (480, 230), (WINDSHIELD_W, WINDSHIELD_H)
    ]
    pygame.draw.polygon(screen, cfg["mountain2"], [(WINDSHIELD_X + x, WINDSHIELD_Y + y) for x, y in pts2])
    
    # Mây
    for cloud in clouds:
        cloud_x = cloud["x"]
        cloud_y = cloud["y"]
        
        if current_weather in ("rain", "storm"):
            cloud_x -= cloud["speed"] * 0.45
        else:
            cloud_x += cloud["speed"] * 0.2
        
        if cloud_x < -150:
            cloud_x = WINDSHIELD_W + 150
        if cloud_x > WINDSHIELD_W + 150:
            cloud_x = -150
        
        cloud["x"] = cloud_x
        
        pygame.draw.ellipse(screen, cfg["cloud"], (WINDSHIELD_X + cloud_x, WINDSHIELD_Y + cloud_y, cloud["w"], cloud["h"]))
        pygame.draw.ellipse(screen, cfg["cloud"], (WINDSHIELD_X + cloud_x + 25, WINDSHIELD_Y + cloud_y - 12, int(cloud["w"] * 0.7), int(cloud["h"] * 0.9)))
    
    # Mưa
    if cfg["rain"]:
        for drop in raindrops:
            drop["y"] += drop["speed"]
            if cfg["storm"]:
                drop["x"] += 1.2
            else:
                drop["x"] += 0.2
            
            if drop["y"] > WINDSHIELD_H:
                drop["y"] = random.randint(-10, 20)
                drop["x"] = random.randint(0, WINDSHIELD_W)
            
            color = (180, 200, 220) if cfg["storm"] else (150, 170, 200)
            pygame.draw.line(screen, color,
                           (WINDSHIELD_X + drop["x"], WINDSHIELD_Y + drop["y"]),
                           (WINDSHIELD_X + drop["x"], WINDSHIELD_Y + drop["y"] + drop["len"]), 1)
    
    # Sương
    if cfg["fog_alpha"] > 0:
        fog = pygame.Surface((WINDSHIELD_W, WINDSHIELD_H), pygame.SRCALPHA)
        fog.fill((205, 210, 215, cfg["fog_alpha"]))
        screen.blit(fog, (WINDSHIELD_X, WINDSHIELD_Y))

# ============================================
# DRAW REALISTIC COCKPIT PANEL (CASA-212)
# ============================================
def draw_cockpit_panel():
    # Khung buồn lái chính
    pygame.draw.rect(screen, (20, 20, 22), (COCKPIT_X, COCKPIT_Y, COCKPIT_W, COCKPIT_H), border_radius=15)
    pygame.draw.rect(screen, (90, 90, 95), (COCKPIT_X, COCKPIT_Y, COCKPIT_W, COCKPIT_H), 3, border_radius=15)
    
    # Kính buồn lái
    pygame.draw.rect(screen, (5, 5, 10), (WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H), border_radius=12)
    pygame.draw.rect(screen, (120, 140, 160), (WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H), 3, border_radius=12)
    
    # Clip vùng nhìn ngoài
    old_clip = screen.get_clip()
    screen.set_clip((WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H))
    draw_outside_scene(current_weather)
    screen.set_clip(old_clip)
    
    # Tiêu đề CASA-212
    title = font_big.render("CASA-212", True, (100, 180, 255))
    screen.blit(title, (COCKPIT_X + 30, COCKPIT_Y + 20))
    
    subtitle = font_med.render("COCKPIT SIMULATOR", True, (150, 180, 220))
    screen.blit(subtitle, (COCKPIT_X + 30, COCKPIT_Y + 60))
    
    # WEATHER MODE
    label = font_small.render("WEATHER MODE:", True, (150, 180, 200))
    screen.blit(label, (COCKPIT_X + 20, COCKPIT_Y + 370))
    
    for b in buttons:
        b.draw(screen)
    
    # FLIGHT INSTRUMENTS PANEL 1
    panel1_x = COCKPIT_X + 30
    panel1_y = COCKPIT_Y + 460
    
    pygame.draw.rect(screen, (25, 30, 40), (panel1_x, panel1_y, 170, 500), border_radius=8)
    pygame.draw.rect(screen, (80, 100, 120), (panel1_x, panel1_y, 170, 500), 2, border_radius=8)
    
    # Tiêu đề panel 1
    panel_title = font_small.render("AIRSPEED", True, (100, 180, 255))
    screen.blit(panel_title, (panel1_x + 15, panel1_y + 10))
    
    value = font_giant.render(f"{int(air_speed)}", True, (0, 255, 0))
    screen.blit(value, (panel1_x + 20, panel1_y + 50))
    
    unit = font_small.render("knots", True, (180, 200, 220))
    screen.blit(unit, (panel1_x + 30, panel1_y + 120))
    
    # ALTITUDE
    alt_label = font_small.render("ALTITUDE", True, (100, 180, 255))
    screen.blit(alt_label, (panel1_x + 15, panel1_y + 160))
    
    alt_value = font_big.render(f"{int(altitude)}", True, (0, 255, 0))
    screen.blit(alt_value, (panel1_x + 20, panel1_y + 200))
    
    alt_unit = font_small.render("feet", True, (180, 200, 220))
    screen.blit(alt_unit, (panel1_x + 35, panel1_y + 260))
    
    # CLIMB RATE
    vs_label = font_small.render("V/S", True, (100, 180, 255))
    screen.blit(vs_label, (panel1_x + 15, panel1_y + 310))
    
    vs_value = font_big.render(f"{int(climb)}", True, (0, 255, 0))
    screen.blit(vs_value, (panel1_x + 20, panel1_y + 350))
    
    vs_unit = font_small.render("ft/min", True, (180, 200, 220))
    screen.blit(vs_unit, (panel1_x + 25, panel1_y + 410))
    
    # FLIGHT INSTRUMENTS PANEL 2
    panel2_x = COCKPIT_X + 220
    panel2_y = COCKPIT_Y + 460
    
    pygame.draw.rect(screen, (25, 30, 40), (panel2_x, panel2_y, 170, 500), border_radius=8)
    pygame.draw.rect(screen, (80, 100, 120), (panel2_x, panel2_y, 170, 500), 2, border_radius=8)
    
    # HEADING
    hdg_label = font_small.render("HEADING", True, (100, 180, 255))
    screen.blit(hdg_label, (panel2_x + 15, panel2_y + 10))
    
    hdg_value = font_giant.render(f"{int(heading)}", True, (0, 255, 0))
    screen.blit(hdg_value, (panel2_x + 20, panel2_y + 50))
    
    hdg_unit = font_small.render("degrees", True, (180, 200, 220))
    screen.blit(hdg_unit, (panel2_x + 20, panel2_y + 120))
    
    # THROTTLE
    thr_label = font_small.render("THROTTLE", True, (100, 180, 255))
    screen.blit(thr_label, (panel2_x + 15, panel2_y + 170))
    
    thr_value = font_big.render(f"{int(throttle)}%", True, (200, 150, 50))
    screen.blit(thr_value, (panel2_x + 20, panel2_y + 210))
    
    # FUEL
    fuel_label = font_small.render("FUEL", True, (100, 180, 255))
    screen.blit(fuel_label, (panel2_x + 15, panel2_y + 280))
    
    fuel_color = (255, 100, 100) if fuel < 20 else (0, 255, 0)
    fuel_value = font_big.render(f"{int(fuel)}%", True, fuel_color)
    screen.blit(fuel_value, (panel2_x + 20, panel2_y + 320))
    
    # FLIGHT INSTRUMENTS PANEL 3
    panel3_x = COCKPIT_X + 410
    panel3_y = COCKPIT_Y + 460
    
    pygame.draw.rect(screen, (25, 30, 40), (panel3_x, panel3_y, 170, 500), border_radius=8)
    pygame.draw.rect(screen, (80, 100, 120), (panel3_x, panel3_y, 170, 500), 2, border_radius=8)
    
    # TEMPERATURE
    temp_label = font_small.render("OAT", True, (100, 180, 255))
    screen.blit(temp_label, (panel3_x + 15, panel3_y + 10))
    
    temp_color = (255, 100, 100) if pfd_temperature > 30 else (100, 200, 255)
    temp_value = font_big.render(f"{pfd_temperature:.1f}°C", True, temp_color)
    screen.blit(temp_value, (panel3_x + 10, panel3_y + 50))
    
    # TURBULENCE
    turb_label = font_small.render("TURB", True, (100, 180, 255))
    screen.blit(turb_label, (panel3_x + 15, panel3_y + 140))
    
    turb_color = (255, 100, 100) if pfd_turbulence > 0.6 else (100, 200, 255)
    turb_value = font_big.render(f"{pfd_turbulence:.2f}G", True, turb_color)
    screen.blit(turb_value, (panel3_x + 10, panel3_y + 180))
    
    # WEATHER STATUS
    weather_label = font_small.render("WEATHER", True, (100, 180, 255))
    screen.blit(weather_label, (panel3_x + 15, panel3_y + 280))
    
    weather_color = (255, 200, 100) if current_weather == "clear" else (255, 100, 100)
    weather_value = font_med.render(current_weather.upper(), True, weather_color)
    screen.blit(weather_value, (panel3_x + 10, panel3_y + 320))
    
    # RADAR SCAN INFO
    scan_label = font_small.render("RADAR SCAN", True, (100, 180, 255))
    screen.blit(scan_label, (panel3_x + 15, panel3_y + 420))
    
    scan_info = f"{radar_scan_angle:.0f}°"
    scan_value = font_med.render(scan_info, True, (100, 200, 255))
    screen.blit(scan_value, (panel3_x + 20, panel3_y + 460))

# ============================================
# MAIN LOOP
# ============================================
running = True
frame_count = 0

while running:
    frame_count += 1
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            for b in buttons:
                if b.is_clicked(pos):
                    current_weather = b.text.lower()
                    for btn in buttons:
                        btn.active = (btn.text.lower() == current_weather)
    
    # Update flight data
    air_speed += random.uniform(-1, 1.5)
    air_speed = clamp(air_speed, 130, 280)
    
    altitude += random.uniform(-10, 10)
    altitude = clamp(altitude, 500, 6000)
    
    heading += random.uniform(-2.5, 2.5)
    if heading > 360:
        heading -= 360
    if heading < 0:
        heading += 360
    
    climb += random.uniform(-30, 30)
    climb = clamp(climb, -500, 800)
    
    throttle += random.uniform(-0.8, 0.8)
    throttle = clamp(throttle, 15, 100)
    
    fuel -= random.uniform(0.02, 0.08)
    fuel = clamp(fuel, 0, 100)
    
    # Update PFD data
    pfd_temperature += random.uniform(-0.3, 0.3)
    pfd_temperature = clamp(pfd_temperature, -30, 50)
    
    pfd_turbulence += random.uniform(-0.015, 0.015)
    pfd_turbulence = clamp(pfd_turbulence, 0, 1.0)
    
    # Update radar data
    for data in radar_data:
        data["angle"] += random.uniform(-1.8, 1.8)
        data["distance"] += random.uniform(-0.025, 0.025)
        data["distance"] = clamp(data["distance"], 0.15, 0.95)
        data["intensity"] += random.uniform(-0.06, 0.06)
        data["intensity"] = clamp(data["intensity"], 0.2, 1.0)
    
    # Render
    screen.fill((8, 10, 15))
    
    # Draw components
    draw_radar_120()
    draw_cockpit_panel()
    
    # FPS indicator (optional)
    if frame_count % 30 == 0:
        fps = int(clock.get_fps())
        fps_text = font_tiny.render(f"FPS: {fps}", True, (100, 100, 100))
        screen.blit(fps_text, (10, 10))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
