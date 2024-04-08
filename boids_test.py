import tkinter as tk
import numpy as np
import random

# Parameters
num_boids = 30
boid_perception = 30
max_force = 0.30
max_speed = 2
obstacle_radius = 10
critical_distance = 20
boid_radius = 8  # This represents half the "diameter" of a boid.
min_separation = boid_radius * 2  # Minimum distance between boid centers to avoid overlap.

class Boid:
    def __init__(self, canvas, x, y):
        self.canvas = canvas
        self.position = np.array([x, y], dtype='float64')
        self.velocity = np.random.rand(2) * 2 - 1
        self.velocity = self.velocity / np.linalg.norm(self.velocity) * max_speed
        self.acceleration = np.zeros(2)
        self.momentum = np.zeros(2)
        self.goal_state = False
        
    def update(self):
        self.update_momentum()  # Update momentum based on current acceleration
        # Blend momentum with velocity to determine the new velocity
        blend_factor = 0.1  # Determines how much momentum influences movement
        self.velocity = (1 - blend_factor) * self.velocity + blend_factor * self.momentum
        # Ensure the new velocity does not exceed max_speed
        if np.linalg.norm(self.velocity) > max_speed:
            self.velocity = self.velocity / np.linalg.norm(self.velocity) * max_speed
        self.position += self.velocity
        self.acceleration *= 0
        
    def display(self):
        x, y = self.position
        self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="white", outline="#D3D3D3", width=2)

    def apply_behaviours(self, boids, obstacles, goals, active_boids_count):
        alignment = self.align(boids)
        cohesion = self.cohere(boids)  # Increase the influence of cohesion
        separation = self.separate(boids)
        obstacle_force = self.avoid_obstacles(obstacles)
        
        self.acceleration += alignment
        self.acceleration += cohesion
        self.acceleration += separation
        self.acceleration += obstacle_force

        goal_force = self.attract_to_goal(goals, active_boids_count)
        self.acceleration += alignment + cohesion + separation + obstacle_force + goal_force

    def align(self, boids):
        # Alignment rule implementation
        steering = np.zeros(2)
        total = 0
        for boid in boids:
            if np.linalg.norm(boid.position - self.position) < boid_perception:
                steering += boid.velocity # Accumulate the velocity of nearby boids
                total += 1 
        if total > 0:
            steering /= total
            steering = steering / np.linalg.norm(steering) * max_speed - self.velocity
            if np.linalg.norm(steering) > max_force:
                steering = steering / np.linalg.norm(steering) * max_force * 2
        return steering
    
    def cohere(self, boids):
        steering = np.zeros(2)
        total = 0
        for boid in boids:
            distance = np.linalg.norm(boid.position - self.position)
            if 0 < distance < boid_perception:
                steering += boid.position
                total += 1
        if total > 0:
            steering /= total
            steering -= self.position
            # Apply scaling based on distance, penalize for being too far
            distance_penalty = np.linalg.norm(steering) - (boid_radius * 30)
            if distance_penalty > 0:
                steering *= (1 + distance_penalty / boid_perception)
            if np.linalg.norm(steering) > max_force:
                steering = steering / np.linalg.norm(steering) * max_force
        return steering
        
    def separate(self, boids):
        steering = np.zeros(2)
        total = 0
        for boid in boids:
            distance = np.linalg.norm(boid.position - self.position)
            if 0 < distance < min_separation:
                diff = self.position - boid.position
                diff /= distance  # Normalize the vector
                steering += diff * (min_separation / distance - 1) * 10  # Increased force
                total += 1
        
        if total > 0:
            steering /= total
            if np.linalg.norm(steering) > max_force:
                steering = steering / np.linalg.norm(steering) * max_force * 1.2
        return steering

    def update_momentum(self):
        # Apply current acceleration to update momentum
        self.momentum += self.acceleration
        # Normalize and scale to max_speed to maintain consistent speed
        self.momentum = self.momentum / np.linalg.norm(self.momentum) * max_speed
        # Apply a damping factor to gradually reduce the influence of old momentum
        damping_factor = 1.1
        self.momentum *= damping_factor

    def avoid_obstacles(self, obstacles):
        steer = np.zeros(2)
        closest_distance = float('inf')  # Initialize with a large number
        most_urgent_avoidance = np.zeros(2)

        for obstacle_pos in obstacles:
            obstacle_vector = obstacle_pos - self.position
            distance_to_obstacle = np.linalg.norm(obstacle_vector)

            if distance_to_obstacle < closest_distance and distance_to_obstacle < boid_perception:
                closest_distance = distance_to_obstacle
                # Normalize vector from boid to obstacle
                direction_to_obstacle = obstacle_vector / distance_to_obstacle

                # Calculate a tangential vector for spiraling motion
                # Using the left perpendicular vector for spiral direction
                tangential_vector = np.array([-direction_to_obstacle[1], direction_to_obstacle[0]])

                # Scale the tangential vector inversely with distance to enhance the spiral effect when close
                spiral_force = tangential_vector * (1 / (distance_to_obstacle + 1))

                # Combine direct avoidance with spiraling motion
                # The avoidance force diminishes with distance, while the spiral force increases
                most_urgent_avoidance = (-direction_to_obstacle + spiral_force) * max_force * 4

        return most_urgent_avoidance

    def perpendicular_vector(self, direction, velocity):
        """Find a vector that is perpendicular to the direction to the obstacle and biased by current velocity."""
        # Determine if left or right perpendicular direction is more aligned with current velocity
        left_perp = np.array([-2*direction[1], direction[0]])
        right_perp = np.array([direction[1], -2*direction[0]])
        if np.dot(left_perp, velocity) > np.dot(right_perp, velocity):
            return left_perp
        else:
            return right_perp

    def rotate_vector(self, vector, angle):
        """Rotate a vector by a given angle in degrees."""
        radians = np.radians(angle)
        cos_angle = np.cos(radians) 
        sin_angle = np.sin(radians) * 2
        return np.array([vector[0] * cos_angle - vector[1] * sin_angle, vector[0] * sin_angle + vector[1] * cos_angle])

    def attract_to_goal(self, goals, active_boids_count):
        if not goals:
            return np.zeros(2)

        closest_goal = min(goals, key=lambda goal: np.linalg.norm(self.position - goal))
        direction_to_goal = closest_goal - self.position
        distance_to_goal = np.linalg.norm(direction_to_goal)

        if distance_to_goal < 10:  # Arbitrary distance to consider the goal reached
            # Ensure the respawn position is specified with float dtype to match self.position
            self.goal_state = True
            self.position = np.array([400.0, 300.0])  # Respawn at the center as floats
            return np.zeros(2)
        
        force_multiplier = 4
        if active_boids_count < 5:
            print("Few boids remaining, increasing force")
            force_multiplier *= 4

        direction_to_goal /= distance_to_goal
        return direction_to_goal * max_force * force_multiplier


class Simulation:
    def __init__(self, master):
        self.master = master
        self.width = 800
        self.height = 600
        self.canvas = tk.Canvas(master, width=self.width, height=self.height, bg='black')
        self.canvas.pack()
        initial_position = np.array([self.width / 2, self.height / 2])
        self.boids = [Boid(self.canvas, initial_position[0] + np.random.rand() * 10 - 5, initial_position[1] + np.random.rand() * 10 - 5) for _ in range(num_boids)]
        # self.boids = [Boid(self.canvas, np.random.rand() * self.width, np.random.rand() * self.height) for _ in range(num_boids)]
        self.obstacles = []
        self.active_boids_count = len(self.boids)  
        self.master.bind('<Button-1>', self.create_obstacle)

        self.goals = []  # Initialize an empty list for goals
        self.master.bind('<Button-2>', self.add_goal)
                         # Bind mouse right-click to add a goal
    
        self.update()

    def create_obstacle(self, event):
        self.obstacles.append(np.array([event.x, event.y]))
    
    def count_active_boids(self):
        # Count boids that have not reached the goal
        self.active_boids_count = sum(not boid.goal_state for boid in self.boids)

    def add_goal(self, event):
        self.goals.append(np.array([event.x, event.y]))  # Add the goal position

    def update(self):
        self.canvas.delete("all")
        for obstacle in self.obstacles:
            self.canvas.create_oval(obstacle[0]-obstacle_radius, obstacle[1]-obstacle_radius,
                                    obstacle[0]+obstacle_radius, obstacle[1]+obstacle_radius,
                                    fill='red')
            
        # Draw goals
        for goal in self.goals:
            self.canvas.create_oval(goal[0]-5, goal[1]-5, goal[0]+5, goal[1]+5, fill='green')

        self.count_active_boids()

        all_boids_reached_goal = all(boid.goal_state for boid in self.boids)
        
        if all_boids_reached_goal:
            self.release_boids()  # Start the incremental release.

        # Update boids with goal attraction
        for boid in self.boids:
            boid.apply_behaviours(self.boids, self.obstacles, self.goals, self.active_boids_count)
            
            boid.update()
            if not boid.goal_state:
                boid.display()
            # boid.display()

        self.master.after(50, self.update)

    def release_boids(self):
        # Check if all boids have reached the goal and are ready to be released
        if all(boid.goal_state for boid in self.boids):
            # Calculate a random delay for each boid's release, up to a maximum of 1000 ms (1 second)
            for boid in self.boids:
                delay = random.randint(50, 1000)  # Random delay between 0 and 1000 milliseconds
                self.master.after(delay, lambda b=boid: self.reset_and_activate_boid(b))

    def reset_and_activate_boid(self, boid):
        # Reset boid position to the center with a random offset
        # random_offset = np.random.rand(2) * 20 - 10
        boid.position = np.array([self.width / 2, self.height / 2]) # + random_offset
        # Reset goal state
        boid.goal_state = False
        # Optionally reset other boid properties (e.g., velocity) as needed
        boid.velocity = np.random.rand(2) * 2 - 1
        boid.velocity = boid.velocity / np.linalg.norm(boid.velocity) * max_speed

root = tk.Tk()
root.title("Boid Simulation with Tkinter")
simulation = Simulation(root)
root.mainloop()
