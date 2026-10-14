// Offline UI fixture only. Never used for live-run presentation evidence.
const {chromium}=require('playwright-core');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const excerpt='Offline test fixture: suppliers can publish their profiles.';
  await page.route('**/api/conversations/*/messages',route=>route.fulfill({json:{text:excerpt,sources:[{id:'fixture',title:'Offline evidence fixture',effective_date:'2026-10-11',excerpt,source:'https://example.invalid'}],plans:[],qualification:{category:'industrial fasteners',buyers:'industrial buyers'},actions:[],ai_generated:false}}));
  await page.goto('http://127.0.0.1:8012');
  await page.getByRole('button',{name:'Ask about mjPROConnect'}).click();
  await page.getByRole('button',{name:'How it works',exact:true}).click();
  await page.getByText('Why this answer?',{exact:false}).click();
  assert.equal(await page.locator('.evidence-source blockquote').innerText(),excerpt);
  await page.getByText('Reviewed 2026-10-11',{exact:true}).waitFor();
  await page.getByText('Details you’ve shared',{exact:true}).click();
  assert.equal(await page.locator('.shared-details dd').allTextContents().then(x=>x.join('|')),'industrial fasteners|industrial buyers');
  for(const viewport of [{width:320,height:568},{width:390,height:844},{width:1280,height:1000}]){
   await page.setViewportSize(viewport);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
   assert(await page.locator('.evidence-source blockquote').isVisible());
  }
  await page.keyboard.press('Escape');
  assert(await page.getByRole('button',{name:'Ask about mjPROConnect'}).evaluate(e=>e===document.activeElement));
  console.log('PASS: offline evidence excerpt/title/date, shared fields, mobile sizing and focus return. No Google calls.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
