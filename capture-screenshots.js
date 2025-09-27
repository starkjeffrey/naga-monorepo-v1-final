const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Create screenshots directory
const screenshotsDir = path.join(__dirname, 'app-screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const vueScreenshotsDir = path.join(screenshotsDir, 'vue-app');
const reactScreenshotsDir = path.join(screenshotsDir, 'react-app');

if (!fs.existsSync(vueScreenshotsDir)) {
  fs.mkdirSync(vueScreenshotsDir, { recursive: true });
}
if (!fs.existsSync(reactScreenshotsDir)) {
  fs.mkdirSync(reactScreenshotsDir, { recursive: true });
}

// Vue app pages to capture
const vuePages = [
  { path: '/', name: 'home' },
  { path: '/signin', name: 'signin' },
  { path: '/student-dashboard', name: 'student-dashboard' },
  { path: '/attendance', name: 'attendance' },
  { path: '/grades', name: 'grades' },
  { path: '/schedule', name: 'schedule' },
  { path: '/finances', name: 'finances' },
  { path: '/profile', name: 'profile' },
  { path: '/messages', name: 'messages' },
  { path: '/announcements', name: 'announcements' },
  { path: '/permission', name: 'permission' },
  { path: '/id-card', name: 'id-card' },
  { path: '/profile-photo', name: 'profile-photo' },
  { path: '/enter-code', name: 'enter-code' },
  { path: '/teacher/dashboard', name: 'teacher-dashboard' },
  { path: '/teacher/attendance', name: 'teacher-attendance' },
  { path: '/teacher/generate-code', name: 'teacher-generate-code' },
  { path: '/teacher/courses', name: 'teacher-courses' },
  { path: '/teacher/grades', name: 'teacher-grades' },
  { path: '/teacher/manual-attendance', name: 'teacher-manual-attendance' }
];

async function captureVueScreenshots() {
  console.log('📸 Capturing Vue app screenshots...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, // iPhone 14 Pro dimensions
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  // Try to start Vue dev server first
  console.log('Starting Vue dev server at http://localhost:5174...');

  for (const pageInfo of vuePages) {
    try {
      const url = `http://localhost:5174${pageInfo.path}`;
      console.log(`  Capturing: ${pageInfo.name} (${url})`);

      await page.goto(url, {
        waitUntil: 'networkidle',
        timeout: 30000
      });

      // Wait a bit for any animations to complete
      await page.waitForTimeout(2000);

      // Capture full page screenshot
      await page.screenshot({
        path: path.join(vueScreenshotsDir, `${pageInfo.name}.png`),
        fullPage: true
      });

      // Also capture viewport screenshot
      await page.screenshot({
        path: path.join(vueScreenshotsDir, `${pageInfo.name}-viewport.png`),
        fullPage: false
      });

      console.log(`    ✅ Captured ${pageInfo.name}`);
    } catch (error) {
      console.log(`    ❌ Failed to capture ${pageInfo.name}: ${error.message}`);
    }
  }

  await browser.close();
}

async function captureReactNativeWebScreenshots() {
  console.log('📸 Capturing React Native web screenshots...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, // iPhone 14 Pro dimensions
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
  });

  const page = await context.newPage();

  try {
    // For React Native, we'll capture the web version if available
    const url = 'http://localhost:19006'; // Expo web default port
    console.log(`  Trying Expo web at ${url}`);

    await page.goto(url, {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Wait for app to load
    await page.waitForTimeout(3000);

    // Capture main screen
    await page.screenshot({
      path: path.join(reactScreenshotsDir, 'main-app.png'),
      fullPage: true
    });

    console.log('    ✅ Captured React Native web preview');
  } catch (error) {
    console.log(`    ❌ React Native web not available: ${error.message}`);
    console.log('    ℹ️  To enable web preview, run: npx expo start --web');
  }

  await browser.close();
}

function generateHTMLReport() {
  console.log('📝 Generating HTML report...');

  const vueScreenshots = fs.readdirSync(vueScreenshotsDir)
    .filter(f => f.endsWith('.png') && !f.includes('-viewport'))
    .map(f => ({
      name: f.replace('.png', ''),
      full: f,
      viewport: f.replace('.png', '-viewport.png')
    }));

  const reactScreenshots = fs.readdirSync(reactScreenshotsDir)
    .filter(f => f.endsWith('.png'))
    .map(f => ({
      name: f.replace('.png', ''),
      file: f
    }));

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NAGA Mobile Apps - Screenshot Comparison</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: white;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            text-align: center;
            color: rgba(255,255,255,0.9);
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .app-section {
            margin-bottom: 50px;
        }
        .section-title {
            color: white;
            font-size: 2em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .tech-badge {
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.5em;
        }
        .screenshots-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .screenshot-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        .screenshot-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        .screenshot-header {
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
            text-transform: capitalize;
        }
        .screenshot-container {
            position: relative;
            background: #f5f5f5;
            padding: 10px;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .screenshot-img {
            max-width: 100%;
            max-height: 600px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .no-screenshot {
            color: #999;
            font-style: italic;
            padding: 40px;
            text-align: center;
        }
        .view-toggle {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        .comparison-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 30px;
        }
        .legend {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .legend h3 {
            margin-bottom: 10px;
            color: #333;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 5px 0;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .status-implemented { background: #4CAF50; }
        .status-partial { background: #FFC107; }
        .status-missing { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 NAGA Mobile Apps Comparison</h1>
        <p class="subtitle">Visual comparison between Vue 3 and React Native implementations</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">${vueScreenshots.length}</div>
                <div class="stat-label">Vue 3 Screens</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${reactScreenshots.length}</div>
                <div class="stat-label">React Native Screens</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${new Date().toLocaleDateString()}</div>
                <div class="stat-label">Generated Date</div>
            </div>
        </div>

        <div class="legend">
            <h3>📋 Implementation Status</h3>
            <div class="legend-item">
                <span class="status-dot status-implemented"></span>
                <span>Fully Implemented</span>
            </div>
            <div class="legend-item">
                <span class="status-dot status-partial"></span>
                <span>Partially Implemented</span>
            </div>
            <div class="legend-item">
                <span class="status-dot status-missing"></span>
                <span>Not Yet Implemented</span>
            </div>
        </div>

        <div class="app-section">
            <h2 class="section-title">
                Vue 3 Mobile App
                <span class="tech-badge">Quasar Framework</span>
            </h2>
            <div class="screenshots-grid">
                ${vueScreenshots.map(s => `
                <div class="screenshot-card">
                    <div class="screenshot-header">${s.name.replace(/-/g, ' ')}</div>
                    <div class="screenshot-container">
                        <img src="vue-app/${s.full}" alt="${s.name}" class="screenshot-img" id="vue-${s.name}">
                        ${fs.existsSync(path.join(vueScreenshotsDir, s.viewport)) ? `
                        <button class="view-toggle" onclick="toggleView('vue-${s.name}', 'vue-app/${s.full}', 'vue-app/${s.viewport}')">
                            Toggle View
                        </button>` : ''}
                    </div>
                </div>
                `).join('')}
            </div>
        </div>

        <div class="app-section">
            <h2 class="section-title">
                React Native Mobile App
                <span class="tech-badge">Expo + React Native Paper</span>
            </h2>
            <div class="screenshots-grid">
                ${reactScreenshots.length > 0 ? reactScreenshots.map(s => `
                <div class="screenshot-card">
                    <div class="screenshot-header">${s.name.replace(/-/g, ' ')}</div>
                    <div class="screenshot-container">
                        <img src="react-app/${s.file}" alt="${s.name}" class="screenshot-img">
                    </div>
                </div>
                `).join('') : `
                <div class="screenshot-card">
                    <div class="screenshot-header">React Native App</div>
                    <div class="screenshot-container">
                        <div class="no-screenshot">
                            <p>React Native screenshots not available.</p>
                            <p>Run the app with: <code>npx expo start --web</code></p>
                        </div>
                    </div>
                </div>
                `}
            </div>
        </div>
    </div>

    <script>
        function toggleView(id, full, viewport) {
            const img = document.getElementById(id);
            if (img.src.includes(viewport.split('/').pop())) {
                img.src = full;
            } else {
                img.src = viewport;
            }
        }
    </script>
</body>
</html>
  `;

  fs.writeFileSync(path.join(screenshotsDir, 'index.html'), html);
  console.log('    ✅ HTML report generated at: app-screenshots/index.html');
}

async function main() {
  console.log('🚀 Starting screenshot capture process...\n');

  try {
    // Check if Vue dev server is running
    await captureVueScreenshots();
  } catch (error) {
    console.error('Vue screenshots failed:', error.message);
  }

  try {
    // Check if React Native web is available
    await captureReactNativeWebScreenshots();
  } catch (error) {
    console.error('React Native screenshots failed:', error.message);
  }

  // Generate HTML report
  generateHTMLReport();

  console.log('\n✨ Process complete!');
  console.log('📂 Screenshots saved in: app-screenshots/');
  console.log('🌐 Open app-screenshots/index.html to view the report');
}

// Main execution
main().catch(error => {
  console.error('Error:', error.message);
  if (error.message.includes("Executable doesn't exist")) {
    console.log('\n📦 Please install Playwright browsers:');
    console.log('   cd frontend-vue-old && npx playwright install');
  }
});