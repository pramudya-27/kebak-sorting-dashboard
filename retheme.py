import re

with open('wsl/static/dashboard.html', 'r') as f:
    content = f.read()

# Remove Three.js script
content = re.sub(r'<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n', '', content)

# Remove canvas and overlay
content = re.sub(r'<canvas id="ocean-canvas"></canvas>\n\s*<div class="caustics-overlay"></div>\n', '', content)

# Remove sound and demo buttons
btn_pattern = r'<button class="btn-ocean" id="soundToggleBtn">.*?</button>\n\s*<button class="btn-ocean" id="demoToggleBtn">.*?</button>'
content = re.sub(btn_pattern, '', content, flags=re.DOTALL)

# Remove ThreeJS and Audio JS sections
js_remove_pattern = r'// 6\. 3D OCEAN BACKGROUND WITH THREE\.JS.*?// 8\. DEMO MODE'
content = re.sub(js_remove_pattern, '// 8. DEMO MODE', content, flags=re.DOTALL)

# Remove event listeners
content = re.sub(r"document\.getElementById\('demoToggleBtn'\)\.addEventListener\('click', \(\) => toggleDemoMode\(\)\);\n", "", content)
content = re.sub(r"document\.getElementById\('soundToggleBtn'\)\.addEventListener\('click', toggleOceanSound\);\n", "", content)

# Keep other JS but replace the CSS completely
# We'll do CSS replacement separately
with open('wsl/static/dashboard.html', 'w') as f:
    f.write(content)
print("HTML/JS cleaned.")
