
import pygame
import random
import math

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Football Match Simulation - Offside Learning Tool")

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
LIGHT_GREEN = (144, 238, 144)
ORANGE = (255, 165, 0)

# Fonts
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)
tiny_font = pygame.font.Font(None, 18)

# Player and Ball settings
PLAYER_RADIUS = 10
BALL_RADIUS = 5
PLAYERS_PER_TEAM = 11

# Field dimensions
FIELD_WIDTH = WIDTH
FIELD_HEIGHT = HEIGHT
HALF_WIDTH = FIELD_WIDTH // 2

# Goal dimensions
GOAL_WIDTH = 10
GOAL_HEIGHT = 100
GOAL_TOP = HEIGHT // 2 - GOAL_HEIGHT // 2
GOAL_BOTTOM = HEIGHT // 2 + GOAL_HEIGHT // 2

# Physics constants
FRICTION = 0.97
MAX_PLAYER_SPEED = 1.5  # Reduced player speed for easier visualization
MAX_BALL_SPEED = 5      # Reduced ball speed
KICK_POWER = 4          # Reduced kick power

# Game states
PLAYING = 0
OFFSIDE_DETECTED = 1
GOAL_SCORED = 2
PAUSED = 3
current_state = PLAYING

# Scores
score_team_red = 0
score_team_blue = 0

# Tracking for offside
last_kicker = None
pass_moment = None
pass_in_progress = False
receiver = None
offside_line_x = None  # Initialize offside line variable
second_last_defender = None
offside_player = None

# Debug mode
DEBUG = False

# For explaining offside
offside_explanation = [
    "Offside Rule in Football:",
    "1. Player must be in opponent's half",
    "2. Player must be ahead of the ball when passed",
    "3. Player must be ahead of the second-last defender"
]

# Button class for UI elements
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.is_hovered = False
        
    def draw(self):
        # Draw button with hover effect
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)  # Border
        
        # Draw text
        text_surf = small_font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.action:
                return self.action()
        return False

# Player class with realistic positioning
class Player:
    def __init__(self, x, y, team, role, position_id):
        self.x = x
        self.y = y
        self.team = team  # 0 = red (left to right), 1 = blue (right to left)
        self.role = role  # "GK", "DEF", "MID", or "FWD"
        self.position_id = position_id  # Unique ID for positioning
        self.home_x = x  # Default position to return to
        self.home_y = y
        self.vx = 0
        self.vy = 0
        self.has_ball = False
        self.position_at_pass = None
        self.target_x = x
        self.target_y = y
        self.attacking = False
        self.speed = MAX_PLAYER_SPEED * random.uniform(0.8, 1.1)  # Vary player speed
        self.highlighted = False  # For offside visualization

    def euclidean_distance(self, other_x, other_y):
        """Calculate Euclidean distance to another point"""
        return math.sqrt((self.x - other_x)**2 + (self.y - other_y)**2)
        
    def move(self, ball, players):
        global last_kicker, pass_moment, pass_in_progress, receiver
        
        # Calculate distances
        dist_to_ball = self.euclidean_distance(ball.x, ball.y)
        teammates = [p for p in players if p.team == self.team and p != self]
        opponents = [p for p in players if p.team != self.team]
        
        # Get team with possession
        ball_possessor = next((p for p in players if p.has_ball), None)
        team_in_possession = ball_possessor.team if ball_possessor else None
        
        # Determine if we're attacking or defending
        self.attacking = (team_in_possession == self.team) or (team_in_possession is None and ball.x > HALF_WIDTH and self.team == 0) or (team_in_possession is None and ball.x < HALF_WIDTH and self.team == 1)
        
        # Reset target to home position by default
        self.target_x = self.home_x
        self.target_y = self.home_y
        
        # Goalkeepers stay near goal
        if self.role == "GK":
            goal_x = 30 if self.team == 0 else WIDTH - 30
            goal_y = HEIGHT / 2
            
            # Only come out for the ball if it's close to goal
            if self.team == 0 and ball.x < 120 and 150 < ball.y < HEIGHT - 150:
                self.target_x = min(120, ball.x)
                self.target_y = ball.y
            elif self.team == 1 and ball.x > WIDTH - 120 and 150 < ball.y < HEIGHT - 150:
                self.target_x = max(WIDTH - 120, ball.x)
                self.target_y = ball.y
            else:
                self.target_x = goal_x
                self.target_y = goal_y
                
        # Field players behavior
        else:
            # Player is closest to ball on their team - chase the ball
            teammates_dist_to_ball = [(p, p.euclidean_distance(ball.x, ball.y)) for p in teammates]
            teammates_dist_to_ball.append((self, dist_to_ball))
            teammates_dist_to_ball.sort(key=lambda x: x[1])
            
            # The closest 2 players from each team will chase the ball
            if self == teammates_dist_to_ball[0][0] or self == teammates_dist_to_ball[1][0]:
                self.target_x = ball.x
                self.target_y = ball.y
            
            # Other players maintain formation with strategic positioning
            else:
                # Attacking team moves forward
                if self.attacking:
                    # Defenders stay back but move up a bit
                    if self.role == "DEF":
                        forward_position = 0.3 if self.team == 0 else 0.7
                        self.target_x = FIELD_WIDTH * forward_position
                        # Spread out horizontally
                        spread = (self.position_id - 2) * 100
                        self.target_y = HEIGHT/2 + spread
                    
                    # Midfielders move up to support attack
                    elif self.role == "MID":
                        forward_position = 0.6 if self.team == 0 else 0.4
                        self.target_x = FIELD_WIDTH * forward_position
                        # Spread out
                        spread = (self.position_id - 6) * 80
                        self.target_y = HEIGHT/2 + spread
                    
                    # Forwards move to attacking positions
                    elif self.role == "FWD":
                        forward_position = 0.8 if self.team == 0 else 0.2
                        self.target_x = FIELD_WIDTH * forward_position
                        # Spread out
                        spread = (self.position_id - 9) * 120
                        self.target_y = HEIGHT/2 + spread
                
                # Defending team gets into defensive shape
                else:
                    # Figure out where the ball is relative to our goal
                    ball_side = ball.y < HEIGHT/2
                    
                    # Defenders form a line in front of goal
                    if self.role == "DEF":
                        back_position = 0.15 if self.team == 0 else 0.85
                        self.target_x = FIELD_WIDTH * back_position
                        # Spread defenders to cover width
                        spread = (self.position_id - 2) * 100
                        self.target_y = min(max(100, HEIGHT/2 + spread), HEIGHT - 100)
                        
                        # Adjust based on ball position
                        if ball.y < self.target_y - 50:
                            self.target_y -= 50
                        elif ball.y > self.target_y + 50:
                            self.target_y += 50
                    
                    # Midfielders provide defensive cover
                    elif self.role == "MID":
                        mid_position = 0.35 if self.team == 0 else 0.65
                        self.target_x = FIELD_WIDTH * mid_position
                        # Position midfielders between ball and goal
                        self.target_y = ball.y + (HEIGHT/2 - ball.y) * 0.5
                        # Add some spread
                        spread = (self.position_id - 6) * 60
                        self.target_y += spread
                        
                    # One forward stays up, others come back
                    elif self.role == "FWD":
                        if self.position_id == 9:  # Striker stays forward
                            forward_position = 0.6 if self.team == 0 else 0.4
                            self.target_x = FIELD_WIDTH * forward_position
                            self.target_y = HEIGHT/2
                        else:  # Other forwards help midfield
                            mid_position = 0.4 if self.team == 0 else 0.6
                            self.target_x = FIELD_WIDTH * mid_position
                            spread = (self.position_id - 9) * 100
                            self.target_y = HEIGHT/2 + spread
        
        # Move toward target position
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist_to_target = max(0.1, math.sqrt(dx**2 + dy**2))
        
        # Only move if we're not at the target
        if dist_to_target > 5:
            normalized_dx = dx / dist_to_target
            normalized_dy = dy / dist_to_target
            
            # Scale by player's speed attribute
            self.vx = normalized_dx * self.speed
            self.vy = normalized_dy * self.speed
        else:
            # At target, slow down
            self.vx *= 0.8
            self.vy *= 0.8
            
        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        
        # Keep players within bounds
        self.x = max(10, min(self.x, FIELD_WIDTH - 10))
        self.y = max(10, min(self.y, FIELD_HEIGHT - 10))
        
        # Handle ball interaction
        if dist_to_ball < PLAYER_RADIUS + BALL_RADIUS:
            # New player touches the ball
            if not self.has_ball:
                # Check if this is receiving a pass
                if pass_in_progress and self.team == last_kicker.team and self != last_kicker:
                    receiver = self
                    # Check offside only when a player receives a pass from teammate
                    offside_result = check_offside(pass_moment, self)
                    if offside_result[0]:
                        return offside_result
                    
                # Not offside or not a pass reception
                self.has_ball = True
                if last_kicker and last_kicker != self:
                    last_kicker.has_ball = False
                
                # If this player is from a different team than last kicker, it's not a pass reception
                if last_kicker and last_kicker.team != self.team:
                    pass_in_progress = False
                
                # New pass begins
                if last_kicker != self:
                    last_kicker = self
                    
                    # Decide direction to kick
                    # Find teammates in advantageous positions
                    available_teammates = [p for p in teammates if p.role in ["MID", "FWD"]]
                    
                    if available_teammates and random.random() < 0.7:  # 70% chance to pass to teammate
                        # Pick a good teammate to pass to
                        pass_target = random.choice(available_teammates)
                        
                        # Calculate kick direction
                        kick_dx = pass_target.x - self.x
                        kick_dy = pass_target.y - self.y
                        kick_dist = max(0.1, math.sqrt(kick_dx**2 + kick_dy**2))
                        kick_dx /= kick_dist
                        kick_dy /= kick_dist
                        
                        # Add some randomness to the pass
                        kick_dx += random.uniform(-0.1, 0.1)
                        kick_dy += random.uniform(-0.1, 0.1)
                        
                        # Apply the kick
                        ball.vx = kick_dx * KICK_POWER * random.uniform(0.9, 1.1)
                        ball.vy = kick_dy * KICK_POWER * random.uniform(0.9, 1.1)
                    else:
                        # Kick in attacking direction
                        attack_dir = 1 if self.team == 0 else -1
                        ball.vx = attack_dir * KICK_POWER * random.uniform(0.8, 1.2)
                        ball.vy = random.uniform(-0.5, 0.5) * KICK_POWER * 0.5
                    
                    # Record the state at the moment of the pass
                    pass_moment = {
                        'kicker': self,
                        'ball_pos': (ball.x, ball.y),
                        'player_positions': [(p.x, p.y, p.team) for p in players]
                    }
                    pass_in_progress = True
                    return False, None, None
            
            # Player already has the ball (dribbling)
            else:
                # Occasionally kick the ball ahead while dribbling
                if random.random() < 0.05:  # 5% chance to kick per frame
                    # Kick in general direction of movement
                    attack_dir = 1 if self.team == 0 else -1
                    ball.vx = attack_dir * KICK_POWER * 0.7 + self.vx * 1.5
                    ball.vy = self.vy * 1.5
                    self.has_ball = False
                else:
                    # Just dribble
                    ball.vx = self.vx * 1.1
                    ball.vy = self.vy * 1.1
        else:
            # Player loses the ball
            if self.has_ball:
                self.has_ball = False
                
        return False, None, None

    def draw(self):
        color = RED if self.team == 0 else BLUE
        # Make goalkeeper a different shade
        if self.role == "GK":
            color = (200, 50, 50) if self.team == 0 else (50, 50, 200)
        
        # Draw player circle
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), PLAYER_RADIUS)
        
        # Add highlight if this player is involved in offside
        if self.highlighted:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), PLAYER_RADIUS + 5, 2)
            
            # Add label above player
            if self.team == receiver.team:
                label = "OFFSIDE"
            else:
                label = "2nd LAST DEF"
                
            label_text = tiny_font.render(label, True, YELLOW)
            screen.blit(label_text, (self.x - label_text.get_width()//2, self.y - PLAYER_RADIUS - 15))
        
        # Show team number
        number_text = small_font.render(str(self.position_id), True, WHITE)
        screen.blit(number_text, (self.x - number_text.get_width()//2, self.y - number_text.get_height()//2))
        
        # Show indicator if this player has the ball
        if self.has_ball:
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), PLAYER_RADIUS + 5, 2)
            
        # Debug: Show target position
        if DEBUG:
            pygame.draw.line(screen, YELLOW, (self.x, self.y), (self.target_x, self.target_y), 1)
            pygame.draw.circle(screen, YELLOW, (int(self.target_x), int(self.target_y)), 3)

# Ball class
class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.path = []  # Store positions for visualization
        self.max_path_length = 50

    def move(self):
        # Save current position for path visualization
        self.path.append((self.x, self.y))
        if len(self.path) > self.max_path_length:
            self.path.pop(0)
            
        self.x += self.vx
        self.y += self.vy
        self.vx *= FRICTION
        self.vy *= FRICTION
        
        # Cap ball speed
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > MAX_BALL_SPEED:
            self.vx = (self.vx / speed) * MAX_BALL_SPEED
            self.vy = (self.vy / speed) * MAX_BALL_SPEED
        
        # Keep ball within bounds
        if self.x < 0 or self.x > FIELD_WIDTH:
            # Check if it's a goal
            if GOAL_TOP < self.y < GOAL_BOTTOM:
                return True  # Goal scored
            else:
                # Out of bounds
                self.vx = -self.vx * 0.5
                self.x = max(5, min(self.x, FIELD_WIDTH - 5))
        
        if self.y < 0 or self.y > FIELD_HEIGHT:
            self.vy = -self.vy * 0.5
            self.y = max(5, min(self.y, FIELD_HEIGHT - 5))
            
        return False  # No goal

    def reset(self):
        self.x = FIELD_WIDTH / 2
        self.y = FIELD_HEIGHT / 2
        self.vx = 0
        self.vy = 0
        self.path = []

    def draw(self):
        # Draw ball path
        for i in range(1, len(self.path)):
            # Fade the path from white to transparent
            alpha = int(255 * (i / len(self.path)))
            color = (255, 255, 255, alpha)
            pygame.draw.line(screen, color, self.path[i-1], self.path[i], 1)
        
        # Draw the ball
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), BALL_RADIUS)

# Function to check offside using Euclidean distance
def check_offside(pass_data, receiving_player):
    """
    Check if the receiving player is in an offside position at the moment the ball is played.
    """
    if not pass_data:
        return False, None, None
    
    attacking_team = pass_data['kicker'].team
    ball_x, ball_y = pass_data['ball_pos']
    
    # Get all defenders from the opposing team (including the goalkeeper)
    defenders = [p for p in players if p.team != attacking_team]
    
    # Sort defenders by their x-coordinate (closest to the goal)
    if attacking_team == 0:  # Red team attacking left to right
        defenders.sort(key=lambda p: p.x)  # Sort by x ascending
    else:  # Blue team attacking right to left
        defenders.sort(key=lambda p: -p.x)  # Sort by x descending
    
    # The second-last defender is the offside line (last defender is usually the goalkeeper)
    if len(defenders) < 2:
        return False, None, None  # Not enough defenders
    
    second_last_defender = defenders[1]
    
    # Offside conditions:
    # 1. Player is in the opponent's half
    in_opponent_half = (attacking_team == 0 and receiving_player.x > HALF_WIDTH) or \
                       (attacking_team == 1 and receiving_player.x < HALF_WIDTH)
    
    if not in_opponent_half:
        return False, None, None  # Player is in their own half, cannot be offside
    
    # 2. Player is closer to the opponent's goal line than the second-last defender
    ahead_of_defender = (attacking_team == 0 and receiving_player.x > second_last_defender.x) or \
                        (attacking_team == 1 and receiving_player.x < second_last_defender.x)
    
    if not ahead_of_defender:
        return False, None, None  # Player is not ahead of the second-last defender
    
    # 3. Player is closer to the opponent's goal line than the ball at the moment of the pass
    ahead_of_ball = (attacking_team == 0 and receiving_player.x > ball_x) or \
                    (attacking_team == 1 and receiving_player.x < ball_x)
    
    if not ahead_of_ball:
        return False, None, None  # Player is not ahead of the ball
    
    # Player is offside if all conditions are met
    return True, second_last_defender, receiving_player

# Create teams with specific formations
def create_teams():
    players = []
    
    # Team 0 (Red) - attacking left to right
    # Goalkeeper (position 1)
    players.append(Player(50, HEIGHT//2, 0, "GK", 1))
    
    # Defenders (positions 2-5)
    positions = [
        (150, 150),  # Left back
        (150, HEIGHT//2 - 75),  # Center back 1
        (150, HEIGHT//2 + 75),  # Center back 2
        (150, HEIGHT - 150)   # Right back
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 0, "DEF", i+2))
    
    # Midfielders (positions 6-8)
    positions = [
        (300, 150),  # Left mid
        (300, HEIGHT//2),  # Center mid
        (300, HEIGHT - 150)  # Right mid
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 0, "MID", i+6))
    
    # Forwards (positions 9-11)
    positions = [
        (450, 150),  # Left forward
        (450, HEIGHT//2),  # Center forward
        (450, HEIGHT - 150)  # Right forward
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 0, "FWD", i+9))
    
    # Team 1 (Blue) - attacking right to left
    # Goalkeeper (position 1)
    players.append(Player(WIDTH-50, HEIGHT//2, 1, "GK", 1))
    
    # Defenders (positions 2-5)
    positions = [
        (WIDTH - 150, 150),  # Left back
        (WIDTH - 150, HEIGHT//2 - 75),  # Center back 1
        (WIDTH - 150, HEIGHT//2 + 75),  # Center back 2
        (WIDTH - 150, HEIGHT - 150)   # Right back
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 1, "DEF", i+2))
    
    # Midfielders (positions 6-8)
    positions = [
        (WIDTH - 300, 150),  # Left mid
        (WIDTH - 300, HEIGHT//2),  # Center mid
        (WIDTH - 300, HEIGHT - 150)  # Right mid
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 1, "MID", i+6))
    
    # Forwards (positions 9-11)
    positions = [
        (WIDTH - 450, 150),  # Left forward
        (WIDTH - 450, HEIGHT//2),  # Center forward
        (WIDTH - 450, HEIGHT - 150)  # Right forward
    ]
    for i, (x, y) in enumerate(positions):
        players.append(Player(x, y, 1, "FWD", i+9))
    
    return players

# Draw field markings
def draw_field():
    # Field background
    pygame.draw.rect(screen, LIGHT_GREEN, (0, 0, WIDTH, HEIGHT))
    
    # Center line
    pygame.draw.line(screen, WHITE, (HALF_WIDTH, 0), (HALF_WIDTH, HEIGHT), 2)
    
    # Center circle
    pygame.draw.circle(screen, WHITE, (HALF_WIDTH, HEIGHT // 2), 70, 2)
    pygame.draw.circle(screen, WHITE, (HALF_WIDTH, HEIGHT // 2), 5, 0)
    
    # Penalty areas
    pygame.draw.rect(screen, WHITE, (0, HEIGHT//2 - 150, 100, 300), 2)  # Left penalty area
    pygame.draw.rect(screen, WHITE, (WIDTH-100, HEIGHT//2 - 150, 100, 300), 2)  # Right penalty area
    
    # Goal areas
    pygame.draw.rect(screen, WHITE, (0, HEIGHT//2 - 50, 50, 100), 2)  # Left goal area
    pygame.draw.rect(screen, WHITE, (WIDTH-50, HEIGHT//2 - 50, 50, 100), 2)  # Right goal area
    
    # Penalty spots
    pygame.draw.circle(screen, WHITE, (80, HEIGHT//2), 3, 0)  # Left penalty spot
    pygame.draw.circle(screen, WHITE, (WIDTH-80, HEIGHT//2), 3, 0)  # Right penalty spot
    
    # Corner arcs
    pygame.draw.arc(screen, WHITE, (-10, -10, 20, 20), 0, math.pi/2, 2)  # Top-left
    pygame.draw.arc(screen, WHITE, (WIDTH-10, -10, 20, 20), math.pi/2, math.pi, 2)  # Top-right
    pygame.draw.arc(screen, WHITE, (-10, HEIGHT-10, 20, 20), 3*math.pi/2, 2*math.pi, 2)  # Bottom-left
    pygame.draw.arc(screen, WHITE, (WIDTH-10, HEIGHT-10, 20, 20), math.pi, 3*math.pi/2, 2)  # Bottom-right
    
    # Goals
    pygame.draw.rect(screen, WHITE, (0, GOAL_TOP, GOAL_WIDTH, GOAL_HEIGHT), 2)  # Left goal
    pygame.draw.rect(screen, WHITE, (FIELD_WIDTH - GOAL_WIDTH, GOAL_TOP, GOAL_WIDTH, GOAL_HEIGHT), 2)  # Right goal

# Function to manually create offside scenario
def setup_offside_scenario(players, ball):
    # Place the ball in the attacking half for the red team
    ball.x = HALF_WIDTH + 50
    ball.y = HEIGHT // 2
    ball.vx = 0
    ball.vy = 0
    
    # Reset all players to base attributes
    for player in players:
        player.has_ball = False
        player.highlighted = False
    
    # Get a red midfielder to be the passer
    red_mid = next(p for p in players if p.team == 0 and p.role == "MID")
    red_mid.x = HALF_WIDTH + 50
    red_mid.y = HEIGHT // 2 + 50
    red_mid.has_ball = True
    
    # Get a red forward to be in offside position
    red_forward = next(p for p in players if p.team == 0 and p.role == "FWD")
    red_forward.x = FIELD_WIDTH - 150  # Very advanced position
    red_forward.y = HEIGHT // 2
    
    # Position the blue defenders to create offside trap
    blue_defenders = [p for p in players if p.team == 1 and p.role == "DEF"]
    for i, defender in enumerate(blue_defenders):
        # Line up the defenders to create an offside trap
        defender.x = FIELD_WIDTH - 250  # Create a defensive line
        defender.y = HEIGHT//2 - 120 + 80 * i  # Spread them out

    # Position blue goalkeeper behind defenders
    blue_gk = next(p for p in players if p.team == 1 and p.role == "GK")
    blue_gk.x = FIELD_WIDTH - 50
    blue_gk.y = HEIGHT // 2

# Function to restart the entire game
def restart_game():
    global current_state, score_team_red, score_team_blue, pass_in_progress
    global last_kicker, pass_moment, receiver, offside_line_x, second_last_defender, offside_player
    
    # Reset game state
    current_state = PLAYING
    pass_in_progress = False
    last_kicker = None
    pass_moment = None
    receiver = None
    offside_line_x = None  # Reset offside line variable
    second_last_defender = None
    offside_player = None
    
    # Reset ball
    ball.reset()
    
    # Reset players to their home positions
    for player in players:
        player.x = player.home_x
        player.y = player.home_y
        player.vx = 0
        player.vy = 0
        player.has_ball = False
        player.highlighted = False
    
    return True

# Function to reset after offside call
def reset_after_offside():
    global current_state, pass_in_progress, offside_line_x, second_last_defender, offside_player
    
    # Reset game state but keep score
    current_state = PLAYING
    pass_in_progress = False
    offside_line_x = None
    
    # Reset player highlights
    if second_last_defender:
        second_last_defender.highlighted = False
    if offside_player:
        offside_player.highlighted = False
    
    second_last_defender = None
    offside_player = None
    
    # Place ball for indirect free kick
    if receiver:
        ball.x = receiver.x
        ball.y = receiver.y
    
    ball.vx = 0
    ball.vy = 0
    
    return True

# Function to toggle debug mode
def toggle_debug():
    global DEBUG
    DEBUG = not DEBUG
    return True

# Draw offside visualization
def draw_offside_visualization():
    if offside_line_x is not None and second_last_defender and offside_player:
        # Draw offside line at the ball's position when the pass was made
        pygame.draw.line(screen, YELLOW, (offside_line_x, 0), (offside_line_x, HEIGHT), 2)
        
        # Add text explanation
        offside_text = font.render("OFFSIDE!", True, YELLOW)
        screen.blit(offside_text, (WIDTH//2 - offside_text.get_width()//2, 20))
        
        # Draw lines connecting the relevant players
        pygame.draw.line(screen, YELLOW, (offside_player.x, offside_player.y), 
                        (offside_player.x, HEIGHT//2), 2)
        pygame.draw.line(screen, YELLOW, (second_last_defender.x, second_last_defender.y), 
                        (second_last_defender.x, HEIGHT//2), 2)
        
        # Add explanation
        instruction_text = small_font.render("Click 'Reset Play' to continue", True, WHITE)
        screen.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, 60))

# Initialize the game
ball = Ball(WIDTH/2, HEIGHT/2)
players = create_teams()

# UI Buttons for interactive controls
restart_button = Button(WIDTH - 150, 20, 120, 30, "Restart Game", ORANGE , (255, 200, 0), 
                        lambda: restart_game())
reset_button = Button(WIDTH - 150, 60, 120, 30, "Reset Play", ORANGE, (255, 200, 0), 
                    lambda: reset_after_offside())
debug_button = Button(WIDTH - 150, 100, 120, 30, "Debug Mode", ORANGE, (255, 200, 0), 
                    lambda: toggle_debug())

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        # Check button events
        restart_button.handle_event(event)
        reset_button.handle_event(event)
        debug_button.handle_event(event)

    # Game logic
    if current_state == PLAYING:
        ball_moved = ball.move()
        for player in players:
            player.move(ball, players)
            if ball_moved:
                if ball_moved:  # Check if a goal was scored
                    if ball.x < GOAL_WIDTH:  # Red team goal
                        score_team_blue += 1
                        current_state = GOAL_SCORED
                    elif ball.x > FIELD_WIDTH - GOAL_WIDTH:  # Blue team goal
                        score_team_red += 1
                        current_state = GOAL_SCORED

    # Drawing
    draw_field()
    for player in players:
        player.draw()
    ball.draw()
    
    # Draw offside visualization if applicable
    draw_offside_visualization()
    
    # Draw scores
    score_text = font.render(f"Red: {score_team_red} - Blue: {score_team_blue}", True, BLACK)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 10))
    
    # Draw buttons
    restart_button.draw()
    reset_button.draw()
    debug_button.draw()
    
    pygame.display.flip()
    pygame.time.delay(30)

pygame.quit()