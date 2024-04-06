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

                    continue
            
            # Decorate according to region type
            self.playable_regions(polygon, centroid, sandy_base, 0.8, 5, tag="region")
            # Set edge to False
            self.regions_data[region_index].update({"edge": False})

        # Merge edge regions and create mountains and oceans
        self.merge_regions()
        # self.merge_regions()

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

    def find_edge_region_neighbours(self):
        neighbours = {}  # This will map each edge region index to its neighbours

        # Iterate over all regions to find those that are marked as edge regions
        for region_index, region_data in self.regions_data.items():
            if region_data["edge"]:  # Ensure we're only considering edge regions
                neighbours[region_index] = set()

                # Now, find other regions that share vertices with this edge region
                for other_index, other_data in self.regions_data.items():
                    if other_index != region_index and other_data["edge"]:  # Avoid comparing the region to itself and ensure it's an edge region
                        shared_vertices = set(region_data["vertices"]) & set(other_data["vertices"])
                        
                        # If they share at least two vertices, we consider them neighbours
                        if len(shared_vertices) >= 2:
                            neighbours[region_index].add(other_index)

        return neighbours

    def merge_polygons(self, region_index, neighbour_index):
        # Assuming vertices are ordered correctly for Shapely to interpret
        polygon1 = Polygon([self.vor.vertices[i] for i in self.regions_data[region_index]["vertices"]])
        polygon2 = Polygon([self.vor.vertices[i] for i in self.regions_data[neighbour_index]["vertices"]])

        # Use the union of the two polygons to merge them
        merged_polygon_shape = polygon1.union(polygon2)

        # Extract the exterior coordinates of the merged polygon
        merged_polygon_coords = list(merged_polygon_shape.exterior.coords)

        return merged_polygon_coords

    def merge_regions(self):
        # Find edge region neighbours
        neighbours = self.find_edge_region_neighbours()
        print("Edge region neighbours:", neighbours)

        # Merge regions appropriately
        merged_regions = set()
        merged_polygons = {}  # Store the merged polygons to avoid recomputing them
        for region_index, neighbour_indices in neighbours.items():
            print("Processing region:", region_index)
            if region_index in merged_regions:
                print("Skipping region:", region_index, "as it has already been merged")
                continue

            valid_neighbour_found = False  # Flag to indicate if a valid neighbour has been found
            for neighbour_index in neighbour_indices:
                if neighbour_index in merged_regions or region_index == neighbour_index:
                    print("Skipping neighbour:", neighbour_index, "as it has already been merged or is the same region")
                    continue  # Skip if the neighbour has been merged or is the same region

                valid_neighbour_found = True  # Valid neighbour found, set the flag to True
                print("Valid neighbour found: Processing neighbour:", neighbour_index)
                break  # Exit the loop since we only need one valid neighbour for merging

            if valid_neighbour_found:
                # Merge the regions
                merged_vertices_indices = set(self.regions_data[region_index]["vertices"]) | set(self.regions_data[neighbour_index]["vertices"])
                print("Merging regions:", region_index, neighbour_index)
                print("Merging:", set(self.regions_data[region_index]["vertices"]) | set(self.regions_data[neighbour_index]["vertices"]))
                
                # Create a new polygon for the merged region
                # merged_polygon = [self.vor.vertices[i] for i in merged_vertices_indices]
                merged_polygon = self.merge_polygons(region_index, neighbour_index)
                print("Merged polygon:", merged_polygon)

                sandy_base = self.get_sandy_color()

                # Update the region data
                new_region_index = max(self.regions_data.keys()) + 1  # Create a new index for the merged region
                self.regions_data[new_region_index] = {
                    "vertices": list(merged_vertices_indices),
                    "polygon": merged_polygon,
                    "sandy_base": self.get_sandy_color(),  # Assuming a method to get color
                    "centroid": None,  # Simplified calculation
                    "is_city": False,
                    "city_coords": None,
                    "edge": True
                }

                merged_polygons[(region_index, neighbour_index)] = merged_polygon

                # self.playable_regions(merged_polygon, new_centroid, sandy_base, 1, 5, tag="region")

                # Mark original regions as merged
                merged_regions.add(region_index)
                merged_regions.add(neighbour_index)

        # print("Merged polygons:", merged_polygons)
        # self.playable_regions(merged_polygon, new_centroid, sandy_base, 1, 5, tag="region")

        for region_index, region_data in self.regions_data.items():
            if region_data["edge"]:
                self.playable_regions(region_data["polygon"], region_data["centroid"], region_data["sandy_base"], 1, 5, tag="region")

        # Find any lone edge regions that were not merged
        for region_index, region_data in self.regions_data.items():
            if region_data["edge"] and region_index not in merged_regions:

                print("Lone edge region:", region_index)
                polygon = region_data["polygon"]
                centroid = region_data["centroid"]
                sandy_base = region_data["sandy_base"]
                # self.playable_regions(polygon, centroid, sandy_base, 1, 5, tag="region")
        
        # Remove the original regions from the canvas
        for region_index in merged_regions:
            print("Removing regions:", region_index)
            del self.regions_data[region_index]

    # def in_box(self):
    #     new_edge = 5
    #     bounding_box = box(new_edge + 2, new_edge + 2,
    #                         self.game_width - new_edge,
    #                         self.game_height - new_edge,
    #                         ccw=True)
    #     i = np.logical_and(np.logical_and(bounding_box[0] <= self.points[:, 0],
    #                                             self.points[:, 0] <= bounding_box[1]),
    #                             np.logical_and(bounding_box[2] <= self.points[:, 1],
    #                                             self.points[:, 1] <= bounding_box[3]))
        
    #     print("i", i)
        # return 

    # def draw_bounding_box(self):
    #     # Define the bounding box dimensions
    #     bbox_margin = 20  # Margin from the edge of the game area
    #     bbox_x1 = bbox_margin
    #     bbox_y1 = bbox_margin
    #     bbox_x2 = self.game_width - bbox_margin
    #     bbox_y2 = self.game_height - bbox_margin

    #     # Draw the bounding box
    #     self.canvas.create_rectangle(bbox_x1, bbox_y1, bbox_x2, bbox_y2, outline='red', width=2)

    def draw_overlapping_regions(self, overlapping_points):
        for region_index, intersection in overlapping_points.items():
            # Check if the intersection is a Polygon (it could also be a MultiPolygon)
            if intersection.geom_type == 'Polygon':
                exterior_coords = list(intersection.exterior.coords)
                flat_polygon = [coord for point in exterior_coords for coord in point]
                self.canvas.create_polygon(flat_polygon, outline='blue', fill='', width=2)
            elif intersection.geom_type == 'MultiPolygon':
                # Handle the case where the intersection is a MultiPolygon
                for poly in intersection:
                    exterior_coords = list(poly.exterior.coords)
                    flat_polygon = [coord for point in exterior_coords for coord in point]
                    self.canvas.create_polygon(flat_polygon, outline='blue', fill='', width=2)

    def adjust_polygon(self, polygon):
        adjusted_polygon = []
        for x, y in polygon:
            # Adjust x and y coordinates to create a border around the canvas
            adjusted_x = min(max(x, 10), self.game_width - 5)
            adjusted_y = min(max(y, 10), self.game_height - 5)
            adjusted_polygon.append((adjusted_x, adjusted_y))
        return adjusted_polygon
    
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

if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()