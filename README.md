# Blender Batch FBX Exporter

A Blender add-on designed for exporting multiple animations and objects to separate FBX files with Unreal Engine-friendly settings. This tool streamlines the export process for characters, skeletal meshes, and their associated animations, allowing for batch exporting of assets.

## Key Features

- **Batch export FBX files** for characters, objects, and animations.
- Custom export settings for Unreal Engine, including unit scaling, correct axis orientation, and baked animations.
- **Character export**: Select multiple objects or collections, define the character's armature, and export them all in one FBX file.
- **Animation export**: Batch export selected animations (actions) with frame range control and scaling options for Unreal Engine.
- User-friendly interface for **quick selection and export**.
- Customizable export settings, including mesh modifiers, tangent space, and more.

## How to Install

1. **Download the ZIP file**: You can find the latest version of the add-on [here](https://github.com/yourusername/blender-batch-fbx-exporter/releases).
2. **Open Blender** and go to `Edit` > `Preferences`.
3. In the Preferences window, select the `Add-ons` tab.
4. Click `Install...` at the top-right of the window.
5. Navigate to and select the **ZIP file** you downloaded.
6. After installation, search for "Batch FBX Exporter" in the add-ons list and enable it by checking the box.
7. The add-on will now be available in the **Tool** tab of the 3D View Sidebar.

## Usage Instructions

1. Set the **export path** for the FBX files.
2. Select whether to **export characters** or **animations**, or both.
3. Customize the export settings, such as limiting the export to selected objects, applying mesh modifiers, or baking animations.
4. For character export, select the armature and the objects associated with the character.
5. For animation export, select which actions (animations) to export, or use the "Select All" option for batch export.
6. Click the **Batch Export FBX** button to start the export process.

## Project Story

The *Batch FBX Exporter* was created to simplify the process of exporting multiple assets from Blender to Unreal Engine. By providing an easy-to-use interface for batch exporting characters and animations, the add-on helps streamline workflows for game developers and animators.

This project was developed with the assistance of AI tools like ChatGPT and Claude, which helped turn the concept into code.

Feel free to explore, use the add-on, suggest improvements, or contribute to its development!
