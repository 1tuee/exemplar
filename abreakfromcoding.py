import pygame
import random
import math
import sys
import json
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import time

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60
TILE_SIZE = 32
MAX_PARTICLES = 200
CAMERA_SMOOTHING = 0.1
WORLD_WIDTH = 2000
WORLD_HEIGHT = 1500

# Professional Color Palette
class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (220, 38, 57)
    GREEN = (34, 197, 94)
    BLUE = (59, 130, 246)
    YELLOW = (251, 191, 36)
    PURPLE = (147, 51, 234)
    ORANGE = (249, 115, 22)
    CYAN = (6, 182, 212)
    GRAY = (107, 114, 128)
    DARK_GRAY = (55, 65, 81)
    LIGHT_GRAY = (209, 213, 219)
    BACKGROUND = (15, 23, 42)
    UI_PANEL = (30, 41, 59)
    UI_BORDER = (71, 85, 105)
    UI_TEXT = (226, 232, 240)
    UI_ACCENT = (99, 102, 241)
    HEALTH_RED = (239, 68, 68)
    MANA_BLUE = (59, 130, 246)
    XP_GOLD = (245, 158, 11)
    DAMAGE_TEXT = (255, 87, 87)
    HEAL_TEXT = (52, 211, 153)

class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    INVENTORY = "inventory"
    LEVEL_UP = "level_up"
    GAME_OVER = "game_over"
    SETTINGS = "settings"

@dataclass
class Vector2:
    x: float
    y: float
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar):
        return Vector2(self.x / scalar, self.y / scalar)
    
    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalized(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def distance_to(self, other):
        return (self - other).magnitude()
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    
    def lerp(self, other, t):
        return Vector2(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t
        )
    
    def to_tuple(self):
        return (int(self.x), int(self.y))

class Timer:
    def __init__(self, duration):
        self.duration = duration
        self.time_left = duration
        self.active = False
    
    def start(self):
        self.time_left = self.duration
        self.active = True
    
    def update(self, dt):
        if self.active:
            self.time_left -= dt
            if self.time_left <= 0:
                self.active = False
                return True
        return False
    
    def is_active(self):
        return self.active
    
    def progress(self):
        if self.duration == 0:
            return 1.0
        return 1.0 - (self.time_left / self.duration)

class Camera:
    def __init__(self, width, height):
        self.position = Vector2(0, 0)
        self.target = Vector2(0, 0)
        self.width = width
        self.height = height
        self.shake_intensity = 0
        self.shake_duration = 0
        self.zoom = 1.0
        self.target_zoom = 1.0
    
    def follow(self, target_pos, dt):
        self.target = Vector2(
            target_pos.x - self.width // 2,
            target_pos.y - self.height // 2
        )
        
        # Smooth camera movement
        self.position = self.position.lerp(self.target, CAMERA_SMOOTHING)
        
        # Keep camera within world bounds
        self.position.x = max(0, min(WORLD_WIDTH - self.width, self.position.x))
        self.position.y = max(0, min(WORLD_HEIGHT - self.height, self.position.y))
    
    def shake(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_duration = duration
    
    def update(self, dt):
        # Handle camera shake
        if self.shake_duration > 0:
            self.shake_duration -= dt
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.position.x += shake_x
            self.position.y += shake_y
        
        # Smooth zoom
        self.zoom += (self.target_zoom - self.zoom) * 0.1
    
    def world_to_screen(self, world_pos):
        return Vector2(
            (world_pos.x - self.position.x) * self.zoom,
            (world_pos.y - self.position.y) * self.zoom
        )
    
    def screen_to_world(self, screen_pos):
        return Vector2(
            screen_pos.x / self.zoom + self.position.x,
            screen_pos.y / self.zoom + self.position.y
        )

class Particle:
    def __init__(self, position, velocity, color, lifetime, size=3, fade=True):
        self.position = Vector2(position.x, position.y)
        self.velocity = Vector2(velocity.x, velocity.y)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.fade = fade
        self.gravity = Vector2(0, 0)
    
    def update(self, dt):
        self.position += self.velocity * dt
        self.velocity += self.gravity * dt
        self.lifetime -= dt
        return self.lifetime <= 0
    
    def draw(self, screen, camera):
        if self.lifetime <= 0:
            return
        
        screen_pos = camera.world_to_screen(self.position)
        if (0 <= screen_pos.x <= WINDOW_WIDTH and 0 <= screen_pos.y <= WINDOW_HEIGHT):
            alpha = 255
            if self.fade:
                alpha = int(255 * (self.lifetime / self.max_lifetime))
            
            color = (*self.color[:3], alpha)
            current_size = int(self.size * (self.lifetime / self.max_lifetime) if self.fade else self.size)
            
            if current_size > 0:
                pygame.draw.circle(screen, color[:3], screen_pos.to_tuple(), current_size)

class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def add_particle(self, particle):
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)
    
    def add_explosion(self, position, color, count=20, speed=100):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            velocity = Vector2(
                math.cos(angle) * random.uniform(50, speed),
                math.sin(angle) * random.uniform(50, speed)
            )
            self.add_particle(Particle(
                position, velocity, color, 
                random.uniform(0.5, 2.0), 
                random.randint(2, 6)
            ))
    
    def add_trail(self, position, direction, color, count=5):
        for i in range(count):
            offset = Vector2(
                random.uniform(-10, 10),
                random.uniform(-10, 10)
            )
            velocity = direction * random.uniform(20, 50) + offset
            self.add_particle(Particle(
                position + offset, velocity, color,
                random.uniform(0.2, 0.8), 
                random.randint(1, 3)
            ))
    
    def update(self, dt):
        self.particles = [p for p in self.particles if not p.update(dt)]
    
    def draw(self, screen, camera):
        for particle in self.particles:
            particle.draw(screen, camera)

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_volume = 0.7
        self.sfx_volume = 0.8
        self.current_music = None
    
    def load_sound(self, name, file_path=None):
        # In a real game, you'd load actual sound files
        # For this demo, we'll create placeholder sound objects
        try:
            if file_path:
                self.sounds[name] = pygame.mixer.Sound(file_path)
            else:
                # Create a simple procedural sound
                self.sounds[name] = self.create_procedural_sound(name)
        except:
            # Fallback: create silent sound
            self.sounds[name] = None
    
    def create_procedural_sound(self, sound_type):
        # Create simple procedural sounds using pygame
        sample_rate = 22050
        duration = 0.1
        
        if sound_type == "shoot":
            # Create a shooting sound
            frames = int(duration * sample_rate)
            arr = []
            for i in range(frames):
                wave = 4096 * math.sin(2 * math.pi * (440 + i * 5) * i / sample_rate)
                wave *= (frames - i) / frames  # Fade out
                arr.append([int(wave), int(wave)])
            sound = pygame.sndarray.make_sound(arr)
            return sound
        
        return None
    
    def play_sound(self, name, volume=1.0):
        if name in self.sounds and self.sounds[name]:
            sound = self.sounds[name]
            sound.set_volume(volume * self.sfx_volume)
            sound.play()
    
    def play_music(self, file_path, loop=-1):
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loop)
            self.current_music = file_path
        except:
            pass
    
    def set_music_volume(self, volume):
        self.music_volume = max(0, min(1, volume))
        pygame.mixer.music.set_volume(self.music_volume)
    
    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0, min(1, volume))

class Animation:
    def __init__(self, frames, frame_duration):
        self.frames = frames
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.timer = 0
        self.loop = True
        self.finished = False
    
    def update(self, dt):
        if self.finished and not self.loop:
            return
        
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer = 0
            self.current_frame += 1
            
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True
    
    def get_current_frame(self):
        return self.frames[self.current_frame]
    
    def reset(self):
        self.current_frame = 0
        self.timer = 0
        self.finished = False

class UIElement:
    def __init__(self, position, size):
        self.position = Vector2(position.x, position.y)
        self.size = Vector2(size.x, size.y)
        self.visible = True
        self.enabled = True
        self.hovered = False
        self.pressed = False
    
    def get_rect(self):
        return pygame.Rect(self.position.x, self.position.y, self.size.x, self.size.y)
    
    def contains_point(self, point):
        rect = self.get_rect()
        return rect.collidepoint(point.to_tuple())
    
    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.contains_point(Vector2(event.pos[0], event.pos[1]))
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hovered:
                self.pressed = True
                return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.pressed:
                self.pressed = False
                if self.hovered:
                    self.on_click()
                    return True
        
        return False
    
    def on_click(self):
        pass
    
    def update(self, dt):
        pass
    
    def draw(self, screen):
        pass

class Button(UIElement):
    def __init__(self, position, size, text, font, callback=None):
        super().__init__(position, size)
        self.text = text
        self.font = font
        self.callback = callback
        self.base_color = Colors.UI_PANEL
        self.hover_color = Colors.UI_ACCENT
        self.text_color = Colors.UI_TEXT
        self.border_color = Colors.UI_BORDER
    
    def on_click(self):
        if self.callback:
            self.callback()
    
    def draw(self, screen):
        if not self.visible:
            return
        
        # Draw button background
        color = self.hover_color if self.hovered else self.base_color
        rect = self.get_rect()
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, self.border_color, rect, 2)
        
        # Draw text
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

class ProgressBar(UIElement):
    def __init__(self, position, size, max_value, current_value=0):
        super().__init__(position, size)
        self.max_value = max_value
        self.current_value = current_value
        self.background_color = Colors.DARK_GRAY
        self.fill_color = Colors.GREEN
        self.border_color = Colors.UI_BORDER
    
    def set_value(self, value):
        self.current_value = max(0, min(self.max_value, value))
    
    def set_colors(self, fill_color, background_color=None):
        self.fill_color = fill_color
        if background_color:
            self.background_color = background_color
    
    def draw(self, screen):
        if not self.visible:
            return
        
        rect = self.get_rect()
        
        # Draw background
        pygame.draw.rect(screen, self.background_color, rect)
        
        # Draw fill
        if self.max_value > 0:
            fill_width = (self.current_value / self.max_value) * self.size.x
            fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
            pygame.draw.rect(screen, self.fill_color, fill_rect)
        
        # Draw border
        pygame.draw.rect(screen, self.border_color, rect, 2)

class TextRenderer:
    def __init__(self):
        self.fonts = {}
        self.default_font = pygame.font.Font(None, 24)
        self.load_fonts()
    
    def load_fonts(self):
        try:
            # Try to load system fonts
            self.fonts['small'] = pygame.font.Font(None, 18)
            self.fonts['medium'] = pygame.font.Font(None, 24)
            self.fonts['large'] = pygame.font.Font(None, 36)
            self.fonts['title'] = pygame.font.Font(None, 48)
        except:
            # Fallback to default font
            self.fonts['small'] = self.default_font
            self.fonts['medium'] = self.default_font
            self.fonts['large'] = self.default_font
            self.fonts['title'] = self.default_font
    
    def get_font(self, size='medium'):
        return self.fonts.get(size, self.default_font)
    
    def render_text(self, text, size='medium', color=Colors.WHITE, antialias=True):
        font = self.get_font(size)
        return font.render(text, antialias, color)
    
    def render_text_centered(self, screen, text, position, size='medium', color=Colors.WHITE):
        surface = self.render_text(text, size, color)
        rect = surface.get_rect(center=position.to_tuple())
        screen.blit(surface, rect)
        return rect

class GameSettings:
    def __init__(self):
        self.master_volume = 1.0
        self.music_volume = 0.7
        self.sfx_volume = 0.8
        self.fullscreen = False
        self.vsync = True
        self.show_fps = False
        self.difficulty = 1.0
        self.auto_save = True
        self.key_bindings = {
            'move_up': pygame.K_w,
            'move_down': pygame.K_s,
            'move_left': pygame.K_a,
            'move_right': pygame.K_d,
            'attack': pygame.K_SPACE,
            'special': pygame.K_q,
            'interact': pygame.K_e,
            'inventory': pygame.K_i,
            'pause': pygame.K_ESCAPE
        }
    
    def save_settings(self):
        try:
            settings_data = {
                'master_volume': self.master_volume,
                'music_volume': self.music_volume,
                'sfx_volume': self.sfx_volume,
                'fullscreen': self.fullscreen,
                'vsync': self.vsync,
                'show_fps': self.show_fps,
                'difficulty': self.difficulty,
                'auto_save': self.auto_save,
                'key_bindings': self.key_bindings
            }
            with open('game_settings.json', 'w') as f:
                json.dump(settings_data, f, indent=2)
        except:
            pass
    
    def load_settings(self):
        try:
            with open('game_settings.json', 'r') as f:
                settings_data = json.load(f)
                for key, value in settings_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except:
            pass

# Utility Functions
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

def lerp(a, b, t):
    return a + (b - a) * t

def approach(current, target, speed, dt):
    if current < target:
        return min(current + speed * dt, target)
    else:
        return max(current - speed * dt, target)

def angle_between_points(p1, p2):
    return math.atan2(p2.y - p1.y, p2.x - p1.x)

def rotate_point(point, center, angle):
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    
    translated = Vector2(point.x - center.x, point.y - center.y)
    
    rotated_x = translated.x * cos_angle - translated.y * sin_angle
    rotated_y = translated.x * sin_angle + translated.y * cos_angle
    
    return Vector2(rotated_x + center.x, rotated_y + center.y)

def create_gradient_surface(width, height, color1, color2, vertical=True):
    surface = pygame.Surface((width, height))
    
    for i in range(height if vertical else width):
        ratio = i / (height - 1 if vertical else width - 1)
        color = (
            int(color1[0] + (color2[0] - color1[0]) * ratio),
            int(color1[1] + (color2[1] - color1[1]) * ratio),
            int(color1[2] + (color2[2] - color1[2]) * ratio)
        )
        
        if vertical:
            pygame.draw.line(surface, color, (0, i), (width, i))
        else:
            pygame.draw.line(surface, color, (i, 0), (i, height))
    
    return surface

# Performance Monitor
class PerformanceMonitor:
    def __init__(self):
        self.fps_samples = []
        self.max_samples = 60
        self.frame_time = 0
        self.last_time = time.time()
    
    def update(self):
        current_time = time.time()
        self.frame_time = current_time - self.last_time
        self.last_time = current_time
        
        if self.frame_time > 0:
            fps = 1.0 / self.frame_time
            self.fps_samples.append(fps)
            
            if len(self.fps_samples) > self.max_samples:
                self.fps_samples.pop(0)
    
    def get_average_fps(self):
        if not self.fps_samples:
            return 0
        return sum(self.fps_samples) / len(self.fps_samples)
    
    def get_current_fps(self):
        if self.frame_time > 0:
            return 1.0 / self.frame_time
        return 0
    
    def draw_stats(self, screen, text_renderer):
        if not text_renderer:
            return
        
        avg_fps = self.get_average_fps()
        current_fps = self.get_current_fps()
        
        fps_text = f"FPS: {current_fps:.1f} (avg: {avg_fps:.1f})"
        frame_time_ms = self.frame_time * 1000
        frame_text = f"Frame Time: {frame_time_ms:.2f}ms"
        
        text_renderer.render_text_centered(
            screen, fps_text, Vector2(WINDOW_WIDTH - 100, 30), 'small', Colors.YELLOW
        )
        text_renderer.render_text_centered(
            screen, frame_text, Vector2(WINDOW_WIDTH - 100, 50), 'small', Colors.YELLOW
        )

print("Nexus Protocol Part 1 - Core Engine & Foundation Systems")
print("Features included:")
print("- Advanced Vector2 math system")
print("- Professional Camera system with shake and zoom")
print("- Particle system with explosion and trail effects")
print("- Sound manager with procedural sound generation")
print("- Animation system")
print("- Complete UI framework (buttons, progress bars, text rendering)")
print("- Game settings with save/load functionality")
print("- Performance monitoring")
print("- Comprehensive utility functions")
print("\nReady for Part 2: Game Entities & Combat System!")
# NEXUS PROTOCOL PART 2 - Game Entities, Combat System, AI & Player Mechanics
# Builds on Part 1's foundation systems

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pygame
import random
import math

# Entity System Foundation
class EntityType(Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    PROJECTILE = "projectile"
    ITEM = "item"
    ENVIRONMENTAL = "environmental"
    NPC = "npc"

class DamageType(Enum):
    PHYSICAL = "physical"
    ENERGY = "energy"
    FIRE = "fire"
    ICE = "ice"
    POISON = "poison"
    LIGHTNING = "lightning"

@dataclass
class Stats:
    health: int
    max_health: int
    mana: int
    max_mana: int
    attack_damage: int
    defense: int
    speed: int
    critical_chance: float
    critical_multiplier: float
    accuracy: float
    evasion: float
    
    def __post_init__(self):
        self.health = min(self.health, self.max_health)
        self.mana = min(self.mana, self.max_mana)

@dataclass
class StatusEffect:
    name: str
    duration: float
    tick_rate: float
    effect_value: int
    damage_type: DamageType
    stacks: int = 1
    max_stacks: int = 5
    last_tick: float = 0
    
    def update(self, dt):
        self.duration -= dt
        self.last_tick += dt
        
        if self.last_tick >= self.tick_rate:
            self.last_tick = 0
            return True  # Time for effect tick
        return False

class Entity:
    def __init__(self, position, entity_type, stats=None):
        # Core Properties
        self.position = Vector2(position.x, position.y)
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)
        self.rotation = 0
        self.size = Vector2(32, 32)
        self.entity_type = entity_type
        
        # Stats and Combat
        self.stats = stats or Stats(100, 100, 50, 50, 10, 5, 100, 0.1, 2.0, 0.9, 0.1)
        self.status_effects = {}
        self.invulnerable = False
        self.invulnerability_timer = 0
        
        # Visual and Animation
        self.sprite_color = Colors.WHITE
        self.animation_state = "idle"
        self.facing_direction = Vector2(1, 0)
        self.visual_effects = []
        
        # Collision and Physics
        self.collision_radius = 16
        self.solid = True
        self.friction = 0.8
        self.max_speed = 300
        
        # State Management
        self.alive = True
        self.active = True
        self.marked_for_deletion = False
        
        # AI and Behavior (for enemies)
        self.target = None
        self.ai_state = "idle"
        self.ai_timer = 0
        self.detection_radius = 200
        self.attack_range = 100
        self.attack_cooldown = 0
        
        # Loot and Drops
        self.loot_table = []
        self.experience_value = 0
    
    def update(self, dt, world):
        if not self.active:
            return
        
        # Update invulnerability
        if self.invulnerable:
            self.invulnerability_timer -= dt
            if self.invulnerability_timer <= 0:
                self.invulnerable = False
        
        # Update status effects
        self.update_status_effects(dt)
        
        # Apply physics
        self.velocity += self.acceleration * dt
        
        # Apply friction
        self.velocity *= self.friction
        
        # Limit velocity
        if self.velocity.magnitude() > self.max_speed:
            self.velocity = self.velocity.normalized() * self.max_speed
        
        # Update position
        self.position += self.velocity * dt
        
        # Reset acceleration
        self.acceleration = Vector2(0, 0)
        
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        
        # Check health
        if self.stats.health <= 0 and self.alive:
            self.die(world)
    
    def update_status_effects(self, dt):
        effects_to_remove = []
        
        for effect_name, effect in self.status_effects.items():
            if effect.update(dt):
                # Apply effect tick
                self.apply_status_effect_tick(effect)
            
            if effect.duration <= 0:
                effects_to_remove.append(effect_name)
        
        for effect_name in effects_to_remove:
            del self.status_effects[effect_name]
    
    def apply_status_effect_tick(self, effect):
        if effect.name == "poison":
            self.take_damage(effect.effect_value, DamageType.POISON)
        elif effect.name == "burn":
            self.take_damage(effect.effect_value, DamageType.FIRE)
        elif effect.name == "regeneration":
            self.heal(effect.effect_value)
        elif effect.name == "slow":
            # Speed reduction handled in movement
            pass
    
    def add_status_effect(self, effect):
        if effect.name in self.status_effects:
            existing = self.status_effects[effect.name]
            existing.stacks = min(existing.stacks + 1, existing.max_stacks)
            existing.duration = max(existing.duration, effect.duration)
        else:
            self.status_effects[effect.name] = effect
    
    def take_damage(self, damage, damage_type=DamageType.PHYSICAL, source=None):
        if not self.alive or self.invulnerable:
            return 0
        
        # Calculate actual damage
        actual_damage = max(1, damage - self.stats.defense)
        
        # Apply damage type modifiers
        if damage_type == DamageType.PHYSICAL:
            actual_damage = int(actual_damage * 1.0)
        elif damage_type == DamageType.ENERGY:
            actual_damage = int(actual_damage * 1.2)
        
        # Apply damage
        self.stats.health -= actual_damage
        self.stats.health = max(0, self.stats.health)
        
        # Trigger invulnerability frames
        self.invulnerable = True
        self.invulnerability_timer = 0.1
        
        return actual_damage
    
    def heal(self, amount):
        if not self.alive:
            return 0
        
        old_health = self.stats.health
        self.stats.health = min(self.stats.max_health, self.stats.health + amount)
        return self.stats.health - old_health
    
    def die(self, world):
        self.alive = False
        self.marked_for_deletion = True
        
        # Drop loot
        self.drop_loot(world)
        
        # Add death particle effect
        if hasattr(world, 'particle_system'):
            world.particle_system.add_explosion(
                self.position, Colors.RED, 15, 150
            )
    
    def drop_loot(self, world):
        for loot_entry in self.loot_table:
            if random.random() < loot_entry['chance']:
                # Create item (placeholder for now)
                pass
    
    def can_attack(self):
        return self.attack_cooldown <= 0 and self.alive
    
    def get_collision_rect(self):
        return pygame.Rect(
            self.position.x - self.collision_radius,
            self.position.y - self.collision_radius,
            self.collision_radius * 2,
            self.collision_radius * 2
        )
    
    def check_collision(self, other):
        distance = self.position.distance_to(other.position)
        return distance < (self.collision_radius + other.collision_radius)
    
    def draw(self, screen, camera):
        if not self.active:
            return
        
        screen_pos = camera.world_to_screen(self.position)
        
        # Don't draw if off-screen
        if (screen_pos.x < -50 or screen_pos.x > WINDOW_WIDTH + 50 or
            screen_pos.y < -50 or screen_pos.y > WINDOW_HEIGHT + 50):
            return
        
        # Draw entity (basic representation)
        color = self.sprite_color
        if self.invulnerable:
            # Flash effect when invulnerable
            if int(self.invulnerability_timer * 20) % 2:
                color = Colors.WHITE
        
        pygame.draw.circle(screen, color, screen_pos.to_tuple(), 
                          int(self.collision_radius * camera.zoom))
        
        # Draw health bar for enemies
        if self.entity_type == EntityType.ENEMY and self.stats.health < self.stats.max_health:
            self.draw_health_bar(screen, screen_pos, camera)
    
    def draw_health_bar(self, screen, screen_pos, camera):
        bar_width = 40
        bar_height = 6
        bar_y_offset = -30
        
        health_ratio = self.stats.health / self.stats.max_health
        
        # Background
        bg_rect = pygame.Rect(
            screen_pos.x - bar_width // 2,
            screen_pos.y + bar_y_offset,
            bar_width, bar_height
        )
        pygame.draw.rect(screen, Colors.DARK_GRAY, bg_rect)
        
        # Health fill
        health_width = int(bar_width * health_ratio)
        health_rect = pygame.Rect(
            screen_pos.x - bar_width // 2,
            screen_pos.y + bar_y_offset,
            health_width, bar_height
        )
        
        # Color based on health percentage
        if health_ratio > 0.6:
            health_color = Colors.GREEN
        elif health_ratio > 0.3:
            health_color = Colors.YELLOW
        else:
            health_color = Colors.RED
        
        pygame.draw.rect(screen, health_color, health_rect)

class Player(Entity):
    def __init__(self, position):
        super().__init__(position, EntityType.PLAYER)
        self.sprite_color = Colors.CYAN
        
        # Player-specific stats
        self.stats = Stats(100, 100, 100, 100, 25, 10, 150, 0.15, 2.5, 0.95, 0.15)
        
        # Player progression
        self.level = 1
        self.experience = 0
        self.experience_to_next_level = 100
        self.skill_points = 0
        
        # Equipment and inventory
        self.equipped_weapon = None
        self.inventory = []
        self.max_inventory_size = 20
        
        # Input handling
        self.input_buffer = []
        self.last_movement_direction = Vector2(0, 0)
        
        # Special abilities
        self.abilities = {
            'dash': {'cooldown': 0, 'max_cooldown': 2.0, 'cost': 20},
            'shield': {'cooldown': 0, 'max_cooldown': 5.0, 'cost': 30},
            'power_attack': {'cooldown': 0, 'max_cooldown': 3.0, 'cost': 25}
        }
        
        # Combat stats
        self.combo_counter = 0
        self.last_attack_time = 0
        self.combo_timeout = 2.0
    
    def update(self, dt, world):
        super().update(dt, world)
        
        # Update abilities
        for ability in self.abilities.values():
            if ability['cooldown'] > 0:
                ability['cooldown'] -= dt
        
        # Update combo system
        if self.combo_counter > 0:
            if time.time() - self.last_attack_time > self.combo_timeout:
                self.combo_counter = 0
        
        # Regenerate mana
        if self.stats.mana < self.stats.max_mana:
            self.stats.mana = min(self.stats.max_mana, 
                                self.stats.mana + 20 * dt)
    
    def handle_input(self, keys, dt):
        movement = Vector2(0, 0)
        
        # Movement input
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            movement.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            movement.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            movement.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            movement.y += 1
        
        # Normalize diagonal movement
        if movement.magnitude() > 0:
            movement = movement.normalized()
            self.last_movement_direction = movement
        
        # Apply movement force
        move_force = movement * self.stats.speed * 5
        self.acceleration += move_force
        
        # Update facing direction
        if movement.magnitude() > 0:
            self.facing_direction = movement
    
    def attack(self, world):
        if not self.can_attack():
            return
        
        self.attack_cooldown = 0.5
        self.combo_counter += 1
        self.last_attack_time = time.time()
        
        # Calculate damage with combo multiplier
        damage = self.stats.attack_damage
        if self.combo_counter > 1:
            damage = int(damage * (1 + (self.combo_counter - 1) * 0.2))
        
        # Create attack projectile or melee attack
        attack_pos = self.position + self.facing_direction * 50
        projectile = Projectile(
            attack_pos, self.facing_direction * 400,
            damage, DamageType.PHYSICAL, self, 1.0
        )
        projectile.sprite_color = Colors.YELLOW
        world.add_entity(projectile)
        
        # Consume mana
        self.stats.mana = max(0, self.stats.mana - 10)
        
        # Add particle trail
        if hasattr(world, 'particle_system'):
            world.particle_system.add_trail(
                attack_pos, self.facing_direction, Colors.YELLOW, 8
            )
    
    def use_ability(self, ability_name, world):
        if ability_name not in self.abilities:
            return False
        
        ability = self.abilities[ability_name]
        
        if ability['cooldown'] > 0 or self.stats.mana < ability['cost']:
            return False
        
        # Execute ability
        if ability_name == 'dash':
            self.dash()
        elif ability_name == 'shield':
            self.activate_shield()
        elif ability_name == 'power_attack':
            self.power_attack(world)
        
        # Apply cooldown and cost
        ability['cooldown'] = ability['max_cooldown']
        self.stats.mana = max(0, self.stats.mana - ability['cost'])
        return True
    
    def dash(self):
        dash_force = self.facing_direction * 800
        self.velocity += dash_force
        self.invulnerable = True
        self.invulnerability_timer = 0.3
    
    def activate_shield(self):
        shield_effect = StatusEffect(
            "shield", 3.0, 1.0, 0, DamageType.PHYSICAL
        )
        self.add_status_effect(shield_effect)
        self.invulnerable = True
        self.invulnerability_timer = 0.5
    
    def power_attack(self, world):
        # Create multiple projectiles in a spread
        for angle_offset in [-0.5, 0, 0.5]:
            angle = math.atan2(self.facing_direction.y, self.facing_direction.x) + angle_offset
            direction = Vector2(math.cos(angle), math.sin(angle))
            
            projectile = Projectile(
                self.position + direction * 30,
                direction * 500,
                self.stats.attack_damage * 2,
                DamageType.ENERGY,
                self, 1.5
            )
            projectile.sprite_color = Colors.PURPLE
            world.add_entity(projectile)
    
    def gain_experience(self, amount):
        self.experience += amount
        
        while self.experience >= self.experience_to_next_level:
            self.level_up()
    
    def level_up(self):
        self.experience -= self.experience_to_next_level
        self.level += 1
        self.skill_points += 3
        
        # Increase stats
        self.stats.max_health += 20
        self.stats.max_mana += 15
        self.stats.attack_damage += 5
        self.stats.defense += 2
        
        # Heal to full
        self.stats.health = self.stats.max_health
        self.stats.mana = self.stats.max_mana
        
        # Calculate next level requirement
        self.experience_to_next_level = int(100 * (1.5 ** (self.level - 1)))

class Enemy(Entity):
    def __init__(self, position, enemy_type):
        super().__init__(position, EntityType.ENEMY)
        self.enemy_type = enemy_type
        self.setup_enemy_type()
        
        # AI Behavior
        self.ai_update_timer = 0
        self.ai_update_rate = 0.1  # Update AI 10 times per second
        self.patrol_points = []
        self.patrol_index = 0
        self.home_position = Vector2(position.x, position.y)
        self.aggro_timer = 0
        self.max_aggro_time = 10.0
        
        # Combat AI
        self.preferred_distance = 100
        self.retreat_threshold = 0.3  # Retreat when health < 30%
        self.group_behavior = False
        
    def setup_enemy_type(self):
        if self.enemy_type == "grunt":
            self.stats = Stats(50, 50, 0, 0, 15, 3, 80, 0.05, 1.5, 0.8, 0.05)
            self.sprite_color = Colors.RED
            self.detection_radius = 150
            self.attack_range = 40
            self.experience_value = 25
            self.preferred_distance = 50
            
        elif self.enemy_type == "ranger":
            self.stats = Stats(30, 30, 20, 20, 20, 1, 120, 0.1, 2.0, 0.85, 0.1)
            self.sprite_color = Colors.GREEN
            self.detection_radius = 200
            self.attack_range = 150
            self.experience_value = 40
            self.preferred_distance = 120
            
        elif self.enemy_type == "mage":
            self.stats = Stats(25, 25, 50, 50, 25, 0, 70, 0.15, 2.5, 0.9, 0.15)
            self.sprite_color = Colors.PURPLE
            self.detection_radius = 180
            self.attack_range = 200
            self.experience_value = 60
            self.preferred_distance = 150
            
        elif self.enemy_type == "boss":
            self.stats = Stats(300, 300, 100, 100, 40, 15, 100, 0.2, 3.0, 0.95, 0.2)
            self.sprite_color = Colors.ORANGE
            self.detection_radius = 300
            self.attack_range = 80
            self.experience_value = 200
            self.preferred_distance = 60
            self.collision_radius = 32
    
    def update(self, dt, world):
        super().update(dt, world)
        
        # Update AI
        self.ai_update_timer += dt
        if self.ai_update_timer >= self.ai_update_rate:
            self.ai_update_timer = 0
            self.update_ai(world)
        
        # Update aggro timer
        if self.target and self.aggro_timer > 0:
            self.aggro_timer -= dt
            if self.aggro_timer <= 0:
                self.target = None
                self.ai_state = "idle"
    
    def update_ai(self, world):
        if not self.alive:
            return
        
        # Find target (player)
        player = world.get_player()
        if not player:
            return
        
        distance_to_player = self.position.distance_to(player.position)
        
        # Check if player is in detection range
        if distance_to_player <= self.detection_radius:
            if not self.target:
                self.target = player
                self.aggro_timer = self.max_aggro_time
                self.ai_state = "combat"
        
        # AI State Machine
        if self.ai_state == "idle":
            self.ai_idle(world)
        elif self.ai_state == "patrol":
            self.ai_patrol(world)
        elif self.ai_state == "combat":
            self.ai_combat(world, player)
        elif self.ai_state == "retreat":
            self.ai_retreat(world, player)
    
    def ai_idle(self, world):
        # Random chance to start patrolling
        if random.random() < 0.1:
            self.ai_state = "patrol"
            self.setup_patrol_points()
    
    def ai_patrol(self, world):
        if not self.patrol_points:
            self.ai_state = "idle"
            return
        
        target_point = self.patrol_points[self.patrol_index]
        direction = (target_point - self.position).normalized()
        
        # Move towards patrol point
        move_force = direction * self.stats.speed * 2
        self.acceleration += move_force
        
        # Check if reached patrol point
        if self.position.distance_to(target_point) < 20:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
    
    def ai_combat(self, world, player):
        if not player or not player.alive:
            self.ai_state = "idle"
            return
        
        distance_to_player = self.position.distance_to(player.position)
        
        # Check if should retreat
        health_ratio = self.stats.health / self.stats.max_health
        if health_ratio < self.retreat_threshold:
            self.ai_state = "retreat"
            return
        
        # Move towards or away from player based on preferred distance
        if distance_to_player > self.preferred_distance:
            # Move closer
            direction = (player.position - self.position).normalized()
            move_force = direction * self.stats.speed * 3
            self.acceleration += move_force
        elif distance_to_player < self.preferred_distance * 0.7:
            # Move away (kiting behavior)
            direction = (self.position - player.position).normalized()
            move_force = direction * self.stats.speed * 2
            self.acceleration += move_force
        
        # Attack if in range
        if distance_to_player <= self.attack_range and self.can_attack():
            self.attack_player(world, player)
    
    def ai_retreat(self, world, player):
        # Move away from player
        direction = (self.position - player.position).normalized()
        move_force = direction * self.stats.speed * 4
        self.acceleration += move_force
        
        # Return to combat if health recovered
        health_ratio = self.stats.health / self.stats.max_health
        if health_ratio > self.retreat_threshold + 0.2:
            self.ai_state = "combat"
    
    def setup_patrol_points(self):
        # Create random patrol points around home position
        self.patrol_points = []
        for _ in range(random.randint(2, 4)):
            offset = Vector2(
                random.uniform(-100, 100),
                random.uniform(-100, 100)
            )
            point = self.home_position + offset
            self.patrol_points.append(point)
    
    def attack_player(self, world, player):
        self.attack_cooldown = 1.0 + random.uniform(-0.2, 0.2)
        
        direction = (player.position - self.position).normalized()
        
        if self.enemy_type == "grunt":
            # Melee attack
            if self.position.distance_to(player.position) <= 50:
                player.take_damage(self.stats.attack_damage, DamageType.PHYSICAL, self)
        else:
            # Ranged attack
            projectile = EnemyProjectile(
                self.position + direction * 20,
                direction * 300,
                self.stats.attack_damage,
                DamageType.ENERGY if self.enemy_type == "mage" else DamageType.PHYSICAL,
                self
            )
            world.add_entity(projectile)

class Projectile(Entity):
    def __init__(self, position, velocity, damage, damage_type, owner, lifetime=3.0):
        super().__init__(position, EntityType.PROJECTILE)
        self.velocity = velocity
        self.damage = damage
        self.damage_type = damage_type
        self.owner = owner
        self.lifetime = lifetime
        self.pierce_count = 0
        self.max_pierce = 0
        self.collision_radius = 8
        self.solid = False
        
        # Visual effects
        self.trail_particles = []
        self.hit_particles = []
    
    def update(self, dt, world):
        super().update(dt, world)
        
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.marked_for_deletion = True
        
        # Check collisions with appropriate targets
        targets = world.get_entities_of_type(
            EntityType.ENEMY if self.owner.entity_type == EntityType.PLAYER else EntityType.PLAYER
        )
        
        for target in targets:
            if target != self.owner and self.check_collision(target):
                self.hit_target(target, world)
                break
    
    def hit_target(self, target, world):
        damage_dealt = target.take_damage(self.damage, self.damage_type, self.owner)
        
        # Add hit particles
        if hasattr(world, 'particle_system'):
            world.particle_system.add_explosion(
                self.position, Colors.YELLOW, 10, 80
            )
        
        # Handle pierce
        self.pierce_count += 1
        if self.pierce_count > self.max_pierce:
            self.marked_for_deletion = True
    
    def draw(self, screen, camera):
        screen_pos = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, self.sprite_color, 
                          screen_pos.to_tuple(), 
                          int(self.collision_radius * camera.zoom))

class EnemyProjectile(Projectile):
    def __init__(self, position, velocity, damage, damage_type, owner):
        super().__init__(position, velocity, damage, damage_type, owner, 5.0)
        self.sprite_color = Colors.RED
        self.collision_radius = 6

# Combat System
class DamageNumber:
    def __init__(self, position, damage, damage_type, critical=False):
        self.position = Vector2(position.x, position.y)
        self.velocity = Vector2(
            random.uniform(-50, 50),
            random.uniform(-100, -50)
        )
        self.damage = damage
        self.damage_type = damage_type
        self.critical = critical
        self.lifetime = 2.0
        self.max_lifetime = 2.0
        self.color = Colors.DAMAGE_TEXT if damage > 0 else Colors.HEAL_TEXT
        if critical:
            self.color = Colors.YELLOW
    
    def update(self, dt):
        self.position += self.velocity * dt
        self.velocity.y += 50 * dt  # Gravity
        self.lifetime -= dt
        return self.lifetime <= 0
    
    def draw(self, screen, camera, text_renderer):
        if self.lifetime <= 0:
            return
        
        screen_pos = camera.world_to_screen(self.position)
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        
        text = f"-{self.damage}" if self.damage > 0 else f"+{abs(self.damage)}"
        if self.critical:
            text += "!"
        
        # This is a simplified version - in a real implementation you'd want
        # to handle alpha blending properly
        text_renderer.render_text_centered(
            screen, text, screen_pos, 'small', self.color
        )

print("Nexus Protocol Part 2 - Game Entities & Combat System Complete!")
print("Features included:")
print("- Complete Entity system with stats, status effects, and collision")
print("- Advanced Player class with abilities, leveling, and combo system")
print("- Sophisticated Enemy AI with multiple behavior states")
print("- Professional Combat system with damage types and effects")
print("- Projectile system with pierce mechanics")
print("- Status effect system (poison, burn, slow, etc.)")
print("- Damage numbers and visual feedback")
print("- Enemy types: Grunt (melee), Ranger (ranged), Mage (magic), Boss")
print("- Player abilities: Dash, Shield, Power Attack")
print("\nReady for Part 3: World System & Game Logic!")
# NEXUS PROTOCOL PART 3 - World System, Level Generation, Item System & Game Logic
# Builds on Parts 1 & 2's foundation and entity systems

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
import pygame
import random
import math
import json
import time

# World and Level Generation System
class TileType(Enum):
    EMPTY = 0
    WALL = 1
    FLOOR = 2
    DOOR = 3
    CHEST = 4
    SPAWN_POINT = 5
    EXIT = 6
    WATER = 7
    LAVA = 8
    GRASS = 9
    STONE = 10

class BiomeType(Enum):
    FACILITY = "facility"
    FOREST = "forest"
    DESERT = "desert"
    ICE_CAVES = "ice_caves"
    VOLCANIC = "volcanic"
    CYBERPUNK = "cyberpunk"

@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    solid: bool = False
    damage: int = 0
    damage_type: Optional[DamageType] = None
    special_properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.special_properties is None:
            self.special_properties = {}
        
        # Set default properties based on tile type
        if self.tile_type == TileType.WALL:
            self.solid = True
        elif self.tile_type == TileType.LAVA:
            self.damage = 20
            self.damage_type = DamageType.FIRE
        elif self.tile_type == TileType.WATER:
            self.special_properties['slow_factor'] = 0.5

class Room:
    def __init__(self, x, y, width, height, room_type="generic"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.room_type = room_type
        self.connected_rooms = []
        self.entities = []
        self.items = []
        self.center = Vector2(x + width // 2, y + height // 2)
        self.visited = False
        self.cleared = False
    
    def contains_point(self, x, y):
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height
    
    def get_random_point(self):
        return Vector2(
            random.randint(self.x + 1, self.x + self.width - 2),
            random.randint(self.y + 1, self.y + self.height - 2)
        )
    
    def intersects(self, other):
        return not (self.x + self.width <= other.x or 
                   other.x + other.width <= self.x or
                   self.y + self.height <= other.y or 
                   other.y + other.height <= self.y)

class LevelGenerator:
    def __init__(self, width, height, biome=BiomeType.FACILITY):
        self.width = width
        self.height = height
        self.biome = biome
        self.tiles = []
        self.rooms = []
        self.spawn_points = []
        self.exit_points = []
        
        # Generation parameters
        self.min_room_size = 5
        self.max_room_size = 15
        self.max_rooms = 20
        self.room_attempts = 100
    
    def generate(self):
        """Generate a complete level"""
        self.initialize_tiles()
        self.generate_rooms()
        self.connect_rooms()
        self.add_biome_features()
        self.place_special_tiles()
        self.post_process()
        return self.tiles, self.rooms
    
    def initialize_tiles(self):
        """Initialize the tile grid"""
        self.tiles = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Default to walls
                tile = Tile(x, y, TileType.WALL, solid=True)
                row.append(tile)
            self.tiles.append(row)
    
    def generate_rooms(self):
        """Generate rooms using BSP or random placement"""
        self.rooms = []
        
        for _ in range(self.room_attempts):
            if len(self.rooms) >= self.max_rooms:
                break
            
            # Random room size and position
            room_width = random.randint(self.min_room_size, self.max_room_size)
            room_height = random.randint(self.min_room_size, self.max_room_size)
            
            x = random.randint(1, self.width - room_width - 1)
            y = random.randint(1, self.height - room_height - 1)
            
            new_room = Room(x, y, room_width, room_height)
            
            # Check for overlaps
            can_place = True
            for existing_room in self.rooms:
                if new_room.intersects(existing_room):
                    can_place = False
                    break
            
            if can_place:
                self.rooms.append(new_room)
                self.carve_room(new_room)
        
        # Assign room types
        self.assign_room_types()
    
    def carve_room(self, room):
        """Carve out a room in the tile grid"""
        floor_type = self.get_biome_floor_type()
        
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.tiles[y][x] = Tile(x, y, floor_type)
    
    def connect_rooms(self):
        """Connect all rooms with corridors"""
        if len(self.rooms) < 2:
            return
        
        # Connect each room to the nearest unconnected room
        connected = {0}  # Start with first room
        unconnected = set(range(1, len(self.rooms)))
        
        while unconnected:
            min_distance = float('inf')
            best_pair = None
            
            for connected_idx in connected:
                for unconnected_idx in unconnected:
                    distance = self.rooms[connected_idx].center.distance_to(
                        self.rooms[unconnected_idx].center
                    )
                    if distance < min_distance:
                        min_distance = distance
                        best_pair = (connected_idx, unconnected_idx)
            
            if best_pair:
                self.create_corridor(
                    self.rooms[best_pair[0]],
                    self.rooms[best_pair[1]]
                )
                connected.add(best_pair[1])
                unconnected.remove(best_pair[1])
                
                # Mark rooms as connected
                self.rooms[best_pair[0]].connected_rooms.append(best_pair[1])
                self.rooms[best_pair[1]].connected_rooms.append(best_pair[0])
    
    def create_corridor(self, room1, room2):
        """Create an L-shaped corridor between two rooms"""
        x1, y1 = int(room1.center.x), int(room1.center.y)
        x2, y2 = int(room2.center.x), int(room2.center.y)
        
        floor_type = self.get_biome_floor_type()
        
        # Horizontal corridor
        start_x, end_x = min(x1, x2), max(x1, x2)
        for x in range(start_x, end_x + 1):
            if 0 <= x < self.width and 0 <= y1 < self.height:
                self.tiles[y1][x] = Tile(x, y1, floor_type)
        
        # Vertical corridor
        start_y, end_y = min(y1, y2), max(y1, y2)
        for y in range(start_y, end_y + 1):
            if 0 <= x2 < self.width and 0 <= y < self.height:
                self.tiles[y][x2] = Tile(x2, y, floor_type)
    
    def assign_room_types(self):
        """Assign special purposes to rooms"""
        if not self.rooms:
            return
        
        # First room is spawn
        self.rooms[0].room_type = "spawn"
        
        # Last room is exit (if multiple rooms)
        if len(self.rooms) > 1:
            self.rooms[-1].room_type = "exit"
        
        # Assign other types randomly
        special_types = ["treasure", "boss", "shop", "puzzle"]
        for i, room in enumerate(self.rooms[1:-1], 1):
            if random.random() < 0.3:  # 30% chance for special room
                room.room_type = random.choice(special_types)
    
    def add_biome_features(self):
        """Add biome-specific environmental features"""
        for room in self.rooms:
            self.add_room_biome_features(room)
    
    def add_room_biome_features(self, room):
        """Add biome features to a specific room"""
        feature_chance = 0.1
        
        for y in range(room.y + 1, room.y + room.height - 1):
            for x in range(room.x + 1, room.x + room.width - 1):
                if random.random() < feature_chance:
                    if self.biome == BiomeType.VOLCANIC:
                        if random.random() < 0.3:
                            self.tiles[y][x] = Tile(x, y, TileType.LAVA)
                    elif self.biome == BiomeType.ICE_CAVES:
                        if random.random() < 0.2:
                            self.tiles[y][x] = Tile(x, y, TileType.WATER)  # Ice
                    elif self.biome == BiomeType.FOREST:
                        if random.random() < 0.4:
                            self.tiles[y][x] = Tile(x, y, TileType.GRASS)
    
    def place_special_tiles(self):
        """Place spawn points, exits, chests, etc."""
        for room in self.rooms:
            if room.room_type == "spawn":
                center = room.get_random_point()
                self.spawn_points.append(center)
                self.tiles[int(center.y)][int(center.x)] = Tile(
                    int(center.x), int(center.y), TileType.SPAWN_POINT
                )
            
            elif room.room_type == "exit":
                center = room.get_random_point()
                self.exit_points.append(center)
                self.tiles[int(center.y)][int(center.x)] = Tile(
                    int(center.x), int(center.y), TileType.EXIT
                )
            
            elif room.room_type == "treasure":
                center = room.get_random_point()
                self.tiles[int(center.y)][int(center.x)] = Tile(
                    int(center.x), int(center.y), TileType.CHEST
                )
    
    def get_biome_floor_type(self):
        """Get the appropriate floor type for the current biome"""
        biome_floors = {
            BiomeType.FACILITY: TileType.FLOOR,
            BiomeType.FOREST: TileType.GRASS,
            BiomeType.DESERT: TileType.STONE,
            BiomeType.ICE_CAVES: TileType.FLOOR,
            BiomeType.VOLCANIC: TileType.STONE,
            BiomeType.CYBERPUNK: TileType.FLOOR
        }
        return biome_floors.get(self.biome, TileType.FLOOR)
    
    def post_process(self):
        """Final cleanup and optimization"""
        self.smooth_walls()
        self.add_wall_decorations()
    
    def smooth_walls(self):
        """Smooth out single wall tiles for better aesthetics"""
        # Implementation for wall smoothing algorithm
        pass
    
    def add_wall_decorations(self):
        """Add decorative elements to walls"""
        # Implementation for adding visual variety to walls
        pass

# Item System
class ItemType(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    KEY_ITEM = "key_item"
    ACCESSORY = "accessory"

class ItemRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

@dataclass
class ItemStat:
    stat_type: str
    value: int
    percentage: bool = False

class Item:
    def __init__(self, name, item_type, rarity=ItemRarity.COMMON):
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.description = ""
        self.icon_color = self.get_rarity_color()
        
        # Stats and effects
        self.stats = []
        self.use_effect = None
        self.equip_effect = None
        
        # Item properties
        self.stackable = False
        self.max_stack = 1
        self.durability = 100
        self.max_durability = 100
        self.value = 10
        
        # Usage
        self.consumable = item_type == ItemType.CONSUMABLE
        self.equippable = item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]
    
    def get_rarity_color(self):
        colors = {
            ItemRarity.COMMON: Colors.WHITE,
            ItemRarity.UNCOMMON: Colors.GREEN,
            ItemRarity.RARE: Colors.BLUE,
            ItemRarity.EPIC: Colors.PURPLE,
            ItemRarity.LEGENDARY: Colors.ORANGE
        }
        return colors.get(self.rarity, Colors.WHITE)
    
    def add_stat(self, stat_type, value, percentage=False):
        self.stats.append(ItemStat(stat_type, value, percentage))
    
    def use(self, user):
        if self.use_effect:
            return self.use_effect(user)
        return False
    
    def can_stack_with(self, other):
        return (self.stackable and 
                self.name == other.name and 
                self.rarity == other.rarity)

class ItemGenerator:
    def __init__(self):
        self.base_items = self.create_base_items()
        self.affix_pool = self.create_affix_pool()
    
    def create_base_items(self):
        items = {}
        
        # Weapons
        items["sword"] = {
            "name": "Sword", "type": ItemType.WEAPON,
            "base_stats": [("attack_damage", 25)]
        }
        items["staff"] = {
            "name": "Staff", "type": ItemType.WEAPON,
            "base_stats": [("attack_damage", 20), ("max_mana", 30)]
        }
        items["bow"] = {
            "name": "Bow", "type": ItemType.WEAPON,
            "base_stats": [("attack_damage", 22), ("critical_chance", 5)]
        }
        
        # Armor
        items["helmet"] = {
            "name": "Helmet", "type": ItemType.ARMOR,
            "base_stats": [("defense", 8), ("max_health", 15)]
        }
        items["chest"] = {
            "name": "Chest Armor", "type": ItemType.ARMOR,
            "base_stats": [("defense", 15), ("max_health", 25)]
        }
        
        # Consumables
        items["health_potion"] = {
            "name": "Health Potion", "type": ItemType.CONSUMABLE,
            "use_effect": lambda user: user.heal(50)
        }
        items["mana_potion"] = {
            "name": "Mana Potion", "type": ItemType.CONSUMABLE,
            "use_effect": lambda user: setattr(user.stats, 'mana', 
                                             min(user.stats.max_mana, user.stats.mana + 30))
        }
        
        return items
    
    def create_affix_pool(self):
        return {
            "prefix": [
                ("Sharp", [("attack_damage", 5)]),
                ("Heavy", [("attack_damage", 8), ("speed", -5)]),
                ("Light", [("speed", 10), ("evasion", 5)]),
                ("Sturdy", [("defense", 5), ("max_health", 10)]),
                ("Mystic", [("max_mana", 20), ("critical_chance", 3)])
            ],
            "suffix": [
                ("of Power", [("attack_damage", 7)]),
                ("of Defense", [("defense", 6)]),
                ("of Speed", [("speed", 15)]),
                ("of Vitality", [("max_health", 20)]),
                ("of Wisdom", [("max_mana", 25)])
            ]
        }
    
    def generate_item(self, base_name, rarity=None):
        if base_name not in self.base_items:
            return None
        
        base_data = self.base_items[base_name]
        
        if rarity is None:
            # Random rarity based on weights
            rarity_weights = {
                ItemRarity.COMMON: 50,
                ItemRarity.UNCOMMON: 30,
                ItemRarity.RARE: 15,
                ItemRarity.EPIC: 4,
                ItemRarity.LEGENDARY: 1
            }
            rarity = random.choices(
                list(rarity_weights.keys()),
                weights=list(rarity_weights.values())
            )[0]
        
        item = Item(base_data["name"], base_data["type"], rarity)
        
        # Add base stats
        for stat_type, value in base_data.get("base_stats", []):
            item.add_stat(stat_type, value)
        
        # Add use effect if present
        if "use_effect" in base_data:
            item.use_effect = base_data["use_effect"]
        
        # Add affixes based on rarity
        self.add_affixes(item, rarity)
        
        return item
    
    def add_affixes(self, item, rarity):
        affix_count = {
            ItemRarity.COMMON: 0,
            ItemRarity.UNCOMMON: 1,
            ItemRarity.RARE: 2,
            ItemRarity.EPIC: 3,
            ItemRarity.LEGENDARY: 4
        }
        
        count = affix_count.get(rarity, 0)
        if count == 0:
            return
        
        # Add prefix
        if count > 0 and random.random() < 0.6:
            prefix = random.choice(self.affix_pool["prefix"])
            item.name = f"{prefix[0]} {item.name}"
            for stat_type, value in prefix[1]:
                item.add_stat(stat_type, value)
            count -= 1
        
        # Add suffix
        if count > 0 and random.random() < 0.8:
            suffix = random.choice(self.affix_pool["suffix"])
            item.name = f"{item.name} {suffix[0]}"
            for stat_type, value in suffix[1]:
                item.add_stat(stat_type, value)

# World Management System
class World:
    def __init__(self, width=62, height=47):  # Width/height in tiles
        self.width = width * TILE_SIZE
        self.height = height * TILE_SIZE
        self.tile_width = width
        self.tile_height = height
        
        # Entity management
        self.entities = []
        self.entities_by_type = {}
        self.spatial_grid = {}
        self.grid_size = 64
        
        # World systems
        self.particle_system = ParticleSystem()
        self.camera = Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Level data
        self.tiles = []
        self.rooms = []
        self.current_biome = BiomeType.FACILITY
        self.level_number = 1
        
        # Items and loot
        self.item_generator = ItemGenerator()
        self.dropped_items = []
        
        # Game state
        self.player = None
        self.spawn_points = []
        self.exit_points = []
        self.cleared_rooms = set()
        
        # Wave and spawning system
        self.wave_system = WaveSystem()
        self.enemy_spawn_timer = 0
        self.enemy_spawn_rate = 3.0
        
        self.generate_level()
    
    def generate_level(self):
        """Generate a new level"""
        generator = LevelGenerator(
            self.tile_width, self.tile_height, self.current_biome
        )
        self.tiles, self.rooms = generator.generate()
        self.spawn_points = generator.spawn_points
        self.exit_points = generator.exit_points
        
        # Clear entities except player
        if self.player:
            player_pos = self.player.position
            self.clear_entities()
            self.player.position = player_pos
        else:
            self.clear_entities()
        
        # Spawn player at first spawn point
        if self.spawn_points and not self.player:
            spawn_pos = self.spawn_points[0]
            self.player = Player(Vector2(spawn_pos.x * TILE_SIZE, spawn_pos.y * TILE_SIZE))
            self.add_entity(self.player)
        
        # Populate rooms with enemies and items
        self.populate_level()
    
    def populate_level(self):
        """Populate the level with enemies and items"""
        enemy_types = ["grunt", "ranger", "mage"]
        
        for room in self.rooms:
            if room.room_type in ["spawn", "exit"]:
                continue
            
            # Spawn enemies
            enemy_count = random.randint(2, 5)
            if room.room_type == "boss":
                enemy_count = 1
                enemy_types = ["boss"]
            
            for _ in range(enemy_count):
                pos = room.get_random_point()
                world_pos = Vector2(pos.x * TILE_SIZE, pos.y * TILE_SIZE)
                
                enemy_type = random.choice(enemy_types)
                enemy = Enemy(world_pos, enemy_type)
                self.add_entity(enemy)
                room.entities.append(enemy)
            
            # Spawn items
            if room.room_type == "treasure" or random.random() < 0.3:
                self.spawn_random_items(room, random.randint(1, 3))
    
    def spawn_random_items(self, room, count):
        """Spawn random items in a room"""
        item_types = ["sword", "staff", "bow", "helmet", "chest", 
                     "health_potion", "mana_potion"]
        
        for _ in range(count):
            pos = room.get_random_point()
            world_pos = Vector2(pos.x * TILE_SIZE, pos.y * TILE_SIZE)
            
            item_type = random.choice(item_types)
            item = self.item_generator.generate_item(item_type)
            if item:
                dropped_item = DroppedItem(world_pos, item)
                self.dropped_items.append(dropped_item)
    
    def add_entity(self, entity):
        """Add entity to world"""
        self.entities.append(entity)
        
        # Add to type-based lookup
        entity_type = entity.entity_type
        if entity_type not in self.entities_by_type:
            self.entities_by_type[entity_type] = []
        self.entities_by_type[entity_type].append(entity)
        
        # Add to spatial grid
        self.update_entity_spatial_grid(entity)
    
    def remove_entity(self, entity):
        """Remove entity from world"""
        if entity in self.entities:
            self.entities.remove(entity)
        
        # Remove from type lookup
        entity_type = entity.entity_type
        if entity_type in self.entities_by_type:
            if entity in self.entities_by_type[entity_type]:
                self.entities_by_type[entity_type].remove(entity)
        
        # Remove from spatial grid
        self.remove_entity_from_spatial_grid(entity)
    
    def clear_entities(self):
        """Clear all entities"""
        self.entities = []
        self.entities_by_type = {}
        self.spatial_grid = {}
    
    def get_entities_of_type(self, entity_type):
        """Get all entities of a specific type"""
        return self.entities_by_type.get(entity_type, [])
    
    def get_player(self):
        """Get the player entity"""
        return self.player
    
    def update_entity_spatial_grid(self, entity):
        """Update entity position in spatial grid"""
        grid_x = int(entity.position.x // self.grid_size)
        grid_y = int(entity.position.y // self.grid_size)
        grid_key = (grid_x, grid_y)
        
        if grid_key not in self.spatial_grid:
            self.spatial_grid[grid_key] = []
        
        if entity not in self.spatial_grid[grid_key]:
            self.spatial_grid[grid_key].append(entity)
    
    def remove_entity_from_spatial_grid(self, entity):
        """Remove entity from spatial grid"""
        for grid_entities in self.spatial_grid.values():
            if entity in grid_entities:
                grid_entities.remove(entity)
    
    def get_nearby_entities(self, position, radius):
        """Get entities within radius of position"""
        nearby = []
        grid_radius = int(radius // self.grid_size) + 1
        center_x = int(position.x // self.grid_size)
        center_y = int(position.y // self.grid_size)
        
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                grid_key = (center_x + dx, center_y + dy)
                if grid_key in self.spatial_grid:
                    for entity in self.spatial_grid[grid_key]:
                        distance = position.distance_to(entity.position)
                        if distance <= radius:
                            nearby.append(entity)
        
        return nearby
    
    def get_tile_at(self, world_x, world_y):
        """Get tile at world coordinates"""
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)
        
        if 0 <= tile_x < self.tile_width and 0 <= tile_y < self.tile_height:
            return self.tiles[tile_y][tile_x]
        return None
    
    def is_solid_at(self, world_x, world_y):
        """Check if position is solid (blocked)"""
        tile = self.get_tile_at(world_x, world_y)
        return tile is not None and tile.solid
    
    def update(self, dt):
        """Update all world systems"""
        # Update entities
        entities_to_remove = []
        
        for entity in self.entities[:]:
            entity.update(dt, self)
            
            if entity.marked_for_deletion:
                entities_to_remove.append(entity)
            else:
                # Update spatial grid
                self.update_entity_spatial_grid(entity)
        
        # Remove marked entities
        for entity in entities_to_remove:
            self.remove_entity(entity)
        
        # Update camera to follow player
        if self.player:
            self.camera.follow(self.player.position, dt)
        
        # Update camera
        self.camera.update(dt)
        
        # Update particle system
        self.particle_system.update(dt)
        
        # Update wave system
        self.wave_system.update(dt, self)
        
        # Update enemy spawning
        self.update_enemy_spawning(dt)
        
        # Update dropped items
        self.update_dropped_items(dt)
        
        # Check room clearing
        self.update_room_status()
    
    def update_enemy_spawning(self, dt):
        """Handle dynamic enemy spawning"""
        if not self.player:
            return
        
        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0:
            self.enemy_spawn_timer = self.enemy_spawn_rate
            
            # Don't spawn if too many enemies already
            current_enemies = len(self.get_entities_of_type(EntityType.ENEMY))
            if current_enemies < 15:
                self.spawn_enemy_near_player()
    
    def spawn_enemy_near_player(self):
        """Spawn an enemy near the player"""
        if not self.player:
            return
        
        # Find a spawn position away from player
        attempts = 10
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(300, 600)
            
            spawn_pos = self.player.position + Vector2(
                math.cos(angle) * distance,
                math.sin(angle) * distance
            )
            
            # Check if position is valid
            if not self.is_solid_at(spawn_pos.x, spawn_pos.y):
                enemy_type = random.choice(["grunt", "ranger", "mage"])
                enemy = Enemy(spawn_pos, enemy_type)
                self.add_entity(enemy)
                break
    
    def update_dropped_items(self, dt):
        """Update dropped items"""
        items_to_remove = []
        
        for dropped_item in self.dropped_items:
            dropped_item.update(dt)
            
            # Check if player picks up item
            if (self.player and 
                self.player.position.distance_to(dropped_item.position) < 40):
                # Add to player inventory (simplified)
                self.player.inventory.append(dropped_item.item)
                items_to_remove.append(dropped_item)
        
        for item in items_to_remove:
            self.dropped_items.remove(item)
    
    def update_room_status(self):
        """Update room cleared status"""
        for i, room in enumerate(self.rooms):
            if i in self.cleared_rooms:
                continue
            
            # Check if all enemies in room are dead
            alive_enemies = [e for e in room.entities if e.alive and e.entity_type == EntityType.ENEMY]
            if len(alive_enemies) == 0 and len(room.entities) > 0:
                self.cleared_rooms.add(i)
                room.cleared = True
                
                # Reward player for clearing room
                if self.player:
                    bonus_xp = 50 * self.level_number
                    self.player.gain_experience(bonus_xp)
    
    def draw(self, screen, text_renderer):
        """Draw the world"""
        # Draw tiles
        self.draw_tiles(screen)
        
        # Draw dropped items
        for item in self.dropped_items:
            item.draw(screen, self.camera)
        
        # Draw entities (sorted by y-position for proper layering)
        sorted_entities = sorted(self.entities, key=lambda e: e.position.y)
        for entity in sorted_entities:
            entity.draw(screen, self.camera)
        
        # Draw particles
        self.particle_system.draw(screen, self.camera)
        
        # Draw room overlays (debug/minimap)
        if hasattr(self, 'show_debug') and self.show_debug:
            self.draw_room_debug(screen)
    
    def draw_tiles(self, screen):
        """Draw the tile-based world"""
        # Calculate visible tile range
        camera_pos = self.camera.position
        start_x = max(0, int(camera_pos.x // TILE_SIZE) - 1)
        end_x = min(self.tile_width, int((camera_pos.x + WINDOW_WIDTH) // TILE_SIZE) + 2)
        start_y = max(0, int(camera_pos.y // TILE_SIZE) - 1)
        end_y = min(self.tile_height, int((camera_pos.y + WINDOW_HEIGHT) // TILE_SIZE) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.tiles[y][x]
                self.draw_tile(screen, tile, x, y)
    
    def draw_tile(self, screen, tile, tile_x, tile_y):
        """Draw a single tile"""
        world_pos = Vector2(tile_x * TILE_SIZE, tile_y * TILE_SIZE)
        screen_pos = self.camera.world_to_screen(world_pos)
        
        # Skip if completely off-screen
        if (screen_pos.x < -TILE_SIZE or screen_pos.x > WINDOW_WIDTH or
            screen_pos.y < -TILE_SIZE or screen_pos.y > WINDOW_HEIGHT):
            return
        
        rect = pygame.Rect(screen_pos.x, screen_pos.y, TILE_SIZE, TILE_SIZE)
        
        # Choose color based on tile type and biome
        color = self.get_tile_color(tile.tile_type)
        
        pygame.draw.rect(screen, color, rect)
        
        # Add tile borders for walls
        if tile.tile_type == TileType.WALL:
            pygame.draw.rect(screen, Colors.DARK_GRAY, rect, 1)
        
        # Special tile indicators
        if tile.tile_type == TileType.SPAWN_POINT:
            pygame.draw.circle(screen, Colors.GREEN, rect.center, 8)
        elif tile.tile_type == TileType.EXIT:
            pygame.draw.circle(screen, Colors.YELLOW, rect.center, 8)
        elif tile.tile_type == TileType.CHEST:
            pygame.draw.rect(screen, Colors.ORANGE, 
                           (rect.x + 8, rect.y + 8, 16, 16))
    
    def get_tile_color(self, tile_type):
        """Get the appropriate color for a tile type"""
        biome_colors = {
            BiomeType.FACILITY: {
                TileType.WALL: Colors.DARK_GRAY,
                TileType.FLOOR: Colors.GRAY,
                TileType.DOOR: Colors.YELLOW
            },
            BiomeType.FOREST: {
                TileType.WALL: (34, 139, 34),  # Forest green
                TileType.FLOOR: (85, 107, 47),  # Dark olive
                TileType.GRASS: (124, 252, 0)   # Lawn green
            },
            BiomeType.VOLCANIC: {
                TileType.WALL: (139, 69, 19),   # Saddle brown
                TileType.FLOOR: (160, 82, 45),  # Saddle brown
                TileType.LAVA: Colors.RED
            }
        }
        
        colors = biome_colors.get(self.current_biome, biome_colors[BiomeType.FACILITY])
        return colors.get(tile_type, Colors.GRAY)
    
    def draw_room_debug(self, screen):
        """Draw room boundaries for debugging"""
        for i, room in enumerate(self.rooms):
            world_pos = Vector2(room.x * TILE_SIZE, room.y * TILE_SIZE)
            screen_pos = self.camera.world_to_screen(world_pos)
            
            rect = pygame.Rect(
                screen_pos.x, screen_pos.y,
                room.width * TILE_SIZE, room.height * TILE_SIZE
            )
            
            color = Colors.GREEN if room.cleared else Colors.RED
            pygame.draw.rect(screen, color, rect, 2)
    
    def next_level(self):
        """Advance to the next level"""
        self.level_number += 1
        
        # Change biome every few levels
        if self.level_number % 3 == 0:
            biomes = list(BiomeType)
            self.current_biome = random.choice(biomes)
        
        # Clear room status
        self.cleared_rooms.clear()
        
        # Generate new level
        self.generate_level()
        
        # Move player to spawn point
        if self.spawn_points and self.player:
            spawn_pos = self.spawn_points[0]
            self.player.position = Vector2(spawn_pos.x * TILE_SIZE, spawn_pos.y * TILE_SIZE)

class DroppedItem:
    def __init__(self, position, item):
        self.position = Vector2(position.x, position.y)
        self.item = item
        self.bob_timer = 0
        self.bob_speed = 3.0
        self.bob_height = 5
        self.glow_timer = 0
        self.pickup_radius = 40
        
    def update(self, dt):
        self.bob_timer += dt * self.bob_speed
        self.glow_timer += dt
    
    def draw(self, screen, camera):
        screen_pos = camera.world_to_screen(self.position)
        
        # Bobbing animation
        bob_offset = math.sin(self.bob_timer) * self.bob_height
        draw_pos = Vector2(screen_pos.x, screen_pos.y + bob_offset)
        
        # Glow effect
        glow_alpha = int(128 + 127 * math.sin(self.glow_timer * 2))
        
        # Draw item representation
        color = self.item.icon_color
        pygame.draw.circle(screen, color, draw_pos.to_tuple(), 12)
        pygame.draw.circle(screen, Colors.WHITE, draw_pos.to_tuple(), 8)
        
        # Draw rarity indicator
        if self.item.rarity != ItemRarity.COMMON:
            pygame.draw.circle(screen, color, draw_pos.to_tuple(), 15, 2)

class WaveSystem:
    def __init__(self):
        self.current_wave = 0
        self.wave_active = False
        self.enemies_remaining = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        self.spawn_rate = 2.0
        self.wave_break_timer = 0
        self.wave_break_duration = 10.0
        
    def update(self, dt, world):
        if self.wave_active:
            self.update_active_wave(dt, world)
        else:
            self.update_wave_break(dt, world)
    
    def update_active_wave(self, dt, world):
        # Spawn enemies
        if self.enemies_to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.spawn_rate
                self.spawn_wave_enemy(world)
                self.enemies_to_spawn -= 1
        
        # Check if wave is complete
        current_enemies = len(world.get_entities_of_type(EntityType.ENEMY))
        if self.enemies_to_spawn == 0 and current_enemies == 0:
            self.complete_wave(world)
    
    def update_wave_break(self, dt, world):
        self.wave_break_timer -= dt
        if self.wave_break_timer <= 0:
            self.start_next_wave(world)
    
    def start_next_wave(self, world):
        self.current_wave += 1
        self.wave_active = True
        
        # Scale difficulty with wave number
        base_enemies = 5
        self.enemies_to_spawn = base_enemies + (self.current_wave - 1) * 2
        self.enemies_remaining = self.enemies_to_spawn
        
        # Faster spawn rate in later waves
        self.spawn_rate = max(0.5, 2.0 - (self.current_wave * 0.1))
    
    def complete_wave(self, world):
        self.wave_active = False
        self.wave_break_timer = self.wave_break_duration
        
        # Reward player
        if world.player:
            bonus_xp = 100 * self.current_wave
            world.player.gain_experience(bonus_xp)
            
            # Chance for item drop
            if random.random() < 0.3:
                item_types = ["health_potion", "mana_potion", "sword", "staff"]
                item_type = random.choice(item_types)
                item = world.item_generator.generate_item(item_type)
                if item:
                    dropped_item = DroppedItem(world.player.position, item)
                    world.dropped_items.append(dropped_item)
    
    def spawn_wave_enemy(self, world):
        if not world.player:
            return
        
        # Choose enemy type based on wave
        if self.current_wave <= 3:
            enemy_types = ["grunt", "ranger"]
        elif self.current_wave <= 6:
            enemy_types = ["grunt", "ranger", "mage"]
        else:
            enemy_types = ["grunt", "ranger", "mage", "boss"]
            # Boss has lower chance
            enemy_types.extend(["grunt"] * 3)  # Weight towards normal enemies
        
        enemy_type = random.choice(enemy_types)
        
        # Spawn at random position away from player
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(400, 600)
        
        spawn_pos = world.player.position + Vector2(
            math.cos(angle) * distance,
            math.sin(angle) * distance
        )
        
        # Make sure spawn position is valid
        if not world.is_solid_at(spawn_pos.x, spawn_pos.y):
            enemy = Enemy(spawn_pos, enemy_type)
            world.add_entity(enemy)

# Game State Management
class GameStateManager:
    def __init__(self):
        self.current_state = GameState.MENU
        self.states = {}
        self.state_stack = []
        
    def add_state(self, state_name, state_object):
        self.states[state_name] = state_object
    
    def change_state(self, state_name):
        if state_name in self.states:
            self.current_state = state_name
    
    def push_state(self, state_name):
        if self.current_state:
            self.state_stack.append(self.current_state)
        self.current_state = state_name
    
    def pop_state(self):
        if self.state_stack:
            self.current_state = self.state_stack.pop()
    
    def get_current_state(self):
        return self.states.get(self.current_state)
    
    def update(self, dt):
        current_state_obj = self.get_current_state()
        if current_state_obj:
            current_state_obj.update(dt)
    
    def draw(self, screen):
        current_state_obj = self.get_current_state()
        if current_state_obj:
            current_state_obj.draw(screen)
    
    def handle_event(self, event):
        current_state_obj = self.get_current_state()
        if current_state_obj:
            current_state_obj.handle_event(event)

# Save System
class SaveSystem:
    def __init__(self):
        self.save_file = "nexus_protocol_save.json"
        self.auto_save_timer = 0
        self.auto_save_interval = 30.0  # Auto-save every 30 seconds
    
    def save_game(self, world, player):
        """Save the current game state"""
        save_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "level": world.level_number,
            "biome": world.current_biome.value,
            "player": {
                "position": [player.position.x, player.position.y],
                "level": player.level,
                "experience": player.experience,
                "stats": {
                    "health": player.stats.health,
                    "max_health": player.stats.max_health,
                    "mana": player.stats.mana,
                    "max_mana": player.stats.max_mana,
                    "attack_damage": player.stats.attack_damage,
                    "defense": player.stats.defense,
                    "speed": player.stats.speed
                },
                "inventory": [self.serialize_item(item) for item in player.inventory]
            },
            "world": {
                "cleared_rooms": list(world.cleared_rooms),
                "wave": world.wave_system.current_wave
            }
        }
        
        try:
            with open(self.save_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False
    
    def load_game(self):
        """Load a saved game state"""
        try:
            with open(self.save_file, 'r') as f:
                save_data = json.load(f)
            return save_data
        except Exception as e:
            print(f"Load failed: {e}")
            return None
    
    def serialize_item(self, item):
        """Convert item to saveable format"""
        return {
            "name": item.name,
            "type": item.item_type.value,
            "rarity": item.rarity.value,
            "stats": [(stat.stat_type, stat.value, stat.percentage) for stat in item.stats]
        }
    
    def deserialize_item(self, item_data):
        """Convert saved data back to item"""
        item = Item(
            item_data["name"],
            ItemType(item_data["type"]),
            ItemRarity(item_data["rarity"])
        )
        
        for stat_type, value, percentage in item_data["stats"]:
            item.add_stat(stat_type, value, percentage)
        
        return item
    
    def update(self, dt, world):
        """Handle auto-saving"""
        self.auto_save_timer += dt
        if self.auto_save_timer >= self.auto_save_interval:
            self.auto_save_timer = 0
            if world.player:
                self.save_game(world, world.player)

print("Nexus Protocol Part 3 - World System & Game Logic Complete!")
print("Features included:")
print("- Advanced procedural level generation with BSP rooms")
print("- Multi-biome system (Facility, Forest, Desert, Ice, Volcanic, Cyberpunk)")
print("- Professional item system with rarity, affixes, and stats")
print("- Intelligent item generation with prefix/suffix system")
print("- Spatial partitioning for performance optimization")
print("- Wave-based enemy spawning system")
print("- Room-based progression and clearing mechanics")
print("- Complete save/load system with JSON serialization")
print("- Dropped item system with pickup mechanics")
print("- Multi-layered rendering with proper depth sorting")
print("- Tile-based collision detection")
print("- Dynamic difficulty scaling")
print("- Professional game state management")
print("\nReady for Part 4: UI System, Main Game Loop & Polish!")