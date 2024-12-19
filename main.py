import pygame
import numpy as np
from math import pi
import os
from datetime import datetime
import time

# Initialize Pygame
pygame.init()

# Constants
WIDTH = 800
HEIGHT = 600
FPS = 60
DEFAULT_SPEED = 1.0
SPEED_INCREMENT = 0.1

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)

# Setup display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Fourier Drawing")
clock = pygame.time.Clock()

class DrawPoint:
    def __init__(self, pos, timestamp):
        self.pos = pos
        self.timestamp = timestamp

class Path:
    def __init__(self):
        self.raw_points = []  # Stores DrawPoints with timestamps
        self.epicycles = []
        self.animation_points = []  # Points drawn during animation
        self.display_index = 0      # Current display position
        self.state = "drawing"      # states: drawing, animating, complete
        self.time = 0              # Animation time from 0 to 1

    def add_point(self, pos):
        current_time = time.time()
        self.raw_points.append(DrawPoint(pos, current_time))

    def calculate_fourier(self):
        if len(self.raw_points) < 2:
            return

        # Convert to complex numbers directly from raw points
        complex_points = [complex(p.pos[0] - WIDTH/2, p.pos[1] - HEIGHT/2) for p in self.raw_points]
        N = len(complex_points)
        
        # Calculate Fourier coefficients
        self.epicycles = []
        for n in range(-N//2, N//2):
            c = 0
            for k in range(N):
                c += complex_points[k] * np.exp(-2j * pi * n * k / N)
            c = c / N
            if abs(c) > 1:  # Filter small coefficients
                self.epicycles.append((n, c))
                
        self.epicycles.sort(key=lambda x: abs(x[1]), reverse=True)

    def calculate_point(self, t):
        x, y = WIDTH/2, HEIGHT/2
        
        for n, c in self.epicycles:
            radius = abs(c)
            angle = 2 * pi * n * t + np.angle(c)
            x += radius * np.cos(angle)
            y += radius * np.sin(angle)
            
        return (x, y)

    def draw_epicycles(self, screen, t):
        x, y = WIDTH/2, HEIGHT/2
        center = (x, y)
        
        for n, c in self.epicycles:
            prev_center = center
            radius = abs(c)
            angle = 2 * pi * n * t + np.angle(c)
            
            x = prev_center[0] + radius * np.cos(angle)
            y = prev_center[1] + radius * np.sin(angle)
            center = (x, y)
            
            pygame.draw.circle(screen, WHITE, (int(prev_center[0]), int(prev_center[1])), int(radius), 1)
            pygame.draw.line(screen, WHITE, prev_center, center, 1)
            
        return center

    def animate(self, screen, speed):
        if self.state == "animating":
            point = self.draw_epicycles(screen, self.time)
            self.animation_points.append(point)
            
            # Draw path up to current point
            if len(self.animation_points) > 1:
                pygame.draw.lines(screen, RED, False, self.animation_points, 1)
            
            # Update time based on speed and number of points
            self.time += (1.0 / len(self.raw_points)) * speed
            if self.time >= 1:
                self.time = 0
                self.state = "complete"

    def draw_complete(self, screen):
        if len(self.animation_points) > 1:
            pygame.draw.lines(screen, RED, False, self.animation_points, 1)

    def draw_original(self, screen):
        """Draw the original recorded points"""
        if len(self.raw_points) > 1:
            points = [p.pos for p in self.raw_points]
            pygame.draw.lines(screen, DARK_GRAY, False, points, 1)

    def complete_animation(self):
        """Skip to end of animation"""
        if self.state == "animating":
            self.state = "complete"

class FourierDrawing:
    def __init__(self):
        self.paths = []
        self.current_path = None
        self.show_help = False
        self.help_rect = None
        self.animating_all = False
        self.current_animation_index = 0
        self.animation_speed = DEFAULT_SPEED
        self.completed_paths = []
        self.show_original = False
        
    def start_new_path(self, clear_existing=False):
        if clear_existing:
            self.paths = []
            self.completed_paths = []
            self.animating_all = False
        self.current_path = Path()

    def complete_all_animations(self):
        """Skip to end of all current animations"""
        for path in self.paths:
            path.complete_animation()
        if self.animating_all:
            for path in self.remaining_paths:
                path.complete_animation()
            self.paths.extend(self.remaining_paths)
            self.remaining_paths = []
            self.animating_all = False
        
    def finish_current_path(self):
        if self.current_path and len(self.current_path.raw_points) > 1:
            self.current_path.calculate_fourier()
            self.current_path.state = "animating"
            self.paths.append(self.current_path)
        self.current_path = None

    def draw_help(self, screen):
        if self.show_help:
            help_text = [
                "Controls:",
                "Left Click - Clear and draw new path",
                "Right Click - Add new path (or complete animation)",
                "Scroll Wheel - Adjust animation speed",
                "Space - Reanimate all paths",
                "G - Toggle original drawing overlay",
                "Backspace/Delete - Clear canvas",
                "ESC - Exit program",
                "H - Toggle help",
                "Enter - Save current view",
                "",
                "Click anywhere to close"
            ]
            
            font = pygame.font.Font(None, 24)
            line_height = 25
            padding = 20
            
            width = max(font.render(line, True, WHITE).get_width() for line in help_text) + padding * 2
            height = len(help_text) * line_height + padding * 2
            
            x = (WIDTH - width) // 2
            y = (HEIGHT - height) // 2
            
            self.help_rect = pygame.Rect(x, y, width, height)
            pygame.draw.rect(screen, GRAY, self.help_rect)
            pygame.draw.rect(screen, WHITE, self.help_rect, 2)
            
            y_pos = y + padding
            for line in help_text:
                text = font.render(line, True, WHITE)
                screen.blit(text, (x + padding, y_pos))
                y_pos += line_height

    def draw_speed_indicator(self, screen):
        font = pygame.font.Font(None, 24)
        speed_text = f"Speed: {self.animation_speed:.1f}x"
        text = font.render(speed_text, True, WHITE)
        text_rect = text.get_rect()
        text_rect.bottomright = (WIDTH - 10, HEIGHT - 10)
        screen.blit(text, text_rect)

def save_drawing(screen):
    if not os.path.exists('drawings'):
        os.makedirs('drawings')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"drawings/fourier_drawing_{timestamp}.png"
    pygame.image.save(screen, filename)
    return filename

def main():
    drawing = FourierDrawing()
    running = True
    drawing_active = False
    
    while running:
        screen.fill(BLACK)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_h:
                    drawing.show_help = not drawing.show_help
                elif event.key == pygame.K_g:
                    drawing.show_original = not drawing.show_original
                elif event.key == pygame.K_RETURN:
                    save_drawing(screen)
                elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    drawing.paths = []
                    drawing.current_path = None
                    drawing.animating_all = False
                    drawing.completed_paths = []
                elif event.key == pygame.K_SPACE:
                    if drawing.paths:
                        original_paths = drawing.paths.copy()
                        drawing.paths = [original_paths[0]]
                        drawing.paths[0].time = 0
                        drawing.paths[0].animation_points = []
                        drawing.paths[0].state = "animating"
                        drawing.completed_paths = []
                        drawing.animating_all = True
                        drawing.current_animation_index = 0
                        drawing.remaining_paths = original_paths[1:]
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if drawing.show_help:
                    if drawing.help_rect and drawing.help_rect.collidepoint(event.pos):
                        drawing.show_help = False
                else:
                    if event.button == 1:  # Left click - clear and draw new
                        drawing_active = True
                        drawing.start_new_path(clear_existing=True)
                    elif event.button == 3:  # Right click - add new path or complete animation
                        if drawing.animating_all or any(p.state == "animating" for p in drawing.paths):
                            drawing.complete_all_animations()
                        else:
                            drawing_active = True
                            drawing.start_new_path(clear_existing=False)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 3):
                    drawing_active = False
                    drawing.finish_current_path()
            elif event.type == pygame.MOUSEWHEEL:
                drawing.animation_speed = min(1.0, max(0.1, drawing.animation_speed + event.y * SPEED_INCREMENT))
                        
        if drawing_active and drawing.current_path:
            pos = pygame.mouse.get_pos()
            drawing.current_path.add_point(pos)
            
            points = [p.pos for p in drawing.current_path.raw_points]
            if len(points) > 1:
                pygame.draw.lines(screen, WHITE, False, points, 1)

        # Draw original paths if enabled
        if drawing.show_original:
            for path in drawing.paths:
                path.draw_original(screen)
            for path in drawing.completed_paths:
                path.draw_original(screen)
        
        # Draw completed paths
        for path in drawing.completed_paths:
            path.draw_complete(screen)
        
        # Draw current paths
        for path in drawing.paths:
            if path.state == "animating":
                path.animate(screen, drawing.animation_speed)
            elif path.state == "complete":
                path.draw_complete(screen)

        # Handle sequential animation
        if drawing.animating_all and drawing.paths:
            current_path = drawing.paths[0]
            if current_path.state == "complete":
                drawing.completed_paths.append(current_path)
                
                if drawing.remaining_paths:
                    next_path = drawing.remaining_paths.pop(0)
                    next_path.time = 0
                    next_path.animation_points = []
                    next_path.state = "animating"
                    drawing.paths = [next_path]
                else:
                    drawing.animating_all = False
                    drawing.paths = drawing.completed_paths
                    drawing.completed_paths = []
            
        drawing.draw_help(screen)
        drawing.draw_speed_indicator(screen)
            
        pygame.display.flip()
        clock.tick(FPS)
        
    pygame.quit()

if __name__ == "__main__":
    main()
