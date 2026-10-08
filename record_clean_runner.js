const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist']
  });
  const ctx = await browser.newContext({
    viewport: { width: 540, height: 960 },
    recordVideo: { dir: 'recordings', size: { width: 540, height: 960 } }
  });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);

  // Keep the run alive with timed jumps. No hands/camera footage: this is direct game capture.
  const started = Date.now();
  let n = 0;
  while (Date.now() - started < 42000) {
    await page.keyboard.press('ArrowUp');
    if (n % 5 === 2) await page.keyboard.press('ArrowRight');
    if (n % 5 === 4) await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(700 + (n % 3) * 90);
    n++;
  }

  const video = page.video();
  await ctx.close();
  const path = await video.path();
  fs.copyFileSync(path, 'captured_gameplay.webm');
  await browser.close();
})();
