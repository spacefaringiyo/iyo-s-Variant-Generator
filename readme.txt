# iyo's Variant Generator 0.2

A user-friendly desktop application for quickly and easily creating multiple variants of KovaaK's scenario files. This tool is for scenario creators who want to generate different difficulty levels (e.g., smaller/larger targets, faster/slower bots) without manually editing `.sce` files.

---

## Features

-   **Load Existing Scenarios:** Browse and load any `.sce` scenario file.
-   **Batch Variant Creation:** Generate dozens of variants in a single click.
-   **Intelligent Bot Modifiers:**
    -   **Size:** Modifies the bot's `MainBBRadius` for precise size changes.
    -   **Speed:** Modifies the bot's `MaxSpeed` and `MaxCrouchSpeed` values.
    -   Handles scenarios with single or multiple bot profiles automatically.
-   **Timescale & Duration:** Easily create variants with different game speeds and challenge lengths.
-   **Smart Score Scaling:** Automatically adjusts scoring for duration variants to maintain score-per-minute integrity.
-   **Persistent Settings:** Remembers your folder path, custom values, and checkbox states between sessions via a `settings.json` file.
-   **User-Friendly Interface:** A clean and simple UI built with Tkinter for maximum compatibility.

## How to Use

1.  **Prerequisites(If you don't use .exe file):** Ensure you have Python installed on your system. 
2.  **Run the Application:** Execute the `variant_generator_tkinter.py` script.
3.  **Select Scenario:**
    -   Click "Browse..." to select your KovaaK's scenarios folder (e.g., `...\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Scenarios`).
    -   Enter the exact name of the scenario file (without the `.sce` extension) you want to modify.
    -   Click "Load Scenario".
4.  **Check Base Stats:** The application will display the detected bot profiles and their base statistics for radius and speed.
5.  **Choose Variants:** Select the checkboxes for all the variants you wish to create. You can "Select All" or "Deselect All" for each category.
6.  **Generate:** Click the "Generate Variants" button. The new `.sce` files will be created in the same folder as the original.

## Customization

You can click the **"Edit Values"** button to change the percentage and duration values used for generation. Click **"Save Values"** to apply your changes. These custom values will be saved for your next session.

## Acknowledgements

-   Developed by iyo.
-   Co-developed with **Gemini**, a large language model from Google.
-   Special thanks to Corporate Serf for providing feedbacks and suggestions.

## License

This project is licensed under the MIT License



## Changelog
0.1 - base
0.2 - added multi bot support
0.3 - accounted for the case where Sce file name and Name= inside the file doesn't match up