package com.saarthi.assistant;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.widget.TextView;
import androidx.webkit.WebViewFeature;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle state) {
        registerPlugin(SaarthiDevicePlugin.class);
        super.onCreate(state);
        // AppForge runs untrusted sandboxed frames. Never expose the legacy
        // JavascriptInterface bridge, which lacks main-frame origin checks.
        bridge.getWebView().removeJavascriptInterface("androidBridge");
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            bridge.getWebView().destroy();
            TextView message = new TextView(this);
            message.setPadding(32, 64, 32, 32);
            message.setText("Update Android System WebView or Chrome to use SAARTHI securely.");
            setContentView(message);
        }
    }
}
