import random
import math
import pygame

# -----------------------------
# CÀI ĐẶT CHUNG
# -----------------------------
pygame.init()
WIDTH, HEIGHT = 1600, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CASA-212 Cockpit Simulator with PFD Radar")
clock = pygame.time.Clock()

# Fonts
font_big = pygame.font.SysFont("consolas", 48, bold=True)
font_med = pygame.font.SysFont("consolas", 32, bold=True)
font_small = pygame.font.SysFont("consolas", 20, bold=True)
font_tiny = pygame.font.SysFont("consolas", 14, bold=True)

# Màn hình PFD quét (bên trái)
PFD_X, PFD_Y = 20, 20
PFD_W, PFD_H = 740, 860

# Kính buồn lái (bên phải trên)
WINDSHIELD_X, WINDSHIELD_Y = 780, 20
WINDSHIELD_W, WINDSHIELD_H = 800, 430

# Panel HUD (bên phải dưới)
HUD_X, HUD_Y = 780, 460
HUD_W, HUD_H = 800, 420

# Radar scan animation
radar_angle = 0
radar_speed = 2

# Dữ liệu radar (mây, nhiệt độ, nhiễu động)
weather_data = []
for i in range(40):
    weather_data.append({
        "angle": random.uniform(0, 360),
        "distance": random.uniform(0.2, 1.0),
        "type": random.choice(["cloud", "turbulence", "heat"]),
        "intensity": random.uniform(0.3, 1.0),
    })

# Radar history
radar_history = []

# PFD Scan angle
scan_line_angle = 0

# Radar color map
radar_colors = {
    "cloud": (100, 150, 255),  # xanh
    "turbulence": (255, 200, 100),  # cam
    "heat": (255, 100, 100),  # đỏ
}

# Radar background circles
radar_circles = [0.25, 0.5, 0.75, 1.0]
radar_center_x = PFD_X + PFD_W // 2
radar_center_y = PFD_Y + PFD_H // 2
radar_radius = 320

# Thời tiết buồn lái
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
        "y": random.randint(90, 280),
        "w": random.randint(120, 240),
        "h": random.randint(35, 60),
        "speed": random.uniform(6, 18),
    })

raindrops = []
for i in range(350):
    raindrops.append({
        "x": random.randint(100, WINDSHIELD_W - 100),
        "y": random.randint(0, WINDSHIELD_H),
        "len": random.randint(10, 24),
        "speed": random.uniform(12, 30),
    })

# Flight data
air_speed = 210
altitude = 2400
heading = 136
climb = 180
throttle = 72

# PFD Temperature
pfd_temperature = 18.5
pfd_turbulence = 0.3

# Button
class Button:
    def __init__(self, x, y, w, h, text, color, active_color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.active_color = active_color
        self.active = False

    def draw(self, surface):
        color = self.active_color if self.active else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=12)
        label = font_small.render(self.text, True, (255, 255, 255))
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

buttons = [
    Button(HUD_X + 20, HUD_Y + 20, 170, 50, "CLEAR", (70, 120, 180), (30, 170, 255)),
    Button(HUD_X + 20, HUD_Y + 85, 170, 50, "RAIN", (70, 140, 120), (40, 200, 150)),
    Button(HUD_X + 20, HUD_Y + 150, 170, 50, "STORM", (90, 70, 70), (190, 80, 80)),
    Button(HUD_X + 20, HUD_Y + 215, 170, 50, "FOG", (100, 110, 110), (160, 170, 170)),
]

for b in buttons:
    b.active = (b.text.lower() == current_weather)

# Utility functions
def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def color_lerp(c1, c2, t):
    r = int(lerp(c1[0], c2[0], t))
    g = int(lerp(c1[1], c2[1], t))
    b = int(lerp(c1[2], c2[2], t))
    return (r, g, b)

# Angle to radians
def deg_to_rad(deg):
    return deg * math.pi / 180

# Angle to position on radar
def angle_to_pos(angle, distance, center_x, center_y, max_radius):
    rad = deg_to_rad(angle - 90)  # 0 degrees at top
    x = center_x + distance * max_radius * math.cos(rad)
    y = center_y + distance * max_radius * math.sin(rad)
    return int(x), int(y)

# Vẽ PFD Radar Quét
def draw_pfd_radar():
    global radar_angle, scan_line_angle
    
    # Khung PFD
    pygame.draw.rect(screen, (8, 8, 15), (PFD_X, PFD_Y, PFD_W, PFD_H), border_radius=20)
    pygame.draw.rect(screen, (80, 100, 130), (PFD_X, PFD_Y, PFD_W, PFD_H), 3, border_radius=20)
    
    # Background radar
    pygame.draw.circle(screen, (15, 25, 40), (radar_center_x, radar_center_y), radar_radius)
    
    # Radar grid circles
    for circle in radar_circles:
        r = int(radar_radius * circle)
        pygame.draw.circle(screen, (40, 60, 90), (radar_center_x, radar_center_y), r, 1)
        dist_label = f"{int(circle * 100)}%"
        label = font_tiny.render(dist_label, True, (120, 150, 200))
        screen.blit(label, (radar_center_x + r - 15, radar_center_y - 10))
    
    # Radar crosshairs
    pygame.draw.line(screen, (60, 90, 140), (radar_center_x - radar_radius - 20, radar_center_y), 
                     (radar_center_x + radar_radius + 20, radar_center_y), 1)
    pygame.draw.line(screen, (60, 90, 140), (radar_center_x, radar_center_y - radar_radius - 20),
                     (radar_center_x, radar_center_y + radar_radius + 20), 1)
    
    # Vẽ dữ liệu thời tiết trên radar
    for data in weather_data:
        x, y = angle_to_pos(data["angle"], data["distance"], radar_center_x, radar_center_y, radar_radius)
        
        # Vùng ảnh hưởng
        radius = int(15 * data["intensity"])
        color = radar_colors.get(data["type"], (100, 100, 255))
        
        # Làm mờ dần dựa vào cường độ
        alpha = int(150 * data["intensity"])
        draw_color = color
        pygame.draw.circle(screen, draw_color, (x, y), radius)
        pygame.draw.circle(screen, draw_color, (x, y), radius, 1)
    
    # Quét radar (scan line)
    scan_line_angle += radar_speed
    if scan_line_angle > 360:
        scan_line_angle = 0
        # Xóa history cũ
        radar_history.clear()
    
    # Vẽ đường quét
    end_x, end_y = angle_to_pos(scan_line_angle, 1.0, radar_center_x, radar_center_y, radar_radius)
    pygame.draw.line(screen, (0, 255, 100), (radar_center_x, radar_center_y), (end_x, end_y), 2)
    
    # Hiệu ứng scan (fade)
    for i, hist_angle in enumerate(radar_history[-20:]):
        hist_x, hist_y = angle_to_pos(hist_angle, 1.0, radar_center_x, radar_center_y, radar_radius)
        fade = int(100 * (i / 20))
        pygame.draw.line(screen, (0, 200 - fade, 100 - fade), (radar_center_x, radar_center_y), 
                         (hist_x, hist_y), 1)
    
    radar_history.append(scan_line_angle)
    
    # Tiêu đề PFD
    title = font_med.render("PFD RADAR", True, (100, 180, 255))
    screen.blit(title, (PFD_X + 30, PFD_Y + 20))
    
    # Thông tin thời tiết
    temp_text = f"TEMP: {pfd_temperature:.1f}°C"
    temp_label = font_small.render(temp_text, True, (200, 150, 100))
    screen.blit(temp_label, (PFD_X + 30, PFD_Y + PFD_H - 160))
    
    turb_text = f"TURB: {pfd_turbulence:.2f}G"
    turb_label = font_small.render(turb_text, True, (200, 100, 100))
    screen.blit(turb_label, (PFD_X + 30, PFD_Y + PFD_H - 120))
    
    # Chú thích màu
    legend_y = PFD_Y + PFD_H - 80
    pygame.draw.circle(screen, (100, 150, 255), (PFD_X + 30, legend_y), 6)
    text = font_tiny.render("Clouds", True, (100, 150, 255))
    screen.blit(text, (PFD_X + 50, legend_y - 8))
    
    pygame.draw.circle(screen, (255, 200, 100), (PFD_X + 180, legend_y), 6)
    text = font_tiny.render("Turbulence", True, (255, 200, 100))
    screen.blit(text, (PFD_X + 200, legend_y - 8))
    
    pygame.draw.circle(screen, (255, 100, 100), (PFD_X + 380, legend_y), 6)
    text = font_tiny.render("Heat/Stress", True, (255, 100, 100))
    screen.blit(text, (PFD_X + 400, legend_y - 8))

# Vẽ cảnh ngoài kính buồn lái
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
    mountain_base_y = 280
    if cfg["storm"]:
        mountain_base_y = 300
    elif cfg["fog_alpha"] > 100:  # FIX: Kiểm tra fog_alpha thay vì "fog"
        mountain_base_y = 290
    
    pts1 = [
        (0, mountain_base_y), (80, 180), (160, 240), (240, 160), (320, 220),
        (400, 170), (480, 240), (WINDSHIELD_W, mountain_base_y)
    ]
    pygame.draw.polygon(screen, cfg["mountain"], [(WINDSHIELD_X + x, WINDSHIELD_Y + y) for x, y in pts1])
    
    pts2 = [
        (0, WINDSHIELD_H), (60, 280), (160, 360), (280, 260), (380, WINDSHIELD_H),
        (480, 320), (WINDSHIELD_W, WINDSHIELD_H)
    ]
    pygame.draw.polygon(screen, cfg["mountain2"], [(WINDSHIELD_X + x, WINDSHIELD_Y + y) for x, y in pts2])
    
    # Mây
    for cloud in clouds:
        cloud_x = cloud["x"]
        cloud_y = cloud["y"]
        cloud_w = cloud["w"]
        cloud_h = cloud["h"]
        
        if current_weather in ("rain", "storm"):
            cloud_x -= cloud["speed"] * 0.45
        else:
            cloud_x += cloud["speed"] * 0.2
        
        if cloud_x < -200:
            cloud_x = WINDSHIELD_W + 200
        if cloud_x > WINDSHIELD_W + 200:
            cloud_x = -200
        
        cloud["x"] = cloud_x
        
        pygame.draw.ellipse(screen, cfg["cloud"], (WINDSHIELD_X + cloud_x, WINDSHIELD_Y + cloud_y, cloud_w, cloud_h))
        pygame.draw.ellipse(screen, cfg["cloud"], (WINDSHIELD_X + cloud_x + 40, WINDSHIELD_Y + cloud_y - 18, int(cloud_w * 0.7), int(cloud_h * 0.9)))
        pygame.draw.ellipse(screen, cfg["cloud"], (WINDSHIELD_X + cloud_x + 90, WINDSHIELD_Y + cloud_y - 10, int(cloud_w * 0.6), int(cloud_h * 0.8)))
    
    # Mưa
    if cfg["rain"]:
        for drop in raindrops:
            drop["y"] += drop["speed"]
            if cfg["storm"]:
                drop["x"] += 1.6
            else:
                drop["x"] += 0.3
            
            if drop["y"] > WINDSHIELD_H:
                drop["y"] = random.randint(-20, 35)
                drop["x"] = random.randint(0, WINDSHIELD_W)
            
            if cfg["storm"]:
                pygame.draw.line(screen, (180, 200, 220), 
                               (WINDSHIELD_X + drop["x"], WINDSHIELD_Y + drop["y"]),
                               (WINDSHIELD_X + drop["x"] - 6, WINDSHIELD_Y + drop["y"] + drop["len"]), 2)
            else:
                pygame.draw.line(screen, (150, 170, 200),
                               (WINDSHIELD_X + drop["x"], WINDSHIELD_Y + drop["y"]),
                               (WINDSHIELD_X + drop["x"], WINDSHIELD_Y + drop["y"] + drop["len"]), 2)
    
    # Sương
    if cfg["fog_alpha"] > 0:
        fog = pygame.Surface((WINDSHIELD_W, WINDSHIELD_H), pygame.SRCALPHA)
        fog.fill((205, 210, 215, cfg["fog_alpha"]))
        screen.blit(fog, (WINDSHIELD_X, WINDSHIELD_Y))

# Vẽ khung buồn lái
def draw_cockpit_frame():
    # Kính buồn lái
    pygame.draw.rect(screen, (8, 8, 10), (WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H), border_radius=20)
    pygame.draw.rect(screen, (100, 120, 130), (WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H), 3, border_radius=20)
    
    # Clip vùng nhìn ngoài
    old_clip = screen.get_clip()
    screen.set_clip((WINDSHIELD_X, WINDSHIELD_Y, WINDSHIELD_W, WINDSHIELD_H))
    draw_outside_scene(current_weather)
    screen.set_clip(old_clip)

# Vẽ HUD Panel
def draw_hud_panel():
    # Khung HUD
    pygame.draw.rect(screen, (15, 20, 30), (HUD_X, HUD_Y, HUD_W, HUD_H), border_radius=20)
    pygame.draw.rect(screen, (80, 100, 130), (HUD_X, HUD_Y, HUD_W, HUD_H), 3, border_radius=20)
    
    # Tiêu đề
    title = font_med.render("WEATHER MODE", True, (100, 180, 255))
    screen.blit(title, (HUD_X + 30, HUD_Y + 20))
    
    # Buttons thời tiết
    for b in buttons:
        b.draw(screen)
    
    # Thông tin chuyến bay bên phải
    info_x = HUD_X + 220
    info_y = HUD_Y + 30
    
    # Speed
    label = font_small.render("IAS", True, (180, 220, 255))
    screen.blit(label, (info_x, info_y))
    value = font_med.render(f"{int(air_speed)}", True, (255, 255, 255))
    screen.blit(value, (info_x, info_y + 30))
    
    # Altitude
    label = font_small.render("ALT", True, (180, 220, 255))
    screen.blit(label, (info_x, info_y + 80))
    value = font_med.render(f"{int(altitude)}", True, (255, 255, 255))
    screen.blit(value, (info_x, info_y + 110))
    
    # Heading
    label = font_small.render("HDG", True, (180, 220, 255))
    screen.blit(label, (info_x, info_y + 160))
    value = font_med.render(f"{int(heading)}", True, (255, 255, 255))
    screen.blit(value, (info_x, info_y + 190))
    
    # V/S
    label = font_small.render("V/S", True, (180, 220, 255))
    screen.blit(label, (info_x, info_y + 240))
    value = font_med.render(f"{int(climb)}", True, (255, 255, 255))
    screen.blit(value, (info_x, info_y + 270))
    
    # Throttle
    label = font_small.render("THR", True, (180, 220, 255))
    screen.blit(label, (info_x, info_y + 320))
    value = font_med.render(f"{int(throttle)}%", True, (255, 255, 255))
    screen.blit(value, (info_x, info_y + 350))

# Main loop
running = True
while running:
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
    
    # Cập nhật dữ liệu
    air_speed += random.uniform(-1.5, 1.5)
    air_speed = clamp(air_speed, 150, 260)
    
    altitude += random.uniform(-10, 10)
    altitude = clamp(altitude, 1200, 4200)
    
    heading += random.uniform(-3, 3)
    if heading > 360:
        heading -= 360
    if heading < 0:
        heading += 360
    
    climb += random.uniform(-30, 30)
    climb = clamp(climb, -300, 500)
    
    throttle += random.uniform(-0.7, 0.7)
    throttle = clamp(throttle, 40, 100)
    
    # Cập nhật dữ liệu PFD
    pfd_temperature += random.uniform(-0.3, 0.3)
    pfd_temperature = clamp(pfd_temperature, -10, 40)
    
    pfd_turbulence += random.uniform(-0.01, 0.01)
    pfd_turbulence = clamp(pfd_turbulence, 0, 1.0)
    
    # Update weather data
    for data in weather_data:
        data["angle"] += random.uniform(-2, 2)
        data["distance"] += random.uniform(-0.02, 0.02)
        data["distance"] = clamp(data["distance"], 0.1, 1.0)
        data["intensity"] += random.uniform(-0.05, 0.05)
        data["intensity"] = clamp(data["intensity"], 0.1, 1.0)
    
    # Render
    screen.fill((5, 8, 12))
    
    # Vẽ PFD radar bên trái
    draw_pfd_radar()
    
    # Vẽ buồn lái bên phải trên
    draw_cockpit_frame()
    
    # Vẽ HUD bên phải dưới
    draw_hud_panel()
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
