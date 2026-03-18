const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  console.log('Navigating to website...');
  await page.goto('https://orchestra-ui.lovable.app/', { waitUntil: 'networkidle', timeout: 60000 });
  
  // Wait a bit extra to ensure animations/renders are done
  await page.waitForTimeout(5000);
  
  console.log('Taking screenshot...');
  await page.screenshot({ path: 'lovable.png', fullPage: true });
  
  console.log('Extracting HTML...');
  const html = await page.content();
  fs.writeFileSync('lovable.html', html);
  
  await browser.close();
  console.log('Done.');
})();
