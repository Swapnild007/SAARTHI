const {defineConfig, devices}=require('@playwright/test');

module.exports=defineConfig({
  testDir:'tests/browser',
  timeout:60000,
  workers:1,
  use:{
    baseURL:'http://127.0.0.1:8765',trace:'retain-on-failure',
    launchOptions:process.env.SAARTHI_BROWSER_EXECUTABLE?{
      executablePath:process.env.SAARTHI_BROWSER_EXECUTABLE,
      args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote']
    }:{},
  },
  projects:[
    {name:'desktop',use:{...devices['Desktop Chrome']}},
    {name:'android-profile',use:{...devices['Pixel 7']}},
  ],
  webServer:{
    command:'python -m uvicorn server:app --app-dir tests/browser --host 127.0.0.1 --port 8765',
    url:'http://127.0.0.1:8765/api/health',
    timeout:15000,
    reuseExistingServer:false
  }
});
