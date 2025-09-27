const fs = require('fs');
const path = require('path');

// Analyze Vue app structure
function analyzeVueApp() {
  const vuePagesDir = path.join(__dirname, 'frontend-vue-old/src/pages');
  const vuePages = [];

  function scanDirectory(dir, prefix = '') {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        scanDirectory(fullPath, prefix + file + '/');
      } else if (file.endsWith('.vue')) {
        const content = fs.readFileSync(fullPath, 'utf8');
        const hasTemplate = content.includes('<template>');
        const hasScript = content.includes('<script');
        const hasStyle = content.includes('<style');

        // Extract component features
        const features = [];
        if (content.includes('q-page')) features.push('Quasar Page');
        if (content.includes('q-btn')) features.push('Buttons');
        if (content.includes('q-input')) features.push('Forms');
        if (content.includes('q-card')) features.push('Cards');
        if (content.includes('q-table')) features.push('Table');
        if (content.includes('q-dialog')) features.push('Dialog');
        if (content.includes('GoogleSignIn')) features.push('Google Auth');
        if (content.includes('QrCode')) features.push('QR Code');
        if (content.includes('camera')) features.push('Camera');

        vuePages.push({
          name: file.replace('.vue', ''),
          path: prefix + file,
          hasTemplate,
          hasScript,
          hasStyle,
          features,
          lines: content.split('\n').length
        });
      }
    });
  }

  if (fs.existsSync(vuePagesDir)) {
    scanDirectory(vuePagesDir);
  }

  return vuePages;
}

// Analyze React Native app structure
function analyzeReactApp() {
  const reactScreensDir = path.join(__dirname, 'mobile/src/screens');
  const reactScreens = [];

  function scanDirectory(dir, prefix = '') {
    const files = fs.readdirSync(dir);
    files.forEach(file => {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        scanDirectory(fullPath, prefix + file + '/');
      } else if (file.endsWith('.tsx')) {
        const content = fs.readFileSync(fullPath, 'utf8');

        // Extract component features
        const features = [];
        if (content.includes('TextInput')) features.push('Text Input');
        if (content.includes('Button')) features.push('Buttons');
        if (content.includes('Card')) features.push('Cards');
        if (content.includes('ScrollView')) features.push('Scrollable');
        if (content.includes('FlatList')) features.push('List');
        if (content.includes('Modal')) features.push('Modal');
        if (content.includes('Camera')) features.push('Camera');
        if (content.includes('QRCode')) features.push('QR Code');
        if (content.includes('GoogleSignIn')) features.push('Google Auth');
        if (content.includes('useAuthStore')) features.push('Auth State');
        if (content.includes('react-native-paper')) features.push('Material Design');

        // Check implementation status
        const hasImplementation = !content.includes('// TODO') &&
                                !content.includes('Coming soon') &&
                                content.includes('return (');

        reactScreens.push({
          name: file.replace('.tsx', ''),
          path: prefix + file,
          features,
          lines: content.split('\n').length,
          implemented: hasImplementation
        });
      }
    });
  }

  if (fs.existsSync(reactScreensDir)) {
    scanDirectory(reactScreensDir);
  }

  return reactScreens;
}

// Generate comparison report
function generateComparisonReport() {
  const vuePages = analyzeVueApp();
  const reactScreens = analyzeReactApp();

  // Create detailed analysis
  const report = {
    summary: {
      vueApp: {
        totalPages: vuePages.length,
        totalLines: vuePages.reduce((sum, p) => sum + p.lines, 0),
        technologies: ['Vue 3', 'Quasar Framework', 'TypeScript', 'Vite']
      },
      reactApp: {
        totalScreens: reactScreens.length,
        implementedScreens: reactScreens.filter(s => s.implemented).length,
        totalLines: reactScreens.reduce((sum, s) => sum + s.lines, 0),
        technologies: ['React Native', 'Expo', 'React Native Paper', 'TypeScript', 'Zustand']
      }
    },
    vuePages,
    reactScreens,
    comparison: generateFeatureComparison(vuePages, reactScreens)
  };

  // Generate HTML report
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NAGA Mobile Apps - Code Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .summary-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }
        .app-summary {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        }
        .app-title {
            font-size: 1.5em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .vue-color { color: #42b883; }
        .react-color { color: #61dafb; }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .stat {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .tech-stack {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }
        .tech-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
        }
        .pages-table {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }
        .table-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            font-size: 1.2em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .feature-pill {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin: 2px;
        }
        .status-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status-complete {
            background: #c8e6c9;
            color: #2e7d32;
        }
        .status-partial {
            background: #fff3cd;
            color: #f57c00;
        }
        .status-todo {
            background: #ffcdd2;
            color: #c62828;
        }
        .comparison-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }
        .comparison-header {
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #333;
        }
        .feature-comparison {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 20px;
            align-items: center;
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .feature-name {
            text-align: center;
            font-weight: 600;
            color: #666;
        }
        .implementation-bar {
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        .implementation-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 NAGA Mobile Apps - Code Analysis Report</h1>

        <div class="summary-grid">
            <div class="app-summary">
                <h2 class="app-title vue-color">
                    <span>⚡</span> Vue 3 Mobile App
                </h2>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">${report.summary.vueApp.totalPages}</div>
                        <div class="stat-label">Total Pages</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${report.summary.vueApp.totalLines.toLocaleString()}</div>
                        <div class="stat-label">Lines of Code</div>
                    </div>
                </div>
                <div class="tech-stack">
                    ${report.summary.vueApp.technologies.map(t =>
                        `<span class="tech-badge">${t}</span>`
                    ).join('')}
                </div>
            </div>

            <div class="app-summary">
                <h2 class="app-title react-color">
                    <span>⚛️</span> React Native App
                </h2>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">${report.summary.reactApp.totalScreens}</div>
                        <div class="stat-label">Total Screens</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${report.summary.reactApp.totalLines.toLocaleString()}</div>
                        <div class="stat-label">Lines of Code</div>
                    </div>
                </div>
                <div class="tech-stack">
                    ${report.summary.reactApp.technologies.map(t =>
                        `<span class="tech-badge">${t}</span>`
                    ).join('')}
                </div>
            </div>
        </div>

        <div class="comparison-section">
            <h3 class="comparison-header">📊 Implementation Comparison</h3>
            ${report.comparison}
        </div>

        <div class="pages-table">
            <div class="table-header">Vue 3 Pages (${vuePages.length})</div>
            <table>
                <thead>
                    <tr>
                        <th>Page Name</th>
                        <th>Path</th>
                        <th>Features</th>
                        <th>Lines</th>
                    </tr>
                </thead>
                <tbody>
                    ${vuePages.map(page => `
                    <tr>
                        <td><strong>${page.name}</strong></td>
                        <td>${page.path}</td>
                        <td>${page.features.map(f =>
                            `<span class="feature-pill">${f}</span>`
                        ).join('') || '-'}</td>
                        <td>${page.lines}</td>
                    </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <div class="pages-table">
            <div class="table-header">React Native Screens (${reactScreens.length})</div>
            <table>
                <thead>
                    <tr>
                        <th>Screen Name</th>
                        <th>Path</th>
                        <th>Features</th>
                        <th>Status</th>
                        <th>Lines</th>
                    </tr>
                </thead>
                <tbody>
                    ${reactScreens.map(screen => `
                    <tr>
                        <td><strong>${screen.name}</strong></td>
                        <td>${screen.path}</td>
                        <td>${screen.features.map(f =>
                            `<span class="feature-pill">${f}</span>`
                        ).join('') || '-'}</td>
                        <td>
                            <span class="status-badge ${screen.implemented ? 'status-complete' : 'status-todo'}">
                                ${screen.implemented ? '✅ Implemented' : '🚧 TODO'}
                            </span>
                        </td>
                        <td>${screen.lines}</td>
                    </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
  `;

  return html;
}

function generateFeatureComparison(vuePages, reactScreens) {
  // Map Vue pages to features
  const vueFeatures = new Map();
  vuePages.forEach(page => {
    const category = page.path.includes('teacher/') ? 'Teacher' : 'Student';
    const feature = `${category}: ${page.name}`;
    vueFeatures.set(feature, page);
  });

  // Map React screens to features
  const reactFeatures = new Map();
  reactScreens.forEach(screen => {
    const category = screen.path.includes('teacher/') ? 'Teacher' :
                    screen.path.includes('student/') ? 'Student' : 'Common';
    const feature = `${category}: ${screen.name}`;
    reactFeatures.set(feature, screen);
  });

  // Compare features
  const allFeatures = new Set([...vueFeatures.keys(), ...reactFeatures.keys()]);
  const comparison = [];

  allFeatures.forEach(feature => {
    const inVue = vueFeatures.has(feature);
    const inReact = reactFeatures.has(feature);
    const reactImplemented = inReact && reactFeatures.get(feature).implemented;

    comparison.push({
      feature,
      vue: inVue,
      react: inReact,
      reactImplemented,
      status: inVue && reactImplemented ? 'complete' :
              inVue && inReact ? 'partial' :
              inVue ? 'vue-only' : 'react-only'
    });
  });

  // Generate HTML for comparison
  return comparison
    .sort((a, b) => a.feature.localeCompare(b.feature))
    .map(item => `
    <div class="feature-comparison">
        <div style="text-align: right">
            ${item.vue ? '✅ Implemented' : '❌ Missing'}
        </div>
        <div class="feature-name">${item.feature}</div>
        <div>
            ${item.reactImplemented ? '✅ Implemented' :
              item.react ? '🚧 In Progress' : '❌ Missing'}
        </div>
    </div>
    `).join('');
}

// Main execution
console.log('🔍 Analyzing mobile apps...\n');

const reportHtml = generateComparisonReport();

// Save report
const reportPath = path.join(__dirname, 'app-analysis-report.html');
fs.writeFileSync(reportPath, reportHtml);

console.log('✅ Analysis complete!');
console.log(`📄 Report saved to: ${reportPath}`);
console.log('\n📊 Quick Summary:');
console.log('  Vue 3 App: ' + analyzeVueApp().length + ' pages');
console.log('  React Native App: ' + analyzeReactApp().length + ' screens');
console.log('\nOpen app-analysis-report.html to view the detailed report.');