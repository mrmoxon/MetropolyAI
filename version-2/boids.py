import tkinter as tk
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageTk  # For converting matplotlib plot to a tkinter compatible format
import random
from shapely.geometry import Polygon, MultiPoint, Point, box
from shapely.ops import unary_union
import time
# from voronoi import mirror_points

class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metropoly")

        # Screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Game window dimensions
        self.game_height = int(self.screen_height * 0.7)
        self.game_width = self.game_height  # To make the window square
        self.root.geometry(f"{int(self.game_width + 50)}x{int(self.game_height + 50)}")

        self.menu_frame = tk.Frame(self.root)
        self.game_frame = None
        self.timer_label = None
        self.start_time = None

        self.canvas = None  # To hold the tkinter canvas for Voronoi diagram
        self.points = None
        self.vor = None
        self.centroids = None

        self.boids = []
        self.boid_speed = 5
        self.perception_radius = 50
        self.max_acceleration = 0.5

        self.regions = 120
        self.cities = 80

        self.setup_menu()

    def setup_menu(self):
        self.menu_frame.pack(fill=tk.BOTH, expand=True)

        play_button = tk.Button(self.menu_frame, text="Play", command=self.start_game)
        play_button.pack(pady=20)

    def start_game(self):
        if self.game_frame:
            self.game_frame.destroy()

        self.menu_frame.pack_forget()
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(fill=tk.BOTH, expand=True)

        # Timer Label - Initialize it here before starting the timer
        self.timer_label = tk.Label(self.game_frame, text="Timer: 0")
        self.timer_label.pack(side=tk.TOP, pady=10)  # Adjust position as needed

        # Restart Button
        restart_button = tk.Button(self.game_frame, text="Restart", command=self.restart_game)
        restart_button.pack(side=tk.BOTTOM, pady=10)

        self.canvas = tk.Canvas(self.game_frame, width=self.game_width, height=self.game_height, bg='white')
        self.canvas.pack()

        self.generate_voronoi()
        # self.build_terrain()
        self.canvas.bind("<Motion>", self.on_mouse_over)
        self.canvas.bind("<Button-1>", self.on_mouse_click)

        # Bind the on_mouse_down function to the ButtonPress event
        # self.canvas.bind("<ButtonPress>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        # Bind the on_mouse_up function to the ButtonRelease event
        self.canvas.bind("<ButtonRelease>", self.on_mouse_up)
        
        self.canvas.bind_all("<MouseWheel>", self.on_vertical_scroll)  # For Windows and MacOS
        self.canvas.bind_all("<Shift-MouseWheel>", self.on_horizontal_scroll)  # A common approach

        self.start_timer()

    def on_vertical_scroll(self, event):
        # Check for platform
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            # For Windows, typical event.delta values are 120 or -120 per scroll step
            scroll_steps = int(-1 * (event.delta / 20))
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11':
            # For Linux, event.num determines the direction
            if event.num == 4:
                scroll_steps = -1  # Scroll up
            else:
                scroll_steps = 1   # Scroll down
        else:
            # For macOS, you might need to directly use event.delta
            scroll_steps = int(-1 * (event.delta))
        
        # Apply the vertical scroll
        self.canvas.yview_scroll(scroll_steps, "units")

    def on_horizontal_scroll(self, event):
        # Check for platform
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            # For Windows, typical event.delta values are 120 or -120 per scroll step
            scroll_steps = int(-1 * (event.delta / 20))
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11':
            # For Linux, event.num determines the direction
            if event.num == 6:  # Adjust based on your specific mouse configuration
                scroll_steps = -1  # Scroll left
            else:
                scroll_steps = 1   # Scroll right
        else:
            # For macOS, you might need to directly use event.delta
            scroll_steps = int(-1 * (event.delta))

        # Apply the horizontal scroll
        self.canvas.xview_scroll(scroll_steps, "units")

    def restart_game(self):
        self.start_game()

    def start_timer(self):
        self.start_time = time.time()
        self.update_timer()

    def update_timer(self):
        if not self.start_time:
            return

        elapsed_time = int(time.time() - self.start_time)
        self.timer_label.config(text=f"Timer: {elapsed_time}")
        self.root.after(1000, self.update_timer)  # Update the timer every 1 second

    def mirror_points(self, points, bounding_box):
        """
        Mirror points at the edges of the bounding box to ensure bounded Voronoi regions.
        """
        points_left = np.copy(points)
        points_left[:, 0] = bounding_box[0] - (points_left[:, 0] - bounding_box[0])

        points_right = np.copy(points)
        points_right[:, 0] = bounding_box[1] + (bounding_box[1] - points_right[:, 0])

        points_down = np.copy(points)
        points_down[:, 1] = bounding_box[2] - (points_down[:, 1] - bounding_box[2])

        points_up = np.copy(points)
        points_up[:, 1] = bounding_box[3] + (bounding_box[3] - points_up[:, 1])

        # Combine original and mirrored points
        all_points = np.vstack([points, points_left, points_right, points_down, points_up])
        
        return all_points

    def generate_voronoi(self):

        distance_from_edge = 20
        new_edge = 20
        buffer_distance = 40

        # Generate points inside the canvas, away from the edge
        inner_points = np.random.rand(self.regions - 4, 2)
        inner_points[:, 0] *= (self.game_width - 2 * distance_from_edge)
        inner_points[:, 1] *= (self.game_height - 2 * distance_from_edge)
        inner_points += distance_from_edge

        # Generate additional buffer points closer to the edge
        buffer_points = np.random.rand(self.regions // 2, 2)  # One third as many buffer points
        buffer_points[:, 0] *= (self.game_width - 2 * buffer_distance)
        buffer_points[:, 1] *= (self.game_height - 2 * buffer_distance)
        buffer_points += buffer_distance

        self.points = np.vstack([inner_points, buffer_points])
        self.bounding_box = np.array([0., self.game_width, 0., self.game_height])

        print("Points:", self.points)
        print("Bounding box:", self.bounding_box)

        self.points = self.mirror_points(self.points, self.bounding_box)
        self.vor = Voronoi(self.points)

        self.regions_data = {}

        for region_index, region_vertices in enumerate(self.vor.regions):

            if not region_vertices or -1 in region_vertices:  # Skip empty or infinite regions
                continue

            polygon = [self.vor.vertices[i] for i in region_vertices]
            sandy_base = self.get_sandy_color()
            centroid = np.mean(polygon, axis=0)

            # Filter out distant regions
            if any(x < (-100) or x >= (self.game_width + 200) for x, _ in polygon) or \
                any(y < (-100) or y >= (self.game_height + 200) for _, y in polygon):
                    continue
            
            # Set all initial data for each region to dict
            self.regions_data[region_index] = {
                "vertices": region_vertices,
                "polygon": polygon,
                "sandy_base": sandy_base,
                "centroid": centroid,
                "is_city": False,  # Will update this flag for cities
                "city_coords": None,  # Will update for cities
                "edge": False  # Will update for edge regions
            }

            # Check if the region is close to the edge
            if any(x < new_edge or x >= (self.game_width - new_edge) for x, _ in polygon) or \
                any(y < new_edge or y >= (self.game_height - new_edge) for _, y in polygon):
                    self.regions_data[region_index].update({"edge": True})

                    # Combine some edge regions into larger ones with neighbors
                    self.playable_regions(polygon, centroid, sandy_base, 0.8, 5, tag="region")
                    continue
            
            # Decorate according to region type
            self.playable_regions(polygon, centroid, sandy_base, 0.8, 5, tag="region")
            # Set edge to False
            self.regions_data[region_index].update({"edge": False})

        # Crown cities
        valid_city_indices = [
                i for i in range(len(self.points))
                if self.vor.point_region[i] in self.regions_data and not self.regions_data[self.vor.point_region[i]].get("edge", False)]
        self.centroids = np.random.choice(valid_city_indices, size=self.cities, replace=False)
        for i in self.centroids:
            # Ensure we have the right region index for each city
            region_index = self.vor.point_region[i]
            if region_index in self.regions_data:
                x, y = self.points[i]
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill='black')

                # Update the data structure
                self.regions_data[region_index].update({
                    "is_city": True,
                    "city_coords": (x, y)
                })

                # Add the index text
                self.canvas.create_text(x + 10, y, text=str(region_index), font=("Arial", 8), tags="index")

    def playable_regions(self, polygon, centroid, sandy_base, opacity, width, tag=""):

        if centroid is None:
            centroid = np.mean(polygon, axis=0)

        sandy_light = self.get_sandy_lighter_color(sandy_base, opacity)
        sandy_outline = self.get_sandy_lighter_color(sandy_base, opacity - 0.3)
        self.canvas.create_polygon(*np.ravel(polygon), outline=sandy_outline, fill=sandy_light, width=width, tags=f"{tag}")

        sandy_light_2 = self.get_sandy_lighter_color(sandy_light, 1.1)
        adjusted_polygon = [(p + centroid) / 2 for p in polygon]
        self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=sandy_light_2, tags=f"{tag}")

        sandy_light_3 = self.get_sandy_lighter_color(sandy_light_2, 1.1)
        adjusted_polygon = [(p + centroid) / 2 for p in adjusted_polygon]
        self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=sandy_light_3, tags=f"{tag}")

    def get_sandy_color(self):
        # Base sandy RGB values
        base_r, base_g, base_b = 222, 184, 135  # RGB for #deb887
        
        # Standard deviation for variation
        std_dev = 5
        
        # Apply Gaussian variation
        r = int(random.gauss(base_r, std_dev))
        g = int(random.gauss(base_g, std_dev))
        b = int(random.gauss(base_b, std_dev))
        
        # Clamp values to valid RGB range
        r = max(min(r, 255), 0)
        g = max(min(g, 255), 0)
        b = max(min(b, 255), 0)
        
        return f'#{r:02x}{g:02x}{b:02x}'

    def get_sandy_lighter_color(self, colour, opacity):

        r, g, b = int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)

        # Base sandy RGB values
        r = int((1 - opacity) * 255 + opacity * r)
        g = int((1 - opacity) * 255 + opacity * g)
        b = int((1 - opacity) * 255 + opacity * b)

        # Clamp values to valid RGB range
        r = max(min(r, 255), 0)
        g = max(min(g, 255), 0)
        b = max(min(b, 255), 0)

        # Convert RGB back to hexadecimal
        lighter_color = f'#{r:02x}{g:02x}{b:02x}'
        return lighter_color

    def on_mouse_over(self, event):
        x, y = event.x, event.y
        min_distance = float('inf')
        closest_region_index = None

        # Iterate through regions_data to find the closest centroid
        for region_index, region_info in self.regions_data.items():
            if region_info['centroid'] is None:
                continue
            centroid = region_info['centroid']
            distance = np.sqrt((centroid[0] - x) ** 2 + (centroid[1] - y) ** 2)
            if distance < min_distance:
                min_distance = distance
                closest_region_index = region_index

        # If a region is close enough, highlight its region
        if closest_region_index is not None:  # Adjust threshold as needed
            self.highlight_region(closest_region_index)
        else:
            # If no region is close enough, remove any existing highlight
            self.canvas.delete("highlight")

    def highlight_region(self, region_index):
        self.canvas.delete("highlight")  # Remove any existing highlights

        if region_index in self.regions_data:
            region_info = self.regions_data[region_index]
            polygon = region_info['polygon']  # Use the pre-computed polygon
            sandy_base = region_info['sandy_base']
            centroid = region_info['centroid']

            # Highlight the region if playable
            self.playable_regions(polygon, centroid, sandy_base, 0.9, 1, tag="highlight")

            # Use city_coords location and draw oval
            if region_info['is_city']:
                x, y = region_info['city_coords']
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill='black', tags="highlight")
                self.canvas.create_text(x + 10, y, text=str(region_index), font=("Arial", 8), tags="index")

    def on_mouse_click(self, event):
        # x, y = event.x, event.y
        # min_distance = float('inf')
        # closest_region_index = None

        # # Iterate through regions_data to find the closest centroid
        # for region_index, region_info in self.regions_data.items():
        #     if region_info['centroid'] is None:
        #         continue
        #     centroid = region_info['centroid']
        #     distance = np.sqrt((centroid[0] - x) ** 2 + (centroid[1] - y) ** 2)
        #     if distance < min_distance:
        #         min_distance = distance
        #         closest_region_index = region_index

        # # If a region is close enough, highlight its region
        # if closest_region_index is not None:
        #     print(f"Clicked on region {closest_region_index}")
        x, y = event.x, event.y
        self.start_region_index = self.identify_region(x, y)
        # print("Start region index:", self.start_region_index)

    def on_mouse_drag(self, event):
        x, y = event.x, event.y
        current_region = self.identify_region(x, y)
        # print(f"Current region: {current_region}, Mouse down at ({x}, {y})")

    def on_mouse_up(self, event):
        x, y = event.x, event.y
        end_region_index = self.identify_region(x, y)
        if self.start_region_index is not None and end_region_index is not None:
            print(f"Clicked on region {self.start_region_index} initially, and ended on region {end_region_index}")

            # Check if start region and end region have citires
            if self.regions_data[self.start_region_index]['is_city'] and self.regions_data[end_region_index]['is_city']:
                self.send_boids(self.start_region_index, end_region_index)

            else:
                print("Start and/or end region does not have a city")

        self.start_region_index = None

    def identify_region(self, x, y):
        min_distance = float('inf')
        closest_region_index = None

        # Iterate through regions_data to find the closest centroid
        for region_index, region_info in self.regions_data.items():
            if region_info['centroid'] is None:
                continue
            centroid = region_info['centroid']
            distance = np.sqrt((centroid[0] - x) ** 2 + (centroid[1] - y) ** 2)
            if distance < min_distance:
                min_distance = distance
                closest_region_index = region_index

        # If a region is close enough, return its index
        return closest_region_index

    def send_boids(self, start, end):
        start = self.regions_data[start]['city_coords']
        start = np.array(start)
        end = self.regions_data[end]['city_coords']
        end = np.array(end)
        print(f"Sending boids from {start} to {end}")

        # Initialize boids with unique IDs based on current active boids
        current_boid_count = len([boid for boid in self.boids if boid.active])
        new_boids = [Boid(start, boid_id=current_boid_count + i) for i in range(10)]
        self.boids.extend(new_boids)

        for boid in new_boids:
            boid.graphic_id = self.canvas.create_oval(
                boid.position[0] - 2, boid.position[1] - 2, 
                boid.position[0] + 2, boid.position[1] + 2, 
                fill='black', tags=f"boid_{boid.id}"
            )

        # Start updating boids for the first time
        self.update_boids_continuously(end)

    def update_boids_continuously(self, end):

        active_boids = [boid for boid in self.boids if boid.active]
        if not active_boids:  # No more active boids to update
            return

        self.update_boids(active_boids, end)

        for boid in active_boids:
            if np.linalg.norm(boid.position - end) < 10:
                boid.active = False  # Deactivate boid
                self.canvas.delete(boid.graphic_id)  # Optionally, remove the boid's visual representation
            else:
                self.move_boid(boid)

        # Schedule the next update
        self.root.after(100, lambda: self.update_boids_continuously(end))

    def update_boids(self, boids, end, cohesion_strength=0.05, alignment_strength=0.05, separation_strength=0.03):
        for boid in boids:
            acceleration = np.zeros(2)

            nearby_boids = [other for other in boids if np.linalg.norm(boid.position - other.position) < self.perception_radius and other != boid]

            # Cohesion: Move towards the average position of nearby boids
            cohesion_vector = np.zeros(2)
            if nearby_boids:
                average_position = np.mean([other.position for other in nearby_boids], axis=0)
                cohesion_vector = (average_position - boid.position) * cohesion_strength

            # Cohesion - Move towards the average position of nearby boids
            cohesion_center = np.mean([other.position for other in boids if np.linalg.norm(boid.position - other.position) < self.perception_radius and other != boid], axis=0, keepdims=True)
            if len(cohesion_center) > 0:
                cohesion_vector = self.normalize(cohesion_center - boid.position) * self.boid_speed - boid.velocity
                acceleration += self.limit_magnitude(cohesion_vector, self.max_acceleration)

            # Alignment: Align velocity with the average velocity of nearby boids
            average_velocity = np.mean([other.velocity for other in boids if np.linalg.norm(boid.position - other.position) < self.perception_radius and other != boid], axis=0, keepdims=True)
            if len(average_velocity) > 0:
                alignment_vector = self.normalize(average_velocity) * self.boid_speed - boid.velocity
                acceleration += self.limit_magnitude(alignment_vector, self.max_acceleration)

            # Separation: Move away from nearby boids to avoid crowding
            separation_vector = np.sum([(boid.position - other.position) / np.linalg.norm(boid.position - other.position)**2 for other in boids if np.linalg.norm(boid.position - other.position) < self.perception_radius and other != boid], axis=0)
            if np.linalg.norm(separation_vector) > 0:
                acceleration += self.limit_magnitude(self.normalize(separation_vector) * self.boid_speed, self.max_acceleration)

            # Goal direction
            goal_direction = self.normalize(end - boid.position) * self.boid_speed
            acceleration += self.limit_magnitude(goal_direction - boid.velocity, self.max_acceleration)

            # Apply acceleration and limit speed
            boid.velocity += acceleration
            boid.velocity = self.limit_magnitude(boid.velocity, self.boid_speed)
            boid.position += boid.velocity

            # Adjust velocity based on the behaviors
            move_vector = cohesion_vector + alignment_vector + separation_vector

            # Calculate direction towards the goal and add to move vector
            to_goal = (end - boid.position) * 0.01
            move_vector += to_goal

            # Normalize and apply speed
            if np.linalg.norm(move_vector) > 0:
                move_vector = move_vector / np.linalg.norm(move_vector) * self.boid_speed

            boid.velocity = move_vector
            boid.position += boid.velocity

    def calculate_cohesion(self, boids):
        """Calculate the average position of the boids to steer towards for cohesion."""
        if not boids:
            return np.zeros(2)
        average_position = np.mean([boid.position for boid in boids], axis=0)
        return average_position

    def move_boid(self, boid):
        dx = boid.velocity[0]
        dy = boid.velocity[1]
        self.canvas.move(boid.graphic_id, dx, dy)  # Move the boid's oval

    def normalize(self, vector):
        norm = np.linalg.norm(vector)
        if norm == 0: 
            return vector
        return vector / norm

    def limit_magnitude(self, vector, max_magnitude):
        magnitude = np.linalg.norm(vector)
        if magnitude > max_magnitude:
            return vector / magnitude * max_magnitude
        return vector

class Boid:
    def __init__(self, position, boid_id):
        self.id = boid_id

        self.position = np.array(position)
        self.velocity = np.zeros(2)  # Start with zero velocity for simplicity
        self.graphic_id = None  # To store the canvas ID of the boid's oval

        self.active = True

if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()