import tkinter as tk
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageTk  # For converting matplotlib plot to a tkinter compatible format
import random
import time

class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metropoly")

        # Screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Game window dimensions
        self.game_height = int(self.screen_height * 0.8)
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

        # Restart Button
        restart_button = tk.Button(self.game_frame, text="Restart", command=self.restart_game)
        restart_button.pack(side=tk.BOTTOM, pady=10)

        self.canvas = tk.Canvas(self.game_frame, width=self.game_width, height=self.game_height, bg='white')
        self.canvas.pack()

        self.generate_voronoi()
        self.canvas.bind("<Motion>", self.on_mouse_over)

        self.start_timer()

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

    def generate_voronoi(self):

        distance_from_edge = 20
        buffer_distance = 40

        # Generate points inside the canvas, away from the edge
        inner_points = np.random.rand(self.regions - 4, 2)
        inner_points[:, 0] *= (self.game_width - 2 * distance_from_edge)
        inner_points[:, 1] *= (self.game_height - 2 * distance_from_edge)
        inner_points += distance_from_edge

        # Generate additional buffer points closer to the edge
        buffer_points = np.random.rand(self.regions // 3, 2)  # One third as many buffer points
        buffer_points[:, 0] *= (self.game_width - 2 * buffer_distance)
        buffer_points[:, 1] *= (self.game_height - 2 * buffer_distance)
        buffer_points += buffer_distance

        self.points = np.vstack([inner_points, buffer_points])

        # Add corner points
        corner_points = np.array([
            [buffer_distance, buffer_distance],
            [self.game_width - buffer_distance, buffer_distance],
            [buffer_distance, self.game_height - buffer_distance],
            [self.game_width - buffer_distance, self.game_height - buffer_distance]
        ])
        self.points = np.vstack([self.points, corner_points])

        self.vor = Voronoi(self.points)
        self.regions_data = {}
        edge_region_indices = set()

        # Draw Voronoi diagram edges
        for region_index, region_vertices in enumerate(self.vor.regions):

            if not region_vertices or -1 in region_vertices:  # Skip empty or infinite regions
                continue

            polygon = [self.vor.vertices[i] for i in region_vertices]
            sandy_base = self.get_sandy_color()
            centroid = np.mean(polygon, axis=0)

            # Edge regions check
            if any(x <= distance_from_edge or x >= self.game_width - distance_from_edge for x, _ in polygon) or \
                any(y <= distance_from_edge or y >= self.game_height - distance_from_edge for _, y in polygon):
                    edge_region_indices.add(region_index)

            # Set all initial data for each region to dict
            self.regions_data[region_index] = {
                "vertices": region_vertices,
                "polygon": polygon,
                "sandy_base": sandy_base,
                "centroid": centroid,
                "is_city": False,  # Will update this flag for cities
                "city_coords": None  # Will update for cities
            }
            
            sandy_light = self.get_sandy_lighter_color(sandy_base, 0.8)
            sandy_outline = self.get_sandy_lighter_color(sandy_base, 0.5)
            self.canvas.create_polygon(*np.ravel(polygon), outline=sandy_outline, fill=sandy_light, width=5)

            sandy_light_2 = self.get_sandy_lighter_color(sandy_light, 1.1)
            adjusted_polygon = [(p + centroid) / 2 for p in polygon]
            self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=sandy_light_2)

            sandy_light_3 = self.get_sandy_lighter_color(sandy_light_2, 1.1)
            adjusted_polygon = [(p + centroid) / 2 for p in adjusted_polygon]
            self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=sandy_light_3)

        # Crown cities
        valid_city_indices = [i for i in range(len(self.points)) if self.vor.point_region[i] not in edge_region_indices]
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

    def adjust_polygon(self, polygon):
        adjusted_polygon = []
        for x, y in polygon:
            # Adjust x and y coordinates to create a border around the canvas
            adjusted_x = min(max(x, 10), self.game_width - 5)
            adjusted_y = min(max(y, 10), self.game_height - 5)
            adjusted_polygon.append((adjusted_x, adjusted_y))
        return adjusted_polygon
    
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

            # Create a darker version of the region's color for the highlight effect
            darker_color = self.get_sandy_lighter_color(sandy_base, 0.8)  # Adjust for the desired effect
            self.canvas.create_polygon(*np.ravel(polygon), outline='', fill=darker_color, tags="highlight")
            
            darker_color_2 = self.get_sandy_lighter_color(darker_color, 1.1)
            adjusted_polygon = [(p + centroid) / 2 for p in polygon]
            self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=darker_color_2, tags="highlight")

            darker_color_3 = self.get_sandy_lighter_color(darker_color_2, 1.1)
            adjusted_polygon = [(p + centroid) / 2 for p in adjusted_polygon]
            self.canvas.create_polygon(*np.ravel(adjusted_polygon), outline='', fill=darker_color_3, tags="highlight")

            # Use city_coords location and draw oval
            if region_info['is_city']:
                x, y = region_info['city_coords']
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill='black', tags="highlight")
                self.canvas.create_text(x + 10, y, text=str(region_index), font=("Arial", 8), tags="index")

if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()