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
  await page.request.post('/fixture/reset-rate');
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

test('Android-profile touch, orientation and denied voice preserve the composer',async({page},testInfo)=>{
  test.skip(testInfo.project.name!=='android-profile','Scenario requires the configured touch profile');
  await page.addInitScript(()=>{
    window.SpeechRecognition=class {
      start(){this.onerror({error:'not-allowed'});}
    };
  });
  const errors=await start(page);
  await input(page).tap();
  await expect(input(page)).toBeFocused();
  await input(page).fill('touch portrait');
  await send(page).tap();
  await expect(replies(page)).toContainText('touch portrait');
  await page.setViewportSize({width:840,height:393});
  await expect(input(page)).toBeInViewport();
  await page.locator('#voiceCommand').tap();
  await expect(page.locator('#composerError')).toContainText('Microphone permission');
  await input(page).fill('touch landscape');
  await send(page).tap();
  await expect(replies(page).last()).toContainText('touch landscape');
  expect(errors).toEqual([]);
});

test('owner signs in through the dialog and remains signed in after reload',async({page})=>{
  const errors=await start(page);
  await page.context().clearCookies();
  await page.getByRole('button',{name:'Private sign-in',exact:true}).click();
  await page.locator('#ownerPassword').fill('incorrect-password');
  await page.locator('#sessionForm button[type=submit]').click();
  await expect(page.locator('#sessionError')).toContainText('Sign-in failed');
  await page.locator('#ownerPassword').fill('browser-fixture-password-1234');
  await page.locator('#sessionForm button[type=submit]').click();
  await expect(page.locator('#sessionDialog')).not.toBeVisible();
  await page.reload();
  const status=await page.request.get('/api/session');
  expect(status.ok()).toBeTruthy();
  await input(page).fill('authenticated owner turn');
  await send(page).click();
  await expect(replies(page).last()).toContainText('authenticated owner turn');
  expect(errors).toEqual([]);
});

test('mobile wizard creates and recovers owner access without a terminal',async({page})=>{
  const errors=await start(page);
  await page.request.post('/fixture/clear-owner');
  await page.context().clearCookies();
  const password='browser-fixture-password-1234';
  const open=async()=>{
    await page.getByRole('button',{name:'Private sign-in',exact:true}).click();
    await page.getByRole('button',{name:'Set up / recover account'}).click();
    await expect(page.locator('#wizardVerify')).toBeVisible();
  };
  const choosePassword=async()=>{
    await page.locator('#wizardNewPassword').fill(password);
    await page.locator('#wizardRepeatPassword').fill(password);
    await page.getByRole('button',{name:'Save password and sign in'}).click();
    await expect(page.locator('#wizardStatus')).toContainText('signed in');
    await page.getByRole('button',{name:'Return to assistant'}).click();
  };
  await open();
  await page.locator('#wizardToken').fill('wrong');
  await page.getByRole('button',{name:'Verify ownership'}).click();
  await expect(page.locator('#wizardError')).toContainText('did not authorize');
  await page.locator('#wizardToken').fill('browser-management-fixture');
  await page.getByRole('button',{name:'Verify ownership'}).click();
  await expect(page.locator('#wizardPassword')).toBeVisible();
  await expect(page.locator('#wizardToken')).toHaveValue('');
  await choosePassword();
  await input(page).fill('wizard-created conversation');
  await send(page).click();
  await expect(replies(page).last()).toContainText('wizard-created conversation');
  await page.reload();
  expect((await page.request.get('/api/session')).ok()).toBeTruthy();
  await page.getByRole('button',{name:'Conversation history',exact:true}).click();
  await page.locator('#mobileHistory').getByRole('button',{name:/wizard-created conversation/}).click();
  await expect(replies(page).last()).toContainText('wizard-created conversation');
  await page.getByRole('button',{name:'Private sign-in',exact:true}).click();
  await page.getByRole('button',{name:'Sign out',exact:true}).click();
  expect((await page.request.get('/api/session')).status()).toBe(401);
  await open();
  await expect(page.locator('#wizardIntent')).toHaveValue('recover');
  await page.locator('#wizardToken').fill('browser-management-fixture');
  await page.getByRole('button',{name:'Verify ownership'}).click();
  await choosePassword();
  expect((await page.request.get('/api/session')).ok()).toBeTruthy();
  expect(errors).toEqual([]);
});

test('mobile wizard explains missing service connections',async({page})=>{
  await start(page);
  await page.route('**/api/onboarding',route=>route.fulfill({json:{
    ok:false,stage:'connection_required',message:'The conversation database is not connected yet.'
  }}));
  await page.getByRole('button',{name:'Private sign-in',exact:true}).click();
  await page.getByRole('button',{name:'Set up / recover account'}).click();
  await expect(page.locator('#wizardConnections')).toBeVisible();
  await expect(page.locator('#wizardVerify')).toBeHidden();
  await expect(page.locator('#wizardStatus')).toContainText('not connected');
});
