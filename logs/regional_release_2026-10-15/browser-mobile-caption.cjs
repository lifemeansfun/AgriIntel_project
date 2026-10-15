const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium}=require('/Users/manishharigovind/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader']});
 try{
 const page=await browser.newPage({viewport:{width:375,height:812}});
 await page.goto('http://127.0.0.1:5174',{waitUntil:'networkidle'});
 await page.waitForTimeout(2500);
 await page.waitForFunction(()=>document.querySelector('#advisory-scenario')?.options.length===2);
 await page.locator('#advisory-scenario').selectOption(await page.locator('#advisory-scenario option').nth(1).getAttribute('value'));
 const caption=page.getByText('Committed production uses median yield; capacity usage uses upper yield. Outside supply is already included in the scenario.',{exact:true});
 await caption.waitFor();
 await page.getByRole('button',{name:'Toggle day/night theme'}).click();
 await caption.scrollIntoViewIfNeeded();
 const rect=await caption.boundingBox();
 assert.ok(rect.x>=0&&rect.x+rect.width<=375);
 assert.ok(rect.height>30,'Caption must wrap at mobile width');
 const screenshot=path.join(__dirname,'final-mobile-supply-caption.png');
 await page.screenshot({path:screenshot});
 fs.writeFileSync(path.join(__dirname,'browser-mobile-caption.json'),JSON.stringify({status:'pass',caption_bounds:rect,screenshot}));
 console.log('PASS mobile supply explanation wraps outside horizontal table scroller');
 } finally{await browser.close();}
})();
