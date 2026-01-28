#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minecraft Plot Map Generator
Erstellt eine interaktive HTML-Karte aus Minecraft-Plot-Daten
"""

import json
import hashlib


def get_color_from_uuid(uuid):
    """Generiert eine konsistente Farbe aus einer UUID"""
    # Hash der UUID erstellen
    hash_obj = hashlib.md5(uuid.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Erste 6 Zeichen als Farbe verwenden
    color = '#' + hash_hex[:6]
    return color


def parse_owner_from_permissions(group_permissions):
    """Extrahiert die Owner-UUID aus den groupPermissions"""
    if '_ALL_' in group_permissions:
        owner_perm = group_permissions['_ALL_'].get('fe.internal.plot.owner')
        if owner_perm:
            return owner_perm
    return None


def get_player_name_from_player_permissions(player_permissions):
    """Extrahiert den Spielernamen aus den playerPermissions"""
    for key, perms in player_permissions.items():
        if 'fe.internal.player.groups' in perms:
            if 'PLOT_OWNER' in perms['fe.internal.player.groups']:
                # Format: (uuid|spielername)
                if '|' in key:
                    return key.split('|')[1].rstrip(')')
    return None


def calculate_area(low, high):
    """
    Berechnet die Fläche in m² (X-Z-Ebene)
    Wichtig: Koordinaten sind Eckpunkte, daher +1 für jeden Block
    """
    width = abs(high['x'] - low['x']) + 1
    depth = abs(high['z'] - low['z']) + 1
    return width * depth


def generate_html_map(json_file, output_file='minecraft_map.html'):
    """Generiert eine interaktive HTML-Karte aus der JSON-Datei"""
    
    # JSON-Datei einlesen
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Dimension-Namen
    dimension_names = {
        -1: 'Nether',
        -2147483648: 'Mystcraft Profiler Dummy',
        0: 'Oberwelt',
        1: 'Ende'
    }
    
    # Plots nach Dimensionen sammeln
    plots_by_dimension = {}
    
    for dim_id_str, world_zone in data['worldZones'].items():
        dim_id = int(dim_id_str)
        dim_name = dimension_names.get(dim_id, f'Dimension {dim_id}')
        
        plots = []
        for area_zone in world_zone.get('areaZones', []):
            # Überspringe Zonen ohne area (wie im Beispiel _PLOT_3)
            area = area_zone.get('area', {})
            if 'dim' not in area and 'low' not in area:
                # Fallback: verwende nur low und high
                low = area_zone['area']['low']
                high = area_zone['area']['high']
                dim = dim_id
            else:
                low = area.get('low', {})
                high = area.get('high', {})
                dim = area.get('dim', dim_id)
            
            # Owner-UUID und Namen extrahieren
            owner_uuid = parse_owner_from_permissions(area_zone.get('groupPermissions', {}))
            owner_name = get_player_name_from_player_permissions(area_zone.get('playerPermissions', {}))
            
            if not owner_name:
                owner_name = 'Unbekannt'
            
            if not owner_uuid:
                owner_uuid = owner_name
            
            # Fläche berechnen
            area_m2 = calculate_area(low, high)
            price = area_m2 * 256
            
            plot_data = {
                'name': area_zone.get('name', 'Unbekannt'),
                'owner': owner_name,
                'owner_uuid': owner_uuid,
                'low': low,
                'high': high,
                'area_m2': area_m2,
                'price': price,
                'color': get_color_from_uuid(owner_uuid)
            }
            
            plots.append(plot_data)
        
        if plots:
            plots_by_dimension[dim_name] = plots
    
    # HTML generieren
    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft Plot Karte</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
            overflow: hidden;
        }}
        
        #controls {{
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: rgba(0, 0, 0, 0.8);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        
        #dimensionSelect {{
            padding: 8px 12px;
            font-size: 14px;
            border: none;
            border-radius: 4px;
            background: #2a2a2a;
            color: #ffffff;
            cursor: pointer;
            margin-bottom: 10px;
            width: 200px;
        }}
        
        #info {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: rgba(0, 0, 0, 0.8);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            max-width: 300px;
        }}
        
        #canvas {{
            display: block;
            cursor: grab;
            background: #0a0a0a;
        }}
        
        #canvas:active {{
            cursor: grabbing;
        }}
        
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.95);
            color: #ffffff;
            padding: 12px;
            border-radius: 6px;
            pointer-events: none;
            display: none;
            z-index: 2000;
            max-width: 280px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            border: 1px solid #444;
        }}
        
        .tooltip h3 {{
            margin: 0 0 8px 0;
            font-size: 16px;
            color: #4CAF50;
        }}
        
        .tooltip p {{
            margin: 4px 0;
            font-size: 13px;
            line-height: 1.4;
        }}
        
        .tooltip .label {{
            color: #aaa;
            font-weight: 500;
        }}
        
        button {{
            padding: 8px 16px;
            margin: 2px;
            background: #2a2a2a;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }}
        
        button:hover {{
            background: #3a3a3a;
        }}
        
        #zoomLevel {{
            color: #aaa;
            font-size: 12px;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div id="controls">
        <select id="dimensionSelect"></select>
        <div>
            <button onclick="zoomIn()">Zoom +</button>
            <button onclick="zoomOut()">Zoom -</button>
            <button onclick="resetView()">Reset</button>
        </div>
        <div id="zoomLevel">Zoom: 100%</div>
    </div>
    
    <div id="info">
        <h3 style="margin-bottom: 10px;">🗺️ Minecraft Plot Karte</h3>
        <p style="font-size: 12px; color: #aaa;">
            <strong>Steuerung:</strong><br>
            • Maus ziehen: Verschieben<br>
            • Mausrad: Zoomen<br>
            • Hover: Plot-Info anzeigen
        </p>
    </div>
    
    <canvas id="canvas"></canvas>
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        const plotData = {json.dumps(plots_by_dimension, ensure_ascii=False, indent=2)};
        
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const tooltip = document.getElementById('tooltip');
        const dimensionSelect = document.getElementById('dimensionSelect');
        
        let currentDimension = null;
        let currentPlots = [];
        let scale = 2;
        let offsetX = 0;
        let offsetY = 0;
        let isDragging = false;
        let lastX = 0;
        let lastY = 0;
        
        // Canvas-Größe anpassen
        function resizeCanvas() {{
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            drawMap();
        }}
        
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        
        // Dimensionen in Select laden
        Object.keys(plotData).forEach(dim => {{
            const option = document.createElement('option');
            option.value = dim;
            option.textContent = dim;
            dimensionSelect.appendChild(option);
        }});
        
        // Erste Dimension auswählen
        if (Object.keys(plotData).length > 0) {{
            currentDimension = Object.keys(plotData)[0];
            dimensionSelect.value = currentDimension;
            currentPlots = plotData[currentDimension];
        }}
        
        dimensionSelect.addEventListener('change', (e) => {{
            currentDimension = e.target.value;
            currentPlots = plotData[currentDimension];
            resetView();
        }});
        
        // Plot-Grenzen berechnen
        function getPlotBounds(plots) {{
            if (plots.length === 0) return {{ minX: -100, maxX: 100, minZ: -100, maxZ: 100 }};
            
            let minX = Infinity, maxX = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            
            plots.forEach(plot => {{
                minX = Math.min(minX, plot.low.x, plot.high.x);
                maxX = Math.max(maxX, plot.low.x, plot.high.x);
                minZ = Math.min(minZ, plot.low.z, plot.high.z);
                maxZ = Math.max(maxZ, plot.low.z, plot.high.z);
            }});
            
            return {{ minX, maxX, minZ, maxZ }};
        }}
        
        // Karte zeichnen
        function drawMap() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (currentPlots.length === 0) {{
                ctx.fillStyle = '#666';
                ctx.font = '16px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Keine Plots in dieser Dimension', canvas.width / 2, canvas.height / 2);
                return;
            }}
            
            // Koordinatensystem
            ctx.save();
            ctx.translate(canvas.width / 2 + offsetX, canvas.height / 2 + offsetY);
            
            // Grid zeichnen
            ctx.strokeStyle = '#222';
            ctx.lineWidth = 1;
            const gridSize = 50 * scale;
            const startX = -Math.ceil(canvas.width / 2 / gridSize) * gridSize;
            const endX = Math.ceil(canvas.width / 2 / gridSize) * gridSize;
            const startY = -Math.ceil(canvas.height / 2 / gridSize) * gridSize;
            const endY = Math.ceil(canvas.height / 2 / gridSize) * gridSize;
            
            for (let x = startX; x <= endX; x += gridSize) {{
                ctx.beginPath();
                ctx.moveTo(x, startY);
                ctx.lineTo(x, endY);
                ctx.stroke();
            }}
            
            for (let y = startY; y <= endY; y += gridSize) {{
                ctx.beginPath();
                ctx.moveTo(startX, y);
                ctx.lineTo(endX, y);
                ctx.stroke();
            }}
            
            // Achsen
            ctx.strokeStyle = '#444';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(-canvas.width, 0);
            ctx.lineTo(canvas.width, 0);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, -canvas.height);
            ctx.lineTo(0, canvas.height);
            ctx.stroke();
            
            // Plots zeichnen
            currentPlots.forEach(plot => {{
                const x1 = plot.low.x * scale;
                const z1 = plot.low.z * scale;
                const x2 = plot.high.x * scale;
                const z2 = plot.high.z * scale;
                
                const width = Math.abs(x2 - x1) + scale;
                const height = Math.abs(z2 - z1) + scale;
                
                ctx.fillStyle = plot.color + 'CC';
                ctx.fillRect(Math.min(x1, x2), Math.min(z1, z2), width, height);
                
                ctx.strokeStyle = plot.color;
                ctx.lineWidth = 2;
                ctx.strokeRect(Math.min(x1, x2), Math.min(z1, z2), width, height);
            }});
            
            ctx.restore();
        }}
        
        // Plot unter Mausposition finden
        function getPlotAtPosition(mouseX, mouseY) {{
            const worldX = (mouseX - canvas.width / 2 - offsetX) / scale;
            const worldZ = (mouseY - canvas.height / 2 - offsetY) / scale;
            
            for (let plot of currentPlots) {{
                const minX = Math.min(plot.low.x, plot.high.x);
                const maxX = Math.max(plot.low.x, plot.high.x) + 1;
                const minZ = Math.min(plot.low.z, plot.high.z);
                const maxZ = Math.max(plot.low.z, plot.high.z) + 1;
                
                if (worldX >= minX && worldX <= maxX && worldZ >= minZ && worldZ <= maxZ) {{
                    return plot;
                }}
            }}
            return null;
        }}
        
        // Mouse Events
        canvas.addEventListener('mousedown', (e) => {{
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
        }});
        
        canvas.addEventListener('mousemove', (e) => {{
            if (isDragging) {{
                const dx = e.clientX - lastX;
                const dy = e.clientY - lastY;
                offsetX += dx;
                offsetY += dy;
                lastX = e.clientX;
                lastY = e.clientY;
                drawMap();
            }}
            
            // Tooltip
            const plot = getPlotAtPosition(e.clientX, e.clientY);
            if (plot) {{
                tooltip.innerHTML = `
                    <h3>${{plot.name}}</h3>
                    <p><span class="label">Besitzer:</span> ${{plot.owner}}</p>
                    <p><span class="label">Koordinaten:</span><br>
                       Von X:${{plot.low.x}} Z:${{plot.low.z}}<br>
                       Bis X:${{plot.high.x}} Z:${{plot.high.z}}</p>
                    <p><span class="label">Fläche:</span> ${{plot.area_m2}} m²</p>
                    <p><span class="label">Kaufpreis:</span> ${{plot.price.toLocaleString('de-DE')}} €</p>
                `;
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX + 15) + 'px';
                tooltip.style.top = (e.clientY + 15) + 'px';
            }} else {{
                tooltip.style.display = 'none';
            }}
        }});
        
        canvas.addEventListener('mouseup', () => {{
            isDragging = false;
        }});
        
        canvas.addEventListener('mouseleave', () => {{
            isDragging = false;
            tooltip.style.display = 'none';
        }});
        
        canvas.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = scale * delta;
            
            if (newScale >= 0.1 && newScale <= 10) {{
                scale = newScale;
                document.getElementById('zoomLevel').textContent = `Zoom: ${{Math.round(scale * 50)}}%`;
                drawMap();
            }}
        }});
        
        // Zoom-Funktionen
        function zoomIn() {{
            if (scale < 10) {{
                scale *= 1.2;
                document.getElementById('zoomLevel').textContent = `Zoom: ${{Math.round(scale * 50)}}%`;
                drawMap();
            }}
        }}
        
        function zoomOut() {{
            if (scale > 0.1) {{
                scale *= 0.8;
                document.getElementById('zoomLevel').textContent = `Zoom: ${{Math.round(scale * 50)}}%`;
                drawMap();
            }}
        }}
        
        function resetView() {{
            scale = 2;
            offsetX = 0;
            offsetY = 0;
            document.getElementById('zoomLevel').textContent = 'Zoom: 100%';
            drawMap();
        }}
        
        // Initial zeichnen
        drawMap();
    </script>
</body>
</html>"""
    
    # HTML-Datei schreiben
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ HTML-Karte wurde erstellt: {output_file}")
    print(f"✓ Dimensionen: {', '.join(plots_by_dimension.keys())}")
    for dim, plots in plots_by_dimension.items():
        print(f"  - {dim}: {len(plots)} Plots")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Verwendung: python minecraft_plot_map.py <json_datei> [output.html]")
        print("Beispiel: python minecraft_plot_map.py zones.json minecraft_map.html")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'minecraft_map.html'
    
    try:
        generate_html_map(json_file, output_file)
    except Exception as e:
        print(f"✗ Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
