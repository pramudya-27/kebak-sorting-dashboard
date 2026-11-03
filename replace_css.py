import re

new_css = """
        :root {
            --bg-body: #f0f4f8; /* Soft ocean breeze */
            --bg-card: #ffffff;
            --border-light: #e2e8f0;
            --primary-blue: #0284c7; /* Ocean Blue */
            --primary-teal: #0d9488; /* Deep Teal */
            --accent-coral: #ef4444;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #64748b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        .container {
            max-width: 1920px;
            margin: 0 auto;
            padding: 32px 40px;
            position: relative;
            z-index: 1;
        }

        /* Header Section */
        header {
            background: var(--bg-card);
            border: 1px solid var(--border-light);
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 32px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03), 0 1px 3px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }

        .header-title-box {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .ocean-logo {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--primary-blue), var(--primary-teal));
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            color: #ffffff;
            box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3);
        }

        h1 {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.5px;
        }

        .subtitle {
            font-size: 0.95rem;
            color: var(--text-secondary);
            margin-top: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }

        .telemetry-badge {
            background: #f1f5f9;
            border: 1px solid var(--border-light);
            padding: 8px 16px;
            border-radius: 12px;
            font-weight: 500;
            font-size: 0.9rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .telemetry-badge i {
            color: var(--primary-blue);
        }

        .status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 20px;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            color: #059669;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-dot {
            width: 10px;
            height: 10px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-light);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            align-items: center;
            gap: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.04);
        }

        .stat-icon {
            width: 60px;
            height: 60px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }

        /* Different colors for stat icons */
        .stat-card:nth-child(1) .stat-icon {
            background: #eff6ff;
            color: #3b82f6;
        }
        .stat-card:nth-child(2) .stat-icon {
            background: #f0fdfa;
            color: #14b8a6;
        }
        .stat-card:nth-child(3) .stat-icon {
            background: #fffbeb;
            color: #f59e0b;
        }
        .stat-card:nth-child(4) .stat-icon {
            background: #f8fafc;
            color: #64748b;
        }

        .stat-content {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
        }

        .stat-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Video Container */
        .video-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 32px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-light);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-light);
        }

        .card h2 i {
            color: var(--primary-blue);
            margin-right: 10px;
        }

        .video-feed {
            position: relative;
            width: 100%;
            aspect-ratio: 16/9;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.05);
        }

        canvas {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }

        .viewport-hud {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10;
        }

        /* Removed neon corners, just keep the tag */
        .hud-tag {
            position: absolute;
            top: 16px;
            right: 16px;
            background: rgba(255, 255, 255, 0.9);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .rec-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-coral);
            border-radius: 50%;
            animation: pulseRec 1.5s infinite;
        }

        @keyframes pulseRec {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
        }

        /* Analytics Section */
        .analytics-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 32px;
            margin-bottom: 40px;
        }

        .chart-wrapper {
            position: relative;
            height: 350px;
            width: 100%;
        }

        .history-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 350px;
            overflow-y: auto;
            padding-right: 8px;
        }

        .history-list::-webkit-scrollbar {
            width: 6px;
        }

        .history-list::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 3px;
        }

        .history-list::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }

        .history-item {
            background: #f8fafc;
            border: 1px solid var(--border-light);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }

        .history-item:hover {
            background: #f1f5f9;
        }

        .history-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .item-name {
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--text-primary);
        }

        .item-time {
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .item-conf {
            background: #eff6ff;
            color: #3b82f6;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700;
        }

        /* Loading Skeleton */
        .skeleton {
            background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
            background-size: 200% 100%;
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }

        /* Responsive Design */
        @media (max-width: 1200px) {
            .video-container {
                grid-template-columns: 1fr;
            }
            .analytics-container {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 768px) {
            .header-controls {
                width: 100%;
                justify-content: space-between;
            }
        }
"""

with open('wsl/static/dashboard.html', 'r') as f:
    content = f.read()

# Replace the entire <style> block
content = re.sub(r'<style>.*?</style>', f'<style>\n{new_css}\n    </style>', content, flags=re.DOTALL)

# Remove hud-corner divs which are no longer needed
content = re.sub(r'<div class="hud-corner.*?</div>', '', content, flags=re.DOTALL)

with open('wsl/static/dashboard.html', 'w') as f:
    f.write(content)
print("CSS replaced.")
