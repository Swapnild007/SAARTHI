(()=>{
  const element=id=>document.getElementById(id);
  const wizard=element('ownerWizard');
  let busy=false;
  const showError=message=>{
    element('wizardError').textContent=message;
    element('wizardError').hidden=!message;
  };
  const request=async(path,payload)=>{
    const response=await fetch(path,{
      method:payload?'POST':'GET',redirect:'error',credentials:'same-origin',
      headers:payload?{'Content-Type':'application/json'}:{},
      body:payload?JSON.stringify(payload):undefined,
      signal:AbortSignal.timeout(23000)
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'Setup could not complete. Check the connection and retry.');
    return data;
  };
  const showStage=stage=>{
    element('wizardConnections').hidden=stage!=='connection_required';
    element('wizardVerify').hidden=stage!=='verify';
    element('wizardPassword').hidden=stage!=='password';
  };
  const check=async()=>{
    showError('');
    showStage('connection_required');
    try{
      const status=await request('/api/onboarding');
      element('wizardStatus').textContent=status.message;
      if(status.ok){
        element('wizardIntent').value=status.stage==='sign_in'?'recover':'setup';
        showStage('verify');
      }
    }catch{showError('Could not check setup. Check your connection and try again.');}
  };
  element('openOwnerSetup').addEventListener('click',()=>{
    element('sessionDialog').close();
    wizard.showModal();
    check();
  });
  element('wizardCheck').addEventListener('click',check);
  element('closeOwnerWizard').addEventListener('click',()=>{
    wizard.close();
    ['wizardToken','wizardNewPassword','wizardRepeatPassword'].forEach(id=>{element(id).value='';});
  });
  const handle=async(event,action)=>{
    event.preventDefault();
    if(busy)return;
    busy=true;
    const button=event.currentTarget.querySelector('[type=submit]');
    button.disabled=true;
    showError('');
    try{await action();}
    catch(error){showError(error.message||'Setup is temporarily unavailable. Try again.');}
    finally{busy=false;button.disabled=false;}
  };
  element('wizardVerify').addEventListener('submit',event=>handle(event,async()=>{
    try{
      await request('/api/onboarding/verify',{
        management_token:element('wizardToken').value,
        intent:element('wizardIntent').value
      });
      element('wizardStatus').textContent='Ownership verified. Create your password within ten minutes.';
      showStage('password');
      element('wizardNewPassword').focus();
    }finally{element('wizardToken').value='';}
  }));
  element('wizardPassword').addEventListener('submit',event=>handle(event,async()=>{
    const password=element('wizardNewPassword').value;
    if(password!==element('wizardRepeatPassword').value)throw new Error('The passwords do not match.');
    try{
      await request('/api/onboarding/password',{password});
      element('wizardStatus').textContent='Your password is saved and you are signed in. Return to the assistant.';
      showStage('complete');
      window.dispatchEvent(new Event('saarthi-owner-signed-in'));
    }finally{
      element('wizardNewPassword').value='';
      element('wizardRepeatPassword').value='';
    }
  }));
  request('/api/onboarding').then(status=>{
    if(status.stage==='verify_owner'||status.stage==='connection_required'){
      if(!wizard.open)wizard.showModal();
      element('wizardStatus').textContent=status.message;
      showStage(status.stage==='verify_owner'?'verify':'connection_required');
    }
  }).catch(()=>{});
  element('ownerSignOut').addEventListener('click',async()=>{
    try{
      await request('/api/session/logout',{});
      window.dispatchEvent(new Event('saarthi-owner-signed-out'));
      element('sessionDialog').close();
    }catch(error){
      element('sessionError').hidden=false;
      element('sessionError').textContent=error.message;
    }
  });
})();
