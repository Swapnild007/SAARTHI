const {test, expect}=require('@playwright/test');

const input=page=>page.getByRole('textbox',{name:'Message',exact:true});
const send=page=>page.getByRole('button',{name:'Send message',exact:true});
const userMessages=page=>page.locator('.conversation-message.user');
const replies=page=>page.locator('.conversation-message.assistant');

async function start(page){
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',route=>{
    if(new URL(route.request().url()).origin!=='http://127.0.0.1:8765')return route.abort();
    return route.continue();
  });
  await page.goto('/');
  await expect(page.locator('body')).not.toHaveClass(/splash-active/,{timeout:10000});
  const signIn=await page.request.post('/api/session/login',{data:{password:'browser-fixture-password-1234'}});
  expect(signIn.ok()).toBeTruthy();
  return errors;
}

test('first send, guarded submission, correct thread and 40-message reload',async({page})=>{
  const errors=await start(page);
  const requests=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/command'))requests.push(request.postDataJSON());});
  await input(page).fill('browser turn 0');
  await send(page).click();
  await expect(userMessages(page)).toHaveCount(1);
  await page.evaluate(()=>document.querySelector('#conversationComposer').requestSubmit());
  await expect(replies(page)).toHaveText(/Reply to browser turn 0/);
  expect(requests).toHaveLength(1);
  for(let i=1;i<20;i++){
    await input(page).fill('browser turn '+i);
    await input(page).press('Enter');
    await expect(replies(page)).toHaveCount(i+1);
  }
  expect(requests).toHaveLength(20);
  expect(new Set(requests.map(request=>request.conversation_id)).size).toBe(1);
  expect(new Set(requests.map(request=>request.turn_id)).size).toBe(20);
  await page.reload();
  await expect(page.locator('body')).not.toHaveClass(/splash-active/,{timeout:10000});
  await page.getByRole('button',{name:'Conversation history',exact:true}).click();
  await page.locator('#mobileHistory').getByRole('button',{name:/browser turn 0/}).click();
  await expect(userMessages(page)).toHaveCount(20);
  await expect(replies(page)).toHaveCount(20);
  expect(errors).toEqual([]);
});

test('timeout recovers, attachments and code reach the original UI',async({page})=>{
  const errors=await start(page);
  await input(page).fill('fixture-deadline');
  await send(page).click();
  await expect(page.locator('#composerError')).toContainText('deadline');
  await expect(send(page)).toBeEnabled();
  const attachment=page.locator('#saarthiFileInput');
  await attachment.setInputFiles({name:'numbers.csv',mimeType:'text/csv',buffer:Buffer.from('name,count\nA,2')});
  await expect(page.locator('[data-remove-attachment]').first()).toBeVisible();
  await input(page).fill('fixture-file:include');
  await send(page).click();
  await expect(replies(page).last()).toContainText('Included numbers.csv');
  await page.locator('[data-remove-attachment]').first().click();
  await input(page).fill('fixture-code');
  await send(page).click();
  await expect(replies(page).last().locator('pre code')).toContainText("print('saarthi')");
  expect(errors).toEqual([]);
});

test('in-flight reply stays on the thread that initiated it',async({page})=>{
  const errors=await start(page);
  await page.route('**/api/command',async route=>{
    const response=await route.fetch();
    await new Promise(resolve=>setTimeout(resolve,700));
    await route.fulfill({response});
  });
  await input(page).fill('original thread');
  await send(page).click();
  await page.evaluate(()=>window.SaarthiApp.startNewConversation());
  await expect(replies(page)).toHaveCount(0);
  await page.getByRole('button',{name:'Conversation history',exact:true}).click();
  await page.locator('#mobileHistory').getByRole('button',{name:/original thread/}).click();
  await expect(replies(page)).toHaveText(/Reply to original thread/);
  expect(errors).toEqual([]);
});

test('a backup restores into an empty browser profile',async({page,browser},testInfo)=>{
  const errors=await start(page);
  await input(page).fill('back up this thread');
  await send(page).click();
  await expect(replies(page)).toHaveText(/Reply to back up this thread/);
  await page.getByRole('button',{name:'Conversation history',exact:true}).click();
  const download=page.waitForEvent('download');
  await page.locator('#mobileHistory').getByRole('button',{name:'Export backup'}).click();
  const file=testInfo.outputPath('conversations.json');
  await (await download).saveAs(file);
  const fresh=await browser.newContext({baseURL:'http://127.0.0.1:8765'});
  try{
    const restored=await fresh.newPage();
    await restored.goto('/');
    await expect(restored.locator('body')).not.toHaveClass(/splash-active/,{timeout:10000});
    await restored.getByRole('button',{name:'Conversation history',exact:true}).click();
    await restored.locator('#mobileHistory [data-history-file]').setInputFiles(file);
    await restored.locator('#mobileHistory').getByRole('button',{name:/back up this thread/}).click();
    await expect(replies(restored)).toHaveText(/Reply to back up this thread/);
    expect(errors).toEqual([]);
  }finally{
    await fresh.close();
  }
});


test('cancellation recovers the composer and does not commit an assistant reply',async({page})=>{
  const errors=await start(page);
  await input(page).fill('fixture-cancel');
  const sent=page.waitForRequest(request=>request.method()==='POST'&&request.url().endsWith('/api/command'));
  await send(page).click();
  await sent;
  await page.waitForTimeout(350);
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  await expect(page.locator('#composerError')).toContainText('This turn was cancelled.');
  await expect(send(page)).toBeEnabled();
  await expect(page.getByRole('button',{name:'Check or retry turn'})).toBeHidden();
  await expect(userMessages(page)).toHaveCount(1);
  await expect(replies(page)).toHaveCount(0);
  expect(errors).toEqual([]);
});
