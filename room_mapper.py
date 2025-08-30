# Room Mapping Tool for 4WD Vehicle Navigation
# Creates a simple room map using rectangles

import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os

class RoomMapper:
    def __init__(self, root):
        self.root = root
        self.root.title("Room Mapping Tool")
        self.root.geometry("800x600")
        
        self.canvas = tk.Canvas(root, bg='white', width=780, height=500)
        self.canvas.pack(pady=10)
        
        # Room data
        self.room_bounds = None
        self.obstacles = []
        self.scale = 1  # pixels per cm
        
        # Drawing state
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        
        self.setup_ui()
        self.bind_events()
        
    def setup_ui(self):
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)
        
        tk.Button(control_frame, text="Set Room Bounds", command=self.set_room_mode).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Add Obstacle", command=self.set_obstacle_mode).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Save Map", command=self.save_map).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Load Map", command=self.load_map).pack(side=tk.LEFT, padx=5)
        
        # Info label
        self.info_label = tk.Label(self.root, text="Click 'Set Room Bounds' to start mapping")
        self.info_label.pack()
        
        self.mode = "none"
        
    def bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
    def set_room_mode(self):
        self.mode = "room"
        self.info_label.config(text="Draw rectangle for room bounds")
        
    def set_obstacle_mode(self):
        self.mode = "obstacle"
        self.info_label.config(text="Draw rectangles for obstacles")
        
    def on_click(self, event):
        if self.mode in ["room", "obstacle"]:
            self.drawing = True
            self.start_x = event.x
            self.start_y = event.y
            
    def on_drag(self, event):
        if self.drawing:
            # Clear previous preview
            self.canvas.delete("preview")
            # Draw preview rectangle
            color = "blue" if self.mode == "room" else "red"
            self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline=color, fill="", tags="preview"
            )
            
    def on_release(self, event):
        if self.drawing:
            self.drawing = False
            self.canvas.delete("preview")
            
            # Get dimensions
            width = abs(event.x - self.start_x)
            height = abs(event.y - self.start_y)
            
            if width < 10 or height < 10:
                return
                
            # Get real-world dimensions
            real_width = simpledialog.askfloat("Width", f"Enter width in cm (drawn: {width}px):")
            real_height = simpledialog.askfloat("Height", f"Enter height in cm (drawn: {height}px):")
            
            if real_width and real_height:
                # Calculate position
                x1 = min(self.start_x, event.x)
                y1 = min(self.start_y, event.y)
                x2 = max(self.start_x, event.x)
                y2 = max(self.start_y, event.y)
                
                rect_data = {
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "width_cm": real_width, "height_cm": real_height
                }
                
                if self.mode == "room":
                    self.room_bounds = rect_data
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=3, tags="room")
                    self.info_label.config(text="Room bounds set. Add obstacles if needed.")
                    
                elif self.mode == "obstacle":
                    self.obstacles.append(rect_data)
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", fill="lightcoral", tags="obstacle")
                    self.info_label.config(text=f"Obstacle added. Total: {len(self.obstacles)}")
    
    def clear_all(self):
        self.canvas.delete("all")
        self.room_bounds = None
        self.obstacles = []
        self.info_label.config(text="Map cleared. Set room bounds to start.")
        
    def save_map(self):
        if not self.room_bounds:
            messagebox.showerror("Error", "Please set room bounds first")
            return
            
        map_data = {
            "room_bounds": self.room_bounds,
            "obstacles": self.obstacles,
            "scale": self.scale
        }
        
        filename = simpledialog.askstring("Save", "Enter filename:", initialvalue="room_map.json")
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            with open(filename, 'w') as f:
                json.dump(map_data, f, indent=2)
            
            messagebox.showinfo("Success", f"Map saved as {filename}")
            
    def load_map(self):
        filename = simpledialog.askstring("Load", "Enter filename:", initialvalue="room_map.json")
        if filename and os.path.exists(filename):
            with open(filename, 'r') as f:
                map_data = json.load(f)
                
            self.clear_all()
            self.room_bounds = map_data.get("room_bounds")
            self.obstacles = map_data.get("obstacles", [])
            self.scale = map_data.get("scale", 1)
            
            # Redraw map
            if self.room_bounds:
                rb = self.room_bounds
                self.canvas.create_rectangle(rb["x1"], rb["y1"], rb["x2"], rb["y2"], 
                                           outline="blue", width=3, tags="room")
                
            for obstacle in self.obstacles:
                self.canvas.create_rectangle(obstacle["x1"], obstacle["y1"], 
                                           obstacle["x2"], obstacle["y2"],
                                           outline="red", fill="lightcoral", tags="obstacle")
            
            self.info_label.config(text=f"Map loaded: {len(self.obstacles)} obstacles")

if __name__ == "__main__":
    root = tk.Tk()
    app = RoomMapper(root)
    root.mainloop()