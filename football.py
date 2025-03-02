import pygame
import random
import math
import time

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Football Match Simulation")

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
LIGHT_GREEN = (144, 238, 144)

# Fonts
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

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
MAX_PLAYER_SPEED = 3
MAX_BALL_SPEED = 8
KICK_POWER = 7

# Game states
PLAYING = 0
OFFSIDE_DETECTED = 1
GOAL_SCORED = 2
current_state = PLAYING

# Scores
score_team_red = 0
score_team_blue = 0

# Tracking for offside
last_kicker = None
pass_moment = None
pass_in_progress = False
receiver = None

# Debug mode
DEBUG = False

# For explaining offside
offside_explanation = [
    "Offside Rule in Football:",
    "1. Player must be in opponent's half",
    "2. Player must be ahead of the ball when passed",
    "3. Player must be ahead of the second-last defender"
]

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
            
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), PLAYER_RADIUS)
        
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

    def move(self):
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

    def draw(self):
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), BALL_RADIUS)

# Function to check offside using Euclidean distance
def check_offside(pass_data, receiving_player):
    if not pass_data:
        return False, None, None
    
    attacking_team = pass_data['kicker'].team
    ball_x, ball_y = pass_data['ball_pos']
    
    # Calculate Euclidean distance between ball and receiving player at time of pass
    # d(P_b, P_r) = sqrt((x_b - x_r)^2 + (y_b - y_r)^2)
    ball_to_receiver_dist = math.sqrt((ball_x - receiving_player.x)**2 + (ball_y - receiving_player.y)**2)
    
    # Get all defenders from the opposing team
    defenders_pos = [(x, y) for x, y, team in pass_data['player_positions'] if team != attacking_team]
    
    # Offside rule does not apply when:
    # 1. Player is in their own half of the pitch
    in_own_half = False
    if (attacking_team == 0 and receiving_player.x <= HALF_WIDTH) or \
       (attacking_team == 1 and receiving_player.x >= HALF_WIDTH):
        in_own_half = True
        return False, None, None
    
    # 2. Player is level with or behind the ball when it's played
    behind_ball = False
    if (attacking_team == 0 and receiving_player.x <= ball_x) or \
       (attacking_team == 1 and receiving_player.x >= ball_x):
        behind_ball = True
        return False, None, None
    
    # Find the second-last defender (including goalkeeper)
    # Sort defenders by their x position based on the attacking direction
    if attacking_team == 0:  # Red attacking left to right
        defenders_pos.sort(key=lambda pos: pos[0])  # Sort by x ascending
    else:  # Blue attacking right to left
        defenders_pos.sort(key=lambda pos: -pos[0])  # Sort by x descending
    
    if len(defenders_pos) < 2:
        return False, None, None  # Not enough defenders
    
    # Get the positions of the last and second-last defenders
    last_defender_pos = defenders_pos[0]
    second_last_defender_pos = defenders_pos[1]
    
    # Calculate Euclidean distance between ball and second-last defender
    # d(P_b, P_d) = sqrt((x_b - x_d)^2 + (y_b - y_d)^2)
    ball_to_defender_dist = math.sqrt((ball_x - second_last_defender_pos[0])**2 + 
                                     (ball_y - second_last_defender_pos[1])**2)
    
    # Calculate Euclidean distance between receiving player and second-last defender
    # d(P_r, P_d) = sqrt((x_r - x_d)^2 + (y_r - y_d)^2)
    receiver_to_defender_dist = math.sqrt((receiving_player.x - second_last_defender_pos[0])**2 + 
                                        (receiving_player.y - second_last_defender_pos[1])**2)
    
    # 3. Player is level with or behind the second-last opponent
    if attacking_team == 0:  # Red attacking left to right
        if receiving_player.x <= second_last_defender_pos[0]:
            return False, None, None
    else:  # Blue attacking right to left
        if receiving_player.x >= second_last_defender_pos[0]:
            return False, None, None
            
    # Find the current second-last defender for visualization
    current_defenders = [p for p in players if p.team != attacking_team]
    if attacking_team == 0:
        current_defenders.sort(key=lambda p: p.x)
    else:
        current_defenders.sort(key=lambda p: -p.x)
    
    second_last_defender = current_defenders[1] if len(current_defenders) >= 2 else None
    
    # Player is in offside position - return distances for visualization
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

# Initialize the game
players = create_teams()
ball = Ball(FIELD_WIDTH / 2, FIELD_HEIGHT / 2)

# Main game loop
running = True
clock = pygame.time.Clock()
offside_info = None

# Timer for offside simulation
start_time = time.time()
offside_simulated = False

while running:
    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Simulate offside after 30 seconds
    if not offside_simulated and elapsed_time >= 30:
        # Force an offside scenario
        # Move the ball and a player into an offside position
        ball.x = HALF_WIDTH + 100  # Ball in the opponent's half
        ball.y = HEIGHT // 2

        # Move a red team player into an offside position
        for player in players:
            if player.team == 0 and player.role == "FWD":  # Red team forward
                player.x = HALF_WIDTH + 150  # Ahead of the second-last defender
                player.y = HEIGHT // 2
                break

        # Simulate a pass to the offside player
        last_kicker = next(p for p in players if p.team == 0 and p.role == "MID")  # Red team midfielder
        pass_moment = {
            'kicker': last_kicker,
            'ball_pos': (ball.x, ball.y),
            'player_positions': [(p.x, p.y, p.team) for p in players]
        }
        pass_in_progress = True
        receiver = next(p for p in players if p.team == 0 and p.role == "FWD")  # Red team forward

        # Mark that offside has been simulated
        offside_simulated = True

    # Rest of the game loop remains the same
    screen.fill(GREEN)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # Reset game
                players = create_teams()
                ball.reset()
                score_team_red = 0
                score_team_blue = 0
                current_state = PLAYING
                last_kicker = None
                pass_moment = None
                pass_in_progress = False
                receiver = None
                start_time = time.time()  # Reset the timer
                offside_simulated = False
            elif event.key == pygame.K_d:  # Toggle debug mode
                DEBUG = not DEBUG

    # Draw field
    draw_field()

    if current_state == PLAYING:
        # Check for offside
        offside_detected = False
        offside_info = None

        # Move players
        for player in players:
            result = player.move(ball, players)
            if result[0]:  # Offside detected
                offside_detected = True
                offside_info = result
                break

        if not offside_detected:
            # Move the ball
            goal_scored = ball.move()

            # Check for goals
            if goal_scored:
                if ball.x <= 0:
                    score_team_blue += 1  # Blue team scores (right to left)
                    current_state = GOAL_SCORED
                    scorer = "Blue team"
                elif ball.x >= FIELD_WIDTH:
                    score_team_red += 1  # Red team scores (left to right)
                    current_state = GOAL_SCORED
                    scorer = "Red team"

                # Reset for kickoff
                ball.reset()
                last_kicker = None
                pass_in_progress = False
                receiver = None
        else:
            current_state = OFFSIDE_DETECTED

    elif current_state == OFFSIDE_DETECTED:
        # Visualize offside line and player
        if offside_info and offside_info[1] and offside_info[2]:
            second_last_defender, offside_player = offside_info[1], offside_info[2]

            # Draw offside line
            pygame.draw.line(screen, YELLOW, (second_last_defender.x, 0),
                           (second_last_defender.x, FIELD_HEIGHT), 2)

            # Highlight offside player
            pygame.draw.circle(screen, YELLOW, (int(offside_player.x), int(offside_player.y)),
                             PLAYER_RADIUS + 5, 3)

            # Show offside message
            screen.blit(font.render("OFFSIDE!", True, YELLOW), (WIDTH // 2 - 50, 50))

            # Show explanation
            for i, line in enumerate(offside_explanation):
                screen.blit(small_font.render(line, True, WHITE), (WIDTH // 2 - 150, 100 + i * 25))

        # Game continues after a short delay
        pygame.time.delay(2000)

        # Reset for free kick
        ball.reset()
        last_kicker = None
        pass_moment = None
        pass_in_progress = False
        receiver = None

        # Return to playing state
        current_state = PLAYING

    elif current_state == GOAL_SCORED:
        # Show goal message
        goal_text = font.render(f"GOAL! {scorer} scores!", True, YELLOW)
        screen.blit(goal_text, (WIDTH // 2 - 100, HEIGHT // 2 - 50))

        # Update score display
        score_text = font.render(f"Red {score_team_red} - {score_team_blue} Blue", True, WHITE)
        screen.blit(score_text, (WIDTH // 2 - 80, 20))

        # Game continues after a short delay
        pygame.time.delay(2000)
        current_state = PLAYING

        # Reset player positions
        for player in players:
            player.x = player.home_x
            player.y = player.home_y
            player.vx = 0
            player.vy = 0
            player.has_ball = False

    # Draw all game objects
    for player in players:
        player.draw()

    ball.draw()

    # Display score and game info
    score_text = font.render(f"Red {score_team_red} - {score_team_blue} Blue", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - 80, 20))

    # Display controls
    controls_text = small_font.render("Press R to reset game | Press D to toggle debug mode", True, WHITE)
    screen.blit(controls_text, (WIDTH // 2 - 180, HEIGHT - 30))

    # Update display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

# Clean up
pygame.quit()