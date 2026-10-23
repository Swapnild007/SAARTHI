/* Local bundled pages keep their origin; only API requests use the configured backend. */
(() => {
  'use strict';
  let cap=window.Capacitor;
  if(!cap&&window.parent!==window)try{cap=window.parent.Capacitor;}catch{}
  const native=!!cap?.isNativePlatform?.();
  const origin=native ? window.SaarthiNativeConfig?.apiOrigin || '' : '';
  const apiUrl=path=>origin+path;
  if(native){
    const original=window.fetch.bind(window);
    window.fetch=(input,options)=>{
      const url=new URL(typeof input==='string'||input instanceof URL?input:input.url,location.href);
      if(url.origin===location.origin&&url.pathname.startsWith('/api/')){
        if(!origin)return Promise.reject(new Error('Android backend is not configured. Offline utilities remain available.'));
        return original(input instanceof Request?new Request(apiUrl(url.pathname+url.search),input):apiUrl(url.pathname+url.search),options);
      }
      return original(input,options);
    };
  }
  const plugins={};
  // Plain-script Capacitor apps receive generated Plugins proxies from Android.
  // registerPlugin is available only when @capacitor/core has been bundled.
  const plugin=name=>plugins[name] ||= (cap.registerPlugin?cap.registerPlugin(name):cap.Plugins?.[name]);
  async function execute(action,args={}){
    try{
      if(!native)return {ok:false,action,code:'UNSUPPORTED',message:'This operation requires the SAARTHI Android app.'};
      let data;
      if(action==='location'){
        const geo=plugin('Geolocation');
        const permission=await geo.requestPermissions({permissions:['location']});
        if(permission.location!=='granted'&&permission.coarseLocation!=='granted')return {ok:false,action,code:'PERMISSION_DENIED',message:'Location permission was denied.'};
        const p=await geo.getCurrentPosition({enableHighAccuracy:false,timeout:10000,maximumAge:30000});
        data={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,timestamp:p.timestamp};
      }else if(action==='camera'){
        data=await plugin('Camera').getPhoto({quality:85,resultType:'uri',source:'CAMERA',saveToGallery:false});
      }else if(action==='network')data=await plugin('Network').getStatus();
      else if(action==='notify'){
        const notifications=plugin('LocalNotifications');
        const permission=await notifications.requestPermissions();
        if(permission.display!=='granted')return {ok:false,action,code:'PERMISSION_DENIED',message:'Notification permission was denied.'};
        await notifications.schedule({notifications:[{id:Math.floor(Math.random()*2147483646)+1,title:'SAARTHI',body:String(args.text||'SAARTHI is ready.').slice(0,500)}]});
        data={submitted:true};
      }else data=await plugin('SaarthiDevice').execute({...args,action});
      if(data?.ok===false)return {...data,action};
      return {ok:true,action,data};
    }catch(error){return {ok:false,action,code:String(error.code||'FAILED'),message:'Device action could not finish. Check permissions and available device services.'};}
  }
  async function saveBlob(blob,name){
    if(blob.size>1000000)throw Error('Export is larger than the native 1 MB limit. Export from the web app.');
    const bytes=new Uint8Array(await blob.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const mime=name.endsWith('.zip')?'application/zip':name.endsWith('.html')?'text/html':'application/json';
    const result=await execute('saveDocument',{name,mime,data:btoa(binary)});
    if(!result.ok)throw Error(result.message);return result;
  }
  window.SaarthiDevice={native,apiOrigin:origin,apiUrl,execute,plugin,saveBlob};
})();
