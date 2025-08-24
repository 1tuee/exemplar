 #* GUI/UX
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import simpledialog
from tkinter import ttk
#* general backend
import redis 
import sqlite3
#? misc
import socket
import struct
import threading
import os
import sys
import time
import zlib
import ctypes
import mmap
import gzip
#*crypto and hashing
import hashlib
import secrets

import pygame
import random
import sys
import math

import pygame
import random
import math
import sys

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 150, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)

class Player:
    def __init__(self):
        self.rect = pygame.Rect(WINDOW_WIDTH // 2 - 15, WINDOW_HEIGHT - 60, 30, 40)
        self.speed = 7
        self.energy = 100
        self.max_energy = 100
        self.shield_active = False
        self.shield_energy = 0
        self.max_shield_energy = 50
        self.weapon_type = 0  # 0: normal, 1: spread, 2: laser
        self.weapon_timer = 0
        
    def move(self, keys):
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < WINDOW_WIDTH:
            self.rect.x += self.speed
        if keys[pygame.K_UP] and self.rect.top > WINDOW_HEIGHT // 2:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.bottom < WINDOW_HEIGHT:
            self.rect.y += self.speed
    
    def activate_shield(self):
        if self.energy >= 20 and not self.shield_active:
            self.energy -= 20
            self.shield_active = True
            self.shield_energy = self.max_shield_energy
    
    def update(self):
        if self.shield_active:
            self.shield_energy -= 1
            if self.shield_energy <= 0:
                self.shield_active = False
        
        # Regenerate energy slowly
        if self.energy < self.max_energy:
            self.energy += 0.2
        
        # Update weapon timer
        if self.weapon_timer > 0:
            self.weapon_timer -= 1
    
    def draw(self, screen):
        # Draw ship
        points = [
            (self.rect.centerx, self.rect.top),
            (self.rect.left, self.rect.bottom),
            (self.rect.centerx, self.rect.bottom - 10),
            (self.rect.right, self.rect.bottom)
        ]
        pygame.draw.polygon(screen, CYAN, points)
        
        # Draw shield
        if self.shield_active:
            pygame.draw.circle(screen, BLUE, self.rect.center, 30, 3)

class Bullet:
    def __init__(self, x, y, angle=0, speed=10):
        self.rect = pygame.Rect(x-2, y-5, 4, 10)
        self.speed = speed
        self.angle = angle
        self.vel_x = math.sin(angle) * speed
        self.vel_y = -math.cos(angle) * speed
    
    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        return self.rect.bottom < 0 or self.rect.top > WINDOW_HEIGHT or \
               self.rect.right < 0 or self.rect.left > WINDOW_WIDTH
    
    def draw(self, screen):
        pygame.draw.rect(screen, YELLOW, self.rect)

class Enemy:
    def __init__(self, enemy_type):
        self.type = enemy_type
        self.health = 1
        
        if enemy_type == "asteroid":
            size = random.randint(20, 40)
            self.rect = pygame.Rect(random.randint(0, WINDOW_WIDTH-size), -size, size, size)
            self.speed = random.randint(2, 4)
            self.rotation = 0
            self.rotation_speed = random.randint(-5, 5)
            self.health = 2
            self.points = 10
            
        elif enemy_type == "alien":
            self.rect = pygame.Rect(random.randint(0, WINDOW_WIDTH-25), -30, 25, 20)
            self.speed = random.randint(3, 6)
            self.shoot_timer = random.randint(30, 90)
            self.health = 1
            self.points = 25
            
        elif enemy_type == "boss":
            self.rect = pygame.Rect(WINDOW_WIDTH//2 - 40, -80, 80, 60)
            self.speed = 2
            self.shoot_timer = 20
            self.health = 10
            self.points = 100
            self.move_direction = 1
    
    def update(self):
        if self.type == "asteroid":
            self.rect.y += self.speed
            self.rotation += self.rotation_speed
            
        elif self.type == "alien":
            self.rect.y += self.speed
            # Zigzag movement
            self.rect.x += math.sin(self.rect.y * 0.02) * 2
            self.shoot_timer -= 1
            
        elif self.type == "boss":
            self.rect.y += self.speed
            if self.rect.y > 50:
                self.rect.x += self.move_direction * 3
                if self.rect.left <= 0 or self.rect.right >= WINDOW_WIDTH:
                    self.move_direction *= -1
                self.shoot_timer -= 1
        
        return self.rect.top > WINDOW_HEIGHT
    
    def can_shoot(self):
        return (self.type == "alien" and self.shoot_timer <= 0) or \
               (self.type == "boss" and self.shoot_timer <= 0)
    
    def shoot(self):
        if self.type == "alien":
            self.shoot_timer = random.randint(60, 120)
            return [EnemyBullet(self.rect.centerx, self.rect.bottom)]
        elif self.type == "boss":
            self.shoot_timer = 30
            bullets = []
            for angle in [-0.5, 0, 0.5]:
                bullets.append(EnemyBullet(self.rect.centerx, self.rect.bottom, angle))
            return bullets
        return []
    
    def draw(self, screen):
        if self.type == "asteroid":
            color = GRAY if self.health > 1 else RED
            pygame.draw.circle(screen, color, self.rect.center, self.rect.width//2)
            
        elif self.type == "alien":
            pygame.draw.ellipse(screen, GREEN, self.rect)
            pygame.draw.ellipse(screen, RED, (self.rect.x+5, self.rect.y+5, 15, 10))
            
        elif self.type == "boss":
            pygame.draw.rect(screen, PURPLE, self.rect)
            pygame.draw.rect(screen, RED, (self.rect.x+10, self.rect.y+10, 60, 40))
            # Health bar
            health_width = (self.health / 10) * self.rect.width
            pygame.draw.rect(screen, GREEN, (self.rect.x, self.rect.y-10, health_width, 5))

class EnemyBullet:
    def __init__(self, x, y, angle=0):
        self.rect = pygame.Rect(x-2, y, 4, 8)
        self.speed = 6
        self.angle = angle
        self.vel_x = math.sin(angle) * self.speed
        self.vel_y = math.cos(angle) * self.speed
    
    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.speed + self.vel_y
        return self.rect.top > WINDOW_HEIGHT
    
    def draw(self, screen):
        pygame.draw.rect(screen, RED, self.rect)

class PowerUp:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x-10, y-10, 20, 20)
        self.type = random.choice(["energy", "shield", "weapon"])
        self.speed = 3
        self.glow = 0
    
    def update(self):
        self.rect.y += self.speed
        self.glow = (self.glow + 5) % 360
        return self.rect.top > WINDOW_HEIGHT
    
    def draw(self, screen):
        color = GREEN if self.type == "energy" else BLUE if self.type == "shield" else ORANGE
        glow_size = 15 + math.sin(math.radians(self.glow)) * 3
        pygame.draw.circle(screen, color, self.rect.center, int(glow_size))
        
        # Draw symbol
        if self.type == "energy":
            pygame.draw.rect(screen, WHITE, (self.rect.centerx-2, self.rect.centery-6, 4, 12))
            pygame.draw.rect(screen, WHITE, (self.rect.centerx-6, self.rect.centery-2, 12, 4))
        elif self.type == "shield":
            pygame.draw.circle(screen, WHITE, self.rect.center, 8, 2)
        else:  # weapon
            pygame.draw.rect(screen, WHITE, (self.rect.centerx-1, self.rect.centery-6, 2, 12))

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cosmic Defender")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.enemy_bullets = []
        self.powerups = []
        
        self.score = 0
        self.wave = 1
        self.enemies_spawned = 0
        self.enemies_this_wave = 5
        self.spawn_timer = 0
        self.boss_spawned = False
        
        self.game_over = False
        self.paused = False
        
        # Background stars
        self.stars = [(random.randint(0, WINDOW_WIDTH), random.randint(0, WINDOW_HEIGHT)) 
                     for _ in range(100)]
    
    def spawn_enemy(self):
        if self.enemies_spawned < self.enemies_this_wave:
            if self.wave % 5 == 0 and not self.boss_spawned:
                # Boss wave
                self.enemies.append(Enemy("boss"))
                self.boss_spawned = True
                self.enemies_spawned = self.enemies_this_wave
            else:
                enemy_type = random.choices(
                    ["asteroid", "alien"], 
                    weights=[70, 30] if self.wave < 3 else [50, 50]
                )[0]
                self.enemies.append(Enemy(enemy_type))
                self.enemies_spawned += 1
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not self.game_over:
                    self.shoot()
                elif event.key == pygame.K_LSHIFT:
                    self.player.activate_shield()
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                elif event.key == pygame.K_r and self.game_over:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    return False
        
        return True
    
    def shoot(self):
        if self.player.energy >= 5:
            self.player.energy -= 5
            
            if self.player.weapon_type == 0:  # Normal
                self.bullets.append(Bullet(self.player.rect.centerx, self.player.rect.top))
            elif self.player.weapon_type == 1:  # Spread
                for angle in [-0.3, 0, 0.3]:
                    self.bullets.append(Bullet(self.player.rect.centerx, self.player.rect.top, angle))
            elif self.player.weapon_type == 2:  # Laser
                for i in range(3):
                    self.bullets.append(Bullet(self.player.rect.centerx, self.player.rect.top - i*20, 0, 15))
    
    def update(self):
        if self.paused or self.game_over:
            return
        
        keys = pygame.key.get_pressed()
        self.player.move(keys)
        self.player.update()
        
        # Spawn enemies
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            self.spawn_timer = max(30 - self.wave * 2, 10)
        
        # Update bullets
        self.bullets = [bullet for bullet in self.bullets if not bullet.update()]
        self.enemy_bullets = [bullet for bullet in self.enemy_bullets if not bullet.update()]
        
        # Update enemies and handle shooting
        for enemy in self.enemies[:]:
            if enemy.update():
                self.enemies.remove(enemy)
            elif enemy.can_shoot():
                self.enemy_bullets.extend(enemy.shoot())
        
        # Update powerups
        self.powerups = [powerup for powerup in self.powerups if not powerup.update()]
        
        # Check collisions
        self.check_collisions()
        
        # Check wave completion
        if self.enemies_spawned >= self.enemies_this_wave and len(self.enemies) == 0:
            self.wave += 1
            self.enemies_spawned = 0
            self.enemies_this_wave = 5 + self.wave * 2
            self.boss_spawned = False
        
        # Update stars
        self.stars = [(x, (y + 2) % WINDOW_HEIGHT) for x, y in self.stars]
    
    def check_collisions(self):
        # Player bullets vs enemies
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if bullet.rect.colliderect(enemy.rect):
                    self.bullets.remove(bullet)
                    enemy.health -= 1
                    if enemy.health <= 0:
                        self.enemies.remove(enemy)
                        self.score += enemy.points
                        # Chance to drop powerup
                        if random.random() < 0.15:
                            self.powerups.append(PowerUp(enemy.rect.centerx, enemy.rect.centery))
                    break
        
        # Enemy bullets vs player
        for bullet in self.enemy_bullets[:]:
            if bullet.rect.colliderect(self.player.rect):
                if self.player.shield_active:
                    self.player.shield_energy -= 10
                    if self.player.shield_energy <= 0:
                        self.player.shield_active = False
                else:
                    self.player.energy -= 20
                self.enemy_bullets.remove(bullet)
        
        # Enemies vs player
        for enemy in self.enemies:
            if enemy.rect.colliderect(self.player.rect):
                if self.player.shield_active:
                    self.player.shield_energy -= 20
                    if self.player.shield_energy <= 0:
                        self.player.shield_active = False
                else:
                    self.player.energy -= 30
        
        # Powerups vs player
        for powerup in self.powerups[:]:
            if powerup.rect.colliderect(self.player.rect):
                self.powerups.remove(powerup)
                if powerup.type == "energy":
                    self.player.energy = min(self.player.max_energy, self.player.energy + 30)
                elif powerup.type == "shield":
                    self.player.energy = min(self.player.max_energy, self.player.energy + 20)
                else:  # weapon
                    self.player.weapon_type = (self.player.weapon_type + 1) % 3
                    self.player.weapon_timer = 300  # 5 seconds at 60 FPS
        
        # Check game over
        if self.player.energy <= 0:
            self.game_over = True
    
    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw stars
        for star in self.stars:
            pygame.draw.circle(self.screen, WHITE, star, 1)
        
        # Draw game objects
        self.player.draw(self.screen)
        
        for bullet in self.bullets:
            bullet.draw(self.screen)
        
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen)
        
        for enemy in self.enemies:
            enemy.draw(self.screen)
        
        for powerup in self.powerups:
            powerup.draw(self.screen)
        
        # Draw UI
        self.draw_ui()
        
        if self.paused:
            pause_text = self.font.render("PAUSED - Press P to continue", True, WHITE)
            pause_rect = pause_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            self.screen.blit(pause_text, pause_rect)
        
        if self.game_over:
            game_over_text = self.font.render("GAME OVER", True, RED)
            restart_text = self.small_font.render("Press R to restart", True, WHITE)
            final_score = self.font.render(f"Final Score: {self.score}", True, WHITE)
            
            go_rect = game_over_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 30))
            restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 30))
            score_rect = final_score.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            
            self.screen.blit(game_over_text, go_rect)
            self.screen.blit(restart_text, restart_rect)
            self.screen.blit(final_score, score_rect)
        
        pygame.display.flip()
    
    def draw_ui(self):
        # Energy bar
        energy_width = (self.player.energy / self.player.max_energy) * 200
        pygame.draw.rect(self.screen, RED, (20, 20, 200, 20))
        pygame.draw.rect(self.screen, GREEN, (20, 20, energy_width, 20))
        energy_text = self.small_font.render("Energy", True, WHITE)
        self.screen.blit(energy_text, (20, 45))
        
        # Score and wave
        score_text = self.small_font.render(f"Score: {self.score}", True, WHITE)
        wave_text = self.small_font.render(f"Wave: {self.wave}", True, WHITE)
        self.screen.blit(score_text, (20, 70))
        self.screen.blit(wave_text, (20, 95))
        
        # Weapon type
        weapon_names = ["Normal", "Spread", "Laser"]
        weapon_text = self.small_font.render(f"Weapon: {weapon_names[self.player.weapon_type]}", True, WHITE)
        self.screen.blit(weapon_text, (20, 120))
        
        # Controls
        controls = [
            "Arrow Keys: Move",
            "Space: Shoot",
            "Shift: Shield",
            "P: Pause"
        ]
        
        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, GRAY)
            self.screen.blit(text, (WINDOW_WIDTH - 150, 20 + i * 25))
    
    def reset_game(self):
        self.player = Player()
        self.bullets = []
        self.enemies = []
        self.enemy_bullets = []
        self.powerups = []
        self.score = 0
        self.wave = 1
        self.enemies_spawned = 0
        self.enemies_this_wave = 5
        self.boss_spawned = False
        self.game_over = False
        self.paused = False
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()