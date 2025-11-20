# main.py
import tkinter as tk
from ttkthemes import ThemedTk
from app_gui import VariantGeneratorApp

if __name__ == "__main__":
    # We use the 'black' theme as a base
    root = ThemedTk(theme="black", themebg=True)
    
    # Define our "Chroma Key" color. 
    # Any pixel with this color will become fully transparent.
    # We use #000001 (almost pure black) to blend well with dark themes.
    root.wm_attributes('-transparentcolor', '#000001')
    
    app = VariantGeneratorApp(root)
    root.mainloop()