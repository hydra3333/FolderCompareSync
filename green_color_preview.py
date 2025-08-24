import tkinter as tk
from tkinter import ttk

def show_green_colors():
    """Display various green colors for comparison"""
    root = tk.Tk()
    root.title("Green Color Preview")
    root.geometry("400x500")
    
    # List of green colors to test
    green_colors = [
        "green",
        "darkgreen", 
        "forestgreen",
        "seagreen",
        "mediumseagreen",
        "darkolivegreen",
        "olivedrab",
        "limegreen",
        "springgreen",
        "lightgreen",
        "palegreen",
        "yellowgreen"
    ]
    
    # Create a frame for the color samples
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    ttk.Label(main_frame, text="Green Color Options:", font=("Arial", 14, "bold")).pack(pady=(0, 10))
    
    # Create color sample buttons
    for color in green_colors:
        # Create a frame for each color sample
        color_frame = ttk.Frame(main_frame)
        color_frame.pack(fill=tk.X, pady=2)
        
        # Color name label
        name_label = ttk.Label(color_frame, text=f'"{color}"', width=20, anchor="w")
        name_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Color sample button
        sample_button = tk.Button(
            color_frame, 
            text="Sample Text", 
            fg=color,
            font=("Arial", 10, "bold"),
            relief="flat",
            bg="white",
            width=15
        )
        sample_button.pack(side=tk.LEFT)
    
    # Add recommendation
    ttk.Label(main_frame, text='\nRecommendation: "darkgreen" is usually the best choice\nfor a professional dark green button.', 
              font=("Arial", 9), foreground="blue").pack(pady=(20, 0))
    
    root.mainloop()

# Run the preview
if __name__ == "__main__":
    show_green_colors()