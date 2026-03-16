import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  page.on('requestfailed', request =>
    console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText)
  );

  console.log('Navigating to http://localhost:5174/');
  await page.goto('http://localhost:5174/', { waitUntil: 'networkidle0' });
  
  console.log('Extracting body...');
  const html = await page.content();
  if (!html.includes('TNeGA')) {
    console.log('BODY DOES NOT CONTAIN APP CONTENT');
  } else {
    console.log('BODY SEEMS OK');
  }

  await browser.close();
})();
